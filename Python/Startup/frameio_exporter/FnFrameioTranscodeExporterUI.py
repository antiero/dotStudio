# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import hiero.ui

from PySide import QtCore
from PySide import QtGui
import FnFrameioTranscodeExporter

from hiero.ui.FnUIProperty import *
from hiero.exporters import FnExternalRenderUI
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
        self.frameIOLoginLogoutButton.setText("LOGOUT...")
        self.frameIOConnectionStatusLabel.setText("Frame.io connected (%s)" % username)
    else:
        self.frameIOLoginLogoutButton.setText("LOGIN...")
        self.frameIOConnectionStatusLabel.setText("Please login to Frame.io")

  def populateUI (self, widget, exportTemplate):

    print "POPULATING FRAME.IO UI"

    #### BUILD CUSTOM FRAME.IO UI HERE
    layout = QtGui.QFormLayout()
    layout.setContentsMargins(9, 0, 9, 0)

    uploadTypeComboBox = QtGui.QComboBox()
    uploadTypeComboBox.addItem("H.264")
    uploadTypeComboBox.addItem("ProRes 422 HQ")
    uploadTypeComboBox.addItem("Raw Footage")

    self.frameioWidget = hiero.core.frameioDelegate.frameioMainViewController

    # Frame.io - Authenticated indicator
    self.frameIOConnectionWidget = QtGui.QWidget()
    self.frameIOConnectionWidgetLayout = QtGui.QHBoxLayout()

    self.frameIOLoginLogoutButton = QtGui.QPushButton("LOGIN...")
    self.frameIOLoginLogoutButton.clicked.connect(self._frameIOUserDetailsClicked)
    self.frameIOConnectionStatusLabel = QtGui.QLabel("Not connected")



    self.frameIOConnectionWidgetLayout.addWidget(self.frameIOConnectionStatusLabel)
    self.frameIOConnectionWidgetLayout.addWidget(self.frameIOLoginLogoutButton)

    self.updateFrameIOLoginUI()

    self.frameIOConnectionWidget.setLayout(self.frameIOConnectionWidgetLayout)
    layout.addRow("Frame.io Connection Status:", self.frameIOConnectionWidget)

    self.frameioWidget.updateConnectionIndicator()

    self.frameIOUploadSourceCheckbox = QtGui.QCheckBox()
    layout.addRow("Upload source QuickTime Clips?:", self.frameIOUploadSourceCheckbox)
    layout.addRow("Upload Type:", uploadTypeComboBox)    
    self.buildCodecUI(layout, includeAuxProperties=True)
    
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
      burninCheckbox.setCheckState(QtCore.Qt.Checked)
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
      additionalNodesCheckbox.setCheckState(QtCore.Qt.Checked)
    additionalNodesButton = QtGui.QPushButton("Edit")
    additionalNodesButton.setToolTip(additionalNodesToolTip)
    additionalNodesButton.clicked.connect(self._additionalNodesEditClicked)
    additionalNodesLayout.addWidget(additionalNodesCheckbox)
    additionalNodesLayout.addWidget(additionalNodesButton)
    layout.addRow("Additional Nodes:", additionalNodesLayout)
    widget.setLayout(layout)

    
  def _frameIOUserDetailsClicked(self):
    #dialog = FnAdditionalNodesDialog.AdditionalNodesDialog(self._preset.properties()["additionalNodesData"], self._tags)
    #if dialog.exec_():
    print "Show the Frame.io login"
    if self.frameIOLoginLogoutButton.text() == "LOGIN...":
        if self.frameioWidget.exec_():
            currentProject = self.frameioWidget.projectDropdown.currentText()
            print "The Current Project was: " + currentProject
            self._preset.properties()["frameio_project"] = currentProject

    else:
        hiero.core.frameioDelegate.disconnectCurrentSession()
    pass

  def _additionalNodesEnableClicked(self, state):
    self._preset.properties()["additionalNodesEnabled"] = state == QtCore.Qt.Checked
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
