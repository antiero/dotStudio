# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import hiero.ui

from PySide.QtCore import Qt
from PySide import QtGui
import FnFrameioTranscodeExporter

from hiero.ui.FnUIProperty import *
from hiero.exporters import FnExternalRenderUI, FnAdditionalNodesDialog
from FnFrameioUI import FnFrameioDialog, gIconPath

class FrameioTranscodeExporterUI(FnExternalRenderUI.NukeRenderTaskUI):
  def __init__(self, preset):
    """Initialize"""
    #super(FrameioTranscodeExporterUI, self).__init__(preset)
    FnExternalRenderUI.NukeRenderTaskUI.__init__(self, preset, FnFrameioTranscodeExporter.FrameioTranscodeExporter, "FrameIO Upload")
    self._tags = []
    self.frameIOLoginLogoutButton = None

    # This tells the authentication indicator to update when the status changes
    print "Registering event"
    hiero.core.events.registerInterest("kFrameioConnectionChanged", self.handleConnectionStatusChangeEvent)


  def handleConnectionStatusChangeEvent(self, event):
    if self.frameIOLoginLogoutButton:
        self.updateFrameIOLoginUI()

  def updateFrameIOLoginUI(self):
    if hiero.core.frameioDelegate.frameioSession.sessionAuthenticated:
        username = hiero.core.frameioDelegate.username
        self.frameIOLoginLogoutButton.setText("Logout...")
        self.frameIOConnectionStatusLabel.setText("Connected (%s)" % username)
        self._updateProjectComboBox()
        self._preset.properties()["frameio_project"] = self.projectComboBox.currentText()
    else:
        self.frameIOLoginLogoutButton.setText("Login...")
        self.frameIOConnectionStatusLabel.setText("Unconnected")

  def populateUI (self, widget, exportTemplate):
    #### BUILD CUSTOM FRAME.IO UI HERE
    layout = QtGui.QFormLayout()
    layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
    layout.setContentsMargins(9, 0, 9, 0)

    
    self.frameioWidget = hiero.core.frameioDelegate.frameioMainViewController

    # This diaog behaves differently in the Export dialog or Bin View
    self.frameioWidget.usingExportDialog = True

    self.projectComboBox = QtGui.QComboBox()
    self.projectComboBox.addItem("Please login to Frame.io")
    self.projectComboBox.currentIndexChanged.connect(self.projectDropdownChanged)


    # Frame.io - Authenticated indicator
    self.frameIOConnectionWidget = QtGui.QWidget()
    self.frameIOConnectionWidgetLayout = QtGui.QHBoxLayout()

    self.frameIOLoginLogoutButton = QtGui.QPushButton("Login...")
    self.frameIOLoginLogoutButton.clicked.connect(self._frameIOUserDetailsClicked)
    self.frameIOConnectionStatusLabel = QtGui.QLabel("Not connected")

    self.frameIOConnectionWidgetLayout.addWidget(self.frameIOConnectionStatusLabel)
    self.frameIOConnectionWidgetLayout.addWidget(self.frameIOLoginLogoutButton)

    self.updateFrameIOLoginUI()

    self.frameIOConnectionWidget.setLayout(self.frameIOConnectionWidgetLayout)
    layout.addRow("", self.frameIOConnectionWidget)
    layout.addRow("Project: ", self.projectComboBox)

    self.buildCodecUI(layout, includeAuxProperties=False)
    self._codecTypeComboBox.setHidden(True)
    layout.labelForField(self._codecTypeComboBox).hide()
    
    retimeToolTip = """Sets the retime method used if retimes are enabled.\n-Motion - Motion Estimation.\n-Blend - Frame Blending.\n-Frame - Nearest Frame"""
    key, value = "method", ("None", "Motion", "Frame", "Blend")
    uiProperty = UIPropertyFactory.create(type(value), key=key, value=value, dictionary=self._preset._properties, label="Retime Method", tooltip=retimeToolTip)
    self._uiProperties.append(uiProperty)
    layout.addRow(uiProperty._label + ":", uiProperty)
   
    burninToolTip = """When enabled, a text burn-in is applied to the media using a Nuke Gizmo.\nClick Edit to define the information applied during burn-in. Burn-in fields accept any combination of dropdown tokens and custom text, for example {clip}_myEdit.\nYou can also include Nuke expression syntax, for example [metadata input/ctime], will add the creation time metadata in the Nuke stream."""

    burninLayout = QtGui.QHBoxLayout()  
    burninCheckbox = QtGui.QCheckBox()
    burninCheckbox.setToolTip(burninToolTip)
    burninCheckbox.stateChanged.connect(self._burninEnableClicked)
    if self._preset.properties()["burninDataEnabled"]:
      burninCheckbox.setCheckState(Qt.Checked)
    burninButton = QtGui.QPushButton("Edit")
    burninButton.setToolTip(burninToolTip)
    burninButton.clicked.connect(self._burninEditClicked)
    burninLayout.addWidget(burninCheckbox)
    burninLayout.addWidget(burninButton)    
    layout.addRow("Burn-in Gizmo", burninLayout)
      
    additionalNodesToolTip = """When enabled, allows custom Nuke nodes to be added into Nuke Scripts.\n Click Edit to add nodes on a per Shot, Track or Sequence basis.\n Additional Nodes can also optionally be filtered by Tag."""

    additionalNodesLayout = QtGui.QHBoxLayout()
    additionalNodesCheckbox = QtGui.QCheckBox()
    additionalNodesCheckbox.setToolTip(additionalNodesToolTip)
    additionalNodesCheckbox.stateChanged.connect(self._additionalNodesEnableClicked)
    if self._preset.properties()["additionalNodesEnabled"]:
      additionalNodesCheckbox.setCheckState(Qt.Checked)
    additionalNodesButton = QtGui.QPushButton("Edit")
    additionalNodesButton.setToolTip(additionalNodesToolTip)
    additionalNodesButton.clicked.connect(self._additionalNodesEditClicked)
    additionalNodesLayout.addWidget(additionalNodesCheckbox)
    additionalNodesLayout.addWidget(additionalNodesButton)
    layout.addRow("Additional Nodes:", additionalNodesLayout)

    try:
        self._codecWidget.setHidden(True)
    except:
        pass

    widget.setLayout(layout)
    #widget.setStyleSheet(self.frameioWidget.styleSheet())


  def _updateProjectComboBox(self):
    """Updates the project dropdown menu with projects from the Authenticated session"""
    projects = hiero.core.frameioDelegate.frameioSession.projectdict().values()
    print "updating the project list with projects: %s" % str(projects)
    self.projectComboBox.clear()
    for project in projects:
        self.projectComboBox.addItem(str(project))


  def projectDropdownChanged(self, index):
    """Called when the Project dropdown changes"""
    self._preset.properties()["frameio_project"] = self.projectComboBox.currentText()

    
  def _frameIOUserDetailsClicked(self):
    if self.frameIOLoginLogoutButton.text() == "Login...":
        if self.frameioWidget.exec_():

            if not hiero.core.frameioDelegate.frameioSession.sessionAuthenticated:
                self.frameioWidget.showLoginView()
            else:
                self.frameioWidget.showUploadView()
    else:
        hiero.core.frameioDelegate.disconnectCurrentSession()
    pass

  def _additionalNodesEnableClicked(self, state):
    self._preset.properties()["additionalNodesEnabled"] = state == Qt.Checked
    pass
    
  def _additionalNodesEditClicked(self):
    dialog = FnAdditionalNodesDialog.AdditionalNodesDialog(self._preset.properties()["additionalNodesData"], self._tags)
    if dialog.exec_():
      self._preset.properties()["additionalNodesData"] = dialog.data()
    pass
        
  def setTags ( self, tags ):
    """setTags passes the subset of tags associated with the selection for export"""
    self._tags = tags    

hiero.ui.taskUIRegistry.registerTaskUI(FnFrameioTranscodeExporter.FrameioTranscodePreset, FrameioTranscodeExporterUI)
