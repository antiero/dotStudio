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
   
  def populateUI (self, widget, exportTemplate):

    print "POPULATING UI"
    #### BUILD CUSTOM FRAME.IO UI HERE
    layout = QtGui.QFormLayout()
    layout.setContentsMargins(9, 0, 9, 0)

    uploadTypeComboBox = QtGui.QComboBox()
    uploadTypeComboBox.addItem("H.264")
    uploadTypeComboBox.addItem("ProRes 422 HQ")
    uploadTypeComboBox.addItem("Raw Footage")

    self.frameioWidget = FnFrameioDialog(hiero.core.frameioDelegate)

    # Frame.io - Authenticated indicator
    self.frameIOConnectionWidget = QtGui.QWidget()
    self.frameIOConnectionWidgetLayout = QtGui.QHBoxLayout()
    self.frameioAuthenticatedLabel = QtGui.QLabel("Frame.io Session not authenticated")
    self.unconnectedPixmap = QtGui.QPixmap(os.path.join(gIconPath, 'logo-unconnected.png'))
    self.connectedPixmap = QtGui.QPixmap(os.path.join(gIconPath, 'logo-connected.png'))
    self.frameioAuthenticatedLabel.setPixmap(self.unconnectedPixmap)
    self.frameioAuthenticatedLabel.setText("Frame.io Session not authenticated")
    self.frameIOLoginButton = QtGui.QPushButton("LOGIN...")
    self.frameIOLoginButton.setStyleSheet(self.frameioWidget.submitButton.styleSheet())
    self.frameIOLoginButton.setFixedWidth(60)
    self.frameIOLoginButton.clicked.connect(self._frameIOUserDetailsClicked)
    self.frameIOConnectionWidgetLayout.addWidget(self.frameioAuthenticatedLabel)
    self.frameIOConnectionWidgetLayout.addWidget(self.frameIOLoginButton)
    self.frameIOConnectionWidget.setLayout(self.frameIOConnectionWidgetLayout)
    layout.addRow("", self.frameIOConnectionWidget)

    #layout.addRow("", self.frameioWidget.emailLineEdit)
    #layout.addRow("", self.frameioWidget.passwordLineEdit)    
    #layout.addRow("Projects:", frameioWidget.projectDropdown)

    #button = self.frameioWidget.submitButton
    #button.clicked.connect(self.frameioWidget.show)
    #   layout.addRow("", button)
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
    if self.frameioWidget.exec_():
        print self.frameioWidget.projectDropdown.currentText()
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
