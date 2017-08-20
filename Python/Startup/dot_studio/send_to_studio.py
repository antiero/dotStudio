import hiero.core
import nuke
import os
import re
import foundry.ui
from PySide2 import QtWidgets

# Helper methods
def pathContainsDigits(d):
  _digits = re.compile('\d')
  return bool(_digits.search(d))

def currentCompIsSaved():
  """Returns True if the current comp has been saved, False otherwise"""
  rt = nuke.root()
  scriptSaved = (rt.name() != "Root" and os.path.isfile(rt.name()))
  return scriptSaved

def currentCompContainsValidWriteNodes():
  """Returns True if any Write nodes in the current Comp are set up to render image Sequences to a writeable path"""
  writeNodes = nuke.allNodes("Write")
  if len(writeNodes)==0:
    return False

  validWriteNodes = []
  for w in writeNodes:
    origFilename = w["file"].value()
    
    # A cheap hack to see whether the filename is set up to render image sequences
    replacedFileName = nuke.filename(w, nuke.REPLACE)
    
    filebase = os.path.basename(replacedFileName)
    dirname = os.path.dirname(replacedFileName)

    # If replaced filename differs, we know it's been set up for %04d / #### frame padding.
    # Then confirm numbers exist in the replacedFilename and that we have Write access for renderes...
    if (origFilename != replacedFileName) and pathContainsDigits(filebase) and os.access(dirname, os.W_OK):
      validWriteNodes+=[w]

  return len(validWriteNodes)>0

def currentCompIsReadyForStudio():
  """Validates whether the Comp is set up correctly for being a nkClip.
  Requirements are: 
  1) Comp has been saved to disk already
  2) Write node is set up to render to image sequence."""

  ready = currentCompIsSaved() and currentCompContainsValidWriteNodes()
  return ready

