# Thumbnail Exporter Task UI
# Thumbnail image export task which can be used via the Export dialog via Shot, Clip or Sequence Processor
# To install copy the ThumbnailExportTask.py and ThumbnailExportTaskUI.py to your <HIERO_PATH>/Python/Startup directory.
# Keyword tokens exist for:
# {frametype} - Position where the thumbnail was taken from (first/middle/last/custom)
# {srcframe} - The frame number of the original source clip file used for thumbnail
# {dstframe} - The destination frame (timeline time) number used for the thumbnail
# Antony Nasce, v1.0, 13/10/13
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets
import hiero.ui
from hiero.ui.FnTaskUIFormLayout import TaskUIFormLayout
import ThumbnailExportTask
import os.path

from PySide2 import QtWidgets

class ThumbnailExportUI(hiero.ui.TaskUIBase):

  kFirstFrame = "First"
  kMiddleFrame = "Middle"
  kLastFrame = "Last"
  kCustomFrame = "Custom"

  def __init__(self, preset):
    """Initialize"""
    hiero.ui.TaskUIBase.__init__(self, ThumbnailExportTask.ThumbnailExportTask, preset, "Thumbnail Exporter")

  def formatComboBoxChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._formatComboBox.currentText()
    self._preset.properties()["format"] = str(value)

  def customOffsetTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._customFrameLineEdit.text()
    self._preset.properties()["customFrameOffset"] = str(value)

  def widthTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._widthBox.text()
    self._preset.properties()["width"] = str(value)

  def heightTextChanged(self):
    # Slot to handle change of thumbnail format combo change state
    value = self._heightBox.text()
    self._preset.properties()["height"] = str(value)

  def frameTypeComboBoxChanged(self, index):
    # Slot to handle change of thumbnail format combo change state

    value = self._frameTypeComboBox.currentText()
    if str(value) == self.kCustomFrame:
      self._customFrameLineEdit.setEnabled(True)
      self._preset.properties()["customFrameOffset"] = str(self._customFrameLineEdit.text())
    else:
      self._customFrameLineEdit.setEnabled(False)
    self._preset.properties()["frameType"] = str(value)

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

    self._preset.properties()["thumbSize"] = str(value)


  def populateUI_work(self, widget, exportTemplate):
    layout = widget.layout()
    info = QtWidgets.QLabel("""<i>Windows Note:</i> Symbolic links will only work in Vista or later.\n
To link across filesystems the remote file server must also be running Vista or later.\n
You may also need administrator privileges to create symbolic links on Windows.""")
    info.setWordWrap(True)
    layout.addWidget(info)

  def populateUI(self, widget, exportTemplate):

    layout = widget.layout()
    formLayout = TaskUIFormLayout()
    layout.addLayout(formLayout)

    # Thumb frame type layout
    thumbFrameLayout = QtWidgets.QHBoxLayout()
    self._frameTypeComboBox = QtWidgets.QComboBox()
    self._frameTypeComboBox.setToolTip("Specify the frame from which to pick the thumbnail.\nCustom allows you to specify a custom frame offset, relative from the first frame.")

    thumbFrameTypes = (self.kFirstFrame, self.kMiddleFrame, self.kLastFrame, self.kCustomFrame)
    for index, item in zip(range(0,len(thumbFrameTypes)), thumbFrameTypes):
      self._frameTypeComboBox.addItem(item)
      if item == str(self._preset.properties()["frameType"]):
        self._frameTypeComboBox.setCurrentIndex(index)

    self._frameTypeComboBox.setMaximumWidth(80)

    self._customFrameLineEdit = QtWidgets.QLineEdit()
    self._customFrameLineEdit.setEnabled(False)
    self._customFrameLineEdit.setToolTip("This is the frame offset from the first frame of the shot/sequence")
    self._customFrameLineEdit.setValidator(QtGui.QIntValidator())
    self._customFrameLineEdit.setMaximumWidth(80);
    self._customFrameLineEdit.setText(str(self._preset.properties()["customFrameOffset"]))

    thumbFrameLayout.addWidget(self._frameTypeComboBox, QtCore.Qt.AlignLeft)
    thumbFrameLayout.addWidget(self._customFrameLineEdit, QtCore.Qt.AlignLeft)
    #thumbFrameLayout.addStretch()

    # QImage save format type
    self._formatComboBox = QtWidgets.QComboBox()
    thumbFrameTypes = ("png", "jpg", "tiff", "bmp")
    for index, item in zip(range(0,len(thumbFrameTypes)), thumbFrameTypes):
      self._formatComboBox.addItem(item)
      if item == str(self._preset.properties()["format"]):
        self._formatComboBox.setCurrentIndex(index)

    self._formatComboBox.currentIndexChanged.connect(self.formatComboBoxChanged)


    # QImage save height
    # Thumb frame type layout
    thumbSizeLayout = QtWidgets.QHBoxLayout()

    self._thumbSizeComboBox = QtWidgets.QComboBox()
    self._thumbSizeComboBox.setMaximumWidth(115)
    self._thumbSizeComboBox.setToolTip("This determines the size of the thumbnail.\nLeave as Default to use Hiero's internal thumbnail size or specify a box or width/height scaling in pixels.")
    thumbSizeTypes = ("Default","To Box", "Scaled to Width", "Scaled to Height")
    for index, item in zip(range(0,len(thumbSizeTypes)), thumbSizeTypes):
      self._thumbSizeComboBox.addItem(item)
      if item == str(self._preset.properties()["thumbSize"]):
        self._thumbSizeComboBox.setCurrentIndex(index)

    thumbSizeLayout.addWidget(self._thumbSizeComboBox)
    self._wLabel = QtWidgets.QLabel('w:')
    self._wLabel.setFixedWidth(12)
    thumbSizeLayout.addWidget(self._wLabel,QtCore.Qt.AlignLeft)
    self._widthBox = QtWidgets.QLineEdit()
    self._widthBox.setToolTip("Thumbnail width in pixels")
    self._widthBox.setEnabled(False)
    self._widthBox.setValidator(QtGui.QIntValidator())
    self._widthBox.setMaximumWidth(40)
    self._widthBox.setText(str(self._preset.properties()["width"]))
    self._widthBox.textChanged.connect(self.widthTextChanged)
    thumbSizeLayout.addWidget(self._widthBox,QtCore.Qt.AlignLeft)

    self._hLabel = QtWidgets.QLabel('h:')
    self._hLabel.setFixedWidth(12)
    thumbSizeLayout.addWidget(self._hLabel,QtCore.Qt.AlignLeft)
    self._heightBox = QtWidgets.QLineEdit()
    self._heightBox.setToolTip("Thumbnail height in pixels")
    self._heightBox.setEnabled(False)
    self._heightBox.setValidator(QtGui.QIntValidator())
    self._heightBox.setMaximumWidth(40)
    self._heightBox.setText(str(self._preset.properties()["height"]))
    self._heightBox.textChanged.connect(self.heightTextChanged)
    thumbSizeLayout.addWidget(self._heightBox,QtCore.Qt.AlignLeft)

    self._thumbSizeComboBox.currentIndexChanged.connect(self.thumbSizeComboBoxChanged)
    self.thumbSizeComboBoxChanged(0)
    self._frameTypeComboBox.currentIndexChanged.connect(self.frameTypeComboBoxChanged)
    self.frameTypeComboBoxChanged(0) # Trigger to make it set the enabled state correctly
    self._customFrameLineEdit.textChanged.connect(self.customOffsetTextChanged)

    formLayout.addRow("Frame Type:",thumbFrameLayout)
    formLayout.addRow("Size:",thumbSizeLayout)
    formLayout.addRow("File Type:",self._formatComboBox)

hiero.ui.taskUIRegistry.registerTaskUI(ThumbnailExportTask.ThumbnailExportPreset, ThumbnailExportUI)
