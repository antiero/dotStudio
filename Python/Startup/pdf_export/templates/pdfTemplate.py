#------------------------------------------------------------------------------
# pdfTemplate.py -
#------------------------------------------------------------------------------
# Copyright (c) 2015 The Foundry Visionmongers Ltd.  All Rights Reserved.
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import lightslategray, black, green, limegreen
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.lib.utils import ImageReader, simpleSplit
import reportlab.lib.pagesizes
import reportlab.pdfgen.canvas
import datetime
import os
import urllib
import xml.sax.saxutils
import time

class FnPDFExporter(object):

    def __init__(self, shotCutList, newShots=None):
        """
        Template for creating PDF sheets for a sequence
        :param shotCutList: Cut list object of sequence version to generate pdf of
        :param newShots: shot indices of new shots since last editorial publish
        :param process: progress process to add and remove from
        """
        self.shotCutList   = shotCutList
        self.project = self.shotCutList[0].project()
        self.sequence = self.shotCutList[0].parentSequence()
        self.imageDataList = []
        self.row               = 3
        self.column            = 3
        self.marginSize        = 25
        self.pageOrientation   = 'landscape'
        self.styles            = getSampleStyleSheet()
        self.companyLogo       = None
        self.showLogo          = None

        self.shotStatuses  = []
        if newShots is None:
            newShots = []

        self.buildImageDataList()
        self.getPdfParameters()

        # prep background for usage
        self.getBackground()
        # prep company logo for potential usage
        self.getCompanyLogo()
        # prep show logo for potential usage
        self.getShowLogo()

        # prep all status icons for potential upload, convert to jpgs if not already
        #self.remoteConvertStatusIcons()

        fontColorImport = __import__("reportlab.lib.colors", globals(), locals(), [self.textColor], -1)
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
        self.outputFilePath =  os.path.join(os.getenv('HOME'), "Desktop", "Sequence_" + self.currentTimeString() + ".pdf")
        self.canvas = reportlab.pdfgen.canvas.Canvas(self.outputFilePath, pagesize=self.pageSize)

        rowCounter = 0
        colCounter = 0
        pageNumber = 1
        self.panelVertShift = 0
        self.textGap    = (self.fontSize+4) * 4
        self.header = self.marginSize*1.5

        # set the font type from parameters
        self.loadFontType()

        # set the canvas settings
        self.setCanvasSettings(pageNumber)

        # loop through imageDataList and create the pages of PDF with all content based on row and column count provided
        for index, imageData in enumerate(self.imageDataList):
            image = imageData['path']
            panel = ImageReader(image)

            # figure out the image sizes based on the number of row's and column's
            panelWidth, panelHeight = self.getPanelSize(panel)

            # get each panels XY position on the pdf page
            panelX, panelY = self.getPanelPosition(panelWidth, panelHeight, rowCounter, colCounter)

            imageData.update({"panelX":panelX,
                              "panelY":panelY,
                              "panelW":panelWidth,
                              "panelH":panelHeight})

            # insert the image and stroke
            self.canvas.drawImage(panel, panelX, panelY, width=panelWidth, height=panelHeight)
            self.canvas.rect(panelX, panelY, width=panelWidth, height=panelHeight)

            # insert panel label and dialogue
            self.setPanelDialogueData(imageData)

            # set index number of each panel
            indexY = panelY - 10
            indexX = panelX + panelWidth
            self.canvas.setFillColor(self.fontColor)
            self.canvas.drawRightString(indexX, indexY, str(index+1))

            # check if shot status exists and set icon
            #self.setPanelShotStatus(imageData)

            # check if the current panel is new and set new icon
            #self.setPanelNewIcon(imageData)

            # set the shot label
            self.setPanelShotLabel(imageData)

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

    def exportPDF(self):
        """Exports the PDF and shows it in the file browser"""

        self.buildCanvas()

        # save the pdf
        self.canvas.save()

        if self.canvas:
            self.cleanUpAndShowPDF()

    def setCanvasSettings(self, pageNumber=1):
        """
        Sets the settings and header/footer of each pdf page
        :param pageNumber: The current page to be built
        """
        # set font type and size for the page
        self.canvas.setFont(self.fontType, self.fontSize)

        # set background color
        self.setBackground()

        # header bar
        self.setHeader()

        # footer bar
        self.setFooter(pageNumber)

    def cleanUpAndShowPDF(self):
        error = None
        for f in self.fileList:
            try:
                os.remove(f)
            except:
                error = "Unable to remove temporary files"
                pass
        if error:
            print error

        if os.path.isfile(self.outputFilePath):
            hiero.ui.openInOSShell(self.outputFilePath)

    def currentTimeString(self):
        # Returns current time epoch number as a string with underscores
        return str(time.time()).replace('.','_')

    def buildImageDataList(self):
        """
        Build the image list with meta data to be constructed into pdf
        """
        markerName = ""
        shotStatus = ""
        markerIndex = 1
        self.fileList = []
        for shot in self.shotCutList:
            thumbPath = "/tmp/%s_%s.jpg" % (shot.name(), self.currentTimeString())

            thumb = shot.thumbnail(shot.sourceIn()).save(thumbPath)

            # We create this list so that the files can be cleaned up after the save finishes
            self.fileList += [thumbPath]    
            dataDict = {'show':self.project,
                        'sequence':self.sequence,
                        'editVersion':"*Version*",
                        'setup':"*setup*",
                        'beat': shot.name(), # "*beat*",
                        'version':"*version*",
                        'path':thumbPath, #shot.source().filename(),
                        'dialogue': shot.parentTrack().name(),#"dialogue", #unicode(shot.recipe.getDialogue().decode('utf8')),
                        'shot':shot.source().name(),
                        'shotLabel':shot.name(),#unicode(urllib.unquote_plus(markerName).decode('utf8')),
                        'shotStatus': "*ShotStatus*", #shotStatus
            }
            self.imageDataList.append(dataDict)

    def getPdfParameters(self):
        """
        Fetch all the show parameters for pdf template
        """
        self.companyName            = "The Foundry" #self.mode.get('[company]')
        self.companyLogoPath        = "/Users/ant/Downloads/logo.jpg" #self.mode.get('[pdfCompanyLogoPath]')
        self.showLogoPath           = "/Users/ant/Downloads/show.jpg" #self.mode.get('[pdfShowLogoPath]')
        self.background             = 'white' #self.mode.get('[pdfBackground]')
        self.fontTypePath           = "/Users/ant/Library/Fonts/OpenSans-Regular.ttf" #self.mode.get('[pdfFontTypePath]')
        self.watermarkText          = "" #self.mode.get('[pdfWatermarkText]')
        self.fontSize               = 10 ##int(self.mode.get('[pdfFontSize]'))
        self.textColor              = 'black' #self.mode.get('[pdfFontColor]')
        self.editComment            = "Comments" #self.shotCutList.comments
        self.title                  = "My Amazing PDF" 
        self.title = xml.sax.saxutils.unescape(unicode(urllib.unquote_plus(self.title).decode('utf8')))

    def getBackground(self):
        """
        get the background, either get color object or ImageReader for image
        If color is darker than RGB(65, 65, 65) the text color will switch to white
        """
        """self.fileService.copyToLocal(self.background)
        if self.fileServiceLocal.exists(self.background):
            if not self.background.endswith(('.jpg', 'jpeg')):
                self.background = self.convertToJpeg(self.background)
            self.backgroundColor = ImageReader(self.repath.localize(self.background))"""
        bgColorImport = __import__("reportlab.lib.colors", globals(), locals(), [self.background], -1)
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

    #
    def convertToJpeg(self, source):
        """
        Convert different image formats to jpeg, due to reportLab not natively supporting other formats
        :param source: image file to be converted
        :return: new jpeg path
        """
        newSource = source.replace(os.path.splitext(source)[-1], '.jpeg')
        if not self.fileService.exists(newSource):
            flix.rendering.FlixNuke().convertImgFormat(source, newSource, [[1,1]])
        self.fileService.copyToLocal(newSource)
        return newSource

    def loadFontType(self):
        """
        Load the provided font from parameters as the default font to use
        """
        self.fontType = 'customFont'
        try:
            pdfmetrics.registerFont(TTFont(self.fontType, self.fontTypePath))
        except TTFError, e:
            raise "Incorrect PDF font type path %s"% self.fontTypePath

    def getPageSize(self):
        """
        get the page width and height based on the layout of the page
        :return: width and height
        """
        tmpImport = __import__("reportlab.lib.pagesizes", globals(), locals(), ['letter'], -1)
        if self.pageOrientation  == "landscape":
            letter = getattr(tmpImport, 'letter')
            self.pageSize = getattr(tmpImport, self.pageOrientation)(letter)
        else:
            self.pageSize = getattr(tmpImport, self.pageOrientation)

        return self.pageSize[0], self.pageSize[1]

    def getPanelSize(self, panel):
        """
        Calculate the width and height of each panel based on layout and row/column
        :param panel:
        :return:
        """
        if self.row >= self.column and not (self.row ==1 and self.column ==1):
            panelHeight = ((self.pageHeight-((self.marginSize*4)+self.textGap))/self.row) - (self.textGap*((self.row-1)/float(self.row)))
            panelWidth = panelHeight * (panel._width/float(panel._height) )
            if ((panelWidth*self.column)+(self.marginSize*(self.column+1))) >= self.pageWidth:
                panelWidth  = ((self.pageWidth-(self.marginSize*2))/self.column) - (self.marginSize*((self.column-1)/float(self.column)))
                panelHeight = panelWidth * (float(panel._height) / panel._width)
        else:
            panelWidth  = ((self.pageWidth-(self.marginSize*2))/self.column) - (self.marginSize*((self.column-1)/float(self.column)))
            panelHeight = panelWidth * (float(panel._height) / panel._width)

        return panelWidth, panelHeight

    def getPanelPosition(self, panelW, panelH, rowCounter, colCounter):
        """
        Calculate the XY position of the given panel, takes in consideration of panel size and number of row/column
        adds extra padding for dialogue and gaps between images for aesthetics
        :param panelW: panel width
        :param panelH: panel height
        :param rowCounter: the current row index
        :param colCounter: the current column index
        :return: panel XY positions as tuple
        """
        # calculate the gap between each image based on image size and page size
        imageGapW = ((self.pageWidth-(self.marginSize*2)) - (panelW * self.column))/(self.column-1) if self.column > 1 else 0
        imageGapH = ((self.pageHeight - ((self.header+(self.fontSize*2))*2)) - (panelH * self.row))/self.row if self.row > 1 else 30

        # calculate where each images x,y positions are
        panelX =  ((panelW + imageGapW) * colCounter) + self.marginSize
        panelY =  ((self.pageHeight-(self.header+(self.fontSize*2)))  - ((panelH+imageGapH)*(rowCounter+1)))
        if rowCounter == 0:
            panelYExpected = ((self.pageHeight-(self.header+(self.fontSize*2)))  - (panelH*(rowCounter+1)))
            if panelY != panelYExpected:
                self.panelVertShift = panelY - panelYExpected
        panelY -= self.panelVertShift

        return panelX, panelY

    def setPanelDialogueData(self, imageData):
        """
        Set the panel label and dialogue for the given panel and place it in the appropriate position based on layout
        :param imageData: dictionary object with panel metaData
        :return: Table object
        """
        panelX = imageData.get("panelX")
        panelY = imageData.get("panelY")
        panelH = imageData.get("panelH")
        panelW = imageData.get("panelW")
        # set the panel label and dialogue for each panel
        #panelLabel = "%04d-%s"%(int(imageData['setup']),imageData['version']) if imageData['version']>1 else "%04d"%int(imageData['setup'])
        if not imageData['beat'] == "p":
            panelLabel = "%s-%s"%(imageData['beat'], "pan")
        panelData = {'panelLabel':panelLabel,
                     'textColor':self.textColor,
                     'fontSize':self.fontSize,
                     'fontName':self.fontType,
                     'dialogue':imageData['dialogue'].replace("\n", "<br/>")}

        panelName = Paragraph('''<para align=center spaceb=3>
                                 <font name=%(fontName)s size=11 color=%(textColor)s>
                                 <b>%(panelLabel)s</b></font><br/>
                                 <font name=%(fontName)s size=%(fontSize)s color=%(textColor)s>
                                 %(dialogue)s</font></para>'''%panelData, self.styles['BodyText'])

        data = [[panelName]]

        # adjust dialogue placement based on row/column layout
        if self.column == 1 and not self.row == 1:
            textX = panelX + panelW + self.marginSize
            textY = (panelY + panelH) - self.textGap
            textWidth = self.pageWidth - panelW - (self.marginSize*3)
        else:
            textWidth = panelW
            textX = panelX
            textY = panelY - self.textGap

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

    def setPanelShotStatus(self, imageData):
        """
        Sets the shots status of the given panel if status exists, aligned to the bottom left of the panel
        :param imageData: dictionary object with panel metaData
        """
        panelX = imageData.get("panelX")
        panelY = imageData.get("panelY")
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
                    statusX = panelX
                    statusY = panelY - statusH - 2
                    self.canvas.drawImage(statusIconReader, statusX, statusY, statusW, statusH)

    def setPanelNewIcon(self, imageData):
        """
        Sets the panels new icons if the panel is new since the last editorial publish, aligned to the top right of the panel
        :param imageData: dictionary object with panel metaData
        """
        panelX = imageData.get("panelX")
        panelY = imageData.get("panelY")
        panelH = imageData.get("panelH")
        panelW = imageData.get("panelW")
        if imageData['shot'].label in self.newShots:
            newLabelW = 25
            newLabelH = 10
            newLabelX = panelX + panelW - newLabelW
            newLabelY = panelY + panelH + 2
            self.canvas.setFillColor(limegreen)
            self.canvas.setStrokeColor(black)
            self.canvas.rect(newLabelX, newLabelY, newLabelW, newLabelH, fill=True, stroke=True)
            newTextX = newLabelX + 2
            newTextY = newLabelY + 2
            self.canvas.setFillColor(black)
            self.canvas.drawString(newTextX, newTextY, 'NEW')

    def setPanelShotLabel(self, imageData):
        """
        sets the panels shot label if belongs to a shot, aligned on the top left of the panel
        :param imageData: dictionary object with panel metaData
        """
        panelX = imageData.get("panelX")
        panelY = imageData.get("panelY")
        panelH = imageData.get("panelH")
        if imageData.get('shotLabel'):
            shotLabelX = panelX
            shotLabelY = panelY + panelH + 2
            self.canvas.setFillColor(self.textColor)
            self.canvas.drawString(shotLabelX, shotLabelY, imageData.get('shotLabel'))

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
        panelName = Paragraph('''<para align=center spaceb=3>
                                  <font name=%(fontName)s size=%(size)s color=%(textColor)s>%(msg1)s<br/>
                                  %(msg2)s</font></para>'''%privacyInfo, self.styles['BodyText'])
        privacyTable = Table([[panelName]], colWidths=(self.pageWidth-(self.marginSize*2)))
        privacyTable.setStyle(TableStyle([('VALIGN',(-1,-1),(-1,-1),'TOP')]))
        privacyTable.wrapOn(self.canvas, self.marginSize, 10)
        privacyTable.drawOn(self.canvas, self.marginSize, 10)

