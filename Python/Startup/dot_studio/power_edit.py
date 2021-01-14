import hiero.core
import nuke
from hiero.ui import activeView, createMenuAction, menuBar
from PySide2 import QtCore, QtGui, QtWidgets


class PowerEditToolAction:
  def __init__(self):
      self._PowerEditToolShowAction = createMenuAction("Power Edit", self.doit)
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)

  class PowerEditToolDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
      super(PowerEditToolAction.PowerEditToolDialog, self).__init__(parent)
      self.setWindowTitle("Power Edit")
      layout = QtWidgets.QGridLayout()
      self.setLayout(layout)
      self.appSettings  = hiero.core.ApplicationSettings()

      label = QLabel("What would you like to do?\n")
      layout.addWidget(label, 0,0)

      self._trimExtendButton = QtWidgets.QRadioButton("Trim")
      self._trimExtendButton.setToolTip('Trim/Extend frames off the Head/Tail of a Shot. Positive value trims frames, negative extends.')
      self._trimExtendheadTailDropdown = QComboBox()
      self._trimExtendheadTailDropdown.addItem('Head+Tail')
      self._trimExtendheadTailDropdown.addItem('Head')
      self._trimExtendheadTailDropdown.addItem('Tail')

      self._frameInc = QtWidgets.QSpinBox()
      self._frameInc.setMinimum(-1e9)
      self._frameInc.setMaximum(1e9)
      self._frameInc.setValue(int(self.getFrameIncDefault()))

      layout.addWidget( self._trimExtendButton, 1,0 )
      layout.addWidget( self._trimExtendheadTailDropdown, 1,1 )

      self._moveButton = QtWidgets.QRadioButton("Move")
      self._moveButton.setToolTip('Move Shots forwards (+) or backwards (-) by X number of frames.')
      layout.addWidget( self._moveButton, 2,0 )

      self._slipButton = QtWidgets.QRadioButton("Slip")
      self._slipButton.setToolTip('Slip Shots forwards (+) or backwards (-) by X number of frames.')
      layout.addWidget( self._slipButton, 3,0 )

      label = QLabel("By this many frames:")
      layout.addWidget(label, 4,0)
      layout.addWidget( self._frameInc, 4,1 )

      self._trimExtendButton.setChecked(True)
      self._trimExtendheadTailDropdown.setEnabled(True)

      self._trimExtendButton.clicked.connect(self.radioButtonClicked)
      self._moveButton.clicked.connect(self.radioButtonClicked)
      self._slipButton.clicked.connect(self.radioButtonClicked)

      buttonBox = QtWidgets.QDialogButtonBox( QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel )
      buttonBox.accepted.connect( self.accept )
      buttonBox.rejected.connect( self.reject )
      layout.addWidget( buttonBox )

    def radioButtonClicked(self):
      if self._trimExtendButton.isChecked():
        self._trimExtendheadTailDropdown.setEnabled(True)
      elif self._moveButton.isChecked():
        self._trimExtendheadTailDropdown.setEnabled(False)

      elif self._slipButton.isChecked():
        self._trimExtendheadTailDropdown.setEnabled(False)

    def selectedAction(self):
      if self._trimButton.isChecked():
        return PowerEditToolDialog.kTrim,
      elif self._moveButton.isChecked():
        return PowerEditToolDialog.kMove
      elif self._slipButton.isChecked():
        return PowerEditToolDialog.kSlip
      else:
        return PowerEditToolDialog.kExtend

    def getFrameIncDefault(self):
      frameInc = self.appSettings.value('Sequence/frame_increment')
      if frameInc == "":
        frameInc = 12
      return frameInc

    def setFrameIncPreference(self):
      self.appSettings.setValue('Sequence/frame_increment',str(self._frameInc.value()))

  def doitGetSelection(self):

    self.selectedTrackItems = []
    view = activeView()
    if not view:
      return
    if not hasattr(view,'selection'):
      return

    s = view.selection()
    if s is None:
      return

    # Ignore transitions from the selection
    self.selectedTrackItems = [item for item in s if isinstance(item, (hiero.core.TrackItem, hiero.core.SubTrackItem))]
    if not self.selectedTrackItems:
      return

    self.doit()

  def doit(self):
    d = self.PowerEditToolDialog()
    if d.exec_():
      frames = d._frameInc.value()
      # Update this preference...
      d.setFrameIncPreference()
      if d._trimExtendButton.isChecked():
        headTailOpt = d._trimExtendheadTailDropdown.currentText()
        self.trimExtendSelection(frames, headTail = headTailOpt)

      elif d._moveButton.isChecked():
        self.moveSelection(frames)
      elif d._slipButton.isChecked():
          self.slipSelection(frames)

  def trimExtendSelection(self, frames, headTail = 'Head+Tail'):
    p = self.selectedTrackItems[0].project()
    p.beginUndo('Trim Selection')
    if headTail == 'Head+Tail':
      for t in self.selectedTrackItems:
        t.trimIn(frames)
        t.trimOut(frames)

    elif headTail == 'Head':
      for t in self.selectedTrackItems:
        t.trimIn(frames)
    elif headTail == 'Tail':
      for t in self.selectedTrackItems:
        t.trimOut(frames)
    p.endUndo()

  def moveSelection(self, frames):
    p = self.selectedTrackItems[0].project()
    p.beginUndo('Move Selection')
    t = self.selectedTrackItems[0]

    # This is a strange function call, should be on the Sequence not TrackItem level!
    try:
      t.moveTrackItems(self.selectedTrackItems, frames)
    except RuntimeError:
      nuke.critical("Requested move rejected. Overlapping track items / negative times are forbidden.")

    p.endUndo()

  def slipSelection(self, frames):
    p = self.selectedTrackItems[0].project()
    p.beginUndo('Slip Selection')
    for t in self.selectedTrackItems:
      t.setSourceIn(int(t.sourceIn())+(int(frames)))
      t.setSourceOut(int(t.sourceOut())+(int(frames)))
    p.endUndo()

  # This handes events from the Timeline
  def eventHandler(self, event):
    self.selectedTrackItems = []
    s = event.sender.selection()
    if len(s)>1:
      enabled = False
    enabled = True
    if s is None:
      s = () # We disable on empty selection.
      enabled = False
    else:
      # Ignore transitions from the selection
      self.selectedTrackItems = [item for item in s if isinstance(item, (hiero.core.TrackItem, hiero.core.SubTrackItem))]

    self._PowerEditToolShowAction.setEnabled(enabled)
    event.menu.addAction(self._PowerEditToolShowAction)

# Add the Action
a = PowerEditToolAction()

# Grab Hiero's MenuBar
M = menuBar()

# Add a Menu to the MenuBar
ToolsMenu = M.addMenu('Tools')
# Create a new QAction
showPowerEditToolDialogAction = createMenuAction('Power Edit', a.doitGetSelection)
showPowerEditToolDialogAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+X'))

# Add the Action to your Nuke Menu
ToolsMenu.addAction(showPowerEditToolDialogAction)
