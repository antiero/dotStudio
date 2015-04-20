# Adds basic frame Marker actions to main Timeline menu and "Mark" context menu.
import operator
import hiero.core
import hiero.ui
from hiero.ui import findMenuAction, registerAction, registerPanel, insertMenuAction, createMenuAction
from PySide import QtGui
from PySide.QtCore import Qt, QAbstractTableModel, QSize, SIGNAL


gStatusTags = {'Approved':'icons:status/TagApproved.png',
  'Unapproved':'icons:status/TagUnapproved.png',
  'Ready To Start':'icons:status/TagReadyToStart.png',
  'Blocked':'icons:status/TagBlocked.png',
  'On Hold':'icons:status/TagOnHold.png',
  'In Progress':'icons:status/TagInProgress.png',
  'Awaiting Approval':'icons:status/TagAwaitingApproval.png',
  'Omitted':'icons:status/TagOmitted.png',
  'Final':'icons:status/TagFinal.png'}

class MarkerSelectionComboDelegate(QtGui.QItemDelegate):
    """
    A delegate that places a fully QComboBox with Tag icons in every
    cell of the column to which it's applied
    """
    def __init__(self, parent):

        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, painter, option, index):

        combo = QtGui.QComboBox(self.parent())
        #self.connect(combo, SIGNAL("currentIndexChanged(int)"), self.parent().currentIndexChanged)

        global gStatusTags
        for key in gStatusTags.keys():
         combo.addItem(QtGui.QIcon(gStatusTags[key]), key)

        if not self.parent().indexWidget(index):
            self.parent().setIndexWidget(
                index, 
                combo
            )

        self.connect(combo, SIGNAL("currentIndexChanged(int)"), 
                 self, SIGNAL("currentIndexChanged()"))

        return combo

    def setEditorData(self, editor, index):
      editor.blockSignals(True)
      #editor.setCurrentIndex(int(index.model().data(index)))
      editor.blockSignals(False)

    def setModelData(self, editor, model, index):
      model.setData(index, editor.currentIndex())

    #def currentIndexChanged(self):
    #    self.commitData.emit(self.sender())                

class MarkersTableModel(QAbstractTableModel):
  def __init__(self, parent, infoDict, header, *args):
    QAbstractTableModel.__init__(self, parent, *args)
    self.infoDict = infoDict
    self.header_labels = header

  def rowCount(self, parent):
    return len(self.infoDict)

  def columnCount(self, parent):
    return len(self.header_labels)
  
  def data(self, index, role):
    if not index.isValid() or len(self.infoDict)==0:
        return None

    seq = hiero.ui.activeSequence()
    if not seq:
      return None

    tag = self.infoDict[index.row()]["Tag"]

    if role == Qt.DecorationRole:
      if index.column() == 0:
        try:
          imageView = seq.thumbnail(tag.inTime())
          pixmap = QtGui.QPixmap.fromImage(imageView.scaledToWidth(100))
        except:
          icon = QtGui.QIcon("icons:VideoOnlyWarning.png")
          pixmap = icon.pixmap(icon.actualSize(QSize(48, 48)))
        return pixmap

      elif index.column() == 1:
        icon = QtGui.QIcon(tag.icon())
        pixmap = icon.pixmap(icon.actualSize(QSize(32, 32)))
        return pixmap

    elif role == Qt.DisplayRole:
        label = self.infoDict[index.row()]["Name"]
        timecode = self.infoDict[index.row()]["Timecode"]
        note = self.infoDict[index.row()]["Note"]

        if index.column() == 2:
            return label
        elif index.column() == 3:
            return timecode
        elif index.column() == 4:
            return note

    elif role == Qt.EditRole:
        # We will update the note column
        if index.column() == 4:
            return

    elif role == Qt.TextAlignmentRole:
        if index.column() == 0:
            return Qt.AlignHCenter | Qt.AlignVCenter
        elif index.column() == 1:
            return Qt.AlignHCenter | Qt.AlignVCenter
    else:
        return

  def flags(self, index):
      #flags = super(self.__class__,self).flags(index)

      # This ensures that only the status and note columns are editable
      if index.column() == 4:
          return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
      else:
          return Qt.ItemIsEnabled | Qt.ItemIsSelectable

      return flags

  def setData(self, index, value, role=Qt.EditRole):
      """This gets called when user enters Text"""
      row = index.row()
      col = index.column()
      if col == 1:
        print "setData", index.row(), index.column(), value
      elif col == 4: 
        tag = self.infoDict[index.row()]["Tag"]
        tag.setNote(str(value))
        self.infoDict[index.row()]["Note"] = tag.note()
        self.emit(SIGNAL('dataChanged()'))
      return True

  def headerData(self, section, orientation, role=Qt.DisplayRole):
      if role == Qt.DisplayRole and orientation == Qt.Horizontal:
          return self.header_labels[section]
      return QAbstractTableModel.headerData(self, section, orientation, role)

  def sort(self, col, order):
      """sort table by given column number col"""
      self.emit(SIGNAL("layoutAboutToBeChanged()"))
      self.infoDict = sorted(self.infoDict,
          key=operator.itemgetter(self.header_labels[col]))
      if order == Qt.DescendingOrder:
          self.infoDict.reverse()
      self.emit(SIGNAL("layoutChanged()"))

