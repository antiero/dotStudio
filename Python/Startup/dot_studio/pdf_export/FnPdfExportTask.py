# PDF Exporter Task
# PDF export task which can be used via the Export dialog via Sequence Processor
import os
import hiero.core
from PySide2.QtCore import Qt
from FnPdfExporter import PDFExporter, printSequenceToPDF

class PdfExportTask(hiero.core.TaskBase):
  def __init__( self, initDict ):
    """Initialize"""
    hiero.core.TaskBase.__init__( self, initDict )

  def startTask(self):
    hiero.core.TaskBase.startTask(self)
    pass
    
  def taskStep(self):
    # Write out the thumbnail for each item
    if isinstance(self._item, (hiero.core.Sequence)):

      self._pdfFilePath = self.resolvedExportPath()
      sequence = self._item

      _thumbnailFrameType = self._preset.properties()['thumbnailFrameType']
      _pageLayoutType = self._preset.properties()["pageLayoutType"]
      _layoutsDict = PDFExporter.PAGE_LAYOUTS_DICT
      _numRows = _layoutsDict[_pageLayoutType][0]
      _numColumns = _layoutsDict[_pageLayoutType][1]
      _orientation = _layoutsDict[_pageLayoutType][2]

      printSequenceToPDF(sequence, self._pdfFilePath, 
                         numRows = _numRows, numColumns = _numColumns,
                         orientation = _orientation,
                         thumbnailFrameType = _thumbnailFrameType)

    self._finished = True
    
    return False

class PdfExportPreset(hiero.core.TaskPresetBase):
  def __init__(self, name, properties):
    hiero.core.TaskPresetBase.__init__(self, PdfExportTask, name)

    # Set any preset defaults here
    self.properties()["format"] = "pdf"
    self.properties()["thumbnailFrameType"] = "Middle"
    self.properties()["pageLayoutType"] = "9 Shots per page"

    # Update preset with loaded data
    self.properties().update(properties)

  def addCustomResolveEntries(self, resolver):
    resolver.addResolver("{ext}", "File format extension of the thumbnail", lambda keyword, task: self.properties()["format"])
  
  def supportedItems(self):
    """Supported only for Sequences currently"""
    return hiero.core.TaskPresetBase.kSequence

hiero.core.taskRegistry.registerTask(PdfExportPreset, PdfExportTask)