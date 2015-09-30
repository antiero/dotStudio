# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import hiero.ui

import PySide.QtCore
import PySide.QtGui
import FnTranscodeExporter
import FnExternalRenderUI
import FnAdditionalNodesDialog

from hiero.ui.FnUIProperty import *

class TranscodeExporterUI(FnExternalRenderUI.NukeRenderTaskUI):
  def __init__(self, preset):
    """Initialize"""
    FnExternalRenderUI.NukeRenderTaskUI.__init__(self, preset, FnTranscodeExporter.TranscodeExporter, "Transcode Images")
    self._tags = []
   
  def populateUI (self, widget, exportTemplate):
    layout = PySide.QtGui.QFormLayout()
    layout.setContentsMargins(9, 0, 9, 0)
    self.buildCodecUI(layout, includeAuxProperties=True)
    
    retimeToolTip = """Sets the retime method used if retimes are enabled.\n-Motion - Motion Estimation.\n-Blend - Frame Blending.\n-Frame - Nearest Frame"""
    key, value = "method", ("None", "Motion", "Frame", "Blend")
    uiProperty = UIPropertyFactory.create(type(value), key=key, value=value, dictionary=self._preset._properties, label="Retime Method", tooltip=retimeToolTip)
    self._uiProperties.append(uiProperty)
    layout.addRow(uiProperty._label + ":", uiProperty)
   
    # create checkbox for whether the EDL task should add Absolute Paths
    keepNukeScriptCheckbox = PySide.QtGui.QCheckBox()
    keepNukeScriptCheckbox.setCheckState(PySide.QtCore.Qt.Unchecked)
    if self._preset.properties()["keepNukeScript"]:
      keepNukeScriptCheckbox.setCheckState(PySide.QtCore.Qt.Checked)    
    keepNukeScriptCheckbox.stateChanged.connect(self.keepNukeScriptCheckboxChanged)
    keepNukeScriptCheckbox.setToolTip("A Nuke script is created for each transcode. If you'd like to keep the temporary .nk file from being destroyed, enable this option. The script will get generated into the same directory as the transcode output")
    layout.addRow("Keep Nuke Script", keepNukeScriptCheckbox)

    burninToolTip = """When enabled, a text burn-in is applied to the media using a Nuke Gizmo.\nClick Edit to define the information applied during burn-in. Burn-in fields accept any combination of dropdown tokens and custom text, for example {clip}_myEdit.\nYou can also include Nuke expression syntax, for example [metadata input/ctime], will add the creation time metadata in the Nuke stream."""

    burninLayout = PySide.QtGui.QHBoxLayout()  
    burninCheckbox = PySide.QtGui.QCheckBox()
    burninCheckbox.setToolTip(burninToolTip)
    burninCheckbox.stateChanged.connect(self._burninEnableClicked)
    if self._preset.properties()["burninDataEnabled"]:
      burninCheckbox.setCheckState(PySide.QtCore.Qt.Checked)
    burninButton = PySide.QtGui.QPushButton("Edit")
    burninButton.setToolTip(burninToolTip)
    burninButton.clicked.connect(self._burninEditClicked)
    burninLayout.addWidget(burninCheckbox)
    burninLayout.addWidget(burninButton)    
    layout.addRow("Burn-in Gizmo", burninLayout)
      
    additionalNodesToolTip = """When enabled, allows custom Nuke nodes to be added into Nuke Scripts.\n Click Edit to add nodes on a per Shot, Track or Sequence basis.\n Additional Nodes can also optionally be filtered by Tag."""

    additionalNodesLayout = PySide.QtGui.QHBoxLayout()
    additionalNodesCheckbox = PySide.QtGui.QCheckBox()
    additionalNodesCheckbox.setToolTip(additionalNodesToolTip)
    additionalNodesCheckbox.stateChanged.connect(self._additionalNodesEnableClicked)
    if self._preset.properties()["additionalNodesEnabled"]:
      additionalNodesCheckbox.setCheckState(PySide.QtCore.Qt.Checked)
    additionalNodesButton = PySide.QtGui.QPushButton("Edit")
    additionalNodesButton.setToolTip(additionalNodesToolTip)
    additionalNodesButton.clicked.connect(self._additionalNodesEditClicked)
    additionalNodesLayout.addWidget(additionalNodesCheckbox)
    additionalNodesLayout.addWidget(additionalNodesButton)
    layout.addRow("Additional Nodes:", additionalNodesLayout)


    widget.setLayout(layout)


  def _additionalNodesEnableClicked(self, state):
    self._preset.properties()["additionalNodesEnabled"] = state == PySide.QtCore.Qt.Checked
    pass
    
  def _additionalNodesEditClicked(self):
    dialog = FnAdditionalNodesDialog.AdditionalNodesDialog(self._preset.properties()["additionalNodesData"], self._tags)
    if dialog.exec_():
      self._preset.properties()["additionalNodesData"] = dialog.data()
    pass
        
  def setTags ( self, tags ):
    """setTags passes the subset of tags associated with the selection for export"""
    self._tags = tags


hiero.ui.taskUIRegistry.registerTaskUI(FnTranscodeExporter.TranscodePreset, TranscodeExporterUI)
