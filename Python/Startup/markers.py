# Adds basic frame Marker actions to main Timeline menu and "Mark" context menu.
import hiero.core
import hiero.ui
from hiero.ui import findMenuAction, registerAction, insertMenuAction, createMenuAction
from PySide import QtGui
from PySide.QtCore import Qt, QAbstractTableModel

class MarkersTableModel(QAbstractTableModel):
  def __init__(self, parent, infoDict, *args):
    QAbstractTableModel.__init__(self, parent, *args)
    self.infoDict = infoDict

  def rowCount(self, parent):
    return len(self.infoDict)

  def columnCount(self, parent):
    return 4
  
  def data(self, index, role=Qt.DecorationRole|Qt.DisplayRole):
    if not index.isValid():
        return None

    tag = self.infoDict[index.row()]["Tag"]
    if role == Qt.DecorationRole:
      if index.column() == 0:
        seq = hiero.ui.activeSequence()
        if not seq:
          return
        else:
          imageView = seq.thumbnail(tag.inTime())
          pixmap = QtGui.QPixmap.fromImage(imageView.scaledToHeight(48))
          return pixmap;

    elif role == Qt.DisplayRole:
        label = self.infoDict[index.row()]["Name"]
        value = self.infoDict[index.row()]["Range"]
        note = self.infoDict[index.row()]["Note"]

        if index.column() == 1:
            return label
        elif index.column() == 2:
            return value
        elif index.column() == 3:
            return note

    elif role == Qt.TextAlignmentRole:
        if index.column() == 1:
            return Qt.AlignRight | Qt.AlignVCenter
        elif index.column() == 2:
            return Qt.AlignLeft | Qt.AlignVCenter

    else:
        return 

class MarkersPanel(QtGui.QWidget):
  """A dockable Markers Panel that displays frame Markers for the Current Sequence"""
  def __init__(self):
    QtGui.QWidget.__init__( self )

    self.setObjectName( "uk.co.thefoundry.markers" )
    self.setWindowTitle( "Markers" )
    self.setWindowIcon( QtGui.QIcon("icons:Tag.png") )
    self.infoDict = []
    self.infoDict += [{"Tag": "", 
                       "Name": "", 
                       "In": 0,
                       "Out": 0,
                       "Range": "",
                       "Note": "",
                       }]

    self.table_model = MarkersTableModel(self, self.infoDict)
    self.table_view = QtGui.QTableView()
    self.table_view.setModel(self.table_model)

    verticalHeader = self.table_view.verticalHeader();
    verticalHeader.setResizeMode(QtGui.QHeaderView.Fixed);
    verticalHeader.setDefaultSectionSize(60);    
    self.table_view.resizeColumnsToContents()
    self.table_view.resizeRowsToContents()

    # set font
    self.table_view.setShowGrid(True)
    self.table_view.verticalHeader().setVisible(True)
    self.table_view.horizontalHeader().setVisible(False)
    self.table_view.setSelectionMode(QtGui.QAbstractItemView.NoSelection)

    layout = QtGui.QVBoxLayout(self)
    layout.addWidget(self.table_view)
    self.setMinimumSize(480, 160)        
    self.setLayout(layout)

    hiero.core.events.registerInterest("kPlaybackClipChanged", self.updateTableView)
    hiero.core.events.registerInterest("kPlaybackStarted", self.updateTableView)
    hiero.core.events.registerInterest("kPlaybackStopped", self.updateTableView)

  def updateTableView(self, event):
    self.__buildDataForCurrentSequence()
    self.table_model = MarkersTableModel(self, self.infoDict)
    self.table_view.setModel(self.table_model)
    self.table_view.resizeColumnsToContents()

  def formatStringFromSeq(self, seq):
    seq = seq.format()
    height = seq.height()
    width = seq.width()
    pixel_aspect = seq.pixelAspect()
    formatString = "%i x %i, %f" % (width, height, pixel_aspect)
    return formatString

  def __buildDataForCurrentSequence(self):
      seq = hiero.ui.activeSequence()
      self.infoDict = []
      if not seq or isinstance(seq, hiero.core.Clip):
          return
      elif isinstance(seq, hiero.core.Sequence):
        # We need a list of Tags, sorted by the inTime...
        tags = list(seq.tags())

        sortedTags = sorted(tags, key=lambda k: k.inTime())
        for tag in sortedTags:
          inTime = tag.inTime()
          outTime = tag.inTime()
          self.infoDict += [{"Tag": tag, 
                             "Name": tag.name(), 
                             "In": inTime, 
                             "Out": outTime, 
                             "Range": "%i-%i" % (inTime, outTime),
                             "Note": tag.note(),
                             }]

