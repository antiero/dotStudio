import os.path
import os
import sys
import shutil
import re


import hiero.core
from hiero.exporters import FnFrameExporter

class FrameioUploadExporter(FnFrameExporter.FrameExporter):
  def __init__( self, initDict ):
    """Initialize"""
    FnFrameExporter.FrameExporter.__init__( self, initDict )
    if self.nothingToDo():
      return

  def _tryCopy(self, src, dst):
    """Attempts to copy src file to dst, including the permission bits, last access time, last modification time, and flags"""

    hiero.core.log.info("Attempting to copy %s to %s" % (src, dst))
    
    try:
      shutil.copy2(src, dst)
    except shutil.Error, e:
      # Dont need to report this as an error
      if e.message.endswith("are the same file"):
        pass
      else:
        self.setError("Unable to copy file. %s" % e.message)

  def doFrame(self, src, dst):
    hiero.core.log.info( "CopyExporter:" )
    hiero.core.log.info( "  - source: " + str(src) )
    hiero.core.log.info( "  - destination: " + str(dst) )

    # Find the base destination directory, if it doesn't exist create it
    dstdir = os.path.dirname(dst)
    if not os.path.exists(dstdir):
      hiero.core.log.info( "make dirs:" + dstdir )
      os.makedirs(dstdir)

    # Hiero treats split RED Clips in a special way. Clips with clip_001.R3D, clip_002.R3D are imported as a single Clip.
    # For the Copy Exporter this means that only the first Clip will be exported, so we must deal with this case.
    if src.lower().endswith(".r3d"):
      hiero.core.log.info("Handling a R3D file...")
      
      # Get the MediaSource for the current Item - we use this to conveniently get the filenameHead for searching purposes
      item = self._item
      
      if isinstance(item,hiero.core.Clip):
        clipMediaSource = item.mediaSource()
      elif isinstance(item,hiero.core.TrackItem):
        clipMediaSource = item.source().mediaSource()
        
      clipHead = clipMediaSource.filenameHead()
      clipRootDir = os.path.dirname(src)

      r3dSequenceMatches = []
      
      for filename in os.listdir(clipRootDir):
        r3dSequenceMatch = re.search(r'%s\_\d+.r3d' % clipHead, filename, re.IGNORECASE)
        
        # If we found a sequence of R3D files, we must copy each individually...
        if r3dSequenceMatch:
          r3dClipName = r3dSequenceMatch.group(0)
          hiero.core.log.info("Got split R3D Clip %s for Copy operation" % (r3dClipName))
          r3dSequenceMatches+=[r3dClipName]

      # If we didn't find any sequentially named files, just copy the single R3D Clip as normal
      if len(r3dSequenceMatches) <= 0:
        self._tryCopy(src, dst)
      
      else:
        for clipNameMatch in r3dSequenceMatches:
          clipPath = os.path.join(clipRootDir, clipNameMatch)
        
          # Update the source Clip path
          newSrc = clipPath

          # We must update the dst path, because this is inherently just the Clip Name, without the _# extension
          newDst = os.path.join(dstdir, clipNameMatch)
        
          self._tryCopy(newSrc, newDst)

    # If it was not an .r3d Clip, just do the copy operation as normal
    else:
      # Copy file including the permission bits, last access time, last modification time, and flags
      self._tryCopy(src, dst)
   
  def taskStep(self):
    # If this is a single file (eg r3d or mov) then we don't need to do every frame.

    if not hiero.core.frameioDelegate.frameioSession.sessionAuthenticated:
      self.setError("Frame.io session has not been authenticated! Please enter username and password")
      return

    ret = FnFrameExporter.FrameExporter.taskStep(self)
    return ret and not self._singleFile

class FrameioUploadPreset(hiero.core.TaskPresetBase):
  def __init__(self, name, properties):
    hiero.core.TaskPresetBase.__init__(self, FrameioUploadExporter, name)
    # Set any preset defaults here

    # This bool will determine whether the user wants to upload source files or transcode them
    self.properties()["frameioUploadSourceFiles"] = True
    
    # Update preset with loaded data
    self.properties().update(properties)

  def supportedItems(self):
    return hiero.core.TaskPresetBase.kSequence | hiero.core.TaskPresetBase.kClip


hiero.core.taskRegistry.registerTask(FrameioUploadPreset, FrameioUploadExporter)
