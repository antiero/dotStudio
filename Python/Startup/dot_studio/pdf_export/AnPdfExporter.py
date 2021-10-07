#------------------------------------------------------------------------------
# AnPdfExporter.py - Produces PDF contact sheet shot layouts for a sequence
#------------------------------------------------------------------------------
# Antony Nasce, v1.1, 18/01/21
#------------------------------------------------------------------------------
# PDF Layout by Abo Biglarpour. PDF writing Reportlab: http://www.reportlab.com
#------------------------------------------------------------------------------
try:
    from reportlab.platypus import Paragraph, Table, TableStyle
except Exception as e:
    print(e)
    print("Unable to import reportlab. Check that reportlab is in your sys.path!")

import reportlab.lib.pagesizes
import reportlab.pdfgen.canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import lightslategray, black, green, limegreen, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.lib.utils import ImageReader, simpleSplit

import os
import sys
import shutil
import tempfile
import datetime
import time
import urllib
import xml.sax.saxutils

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QProgressDialog, QMenu, QDialog, QFormLayout, QComboBox, QDialogButtonBox, QSizePolicy

import hiero.ui
from foundry.ui import FnFilenameField
from hiero.core import Timecode

class PDFExporter(object):

    # Data for Export Tasks and GUI action
    THUMB_FIRST_FRAME = "First"
    THUMB_MIDDLE_FRAME = "Middle"
    THUMB_LAST_FRAME = "Last"
    THUMB_FRAME_TYPES = (THUMB_FIRST_FRAME, THUMB_MIDDLE_FRAME, THUMB_LAST_FRAME)
    PAGE_LAYOUTS_DICT = {"1 per page" : [1, 1, "landscape"], 
                         "2 x 2": [2, 2, "landscape"], 
                         "3 x 3": [3, 3, "landscape"],
                         "3 x 1": [3, 1, "letter"]}

    def __init__(self, shotCutList, outputFilePath = None, 
                 rows = 3, columns = 3, orientation = "landscape", 
                 thumbnailFrameType = "Middle"):
        """
        Template for creating PDF sheets for a sequence
        :param shotCutList: List of TrackItems to generate pdf for
        :param outputFilePath: PDF output file path
        :param rows: number of rows in the PDF
        :param columns: number of columns in the PDF
        :param orientation: page orientation of PDF ('landscape' or 'letter')
        :param thumbnailFrame: the thumbnail frame type ("First, Middle", "Last")
        """
        self.shotCutList   = shotCutList
        self.outputFilePath = outputFilePath
        self.project = self.shotCutList[0].project()
        self.sequence = self.shotCutList[0].parentSequence()
        self.imageDataList = []
        self.row               = rows
        self.column            = columns
        self.marginSize        = 25
        self.pageOrientation   = orientation
        self.styles            = getSampleStyleSheet()
        self.companyLogo       = None
        self.showLogo          = None
        self.offlineLogoPath   = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images/offline.jpg")

        # Determine which frame should be used for the Shot thumbnail
        self.thumbnailFrameType = thumbnailFrameType
        if self.thumbnailFrameType not in self.THUMB_FRAME_TYPES:
            self.thumbnailFrameType = self.THUMB_MIDDLE_FRAME

        self.shotStatuses  = []

        self.buildImageDataList()
        self.getPdfParameters()

        # prep background for usage
        self.getBackground()
        # prep company logo for potential usage
        self.getCompanyLogo()
        # prep show logo for potential usage
        self.getShowLogo()

        fontColorImport = __import__("reportlab.lib.colors", globals(), locals(), [self.textColor], 0)
        self.fontColor = getattr(fontColorImport, self.textColor)

        today = datetime.datetime.now()
        self.pageInfo = today.strftime("%b %d %Y %I:%M:%S %p")


    def buildCanvas(self):
        """
        Builds a canvas object with current settings
        :return: canvas object
        """
        # get page width and height
        self.pageWidth, self.pageHeight = self.getPageSize()

        # create an empty canvas
        if not self.outputFilePath:
            self.outputFilePath =  os.path.join(os.getenv('HOME'), "Desktop", "Sequence_" + self.currentTimeString() + ".pdf")

        self.canvas = reportlab.pdfgen.canvas.Canvas(self.outputFilePath, pagesize=self.pageSize)

        rowCounter = 0
        colCounter = 0
        pageNumber = 1
        self.shotVertShift = 0
        self.textGap    = (self.fontSize+4) * 4
        self.header = self.marginSize*1.5

        # set the font type from parameters
        self.loadFontType()

        # set the canvas settings
        self.setCanvasSettings(pageNumber)

        # loop through imageDataList and create the pages of PDF with all content based on row and column count provided
        for index, imageData in enumerate(self.imageDataList):
            image = imageData['path']
            shot = ImageReader(image)

            # figure out the image sizes based on the number of row's and column's
            shotWidth, shotHeight = self.getShotSize(shot)

            # get each shots XY position on the pdf page
            shotX, shotY = self.getShotPosition(shotWidth, shotHeight, rowCounter, colCounter)

            imageData.update({"shotX":shotX,
                              "shotY":shotY,
                              "shotW":shotWidth,
                              "shotH":shotHeight})

            # insert the image and stroke
            self.canvas.drawImage(shot, shotX, shotY, width=shotWidth, height=shotHeight)
            self.canvas.rect(shotX, shotY, width=shotWidth, height=shotHeight)

            # insert shot label and track
            self.setShotTrackData(imageData)

            # set index number of each shot
            indexY = shotY - 10
            indexX = shotX + shotWidth
            self.canvas.setFillColor(self.fontColor)
            self.canvas.drawRightString(indexX, indexY, str(index+1))

            # TO-DO Status and New shots?
            # check if shot status exists and set icon
            #self.setShotShotStatus(imageData)
            # check if the current shot is new and set new icon
            #self.setShotNewIcon(imageData)

            # set the shot time label (this will be a Time info)
            self.setShotShotLabel(imageData)

            # check the row's and column's counter to set the next image in the correct place
            colCounter += 1
            if colCounter == self.column:
                colCounter = 0
                rowCounter += 1

            if rowCounter == self.row and not index == (len(self.imageDataList)-1):
                self.setWatermark()
                self.canvas.showPage()
                pageNumber += 1
                self.setCanvasSettings(pageNumber)
                rowCounter = 0
            
        return self.canvas

    def exportPDF(self, show=True):
        """Exports the PDF and shows it in the file browser"""

        self.buildCanvas()

        # save the pdf
        self.canvas.save()


        self.cleanUpTempFiles()

        if self.canvas and show:
            self.showPDF()

    def setCanvasSettings(self, pageNumber=1):
        """
        Sets the settings and header/footer of each pdf page
        :param pageNumber: The current page to be built
        """
        # set font type and size for the page
        #self.canvas.setFont(self.fontType, self.fontSize)

        # set background color
        self.setBackground()

        # header bar
        self.setHeader()

        # footer bar
        self.setFooter(pageNumber)

    def cleanUpTempFiles(self):
        error = None
        for f in self.fileList:
            try:
                os.remove(f)
            except:
                pass
        if error:
            print(error)

    def showPDF(self):
        if os.path.isfile(self.outputFilePath):
            hiero.ui.openInOSShell(self.outputFilePath)

    def currentTimeString(self):
        # Returns current time epoch number as a string with underscores
        return str(time.time()).replace('.','_')

    def sequenceInfoString(self, sequence):
        """Returns a string to match the BinItem display, of the form:wxh, %if @%iFPS"""
        format = sequence.format()
        width = format.width()
        height = format.height()
        fps = sequence.framerate().toString()
        duration = sequence.duration()
        infoString = "%ix%i, %if @%sFPS" % (width, height, duration, fps)
        return infoString

    def validString(self, stringToValidate):
        string = xml.sax.saxutils.unescape(str(urllib.parse.unquote_plus(stringToValidate)))
        if len(string)>50:
            string = string[0:49]

        return string

    def getThumbFrameForShot(self, shot):
        """Returns the frame number from which to take the thumbnail based on the options passed to the export task"""
        # Case for Clips and Sequences
        if self.thumbnailFrameType == self.THUMB_FIRST_FRAME:
            thumbFrame = shot.sourceIn()
        elif self.thumbnailFrameType == self.THUMB_MIDDLE_FRAME:
            thumbFrame = shot.sourceIn()+int((shot.sourceOut()-shot.sourceIn())/2)
        elif self.thumbnailFrameType == self.THUMB_LAST_FRAME:
            thumbFrame = shot.sourceOut()
        
        return int(thumbFrame)

    def buildImageDataList(self):
        """
        Build the image list with meta data to be constructed into pdf
        """
        markerName = ""
        shotStatus = ""
        markerIndex = 1
        self.fileList = []
        self.tempFileDir = tempfile.gettempdir()

        numFiles = len(self.shotCutList)
        progress = QProgressDialog("Generating PDF...", "Cancel Export", 0, numFiles, hiero.ui.mainWindow())
        progress.setWindowModality(Qt.WindowModal)
        tc = Timecode()
        timecodeStart = self.sequence.timecodeStart()
        timecodeDisplayMode = Timecode().kDisplayTimecode
        fps = self.sequence.framerate()

        count = 1
        for shot in self.shotCutList:
            thumbPath = os.path.join(self.tempFileDir,"%s_%s.jpg" % (shot.name(), self.currentTimeString()))

            thumbnailFrame = self.getThumbFrameForShot(shot)

            # Try and get a thumbnail, assuming the media is present etc...
            try:
                thumb = shot.thumbnail( thumbnailFrame ).save(thumbPath)
            except:
                shutil.copy(self.offlineLogoPath, thumbPath)

            if not os.path.isfile(thumbPath) or progress.wasCanceled():
                self.cleanUpTempFiles()
                progress.cancel()
                break

            # This file list gets cleaned up after the PDF save finishes
            self.fileList += [thumbPath]

            dataDict = {'show':self.project,
                        'sequence':self.sequence,
                        'editVersion':"*Version*",
                        'setup':"*setup*",
                        'timeString': tc.timeToString(shot.timelineIn() + timecodeStart, fps, timecodeDisplayMode) + ", %if" % shot.duration(),
                        'name': self.validString(shot.name()),
                        'version':"*version*",
                        'path': thumbPath, 
                        'track': self.validString(shot.parentTrack().name()),
                        'shot': self.validString(shot.source().name()),
                        'shotLabel': self.validString(shot.name()),
                        'shotStatus': "*ShotStatus*",
            }
            
            self.imageDataList.append(dataDict)
            progress.setValue(count)
            count += 1

    def getPdfParameters(self):
        """
        Fetch all the show parameters for pdf template
        """
        self.companyName            = "AwesomeFX"
        self.companyLogoPath        = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images/company.jpg")
        self.showLogoPath           = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images/show.jpg")
        self.background             = "white"
        self.fontTypePath           = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fonts/OpenSans-Light.ttf")
        self.watermarkText          = "" # "e.g. CONFIDENTIAL"
        self.fontSize               = 10
        self.textColor              = "black"
        self.editComment            = "Comments"
        self.title                  = self.sequence.name() + " , " + self.sequenceInfoString(self.sequence)

    def getBackground(self):
        """
        get the background, either get color object or ImageReader for image
        If color is darker than RGB(65, 65, 65) the text color will switch to white
        """
        bgColorImport = __import__("reportlab.lib.colors", globals(), locals(), [self.background], 0)
        self.backgroundColor = getattr(bgColorImport, self.background)
        if self.backgroundColor.int_rgb() < 4276545:
            self.textColor = 'white'

    def getCompanyLogo(self):
        if os.path.isfile(self.companyLogoPath):
            if not self.companyLogoPath.endswith(('.jpg', 'jpeg')):
                self.companyLogoPath = self.convertToJpeg(self.companyLogoPath)
            self.companyLogo = ImageReader(self.companyLogoPath)

    def getShowLogo(self):
        if os.path.isfile(self.showLogoPath):
            if not self.showLogoPath.endswith(('.jpg', 'jpeg')):
                self.showLogoPath = self.convertToJpeg(self.showLogoPath)
            self.showLogo = ImageReader(self.showLogoPath)

    def setBackground(self):
        """
        set the background to either color or image if provided
        """
        if isinstance(self.backgroundColor, ImageReader):
            bgWidth = float(self.backgroundColor._width)
            bgHeight = float(self.backgroundColor._height)
            bgImgWidth = self.pageWidth
            bgImgHeight = bgImgWidth * (bgHeight/bgWidth )
            bgY = (self.pageHeight - bgImgHeight) / 2
            self.canvas.drawImage(self.backgroundColor, 0, bgY, width=bgImgWidth, height=bgImgHeight)
        else:
            self.canvas.setFillColor(self.backgroundColor)
            self.canvas.rect(0, 0, self.pageWidth, self.pageHeight, fill=True, stroke=False)

    # TO-DO: Make this a pure Nuke-only function
    def convertToJpeg(self, source):
        """
        Convert different image formats to jpeg, due to reportLab not natively supporting other formats
        :param source: image file to be converted
        :return: new jpeg path
        """
        newSource = source.replace(os.path.splitext(source)[-1], '.jpeg')
        return newSource

    def loadFontType(self):
        """
        Load the provided font from parameters as the default font to use
        """
        self.fontType = 'customFont'
        try:
            pdfmetrics.registerFont(TTFont(self.fontType, self.fontTypePath))
        except Exception as e:
            print(e)
            print("Incorrect PDF font type path %s" % self.fontTypePath)

    def getPageSize(self):
        """
        get the page width and height based on the layout of the page
        :return: width and height
        """
        tmpImport = __import__("reportlab.lib.pagesizes", globals(), locals(), ['letter'], 0)
        if self.pageOrientation  == "landscape":
            letter = getattr(tmpImport, 'letter')
            self.pageSize = getattr(tmpImport, self.pageOrientation)(letter)
        else:
            self.pageSize = getattr(tmpImport, self.pageOrientation)

        return self.pageSize[0], self.pageSize[1]

    def getShotSize(self, shot):
        """
        Calculate the width and height of each shot based on layout and row/column
        :param shot:
        :return:
        """
        if self.row >= self.column and not (self.row ==1 and self.column ==1):
            shotHeight = ((self.pageHeight-((self.marginSize*4)+self.textGap))/self.row) - (self.textGap*((self.row-1)/float(self.row)))
            shotWidth = shotHeight * (shot._width/float(shot._height) )
            if ((shotWidth*self.column)+(self.marginSize*(self.column+1))) >= self.pageWidth:
                shotWidth  = ((self.pageWidth-(self.marginSize*2))/self.column) - (self.marginSize*((self.column-1)/float(self.column)))
                shotHeight = shotWidth * (float(shot._height) / shot._width)
        else:
            shotWidth  = ((self.pageWidth-(self.marginSize*2))/self.column) - (self.marginSize*((self.column-1)/float(self.column)))
            shotHeight = shotWidth * (float(shot._height) / shot._width)

        return shotWidth, shotHeight

    def getShotPosition(self, shotW, shotH, rowCounter, colCounter):
        """
        Calculate the XY position of the given shot, takes in consideration of shot size and number of row/column
        adds extra padding for track name and gaps between images for aesthetics
        :param shotW: shot width
        :param shotH: shot height
        :param rowCounter: the current row index
        :param colCounter: the current column index
        :return: shot XY positions as tuple
        """
        # calculate the gap between each image based on image size and page size
        imageGapW = ((self.pageWidth-(self.marginSize*2)) - (shotW * self.column))/(self.column-1) if self.column > 1 else 0
        imageGapH = ((self.pageHeight - ((self.header+(self.fontSize*2))*2)) - (shotH * self.row))/self.row if self.row > 1 else 30

        # calculate where each images x,y positions are
        shotX =  ((shotW + imageGapW) * colCounter) + self.marginSize
        shotY =  ((self.pageHeight-(self.header+(self.fontSize*2)))  - ((shotH+imageGapH)*(rowCounter+1)))
        if rowCounter == 0:
            shotYExpected = ((self.pageHeight-(self.header+(self.fontSize*2)))  - (shotH*(rowCounter+1)))
            if shotY != shotYExpected:
                self.shotVertShift = shotY - shotYExpected
        shotY -= self.shotVertShift

        return shotX, shotY

    def setShotTrackData(self, imageData):
        """
        Set the shot name and track for the given shot and place it in the appropriate position based on layout
        :param imageData: dictionary object with shot metaData
        :return: Table object
        """
        shotX = imageData.get("shotX")
        shotY = imageData.get("shotY")
        shotH = imageData.get("shotH")
        shotW = imageData.get("shotW")
        # set the shot label and track for each shot
        #shotLabel = "%04d-%s"%(int(imageData['setup']),imageData['version']) if imageData['version']>1 else "%04d"%int(imageData['setup'])
        shotLabel = "%s" % imageData['name']
        shotData = {'shotLabel':shotLabel,
                     'textColor':self.textColor,
                     'fontSize':self.fontSize,
                     'fontName':self.fontType,
                     'track':imageData['track'].replace("\n", "<br/>")}

        shotName = Paragraph('''<para align=center spaceb=3>
                                 <font name=%(fontName)s size=11 color=%(textColor)s>
                                 <b>%(shotLabel)s</b></font><br/>
                                 <font name=%(fontName)s size=%(fontSize)s color=%(textColor)s>
                                 %(track)s</font></para>'''%shotData, self.styles['BodyText'])

        data = [[shotName]]

        # adjust track placement based on row/column layout
        if self.column == 1 and not self.row == 1:
            textX = shotX + shotW + self.marginSize
            textY = (shotY + shotH) - self.textGap
            textWidth = self.pageWidth - shotW - (self.marginSize*3)
        else:
            textWidth = shotW
            textX = shotX
            textY = shotY - self.textGap

        table = Table(data, colWidths=textWidth, rowHeights=self.textGap)
        table.setStyle(TableStyle([('VALIGN',(-1,-1),(-1,-1),'TOP')]))
        table.wrapOn(self.canvas, textX, self.textGap)
        table.drawOn(self.canvas, textX, textY)
        return table

    def setWatermark(self):
        if self.watermarkText:
            self.canvas.setFont(self.fontType, 70)
            self.canvas.setFillColor(self.fontColor, alpha=0.1)
            self.canvas.drawCentredString(self.pageWidth/2, self.pageHeight/2, self.watermarkText)

    def setCompanyLogo(self):
        logoW = 0
        if isinstance(self.companyLogo, ImageReader):
            logoH = self.marginSize * 1.5
            logoW = logoH * (self.companyLogo._width/float(self.companyLogo._height))
            logoX = self.marginSize
            logoY = self.marginSize/2
            self.canvas.drawImage(self.companyLogo, logoX, logoY, logoW, logoH)
        return logoW

    def setShowLogo(self):
        showLogoWidth = 0
        if isinstance(self.showLogo, ImageReader):
            logoWidth = float(self.showLogo._width)
            logoHeight = float(self.showLogo._height)
            showLogoHeight = self.marginSize
            showLogoWidth = showLogoHeight * (logoWidth/logoHeight)
            logoX = self.marginSize
            logoY = self.pageHeight-self.header
            self.canvas.drawImage(self.showLogo, logoX, logoY, width=showLogoWidth, height=showLogoHeight)
        return showLogoWidth

    def setShotShotStatus(self, imageData):
        """
        UNUSED - Should be updated to optionally include Shot Status
        Sets the shots status of the given shot if status exists, aligned to the bottom left of the shot
        :param imageData: dictionary object with shot metaData
        """
        shotX = imageData.get("shotX")
        shotY = imageData.get("shotY")
        if imageData.get('shotStatus'):
            statusIcon = [status.iconPath for status in self.shotStatuses.statuses if imageData['shotStatus'] == status.label]
            if len(statusIcon) > 0:
                statusIcon = statusIcon[0]
                if self.fileService.exists(statusIcon):
                    if not statusIcon.endswith(('.jpg', '.jpeg')):
                        statusIcon = statusIcon.replace(os.path.splitext(statusIcon)[-1], ".jpg")
                    statusIconReader = ImageReader(self.repath.localize(statusIcon))
                    statusH = 15
                    statusW = statusH * (statusIconReader._width/float(statusIconReader._height))
                    statusX = shotX
                    statusY = shotY - statusH - 2
                    self.canvas.drawImage(statusIconReader, statusX, statusY, statusW, statusH)

    def setShotNewIcon(self, imageData):
        """
        UNUSED - Should be updated to optionally include Tag Icons
        Sets the shots new icons if the shot is new since the last editorial publish, aligned to the top right of the shot
        :param imageData: dictionary object with shot metaData
        """
        shotX = imageData.get("shotX")
        shotY = imageData.get("shotY")
        shotH = imageData.get("shotH")
        shotW = imageData.get("shotW")
        if imageData['shot'].label in self.newShots:
            newLabelW = 25
            newLabelH = 10
            newLabelX = shotX + shotW - newLabelW
            newLabelY = shotY + shotH + 2
            self.canvas.setFillColor(limegreen)
            self.canvas.setStrokeColor(black)
            self.canvas.rect(newLabelX, newLabelY, newLabelW, newLabelH, fill=True, stroke=True)
            newTextX = newLabelX + 2
            newTextY = newLabelY + 2
            self.canvas.setFillColor(black)
            self.canvas.drawString(newTextX, newTextY, 'NEW')

    def setShotShotLabel(self, imageData):
        """
        sets the shots shot label if belongs to a shot, aligned on the top left of the shot
        :param imageData: dictionary object with shot metaData
        """
        shotX = imageData.get("shotX")
        shotY = imageData.get("shotY")
        shotH = imageData.get("shotH")
        if imageData.get('timeString'):
            shotLabelX = shotX
            shotLabelY = shotY + shotH + 2
            self.canvas.setFillColor(self.textColor)
            self.canvas.drawString(shotLabelX, shotLabelY, imageData.get('timeString'))

    def setHeader(self):
        """
        sets all the header information per page, adds Title and tile bar, aligned on the top center of the page
        """
        showLogoWidth = self.setShowLogo()
        showLogoWidth = showLogoWidth + 5 if showLogoWidth else 0 # add 5 for padding if show logo exists
        self.canvas.setLineWidth(width=1)
        self.canvas.setFillColor(lightslategray)
        self.canvas.setStrokeColor(black)
        self.canvas.rect(self.marginSize + showLogoWidth, (self.pageHeight-self.header), (self.pageWidth-(self.marginSize*2)) - showLogoWidth, self.marginSize, fill=True, stroke=True)
        
        # header text
        self.canvas.setFillColor(black)
        titleSplit = simpleSplit(self.title, self.fontType, 16, (self.pageWidth-(self.marginSize*2)) - showLogoWidth)
        self.canvas.setFont(self.fontType, 16)
        self.canvas.drawString((self.marginSize*1.25) + showLogoWidth, self.pageHeight - (self.marginSize*1.125), titleSplit[0])

    def setFooter(self, pageNumber):
        """
        sets all footer information per page, add page info, footer bar, and privacy info, aligned on the bottom center of the page
        :param pageNumber:
        :return:
        """
        companyLogoW = self.setCompanyLogo()
        companyLogoW += 5 if companyLogoW else 0 # add 5 for padding if company logo exists
        self.canvas.setLineWidth(width=1)
        self.canvas.setFillColor(lightslategray)
        self.canvas.setStrokeColor(black)
        self.canvas.rect(self.marginSize+companyLogoW, self.header, (self.pageWidth-(self.marginSize*2))-companyLogoW, (self.marginSize/2), fill=True, stroke=True)
        self.canvas.setFillColor(black)
        # footer text
        self.canvas.setFont(self.fontType, 9)
        self.canvas.drawRightString(self.pageWidth-(self.marginSize*1.25), (self.marginSize*1.625),"%s Page - %d" % (self.pageInfo, pageNumber))

        # set privacy info on the bottom of the page
        privacyInfo = {'msg1':"CONFIDENTIAL: The images, artwork and other materials displayed are the proprietary property of %s."%self.companyName,
                       'msg2':"Any unauthorized use, printing, copying or distribution of such images, artwork and materials is strictly prohibited. All rights reserved.",
                       'textColor':self.textColor,
                       'fontName':self.fontType,
                       'size':7}
        shotName = Paragraph('''<para align=center spaceb=3>
                                  <font name=%(fontName)s size=%(size)s color=%(textColor)s>%(msg1)s<br/>
                                  %(msg2)s</font></para>'''%privacyInfo, self.styles['BodyText'])
        privacyTable = Table([[shotName]], colWidths=(self.pageWidth-(self.marginSize*2)))
        privacyTable.setStyle(TableStyle([('VALIGN',(-1,-1),(-1,-1),'TOP')]))
        privacyTable.wrapOn(self.canvas, self.marginSize, 10)
        privacyTable.drawOn(self.canvas, self.marginSize, 10)

