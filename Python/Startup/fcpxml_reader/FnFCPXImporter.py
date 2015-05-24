from fcpxml_parser import fcpxml_wrapper
import hiero.ui
from hiero.core.events import registerInterest, unregisterInterest, EventType
import os

class FCPXImporter:
  def __init__(self):
    """A Final Cut Pro X importer for Nuke Studio"""
    self.__title = "A Final Cut Pro X importer for Nuke Studio"

    # This will be the fcpxml_wrapper wrapping the .fcpxml file
    self.wrapper = None    

  def _getSourceClipFromExistingAssetsBin(self, project, seqClip):
    """Returns a Clip object from the project with an asset_id"""
    clips = hiero.core.findItemsInProject(project, hiero.core.Clip)

    asset_id = seqClip.asset.id
    foundClip = None
    for clip in clips:
      clipTags = clip.tags()
      for tag in clipTags:
        tagMeta = tag.metadata()
        if tagMeta.hasKey('tag.fcpx.id'):
          tagID = tagMeta.value('tag.fcpx.id')
          if tagID == asset_id:
            foundClip = clip
            break

    asset = self.wrapper.getAssetByRefID(asset_id)
    return foundClip

  def _createSequence(self, sequenceWrapper, project):
    """Creates a hiero.core.Sequence from an fcpxml sequence_wrapper and adds it to the specified project"""
    sequenceName = sequenceWrapper.parentProject.name
    sequence = hiero.core.Sequence(sequenceName)
    sequence.setFramerate(sequenceWrapper.framerate)
    sequenceClips = sequenceWrapper.clips
    for seqClip in sequenceClips:
      #print "Sequence Clip:" + str(seqClip)
      if seqClip.asset:
        #print "Clip Asset:" + str(seqClip.asset)

        sourceClip = self._getSourceClipFromExistingAssetsBin(project, seqClip)
        if not sourceClip:
          print "Unable to find Clip for asset_id. Should return an empty Clip"
          sourceClip = hiero.core.Clip(seqClip.asset.filepath)

        #ti = hiero.core.TrackItem(seqClip.name, hiero.core.TrackItem.MediaType.kVideo)
        #ti.setSource(sourceClip)
        trackItems = sequence.addClip(sourceClip, seqClip.timeline_in, videoTrackIndex=seqClip.lane)

        # This method returns linked audio and video TrackItems potentially...
        for trackItem in trackItems:
          clip = trackItem.source()
          sourceClipStartTimecode = clip.timecodeStart()
          trackItem.setSourceIn(seqClip.start_frame - sourceClipStartTimecode)
          trackItem.setSourceOut(seqClip.end_frame - sourceClipStartTimecode)          
          trackItem.setTimelineIn(seqClip.timeline_in)
          trackItem.setTimelineOut(seqClip.timeline_out)

    return sequence

  def importFCPXMLFile(self, filepath, proj = None):
    """Imports the contents of an .fcpxml (sequences and clips) to a project (proj)

    @param: filepath - the full path to an .fcpxml file (Final Cut Pro X)
    @param: proj (optional) - a hiero.core.Project File to import to.
    @return: the imported hiero.core.Sequence(s)

    """
    if not proj:
      proj = hiero.core.newProject()

    root = proj.clipsBin()
    assetsBin = hiero.core.Bin("assets")
    root.addItem(assetsBin)
    sequencesBin = hiero.core.Bin("sequences")
    root.addItem(sequencesBin)

    # Read this sequence file into the fcpxml_wrapper 
    self.wrapper = fcpxml_wrapper(filepath)
    clipAssets = self.wrapper.assets
    for asset in clipAssets:
      C = hiero.core.Clip(asset.filepath)
      # Create a Tag with the FCP data
      T = hiero.core.Tag("fcpxml")
      tagMeta = T.metadata()
      tagMeta.setValue("tag.fcpx.id", asset.id)
      tagMeta.setValue("tag.fcpx.audio_channels", str(asset.audio_channels))
      tagMeta.setValue("tag.fcpx.audio_rate", str(asset.audio_rate))
      tagMeta.setValue("tag.fcpx.audio_sources", str(asset.audio_sources))
      tagMeta.setValue("tag.fcpx.duration", str(asset.duration))
      tagMeta.setValue("tag.fcpx.start_frame", str(asset.start_frame))
      tagMeta.setValue("tag.fcpx.end_frame", str(asset.end_frame))
      tagMeta.setValue("tag.fcpx.has_video", str(asset.has_video))
      tagMeta.setValue("tag.fcpx.has_audio", str(asset.has_audio))
      tagMeta.setValue("tag.fcpx.name", str(asset.name))
      tagMeta.setValue("tag.fcpx.format", str(asset.format))
      tagMeta.setValue("tag.fcpx.filepath", str(asset.filepath))
      tagMeta.setValue("tag.fcpx.uid", str(asset.uid))
      C.addTag(T)
      assetsBin.addItem(hiero.core.BinItem(C))

    projects = self.wrapper.projects
    for project in projects:
      sequences = project.sequences
      for sequence in sequences:
        newSequence = self._createSequence(sequence, proj)
        sequencesBin.addItem(hiero.core.BinItem(newSequence))  

### Handle the dropping of an .fcpxml file into the Bin View
class BinViewDropHandler:
  kTextMimeType = "text/plain"
  
  def __init__(self):
    # hiero doesn't deal with drag and drop for text/plain data, so tell it to allow it
    hiero.ui.registerBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)
    
    # register interest in the drop event now
    registerInterest((EventType.kDrop, EventType.kBin), self.dropHandler)
    self.importer = FCPXImporter()

  def isSequenceFile(self, f, extension = '.fcpxml'):
    return f.lower().endswith( extension )    

  def dropHandler(self, event):
    
    # get the mime data
    #print "mimeData: ", dir(event.mimeData)
    urls = [url.toLocalFile() for url in event.mimeData.urls()]

    # Build a list of possible XML/EDL files
    sequenceFiles = []
    for url in urls:
      if os.path.isdir(url):
        for root, dirs, files in os.walk(url):
          FILES = [os.path.join(root, file) for file in files]
          for f in FILES: 
            if self.isSequenceFile(f):
              sequenceFiles+=[f]    

      elif self.isSequenceFile(url):
        sequenceFiles+=[url]

    if len(sequenceFiles)==0:
      return

    # Now we should have a list of Sequences. We should now import them
    # We should really detect if the drop event was received by an item in the tree or not...

    # figure out which item it was dropped onto
    receiver = event.dropItem
    if hasattr(receiver, 'project'):
      proj = receiver.project()
    else:
      proj = hiero.core.projects()[-1]

    # And finally catch the case where no projects might exist...
    if not proj:
      proj = hiero.core.newProject()

    for fcpxmlFile in sequenceFiles:
      self.importer.importFCPXMLFile(fcpxmlFile, proj)

  def unregister(self):
    unregisterInterest((EventType.kDrop, EventType.kBin), self.dropHandler)
    hiero.ui.unregisterBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)

# Instantiate the handler to get it to register itself.
dropHandler = BinViewDropHandler()
importer = FCPXImporter()
hiero.core.importFCPXFile = importer.importFCPXMLFile