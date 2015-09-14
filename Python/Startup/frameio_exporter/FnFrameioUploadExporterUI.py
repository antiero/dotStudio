import os.path
import PySide.QtCore
import PySide.QtGui

import hiero.ui
import FnFrameioUploadExporter


class FrameioUploadExporterUI(hiero.ui.TaskUIBase):
  def __init__(self, preset):
    """Initialize"""
    hiero.ui.TaskUIBase.__init__(self, FnFrameioUploadExporter.FrameioUploadExporter, preset, "Frame.io Uploader")

  def populateUI(self, widget, exportTemplate):
    layout = PySide.QtGui.QFormLayout()
    uploadPartsCheckBox = PySide.QtGui.QCheckBox()
    layout.addRow("Upload Raw Footage (no transcoding)", uploadPartsCheckBox)
    widget.setLayout(layout)
    return widget

hiero.ui.taskUIRegistry.registerTaskUI(FnFrameioUploadExporter.FrameioUploadPreset, FrameioUploadExporterUI)