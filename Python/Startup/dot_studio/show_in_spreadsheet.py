# Adds 'Open In > Spreadsheet' action for showing a Shot in the Spreadsheet TreeView
# You can this automatically show on selection change by setting gEnabledOnSelectionChange to True
# Working with some Caveats:
# -Does not work when text filtering is set in the Spreadsheet search box.
import hiero.core
import hiero.ui
from PySide.QtGui import *
from PySide.QtCore import *

# Global behaviour for making this action trigger with a Selection Change event. 
# Set to False if you don't want the Spreadsheet to scroll automatically on shot selection change
gEnabledOnSelectionChange = False

###  Widget Finding Methods - This stuff crawls all the PySide widgets, looking for an answer 
def findWidget(w):
  global foundryWidgets
  if 'Foundry' in w.metaObject().className():
    foundryWidgets+=[w]
    
  for c in w.children():
    findWidget(c)
  return foundryWidgets

def getFoundryWidgetsWithClassName(filter=None):
  global foundryWidgets
  foundryWidgets = []
  widgets = []
  app = QApplication.instance()
  for w in app.topLevelWidgets():
    findWidget(w)

  filteredWidgets = foundryWidgets
  if filter:
    filteredWidgets = []
    for widget in foundryWidgets:
      if filter in widget.metaObject().className():
        filteredWidgets+=[widget]
  return filteredWidgets

def spreadsheetTreeViewWidgets():
  """
  Does some PySide widget Magic to detect the Spreadsheet TreeViews
  """
  spreadsheetViews = getFoundryWidgetsWithClassName(filter='SpreadsheetTreeView')
  return spreadsheetViews

def getSpreadsheetViewWithName(name):
  spreadsheetViews = spreadsheetTreeViewWidgets()

  matches = []
  for widget in spreadsheetViews:
    if widget.parentWidget().windowTitle() == name:
      matches+=[widget]

  return matches

def median(lst):
  """Used to get the row index median for multiple shots"""
  even = (0 if len(lst) % 2 else 1) + 1
  half = (len(lst) - 1) / 2
  return sum(sorted(lst)[half:half + even]) / float(even)

# Main action, added to timeline right-click menu and Timeline Menu on main Menubar.
class SpreadsheetScrollToAction(QAction):
  """Action to Scroll Spreadsheet to row where the selected shot is.
  If multiple shots are selected, the median index is treated as the row number."""

  global gEnabledOnSelectionChange

  # By Default Enable this behaviour on selection change event... might be expensive but seems ok with 200 shot timeline
  enabledOnSelectionChange = gEnabledOnSelectionChange # Set to False if you don't want this to happen on every selection change

  def __init__(self):
    QAction.__init__(self, "Show in Spreadsheet", None)
    self.triggered.connect(self.showShotSelectionInSpreadsheet)
    hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
    #self.setShortcut("Ctrl+Shift+F")

    if self.enabledOnSelectionChange:
      hiero.core.events.registerInterest("kSelectionChanged",self.showShotSelectionInSpreadsheet)

  def showShotSelectionInSpreadsheet(self, *args):
    """Show the shot selection in the SpreadsheetView"""
    selection = hiero.ui.activeView().selection()
    
    # We filter out only TrackItems, no Transitions or other Selections...
    shotSelection = [shot for shot in selection if isinstance(shot,hiero.core.TrackItem)]

    # Bail if no shots selected
    if len(shotSelection)==0:
      return

    shot = shotSelection[0]
    sequence = shot.parentSequence()
    sequenceName = sequence.name()
    
    # We find the Spreadsheet Treeview based on the sequence name.... (a bit hacky as we MAY have more than one...)
    spreadsheetTreeView = getSpreadsheetViewWithName(sequenceName)

    if len(spreadsheetTreeView)==0:
      hiero.ui.openInSpreadsheet(sequence)
      spreadsheetTreeView = getSpreadsheetViewWithName(sequenceName)[0]
      if not spreadsheetTreeView:
        return
    else:
      spreadsheetTreeView = spreadsheetTreeView[0]
    
    # If it's just one shot selected, work out its index, easy...
    if len(shotSelection)==1:
      eventNumberIndex = shot.eventNumber()
    else:
      # We have multiple shots selected...
      eventNumbers = []
      for shot in shotSelection:
        eventNumbers+=[shot.eventNumber()]

      eventNumberIndex = median(eventNumbers)

    # This bit does the scrolling...
    model = spreadsheetTreeView.model()
    
    # This returns a QModelIndex
    try:
      qm = model.index(eventNumberIndex-1,0)
    except:
      print "Could not find an index %i in the model." % eventNumberIndex-1

    # Gotcha! The Spreadsheet View MIGHT have been sorted by Name/Event number, make the row index a problem...
    # Call sort first, so that rows are numbered Sequentially
    model.sort(-1)

    # Try scrolling there...
    try:
      spreadsheetTreeView.scrollTo(qm)
    except:
      print 'Unable to scroll to shot. Was the Spreadsheet being filtered by text in the text field?'

  def eventHandler(self, event):

    # We check that the view which sent this event has a 'getSelection' method, to return the selected items
    if not hasattr(event.sender, 'selection'):
      return

    # Get the selection...
    selection = event.sender.selection()

    if len(selection)==0:
      return
    
    # We filter out only TrackItems, no Transitions or other Selections...
    shotSelection = [shot for shot in selection if isinstance(shot,hiero.core.TrackItem)]
    
    # Add the Menu to the right-click menu with an appropriate title
    if len(shotSelection)>0:
      self.setEnabled(len(shotSelection)>0)

      # Add the Action to the Contextual Menu...
      for a in event.menu.actions():
        if a.text().lower().strip() == "open in":
          self.setText("Spreadsheet View")
          hiero.ui.insertMenuAction( self, a.menu() )

act = SpreadsheetScrollToAction()
timelineMenu = hiero.ui.findMenuAction('foundry.menu.sequence').menu()
timelineMenu.addAction(act)