# GrabStill.py - Adds a right-click menu action for creating still frame clips from the active Viewer frame
# To install, copy to ~/.hiero/Python/Startup/ or ~/.nuke/Python/Startup/ for Nuke Studio.

import hiero.core
import hiero.ui
import os.path
from PySide2 import QtWidgets
import tempfile

def mapRetime(ti, timelineTime):
  return ti.sourceIn() + int((timelineTime - ti.timelineIn()) * ti.playbackSpeed())

# Method to return the visible TrackItem in the Current Viewer for a Sequence, seq, used for Tagging Shots in the Viewer
def visibleShotAtTime(seq,time):
  shot = seq.trackItemAt(time)
  if shot == None:
    return shot
    
  elif shot.isMediaPresent() and shot.isEnabled():
    return shot

def getFrameInfoFromTrackItemAtTime(trackItem,T):
  
  # File Source
  clip = trackItem.source()
  file_knob = clip.mediaSource().fileinfos()[0].filename()

  clip = trackItem.source()

  first_last_frame = int(mapRetime(trackItem,T)+clip.sourceIn())
  return file_knob, first_last_frame, trackItem

class GrabThisFrameAction(QtWidgets.QAction):

  def __init__(self):
      QtWidgets.QAction.__init__(self, "Grab still frame Clip", None)
      self.triggered.connect(self.createStillFromCurrentViewerFrame)
      hiero.core.events.registerInterest("kShowContextMenu/kViewer", self.eventHandler)

  def createStillFromCurrentViewerFrame(self):
  
    currentShot = []
          
    # Current Time of the Current Viewer
    T = self.currentViewer.time()
    if self.currentClipSequence == None:
      return
    else:
      sequence = self.currentClipSequence.binItem().activeItem()
      if isinstance(sequence,hiero.core.Clip):
        clip = hiero.core.Clip(sequence.mediaSource().fileinfos()[0].filename(),T, T)
      elif isinstance(sequence,hiero.core.Sequence):
        
        # Check that Media is Online - we won't add a Tag to Offline Media
        currentShot = visibleShotAtTime(sequence,T)
        if not currentShot:
          QtWidgets.QMessageBox.warning(None, "Grab Frame", "Unable to Grab a Still Frame.", QtWidgets.QMessageBox.Ok)
          return
        else:
          fileKnob,first_last_frame,trackItem = getFrameInfoFromTrackItemAtTime(currentShot,T)
          clip = hiero.core.Clip(hiero.core.MediaSource(fileKnob),first_last_frame, first_last_frame)
          
      # Create a 'Stills' Bin, and add the Still Frame as a new Clip
      proj = self.currentClipSequence.project()
      rt = proj.clipsBin()
      try:
        b = rt['Stills']
      except:
        b = rt.addItem(hiero.core.Bin('Stills'))
      
      try:
        bi = hiero.core.BinItem(clip)
        clip.setName(bi.name()+'_still')
        b.addItem(bi)
      except Exception as e:
        print("Unable to create Still frame: %s" % str(e))

  def eventHandler(self, event):
    self.currentClipSequence = None
    self.currentViewer = None
    self.currentPlayer = None
    
    self.currentViewer = event.sender
    self.currentPlayer = self.currentViewer.player()
    self.currentClipSequence = self.currentPlayer.sequence()
    if not self.currentClipSequence:
      return
    else:
      title = "Grab still frame Clip"
      self.setText(title)
      event.menu.addAction( self )

# Instantiate the action to get it to register itself.
GrabThisFrameAction = GrabThisFrameAction()