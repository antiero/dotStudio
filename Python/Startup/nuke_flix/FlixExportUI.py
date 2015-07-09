# An export to Flix Dialog
import os.path
import hiero.core
import hiero.ui
import glob

from PySide.QtGui import *
from PySide.QtCore import *

from hiero.core import log, TaskGroup, TaskBase

# Need to work a strategy of not using Globals
gCurrentFlixXML = ""
gCurrentFlixMovie = ""

class FLIXExportDialog(QDialog):
  def __init__(self,  selection, selectedPresets, parent=None):
    super(FLIXExportDialog, self).__init__(parent)
    self.setWindowTitle("Select a FLIX Show and Sequence to Export to...")
    self.setWindowIcon(QIcon("/Users/ant/.nuke/Python/Startup/nuke_flix/flix_logo.png"))
    self.setSizeGripEnabled(True)
    
    self._exportTemplate = None

    self._currentShow = ""
    self._currentSequence = ""
    self._branch = "main"
    self._currentXMLFile = None
    self._currentMovFile = None
    self._currentComment = ""
    self._currentUser = os.getenv('USER')
    self._importStillsOption = True

    layout = QVBoxLayout()
    formLayout = QFormLayout()

    self._flixShows = ["htr", "training"]

    self._flixBranches = ["main"]

    self._flixShowList = QComboBox() # "Show"
    self._flixShowList.currentIndexChanged.connect(self.flixShowComboChanged)
    self._flixShowList.setFixedWidth(80)

    for show in self._flixShows:
      self._flixShowList.addItem(show)

    self._flixSequenceList = QComboBox() # "Sequence"
    self.updateFlixSequenceListForShow(self._flixShowList.currentText())
    self._flixSequenceList.setFixedWidth(100)
    self._flixSequenceList.currentIndexChanged.connect(self.updateFlixBranchesListForCurrentShowAndSequence)

    self._flixBranchList = QComboBox() # "Branch"

    for branch in self._flixBranches:
      self._flixBranchList.addItem(branch)    
    self._flixBranchList.setFixedWidth(100)

    self._importStillsCheckBox = QCheckBox("Import Stills?")
    self._importStillsCheckBox.setCheckState(Qt.Checked)
    self._importStillsCheckBox.clicked.connect(self._importStillsCheckChanged)


    # Top Row is Seq-Show-Import as Stills
    topLayout = QHBoxLayout()
    topLayout.setAlignment(Qt.AlignLeft)
    topLayout.addWidget(QLabel("Show"))
    topLayout.addWidget(self._flixShowList)
    topLayout.addWidget(QLabel("Sequence"))
    topLayout.addWidget(self._flixSequenceList)
    topLayout.addWidget(QLabel("Branch"))
    topLayout.addWidget(self._flixBranchList)
    topLayout.addWidget(self._importStillsCheckBox)

    formLayout.addRow(topLayout)

    self._commentField = QLineEdit()
    formLayout.addRow("Comment", self._commentField)

    # Get the Presets with FLIX in the name...
    presetNames = [preset.name() for preset in hiero.core.taskRegistry.localPresets() if 'flix' in preset.name().lower()]
  
    # List box for track selection
    presetListModel = QStandardItemModel()
    presetListView = QListView()
    presetListView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    presetListView.setModel(presetListModel)   
    for preset in presetNames:
      item = QStandardItem(preset)     
      if preset in selectedPresets:      
        item.setCheckState(Qt.Checked)
      else:
        item.setCheckState(Qt.Unchecked)
        
      item.setCheckable(True)
      presetListModel.appendRow(item)
      
    self._presetListModel = presetListModel
    presetListView.clicked.connect(self.presetSelectionChanged)
    presetListView.setFixedHeight(40)
      
    formLayout.addRow("Presets:", presetListView)      

    layout.addLayout(formLayout)
    
    self._exportTemplate = hiero.core.ExportStructure2()
    self._exportTemplateViewer = hiero.ui.ExportStructureViewer(self._exportTemplate)
            
    layout.addWidget(self._exportTemplateViewer)

    # Add the standard ok/cancel buttons, default to ok.
    self._buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    self._buttonbox.button(QDialogButtonBox.StandardButton.Ok).setText("Export")
    self._buttonbox.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
    self._buttonbox.button(QDialogButtonBox.StandardButton.Ok).setToolTip("Executes exports on selection for each selected preset")
    self._buttonbox.accepted.connect(self.acceptTest)
    self._buttonbox.rejected.connect(self.reject)
    layout.addWidget(self._buttonbox)

    self.updateFlixShowList()
    self.updateFlixBranchesListForCurrentShowAndSequence()
    self.setLayout(layout)

    # This is required for the post-export task behaviour of importing into FLIX
    self.setupCustomTaskGroupBehaviour()

  def customFinishTaskHandler(TaskBase, self):
    log.info("Finished Task")
    self._finished = True
    resolvedPath = self.resolvedExportPath()
    log.info("Resolved Export Path: %s" % resolvedPath)
    if resolvedPath.endswith('xml'):
      global gCurrentFlixXML
      gCurrentFlixXML = resolvedPath

    if resolvedPath.endswith('mov'):
      global gCurrentFlixMovie
      gCurrentFlixMovie = resolvedPath

    # ANT: THIS IS UGLY AS HELL
    if os.path.isfile(gCurrentFlixXML) and os.path.isfile(gCurrentFlixMovie):
      hiero.core.FLIXExporter.dialog.importCurrentSequenceToFlix()

  def importCurrentSequenceToFlix(self):
    global gCurrentFlixMovie
    global gCurrentFlixMovie
    self._currentXMLFile = gCurrentFlixXML
    self._currentMovFile = gCurrentFlixMovie

    if self._currentMovFile and self._currentXMLFile:
      print "Will now import to show: %s, seq: %s, branch: %s, xml: %s, movie: %s, comment %s, user: %s, importStills %s" % (self._currentShow, 
                                                                                             self._currentSequence, 
                                                                                             self._branch,
                                                                                             self._currentXMLFile, 
                                                                                             self._currentMovFile,
                                                                                             self._currentComment,
                                                                                             self._currentUser,
                                                                                             str(self._importStillsOption)
                                                                                             )

      hiero.core.flixConnection.makeImportSequenceRequest(show=self._currentShow, 
                                                          sequence=self._currentSequence, 
                                                          branch=self._branch,
                                                          edlPath=self._currentXMLFile, 
                                                          moviePath=self._currentMovFile,
                                                          comment=self._currentComment,
                                                          username=self._currentUser,
                                                          importAsStills=self._importStillsOption
                                                          )

  def _importStillsCheckChanged(self):
    self._importStillsOption = self._importStillsCheckBox.isChecked()
    return self._importStillsOption

  def setupCustomTaskGroupBehaviour(self):
    """We inject custom behaviour into the TaskGroup to allow the
    Movie and XML to be imported into FLIX after the job has finished"""
    TaskBase.finishTask = self.customFinishTaskHandler

  def flixShowComboChanged(self):
    show = self.currentShow()
    self.updateFlixSequenceListForShow(show)
    self.updateFlixBranchesListForCurrentShowAndSequence()

  def updateFlixShowList(self):
    try:
      self._flixShows = hiero.core.flixConnection.getShowList()
    except:
      print "unable to get Flix shows - is Flix open?"
      self._flixShows = []

    self._flixShowList.clear()
    for show in self._flixShows:
      self._flixShowList.addItem(show)

    self.updateFlixSequenceListForShow(self.currentShow())

  def updateFlixSequenceListForShow(self, show):
    log.info("Getting updated Flix sequence list for show %s" % show)
    try:
      self._flixSequences = hiero.core.flixConnection.getSequencesForShow(show)
    except:
      print "unable to get Flix sequences for %s - is Flix open?" % show
      self._flixSequences = []

    self._flixSequenceList.clear()
    for sequence in self._flixSequences:
      self._flixSequenceList.addItem(sequence)

  def updateFlixBranchesListForCurrentShowAndSequence(self):
    """Updates the Branches UI list based on the current show and sequence"""
    show = self.currentShow()
    sequence = self.currentSequence()
    log.info("Getting updated Flix sequence list for show %s and sequence %s" % (show, sequence))
    try:
      self._flixBranches = hiero.core.flixConnection.getSequenceBranchesForShowAndSequence(show, sequence)
    except:
      print "unable to get Flix branches for %s - is Flix open?" % show
      self._flixBranches = []

    self._flixBranchList.clear()
    for branch in self._flixBranches:
      self._flixBranchList.addItem(branch)      

  def acceptTest(self):
    self._currentXMLFile = None
    self._currentMovFile = None
    self._currentShow = self.currentShow()
    self._currentSequence = self._flixSequenceList.currentText()
    self._currentComment = self._commentField.text() # NOTE: handle non-ascii here properly!!!
    self.accept()

  def currentShow(self):
    return self._flixShowList.currentText()

  def currentSequence(self):
    return self._flixSequenceList.currentText()    

  def currentBranch(self):
    return self._flixBranchList.currentText()    
  
  def presetSelectionChanged (self, index):
    if index.isValid():
      item = self._presetListModel.itemFromIndex(index)
      presetName = item.text()
      checked = item.checkState() == Qt.Checked

      self._preset = hiero.core.taskRegistry.processorPresetByName(presetName)        
      self._exportTemplate.restore(self._preset._properties["exportTemplate"])
      if self._preset._properties["exportRoot"] != "None":
        self._exportTemplate.setExportRootPath(self._preset._properties["exportRoot"])
      self._exportTemplateViewer.setExportStructure(self._exportTemplate)
      self._resolver = self._preset.createResolver().addEntriesToExportStructureViewer(self._exportTemplateViewer)
      
  def presets(self):
    presets = []
    for row in range(0, self._presetListModel.rowCount()):
      item = self._presetListModel.item(row)
      presetName = item.text()
      checked = item.checkState() == Qt.Checked
      if checked:
        presets.append(presetName)
    
    return presets

