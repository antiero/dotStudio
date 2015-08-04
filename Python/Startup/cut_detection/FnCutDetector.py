import hiero.ui
import hiero.core
from PySide import QtGui, QtCore
import os, urlparse
import nuke

class MyListModel(QtCore.QAbstractListModel): 
    def __init__(self, datain, parent=None, *args): 
        """ datain: a list where each item is a row
        """
        QtCore.QAbstractListModel.__init__(self, parent, *args) 
        self.listdata = datain

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.listdata) 

    def data(self, index, role):
        if index.isValid() and role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(self.listdata[index.row()])
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return "Shot " + str(index.row())

class MyListView(QtGui.QListView):
    """docstring for MyListView"""
    def __init__(self):
        super(MyListView, self).__init__()
        # show in Icon Mode
        self.setViewMode(QtGui.QListView.IconMode)
        #self.setResizeMode(QtGui.QListView.ResizeMode.Adjust)
        self.setIconSize(QtCore.QSize(200,200))
        self.setUniformItemSizes(True)
        # self.setDefaultDropAction(QtCore.Qt.MoveAction)
        # self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        # self.setDragDropOverwriteMode(True)
        # self.setDragEnabled(True)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)


        # create table
        list_data = []
        self.lm = MyListModel(list_data, self)


    def createTrackItemStripForSequence(self, sequence):
        T = sequence.duration()
        trackItems = []
        for frame in range(0,T):
            ti = sequence.trackItemAt(frame)
            if len(trackItems)==0:
                trackItems+=[ti]

            else:
                if ti not in trackItems:
                    trackItems.append(ti)
        return trackItems

    def getCutDetectorImagesForCurrentViewer(self):
        seq = hiero.ui.activeSequence()
        trackItems = self.createTrackItemStripForSequence(seq)
        numItems = len(trackItems)
        print "Got %i trackItems" % numItems
        images = []
        for i in range(0, numItems):
            try:
                qimage = trackItems[i].thumbnail(trackItems[i].sourceIn())
                pixmap = QtGui.QPixmap.fromImage(qimage.scaledToWidth(200))
                images += [pixmap]
            except:
                pass

        return images        

    def updateView(self):
        images = self.getCutDetectorImagesForCurrentViewer()
        self.lm = MyListModel(images, self)
        self.setModel(self.lm)

