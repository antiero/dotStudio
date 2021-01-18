# PDF Exporter Task UI
# PDF image export task which can be used via the Export dialog via Sequence Processor
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets
import hiero.ui
from hiero.ui.FnTaskUIFormLayout import TaskUIFormLayout
import AnPdfExportTask
from AnPdfExporter import PDFExporter

class PdfExportUI(hiero.ui.TaskUIBase):

  def __init__(self, preset):
    """Initialize"""
    hiero.ui.TaskUIBase.__init__(self, AnPdfExportTask.PdfExportTask, preset, "PDF Exporter")
  
  def customOffsetTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._customFrameLineEdit.text()
    self._preset.properties()["customFrameOffset"] = unicode(value)

  def frameTypeComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._frameTypeComboBox.currentText()
    self._preset.properties()["thumbnailFrameType"] = unicode(value)    

  def pageLayoutComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._pdfPageLayoutComboBox.currentText()

    self._preset.properties()["pageLayoutType"] = unicode(value)

  def populateUI(self, widget, exportTemplate):
    layout = widget.layout()

    formLayout = TaskUIFormLayout()
    layout.addLayout(formLayout)

    # Thumb frame type layout
    thumbFrameLayout = QtWidgets.QHBoxLayout()
    self._frameTypeComboBox = QtWidgets.QComboBox()    
    self._frameTypeComboBox.setToolTip("Specify the frame from which to pick the thumbnail.")

    self._pdfLayouts = PDFExporter.PAGE_LAYOUTS_DICT
    self._thumbFrameTypes = PDFExporter.THUMB_FRAME_TYPES

    for index, item in zip(range(0,len(self._thumbFrameTypes)), self._thumbFrameTypes):
      self._frameTypeComboBox.addItem(item)
      if item == str(self._preset.properties()["thumbnailFrameType"]):
        self._frameTypeComboBox.setCurrentIndex(index)

    self._frameTypeComboBox.setMaximumWidth(80)
    thumbFrameLayout.addWidget(self._frameTypeComboBox, QtCore.Qt.AlignLeft)

    self._pdfPageLayoutComboBox = QtWidgets.QComboBox()
    self._pdfPageLayoutComboBox.setMaximumWidth(115)
    self._pdfPageLayoutComboBox.setToolTip("This determines the layout of the PDF")

    for index, item in zip(range(0,len(self._pdfLayouts)), self._pdfLayouts):
      self._pdfPageLayoutComboBox.addItem(item)
      if item == str(self._preset.properties()["pageLayoutType"]):
        self._pdfPageLayoutComboBox.setCurrentIndex(index)

    self._pdfPageLayoutComboBox.currentIndexChanged.connect(self.pageLayoutComboBoxChanged)
    self.pageLayoutComboBoxChanged(0)
    self._frameTypeComboBox.currentIndexChanged.connect(self.frameTypeComboBoxChanged)
    self.frameTypeComboBoxChanged(0) # Trigger to make it set the enabled state correctly
    
    formLayout.addRow("Frame Type:",thumbFrameLayout)
    formLayout.addRow("Layout:",self._pdfPageLayoutComboBox)  

hiero.ui.taskUIRegistry.registerTaskUI(AnPdfExportTask.PdfExportPreset, PdfExportUI)