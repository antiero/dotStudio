# split_clip - an action which operates on Clips in the Bin View and Splits Clips which may be split, into proper Split Clips
# Usage:
# Copy split_clip.py to your <HIERO_PLUGIN_PATH>/Python/Startup dir
# Right-click on Clips in the Bin that should be Split > Split Clip
# Result: You should have new Split Clips in the Bin.
import hiero.core
from PySide.QtGui import *
import os, re

#### Clip Helper Methods ####
def getClipSelection(selection):
  """Convenience for returning a list of Clips from a selection"""
  clipItems = [item.activeItem() for item in selection if hasattr(item,'activeItem') and isinstance(item.activeItem(),hiero.core.Clip)]
  return clipItems

def clipInstancesInProject(testClip):
  """This is a method which returns the number of times a Clip exists in a Project.
  Notes: a Clip instance is considered a strict match with testClip if its MediaSource, Start Timecode, Duration and Colour Transform are identical"""
  proj = testClip.project()
  clipsInProject = hiero.core.findItemsInProject(proj, hiero.core.Clip)

  def clipAttrs(_clip):
    return (_clip.mediaSource(), _clip.timecodeStart(), _clip.duration(), _clip.sourceMediaColourTransform())

  testClipAttrs = clipAttrs(testClip)

  occurances = 0

  for clip in clipsInProject:
    if clipAttrs(clip) == testClipAttrs:
      occurances+=1
  
  return occurances

#### Split Clip Main Action ####
class SplitClipAction(QAction):

  def __init__(self):
      QAction.__init__(self, "Split Clip", None)
      self.triggered.connect(self.splitClipSelection)
      hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)

  def splitClipSelection(self):
    selection = hiero.ui.activeView().selection()

    clipSelection = getClipSelection(selection)
    if len(clipSelection)<=0:
      return

    # Now for each Clip, split it into separate Clips
    for clip in clipSelection:
      self.splitClip(clip)

  def splitClip(self, clip, deleteOriginal = False):
    """Takes a Clip which may be a split sequence and splits it into it new sub-clip Clips
    Note: Set 'deleteOriginal' to True if you want to delete the original Clip"""
    mediaSource = clip.mediaSource()
    if mediaSource.singleFile():
      print 'Clip input is not an image sequence and cannot be split'
      return None

    fileName = mediaSource.fileinfos()[0].filename()
    frameHead = mediaSource.filenameHead()
    frameDir = fileName.split(frameHead)[0]

    splitSeqs = [] 
    seqListCandidates = hiero.core.filenameList(frameDir, splitSequences = True, returnHiddenFiles = False)
    for seq in seqListCandidates:
      if frameHead in seq:
        splitSeqs+=[os.path.join(frameDir,seq)]

    # Now we do the splitting of the Clip
    clipBinRoot = clip.binItem().parentBin()
    proj = clip.project()
    with proj.beginUndo('Split Bin Clip'):
      for source in splitSeqs:
        # Detect the path frame padding form (%0#d) of the filename from the MediaSource
        M = hiero.core.MediaSource(source)
        filePathPadded = M.toString().split('Source:')[-1].split()[0]

        _first = None
        _last = None
        # Check for first-last extension...
        flCheck = re.findall('\d+\-\d+',source.split()[-1])
        if len(flCheck)==1:
          _first = int(flCheck[0].split('-')[0])
          _last = int(flCheck[0].split('-')[1])
        else:
          # It should be a single frame, with no 'first-last' in the media source path
          frame = re.findall(r'\b\d+\b', source)
          print 'FRAME IS ' + str(frame)
          if len(frame)>=1:
            # We may have found a funny file name which starts with a number and later has a frame number. We assume the last occuring number is the frame.
            frame = frame[-1]

            # Now ensure this value can be strictly cast as a valid integer
            try:
              _first = int(frame)
              _last = _first
            except ValueError:
              print 'Frame numbering for %s was ambiguous and frame value not be not be detected for still frame.' % source
              return

        clip = hiero.core.Clip(filePathPadded, _first, _last)
        clip.setInTime(_first)
        clip.setOutTime(_last)

        # Only add this new Clip if an identical Clip cannot be found in the Project
        if clipInstancesInProject(clip)==0:
          print 'Adding new sub-Clip for %s, first=%d, last=%d' % (filePathPadded, _first,_last)
          clipBinRoot.addItem(hiero.core.BinItem(clip))

    if deleteOriginal:
      clipBinRoot = c.binItem().parentBin()
      with proj.beginUndo('Delete Original Clip'):
        clipBinRoot.removeItem(clip.binItem())

  def eventHandler(self, event):
    if not hasattr(event.sender, 'selection'):
      return

    # Disable if nothing is selected
    selection = event.sender.selection()

    if selection is None:
      return

    clips = getClipSelection(selection)

    self.setEnabled( len(clips) >= 1 )
    event.menu.addAction(self)

splitClipBinAction = SplitClipAction()