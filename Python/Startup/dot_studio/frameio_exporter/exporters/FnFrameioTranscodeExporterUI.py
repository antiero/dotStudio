# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import hiero.ui

from PySide.QtCore import Qt
from PySide2 import QtGui
import FnFrameioTranscodeExporter

from hiero.ui.FnUIProperty import *
from hiero.exporters import FnExternalRenderUI, FnAdditionalNodesDialog
from frameio_exporter.ui.FnFrameioUI import FnFrameioDialog

import nuke

class FrameioTranscodeExporterUI(FnExternalRenderUI.NukeRenderTaskUI):
  def __init__(self, preset):
    """Initialize"""
    #super(FrameioTranscodeExporterUI, self).__init__(preset)
    FnExternalRenderUI.NukeRenderTaskUI.__init__(self, preset, FnFrameioTranscodeExporter.FrameioTranscodeExporter, "FrameIO Upload")
    self._tags = []
    self.frameIOLoginLogoutButton = None

    # For now, the uploader will only handle QuickTime Movie
    self._preset.properties()["frameio_project"] = "mov"

    # This tells the authentication indicator to update when the status changes
    hiero.core.events.registerInterest("kFrameioConnectionChanged", self.handleConnectionStatusChangeEvent)


  def handleConnectionStatusChangeEvent(self, event):
    if self.frameIOLoginLogoutButton:
        self.updateFrameIOLoginUI()

  def updateFrameIOLoginUI(self):
    if not nuke.frameioDelegate.frameioMainViewController.usingExportDialog:
        return

    if nuke.frameioDelegate.frameioSession.sessionHasValidCredentials:
        username = nuke.frameioDelegate.username
        self.frameIOLoginLogoutButton.setText("Logout...")
        self.frameIOConnectionStatusLabel.setText("Connected (%s)" % username)
        self._updateProjectComboBox()
        self._preset.properties()["frameio_project"] = self.projectComboBox.currentText()
    else:
        self.frameIOLoginLogoutButton.setText("Login...")
        self.frameIOConnectionStatusLabel.setText("Unconnected")

  def populateUI (self, widget, exportTemplate):
    #### BUILD CUSTOM FRAME.IO UI HERE
    layout = QtWidgets.QFormLayout()
    layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
    layout.setContentsMargins(9, 0, 9, 0)

    
    self.frameioWidget = nuke.frameioDelegate.frameioMainViewController

    # This diaog behaves differently in the Export dialog or Bin View
    self.frameioWidget.usingExportDialog = True

    self.projectComboBox = QtWidgets.QComboBox()
    self.projectComboBox.addItem("Please login to Frame.io")
    self.projectComboBox.currentIndexChanged.connect(self.projectDropdownChanged)


    # Frame.io - Authenticated indicator
    self.frameIOConnectionWidget = QtWidgets.QWidget()
    self.frameIOConnectionWidgetLayout = QtWidgets.QHBoxLayout()

    self.frameIOLoginLogoutButton = QtWidgets.QPushButton("Login...")
    self.frameIOLoginLogoutButton.clicked.connect(self._frameIOUserDetailsClicked)
    self.frameIOConnectionStatusLabel = QtWidgets.QLabel("Not connected")

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

    burninLayout = QtWidgets.QHBoxLayout()  
    burninCheckbox = QtGui.QCheckBox()
    burninCheckbox.setToolTip(burninToolTip)
    burninCheckbox.stateChanged.connect(self._burninEnableClicked)
    if self._preset.properties()["burninDataEnabled"]:
      burninCheckbox.setCheckState(Qt.Checked)
    burninButton = QtWidgets.QPushButton("Edit")
    burninButton.setToolTip(burninToolTip)
    burninButton.clicked.connect(self._burninEditClicked)
    burninLayout.addWidget(burninCheckbox)
    burninLayout.addWidget(burninButton)    
    layout.addRow("Burn-in Gizmo", burninLayout)
      
    additionalNodesToolTip = """When enabled, allows custom Nuke nodes to be added into Nuke Scripts.\n Click Edit to add nodes on a per Shot, Track or Sequence basis.\n Additional Nodes can also optionally be filtered by Tag."""

    additionalNodesLayout = QtWidgets.QHBoxLayout()
    additionalNodesCheckbox = QtGui.QCheckBox()
    additionalNodesCheckbox.setToolTip(additionalNodesToolTip)
    additionalNodesCheckbox.stateChanged.connect(self._additionalNodesEnableClicked)
    if self._preset.properties()["additionalNodesEnabled"]:
      additionalNodesCheckbox.setCheckState(Qt.Checked)
    additionalNodesButton = QtWidgets.QPushButton("Edit")
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
    projects = nuke.frameioDelegate.frameioSession.projectdict().values()
    self.projectComboBox.clear()
    for project in projects:
        self.projectComboBox.addItem(str(project))


  def projectDropdownChanged(self, index):
    """Called when the Project dropdown changes"""
    self._preset.properties()["frameio_project"] = self.projectComboBox.currentText()

    
  def _frameIOUserDetailsClicked(self):
    if self.frameIOLoginLogoutButton.text() == "Login...":
        if self.frameioWidget.exec_():

            if not nuke.frameioDelegate.frameioSession.sessionHasValidCredentials:
                self.frameioWidget.showLoginView()
            else:
                self.frameioWidget.showUploadView()
    else:
        nuke.frameioDelegate.disconnectCurrentSession()
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
