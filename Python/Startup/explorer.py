import sys
import hiero.ui
import hiero.core
from PySide import QtGui, QtCore

class ThumbListWidget(QtGui.QListWidget):
    def __init__(self, type, parent=None):
        super(ThumbListWidget, self).__init__(parent)
        self.setIconSize(QtCore.QSize(124, 124))
        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(ThumbListWidget, self).dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super(ThumbListWidget, self).dragLeaveEvent(event)            

    def dragMoveEvent(self, event):
        print "Drag Move Event, event is:" + str(event)
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            super(ThumbListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        print 'dropEvent', event
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.emit(QtCore.SIGNAL("dropped"), links)
        else:
            event.setDropAction(QtCore.Qt.MoveAction)
            super(ThumbListWidget, self).dropEvent(event)


class Explorer(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__( self )
        self.setWindowTitle( "Explorer" ) 
        self.setObjectName( "uk.co.thefoundry.explorer.1" )
        self.setWindowIcon( QtGui.QIcon("icons:FBGridView.png") )

        self.resize(600, 600)
        settings = QtGui.QAction('&Settings', self)
        settings.setStatusTip('Specify rename file settings')

        self.optionsWidget = QtGui.QWidget(self)

        files_list = ThumbListWidget(self)
        select_path_label = QtGui.QLabel("Target Path")
        dest_path_edit = QtGui.QLineEdit()
        select_path = QtGui.QPushButton("Search...")
        description_label = QtGui.QLabel("What reason where the photos/videos taken?")
        description_edit = QtGui.QLineEdit()
        start = QtGui.QPushButton("Copy and Start Renaming")

        self.fileBrowserWidget = QtGui.QWidget(self)

        self.dirmodel = QtGui.QFileSystemModel()
        # Don't show files, just folders
        self.dirmodel.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllDirs)

        self.folder_view = QtGui.QTreeView(parent=self);
        self.folder_view.setModel(self.dirmodel)
        self.folder_view.clicked[QtCore.QModelIndex].connect(self.clicked)

        self.connect(self.folder_view, QtCore.SIGNAL("dropped"), self.items_dropped)
        self.connect(files_list, QtCore.SIGNAL("dropped"), self.items_dropped)

        # Don't show columns for size, file type, and last modified
        self.folder_view.setHeaderHidden(True)
        self.folder_view.hideColumn(1)
        self.folder_view.hideColumn(2)
        self.folder_view.hideColumn(3)


        self.selectionModel = self.folder_view.selectionModel()

        self.filemodel = QtGui.QFileSystemModel()
        # Don't show folders, just files
        self.filemodel.setFilter(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.Files)

        self.folder_view.setDragEnabled(True)

        self.file_view = QtGui.QListView(parent=self);
        self.file_view.setModel(self.filemodel)
        self.file_view.setRootIndex(self.filemodel.index("/"))

        group_input = QtGui.QGroupBox()
        grid_input = QtGui.QGridLayout()

        splitter_filebrowser = QtGui.QSplitter()
        splitter_filebrowser.addWidget(self.folder_view)
        splitter_filebrowser.addWidget(self.file_view)
        splitter_filebrowser.setStretchFactor(0,2)
        splitter_filebrowser.setStretchFactor(1,4)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(splitter_filebrowser)
        self.fileBrowserWidget.setLayout(hbox)

        grid_input.addWidget(select_path_label, 0, 0)
        grid_input.addWidget(dest_path_edit, 1, 0)
        grid_input.addWidget(select_path, 1, 1)
        grid_input.addWidget(description_label, 2, 0)
        grid_input.addWidget(description_edit, 3, 0)
        grid_input.addWidget(start, 3, 1)
        group_input.setLayout(grid_input)   

        vbox_options = QtGui.QVBoxLayout(self.optionsWidget)
        vbox_options.addWidget(files_list)
        vbox_options.addWidget(group_input)
        self.optionsWidget.setLayout(vbox_options)

        splitter_filelist = QtGui.QSplitter()
        splitter_filelist.setOrientation(QtCore.Qt.Vertical)
        splitter_filelist.addWidget(self.fileBrowserWidget)
        splitter_filelist.addWidget(self.optionsWidget)
        vbox_main = QtGui.QVBoxLayout(self)
        vbox_main.addWidget(splitter_filelist)       
        vbox_main.setContentsMargins(0,0,0,0)

        self.set_path
        #self.setLayout(vbox_main)     

    def set_path(self, path=None):
        if not path:
            self.dirmodel.setRootPath("/")
        else:
            self.dirmodel.setRootPath(path)

    def items_dropped(self, arg):
        print 'items_dropped', arg            

    def clicked(self, index):
        # the signal passes the index of the clicked item

        dir_path = self.filemodel.filePath(index)
        print("Clicked, index", str(index))
        print("Clicked, index", str(dir_path))
        root_index = self.filemodel.setRootPath(dir_path)
        self.file_view.setRootIndex(root_index)
        self.file_view.setRootIndex(self.filemodel.index(dir_path))

hiero.ui.explorer = Explorer()
hiero.ui.explorer.__doc__ = "The File Explorer panel object."
hiero.ui.explorer.set_path('/')
hiero.ui.registerPanel( "uk.co.thefoundry.explorer", hiero.ui.explorer )
wm = hiero.ui.windowManager()
wm.addWindow( hiero.ui.explorer )

from hiero.core.events import *

class BinViewDropHandler:
  kTextMimeType = "text/plain"
  
  def __init__(self):
    # hiero doesn't deal with drag and drop for text/plain data, so tell it to allow it
    hiero.ui.registerBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)
    
    # register interest in the drop event now
    hiero.core.events.registerInterest((EventType.kDrop, EventType.kBin), self.dropHandler)

  def dropHandler(self, event):
    
    # get the mime data
    print "mimeData: ", event.mimeData

    # fast/easy way to get at text data
    #if event.mimeData.hasText():
    #  print event.mimeData.text()
      
    # more complicated way
    if event.mimeData.hasFormat(BinViewDropHandler.kTextMimeType):
      byteArray = event.mimeData.data(BinViewDropHandler.kTextMimeType)
      print byteArray.data()
        
      # signal that we've handled the event here
      event.dropEvent.accept()

    # get custom hiero objects if drag from one view to another (only present if the drop was from one hiero view to another)
    if hasattr(event, "items"):
      print "hasItems"
      print event.items
    
    # figure out which item it was dropped onto
    print "dropItem: ", event.dropItem
    
    # get the widget that the drop happened in
    print "dropWidget: ", event.dropWidget
    
    # get the higher level container widget (for the Bin View, this will be the Bin View widget)
    print "containerWidget: ", event.containerWidget
    
    # can also get the sender
    print "eventSender: ", event.sender
      
  #def unregister(self):
  #  unregisterInterest((EventType.kDrop, EventType.kBin), self.dropHandler)
  #  hiero.ui.unregisterBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)

# Instantiate the handler to get it to register itself.
dropHandler = BinViewDropHandler()