class FLIXExportAction(QAction):
  def __init__(self):
      QAction.__init__(self, "Export to FLIX...", None)
      self.triggered.connect(self.doit)
      self.setIcon(QIcon("/Users/ant/.nuke/Python/Startup/nuke_flix/flix_logo.png"))
      hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
      self._selectedPresets = []

  class CustomItemWrapper:
    def __init__ (self, item):
      self._item = item
      
      if isinstance(self._item, hiero.core.BinItem):
        self._item = self._item.activeItem()
      
    
    def isNull (self):
      return self._item == None
      
    def sequence (self):
      if isinstance(self._item, hiero.core.Sequence):
        return self._item
      return None

    def clip (self):
      if isinstance(self._item, hiero.core.Clip):
        return self._item
      return None
    
    def trackItem (self):
      if isinstance(self._item, hiero.core.TrackItem):
        return self._item
      return None
    
    def name (self):
      return self._item.name()
      
  def doit(self):

    # Prepare list of selected items for export
    selection = [FLIXExportAction.CustomItemWrapper(item) for item in hiero.ui.activeView().selection()]

    # Create dialog
    self.dialog = FLIXExportDialog(selection, self._selectedPresets)
    # If dialog returns true
    if self.dialog.exec_():    
      # Grab list of selected preset names
      self._selectedPresets = self.dialog.presets()      
      for presetName in self._selectedPresets:
        # Grab preset from registry
        preset = hiero.core.taskRegistry.processorPresetByName(presetName)
        # Launch export
        log.info("executing preset: %s with selection %s" % (preset, selection))
        hiero.core.res = hiero.core.taskRegistry.createAndExecuteProcessor(preset, selection)

  def eventHandler(self, event):
      if not hasattr(event.sender, 'selection'):
        return
  
      s = event.sender.selection()
      
      self.setEnabled(True)
      # Just allow a single Edit export for now...
      sequences = [item.activeItem() for item in s if hasattr(item, 'activeItem') and isinstance(item.activeItem(), hiero.core.Sequence)]

      if len(sequences) != 1:
          self.setEnabled(False)
          for each in s :
              if isinstance(each, hiero.core.BinItem) :
                  if type(each.activeItem()) != type(s[0].activeItem()) :
                      self.setEnabled(False)
                      break
                  
      title = "Export to FLIX..."
      self.setText(title)
      event.menu.addAction(self)
      
# Instantiate the action to get it to register itself.
hiero.core.FLIXExporter = FLIXExportAction()