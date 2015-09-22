# A scrubb-able thumbnail Widget for displaying Clips
from PySide import QtCore
from PySide import QtGui
import hiero.core

class ThumbnailWidget(QtGui.QWidget):
    def __init__(self, sourceItem=None):
        """
        A scrubb-able Clip thumbnail view for including in Custom widgets
        sourceItem can be either a BinItem, a Clip or a Sequence
        """

        QtGui.QWidget.__init__(self)

        self.setParent(hiero.ui.mainWindow())
        # A QWidget for displaying
        self.sourceItem = sourceItem

        self.setGeometry(240, 160, 320, 180)

        # In the case a BinItem is passed, take the activeItem
        if isinstance(sourceItem, hiero.core.BinItem):
        	self.sourceItem = sourceItem.activeItem()
        elif isinstance(sourceItem, hiero.core.TrackItem):
            self.sourceItem = sourceItem.source()

        imageErrorIcon = QtGui.QIcon("icons:MediaOffline.png")
        self.imageErrorPixmap = imageErrorIcon.pixmap(imageErrorIcon.actualSize(QtCore.QSize(48, 48)))

        # Some initial values
        self.currentFrame = 1
        self.currentXPos = 1

        # To determine if visual cue for Playhead as mouse is dragged is shown
        self.showPlayhead = True
        self.playheadColor = QtGui.QColor(246,146,30, 255)
        self.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground); 
        self.mouseInside = False

        self.initUI()


    def keyPressEvent(self, e):
        """Handle J, L key events and close if Escape is pressed"""
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif e.key() == QtCore.Qt.Key_J:
            frame = self.currentFrame - 1
            self.updatePosterFrameForFrame(frame)
        	
        elif e.key() == QtCore.Qt.Key_L:
            frame = self.currentFrame + 1
            self.updatePosterFrameForFrame(frame)


    def enterEvent(self, event):
        self.mouseInside = True

    def leaveEvent(self, event):
        self.mouseInside = False
        self.sourceItem.setPosterFrame( self.currentFrame )
        self.close()

    def showAt(self, pos):
        self.move(pos.x()-self.width()/2, pos.y()-self.height()/2)
        self.show()        

    def initUI(self):
        layout = QtGui.QGridLayout()
        self.setMouseTracking(True)

        try:
            qImage = self.sourceItem.thumbnail()
            self.posterFramePixmap = QtGui.QPixmap().fromImage(qImage)
        except:
            self.posterFramePixmap = self.imageErrorPixmap

        self.thumbGraphicsScene = QtGui.QGraphicsScene(self)

        self.thumbGraphicsView = QtGui.QGraphicsView(self.thumbGraphicsScene)
        self.thumbGraphicsView.setGeometry(self.rect())
        self.thumbGraphicsView.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.thumbGraphicsView.mouseMoveEvent = self.mouseMoveEvent

        self.thumbGraphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.thumbGraphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.thumbGraphicsView.setMouseTracking(True)

        self.thumbGraphicsScenePixMapItem = QtGui.QGraphicsPixmapItem(self.posterFramePixmap)
        self.thumbGraphicsScene.addItem(self.thumbGraphicsScenePixMapItem)

        self.thumbGraphicsView.setFixedWidth(self.rect().width())

        self.playheadLine = QtGui.QGraphicsLineItem()
        self.playheadLine.setPen(QtGui.QPen(self.playheadColor, 2))
        self.playheadLine.setVisible(False)
        self.thumbGraphicsScene.addItem(self.playheadLine)

        self.thumbGraphicsView.setMouseTracking(True)

        layout.addWidget(self.thumbGraphicsView)
        self.setLayout(layout)

    def updatePlayheadPosition(self):
        """
        Re-draws the playhead if playhead rendering enabled
        """
        if self.showPlayhead:
            self.playheadLine.setVisible(True)
            self.playheadLine.setLine(self.currentXPos, self.thumbGraphicsView.rect().y(), self.currentXPos, self.thumbGraphicsView.rect().y()+self.thumbGraphicsView.rect().height())
        else:
            self.playheadLine.setVisible(False)

    def updatePosterFrameForFrame(self, frame):
        # Updates the current poster frame, specified by frame
        self.currentFrame = frame
        try:
            qImage = self.sourceItem.thumbnail(self.currentFrame)
            posterFramePixmap = QtGui.QPixmap().fromImage(qImage)
        except:
            posterFramePixmap = self.imageErrorPixmap

        self.thumbGraphicsScenePixMapItem.setPixmap(posterFramePixmap)




    def updatePosterFrameForPlaybackPercentage(self, perc):
        # Sets the thumbnail for the frame at a given playback percentage

        if isinstance(self.sourceItem, hiero.core.Clip):
            sourceIn = self.sourceItem.sourceIn()
            sourceOut = self.sourceItem.sourceOut()
            duration = sourceOut - sourceIn
            self.currentFrame = int(float(sourceIn) + (perc * float(duration)))
        elif isinstance(self.sourceItem, hiero.core.Sequence):
            duration = self.sourceItem.duration()
            self.currentFrame = perc * float(duration)
        try:
            qImage = self.sourceItem.thumbnail(self.currentFrame)
            posterFramePixmap = QtGui.QPixmap().fromImage(qImage).scaled(self.thumbGraphicsView.size(), aspectRadioMode = QtCore.Qt.KeepAspectRatio, mode = QtCore.Qt.SmoothTransformation)
        except:
            posterFramePixmap = self.imageErrorPixmap

        self.thumbGraphicsScenePixMapItem.setPixmap(posterFramePixmap)


    def mouseMoveEvent(self, event):
        # When the mouse moves over the widget it will force an update of the poster frame
        if event.buttons() == QtCore.Qt.NoButton:
            self.currentXPos = event.pos().x()
            mosXposPercentage = float(self.currentXPos)/float(self.rect().width())
            self.updatePosterFrameForPlaybackPercentage(mosXposPercentage)
            self.updatePlayheadPosition()

        super(ThumbnailWidget, self).mouseMoveEvent(event)

def showThumbForActiveItem():
    view = hiero.ui.activeView()

    if not view:
        return
        
    selection = view.selection()
    if len(selection) != 1:
        return

    item = selection[0]
    T = ThumbnailWidget(item)
    T.showAt(QtGui.QCursor.pos())

act = hiero.ui.createMenuAction("Clip Thumb", showThumbForActiveItem)
act.setShortcut("?")
w = hiero.ui.findMenuAction("Window")
w.menu().addAction(act)