class MarkersPanel(QtGui.QWidget):
  """A dockable Markers Panel that displays frame Markers for the Current Sequence"""
  def __init__(self):
    QtGui.QWidget.__init__( self )
    self.setWindowTitle( "Markers" )
    self.setWindowIcon( QtGui.QIcon("icons:Tag.png") )

    self.timecodeDisplayMode  = hiero.core.Timecode().kDisplayTimecode
    self.infoDict = []
    self.headerKeys = ["", "Marker", "Name", "Timecode", "Note"]
    self.table_model = MarkersTableModel(self, self.infoDict, self.headerKeys)
    self.table_view = QtGui.QTableView()
    self.table_view.setSortingEnabled(True)
    self.table_view.setModel(self.table_model)
    verticalHeader = self.table_view.verticalHeader()
    verticalHeader.setResizeMode(QtGui.QHeaderView.Fixed)
    verticalHeader.setDefaultSectionSize(60);    
    self.table_view.resizeColumnsToContents()
    self.table_view.resizeRowsToContents()
    self.table_view.setColumnWidth(0, 48)
    self.table_view.setColumnWidth(1, 32)
    self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
    self.table_view.setShowGrid(True)
    self.table_view.verticalHeader().setVisible(False)

    #self.table_view.setItemDelegateForColumn(1, MarkerSelectionComboDelegate(self.table_view))

    self.table_view.doubleClicked.connect(self.movePlayheadToMarker)

    layout = QtGui.QVBoxLayout(self)
    self.searchLineEdit = QtGui.QLineEdit()
    self.searchLineEdit.setStyleSheet("QLineEdit { border: 1px solid black; }")
    self.searchLineEdit.setPlaceholderText("Filter")
    layout.addWidget(self.searchLineEdit)
    layout.addWidget(self.table_view)

    #self.clearSelectedMarkersButton = QtGui.QPushButton("Clear Selected")
    #self.clearAllMarkersButton = QPushButton("Clear All")
    #self.clearAllMarkersButton.clicked.connect(MarkerActions()._clearAllMarkersAction)
    #layout.addWidget(self.clearAllMarkersButton)

    self.setMinimumSize(480, 160)
    self.setLayout(layout)
    hiero.core.events.registerInterest("kContextChanged", self._updateTableViewEvent)
    hiero.core.events.registerInterest("kPlaybackStarted", self._updateTableViewEvent)
    hiero.core.events.registerInterest("kPlaybackStopped", self._updateTableViewEvent)
    self.updateTableView()


  def clearSelectedMarkers(self):
    selectionModel = self.table_view.selectionModel()

    hasSelection  = selectionModel.hasSelection()
    if hasSelection:
      selectedRows = selectionModel.selectedRows()
      print "Selected Marker indices will be deleted: %s" % str(selectedRows)


  def showEvent(self, event):
      super(MarkersPanel, self).showEvent(event)
      self.updateTableView()

  def movePlayheadToMarker(self, modelIndex):
    # Now access the Tag from the row and move playhead to its in time..
    inTime = self.table_model.infoDict[modelIndex.row()]['In']
    cv = hiero.ui.currentViewer()
    cv.setTime(int(inTime))

  def toggleTimecodeDisplay(self):
    """TO-DO: Toggles the mode for timecode or frame display"""
    if self.timecodeDisplayMode == hiero.core.Timecode().kDisplayTimecode:
      self.timecodeDisplayMode = hiero.core.Timecode().kDisplayFrame
    else:
      # Should support drop display here too?...
      self.timecodeDisplayMode == hiero.core.Timecode().kDisplayTimecode
    self.updateTableView()

  def _updateTableViewEvent(self, event):
    self.updateTableView()

  def updateTableView(self):
    self.__buildDataForCurrentSequence()
    self.table_model = MarkersTableModel(self, self.infoDict, self.headerKeys)
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
          tc = hiero.core.Timecode()
          inTimecode = tc.timeToString(inTime,25, self.timecodeDisplayMode)
          outTimecode = tc.timeToString(outTime,25, self.timecodeDisplayMode)

          if self.timecodeDisplayMode == tc.kDisplayTimecode:
            timecodeString = "In: %s\nOut: %s" % (str(inTimecode), str(outTimecode))
          else:
            timecodeString = "In: %i\nOut: %i" % (inTime, outTime)
          self.infoDict += [{"Tag": tag, 
                             "Name": tag.name(), 
                             "In": inTime, 
                             "Out": outTime,
                             "Timecode": "In: %s\nOut: %s" % (str(inTimecode), str(outTimecode)),
                             "Note": tag.note(),
                             "Marker": str(tag.icon()),
                             "Thumbnail": str(tag.icon())
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
    hiero.ui.markersPanel.updateTableView()

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

    hiero.ui.markersPanel.updateTableView()
  
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

    hiero.ui.markersPanel.updateTableView()

  def eventHandler(self, event):
    """Add these actions to the Mark sub-menu"""
    for a in event.menu.actions():
      if a.text().lower().strip() == "mark":
        insertMenuAction( self._addMarkerAction, a.menu())
        insertMenuAction( self._clearAllMarkersAction, a.menu())
        insertMenuAction( self._clearMarkersInOutAction, a.menu())

hiero.ui.markersPanel = MarkersPanel()
hiero.ui.markersPanel.__doc__ = "The Markers panel object. Call hiero.ui.markersPanel.updateTableView() to refresh the panel."
registerPanel( "uk.co.thefoundry.markers", hiero.ui.markersPanel )
markerActions = MarkerActions()

wm = hiero.ui.windowManager()
wm.addWindow( hiero.ui.markersPanel )

# Add action to Timeline menu so it can be given a Global keyboard shortcut
timelineMenu = findMenuAction("foundry.menu.sequence")

if timelineMenu:
  insertMenuAction( markerActions._addMarkerAction, timelineMenu.menu(), after="foundry.timeline.markClip" )
  insertMenuAction( markerActions._clearAllMarkersAction, timelineMenu.menu(), after="foundry.timeline.addMarker" )
  insertMenuAction( markerActions._clearMarkersInOutAction, timelineMenu.menu(), after="foundry.timeline.clearAllMarkers" )