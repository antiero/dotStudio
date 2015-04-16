# Adds Set Poster frame action to the Viewer menu
import hiero.core
from hiero.ui import activeSequence, currentViewer, findMenuAction, insertMenuAction, registerAction
from PySide.QtGui import QAction, QFocusEvent

class SetPosterFrameAction(QAction):
  """Action which sets the Poster frame for the active Clip/Sequence to be the Currently displayed frame"""

  def __init__(self):
      QAction.__init__(self, "Set Poster Frame", None)
      self.triggered.connect(self.setPosterFrameForActiveSequence)
      hiero.core.events.registerInterest("kShowContextMenu/kViewer", self.eventHandler)
      self.setObjectName("foundry.viewer.setPosterFrame")
      self.setShortcut("Shift+P")
      self.currentViewer = None

  def setPosterFrameForActiveSequence(self):
    if not self.currentViewer:
      self.currentViewer = currentViewer()

    currentTime = self.currentViewer.time()
    activeSequence = self.currentViewer.player().sequence()

    if activeSequence and currentTime:
      activeSequence.setPosterFrame(int(currentTime))

    self.currentViewer = None

  def eventHandler(self, event):
    enabled = event.sender.player().sequence() is not None
    for a in event.menu.actions():
      if a.text().lower().strip() == "mark":
        self.setEnabled(enabled)
        insertMenuAction( self, a.menu())

# Instantiate the action, add it to the Viewer menu and register it.
action = SetPosterFrameAction()
v = findMenuAction("foundry.menu.viewer")
insertMenuAction(action, v.menu(), after = 'foundry.viewer.clearInOut')
registerAction(action)