import os.path
import PySide.QtCore
import PySide.QtGui

import hiero.ui
import FnFrameioUploadExporter
from FnFrameioUI import FnFrameioWidget

class FrameioUploadExporterUI(hiero.ui.TaskUIBase):
  def __init__(self, preset):
    """Initialize"""
    hiero.ui.TaskUIBase.__init__(self, FnFrameioUploadExporter.FrameioUploadExporter, preset, "Frame.io Uploader")

  def populateUI(self, widget, exportTemplate):
    layout = PySide.QtGui.QFormLayout()
    uploadTypeComboBox = PySide.QtGui.QComboBox()

    uploadTypeComboBox.addItem("H.264")
    uploadTypeComboBox.addItem("ProRes 422 HQ")
    uploadTypeComboBox.addItem("Raw Footage")
    frameioWidget = FnFrameioWidget(hiero.core.frameioDelegate)
    layout.addRow("", frameioWidget.emailLineEdit)
    layout.addRow("", frameioWidget.passwordLineEdit)    
    layout.addRow("Upload Type:", uploadTypeComboBox)
    widget.setLayout(layout)

    return widget

hiero.ui.taskUIRegistry.registerTaskUI(FnFrameioUploadExporter.FrameioUploadPreset, FrameioUploadExporterUI)