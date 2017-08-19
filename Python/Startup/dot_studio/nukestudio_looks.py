# Look Maker - Conveniently allow grade node presets 
# Allow Effects to be saved/restored within a Studio Project
# Right-click Effect > Save Look 
from PySide.QtGui import *
import hiero.core
import hiero.ui
import nuke
import os
import uuid
import ast
import glob

class LookNameDialog(QDialog):
  def __init__(self):
    QDialog.__init__(self, parent=hiero.ui.mainWindow())

    self.setWindowTitle("Set Look Name")
    layout = QFormLayout()

    self._lookNameTextEdit = QLineEdit()
    self._lookNameTextEdit.setText("Grade")
    self._lookNameTextEdit.setToolTip('Enter name for Look.')
    layout.addRow("Enter Look Name: ", self._lookNameTextEdit)

    self._buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    self._buttonbox.button(QDialogButtonBox.Ok).setText("Save")
    self._buttonbox.accepted.connect(self.accept)
    self._buttonbox.rejected.connect(self.reject)
    layout.addRow("",self._buttonbox)

    self.setLayout(layout)
    
    # Set the focus to be the Note field
    self._lookNameTextEdit.setFocus()
    self._lookNameTextEdit.selectAll()

class LooksMenu(object):
  def __init__(self):
    self._saveLookAction = hiero.ui.createMenuAction("Save Look...", self.saveGradeAsLook)
    self._clearLooksAction = hiero.ui.createMenuAction("Clear Project Looks", self.clearLooksFromProject)
    self._clearLookThumbnailCacheAction = hiero.ui.createMenuAction("Clear Look Thumbnails", self.clearLooksThumbnailCache)
    self._lookNameDialog = LookNameDialog()

    self._looksMainMenu = None
    self._restoreLookSubMenu = None
    self._tagActions = []

    # Get the .nuke Plugin path for saving thumbnails of Looks
    rootPluginPath = nuke.pluginPath()[0]
    self._lookThumbnailPath = os.path.join(rootPluginPath, "Looks", "thumbnails")

    hiero.core.events.registerInterest((hiero.core.events.EventType.kShowContextMenu, hiero.core.events.EventType.kTimeline), self.eventHandler)

  def getActiveProject(self):
    project = hiero.ui.activeSequence().project()
    return project

  def saveLookThumbnailToDisk(self):
    """Saves a Thumbnail of the look as shown in the Viewer at time of saving the look.
    Returns thumbnail .png name for use as Icon"""
    im = hiero.ui.currentViewer().image()

    # Get the .nuke Plugin path..
    lookThumbnailPath = os.path.join(self._lookThumbnailPath, "Looks", "thumbnails")
    if not os.path.isdir(lookThumbnailPath):
      os.makedirs(lookThumbnailPath)

    thumbFileName = str(uuid.uuid4()) + ".png"

    pngSavePath = os.path.join(lookThumbnailPath, thumbFileName)
    if im.save( pngSavePath ):
      return thumbFileName
    else:
      return None

  # This is just a convenience method for returning QActions with a title, triggered method and icon.
  def makeAction(self,title, method, icon = None):
    action = QAction( title, None )
    action.setIcon(QIcon(icon))
    
    # We do this magic, so that the title string from the action is used as the Tag to restore
    def methodWrapper():
      method(title)
    
    action.triggered.connect( methodWrapper )
    return action   

  def _buildLookMenu(self):
    """Builds a list of looks that can be restored, based on the 'Looks' Bin in the tags Project"""
    # Locate the 'Looks' tag Bin
    self._looksMainMenu = QMenu("Looks")
    self._restoreLookSubMenu = QMenu("Restore")
    project = self.getActiveProject()
    looksTagBin = self.getLooksTagBinForProject(project)    
    tags = looksTagBin.items()

    self._lookActions = []
    for tag in tags:
      tagName = tag.name()
      self._lookActions+=[self.makeAction( tagName, self.addLookSoftEffectFromMenuAction, icon=tag.icon())]

    for act in self._lookActions:
      self._restoreLookSubMenu.addAction(act)

    self._looksMainMenu.addMenu(self._restoreLookSubMenu)
    self._looksMainMenu.addAction(self._saveLookAction)
    self._looksMainMenu.addAction(self._clearLooksAction)

    return self._looksMainMenu

  def addLookSoftEffectFromMenuAction(self, tagName):
    """Applies a Grade Look to the current selection"""
    
    selection = hiero.ui.activeView().selection()
    if len(selection)<1:
      return
     
    project = selection[0].project()
    lookTag = self.getLooksTagFromProjectWithName(project, tagName)

    tagMetadata = lookTag.metadata()
    
    # We can only handle the following cases.. either:
    # 1 - Simple Case - Selection is a Grade node -> just reset the node and restore values_
    gradeSoftEffects = self.getEffectsFromSelection(selection)

    for grade in gradeSoftEffects:
      # For each soft effect, reset knobs to default, then set them...
      gradeNode = grade.node()
      gradeNode.resetKnobsToDefault()
    
      for key in tagMetadata.keys():
        # Get a literal eval value as this is stored as a string in the Tag...
        if key.startswith("tag.Grade_"):
          knobName = key.replace("tag.Grade_", "")
          value = ast.literal_eval(str(tagMetadata.value(key)))
          gradeNode[knobName].setValue( value )

  def showLookTextDialogForSoftEffect(self, effect):
    """Raises a dialog to ask for name of Look to save"""
    if self._lookNameDialog.exec_():
      tagName = self._lookNameDialog._lookNameTextEdit.text()
      nodeTag = self.createTagObjectForNode(effect.node(), tagName)
      self.addTagToProjectLooksBin(nodeTag, effect.project())

  def createTagObjectForNode(self, node, name):
    """Extracts node knob values and stores in metadata of a Tag"""
    tag = hiero.core.Tag(name)
    tagMetadata = tag.metadata()

    # Add a Metadata key to define this Tag as a Look Tag
    tagMetadata.setValue("tag.nodeClass", "Grade")

    # Returns a string like 'whitepoint gamma' ...
    knobNameString = node.writeKnobs(nuke.WRITE_NON_DEFAULT_ONLY)

    # Split this string to get knob names...
    knobNames = knobNameString.split()

    for knobName in knobNames:
      knobValue = node[knobName].value()

      # Set this as a key in the Tag metadata collection prefix with tag.Grade_
      tagMetadata.setValue("tag.Grade_"+knobName, str(knobValue))

    # Save a Thumbnail of the Current Viewer - this 
    thumbnail = self.saveLookThumbnailToDisk()
    tag.setIcon(thumbnail)
    return tag

  def getEffectsFromSelection(self, selection, nodeClass = "Grade"):
    """Returns a list of EffectTrackItems from a selection (default is Grade nodes)"""
    gradeEffects = [item for item in selection if isinstance(item, hiero.core.SubTrackItem) and item.node().Class()==nodeClass]
    return gradeEffects

  def getLooksTagBinForProject(self, project):
    """Returns the 'Looks' Bin in which Look Tags are stored"""
    tagsBin = project.tagsBin()
    looksBin = hiero.core.findItemsInBin(tagsBin, hiero.core.Bin, "Looks")
    if len(looksBin)>=1:
      looksBin = looksBin[0]
    else:
      looksBin = hiero.core.Bin("Looks")
      tagsBin.addItem(looksBin)

    return looksBin

  def getLooksTagFromProjectWithName(self, project, tagName):
    """Returns a Tag object from the looks bin in Project with nane = tagName"""
    looksBin = self.getLooksTagBinForProject(project)
    tag = None
    try:
      tag = looksBin[tagName]
    except:
      print "Unable to find Tag with name: %s. Was it deleted?" % tagName
      return tag

    return tag    

  def clearLooksFromProject(self):
    """Removes Looks from Project and thumbnails from ~/.nuke/Looks/thumbnail dir"""

    clearYesNo = nuke.ask("Are you sure you wish to clear all Project Looks and thumbnails?")

    if clearYesNo:
      project = hiero.ui.activeSequence().project()
      tagsBin = self.getLooksTagBinForProject(project)
      tagItems = tagsBin.items()
      for tag in tagItems:
        tagsBin.removeItem(tag)
        thumbnailPath = tag.icon()
        try:
          os.remove(thumbnailPath)
        except OSError:
          pass

  def clearLooksThumbnailCache(self):
    """Removes all Look thumbnails from ~/.nuke/Looks/thumbnail dir"""
    filelist = glob.glob(self._lookThumbnailPath + "/*")
    for f in filelist:
      try:
        os.remove(f)
      except:
        print "Unable to remove file %s f"

  def addTagToProjectLooksBin(self, tag, project):
    looksBin = self.getLooksTagBinForProject(project)
    looksBin.addItem(tag)
    self.showTagsBin()

  def showTagsBin(self):
    # Show the Tags Panel
    tagsAction = hiero.ui.findMenuAction("Tags")
    tagsAction.trigger()

  def saveGradeAsLook(self):
    # Only support saving of a single Look
    view = hiero.ui.activeView()
    if not hasattr(view, "selection"):
      return

    selection = view.selection()
    gradeEffects = self.getEffectsFromSelection(selection)

    if len(gradeEffects)==1:
      gradeEffects[0].node() 
      softEffect = gradeEffects[0]
      self.showLookTextDialogForSoftEffect(softEffect)
    else:
      return

  def eventHandler(self, event):
    view = hiero.ui.activeView()
    if not hasattr(view, "selection"):
      return

    selection = view.selection()
    # Only add the Menu if Bins or Sequences are selected (this ensures menu isn't added in the Tags Pane)
    if len(selection) > 0: 
      lookMenu = self._buildLookMenu()
      event.menu.addMenu(lookMenu)

lm = LooksMenu()
cacheMenu = hiero.ui.findMenuAction("foundry.menu.cache")
hiero.ui.insertMenuAction(lm._clearLookThumbnailCacheAction, cacheMenu.menu(), after="Clear Playback Cache")