import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtWidgets
import hiero.ui

def visibleShotAtTime(sequence, t):
  """visibleShotAtTime(sequence, t) -> Returns the visible TrackItem in a Sequence (sequence) at a specified frame (time).
  @param: sequence - a core.Sequence
  @param: t - an integer (frame no.) at which to return the current TrackItem
  returns: hiero.core.TrackItem"""
  
  shot = sequence.trackItemAt(t)
  if shot == None:
    return shot
    
  elif shot.isMediaPresent() and shot.isEnabled():
    return shot
  
  else:
    # If we're here, the Media is offline or disabled... work out what's visible on other tracks...
    badTrack = shot.parent()
    vTracks = list(sequence.videoTracks())
    vTracks.remove(badTrack)
    for track in reversed(vTracks):
      trackItems = track.items()
      for shotCandidate in trackItems:
        if shotCandidate.timelineIn() <= t and shotCandidate.timelineOut() >= time:
          if shotCandidate.isMediaPresent() and shotCandidate.isEnabled():
            shot = shotCandidate
            break
  
  return shot

class ClipInfoWindow(QtWidgets.QWidget):
    def __init__(self, *args):
        QtWidgets.QWidget.__init__(self, *args)
        # setGeometry(x_pos, y_pos, width, height)
        self.setGeometry(240, 160, 480, 320)
        self.setWindowTitle("Clip Info")

        self.setAttribute( QtCore.Qt.WA_TranslucentBackground, True )  
        self.setWindowFlags( QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint )
        self.setWindowOpacity(0.9)
        self.setMouseTracking(True)

        self.draggable = True
        self.dragging_threshould = 2
        self.__mousePressPos = None
        self.__mouseMovePos = None

        self.infoDict = []
        self.infoDict += [{"label": "Clip", "value": "None", "enabled":True}]
        self.infoDict += [{"label": "Duration", "value": 0, "enabled":True}]

        self.table_model = MyTableModel(self, self.infoDict)
        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.resizeColumnsToContents()

        # set font
        font = QtGui.QFont()
        font.setPixelSize(16)
        self.table_view.setFont(font)

        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setVisible(False)
        self.table_view.verticalScrollBar().setDisabled(True);
        self.table_view.horizontalScrollBar().setDisabled(True);
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        self.table_view.setStyleSheet("QTableView::item { border-width:0px; border-right: 1px solid gray; }")

        # set column width to fit contents (set font first!)
        self.table_view.setSortingEnabled(False)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table_view)
        sizeGrip = QtWidgets.QSizeGrip(self)
        sizeGrip.setStyleSheet("QSizeGrip { height:12px; }")
        layout.addWidget(sizeGrip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight);
        self.setMinimumSize(160, 160)        
        self.setLayout(layout)

        hiero.core.events.registerInterest("kPlaybackClipChanged", self.clipChanged)
        hiero.core.events.registerInterest("kPlaybackStarted", self.clipChanged)
        hiero.core.events.registerInterest("kPlaybackStopped", self.clipChanged)

    def clipChanged(self, event):
    	self.updateTableView()

    def showAt(self, pos):
        # BUILD DATA WHEN SHOWN - is this the best time to do this?
        self.updateTableView()
        self.move(pos.x()-self.width()/2, pos.y()-self.height()/2)
        self.show()

    def keyPressEvent(self, e):
        """Close the popover if Escape is pressed"""            
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    def updateTableView(self):
    	self.__buildDataForCurrentClip()
        self.table_model = MyTableModel(self, self.infoDict)
        self.table_view.setModel(self.table_model)
        self.table_view.resizeColumnsToContents()

    def formatStringFromSeq(self, seq):
    	seq = seq.format()
    	height = seq.height()
    	width = seq.width()
    	pixel_aspect = seq.pixelAspect()
    	formatString = "%i x %i, %f" % (width, height, pixel_aspect)
    	return formatString

    def __buildDataForCurrentClip(self):
        cv = hiero.ui.currentViewer()
        seq = cv.player().sequence()
        self.infoDict = []
        if not seq:
            return
        elif isinstance(seq, hiero.core.Clip):
            self.infoDict += [{"label": "name", "value": seq.name(), "enabled":True}]
            self.infoDict += [{"label": "format", "value": self.formatStringFromSeq(seq), "enabled":True}] 
            self.infoDict += [{"label": "duration", "value": seq.duration(), "enabled":True}]
            self.infoDict += [{"label": "fps", "value": str(seq.framerate()), "enabled":True}]
            self.infoDict += [{"label": "filename", "value": seq.mediaSource().fileinfos()[0].filename(), "enabled":True}]
        elif isinstance(seq, hiero.core.Sequence):
			currentShot = visibleShotAtTime(seq, cv.time())
			self.infoDict += [{"label": "name", "value": seq.name(), "enabled":True}]
			self.infoDict += [{"label": "shot", "value": currentShot.name(), "enabled":True}]
			self.infoDict += [{"label": "fps", "value": str(seq.framerate()), "enabled":True}]
			self.infoDict += [{"label": "duration", "value": seq.duration(), "enabled":True}]

    def paintEvent(self, event):
        # get current window size
        s = self.size()
        qp = QtGui.QPainter()
        #qp.setRenderHint(QPainter.Antialiasing, True)
        qp.begin(self)
        qp.setBrush( self.palette().window() )
        qp.setPen(QtCore.Qt.black)
        qp.drawRoundedRect(0,0,s.width(), s.height(), 10, 10)
        qp.end()
 
    def mousePressEvent(self, event):
        if self.draggable and event.button() == QtCore.Qt.LeftButton:
            self.__mousePressPos = event.globalPos()                # global
            self.__mouseMovePos = event.globalPos() - self.pos()    # local
        super(ClipInfoWindow, self).mousePressEvent(event)
 
    def mouseMoveEvent(self, event):
        if self.draggable and event.buttons() & QtCore.Qt.LeftButton:
            globalPos = event.globalPos()
            moved = globalPos - self.__mousePressPos
            if moved.manhattanLength() > self.dragging_threshould:
                # move when user drag window more than dragging_threshould
                diff = globalPos - self.__mouseMovePos
                self.move(diff)
                self.__mouseMovePos = globalPos - self.pos()
        super(ClipInfoWindow, self).mouseMoveEvent(event)
 
    def mouseReleaseEvent(self, event):
        if self.__mousePressPos is not None:
            if event.button() == QtCore.Qt.LeftButton:
                moved = event.globalPos() - self.__mousePressPos
                if moved.manhattanLength() > self.dragging_threshould:
                    # do not call click event or so on
                    event.ignore()
                self.__mousePressPos = None
        super(ClipInfoWindow, self).mouseReleaseEvent(event)
    

class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, infoDict, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.infoDict = infoDict
        self.setupData()

    def setupData(self):
        """Prune the active list of data based on 'enabled' property of data Dict"""
        self.infoDict = [data for data in self.infoDict if data['enabled']]

    def rowCount(self, parent):
        return len(self.infoDict)

    def columnCount(self, parent):
        return 2
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        elif role == QtCore.Qt.DisplayRole:
            label = self.infoDict[index.row()]["label"]
            value = self.infoDict[index.row()]["value"]

            if index.column() == 0:
                return label
            elif index.column() == 1:
                return value

        elif role == QtCore.Qt.TextAlignmentRole:
            if index.column() == 0:
                return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            elif index.column() == 1:
                return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        else:
            return

_popover = None
_popoverShown = False
def toggleClipInfoWindow():
    global _popover
    global _popoverShown
    if not _popoverShown:
        _popover = ClipInfoWindow()
        v = hiero.ui.activeView()
        _popover.showAt(QtGui.QCursor.pos())
        _popoverShown = True
    else:
        _popover.hide()
        _popoverShown = False

action = QtWidgets.QAction("Clip Info", None)
action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+0"))
action.triggered.connect(toggleClipInfoWindow)
hiero.ui.addMenuAction("Window", action)