class MarkerActions(object):
  """Actions for adding frame Markers and Clearing them"""
  def __init__(self):
    self._addMarkerAction = createMenuAction("Add Marker", self.addMarkerToCurrentFrame)
    self._addMarkerAction.setShortcut( "M" )
    self._addMarkerAction.setObjectName("foundry.timeline.addMarker")
    registerAction(self._addMarkerAction)

    self._clearAllMarkersAction = createMenuAction("Clear All Markers", self.clearAllMarkers)
    self._clearAllMarkersAction.setObjectName("foundry.timeline.clearAllMarkers")
    registerAction(self._clearAllMarkersAction)

    self._clearMarkersInOutAction = createMenuAction("Clear Markers In/Out Range", self.clearMarkersInActiveRange)
    self._clearMarkersInOutAction.setObjectName("foundry.timeline.clearMarkersInOut")
    registerAction(self._clearMarkersInOutAction)

    hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
    hiero.core.events.registerInterest("kShowContextMenu/kViewer", self.eventHandler)

  def addMarkerToCurrentFrame(self):
    """Adds a basic single frame Marker to the current Frame"""
    activeSequence = hiero.ui.activeSequence()
    if not activeSequence:
      return

    activeView = hiero.ui.activeView()
    if not activeView:
      return

    currentTime = None
    if isinstance(activeView, hiero.ui.Viewer):
      currentTime = activeView.time()
    elif isinstance(activeView, hiero.ui.TimelineEditor):
      currentTime = hiero.ui.currentViewer().time()

    if not currentTime:
      return

    markerTag = hiero.core.Tag("Marker")
    M = markerTag.metadata()
    activeSequence.addTagToRange(markerTag, currentTime, currentTime)

  def clearAllMarkers(self):
    activeSequence = hiero.ui.activeSequence()
    if not activeSequence:
      return

    activeView = hiero.ui.activeView()
    if not activeView:
      return

    tags = activeSequence.tags()
    if len(tags)<1:
      return

    proj = activeSequence.project()
    with proj.beginUndo("Clear All Markers"):
      for tag in tags:
        activeSequence.removeTag(tag)
  
  def clearMarkersInActiveRange(self):
    activeSequence = hiero.ui.activeSequence()
    if not activeSequence:
      return

    activeView = hiero.ui.activeView()
    if not activeView:
      return

    try:
      inTime = activeSequence.inTime()
    except:
      inTime = 0

    try:
      outTime = activeSequence.outTime()
    except:
      outTime = activeSequence.duration()

    tags = activeSequence.tags()
    if len(tags)<1:
      return

    proj = activeSequence.project()
    with proj.beginUndo("Clear Markers In/Out Range"):
      for tag in tags:
        if tag.inTime() >= inTime and tag.outTime() <= outTime:
          activeSequence.removeTag(tag)        

  def eventHandler(self, event):
    """Add these actions to the Mark sub-menu"""
    #for a in event.menu.actions():
    #  if a.text().lower().strip() == "mark":
    print "Event Handler Called"
    insertMenuAction( self._addMarkerAction, a.menu())
    insertMenuAction( self._clearAllMarkersAction, a.menu())
    insertMenuAction( self._clearMarkersInOutAction, a.menu())

markersPanel = MarkersPanel()
markerActions = MarkerActions()

wm = hiero.ui.windowManager()
wm.addWindow( markersPanel )

# Add action to Timeline menu so it can be given a Global keyboard shortcut
timelineMenu = findMenuAction("foundry.menu.sequence")

if timelineMenu:
  insertMenuAction( markerActions._addMarkerAction, timelineMenu.menu(), after="foundry.timeline.markClip" )
  insertMenuAction( markerActions._clearAllMarkersAction, timelineMenu.menu(), after="foundry.timeline.addMarker" )
  insertMenuAction( markerActions._clearMarkersInOutAction, timelineMenu.menu(), after="foundry.timeline.clearAllMarkers" )