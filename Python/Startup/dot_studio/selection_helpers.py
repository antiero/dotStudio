# Selection Helpers includes a way to Copy the selected path and Python objects based on the current selection
# Install in ~/.nuke/Python/Startup

# 1) Copy Python Selection - adds a right-click Menu to the Timeline, Spreadsheet and Bin View for getting the current Selection
# After running this action, 'hiero.selectedItems' will store the selected items for use in the Script Editor.
# An Action is also added to the Edit Menu, with a keyboard shortcut of Ctrl/Cmd+Alt+C.
# By default in the Bin View, the selection will return the activeItem, i.e. the Clip or Sequence, rather than the BinItem.
# This behaviour can be overridden by changing kAlwaysReturnActiveItem = True to False
# This can be set dynamically in the Script editor via: hiero.plugins.selection_helpers.SelectedShotAction.kAlwaysReturnActiveItem = False
import hiero.core
import hiero.ui
from PySide.QtGui import QAction, QApplication

class SelectedShotAction(QAction):
  kAlwaysReturnActiveItem = True # Change me to False if you want BinItems rather than Clips/Sequences in the BinView
  def __init__(self):
    QAction.__init__(self, "Copy Python Selection", None)
    self.triggered.connect(self.getPythonSelection)
    hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
    hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
    hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
    self.setShortcut("Ctrl+Alt+C")
    self._selection = ()

  def getPythonSelection(self):
    """Get the Python selection and stuff it in: hiero.selectedItems"""
    self.updateActiveViewSelection()
    
    print "Selection copied to 'hiero.selectedItems':\n", self._selection
    clipboard = QApplication.clipboard()
    clipboard.setText("hiero.selectedItems")
    hiero.selectedItems = self._selection
  
  def updateActiveViewSelection(self):
    view = hiero.ui.activeView()

    if hasattr(view, 'selection'):
      selection = view.selection()

      # If we're in the BinView, we pretty much always want the activeItem, so whack that in...
      if isinstance(view,hiero.ui.BinView):
        if self.kAlwaysReturnActiveItem:
          self._selection = [(item.activeItem() if hasattr(item,'activeItem') else item) for item in selection]
          
          # We  special case when a Project is selected, as the default selection method returns a Bin('Sequences') item, not a Project.
          indices_to_replace = [i for i, item in enumerate(self._selection) if (hasattr(item,'parentBin') and isinstance(item.parentBin(), hiero.core.Project))]
          for ix in indices_to_replace:
            self._selection[ix] = self._selection[ix].parentBin()

        else:
          self._selection = selection

      elif isinstance(view,(hiero.ui.TimelineEditor, hiero.ui.SpreadsheetView)):
          self._selection = selection

      # Finally, if there is only one item selected, don't bother returning a tuple, just that item
      if len(self._selection)==1:
        self._selection = self._selection[0]

  def eventHandler(self, event):
    self._selection = () # Clear the curent selection

    # Add the Menu to the right-click menu
    event.menu.addAction( self )

# The act of initialising the action adds it to the right-click menu...
SelectedShotAction = SelectedShotAction()

# And to enable the Ctrl/Cmd+Alt+C, add it to the Menu bar Edit menu...
editMenu = hiero.ui.findMenuAction("foundry.menu.edit")
editMenu.menu().addAction(SelectedShotAction)

# 2) "Copy Path(s) to Clipboard" - this example adds a right-click Menu to the Timeline, Spreadsheet and Bin View for Copying the Clip media paths of the current selected items
# After running this action, 'hiero.selectedClipPaths' will store the selected items for use in the Script Editor.
# Paths will be copied to the system Clip board so you can paste with Ctrl/Cmd+V
# Action is added to the Edit Menu, with a keyboard shortcut of Ctrl/Cmd+Shift+Alt+C. (THE CLAW!)

def filePathFromClip(clip):
  """Convenience method to drill down from Clip > Mediasource to return file path as string"""
  try:
    file_path = clip.mediaSource().fileinfos()[0].filename()
  except:
    file_path = ""
  return file_path

class CopyPathToClipBoardAction(QAction):
  
  def __init__(self):
    QAction.__init__(self, "Copy Path(s) to Clipboard", None)
    self.triggered.connect(self.getPythonSelection)
    hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
    hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
    hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
    self.setShortcut("Ctrl+Shift+Alt+C")
    self.setObjectName("foundry.menu.copypathstoclipboard")

  def getPythonSelection(self):
    """Get the Clip media path in the active View and stuff it in: hiero.selectedClipPaths"""
    selection = self.getClipPathsForActiveView()

    if selection:    
      hiero.selectedClipPaths = selection
      clipboard = QApplication.clipboard()
      clipboard.setText(str(hiero.selectedClipPaths))
      print "Clip media path selection copied to Clipboard and stored in: hiero.selectedClipPaths:\n", selection      
  
  def getClipPathsForActiveView(self):
    view = hiero.ui.activeView()
    selection = None
    if hasattr(view, 'selection'):
      selection = view.selection()

      # If we're in the BinView, the selection is always a BinItem. The Clips are accessed via 'activeItem'
      if isinstance(view,hiero.ui.BinView):

        selection = [ filePathFromClip( item.activeItem() ) for item in selection if hasattr(item, 'activeItem') and isinstance( item.activeItem(), hiero.core.Clip) ]

      # If we're in the Timeline/Spreadsheet, the selection we're after is a TrackItem. The Clips are accessed via 'source'
      elif isinstance(view,(hiero.ui.TimelineEditor, hiero.ui.SpreadsheetView)):
          selection = [ filePathFromClip( item.source() ) for item in selection if hasattr( item, 'source' ) and isinstance( item, hiero.core.TrackItem) ]

      # If there is only one item selected, don't bother returning a list, just that item
      if len(selection)==1:
        selection = selection[0]
    
    return selection

  def eventHandler(self, event):
    if not hasattr(event.sender, 'selection'):
      return

    # Add the Menu to the right-click menu
    event.menu.addAction( self )

# The act of initialising the action adds it to the right-click menu...
CopyPathToClipBoardAction = CopyPathToClipBoardAction()

# And to enable the Ctrl/Cmd+Shift+Alt+C, add it to the Menu bar Edit menu...
editMenu.menu().addAction(CopyPathToClipBoardAction)