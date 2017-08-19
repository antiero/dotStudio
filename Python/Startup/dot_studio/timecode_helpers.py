# Timecode Helper Functions - WIP
# These methods add some helpers to work with Timecodes, added to the Spreadsheet and Timeline
import hiero.core
from hiero.ui import createMenuAction, insertMenuAction
from PySide2 import QtGui, QtCore

hiero.core.shotClipboard = []

class TrackItemTCObject(object):
  def __init__(self, shot):
    """A convenient object for obtaining the timecode info as a string"""
    self.item = shot
    self.timecode = hiero.core.Timecode
    self.updateSequence()

    if self.dropFrame:
      self._timecodeDisplayMode = self.timecode.kDisplayDropFrameTimecode
    else:
      self._timecodeDisplayMode = self.timecode.kDisplayTimecode    

  def updateSequence(self):
    """Called prior to each timecode request, in case parent Sequence has changed"""
    self.sequence = self.item.parentSequence()
    self.dropFrame = self.sequence.dropFrame()
    self.fps = self.sequence.framerate()

  def srcIn(self):
    self.updateSequence()
    self.frameSrcIn = self.item.sourceIn()
    if self._timecodeDisplayMode == hiero.core.Timecode.kDisplayFrames:
      return self.frameSrcIn
    else:
      return self.timecode.timeToString(self.frameSrcIn, self.fps, self.timecodeDisplayMode())

  def srcOut(self):
    self.updateSequence()
    self.frameSrcOut = self.item.sourceOut()
    if self._timecodeDisplayMode == hiero.core.Timecode.kDisplayFrames:
      return self.frameSrcOut
    else:
      return self.timecode.timeToString(self.frameSrcOut, self.fps, self.timecodeDisplayMode())

  def dstIn(self):
    self.updateSequence()
    self.frameDstIn = self.sequence.timecodeStart() + self.item.timelineIn()
    if self._timecodeDisplayMode == hiero.core.Timecode.kDisplayFrames:
      return self.frameDstIn
    else:
      return self.timecode.timeToString(self.frameDstIn, self.fps, self.timecodeDisplayMode())

  def dstOut(self):
    self.updateSequence()
    self.frameDstOut = self.sequence.timecodeStart() + self.item.timelineOut()
    if self._timecodeDisplayMode == hiero.core.Timecode.kDisplayFrames:
      return self.frameDstOut
    else:
      return self.timecode.timeToString(self.frameDstOut, self.fps, self.timecodeDisplayMode())

  def timecodeDisplayMode(self):
    """Returns the mode of hiero.core.Timecode for this object.
    Options are kDisplayTimecode, kDisplayFrames, kDisplayDropFrameTimecode.
    Note: by default if a parentSequence uses drop Frame, the timecode will automatically be kDisplayDropFrameTimecode
    """    
    return self._timecodeDisplayMode

  def setTimecodeDisplayMode(self, mode):
    """Returns the mode of hiero.core.Timecode for this object.
    Options are kDisplayTimecode, kDisplayFrames, kDisplayDropFrameTimecode.
    Note: by default if a parentSequence uses drop Frame, the timecode will automatically be kDisplayDropFrameTimecode
    Returns True if mode supplied was valid, False otherwise
    """
    if mode not in (hiero.core.Timecode.kDisplayTimecode, hiero.core.Timecode.kDisplayTimecode, hiero.core.Timecode.kDisplayFrames):
      print "Please supply a valid Timecode display mode (kDisplayTimecode, kDisplayFrames, kDisplayDropFrameTimecode)"
      return False

    self._timecodeDisplayMode = mode
    return True

  def __str__(self):
    """A string describing this Shot TC"""
    self.updateSequence()
    return "Shot: %s, Clip In: %s, Clip Out: %s, Timeline In: %s, Timeline Out: %s" % (self.item.name(), self.srcIn(), self.srcOut(), self.dstIn(), self.dstOut())

