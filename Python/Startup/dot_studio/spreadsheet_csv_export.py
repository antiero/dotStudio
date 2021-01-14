# This action adds itself to the Spreadsheet View context menu allowing the contents of the Spreadsheet be exported as a CSV file.
# Usage: Right-click in Spreadsheet > "Export as .CSV"
# Note: This only prints the text data that is visible in the active Spreadsheet View.
# If you've filtered text, only the visible text will be printed to the CSV file
# Usage: Copy to <HIERO_PLUGIN_PATH>/Python/StartupUI
import hiero.core.events
import hiero.ui
import os, csv
from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2 import QtCore

### Magic Widget Finding Methods - This stuff crawls all the PySide widgets, looking for an answer 
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
  app = QtWidgets.QApplication.instance()
  for w in app.topLevelWidgets():
    findWidget(w)

  filteredWidgets = foundryWidgets
  if filter:
    filteredWidgets = []
    for widget in foundryWidgets:
      if filter in widget.metaObject().className():
        filteredWidgets+=[widget]
  return filteredWidgets

# When right click, get the Sequence Name
def activeSpreadsheetTreeView():
  """
  Does some PySide widget Magic to detect the Active Spreadsheet TreeView.
  """
  spreadsheetViews = getFoundryWidgetsWithClassName(filter='SpreadsheetTreeView')
  for spreadSheet in spreadsheetViews:
    if spreadSheet.hasFocus():
      activeSpreadSheet = spreadSheet
      return activeSpreadSheet
  return None

#### Adds "Export .CSV" action to the Spreadsheet Context menu ####
class SpreadsheetExportCSVAction(QtWidgets.QAction):

  def __init__(self):
    QtWidgets.QAction.__init__(self, "Export as .CSV", None)
    self.triggered.connect(self.exportCSVFromActiveSpreadsheetView)
    hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
    self.setIcon(QtGui.QIcon("icons:FBGridView.png"))

  def eventHandler(self, event):
    # Insert the action to the Export CSV menu
    event.menu.addAction(self)

  #### The guts!.. Writes a CSV file from a Sequence Object ####
  def exportCSVFromActiveSpreadsheetView(self):

    # Get the active QTreeView from the active Spreadsheet
    spreadsheetTreeView = activeSpreadsheetTreeView()

    if not spreadsheetTreeView:
      return 'Unable to detect the active TreeView.'
    seq = hiero.ui.activeView().sequence()
    if not seq:
      print 'Unable to detect the active Sequence from the activeView.'
      return

    # The data model of the QTreeView
    model = spreadsheetTreeView.model()

    csvSavePath = os.path.join(QtCore.QDir.homePath(),'Desktop',seq.name()+'.csv')
    savePath,filter = QtWidgets.QFileDialog.getSaveFileName(None,caption="Export Spreadsheet to .CSV as...",dir = csvSavePath, filter = "*.csv")
    print 'Saving To: ' + str(savePath)

    # Saving was cancelled...
    if len(savePath)==0:
      return

    # Get a CSV writer object
    f = open(savePath, 'w')
    csvWriter = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

    # This is a list of the Column titles
    csvHeader = []

    for col in range(0,model.columnCount()):
      if not spreadsheetTreeView.isColumnHidden(col):
        csvHeader+=[model.headerData(col,QtCore.Qt.Horizontal)]

    # Write the Header row to the CSV file
    csvWriter.writerow(csvHeader)

    # Go through each row/column and print 
    for row in range(model.rowCount()):
      row_data = []
      for col in range(model.columnCount()):
        if not spreadsheetTreeView.isColumnHidden(col):
          row_data.append(model.index( row, col, QtCore.QModelIndex() ).data( QtCore.Qt.DisplayRole ))
      
      # Write row to CSV file...  
      csvWriter.writerow(row_data)

    f.close()
    # Conveniently show the CSV file in the native file browser...
    QtGui.QDesktopServices.openUrl(QUrl('file:///%s' % (os.path.dirname(savePath))))  

# Add the action...
csvActions = SpreadsheetExportCSVAction()