class ExportPdfOptionDialog(QDialog):
    """
    Displays options UI for the PDF
    """

    def __init__(self, parent = None):
        if not parent:
            parent = hiero.ui.mainWindow()
        super(ExportPdfOptionDialog, self).__init__(parent)

        layout = QFormLayout()
        self._fileNameField  = FnFilenameField(False, isSaveFile=False, caption="Set PDF name", filter='*.pdf')
        self._fileNameField.setFilename(os.path.join(os.getenv('HOME'), "Desktop", "Sequence.pdf"))
        self._pdfLayoutDropdown  = QComboBox()
        self._pdfLayoutDropdown.setToolTip("Set the PDF page layout type.")
        self._thumbFrameTypeDropdown  = QComboBox()
        self._thumbFrameTypeDropdown.setToolTip("Set which frame to take the thumbnail from.")

        self._buttonbox = QDialogButtonBox( QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttonbox.button(QDialogButtonBox.Ok).setText("Export")
        self._buttonbox.accepted.connect(self.accept)
        self._buttonbox.rejected.connect(self.reject)

        self._pdfLayouts = PDFExporter.PAGE_LAYOUTS_DICT

        self._thumbFrameTypes = PDFExporter.THUMB_FRAME_TYPES

        for pdfLayout in sorted(self._pdfLayouts, reverse=True):
            self._pdfLayoutDropdown.addItem(pdfLayout)

        for frameType in self._thumbFrameTypes:
            self._thumbFrameTypeDropdown.addItem(frameType)

        layout.addRow("Save to:", self._fileNameField)
        layout.addRow("PDF Layout:", self._pdfLayoutDropdown)
        layout.addRow("Thumbnail Frame:", self._thumbFrameTypeDropdown)        
        layout.addRow("", self._buttonbox)

        self.setLayout(layout)
        self.setWindowTitle("Export PDF Options")
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Fixed )

    def _thumbnailFrameType(self):
        """Returns the currently selected thumbnail frame type"""
        return self._thumbFrameTypeDropdown.currentText()

    def _numRows(self):
        """Returns the number of rows for the pdf"""
        optionText = self._pdfLayoutDropdown.currentText()
        return self._pdfLayouts[optionText][0]

    def _numColumns(self):
        """Returns the number of columns for the pdf"""
        optionText = self._pdfLayoutDropdown.currentText()
        return self._pdfLayouts[optionText][1]

    def _filePath(self):
        """Returns the filepath for the pdf"""
        filename = self._fileNameField.filename()
        if not filename.endswith('.pdf'):
            filename = filename + ".pdf"
        return filename

