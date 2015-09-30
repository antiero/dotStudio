# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import tempfile
import re
import sys
import math
import traceback
import copy

import hiero.core
import hiero.core.log as log
import hiero.core.nuke as nuke

import FnShotExporter
import FnExternalRender
import FnEffectHelpers
from FnSubmission import Submission
from FnReformatHelpers import reformatNodeFromPreset
from . FnExportUtil import trackItemTimeCodeNodeStartFrame


class TranscodeExporter(FnExternalRender.NukeRenderTask):
  def __init__(self, initDict):
    """Initialize"""
    FnExternalRender.NukeRenderTask.__init__(self, initDict )

    self._audioFile  = None
    self._deleteAudioOnFinished = None
    self._tag_guid = None

    # Figure out the script location
    path = self.resolvedExportPath()
    dirname, filename = os.path.split(path)
    root, ext = os.path.splitext(filename)

    # Remove any trailing .#### or %0?d characters.  This should only be done to the filename part of the path,
    # otherwise the directory can end up being different to where the transcodes are placed.
    #
    # We might want to disallow these characters from dir names at some other time, but if we do that would be handled
    # in resolvedExportPath().
    percentmatch = re.search("%\d+d", root)
    if percentmatch:
      percentpad = percentmatch.group()
      root = root.replace(percentpad, '')

    # Join the dir and root.  Note that os.path.join is not used here because it introduces backslashes on Windows,
    # which is bad if they get written into a Nuke script
    self._root = dirname + "/" + root.rstrip('#').rstrip('.')

    scriptExtension = ".nknc" if hiero.core.isNC() else ".nk"
    self._scriptfile = self._root + scriptExtension

    log.debug( "TranscodeExporter writing script to %s", self._scriptfile )

    self._renderTask = None
    if self._submission is not None:

      # Pass the frame range through to the submission.  This is useful for rendering through the frame
      # server, otherwise it would have to evaluate the script to determine it.
      start, end = self.outputRange()
      submissionDict = copy.copy(initDict)
      submissionDict["startFrame"] = start
      submissionDict["endFrame"] = end

      # Create a job on our submission to do the actual rendering.
      self._renderTask = self._submission.addJob( Submission.kNukeRender, submissionDict, self._scriptfile )

  def updateItem (self, originalItem, localtime):
    """updateItem - This is called by the processor prior to taskStart, crucially on the main thread.\n
      This gives the task an opportunity to modify the original item on the main thread, rather than the clone."""

    timestamp = self.timeStampString(localtime)
    tagName = str("Transcode {0} {1}").format(self._preset.properties()["file_type"], timestamp)
    tag = hiero.core.Tag(tagName, "icons:Nuke.png", False)

    tag.metadata().setValue("tag.pathtemplate", self._exportPath)
    tag.metadata().setValue("tag.description", "Transcode " + self._preset.properties()["file_type"])

    tag.metadata().setValue("tag.path", self.resolvedExportPath())
    tag.metadata().setValue("tag.localtime", str(localtime))

    # No point in adding script path if we're not planning on keeping the script
    if self._preset.properties()["keepNukeScript"]:
      tag.metadata().setValue("tag.script", self._scriptfile)

    start, end = self.outputRange()
    tag.metadata().setValue("tag.startframe", str(start))
    tag.metadata().setValue("tag.duration", str(end-start+1))
    
    frameoffset = self._startFrame if self._startFrame else 0
    if hiero.core.isVideoFileExtension(os.path.splitext(self.resolvedExportPath())[1].lower()):
      frameoffset = 0
    tag.metadata().setValue("tag.frameoffset", str(frameoffset))

    # Note: if exporting without cut handles, i.e. the whole clip, we do not try to determine  the handle values,
    # just writing zeroes.  The build track classes need to treat this as a special case.
    # There is an interesting 'feature' of how tags work which means that if you create a Tag with a certain name,
    # the code tries to find a previously created instance with that name, which has any metadata keys that were set before.
    # This means that when multiple shots are being exported, they inherit the tag from the previous one.  To avoid problems
    # always set these keys.
    startHandle, endHandle = 0, 0
    if self._cutHandles:
      startHandle, endHandle = self.outputHandles()

    tag.metadata().setValue("tag.starthandle", str(startHandle))
    tag.metadata().setValue("tag.endhandle", str(endHandle))

    # Store if retimes were applied in the export.  Note that if self._cutHandles
    # is None, we are exporting the full clip and retimes are never applied whatever the
    # value of self._retime
    applyingRetime = (self._retime and self._cutHandles is not None)
    appliedRetimesStr = "1" if applyingRetime else "0"
    tag.metadata().setValue("tag.appliedretimes", appliedRetimesStr)


    self._tag_guid = tag.guid()

    originalItem.addTag(tag)

    # The guid of the tag attached to the trackItem is different from the tag instace we created
    # Get the last tag in the list and store its guid
    self._tag_guid = originalItem.tags()[-1].guid()


  def writeAudio(self):
    if isinstance(self._item, (hiero.core.Sequence, hiero.core.TrackItem)):
      if self._sequenceHasAudio(self._sequence):

        self._audioFile = self._root + ".wav"

        if isinstance(self._item, hiero.core.Sequence):
          start, end = self.outputRange()
          self._item.writeAudioToFile(self._audioFile, start, end)

        elif isinstance(self._item, hiero.core.TrackItem):
          startHandle, endHandle = self.outputHandles()
          start, end = (self._item.timelineIn() - startHandle), (self._item.timelineOut() + endHandle) + 1

          # If trackitem write out just the audio within the cut
          self._sequence.writeAudioToFile(self._audioFile, start, end)

    if isinstance(self._item, hiero.core.Clip):
      if self._item.mediaSource().hasAudio():

        self._audioFile = self._root + ".wav"

        # If clip, write out full length
        self._item.writeAudioToFile(self._audioFile)

  def startTask(self):
    try:
      # Call base start task.
      FnExternalRender.NukeRenderTask.startTask(self)

      includeaudio = None
      # Aux properties are transcode ui options which dont automatically get added to the write node
      presetproperties = self._preset.properties()
      filetype = presetproperties["file_type"]
      if filetype in presetproperties:
        if "audiofile" in presetproperties[filetype]:
          includeaudio = presetproperties[filetype]["audiofile"]

      if includeaudio is None:
        includeaudio = self._preset._getCodecSettingsDefault(filetype, "audiofile")

      if self._deleteAudioOnFinished is None:
        self._deleteAudioOnFinished = self._preset._getCodecSettingsDefault(filetype, "deleteaudiofile")

      # Write out the audio bounce down
      if includeaudio:
        self.writeAudio()

      # Write our Nuke script
      self.buildScript()
      self.writeScript()

      # Start the render task if we have one
      if self._renderTask:
        self._renderTask.startTask()
        if self._renderTask.error():
          self.setError( self._renderTask.error() )
    except Exception as e:
      if self._renderTask and self._renderTask.error():
        self.setError( self._renderTask.error() )
      else:
        self.setError( "Error starting transcode\n\n%s" % str(e) )
        exc_type, exc_value, exc_traceback = sys.exc_info()
        hiero.core.log.exception("TranscodeExporter.startTask")

  def cleanupAudio(self):
    # Delete generated audio file if it was being written into a MOV
    if self._audioFile and self._deleteAudioOnFinished:
      self.deleteTemporaryFile( self._audioFile )

  def finishTask(self):
    # Finish the render task if we have one
    if self._renderTask:
      self._renderTask.finishTask()
    FnExternalRender.NukeRenderTask.finishTask(self)
    self.cleanupAudio()

  def _buildAdditionalNodes(self, item):
    # Callback from script generation to add additional nodes
    nodes = []
    data = self._preset.properties()["additionalNodesData"]
    if self._preset.properties()["additionalNodesEnabled"]:
      if isinstance(item, hiero.core.Clip):
        # Use AdditionalNodes data to populate based on clip tags
        nodes.extend(FnExternalRender.createAdditionalNodes(FnExternalRender.kPerShot, data, item))
      elif isinstance(item, hiero.core.TrackItem):
        # Use AdditionalNodes data to populate based on TrackItem tags
        nodes.extend(FnExternalRender.createAdditionalNodes(FnExternalRender.kPerShot, data, item))
      elif isinstance(item, (hiero.core.VideoTrack, hiero.core.AudioTrack)):
        # Use AdditionalNodes data to populate based on sequence tags
        nodes.extend(FnExternalRender.createAdditionalNodes(FnExternalRender.kPerTrack, data, item))
      elif isinstance(item, hiero.core.Sequence):
        # Use AdditionalNodes data to populate based on sequence tags
        nodes.extend(FnExternalRender.createAdditionalNodes(FnExternalRender.kPerSequence, data, item))

    return nodes


  def createPresetReformatNode(self):
    """ If reformat options are selected on the preset, create a ReformatNode.  Otherwise returns None. """
    try:
      return reformatNodeFromPreset(self._preset)
    except Exception as e:
      self.setError(str(e))


  def buildScript (self):
    # Generate a nuke script to render.
    script = nuke.ScriptWriter()
    self._script = script

    # Project setting for using OCIO nodes for colourspace transform
    useOCIONodes = self._project.lutUseOCIOForExport()

    # Export an individual track item
    if isinstance(self._item, (hiero.core.TrackItem, hiero.core.Clip)):

      isMovieContainerFormat = self._preset.properties()["file_type"] in ("mov", "mov32", "mov64", "ffmpeg")

      start, end = self.outputRange(ignoreRetimes=True, clampToSource=False)
      unclampedStart = start
      log.debug( "rootNode range is %s %s", start, end )

      firstFrame, lastFrame = start, end
      if self._startFrame is not None:
        firstFrame = self._startFrame

      # if startFrame is negative we can only assume this is intentional
      if start < 0 and (self._startFrame is None or self._startFrame >= 0) and not isMovieContainerFormat:
        # We dont want to export an image sequence with a negative frame numbers
        self.setWarning("%i Frames of handles will result in a negative frame index.\nFirst frame clamped to 0." % self._cutHandles)
        start = 0

      # The clip framerate may be invalid, if so, use parent sequence framerate
      fps, framerate, dropFrames = None, None, False
      if self._sequence:
        framerate = self._sequence.framerate()
        dropFrames = self._sequence.dropFrame()
      if self._clip.framerate().isValid():
        framerate = self._clip.framerate()
        dropFrames = self._clip.dropFrame()
      if framerate:
        fps = framerate.toFloat()

      # Create root node, this defines global frame range and framerate
      rootNode = nuke.RootNode(start, end, fps)
      rootNode.setKnob("project_directory", os.path.split(self.resolvedExportPath())[0])
      rootNode.addProjectSettings(self._projectSettings)
      script.addNode(rootNode)

      # Add Unconnected additional nodes
      if self._preset.properties()["additionalNodesEnabled"]:
        script.addNode(FnExternalRender.createAdditionalNodes(FnExternalRender.kUnconnected, self._preset.properties()["additionalNodesData"], self._item))

      # Now add the Read node.
      if self._cutHandles is None:
        self._clip.addToNukeScript(script, additionalNodesCallback=self._buildAdditionalNodes, firstFrame=firstFrame, trimmed=True, useOCIO=useOCIONodes)
      else:
        startHandle, endHandle = self.outputHandles()
        self._item.addToNukeScript(script,
                                  firstFrame=firstFrame,
                                  additionalNodesCallback=self._buildAdditionalNodes,
                                  includeRetimes=self._retime,
                                  retimeMethod=self._preset.properties()["method"],
                                  startHandle=startHandle,
                                  endHandle=endHandle,
                                  useOCIO=useOCIONodes )


      metadataNode = nuke.MetadataNode(metadatavalues=[("hiero/project", self._projectName), ("hiero/project_guid", self._project.guid()),("hiero/shot_tag_guid", self._tag_guid)] )

      # Add sequence Tags to metadata
      metadataNode.addMetadataFromTags( self._clip.tags() )

      # Need a framerate inorder to create a timecode
      if framerate:
        # Apply timeline offset to nuke output
        if self._cutHandles is None:
          timeCodeNodeStartFrame = unclampedStart
        else:
          startHandle, endHandle = self.outputHandles()
          timeCodeNodeStartFrame = trackItemTimeCodeNodeStartFrame(unclampedStart, self._item, startHandle, endHandle)

        script.addNode(nuke.AddTimeCodeNode(timecodeStart=self._clip.timecodeStart(), fps=framerate, dropFrames=dropFrames, frame=timeCodeNodeStartFrame))

        # The AddTimeCode field will insert an integer framerate into the metadata, if the framerate is floating point, we need to correct this
        metadataNode.addMetadata([("input/frame_rate",framerate.toFloat())])

      script.addNode(metadataNode)

      # Add effects from the sequence if we're exporting the cut.  It makes no sense to do this if the full clip is being exported.
      if isinstance(self._item, hiero.core.TrackItem) and self._cutHandles is not None:
        effectOffset = firstFrame - self._item.timelineIn() + self._cutHandles
        effects, annotations = FnEffectHelpers.findEffectsAnnotationsForTrackItems( [self._item] )

        # TODO Should we do anything with the annotations here?

        for effect in effects:
          effect.addToNukeScript(script, offset=effectOffset)


      # Add Burnin group (if enabled)
      self.addBurninNodes(script)

      # Get the output format, either from the clip or the preset,  and set it as the root format.
      # If a reformat is specified in the preset, add it immediately before the Write node.
      reformatNode = self._clip.format().addToNukeScript(None)
      presetReformatNode = self.createPresetReformatNode()
      if presetReformatNode:
        reformatNode = presetReformatNode
        script.addNode(reformatNode)
      rootNode.setKnob("format", reformatNode.knob("format"))

      # Build Write node from transcode settings
      try:
        writeNode = self.nukeWriteNode(framerate, project=self._project)
      except RuntimeError as e:
        # Failed to generate write node, set task error in export queue
        # Most likely because could not map default colourspace for format settings.
        self.setError(str(e))

      if self._audioFile:
        # If the transcode format is QuickTime add the path to the audio file knob

        if isMovieContainerFormat:
          writeNode.setKnob("audiofile", self._audioFile)
          # Option to keep WAV even if audio has been embedded in Quicktime
          presetproperties = self._preset.properties()
          filetype = presetproperties["file_type"]
          if "deleteaudiofile" in presetproperties[filetype]:
            self._deleteAudioOnFinished = presetproperties[filetype]["deleteaudiofile"]
          #writeNode.setKnob("units", 'Frames')
          #writeNode.setKnob("audio_offset",  offset)

      # And next the Write.
      script.addNode(writeNode)

    # Export an entire sequence
    elif isinstance(self._item, hiero.core.Sequence):

      # Get the range to set on the Root node. This is the range the nuke script will render by default.
      start, end = self.outputRange()
      log.debug( "TranscodeExporter: rootNode range is %s %s", start, end )

      framerate = self._sequence.framerate()
      dropFrames = self._sequence.dropFrame()
      fps = framerate.toFloat()

      rootNode = nuke.RootNode(start, end, fps)
      rootNode.setKnob("project_directory", os.path.split(self.resolvedExportPath())[0])
      rootNode.addProjectSettings(self._projectSettings)
      script.addNode(rootNode)

      # Add Unconnected additional nodes
      if self._preset.properties()["additionalNodesEnabled"]:
        script.addNode(FnExternalRender.createAdditionalNodes(FnExternalRender.kUnconnected, self._preset.properties()["additionalNodesData"], self._item))
      
      # Build out the sequence.

      additionalNodes = []

      self._sequence.addToNukeScript( script,
                                      additionalNodes=additionalNodes,
                                      additionalNodesCallback=self._buildAdditionalNodes,
                                      includeRetimes=True,
                                      retimeMethod=self._preset.properties()["method"],
                                      useOCIO=useOCIONodes,
                                      skipOffline=self._skipOffline,
                                      mediaToSkip=self._mediaToSkip
                                      )

      # Create metadata node
      metadataNode = nuke.MetadataNode(metadatavalues=[("hiero/project", self._projectName), ("hiero/project_guid", self._project.guid()), ("hiero/shot_tag_guid", self._tag_guid)] )

      # Add sequence Tags to metadata
      metadataNode.addMetadataFromTags( self._sequence.tags() )

      # Apply timeline offset to nuke output
      script.addNode(nuke.AddTimeCodeNode(timecodeStart=self._sequence.timecodeStart(), fps=framerate, dropFrames=dropFrames, frame= 0 if self._startFrame is None else self._startFrame))

      # The AddTimeCode field will insert an integer framerate into the metadata, if the framerate is floating point, we need to correct this
      metadataNode.addMetadata([("input/frame_rate", framerate.toFloat())])

      # And next the Write.
      script.addNode(metadataNode)

      # Add Burnin group (if enabled)
      self.addBurninNodes(script)

      # Get the output format, either from the sequence or the preset,  and set it as the root format.
      # If a reformat is specified in the preset, add it immediately before the Write node.
      outputReformatNode = self._sequence.format().addToNukeScript(resize=nuke.ReformatNode.kResizeNone, black_outside=False)
      rootFormat = outputReformatNode.knob("format")
      presetReformatNode = self.createPresetReformatNode()
      if presetReformatNode:
        outputReformatNode = presetReformatNode
        script.addNode(presetReformatNode)

        # If there is a reformat and it's 'to format', set the root format knob to that.
        if "format" in presetReformatNode.knobs():
          rootFormat = presetReformatNode.knob("format")

      rootNode.setKnob("format", rootFormat)

      # Build Write node from transcode settings
      try:
        writeNode = self.nukeWriteNode(framerate, project=self._project)
      except RuntimeError as e:
        # Failed to generate write node, set task error in export queue
        # Most likely because could not map default colourspace for format settings.
        self.setError(str(e))


      if self._audioFile:
        # If the transcode format is QuickTime, add the path to the audio file knob
        isMovieContainerFormat = self._preset.properties()["file_type"] in ("mov", "mov32", "mov64", "ffmpeg")

        if isMovieContainerFormat:
          writeNode.setKnob("audiofile", self._audioFile)
          presetproperties = self._preset.properties()
          filetype = presetproperties["file_type"]
          if "deleteaudiofile" in presetproperties[filetype]:
            self._deleteAudioOnFinished = presetproperties[filetype]["deleteaudiofile"]

      # Add Write node to the script
      script.addNode(writeNode)

      rootNode.setKnob(nuke.RootNode.kTimelineWriteNodeKnobName, writeNode.knob("name"))


  # And finally, write out the script (next to the output files).
  def writeScript (self):
    self._script.writeToDisk(self._scriptfile)

  def taskStep(self):
    # Call taskStep on our render task
    if self._renderTask:
      result = self._renderTask.taskStep()
      if self._renderTask.error():
        self.setError(self._renderTask.error())
      return result
    else:
      return False

  def forcedAbort(self):
    if self._renderTask:
      self._renderTask.forcedAbort()
    self.cleanupAudio()

  def progress(self):
    if self._renderTask:
      progress = self._renderTask.progress()
      if self._renderTask.error():
        self.setError(self._renderTask.error())
      return progress
    elif self._finished:
      return 1.0
    else:
      return 0.0


  def outputHandles ( self, ignoreRetimes = True):
    """ Override which does nothing except changing the default value of
    ignoreRetimes from False to True.  This is not good, but the code calling
    this method is currently depending on it.
    """
    return super(TranscodeExporter, self).outputHandles(ignoreRetimes)


  def outputRange(self, ignoreHandles=False, ignoreRetimes=True, clampToSource=True):
    """outputRange(self)
    Returns the output file range (as tuple) for this task, if applicable"""
    start = 0
    end  = 0
    if isinstance(self._item, (hiero.core.TrackItem, hiero.core.Clip)):
      # Get input frame range
      
      ignoreRetimes = self._preset.properties()["method"] != "None"
      start, end = self.inputRange(ignoreHandles=ignoreHandles, ignoreRetimes=ignoreRetimes, clampToSource=clampToSource)

      if self._retime and isinstance(self._item, hiero.core.TrackItem) and ignoreRetimes:
        srcDuration = abs(self._item.sourceDuration())
        playbackSpeed = abs(self._item.playbackSpeed())
        # If the clip is a freeze frame, then playbackSpeed will be 0.  Handle the resulting divide-by-zero error and set output range to duration
        # of the clip.
        try:
          end = (end - srcDuration) + (srcDuration / playbackSpeed) + (playbackSpeed - 1.0)
        except:
          end = start + self._item.duration() - 1
        
      start = int(math.floor(start))
      end = int(math.ceil(end))


      # If the item is a TrackItem, and the task is configured to output to sequence time,
      # map the start and end into sequence time.
      if self.outputSequenceTime() and isinstance(self._item, hiero.core.TrackItem):
        offset = self._item.timelineIn() - int(self._item.sourceIn() + self._item.source().sourceIn())
        start = max(0, start + offset)
        end = end + offset

      # Offset by custom start time
      elif self._startFrame is not None:
        end = self._startFrame + (end - start)
        start = self._startFrame

    elif isinstance(self._item, hiero.core.Sequence):
      start, end = 0, self._item.duration() - 1

      try:
        start = self._item.inTime()
      except RuntimeError:
        # This is fine, no in time set
        pass

      try:
        end = self._item.outTime()
      except RuntimeError:
        # This is fine, no out time set
        pass

    return (start, end)

class TranscodePreset(hiero.core.RenderTaskPreset):
  def __init__(self, name, properties):
    hiero.core.RenderTaskPreset.__init__(self, TranscodeExporter, name, properties)

    # Set any preset defaults here
    self.properties()["keepNukeScript"] = False
    self.properties()["burninDataEnabled"] = False
    self.properties()["burninData"] = dict((datadict["knobName"], None) for datadict in FnExternalRender.NukeRenderTask.burninPropertyData)
    self.properties()["additionalNodesEnabled"] = False
    self.properties()["additionalNodesData"] = []
    self.properties()["method"] = "Blend"

    # Give the Write node a name, so it can be referenced elsewhere
    if "writeNodeName" not in self.properties():
      self.properties()["writeNodeName"] = "Write_{ext}"

    self.properties().update(properties)

  def supportedItems(self):
    return hiero.core.TaskPresetBase.kAllItems

hiero.core.taskRegistry.registerTask(TranscodePreset, TranscodeExporter)
