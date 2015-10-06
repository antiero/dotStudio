import hiero.ui
import hiero.core
from PySide import QtGui, QtCore

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
        self.setResizeMode(QtGui.QListView.ResizeMode.Adjust)
        self.setUniformItemSizes(True)

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

    def getFilmStripImagesForCurrentViewer(self):
        seq = hiero.ui.activeSequence()
        trackItems = self.createTrackItemStripForSequence(seq)
        numItems = len(trackItems)
        #print "Got %i trackItems" % numItems
        images = []
        for i in range(0, numItems):
            try:
                qimage = trackItems[i].thumbnail()
                pixmap = QtGui.QPixmap.fromImage(qimage.scaledToWidth(300))
                images += [pixmap]
            except:
                pass

        return images        

    def updateView(self):
        images = self.getFilmStripImagesForCurrentViewer()
        self.lm = MyListModel(images, self)
        self.setModel(self.lm)

class FilmStripPanel(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__( self )
        self.setWindowTitle( "Film Strip" ) 
        self.setObjectName( "uk.co.thefoundry.filmstrip" )
        self.setWindowIcon( QtGui.QIcon("icons:TabMedia.png") )        
        self.initUI()
        hiero.core.events.registerInterest("kPlaybackClipChanged", self._updateViewCallback)
        hiero.core.events.registerInterest("kPlaybackStarted", self._updateViewCallback)
        hiero.core.events.registerInterest("kPlaybackStopped", self._updateViewCallback)

    def _updateViewCallback(self, event):
        self.updateView()

    def initUI(self):
        layout = QtGui.QFormLayout(self)
        self.contactSheet = MyListView()
        # create table
        self.list_data = []
        self.listModel = MyListModel(self.list_data, self)
        self.clearSelectedMarkersButton = QtGui.QPushButton("Refresh")
        self.clearSelectedMarkersButton.clicked.connect(self.updateView)
        layout.addRow("",self.clearSelectedMarkersButton)
        layout.addRow("",self.contactSheet)
        self.setLayout(layout)

    def createTrackItemStripForSequence(self, sequence):
        if not sequence:
            return []

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

    def getFilmStripImagesForCurrentViewer(self):
        seq = hiero.ui.activeSequence()
        trackItems = self.createTrackItemStripForSequence(seq)
        numItems = len(trackItems)
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
        images = self.getFilmStripImagesForCurrentViewer()
        self.listModel = MyListModel(images, self)
        self.contactSheet.setModel(self.listModel)

#filmStrip = FilmStripPanel()
#hiero.ui.registerPanel( "uk.co.thefoundry.filmstrip", filmStrip )

#wm = hiero.ui.windowManager()
#wm.addWindow( filmStrip )