class SetupCompDialog(QtWidgets.QDialog):
  """ Dialog for selecting a project shot preset. """

  @staticmethod
  def getPresetFromDialog(project, text):
    """ Show a ProjectSetupCompDialog and return the selected preset, or None if the user cancelled. """
    dialog = SetupCompDialog(project, text)
    if dialog.exec_():
      shotPreset = dialog.selectedPreset()
      project.setShotPresetName(shotPreset.name())
      return shotPreset
    else:
      return None

  def __init__(self, project, text):
    super(SetupCompDialog, self).__init__(hiero.ui.mainWindow())

    self.setWindowTitle("Project Shot Preset")

    self._project = project

    # Keyword resolver for using {tokens} in the Comp Setup dialog
    self._resolver = hiero.core.FnResolveTable.ResolveTable()
    self._resolver.addResolver("{shot}", "Name of the Shot being processed", lambda keyword, task: task.name())
    self._resolver.addResolver("{version}", "Source filename of the TrackItem", lambda keyword, task: task.source().mediaSource().filename())    

    layout = QtWidgets.QFormLayout()
    self.setLayout(layout)

    label = QtWidgets.QLabel(text)
    layout.addWidget(label)

    self.projectRootPicker = foundry.ui.FnFilenameField("Select Project Root")
    self.projectRootPicker.setFilename(str(project.projectRoot()))
    
    projectRoot = "" # Get this from a uistate.ini / Preference?

    projectRoots = self.possibleProjectRoots()
    if len(projectRoots)<1:
      projectRoot = os.path.expanduser("~")

    else:
      projectRoot = projectRoots[-1]

    self.projectRootPicker.setFilename(projectRoot)
    layout.addRow("Project Root", self.projectRootPicker)

    self.shotNameLineEdit = QtWidgets.QLineEdit()
    self.shotNameLineEdit.setText("Shot0010")
    layout.addRow("Shot Name", self.shotNameLineEdit)

    self.shotPresetCombo = QtWidgets.QComboBox()
    layout.addRow("Preset", self.shotPresetCombo)
    self.shotPresetCombo.currentIndexChanged.connect(self.shotPresetChanged)    

    #self.infoLabel = QLabel()
    #self.infoLabel.setText("Comp details here...")
    #layout.addRow("", self.infoLabel)

    #self.versionWidget = hiero.ui.VersionWidget()
    #layout.addRow("Version", self.versionWidget)

    for preset in hiero.core.taskRegistry.nukeShotExportPresets(project):
      self.shotPresetCombo.addItem(preset.name(), preset)

    buttonBox = QtWidgets.QDialogButtonBox( QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel )
    buttonBox.accepted.connect( self.accept )
    buttonBox.rejected.connect( self.reject )
    layout.addWidget( buttonBox )

  def createWriteNodeFromPreset(self, preset):
    """Return a Nuke Write node based on a path and a preset."""
    
    for path, taskPreset in preset.properties()["exportTemplate"]:
      if isinstance(taskPreset, hiero.exporters.FnExternalRender.NukeRenderPreset):
        writeNode = nuke.nodes.Write()
        properties = taskPreset.properties()
        print "Unresolved Path is: %s" % path
        file_type = properties["file_type"]
        writeNode["file_type"].setValue(str(file_type))

        # Replace {shot} from the current name in the dialog
        _shotName = self.currentShotName()
        path = path.replace(r"{shot}", _shotName)

        # Replace {ext} from the current file_type
        path = path.replace(r"{ext}", file_type)

        # Replace {_nameindex} with nothing. 
        # It means nothing in the context of sending a Comp to Studio
        path = path.replace(r"{_nameindex}", "")

        # Replace {version} from version index and padding, from the preset
        # TO-DO: Make this an option on the dialog via VersionWidget?
        _resolvedVersionStringFromPreset = self.resolvedVersionStringFromPreset(preset)
        path = path.replace(r"{version}", str(_resolvedVersionStringFromPreset))

        # Now we need to prepend the project Root to the path...
        path = os.path.join(self.currentProjectRoot(), path)

        print "Resolved Path is: %s" % path
        writeNode["file"].setValue(path)

        if "channels" in properties:
          writeNode["channels"].setValue(properties["channels"])

        colourTransform = None
        if "colourspace" in properties:  
          colourTransform = properties["colourspace"]
          if colourTransform == 'raw':
            colourTransform = 'linear'

        if colourTransform is not None:
          writeNode["colorspace"].setValue(colourTransform)

        fileTypeSettings = properties[file_type]
        for key in fileTypeSettings.keys():
          writeNode[key].setValue(str(properties[file_type][key]))

    # TO-DO: Handle Presets which use OCIO nodes, and QuickTime movies    
    return writeNode    

  def possibleProjectRoots(self):
    """Returns a list of possible Project roots for the currently open Studio projects"""
    projectRoots = projectRoots = [proj.projectRoot() for proj in hiero.core.projects() if os.access(proj.projectRoot(), os.W_OK)]
    return projectRoots

  def currentShotName(self):
    """Returns the current shot name from the dialog"""
    return unicode(self.shotNameLineEdit.text())

  def currentProjectRoot(self):
    """Returns the current shot name from the dialog"""
    return unicode(self.projectRootPicker.filename())    

  def resolvedVersionStringFromPreset(self, preset):
    versionIndex = self.versionIndexFromPreset(preset)
    versionPadding = self.versionPaddingFromPreset(preset)
    resolvedVersionString = "v%s" % format(versionIndex, "0%id" % int(versionPadding))
    return resolvedVersionString
  
  def versionPaddingFromPreset(self, preset):
    return preset.properties()["versionPadding"]

  def versionIndexFromPreset(self, preset):
    return preset.properties()["versionIndex"]

  def getWriteNodeTasksFromPreset(self, preset):
    """Returns a non-Cherbetjified Dictionary from a Preset"""
    writeNodeOutputTasks = []
    for path, taskPreset in preset.properties()["exportTemplate"]:
      if isinstance(taskPreset, hiero.exporters.FnExternalRender.NukeRenderPreset):
        properties = taskPreset.properties()
        file_type = properties["file_type"]
        channels = properties["channels"]
        dataTypeInfo = properties[file_type] # Bonkers Cherbetji

        writeNodeOutputTasks+=[{"path" : path, "file_type":file_type, "channels": channels}]

    print "Got Possible Nuke Write nodes Tasks %s" % writeNodeOutputTasks
    return writeNodeOutputTasks

  def getNukeScriptSaveTasksFromPreset(self, preset):
    nkScriptTasks = []
    for path, taskPreset in preset.properties()["exportTemplate"]:
      if isinstance(taskPreset, hiero.exporters.FnNukeShotExporter.NukeShotPreset):
        
        nkScriptTasks+=[{"preset":taskPreset, "path": path}]

    print "Got Possible Nuke Script Save Tasks: %s" % nkScriptTasks
    return nkScriptTasks

  def shotPresetChanged(self, index):

    presetsDict = dict([ (preset.name(), preset) for preset in hiero.core.taskRegistry.localPresets() + hiero.core.taskRegistry.projectPresets(self._project) ])

    value = self.shotPresetCombo.currentText()
    if value in presetsDict:
      self._preset = presetsDict[value]
      #self.infoLabel.setText(self.getUnresolvedWritePathFromPreset(self._preset))
      self.getWriteNodeTasksFromPreset(self._preset)
      self.getNukeScriptSaveTasksFromPreset(self._preset)

  def selectedPreset(self):
    index = self.shotPresetCombo.currentIndex()
    return self.shotPresetCombo.itemData(index)

