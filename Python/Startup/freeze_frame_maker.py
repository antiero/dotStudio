### FreezeFrameMaker.py  - A Freeze Frame Maker which extends the basic 'Make Freeze Frame' functionality
# Antony Nasce - v1.0 28/07/13
# Produces Freeze frames at current, first, middle or last frame from Timeline or Viewer
# Usage: Copy this file to: ~/.hiero/Python/StartupUI
# Right-click in Viewer or Timeline View, or use Ctrl/Cmd+[0,1,2,3] hotkeys.
# New Still Clips are added to a 'Stills' Bin at the root of the Project
# New Still TrackItems are added at the first available Track above the source TrackItem
# 'First', 'Middle' and 'Last' frame actions work on multiple shot selections in the Timeline View.
# Requires Hiero 1.7v2 or later.

import hiero.core
import hiero.ui
from hiero.ui import findMenuAction, insertMenuAction, createMenuAction
from PySide.QtGui import *

##### Helper Methods #####
def visibleShotAtTime(sequence, t):
  """visibleShotAtTime(sequence, t) -> Returns the visible TrackItem in a Sequence (sequence) at a specified frame (t)."""
  shot = sequence.trackItemAt(t)
  if shot == None:
    return shot
    
  elif shot.isMediaPresent() and shot.isEnabled():
    return shot
  
  else:
    # If we're here, the Media is offline or disabled... work out what's visible on other tracks...
    badTrack = shot.parent()
    vTracks = list(sequence.videoTracks())
    vTracks.remove(badTrack)
    for track in reversed(vTracks):
      trackItems = track.items()
      for shotCandidate in trackItems:
        if shotCandidate.timelineIn() <= t and shotCandidate.timelineOut() >= time:
          if shotCandidate.isMediaPresent() and shotCandidate.isEnabled():
            shot = shotCandidate
            break
  
  return shot

def trackAboveTrackItemHasCollision(trackItem):
  """This returns True if the TrackItem in the Track above 'trackItem' overlaps in time, False otherwise"""
  track = trackItem.parent()
  sequence = track.parent()
  trackBelowIndex = track.trackIndex()
  numVideoTracks = len(sequence.videoTracks())
  # Check if Track exists above first...
  if trackBelowIndex == numVideoTracks-1:
    return False
  else:
    trackAbove = sequence[trackBelowIndex+1]
    tIn = trackItem.timelineIn()
    tOut = trackItem.timelineOut()
    for t in range(tIn,tOut):
      # We scan the frames between the in and out points. If any other TrackItems exist in this range, there's a conflict
      if sequence.trackItemAt(t) != trackItem:
        return True
    return False  

def mapRetime(ti, timelineTime):
  """Maps the trackItem source in time to timeline in time, handling any retimes"""
  return ti.sourceIn() + int((timelineTime - ti.timelineIn()) * ti.playbackSpeed())

def getFreezeFrameInfoFromTrackItemAtTime(trackItem,T):
  """This does the convoluted magic to get the necessaries to produce a Still from a TrackItem at time T"""
  # File Source
  clip = trackItem.source()
  file_knob = clip.mediaSource().fileinfos()[0].filename()
  first_last_frame = int(mapRetime(trackItem,T)+clip.sourceIn())
  return file_knob, first_last_frame, trackItem

def titleStringTriggeredAction(title, method, icon = None, shortcut = None):
  """This is a magic convenience method for returning a QActions with a triggered method based on the title string"""
  action = QAction(title,None)
  action.setIcon(QIcon(icon))
  action.setShortcut(shortcut)
  
  # We do this magic, so that the title string from the action drives what kind of still frame position is made
  def methodWrapper():
    method(title)
  
  action.triggered.connect( methodWrapper )
  return action

