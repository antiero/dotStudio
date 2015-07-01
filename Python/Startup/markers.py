# Adds basic frame Marker actions to main Timeline menu and "Mark" context menu.
import operator
import hiero.core
import hiero.ui
import copy
from hiero.ui import findMenuAction, registerAction, registerPanel, insertMenuAction, createMenuAction
from PySide import QtGui
from PySide.QtCore import Qt, QAbstractTableModel, QSize, SIGNAL
from compiler.ast import flatten


def sequence_annotations(self):
  """hiero.core.Sequence.annotations -> returns the Annotations for a Sequence"""
  tracks = self.videoTracks()
  annotations = []
  for track in tracks:
    subTrackItems = flatten(track.subTrackItems())
    annotations += [item for item in subTrackItems if isinstance(item, hiero.core.Annotation)]

  return annotations

def clip_annotations(self):
  """hiero.core.Clip.annotations -> returns the Annotations for a Clip"""
  annotations = []
  subTrackItems = flatten(self.subTrackItems())
  annotations += [item for item in subTrackItems if isinstance(item, hiero.core.Annotation)]
  return annotations

hiero.core.Sequence.annotations = sequence_annotations
hiero.core.Clip.annotations = clip_annotations

class UpdateMarkerDialog(QtGui.QDialog):

  def __init__(self, itemSelection=None,parent=None):
    if not parent:
      parent = hiero.ui.mainWindow()
    super(UpdateMarkerDialog, self).__init__(parent)
    self.setWindowTitle("Modify Marker")
    self.setWindowIcon(QtGui.QIcon("icons:TagsIcon.png"))
    self.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed )

    layout = QtGui.QFormLayout()
    self._itemSelection = itemSelection

    print "Dialog raised with %s" % str(self._itemSelection)

    self._currentIcon = ""
    self._currentName = ""
    self._currentNote = ""
    self._currentInTime = ""
    self._currentDuration = ""

    if self._itemSelection:
      self._currentIcon = self._itemSelection["Icon"]
      self._currentName = self._itemSelection["Name"]
      self._currentNote = self._itemSelection["Note"]
      self._currentInTime = self._itemSelection["TimecodeStart"]
      self._currentDuration = self._itemSelection["Duration"]

    # Name for Marker
    self._markerLabelEdit = QtGui.QLineEdit()
    self._markerLabelEdit.setText(self._currentName)
    self._markerLabelEdit.setToolTip('Enter the name of the Marker.')
    layout.addRow("Label: ",self._markerLabelEdit)

    # Time + Duration Layout
    self._timeLayout = QtGui.QHBoxLayout()
    self._timeInLabel = QtGui.QLabel(str(self._currentInTime))
    self._durationLabel = QtGui.QLabel("Duration: %s" % str(self._currentDuration))
    self._timeLayout.addWidget(self._timeInLabel)
    self._timeLayout.addWidget(self._durationLabel)
    layout.addRow("Time:",self._timeLayout)

    # Marker Colours
    self._markerButtonLayout = QtGui.QHBoxLayout()
    markerTags = self.__getMarkerTags()
    for tag in markerTags:
      markerButton = self.__createMarkerButtonFromTag(tag)
      self._markerButtonLayout.addWidget(markerButton)

    # Add a Combobox for selecting a Tag...
    self._iconCombo = QtGui.QComboBox()
    self._iconCombo.currentIndexChanged.connect(self.tagIconChanged)
    self._markerButtonLayout.addWidget(self._iconCombo)    

    layout.addRow("Colour", self._markerButtonLayout)

    self._noteEdit = QtGui.QPlainTextEdit()
    print "CURRENT NOTE IS: " + str(self._currentNote)
    self._noteEdit.setToolTip('Enter notes here.')
    #self._noteEdit.setFixedHeight(80)
    self._noteEdit.setPlainText(self._currentNote)
    layout.addRow("Note: ",self._noteEdit)

    # Standard buttons for Add/Cancel
    self._buttonbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
    self._buttonbox.button(QtGui.QDialogButtonBox.Ok).setText("OK")
    self._buttonbox.accepted.connect(self.accept)
    self._buttonbox.rejected.connect(self.reject)
    layout.addRow("",self._buttonbox)
    
    # To-do: Set the focus on the _noteEdit field
    self.setLayout(layout)
    
    # Set the focus to be the Note field
    self._markerLabelEdit.setFocus()

  def _getCurrentData(self):
    """returns the currently displayed data from the Dialog as a dictionary"""
    currentDataDict = {"Name":self._markerLabelEdit.text(), 
                       "Icon": self.getTagIcon(), 
                       "Note": self.getTagNote()
                       }
    return currentDataDict

  def __createMarkerButtonFromTag(self, tag):
      markerButton = QtGui.QPushButton("")
      markerButton.setIcon(QtGui.QIcon(tag.icon()))
      markerButton.setObjectName("marker."+tag.name())
      markerButton.setFlat(True)
      markerButton.clicked.connect(lambda: self.__markerLabelClicked(tag.icon()))
      return markerButton

  def __markerLabelClicked(self, markerButton):
    """Sets the current icon variable to the button icon that was clicked"""
    self._currentIcon = markerButton

  def __getMarkerTags(self):
    tagsBin = hiero.core.project("Tag Presets").tagsBin()
    markerBin = tagsBin["Markers"]
    markerTags = markerBin.items()
    return markerTags

  def __getStatusTags(self):
    tagsBin = hiero.core.project("Tag Presets").tagsBin()
    markerBin = tagsBin["Status"]
    markerTags = markerBin.items()
    return markerTags

  # Override the exec_ method to update the TagComboBox with any new Project Tags
  def exec_(self):
    return super(UpdateMarkerDialog, self).exec_()

  def tagIconChanged(self,index):
    #update the note field
    print "tagIconChanged"
    #note = self.tags[index].note()
    #self._noteEdit.setText(note)
    
  # This returns a hiero.core.Tag object, currently described by the UpdateMarkerDialog 
  def getTagNote(self):
    print "getTag"
    # This gets the contents of the Note field
    tagNote = unicode(self._noteEdit.toPlainText())
    return tagNote

  def getTagIcon(self):
    print "getTagIcon"
    return self._currentIcon

class MarkerSortFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self):
        super(MarkerSortFilterProxyModel, self).__init__()
        self.filterString = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def setKeyword(self, arg):
        if arg: 
          self.filterString=str(arg)
        else:
          self.filterString= ""

        self.invalidate()

    def filterAcceptsRow(self, row, parent):
        if self.filterString == "" or len(self.filterString)==0:
            return True
        
        model = self.sourceModel()
        test = str(model.infoDict[row].values()).lower()

        if self.filterString.lower() in test:
            return True
        else:
            return False            

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

    item = self.infoDict[index.row()]["Item"]

    if role == Qt.DecorationRole:
      if index.column() == 0:
        try:
          if isinstance(item, hiero.core.Tag):
            imageView = seq.thumbnail(item.inTime())
          elif isinstance(item, hiero.core.Annotation):
            imageView = seq.thumbnail(item.timelineIn())
          pixmap = QtGui.QPixmap.fromImage(imageView.scaledToWidth(100))
        except:
          icon = QtGui.QIcon("icons:VideoOnlyWarning.png")
          pixmap = icon.pixmap(icon.actualSize(QSize(48, 48)))
        return pixmap

      elif index.column() == 1:
        icon = QtGui.QIcon(self.infoDict[index.row()]["Thumbnail"])
        pixmap = icon.pixmap(icon.actualSize(QSize(32, 32)))
        return pixmap

    elif role == Qt.DisplayRole:
        label = self.infoDict[index.row()]["Name"]
        timecode = self.infoDict[index.row()]["TimecodeStart"]
        note = self.infoDict[index.row()]["Note"]
        duration = self.infoDict[index.row()]["Duration"]

        if index.column() == 2:
            return label
        elif index.column() == 3:
            return timecode
        elif index.column() == 4:
            return duration
        elif index.column() == 5:
            return note

    elif role == Qt.EditRole:
        # We will update the note column
        if index.column() == 5:
            return

    elif role == Qt.TextAlignmentRole:

        if index.column() == 3:
            return Qt.AlignLeft | Qt.AlignVCenter

        if index.column() == 5:
            return Qt.AlignJustify | Qt.AlignVCenter

        return Qt.AlignHCenter | Qt.AlignVCenter
 
    else:
        return

  def flags(self, index):

      # This ensures that only the status and note columns are editable
      if index.column() == 5:
          return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
      else:
          return Qt.ItemIsEnabled | Qt.ItemIsSelectable

      return flags

  def setData(self, index, value, role=Qt.EditRole):
      """This gets called when user enters Text"""
      row = index.row()
      col = index.column()
      #if col == 1:
      #  print "setData", index.row(), index.column(), value
      if col == 5:
        if len(value)>0:
          tag = self.infoDict[index.row()]["Item"]
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

  kModeTags = "Tags"
  kModeAnnotations = "Annotations"
  kModeAnnotationsAndTags = "Annotations + Tags"

  def __init__(self):
    QtGui.QWidget.__init__( self )
    self.setWindowTitle( "Markers" ) 
    self.setObjectName( "uk.co.thefoundry.markers.1" )
    self.setWindowIcon( QtGui.QIcon("icons:Tag.png") )

    self._dialog = None

    self.timecodeDisplayMode  = hiero.core.Timecode().kDisplayTimecode

    # The mode to display data - either Tags, Annotations, or Annotations + Tags
    self._dataDisplayMode  = self.kModeTags
    self.infoDict = []
    self.headerKeys = ["", "Icon", "Name", "Time", "Duration", "Note"]
    self.table_model = MarkersTableModel(self, self.infoDict, self.headerKeys)

    self.markerSortFilterProxyModel=MarkerSortFilterProxyModel()
    self.markerSortFilterProxyModel.setSourceModel(self.table_model)

    self.table_view = QtGui.QTableView()
    self.table_view.setSortingEnabled(True)
    self.table_view.setModel(self.markerSortFilterProxyModel)
    verticalHeader = self.table_view.verticalHeader()
    verticalHeader.setResizeMode(QtGui.QHeaderView.ResizeToContents)    
    self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
    self.table_view.setShowGrid(True)
    self.table_view.verticalHeader().setVisible(False)
    self.table_view.clicked.connect(self.movePlayheadToMarker)

    self.table_view.doubleClicked.connect(self.displayMarkerDialog)

    layout = QtGui.QVBoxLayout(self)
    self.currentSequenceNameLabel = QtGui.QLabel("Sequence")
    self.topLayout = QtGui.QHBoxLayout()
    self.searchLineEdit = QtGui.QLineEdit()
    self.searchLineEdit.textChanged.connect(self.markerSortFilterProxyModel.setKeyword)
    self.searchLineEdit.setStyleSheet("QLineEdit { border: 0.5px solid black; border-radius: 9px; padding: 1 6px; }")
    self.searchLineEdit.setPlaceholderText("Filter")


    # A dropdown to display either Tags or Annotations
    self.displayModeComboBox = QtGui.QComboBox(self)
    self.displayModeComboBox.addItems([self.kModeTags, self.kModeAnnotations, self.kModeAnnotationsAndTags])
    self.displayModeComboBox.currentIndexChanged.connect(self.displayModeChanged)

    self.clearSelectedMarkersButton = QtGui.QPushButton("Selected")
    self.clearSelectedMarkersButton.setIcon(QtGui.QIcon("icons:status/TagOnHold.png"))
    self.clearAllMarkersButton = QtGui.QPushButton("All")
    self.clearAllMarkersButton.setIcon(QtGui.QIcon("icons:status/TagOmitted.png"))
    self.clearAllMarkersButton.setFixedWidth(80)
    self.clearSelectedMarkersButton.setFixedWidth(100)
    self.clearAllMarkersButton.clicked.connect(hiero.ui.clearAllTimelineMarkers)
    self.clearSelectedMarkersButton.clicked.connect(self.clearTagsForSelectedRows)

    self.topLayout.addWidget(self.currentSequenceNameLabel)
    self.topLayout.addWidget(self.displayModeComboBox)
    self.topLayout.addWidget(self.searchLineEdit)
    layout.addLayout(self.topLayout)
    layout.addWidget(self.table_view)

    self.buttonLayout = QtGui.QHBoxLayout()
    self.buttonLayout.setAlignment(Qt.AlignLeft);
    self.buttonLayout.addWidget(self.clearAllMarkersButton)
    self.buttonLayout.addWidget(self.clearSelectedMarkersButton)
    layout.addLayout(self.buttonLayout)

    self.setMinimumSize(480, 160)
    self.setLayout(layout)
    
    hiero.core.events.registerInterest("kPlaybackClipChanged", self._updateTableViewEvent)
    hiero.core.events.registerInterest("kPlaybackStarted", self._updateTableViewEvent)
    hiero.core.events.registerInterest("kPlaybackStopped", self._updateTableViewEvent)
    self.updateTableView()
    self.table_view.resizeColumnsToContents()
    self.table_view.setColumnWidth(0, 100)    
    self.table_view.setColumnWidth(1, 48)
    self.table_view.setColumnWidth(4, 64)
    self.table_view.setColumnWidth(5, 320)

  def displayModeChanged(self):
    self._dataDisplayMode = self.displayModeComboBox.currentText()
    self.updateTableView()
    #print "Display Mode changed to: " + str(self._dataDisplayMode)

  def clearTagsForSelectedRows(self):
    selectionModel = self.table_view.selectionModel()

    hasSelection  = selectionModel.hasSelection()
    if hasSelection:
      selectedIndexes = selectionModel.selectedIndexes()
      selection = selectionModel.selection()
      mappedModelIndices = [] 
      for modelIndex in selectedIndexes:
        mappedModelIndices += [self.markerSortFilterProxyModel.mapToSource(modelIndex)]

      dataForDeletion = []
      for index in mappedModelIndices:
        dataForDeletion += [self.table_model.infoDict[ index.row() ]]

      for data in dataForDeletion:
        sequence = data['Sequence']
        try:
          sequence.removeTag(data['Item'])
        except:
          pass

    self.updateTableView()

  def showEvent(self, event):
      super(MarkersPanel, self).showEvent(event)
      self.updateTableView()

  def movePlayheadToMarker(self, modelIndex):
    # Now access the Tag from the row and move playhead to its in time..

    # We may be filtered, so need to map the index to the Source index
    mappedModelIndex = self.markerSortFilterProxyModel.mapToSource(modelIndex)

    inTime = self.table_model.infoDict[ mappedModelIndex.row() ]["InTime"]

    cv = hiero.ui.currentViewer()
    cv.setTime(int(inTime))

  def displayMarkerDialog(self, modelIndex):
    mappedModelIndex = self.markerSortFilterProxyModel.mapToSource(modelIndex)
    item = self.table_model.infoDict[ mappedModelIndex.row() ]

    self._dialog = UpdateMarkerDialog(itemSelection = item)

    if self._dialog.exec_():
      
      data = self._dialog._getCurrentData()
      print "Display Dialog with data %s" % str(data)
      newNote = data["Note"]
      newIcon = data["Icon"]
      tag = self.table_model.infoDict[ mappedModelIndex.row() ]["Item"]
      tag.setNote(data["Note"])
      self.infoDict[mappedModelIndex.row()]["Note"] = tag.note()
      tag.setIcon(newIcon)
      self.infoDict[mappedModelIndex.row()]["Icon"] = newIcon
      self.updateTableView()

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
    seq = hiero.ui.currentViewer().player().sequence()
    if not seq:
      self.infoDict = []
    else:
      self.currentSequenceNameLabel.setText(seq.name())
      self.__buildDataForSequence(seq)
    
    self.table_model.infoDict = self.infoDict
    self.markerSortFilterProxyModel.setSourceModel(self.table_model)
    
  def formatStringFromSeq(self, seq):
    seq = seq.format()
    height = seq.height()
    width = seq.width()
    pixel_aspect = seq.pixelAspect()
    formatString = "%i x %i, %f" % (width, height, pixel_aspect)
    return formatString

  def __getTagsDictForSequence(self, seq):
    timecodeStart = seq.timecodeStart()

    # We need to get Tags which are NOT applied to the whole Clip/Sequence...
    tags = [tag for tag in list(seq.tags()) if int(tag.metadata().value('tag.applieswhole')) == 0]

    fps = seq.framerate()
    sortedTags = sorted(tags, key=lambda k: k.inTime())
    tagDict = []
    for tag in sortedTags:
      tagMeta = tag.metadata()
      inTime = tag.inTime()
      outTime = tag.outTime() # tag.inTime()
      try:
        duration = int(tagMeta.value('tag.duration'))
      except:
        duration = (outTime-inTime)

      tc = hiero.core.Timecode()
      inTimecode = tc.timeToString(inTime + timecodeStart, fps, self.timecodeDisplayMode)
      outTimecode = tc.timeToString(outTime + timecodeStart, fps, self.timecodeDisplayMode)

      if self.timecodeDisplayMode == tc.kDisplayTimecode:
        timecodeString = "%s" % (str(inTimecode))
      else:
        timecodeString = "%i" % (inTime)
      tagDict += [{"Item": tag, 
                         "Name": tag.name(), 
                         "InTime": inTime, 
                         "OutTime": outTime,
                         "TimecodeStart": "%s" % (str(inTimecode)),
                         "Note": tag.note(),
                         "Duration": duration,
                         "Icon": str(tag.icon()),
                         "Sequence": seq,
                         "Thumbnail": str(tag.icon())
                         }]
    return tagDict

  def __getAnnoationsDictForSequence(self, seq):
    timecodeStart = seq.timecodeStart()
    annotations = seq.annotations()
    fps = seq.framerate()
    sortedAnnotations = sorted(annotations, key=lambda k: k.timelineIn())
    annotationsDict = []
    for annotation in sortedAnnotations:
      inTime = annotation.timelineIn()
      outTime = annotation.timelineOut()
      duration = (outTime-inTime)
      notes = annotation.notes()

      tc = hiero.core.Timecode()
      inTimecode = tc.timeToString(inTime + timecodeStart, fps, self.timecodeDisplayMode)
      outTimecode = tc.timeToString(outTime + timecodeStart, fps, self.timecodeDisplayMode)

      if self.timecodeDisplayMode == tc.kDisplayTimecode:
        timecodeString = "%s" % (str(inTimecode))
      else:
        timecodeString = "%i" % (inTime)
      annotationsDict += [{"Item": annotation, 
                         "Name": annotation.parent().name(), 
                         "InTime": inTime, 
                         "OutTime": outTime,
                         "TimecodeStart": "%s" % (str(inTimecode)),
                         "Note": " , ".join(notes),
                         "Duration": duration,
                         "Icon": "icons:ViewerToolAnnotationVis.png",
                         "Sequence": seq,
                         "Thumbnail": "icons:ViewerToolAnnotationVis.png"
                         }]
    return annotationsDict

  def __buildDataForSequence(self, seq):
      
      if not seq:
        return

      self.infoDict = []
      #if not seq or isinstance(seq, hiero.core.Clip):
      #    return
      #elif isinstance(seq, hiero.core.Sequence):
      # We need a list of Tags, sorted by the inTime...
      if self._dataDisplayMode in (self.kModeTags, self.kModeAnnotationsAndTags):
        self.infoDict += self.__getTagsDictForSequence(seq)
      if self._dataDisplayMode in (self.kModeAnnotations, self.kModeAnnotationsAndTags):
        self.infoDict += self.__getAnnoationsDictForSequence(seq)

      # Now sort these based on inTime
      sortedDict = sorted(self.infoDict, key=lambda k: k["InTime"]) 
      self.infoDict = sortedDict

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

    markerTag = hiero.core.Tag("Icon")
    M = markerTag.metadata()
    activeSequence.addTagToRange(markerTag, currentTime, currentTime)
    hiero.ui.markersPanel.updateTableView()

  def clearAllMarkers(self, sequence=None):
    """Clears all Tags annotations from the active Sequence"""

    if not sequence:
      activeSequence = hiero.ui.activeSequence()

    if not activeSequence:
      cv = hiero.ui.currentViewer()
      activeSequence = cv.player().sequence()
      if not activeSequence:
        return

    tags = activeSequence.tags()

    proj = activeSequence.project()
    with proj.beginUndo("Clear All Markers"):
      for tag in tags:
        activeSequence.removeTag(tag)

      annotations = activeSequence.annotations()
      for annotation in annotations:
        parentTrack = annotation.parentTrack()
        parentTrack.removeSubTrackItem(annotation)

    hiero.ui.markersPanel.updateTableView()
  
  def clearMarkersInActiveRange(self):
    activeSequence = hiero.ui.activeSequence()

    if not activeSequence:
      cv = hiero.ui.currentViewer()
      activeSequence = cv.player().sequence()
      if not activeSequence:
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

markerActions = MarkerActions()
hiero.ui.clearAllTimelineMarkers = markerActions.clearAllMarkers
hiero.ui.clearMarkersInActiveRange = markerActions.clearMarkersInActiveRange

hiero.ui.markersPanel = MarkersPanel()
hiero.ui.markersPanel.__doc__ = "The Markers panel object. Call hiero.ui.markersPanel.updateTableView() to refresh the panel."
registerPanel( "uk.co.thefoundry.markers", hiero.ui.markersPanel )

wm = hiero.ui.windowManager()
wm.addWindow( hiero.ui.markersPanel )

# Add action to Timeline menu so it can be given a Global keyboard shortcut
timelineMenu = findMenuAction("foundry.menu.sequence")

if timelineMenu:
  insertMenuAction( markerActions._addMarkerAction, timelineMenu.menu(), after="foundry.timeline.markClip" )
  insertMenuAction( markerActions._clearAllMarkersAction, timelineMenu.menu(), after="foundry.timeline.addMarker" )
  insertMenuAction( markerActions._clearMarkersInOutAction, timelineMenu.menu(), after="foundry.timeline.clearAllMarkers" )