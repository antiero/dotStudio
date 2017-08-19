# Pdf Exporter Task UI
# Pdf image export task which can be used via the Export dialog via Shot, Clip or Sequence Processor
# To install copy the PdfExportTask.py and PdfExportTaskUI.py to your <HIERO_PATH>/Python/Startup directory.
# Keyword tokens exist for: 
# {frametype} - Position where the thumbnail was taken from (first/middle/last/custom)
# {srcframe} - The frame number of the original source clip file used for thumbnail
# {dstframe} - The destination frame (timeline time) number used for the thumbnail
# Antony Nasce, v1.0, 13/10/13

import PySide.QtCore
import PySide.QtGui
import hiero.ui
import FnPdfExportTask

class PdfExportUI(hiero.ui.TaskUIBase):

  kFirstFrame = "First"
  kMiddleFrame = "Middle"
  kLastFrame = "Last"
  kCustomFrame = "Custom"

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

  def widthTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._widthBox.text()
    self._preset.properties()["width"] = unicode(value)

  def heightTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._heightBox.text()
    self._preset.properties()["height"] = unicode(value)

  def frameTypeComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._frameTypeComboBox.currentText()
    if str(value) == self.kCustomFrame:
      self._customFrameLineEdit.setEnabled(True)
      self._preset.properties()["customFrameOffset"] = unicode(self._customFrameLineEdit.text())
    else:
      self._customFrameLineEdit.setEnabled(False)
    self._preset.properties()["frameType"] = unicode(value)    

  def thumbSizeComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state
    
    value = self._thumbSizeComboBox.currentText()
    if value == "Default":
      self._widthBox.setEnabled(False)
      self._wLabel.setEnabled(False)      
      self._heightBox.setEnabled(False)
      self._hLabel.setEnabled(False)
    elif value == "To Box":
      self._widthBox.setEnabled(True)
      self._heightBox.setEnabled(True)
      self._wLabel.setEnabled(True)
      self._hLabel.setEnabled(True)
    elif value == "Scaled to Width":
      self._widthBox.setEnabled(True)
      self._wLabel.setEnabled(True)
      self._heightBox.setEnabled(False)
      self._hLabel.setEnabled(False)      
    elif value == "Scaled to Height":
      self._widthBox.setEnabled(False)
      self._wLabel.setEnabled(False)
      self._heightBox.setEnabled(True)
      self._hLabel.setEnabled(True)

    self._preset.properties()["thumbSize"] = unicode(value)

  def populateUI(self, widget, exportTemplate):
    layout = PySide.QtWidgets.QFormLayout()
    layout.setContentsMargins(9, 0, 9, 0)
    widget.setLayout(layout)

    # Thumb frame type layout
    thumbFrameLayout = PySide.QtWidgets.QHBoxLayout()
    self._frameTypeComboBox = PySide.QtWidgets.QComboBox()    
    self._frameTypeComboBox.setToolTip("Specify the frame from which to pick the thumbnail.\nCustom allows you to specify a custom frame offset, relative from the first frame.")

    thumbFrameTypes = (self.kFirstFrame, self.kMiddleFrame, self.kLastFrame, self.kCustomFrame)
    for index, item in zip(range(0,len(thumbFrameTypes)), thumbFrameTypes):
      self._frameTypeComboBox.addItem(item)
      if item == str(self._preset.properties()["frameType"]):
        self._frameTypeComboBox.setCurrentIndex(index)

    self._frameTypeComboBox.setMaximumWidth(80)

    self._customFrameLineEdit = PySide.QtWidgets.QLineEdit()
    self._customFrameLineEdit.setEnabled(False)
    self._customFrameLineEdit.setToolTip("This is the frame offset from the first frame of the shot/sequence")
    self._customFrameLineEdit.setValidator(PySide.QtGui.QIntValidator())
    self._customFrameLineEdit.setMaximumWidth(80);
    self._customFrameLineEdit.setText(str(self._preset.properties()["customFrameOffset"]))

    thumbFrameLayout.addWidget(self._frameTypeComboBox, PySide.QtCore.Qt.AlignLeft)
    thumbFrameLayout.addWidget(self._customFrameLineEdit, PySide.QtCore.Qt.AlignLeft)
    #thumbFrameLayout.addStretch()

    # QImage save format type
    self._formatComboBox = PySide.QtWidgets.QComboBox()
    thumbFrameTypes = ("png", "jpg", "tiff", "bmp")
    for index, item in zip(range(0,len(thumbFrameTypes)), thumbFrameTypes):
      self._formatComboBox.addItem(item)
      if item == str(self._preset.properties()["format"]):
        self._formatComboBox.setCurrentIndex(index)

    self._formatComboBox.currentIndexChanged.connect(self.formatComboBoxChanged)
    

    # QImage save height
    # Thumb frame type layout
    thumbSizeLayout = PySide.QtWidgets.QHBoxLayout()

    self._thumbSizeComboBox = PySide.QtWidgets.QComboBox()
    self._thumbSizeComboBox.setMaximumWidth(115)
    self._thumbSizeComboBox.setToolTip("This determines the size of the thumbnail.\nLeave as Default to use Hiero's internal thumbnail size or specify a box or width/height scaling in pixels.")
    thumbSizeTypes = ("Default","To Box", "Scaled to Width", "Scaled to Height")
    for index, item in zip(range(0,len(thumbSizeTypes)), thumbSizeTypes):
      self._thumbSizeComboBox.addItem(item)
      if item == str(self._preset.properties()["thumbSize"]):
        self._thumbSizeComboBox.setCurrentIndex(index)

    thumbSizeLayout.addWidget(self._thumbSizeComboBox)
    self._wLabel = PySide.QtWidgets.QLabel('w:')
    self._wLabel.setFixedWidth(12)    
    thumbSizeLayout.addWidget(self._wLabel,PySide.QtCore.Qt.AlignLeft)
    self._widthBox = PySide.QtWidgets.QLineEdit()
    self._widthBox.setToolTip("PDF width in pixels")
    self._widthBox.setEnabled(False)
    self._widthBox.setValidator(PySide.QtGui.QIntValidator())
    self._widthBox.setMaximumWidth(40)
    self._widthBox.setText(str(self._preset.properties()["width"]))  
    self._widthBox.textChanged.connect(self.widthTextChanged)  
    thumbSizeLayout.addWidget(self._widthBox,PySide.QtCore.Qt.AlignLeft)

    self._hLabel = PySide.QtWidgets.QLabel('h:')
    self._hLabel.setFixedWidth(12)
    thumbSizeLayout.addWidget(self._hLabel,PySide.QtCore.Qt.AlignLeft)
    self._heightBox = PySide.QtWidgets.QLineEdit()
    self._heightBox.setToolTip("PDF height in pixels")
    self._heightBox.setEnabled(False)
    self._heightBox.setValidator(PySide.QtGui.QIntValidator())
    self._heightBox.setMaximumWidth(40)
    self._heightBox.setText(str(self._preset.properties()["height"]))
    self._heightBox.textChanged.connect(self.heightTextChanged)    
    thumbSizeLayout.addWidget(self._heightBox,PySide.QtCore.Qt.AlignLeft)

    self._thumbSizeComboBox.currentIndexChanged.connect(self.thumbSizeComboBoxChanged)
    self.thumbSizeComboBoxChanged(0)
    self._frameTypeComboBox.currentIndexChanged.connect(self.frameTypeComboBoxChanged)
    self.frameTypeComboBoxChanged(0) # Trigger to make it set the enabled state correctly
    self._customFrameLineEdit.textChanged.connect(self.customOffsetTextChanged)
    
    layout.addRow("Frame Type:",thumbFrameLayout)
    layout.addRow("Size:",thumbSizeLayout)
    layout.addRow("File Type:",self._formatComboBox)    

hiero.ui.taskUIRegistry.registerTaskUI(FnPdfExportTask.PdfExportPreset, PdfExportUI)