class FnCutDetectorPanel(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__( self )
        self.setWindowTitle( "Cut Detector" ) 
        self.setObjectName( "uk.co.thefoundry.cutdetection" )
        self.setWindowIcon( QtGui.QIcon("icons:TimelineToolJoin.png") )        
        self.initUI()

        self.setAcceptDrops(True)

        self.cutDetector = []
        self.inputClip = []
        self.cutPoints = []
        self.project = None
        self.clipsBin = None
        self.clip = None
        self.clipPath = None
        self.decisionKnob = None
        self.first = None
        self.last = None

    def _decisionValues(self, knob, first, last):
        """
        Returns a vector of decision knobValues, over a range of 'first' to 'last' frames at which there is a '1'
        """

        print "Returning value for knob %s over range %i to %i frames" %  (knob.name(), first, last)

        decArray = [0] * int((last-first)+1)
        for x in range(first,last):
            decArray[x] = knob.valueAt(x)

        return decArray

    def _generateCutPoints(self):
        """Gets a vector of frames for a given inputClip with first and last frame where cuts have been detected"""

        cutPoints = []
        self.decisionKnob = self.cutDetector["decision"]
        if self.decisionKnob:
            DEC = self._decisionValues(self.decisionKnob, self.first, self.last)
            cutPoints = [i for i, x in enumerate(DEC) if x == 1]

        print "Got cut points : %s" % str(cutPoints)
        return cutPoints

    def _updateViewCallback(self, event):
        self.updateView()

    def initUI(self):
        layout = QtGui.QFormLayout(self)

        self.spacingSlider = QtGui.QSlider()
        #self.spacingSlider.valueChanged.connect(self._spacingSliderChanged)

        self.mainClipImageLabel = QtGui.QLabel()
        cwd = os.path.dirname(os.path.realpath(__file__))
        self.mainClipImageLabel.setPixmap(QtGui.QPixmap(os.path.join(cwd, "dropZone.png")))
        self.mainClipImageLabel.setAcceptDrops(True)            

        self.contactSheet = MyListView()
        self.contactSheet.setAcceptDrops(False)
        # create table
        self.list_data = []
        self.listModel = MyListModel(self.list_data, self)

        self.topLayout = QtGui.QHBoxLayout()

        self.clearSelectedMarkersButton = QtGui.QPushButton("Update")
        self.clearSelectedMarkersButton.setAcceptDrops(False)
        self.clearSelectedMarkersButton.clicked.connect(self.updateView)
        self.topLayout.addWidget(self.mainClipImageLabel)
        self.topLayout.addWidget(self.clearSelectedMarkersButton)
        #self.topLayout.addWidget(self.spacingSlider)

        layout.addRow("",self.topLayout)
        layout.addRow("",self.contactSheet)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        event.accept()        

    def dropEvent(self, event):
        mimeText = event.mimeData().text()
        p = urlparse.urlparse(mimeText)
        finalPath = os.path.abspath(os.path.join(p.netloc, p.path))
        print "File dropped:\n" + finalPath

        askResult = nuke.ask("Detect cuts for Clip: %s" % finalPath)
        print askResult
        if askResult:
            self.clipPath = finalPath.replace('\n','')
            self.createTimelineFromDroppedClip(self.clipPath)

    def createTimelineFromDroppedClip(self, clipPath):
        nuke.scriptClear()
        nuke.scriptReadFile('/Users/ant/.nuke/Python/Startup/cut_detection/cutDetector.nk')
        self.inputNode = nuke.toNode('InputClip')
        self.cutDetector = nuke.toNode('CutDetector')
        self.inputNode['file'].fromUserText(clipPath)
        self.first = self.inputNode['first'].value()
        self.last = self.inputNode['last'].value()
        nuke.execute("CutDetector.CurveTool1", self.first, self.last)

        #nuke.executeBackgroundNuke(nuke.EXE_PATH, [nuke.toNode("CutDetector.CurveTool1")], 
        #                           nuke.FrameRanges("%i-%i" % (self.first, self.last)),
        #                           ['main'], {'maxThreads':4, 'maxCache':'4G'})
        

    def _spacingSliderChanged(self, value=0):
        self.contactSheet.setSpacing(value)

    def createTrackItemStripForSequence(self, sequence):
        T = sequence.duration()
        trackItems = []
        for frame in range(0,T):
            ti = sequence.trackItemAt(frame)
            if len(trackItems)==0:
                trackItems+=[ti]

            else:
                if ti not in trackItems:
                    trackItems.append(ti)
        return trackItems

    def createSequenceFromCurrentClip(self):
        if self.clipPath:
            self.sequence = hiero.core.Sequence("CutSequence")
            self.clip = hiero.core.Clip(self.clipPath)
            self.sequence = hiero.core.Sequence(self.clip.name())
            if not self.project or not self.clipsBin:
                self.project = hiero.core.newProject()
                self.clipsBin = self.project.clipsBin()

            self.clipsBin.addItem(hiero.core.BinItem(self.clip))
            self.clipsBin.addItem(hiero.core.BinItem(self.sequence))
            self.sequence.addClip(self.clip,0)
            hiero.ui.openInTimeline(self.sequence.binItem())

    def getCutDetectorImagesForCurrentClip(self):
        cuts = self._generateCutPoints()
        numCuts = len(cuts)
        print "getCutDetectorImagesForCurrentClip: CUTS: %s" % str(cuts)
        self.createSequenceFromCurrentClip()

        images = []
        for cutTime in cuts:
            qimage = self.clip.thumbnail(cutTime)
            pixmap = QtGui.QPixmap.fromImage(qimage.scaledToWidth(100))
            images += [pixmap]

        return images

    def updateView(self):
        images = self.getCutDetectorImagesForCurrentClip()
        self.listModel = MyListModel(images, self)
        self.contactSheet.setModel(self.listModel)