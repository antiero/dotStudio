# PDF Exporter Task UI
# PDF image export task which can be used via the Export dialog via Sequence Processor
import PySide.QtCore
import PySide.QtGui
import hiero.ui
import FnPdfExportTask
from FnPdfExporter import PDFExporter

class PdfExportUI(hiero.ui.TaskUIBase):

  def __init__(self, preset):
    """Initialize"""
    hiero.ui.TaskUIBase.__init__(self, FnPdfExportTask.PdfExportTask, preset, "PDF Exporter")

  def formatComboBoxChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._formatComboBox.currentText()
    self._preset.properties()["format"] = unicode(value)
  
  def customOffsetTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._customFrameLineEdit.text()
    self._preset.properties()["customFrameOffset"] = unicode(value)

  def frameTypeComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._frameTypeComboBox.currentText()

    """ UNUSED for CUSTOM frame
    if str(value) == self.kCustomFrame:
      self._customFrameLineEdit.setEnabled(True)
      self._preset.properties()["customFrameOffset"] = unicode(self._customFrameLineEdit.text())
    else:
      self._customFrameLineEdit.setEnabled(False)"""

    self._preset.properties()["thumbnailFrameType"] = unicode(value)    

  def pageLayoutComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._pdfPageLayoutComboBox.currentText()

    self._preset.properties()["pageLayoutType"] = unicode(value)

  def populateUI(self, widget, exportTemplate):
    layout = PySide.QtGui.QFormLayout()
    layout.setContentsMargins(9, 0, 9, 0)
    widget.setLayout(layout)

    # Thumb frame type layout
    thumbFrameLayout = PySide.QtGui.QHBoxLayout()
    self._frameTypeComboBox = PySide.QtGui.QComboBox()    
    self._frameTypeComboBox.setToolTip("Specify the frame from which to pick the thumbnail.")

    self._pdfLayouts = PDFExporter.PAGE_LAYOUTS_DICT
    self._thumbFrameTypes = PDFExporter.THUMB_FRAME_TYPES

    for index, item in zip(range(0,len(self._thumbFrameTypes)), self._thumbFrameTypes):
      self._frameTypeComboBox.addItem(item)
      if item == str(self._preset.properties()["thumbnailFrameType"]):
        self._frameTypeComboBox.setCurrentIndex(index)

    self._frameTypeComboBox.setMaximumWidth(80)

    """self._customFrameLineEdit = PySide.QtGui.QLineEdit()
    self._customFrameLineEdit.setEnabled(False)
    self._customFrameLineEdit.setToolTip("This is the frame offset from the first frame of the shot/sequence")
    self._customFrameLineEdit.setValidator(PySide.QtGui.QIntValidator())
    self._customFrameLineEdit.setMaximumWidth(80)

    self._customFrameLineEdit.setText(str(self._preset.properties()["customFrameOffset"]))"""

    thumbFrameLayout.addWidget(self._frameTypeComboBox, PySide.QtCore.Qt.AlignLeft)
    #thumbFrameLayout.addWidget(self._customFrameLineEdit, PySide.QtCore.Qt.AlignLeft)

    self._pdfPageLayoutComboBox = PySide.QtGui.QComboBox()
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
    #self._customFrameLineEdit.textChanged.connect(self.customOffsetTextChanged)
    
    layout.addRow("Frame Type:",thumbFrameLayout)
    layout.addRow("Layout:",self._pdfPageLayoutComboBox)
    layout.addRow("File Type:",self._formatComboBox)    

hiero.ui.taskUIRegistry.registerTaskUI(FnPdfExportTask.PdfExportPreset, PdfExportUI)