class PasteShotInfoDialog(QtWidgets.QDialog):
  # A dialog which allows the user to choose Shot info to apply to a selection of shots"""
  def __init__(self, selection=None,parent=None):
    super(PasteShotInfoDialog, self).__init__(parent)
    self.setWindowTitle("Select what to paste")
    self.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed )

    # Make double sure our destination items are a list of shots and that they exist on Tracks which are not locked
    self._destinationShots = selection
    self._currentCopiedShot = self.getCopiedShot()
    if not self._currentCopiedShot:
      return 

    self.setupDialogUI()

  def setupDialogUI(self):
    """This is called when dialog is exec'd.
    will populate the Dialog with the timecode object stored in hiero.core.shotClipboard
    """
    # We'll display the Copied Shot info in the dialog

    if not self._currentCopiedShot:
      return

    self.layout = QtWidgets.QFormLayout()
    tcShot = TrackItemTCObject(self._currentCopiedShot)
    self.setWindowTitle("Paste from: %s" % str(self._currentCopiedShot.name()))
    tcString = tcShot.__str__()

    self._clipboardTCInfoLabel = QtWidgets.QLabel("Select which timecode to Paste:")
    self.layout.addRow("", self._clipboardTCInfoLabel)

    # There are 4 options: srcIn, srcOut, dstIn, dstOut
    self._srcInCheckBox = QtGui.QCheckBox("Source In (%s)" % str(tcShot.srcIn()))
    self._srcInCheckBox.setChecked(False)
    self.layout.addRow("", self._srcInCheckBox)

    self._srcOutCheckBox = QtGui.QCheckBox("Source Out (%s)" % str(tcShot.srcOut()))
    self._srcOutCheckBox.setChecked(False)
    self.layout.addRow("", self._srcOutCheckBox)

    self._dstInCheckBox = QtGui.QCheckBox("Timeline In (%s)" % str(tcShot.dstIn()))
    self._dstInCheckBox.setChecked(False)
    self.layout.addRow("", self._dstInCheckBox)

    self._dstOutCheckBox = QtGui.QCheckBox("Timeline Out (%s)" % str(tcShot.dstOut()))
    self._dstOutCheckBox.setChecked(False)
    self.layout.addRow("", self._dstOutCheckBox)

    # Standard buttons for Add/Cancel
    self._buttonbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

    if len(self._destinationShots) == 1:
      self._buttonbox.button(QtWidgets.QDialogButtonBox.Ok).setText("Paste")

    if len(self._destinationShots) > 1:
      numDestShots = len(self._destinationShots)
      self._buttonbox.button(QtWidgets.QDialogButtonBox.Ok).setText("Paste to %i shots" % numDestShots)
    
    self._buttonbox.button(QtWidgets.QDialogButtonBox.Ok).setToolTip(str(self._destinationShots))
    self._buttonbox.accepted.connect(self.accept)
    self._buttonbox.rejected.connect(self.reject)
    self.layout.addRow("",self._buttonbox)

    self.setLayout(self.layout)

  def getCopiedShot(self):
    """Just returns the shot stored in hiero.core.shotClipboard, None if multiple shots exist"""
    print "getCopiedShot: hiero.core.shotClipboard is %s" % str(hiero.core.shotClipboard)
    if len(hiero.core.shotClipboard) != 1:
      return None
    else:
      return hiero.core.shotClipboard[0]

