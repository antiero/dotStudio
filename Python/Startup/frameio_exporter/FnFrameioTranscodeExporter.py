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

from hiero.exporters import FnTranscodeExporter, FnTranscodeExporterUI

from hiero.exporters.FnTranscodeExporter import TranscodeExporter, TranscodePreset
from hiero.exporters.FnExternalRender import NukeRenderTask

from FnFrameioUI import gIconPath

class FrameioTranscodeExporter(FnTranscodeExporter.TranscodeExporter):
  def __init__(self, initDict):
    """Sub-class Transcode Exporter to handle uploading of files to Frame.io services"""
    FnTranscodeExporter.TranscodeExporter.__init__( self, initDict )


  def startTask(self):   
    # Call parent startTask
    FnTranscodeExporter.TranscodeExporter.startTask(self)    

  def updateItem (self, originalItem, localtime):
    """updateItem - This is called by the processor prior to taskStart, crucially on the main thread.\n
      This gives the task an opportunity to modify the original item on the main thread, rather than the clone."""

    print "updateItem called"

    timestamp = self.timeStampString(localtime)
    tagName = str("Transcode {0} {1}").format(self._preset.properties()["file_type"], timestamp)
    tag = hiero.core.Tag(tagName, os.path.join(gIconPath, "logo-connected.png"))

    tag.metadata().setValue("tag.pathtemplate", self._exportPath)
    tag.metadata().setValue("tag.description", "Frame.io Upload " + self._preset.properties()["file_type"])

    tag.metadata().setValue("tag.frameioRefernceID", "Frame.io - filereferenceid")

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

    tag.metadata().setValue("tag.frameio_upload_time", str(timestamp))

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

  def finishTask (self):  
    FnTranscodeExporter.TranscodeExporter.finishTask(self)

  def taskStep(self):
    # The parent implimentation of taskstep
    #  - Calls self.writeScript() which writes the script to the path in self._scriptfile
    #  - Executes script in Nuke with either HieroNuke or local Nuke as defined in preferences
    #  - Parses the output ever frame until complete
    
    return FnTranscodeExporter.TranscodeExporter.taskStep(self)

  def forcedAbort (self):
    # Parent impliementation terminates nuke process
    FnTranscodeExporter.TranscodeExporter.forcedAbort(self)    
    return

  def progress(self):
    # Parent implimentation returns a float between 0.0-1.0 representing progress
    # Progress is monitored by parsing frame progress in stdout from Nuke 
    
    # Ensure return type is float or shiboken will throw an error
    return float(FnTranscodeExporter.TranscodeExporter.progress(self))


class FrameioTranscodePreset(FnTranscodeExporter.TranscodePreset):
  def __init__(self, name, properties):
    FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
    self._parentType = FrameioTranscodeExporter

    # Set any preset defaults here
    self.properties()["keepNukeScript"] = False
    self.properties()["burninDataEnabled"] = False
    self.properties()["burninData"] = dict((datadict["knobName"], None) for datadict in NukeRenderTask.burninPropertyData)
    self.properties()["additionalNodesEnabled"] = False
    self.properties()["additionalNodesData"] = []
    self.properties()["method"] = "Blend"
    self.properties()["file_type"] = "mov"

    # Give the Write node a name, so it can be referenced elsewhere
    if "writeNodeName" not in self.properties():
      self.properties()["writeNodeName"] = "Write_{ext}"

    self.properties().update(properties)

  def supportedItems(self):
    return hiero.core.TaskPresetBase.kAllItems


  def supportedItems(self):
    return hiero.core.TaskPresetBase.kSequence

hiero.core.taskRegistry.registerTask(FrameioTranscodePreset, FrameioTranscodeExporter)
