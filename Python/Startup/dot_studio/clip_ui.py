# A scrubb-able thumbnail Widget for displaying Clips
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
import hiero.core

class ThumbnailWidget(QtWidgets.QWidget):
    def __init__(self, sourceItem=None):
        """
        A scrubb-able Clip thumbnail view for including in Custom widgets
        sourceItem can be either a BinItem, a Clip or a Sequence
        """

        QtWidgets.QWidget.__init__(self)

        #self.setParent(hiero.ui.mainWindow())
        # A QWidget for displaying
        self.sourceItem = sourceItem

        self.setGeometry(240, 160, 320, 180)

        # In the case a BinItem is passed, take the activeItem
        if isinstance(sourceItem, hiero.core.BinItem):
        	self.sourceItem = sourceItem.activeItem()
        elif isinstance(sourceItem, hiero.core.TrackItem):
            self.sourceItem = sourceItem.source()

        imageErrorIcon = QtGui.QIcon("icons:MediaOffline.png")
        currentPosterFrameIndicator = QtGui.QIcon("icons:PosterFrame.png")
        self.imageErrorPixmap = imageErrorIcon.pixmap(imageErrorIcon.actualSize(QtCore.QSize(48, 48)))
        self.currentPosterFramePixmap = currentPosterFrameIndicator.pixmap(currentPosterFrameIndicator.actualSize(QtCore.QSize(26, 26)))

        # Some initial values
        self.currentFrame = self.sourceItem.posterFrame()
        self.currentXPos = 1

        # To determine if visual cue for Playhead as mouse is dragged is shown
        self.showPlayhead = True
        self.playheadColor = QtGui.QColor(246,146,30, 255)
        self.setWindowFlags( QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint )
        self.setAttribute( QtCore.Qt.WA_TranslucentBackground, True ) 
        self.mouseInside = False

        self.initUI()


    def keyPressEvent(self, e):
        """Handle J, L key events and close if Escape is pressed"""
        if e.key() == QtCore.Qt.Key_Escape or e.key() == 47:
            self.close()
        elif e.key() == QtCore.Qt.Key_J:
            frame = self.currentFrame - 1
            self.updatePosterFrameForFrame(frame)
        	
        elif e.key() == QtCore.Qt.Key_L:
            frame = self.currentFrame + 1
            self.updatePosterFrameForFrame(frame)


    def enterEvent(self, event):
        self.mouseInside = True


    def setPosterFrameForCurrentFrame(self):
        self.sourceItem.setPosterFrame( self.currentFrame )

    def leaveEvent(self, event):
        self.mouseInside = False
        #self.setPosterFrameForCurrentFrame()
        self.close()

    def showAt(self, pos):
        self.move(pos.x()-self.width()/2, pos.y()-self.height()/2)
        self.show()


    def initUI(self):
        layout = QtWidgets.QGridLayout()
        self.setMouseTracking(True)

        try:
            qImage = self.sourceItem.thumbnail()
            self.posterFramePixmap = QtGui.QPixmap().fromImage(qImage)
        except:
            self.posterFramePixmap = self.imageErrorPixmap

        self.thumbGraphicsScene = QtWidgets.QGraphicsScene(self)

        self.thumbGraphicsView = QtWidgets.QGraphicsView(self.thumbGraphicsScene)
        self.thumbGraphicsView.setGeometry(self.rect())
        self.thumbGraphicsView.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.thumbGraphicsView.mouseMoveEvent = self.mouseMoveEvent

        self.thumbGraphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.thumbGraphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.thumbGraphicsView.setMouseTracking(True)

        self.thumbGraphicsScenePixMapItem = QtWidgets.QGraphicsPixmapItem(self.posterFramePixmap)
        self.thumbGraphicsScene.addItem(self.thumbGraphicsScenePixMapItem)

        self.currentPosterFramePixMapItem = QtWidgets.QGraphicsPixmapItem(self.currentPosterFramePixmap)
        self.currentPosterFramePixMapItem.setPos(5, int(0.7*float(self.thumbGraphicsView.rect().height())))
        self.currentPosterFramePixMapItem.setVisible(False)
        self.thumbGraphicsScene.addItem(self.currentPosterFramePixMapItem)

        self.thumbGraphicsView.setFixedWidth(self.rect().width())

        self.playheadLine = QtWidgets.QGraphicsLineItem()
        self.pen = QtGui.QPen(self.playheadColor, 2)
        self.playheadLine.setPen(self.pen)
        self.playheadLine.setVisible(False)
        self.thumbGraphicsScene.addItem(self.playheadLine)

        self.thumbGraphicsView.setMouseTracking(True)

        layout.addWidget(self.thumbGraphicsView)
        self.setLayout(layout)

    def updateOverlays(self):
        """
        Re-draws the playhead if playhead rendering enabled
        """
        if self.showPlayhead:
            self.playheadLine.setVisible(True)
            self.playheadLine.setLine(self.currentXPos, self.thumbGraphicsView.rect().y(), self.currentXPos, self.thumbGraphicsView.rect().y()+self.thumbGraphicsView.rect().height())
        else:
            self.playheadLine.setVisible(False)

        if int(self.currentFrame) == int(self.sourceItem.posterFrame()):
            self.currentPosterFramePixMapItem.setVisible(True)
        else:
            self.currentPosterFramePixMapItem.setVisible(False)

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
            currentPoint = self.thumbGraphicsView.mapFromGlobal(QtGui.QCursor.pos())
            self.currentXPos = currentPoint.x()

            # Avoid zero division
            if self.currentXPos<1:
                self.currentXPos = 1

            mosXposPercentage = float(self.currentXPos)/float(self.thumbGraphicsView.rect().width())
            self.updatePosterFrameForPlaybackPercentage(mosXposPercentage)
            self.updateOverlays()


    def mousePressEvent(self, event):
        self.setPosterFrameForCurrentFrame()

def showThumbForActiveItem():
    view = hiero.ui.activeView()

    if not view or not hasattr(view, 'selection'):
        return
        
    selection = view.selection()
    if len(selection) != 1:
        return

    item = selection[0]
    T = ThumbnailWidget(item)
    T.showAt(QtGui.QCursor.pos())

act = hiero.ui.createMenuAction("Clip Thumb", showThumbForActiveItem)
act.setShortcut("/")
w = hiero.ui.findMenuAction("Window")
w.menu().addAction(act)