# Menu which adds a Tags Menu to the Viewer, Project Bin and Timeline/Spreadsheet
class TimecodeMenu:

  def __init__(self):
      self._timecodeMenu = QtGui.QMenu("Timecode")

      # These actions in the viewer are a special case, because they drill down in to what is currrenly being
      self._copyTCAction = createMenuAction("Copy TC", self.copyTC)
      self._pasteTCAction = createMenuAction("Paste TC", self.pasteTC)
      self._pasteTCSpecialAction = createMenuAction("Paste TC Special...", self.pasteTCSpecial)
      self._setSrcInToFirstFrameOfClipAction = createMenuAction("Set srcIn to 1st frame of Clip", self.setSrcInToFirstFrameOfClip)
      self._resetOriginalTCAction = createMenuAction("Set srcIn to Original EDL TC", self.resetTC)

      self._timecodeMenu.addAction(self._copyTCAction)
      self._timecodeMenu.addAction(self._pasteTCAction)
      self._timecodeMenu.addAction(self._pasteTCSpecialAction)
      self._timecodeMenu.addAction(self._setSrcInToFirstFrameOfClipAction)
      self._timecodeMenu.addAction(self._resetOriginalTCAction)      

      hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)

  def resetTC(self):
    """'Copies' the shot selection to the 'Clipboard', storing it in hiero.core.shotClipboard"""
    # TO-DO Reset the TC from the edl metadata if it exists.
    view = hiero.ui.activeView()
    if not view:
      return
    
    selection = view.selection()    
    shotSelection = self.getShotSelectionForActiveView()
    for shot in shotSelection:
      M = shot.metadata()
      if M.hasKey('foundry.edl.srcIn'):
        originalSrcIn = int(M.value('foundry.edl.srcIn'))
        sourceClip = shot.source()
        clipSourceIn = originalSrcIn - sourceClip.timecodeStart()
        shot.setSourceIn(clipSourceIn)
        shot.setSourceOut(clipSourceIn + (shot.duration()-1))

        print "original src In is %i, will be changed to %i" % (originalSrcIn, clipSourceIn)
        try:
          shot.setSourceIn(clipSourceIn)
        except:
          print "Could not set 'foundry.edl.srcIn'"       

  def setSrcInToFirstFrameOfClip(self):
    """Sets the Shot's srcIn to be the first available frame of the Clip"""
    # TO-DO Reset the TC from the edl metadata if it exists.
    view = hiero.ui.activeView()
    if not view:
      return
    
    selection = view.selection()    
    shotSelection = self.getShotSelectionForActiveView()
    for shot in shotSelection:
      sourceClip = shot.source()
      try:
        clipSourceIn = sourceClip.sourceIn() - sourceClip.timelineOffset()
        shot.setSourceIn(clipSourceIn)
        shot.setSourceOut(clipSourceIn + (shot.duration()-1))
      except:
        print "Unable to adjust source in timecode for %s" % str(shot)

  def copyTC(self):
    """'Copies' the shot selection to the 'Clipboard', storing it in hiero.core.shotClipboard"""

    view = hiero.ui.activeView()
    if not view:
      return
    
    selection = view.selection()    
    shotSelection = self.getShotSelectionForActiveView()
    hiero.core.shotClipboard = shotSelection
    print "Copied to hiero.core.shotClipboard: %s" % str(hiero.core.shotClipboard)

  def getShotSelectionForActiveView(self):
    view = hiero.ui.activeView()
    if not view:
      return None
    
    selection = view.selection()    

    # We can only apply pasted TC data to shots which exist on un-locked Tracks
    destShotSelection = [item for item in selection if isinstance(item, (hiero.core.TrackItem)) and not item.parent().isLocked()]
    return destShotSelection

  def pasteTC(self):
    """This action applies all TC info (src+dst) from the source shot in hiero.core.shotClipboard
    to the current selection of shots.
    """
    # We can only apply pasted TC data to shots which exist on un-locked Tracks
    destShotSelection = self.getShotSelectionForActiveView()

    # If there's more than one shot in the Clipboard, bail out and Warn
    if len(hiero.core.shotClipboard) != 1:
      print "[Paste TC Error] : you can only paste shot info from a single shot.\n  -Current Shot clipboard contains multiple shots: %s" % str(hiero.core.shotClipboard)
      return

    copiedShot = hiero.core.shotClipboard[0]
    proj = copiedShot.project()
    seq = copiedShot.parentSequence()

    # Else, we have a single shot, so apply all TCs to all destination shots...
    srcIn = copiedShot.sourceIn()
    srcOut = copiedShot.sourceOut()
    dstIn = copiedShot.timelineIn()
    dstOut = copiedShot.timelineOut()

    for destShot in destShotSelection:
      try:
        destShot.setTimelineIn(dstIn)
        seq.editFinished()
        destShot.setTimelineOut(dstOut)        
        seq.editFinished()
        destShot.setSourceIn(srcIn)
        seq.editFinished()
        destShot.setSourceOut(srcOut)
        seq.editFinished()
      except: 
        print "[Paste TC Error: Unable to paste TC info from %s to %s.\nCheck timecodes do not cause overlap conflicts." % (str(copiedShot), str(destShot))    

  def pasteTCSpecial(self):
    selectedShots = self.getShotSelectionForActiveView()
    dialog = PasteShotInfoDialog(selection=selectedShots, parent = hiero.ui.mainWindow())

    # Raise the dialog and if accept is given, do the business...
    if dialog.exec_():
      pasteDstIn = dialog._dstInCheckBox.isChecked()
      pasteDstOut = dialog._dstOutCheckBox.isChecked()
      pasteSrcIn = dialog._srcInCheckBox.isChecked()      
      pasteSrcOut = dialog._srcOutCheckBox.isChecked()

      shots = dialog._destinationShots
      copiedShot = dialog._currentCopiedShot
      srcIn = copiedShot.sourceIn()
      srcOut = copiedShot.sourceOut()
      dstIn = copiedShot.timelineIn()
      dstOut = copiedShot.timelineOut()           

      proj = copiedShot.project()
      seq = dialog._destinationShots[0].parentSequence()

      # NEED TO ADD GROUP UNDO HERE BUT CANNOT GET THIS TO WORK!
      # Grab what TC bits need to be pasted
      for shot in shots:
        if pasteDstIn:
          try:
            shot.setTimelineIn(dstIn)
            seq.editFinished()
          except:
            print "Unable to set dstIn"

        if pasteDstOut:
          try:
            shot.setTimelineOut(dstOut)
            seq.editFinished()
          except:
            print "Unable to set dstOut"

        if pasteSrcIn:
          try:
            shot.setSourceIn(srcIn)
            seq.editFinished()
          except:
            print "Unable to set srcIn"

        if pasteSrcOut:
          try:
            shot.setSourceOut(srcOut)
            seq.editFinished()
          except:
            print "Unable to set srcOut"

  # This handles events from the Project Bin View
  def eventHandler(self, event):

    if not hasattr(event.sender, 'selection'):
      # Something has gone wrong, we should only be here if raised
      # by the timeline view which gives a selection.
      return
    s = event.sender.selection()

    # Return if there's no Selection. We won't add the Tags Menu.
    if s == None:
      return

    # Filter the selection to only act on TrackItems, not Transitions etc.
    shotSelection = self.getShotSelectionForActiveView()

    # We only enable Paste operations if ONE shot is in the hiero.core.shotClipboard

    enablePaste = (len(hiero.core.shotClipboard) == 1)
    self._pasteTCAction.setEnabled(enablePaste)
    self._pasteTCSpecialAction.setEnabled(enablePaste)
    
    # Insert the Tags menu with the Clear Tags Option
    insertMenuAction(self._timecodeMenu.menuAction(),  event.menu)

# Instantiate the Menu to get it to register itself.
tcMenu = TimecodeMenu()