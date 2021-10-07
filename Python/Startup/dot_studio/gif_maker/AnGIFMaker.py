# Adds action to export an animated GIF from a Sequence
# Either seleect a range of TrackItems or set in an out points on the Sequence.
import sys, os
import sys 
# NOTE: Set this path to your PIL imaging library, install PIL via: pip install pillow
sys.path.append("/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages")
try:
    from PIL import Image
except:
    print("WARNING: Python Imaging Library not imported. Please install via pip install pillow and append install path to sys.path.")
import os, time
import hiero.core
import hiero.ui
from PySide2 import QtGui, QtCore, QtWidgets
from io import BytesIO

class RenderPreviewDialog(QtWidgets.QWidget):
    """A render preview dialog of the GIF being rendered"""
    def __init__(self):
        super(RenderPreviewDialog, self).__init__()
        self.initUI()
        
    def initUI(self):
        """Set up the UI"""
        self.pixmap = QtGui.QPixmap("icons:TagHiero.png")
        self.lbl = QtWidgets.QLabel(self)
        self.lbl.setPixmap(self.pixmap)
        self.lbl.setScaledContents(True)
        self.lbl.move(100, 5)       

        self.pbar = QtWidgets.QProgressBar(self)
        self.pbar.setGeometry(30, 80, 220, 20)

        self.btn = QtWidgets.QPushButton('Cancel', self)
        self.btn.move(100, 110)
        self.btn.clicked.connect(self.cancel)

        self.setGeometry(300, 300, 280, 140)
        self.setWindowTitle('Rendering GIF')
        self.renderingEnabled = True

    def cancel(self):
      self.renderingEnabled = False

class MakeGIFAction(QtWidgets.QAction):
  def __init__(self):
      QtWidgets.QAction.__init__(self, "Make GIF", None)
      self._currentSequence = None
      self._inFrame = None
      self._outFrame = None
      self.renderPreview = RenderPreviewDialog()

      self.triggered.connect(self.doit)
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kViewer", self.eventHandler)


  def exportGIFFromSequence(self, sequence, inFrame, outFrame, outputFilePath=None, fps = 24.0):
    """
    Exports a Sequence to a GIF over a range of in-outFrame. 
    If no outputFilePath is specified, the GIF is written to the Desktop.
    duration sets the time between rendered frames
    """

    duration = outFrame - inFrame

    if duration > 500:
      print("The mighty GIF cannot handle your duration of 500+ frames! Rendering only the first 500 frames")
      outFrame = inFrame+499

    # Images for GIF...
    if hasattr(sequence,'thumbnail'):
      images = []
      self.renderPreview.show()

      count = 1
      for t in range(inFrame, outFrame):
        thumb = sequence.thumbnail(t)

        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.ReadWrite)
        thumb.save(buffer, "PNG")

        strio = BytesIO()
        strio.write(buffer.data())
        buffer.close()
        strio.seek(0)
        images += [Image.open(strio)]

        progress = int(100.0*(float(count)/float(duration)))
        hiero.core.log.debug('Progress is: '+ str(progress))
        self.renderPreview.lbl.setPixmap(QtGui.QPixmap(thumb)) 

        self.renderPreview.pbar.setValue(progress)
        QtCore.QCoreApplication.processEvents()

        count+=1

        if not self.renderPreview.renderingEnabled:
          print("Rendering Cancelled")
          self.renderPreview.hide()
          self.renderPreview.renderingEnabled = True
          return

    if not outputFilePath:
      try:
        outputFilePath = os.path.join(os.getenv('HOME'),'Desktop',('myGif_%i.gif' % time.time()))
      except:
        from os.path import expanduser
        outputFilePath = os.path.join(expanduser('~'),'Desktop',('myGif_%i.gif' % time.time()))

    images[0].save(outputFilePath, save_all=True, append_images=images[1:], optimize=True, duration=(len(images)/fps))
    self.renderPreview.hide()
    hiero.ui.openInOSShell(outputFilePath)    

  def doit(self):
    # remove any non-trackitem entries (ie transitions)
    view = hiero.ui.activeView()
    # If the active view is a timeline or a viewer, we favour rendering a GIF over the range of selected trackItems.
    # If there are no selected TrackItems, then we try in and out frames, (limited to 500 frames).
    # The GIF will fail to export if these things are not set.

    if isinstance(view, hiero.ui.TimelineEditor):
      sequence = view.sequence()
      if not sequence:
        return

      selection = [item for item in view.selection() if isinstance(item, hiero.core.TrackItem)]

    elif isinstance(view, hiero.ui.Viewer):
      sequence = view.player().sequence()
      if not sequence:
        return

      timeline = hiero.ui.getTimelineEditor(sequence)
      selection = [item for item in timeline.selection() if isinstance(item, hiero.core.TrackItem)]

    if len(selection)>0:
      # Find the earliest and latest frames in the selection set
      inFrame = min([item.timelineIn() for item in selection])
      outFrame = max([item.timelineOut() for item in selection])
    else:
      try:
        inFrame = sequence.inTime()
        outFrame = sequence.outTime()
      except:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText("Please set an In and Out point. (Frame Range is limited to 500 frames)")
        msgBox.exec_()
        return

    # If we have a sequence, work out whether a frame range is set, else 
    if sequence and inFrame and outFrame:
      self.exportGIFFromSequence(sequence, inFrame, outFrame)

  def eventHandler(self, event):
    event.menu.addAction(self)