class SendCompMenu(object):
  def __init__(self):
    self.nodeGraphMenu = nuke.menu( 'Node Graph' )
    self.sendCompMenu = self.nodeGraphMenu.addMenu("Send Comp")
    self.sendCompToStudioAction = self.sendCompMenu.addCommand("To Project Bin", sendCompToStudioProject)

def sendCompToStudioProject():
  """Sends the current Comp to NukeStudio Project bin.
  If multiple Projects are open, you must choose a destination"""

  # First work out a destination project for the Comp...
  projects = hiero.core.projects()
  numProjects = len(projects)
  
  selectedNodes = nuke.selectedNodes()

  # Case 1: No Studio Projects exist, just create an empty one...
  if numProjects == 0:
    project = hiero.core.newProject()
  
  # Case 2: One Project exists, use that...
  elif numProjects == 1:
    project = projects[0]

  # Case 3: Multiple Projects exist, display a pop-up to display possible destination projects
  elif numProjects > 1:
    projIndex = nuke.choice("Choose a destination Project", "Choose Project", [proj.name() for proj in projects])
    project = projects[projIndex]

  # First the simple case, where a Script has alreay been set up to Render everything we need...
  projectRootBin = project.clipsBin()
  ready = currentCompIsReadyForStudio()
  if ready:
    nkScript = nuke.root().name()
    nkClipBinItem = hiero.core.BinItem(hiero.core.Clip(nkScript))
    projectRootBin.addItem(nkClipBinItem)
    hiero.ui.setWorkspace("Finishing")
  else:
    presetDialog = SetupCompDialog(project, "")
    nuke.currentPreset = presetDialog.getPresetFromDialog(project, "Setup Comp")
    print "nuke.currentPreset is: %s" % str(nuke.currentPreset)
    writeNode = presetDialog.createWriteNodeFromPreset(nuke.currentPreset)
    outputNode = selectedNodes[-1]
    writeNode.setInput(0, outputNode)

    # To-do: Save the Script somewhere and set the correct path for nkClip
    nkScript = writeNode['file'].value()
    nkClipBinItem = hiero.core.BinItem(hiero.core.Clip(nkScript))
    projectRootBin.addItem(nkClipBinItem)
    hiero.ui.setWorkspace("Finishing")
    
if nuke.env['studio']:
  M = SendCompMenu()