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
            #return QtCore.QVariant(self.listdata[index.row()])

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

    def getSceneDetectorImagesForCurrentViewer(self):
        seq = hiero.ui.activeSequence()
        trackItems = self.createTrackItemStripForSequence(seq)
        numItems = len(trackItems)
        print "Got %i trackItems" % numItems
        images = []
        for i in range(0, numItems):
            try:
                qimage = trackItems[i].thumbnail()
                pixmap = QtGui.QPixmap.fromImage(qimage.scaledToWidth(200))
                images += [pixmap]
            except:
                pass

        return images        

    def updateView(self):
        images = self.getSceneDetectorImagesForCurrentViewer()
        self.lm = MyListModel(images, self)
        self.setModel(self.lm)

class FnSceneDetectorPanel(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__( self )
        self.setWindowTitle( "Scene Detector" ) 
        self.setObjectName( "uk.co.thefoundry.scenedetection" )
        self.setWindowIcon( QtGui.QIcon("icons:TimelineToolJoin.png") )        
        self.initUI()

        self.setAcceptDrops(True)
        #hiero.core.events.registerInterest("kPlaybackStarted", self._updateViewCallback)
        #hiero.core.events.registerInterest("kPlaybackStopped", self._updateViewCallback)

    def _updateViewCallback(self, event):
        self.updateView()

    def initUI(self):
        layout = QtGui.QFormLayout(self)

        self.spacingSlider = QtGui.QSlider()


        #self.spacingSlider.valueChanged.connect(self._spacingSliderChanged)

        self.mainClipImageLabel = QtGui.QLabel()
        self.mainClipImageLabel.setPixmap(QtGui.QPixmap("/Users/ant/.nuke/Python/Startup/scene_detection/dropZone.png"))
        self.mainClipImageLabel.setAcceptDrops(True)            

        self.contactSheet = MyListView()
        self.contactSheet.setAcceptDrops(False)
        # create table
        self.list_data = []
        self.listModel = MyListModel(self.list_data, self)
        #self.contactSheet.setFixedHeight(120)

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

        askResult = nuke.ask("Detect Scenes for Clip: %s" % finalPath)
        print askResult
        if askResult:
          self.createTimelineFromDroppedClip(finalPath)

    def createTimelineFromDroppedClip(self, clipPath):
        nuke.scriptClear()
        nuke.scriptReadFile('/Users/ant/.nuke/Python/Startup/scene_detection/sceneDetect.nk')
        inputNode = nuke.toNode('InputClip')
        detector = nuke.toNode('SceneDetector')
        inputNode['file'].fromUserText(clipPath)
        first = inputNode['first'].value()
        last = inputNode['last'].value()
        nuke.execute("SceneDetector.CurveTool1", first, last)

    def _spacingSliderChanged(self, value=0):
        #print "Slider changed to %i" % int(value)
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

    def getSceneDetectorImagesForCurrentViewer(self):
        seq = hiero.ui.currentViewer().player().sequence()
        if not seq:
            return []

        trackItems = self.createTrackItemStripForSequence(seq)
        numItems = len(trackItems)
        print "Got %i trackItems" % numItems
        images = []
        for i in range(0, numItems):
            try:
                qimage = trackItems[i].thumbnail()
                pixmap = QtGui.QPixmap.fromImage(qimage.scaledToWidth(100))
                images += [pixmap]
            except:
                pass

        return images        

    def updateView(self):
        images = self.getSceneDetectorImagesForCurrentViewer()
        self.listModel = MyListModel(images, self)
        self.contactSheet.setModel(self.listModel)