# Freeze Frame Maker Class for Menu and actions
class FreezeFrameMaker:

  """This Class creates 4 menu actions for adding Still frames from Clips and Shots"""
  # This constants drive the menu actions
  kFirstFrame = "First frame"
  kMiddleFrame = "Middle frame"
  kLastFrame = "Last frame"
  kCurrentFrame = "Current frame"
  
  def __init__(self):
      self._menu = QMenu("Freeze Frame")
      self._menu.setIcon(QIcon("icons:TagSnow.png"))

      # This viewer action is a special case. It drills down to what shot is currently visible, regardless of shot selection
      self._currentFrameAction  = createMenuAction(self.kCurrentFrame, self.addStillFromCurrentViewerFrame)
      self._currentFrameAction.setShortcut('Ctrl+0')

      # These are actions which you can access by selecting shots on the Timeline
      self._firstFrameAction = titleStringTriggeredAction(self.kFirstFrame, self.addStillForPosition,shortcut='Ctrl+1')
      self._middleFrameAction = titleStringTriggeredAction(self.kMiddleFrame, self.addStillForPosition,shortcut='Ctrl+2')
      self._lastFrameAction = titleStringTriggeredAction(self.kLastFrame, self.addStillForPosition,shortcut='Ctrl+3')
      
      # Add actions to the QMenu
      self._menu.addAction(self._currentFrameAction)    
      self._menu.addAction(self._firstFrameAction)
      self._menu.addAction(self._middleFrameAction)
      self._menu.addAction(self._lastFrameAction)

      # Register for Timeline View and Viewer right-click menus
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.timelineEventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kViewer", self.viewerEventHandler)


  def addStillClipToStillsBin(self,proj,clip, colourTransform):
    """This handles the addition of a Still Clip to the Stills Bin"""
    rt = proj.clipsBin()
    try:
      b = rt['Stills']
    except:
      b = rt.addItem(hiero.core.Bin('Stills'))
    bi = hiero.core.BinItem(clip)
    b.addItem(bi)

    # This is currently a necessary step because Colour Transforms cannot be set until the Clip is added to the Bin
    clip = bi.activeItem()
    clip.setSourceMediaColourTransform(colourTransform)
    return clip

  def addStillTrackItemToSequence(self,clip,trackItem):
    """This handles the addition of the Still TrackItem to the Sequence, avoiding collisions"""

    # Create a new TrackItem for the Still frame, from the clip, with timing from trackItem
    stillTrackItem = hiero.core.TrackItem(trackItem.name(),hiero.core.TrackItem.MediaType.kVideo)
    stillTrackItem.setSource(clip)
    stillTrackItem.setTimelineIn(trackItem.timelineIn())
    stillTrackItem.setTimelineOut(trackItem.timelineOut())

    sequence = trackItem.parent().parent()
    numVideoTracks  = len(sequence.videoTracks())

    trackAboveCollisionTest = trackAboveTrackItemHasCollision(trackItem)
    oldTrack = trackItem.parent()
    oldTrackIndex = oldTrack.trackIndex()

    # Add stillTrackItem to the Sequence, avoiding collisions
    if trackAboveCollisionTest or numVideoTracks-1 <= oldTrackIndex:
      newTrack = sequence.addTrack(hiero.core.VideoTrack(oldTrack.name()))
    else:
      newTrack = sequence.videoTracks()[oldTrackIndex+1]

    try:
      newTrack.addItem(stillTrackItem)
    except:
      # This case can happen if a TrackItem is disabled, trackItemAt does not detect collisions
      newTrack = sequence.addTrack(hiero.core.VideoTrack(oldTrack.name()))
      newTrack.addItem(stillTrackItem)
    sequence.editFinished()      

  def addStillFromCurrentViewerFrame(self):
    """Adds a Still Frame Clip and TrackItem, from the Current Viewer Frame"""
    # Current Time of the Current Viewer
    cv = hiero.ui.currentViewer()
    T = cv.time()
    sequence = cv.player().sequence()
    if not sequence:
      hiero.core.log.debug("No Clip/Sequence was found in the Current Viewer")
      return

    proj = sequence.project()

    # Handle the Case that it's just a Clip in the Viewer for making a Still Frame
    if isinstance(sequence,hiero.core.Clip):
      cTransform = sequence.sourceMediaColourTransform()
      currentFrame = int(sequence.mediaSource().startTime()) + int(T)
      clip = hiero.core.Clip(sequence.mediaSource().fileinfos()[0].filename(),currentFrame, currentFrame)
      # This adds the FreezeFrameClip to the Bin and returns it with the appropriate TrackItem colourTransform applied
      clip = self.addStillClipToStillsBin(proj,clip,clip.sourceMediaColourTransform())
      return

    elif isinstance(sequence,hiero.core.Sequence):

      # Check that Media is Online - we won't add a Tag to Offline Media
      currentShot = visibleShotAtTime(sequence,T)    

      if not currentShot:
        QMessageBox.warning(None, "Freeze Frame Maker", "Unable to make a Still Frame from the current frame.", QMessageBox.Ok)
        return
      else:
        fileKnob,currentFrame,trackItem = getFreezeFrameInfoFromTrackItemAtTime(currentShot,T)
        clip = hiero.core.Clip(hiero.core.MediaSource(fileKnob),currentFrame, currentFrame)

      colourTransform = trackItem.sourceMediaColourTransform()

      # This adds the FreezeFrameClip to the Bin and returns it with the appropriate TrackItem colourTransform applied
      clip = self.addStillClipToStillsBin(proj,clip,colourTransform)

      # Add the Still to the Sequence
      self.addStillTrackItemToSequence(clip,trackItem)

  def addStillForPosition(self, kPosition):
    """This is the main action called by the menu action, which creates the Still clip and adds it to the Sequence.
    The Still created is based on the kPosition type"""

    # If we're here, we're acting upon a TrackItem Selection in the Timeline
    view = hiero.ui.activeView()    
    selection = view.selection()
    if len(selection) == 0:
      return
    else:
      proj = selection[0].project()
      root = proj.clipsBin()
      trackItems = [item for item in selection if isinstance(item,hiero.core.TrackItem)]
      for trackItem in trackItems:

        if kPosition == self.kFirstFrame:
          FreezeFrame = trackItem.sourceIn()
        elif kPosition == self.kMiddleFrame:
          FreezeFrame = int((trackItem.sourceOut()-trackItem.sourceIn())/2)
        elif kPosition == self.kLastFrame:
          FreezeFrame = trackItem.sourceOut()

        # The Colour Transform of the TrackItem
        colourTransform = trackItem.sourceMediaColourTransform()

        # This is the (convoluted) magic to create a single Frame Clip in the Bin
        fileKnob,currentFrame,ti = getFreezeFrameInfoFromTrackItemAtTime(trackItem,FreezeFrame)

        # This is an adjustment for the Timeline time of the current TrackItem
        FreezeFrame = currentFrame+trackItem.timelineIn()

        # This creates a single Frame object
        FreezeFrameClip = hiero.core.Clip(hiero.core.MediaSource(fileKnob),FreezeFrame, FreezeFrame)

        # This adds the FreezeFrameClip to the Bin and returns it with the appropriate TrackItem colourTransform applied
        clip = self.addStillClipToStillsBin(proj,FreezeFrameClip,colourTransform)

        # Add the Still TrackItem to the Sequence, avoiding collisions
        self.addStillTrackItemToSequence(clip, trackItem)        

  ##### Context menu Handlers #####
  def timelineEventHandler(self,event):
    enableSelectionActions = True
    if len(event.sender.selection()) == 0:
      enableSelectionActions = False
    self._firstFrameAction.setEnabled(enableSelectionActions)
    self._middleFrameAction.setEnabled(enableSelectionActions)
    self._lastFrameAction.setEnabled(enableSelectionActions)
    self._currentFrameAction.setText(self.kCurrentFrame)
    insertMenuAction(self._menu.menuAction(), event.menu)

  def viewerEventHandler(self,event):
    act = self._currentFrameAction
    act.setText("Freeze current frame")
    event.menu.addAction(act)

act = FreezeFrameMaker()
menu = act._menu
# Add to Timeline Menu so that shortcuts work
hiero.ui.addMenuAction("foundry.menu.sequence",menu.menuAction())