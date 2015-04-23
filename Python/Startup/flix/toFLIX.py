import hiero.ui
import hiero.core
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
import socket
import flix_helpers

class ToFLIXWidget(QWidget):
  def __init__(self):
    """Prototype Widget for sending commands to FLIX over a socket"""
    QWidget.__init__( self )

    self.setObjectName( "uk.co.thefoundry.flixwidget.1" )
    self.setWindowTitle( "Flix" )
    self.setLayout( QFormLayout() )  
    bar = QToolBar()

    selectPreviousPanelAction = QAction(QIcon('icons:TCPlayBackward.png'), '', self)
    selectPreviousPanelAction.setShortcut('Shift+8')
    selectPreviousPanelAction.triggered.connect(self.selectPreviousFlixPanel)
    selectPreviousPanelAction.setToolTip("Click to move the select the previous FLIX panel")
    bar.addAction( selectPreviousPanelAction )

    selectNextPanelAction = QAction(QIcon('icons:TCPlayForward.png'), '', self)
    selectNextPanelAction.setShortcut('Shift+9')
    selectNextPanelAction.triggered.connect(self.selectNextFlixPanel)
    selectNextPanelAction.setToolTip("Click to move the select the next FLIX panel")
    bar.addAction( selectNextPanelAction )

    bar.addSeparator()

    newPanelCurrentViewerImageAction = QAction(QIcon('icons:Add.png'), '', self)
    newPanelCurrentViewerImageAction.setShortcut('Shift+0')
    newPanelCurrentViewerImageAction.triggered.connect(flix_helpers.newFlixPanelFromCurrentViewerImage)
    newPanelCurrentViewerImageAction.setToolTip("Click to add a new Panel from the currnet Viewer image")
    bar.addAction( newPanelCurrentViewerImageAction )

    replacePanelCurrentViewerImageAction = QAction(QIcon('icons:Duplicate.png'), '', self)
    replacePanelCurrentViewerImageAction.setShortcut('Shift+V')
    replacePanelCurrentViewerImageAction.triggered.connect(flix_helpers.replaceFlixPanelFromCurrentViewerImage)
    replacePanelCurrentViewerImageAction.setToolTip("Click to add a replace the currently selected Panel with the current Viewer image")
    bar.addAction( replacePanelCurrentViewerImageAction )

    newPanelCurrentNukeViewerImageAction = QAction(QIcon('icons:Nuke.png'), '', self)
    newPanelCurrentNukeViewerImageAction.triggered.connect(lambda: flix_helpers.newFlixPanelFromCurrentViewerImage(False))
    newPanelCurrentNukeViewerImageAction.setToolTip("Click to add a new Panel from the current Nuke Comp viewport")
    #bar.addAction( newPanelCurrentNukeViewerImageAction )

    self.layout().addRow( "", bar )

  def selectNextFlixPanel(self):
    self.makeFlixCall('selectNextPanel')

  def selectPreviousFlixPanel(self):
    self.makeFlixCall('selectPreviousPanel')    

  def makeFlixCall(self, cmd, TCP_IP = "127.0.0.1", TCP_PORT = 35980, BUFFER_SIZE = 1024):
    """Sends 'cmd' to the default FLIX address and port"""
    MESSAGE = "GET /core/"+cmd+" HTTP/1.0\r\n\r\n"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send(MESSAGE)
    data = s.recv(BUFFER_SIZE)
    s.close() 
    print "received data:", data

flixWidget = ToFLIXWidget()
wm = hiero.ui.windowManager()
wm.addWindow( flixWidget )