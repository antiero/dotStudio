# Prints the thumbnails of a Sequence to PDF.
from PySide import QtGui, QtCore

import sys
import time
import hiero.ui
#import shutil # Should clear up tmp png files, or work out how to use image data without writing to file

class PDFMaker(object):
    def __init__(self):
        self.makePDFAction  = hiero.ui.createMenuAction("Print PDF", self.onPrint)
        hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)

        # Will store the QPrinter instance
        self.printer = None
        # Will store the QPrintDialog, because it
        # might get garbage-collected, and the QPrinter with it
        self.pdialog = None

    def eventHandler(self, event):
        selection = event.sender.selection()
        sequences = [item for item in selection if isinstance(item.activeItem(), hiero.core.Sequence)]
        if len(sequences) == 1:
            event.menu.addAction(self.makePDFAction)

    def printState(self):
        print '*'*20
        if self.printer is None:
            print '-- no printer -- '
        else:
            print 'printer name', self.printer.printerName()
            print 'page size', self.printer.pageSize()
            print 'paper size', self.printer.paperSize()
        print
        print

    def askPrinter(self):
        # Either like this:
        # 
        # self.printer = QtGui.QPrinter()
        # self.pdialog = dialog = QtGui.QPrintDialog(self.printer)

        # Or like that:
        # 
        self.pdialog = dialog = QtGui.QPrintDialog()

        dialog.setOption(QtGui.QAbstractPrintDialog.PrintCollateCopies, False)
        dialog.setOption(QtGui.QAbstractPrintDialog.PrintCurrentPage, False)
        dialog.setOption(QtGui.QAbstractPrintDialog.PrintPageRange, False)
        dialog.setOption(QtGui.QAbstractPrintDialog.PrintSelection, False)
        dialog.setOption(QtGui.QAbstractPrintDialog.PrintShowPageSize, True)
        dialog.setOption(QtGui.QAbstractPrintDialog.PrintToFile, True)

        #print 'before PrintDialog'
        self.printState()

        if dialog.exec_() != QtGui.QDialog.Accepted:
            return False

        # And that, if not set before
        self.printer = dialog.printer()

        #print 'after PrintDialog, printer is %s' % str(self.printer)
        self.printState()

        return True

    def onPrint(self):
        if not self.askPrinter():
            print 'Unable to get ask for Printers...'
            return

        self.preview()

    def preview(self):
        dialog = QtGui.QPrintPreviewDialog(self.printer)
        dialog.paintRequested.connect(self.handlePaintRequest)
        dialog.exec_()

    def handlePaintRequest(self, printer):
        doc = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(doc)

        seq = hiero.ui.activeSequence()
        tracks = seq.videoTracks()
        trackItems = []
        for track in tracks:
            trackItems += [item for item in track.items() if isinstance(item, hiero.core.TrackItem)]

        cursor.insertText("""
        Sequence: %s
        """ % seq.name())
        cursor.insertText("-"*20)

        table = cursor.insertTable(len(trackItems), 4 ) #max(len(d) for d in trackItems))        
        for trackItem in trackItems:
                cursor.insertText(unicode(trackItem.parentTrack().name()))
                cursor.movePosition(QtGui.QTextCursor.NextCell)
                cursor.insertText(unicode(trackItem.name()))
                cursor.movePosition(QtGui.QTextCursor.NextCell)
                imageFormat = QtGui.QTextImageFormat()
                inFrame = int(trackItem.sourceIn())+int(0.1*(float(trackItem.sourceOut())-float(trackItem.sourceIn())))
                outFrame = int(trackItem.sourceIn())+int(0.9*(float(trackItem.sourceOut())-float(trackItem.sourceIn())))

                image = trackItem.thumbnail(inFrame).scaledToHeight(72)
                fileName = '/tmp/t_%i%s_%i.png' % (int(time.time()), trackItem.name(), inFrame)
                r = image.save(fileName)
                doc.addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl("file://%s" % fileName), image)
                imageFormat.setName(fileName)
                cursor.insertImage(imageFormat)
                cursor.movePosition(QtGui.QTextCursor.NextCell)

                imageFormat = QtGui.QTextImageFormat()
                image = trackItem.thumbnail(outFrame).scaledToHeight(72)
                fileName = '/tmp/t_%i%s_%i.png' % (int(time.time()), trackItem.name(), outFrame)
                r = image.save(fileName)
                doc.addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl("file://%s" % fileName), image)
                imageFormat.setName(fileName)
                cursor.insertImage(imageFormat)
                cursor.movePosition(QtGui.QTextCursor.NextCell)


        cursor.movePosition(QtGui.QTextCursor.NextBlock)
        doc.print_(printer)

act = PDFMaker()