def printSequenceToPDF(sequence, outputFilePath, 
                       numRows=3, numColumns=3, 
                       orientation='landscape', 
                       thumbnailFrameType="Middle", showPDF=False):
    """
    Prints a hiero.core.Sequence object to PDF
        :param sequence: sequence to export
        :param outputFilePath: PDF output file path
        :param numRows: number of rows in the PDF
        :param numColumns: number of columns in the PDF
        :param orientation: page orientation of PDF ('landscape' or 'letter')
        :param thumbnailFrame: the thumbnail frame type ("First, Middle", "Last")
        :param showPDF: boolean to optionally show the PDF in file browser after export
    """
    videoTracks = sequence.videoTracks()
    trackItems = []
    for track in videoTracks:
        trackItems += [item for item in track.items() if isinstance(item, hiero.core.TrackItem)]

    printer = PDFExporter(trackItems, outputFilePath, rows = numRows, columns = numColumns, thumbnailFrameType = thumbnailFrameType)
    printer.exportPDF(show=showPDF)        

class ExportPdfAction(object):
    def __init__(self):
        self.makePDFAction  = hiero.ui.createMenuAction("Export PDF...", self.printSelectedSequenceToPDF)
        hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)

    def printSelectedSequenceToPDF(self):
        """Prints the selected Sequences to PDF and shows them in the browser"""
        view = hiero.ui.activeView()
        if not view or not hasattr(view, 'selection'):
            return        
        selection = view.selection()

        print(selection)

        sequences = [item.activeItem() for item in selection if hasattr(item, "activeItem") and isinstance(item.activeItem(), hiero.core.Sequence)]

        if len(sequences)<=0:
            return

        sequence = sequences[0]

        dialog = ExportPdfOptionDialog()
        if dialog.exec_():
            numRows = dialog._numRows()
            numColumns = dialog._numColumns()
            outputFilePath = dialog._filePath()
            thumbnailFrameType = dialog._thumbnailFrameType()
            printSequenceToPDF(sequence, outputFilePath, numRows=numRows, numColumns=numColumns, thumbnailFrameType=thumbnailFrameType, showPDF = True)

    def eventHandler(self, event):
        selection = event.sender.selection()
        sequences = [item for item in selection if hasattr(item, "activeItem") and isinstance(item.activeItem(), hiero.core.Sequence)]
        if len(sequences) == 1:
            event.menu.addAction(self.makePDFAction)