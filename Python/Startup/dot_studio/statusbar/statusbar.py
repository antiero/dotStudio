# Modified from hiero.ui.FnStatusBar
import hiero.ui
from hiero.ui.nuke_bridge import nukestudio
from PySide2.QtCore import Qt, QTimer, QCoreApplication
from PySide2.QtGui import QIcon, QPixmap, QMovie
from PySide2 import QtWidgets
try:
  import psutil
  gEnableResourceMonitoring = True
except:
  print 'Unable to import psutil. Resource monitoring will be disabled.'
  gEnableResourceMonitoring = False

import os
import re
from psutil_helper import PSUtilProcessWrapper, bytesToMB

# Global path for icons
cwd = os.path.dirname(os.path.realpath(__file__))
gIconPath = os.path.abspath(os.path.join(cwd, "icons"))

gInitialDelayMS = 3000
gUpdateIntervalMS = 1000

# Popover Dialog to change settings (UNUSED CURRENTLY)
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent = hiero.ui.mainWindow()):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Select info to show in info bar")
        self.layout = QFormLayout()
        self.cpuSetting = QCheckBox("")
        self.layout.addRow("CPU", self.cpuSetting)
        self.memorySetting = QCheckBox("")
        self.layout.addRow("Memory", self.memorySetting)
        self.diskSetting = QCheckBox("")
        self.layout.addRow("Disk", self.diskSetting)
        self.networkSetting = QCheckBox("")
        self.layout.addRow("Network", self.networkSetting)
        self.setLayout(self.layout)

class InfoBar(object):
  """Adds a info bar to the bottom of the main window"""

  # Should be stored and restored from uistate.ini
  infoSettings = {"showCPU": True,
                 "showMemory": True,
                 "showDisk": True,
                 "showNetwork": True
                 }
  
  def __init__(self):

    global gEnableResourceMonitoring
    self.enableResourceMonitoring  = gEnableResourceMonitoring
    self.bar = hiero.ui.mainWindow().statusBar()

    self.updateMonitorIntervalMS = gUpdateIntervalMS # The monitor update time in milliseconds.
    self.timer = QTimer()
    self.timer.setSingleShot(False)
    self.timer.timeout.connect(self.updateStatusBar)

    self.currentDiskIOBytes = psutil.disk_io_counters().read_bytes
    self.currentNetworkBytesReceived = psutil.net_io_counters().bytes_recv

    # This observes the current pid (the App process id) via psutil, and reports back
    if self.enableResourceMonitoring:
      self.processHelper = PSUtilProcessWrapper()

    # The frameServer instance
    self.frameServerInstance = nukestudio.frameServer

    # Initialise the Status Bar
    self.setupUI()

    # We haven't started monitoring at this point
    self.isMonitoring = False

    # Begin monitoring after a few secs to give frame server time to start up properly
    QTimer.singleShot(gInitialDelayMS, self.startMonitoring)

  def getLatestStyleSheet(self):
    styleFile = os.path.join( cwd, "style.stylesheet")
    with open(styleFile, "r") as fh:
      return fh.read()

  def hide(self):
    """Hide the info bar"""
    self.bar.setHidden(True)

  def show(self):
    """Show the info bar"""  
    self.bar.setHidden(False)
    
  def rendersExistInQueue(self):
    """Return whether renders exist in the Frame server queue"""
    return len(self.frameServerInstance.renderQueue.requestsInProgress) > 0

  def _handleServerUnreachable(self):
    """This is called when the server becomes unreachable"""
    print "[WARNING]: Nuke Frame Server was not reachable."
    self.frameserverStatusLabel.setPixmap(QPixmap("icons:Offline.png"));
    self.restartServerButton.setHidden(False)  

  def _setResourcesLabelColour(self, memRatio, cpuUsage):

    """Sets the Resources label to be red if the memory usage gets too high"""
    if memRatio > 0.9:
      color  = QColor( Qt.red )
      alpha  = 220
      values = "{r}, {g}, {b}, {a}".format(r = color.red(),
                                           g = color.green(),
                                           b = color.blue(),
                                           a = alpha
                                           )
      #self.nukeResourcesLabel.setStyleSheet("QLabel { vertical-align: middle; font: 10pt; color: rgba("+values+"); }")
    else:
      #self.nukeResourcesLabel.setStyleSheet("QLabel { vertical-align: middle; font: 10pt; }")
      return


  def restartServerAsync(self):
    self.frameServerInstance.stop()
    self.frameServerInstance.start()
    QTimer.singleShot(3000, self.startMonitoring)

  def restartServer(self):
    """Called to restart the Nuke Frame Server, done asynchronously"""
    self.stopMonitoring()
    self.restartServerButton.setHidden(True)
    #self.nukeResourcesLabel.setText("Re-Starting Frame Server...")
    QTimer.singleShot(150, self.restartServerAsync)

  # Displays the resources label, based on settings.
  def buildResourcesLabel(self):
    if self.isMonitoring:
      print "Building resources Label..."

  def updateResourcesStatusLabel(self):
    """Updates the Memory Label String"""

    if self.enableResourceMonitoring:
      if self.memoryString.isVisible():
        self.updateMemoryLayout()

      if self.cpuString.isVisible():
        self.updateCPULayout()

      if self.diskString.isVisible():
        self.updateDiskLayout()

      if self.networkString.isVisible():
        self.updateNetworkLayout()

      #totalSystemMemoryGB = self.processHelper.totalSystemMemory()
      #memRatio = currentMemUsageGB / totalSystemMemoryGB
      # This little test makes the label red if the memory usage exceeds 90% of the maximum allowed
      #self._setResourcesLabelColour( memRatio, currentCPUUsageAsPercentatge )

  def updateMemoryLayout(self):
    currentMemUsageGB = self.processHelper.nukeMemoryUsageInGB()
    currentMemUsageAsPercentage = self.processHelper.nukeMemoryUsageAsPercentage()
    self.memoryString.setText("%.2f GB (%.1f%%)" % (currentMemUsageGB, currentMemUsageAsPercentage))

  def updateCPULayout(self):
    currentCPUUsageAsPercentatge = self.processHelper.nukeCPUUsageAsPercentage()
    self.cpuString.setText("%.1f%%" % currentCPUUsageAsPercentatge)

  def updateDiskLayout(self):
    diskMBPerSec = self._diskMBPerSec()
    self.diskString.setText("%.2f MB/s" % diskMBPerSec)

  def updateNetworkLayout(self):
    networkMBPerSec = self._networkMBPerSec()
    self.networkString.setText("%.2f MB/s" % networkMBPerSec)

  def _diskMBPerSec(self):
    """Returns Total Disk Read+Write speed in MB/s"""
    oldBytes = self.currentDiskIOBytes
    DISKS = psutil.disk_io_counters(perdisk=True)
    readWriteBytes =[(DISKS[disk].read_bytes, DISKS[disk].write_bytes) for disk in DISKS.keys()]
    newBytes = sum([sum(x) for x in zip(*readWriteBytes)])
    bytesDiff = newBytes-oldBytes
    self.currentDiskIOBytes = newBytes
    bytesPerSecond = (newBytes-oldBytes)/(self.updateMonitorIntervalMS/1000)
    MBPerSecond = bytesToMB(bytesPerSecond)
    return MBPerSecond

  def _networkMBPerSec(self):
    """Returns Total Network Read+Write speed in MB/s"""
    oldBytes = self.currentNetworkBytesReceived

    NET = psutil.net_io_counters(pernic=True)
    readWriteBytes =[(NET[adapter].bytes_recv, NET[adapter].bytes_sent) for adapter in NET.keys()]
    newBytes = sum([sum(x) for x in zip(*readWriteBytes)])
    bytesDiff = newBytes-oldBytes
    self.currentNetworkBytesReceived = newBytes
    bytesPerSecond = (newBytes-oldBytes)/(self.updateMonitorIntervalMS/1000)
    MBPerSecond = bytesToMB(bytesPerSecond)
    return MBPerSecond

  def setupUI(self):
    """Initialise the UI"""

    self.bar.setStyleSheet( self.getLatestStyleSheet() )
    #self.bar.setFixedHeight(30)
    self.frameserverStatusLabel = QLabel("")

    # Resources
    self.cpuIconPath = os.path.join(gIconPath, "cpu.png")
    self.memoryIconPath = os.path.join(gIconPath, "memory.png")
    self.diskReadIconPath = os.path.join(gIconPath, "disk_read.png")
    self.networkReadIconPath = os.path.join(gIconPath, "net_read.png")

    # MEMORY SECTION
    self.memoryImageButton = QtWidgets.QPushButton(QPixmap((self.memoryIconPath)).scaledToHeight(20, Qt.SmoothTransformation),"")
    self.memoryImageButton.setObjectName("show_button_memory")
    self.memoryImageButton.setToolTip("Click to toggle monitoring of 'Real Memory' usage")
    self.memoryString = QtWidgets.QLabel("MEMORY (GB)")
    self.memoryString.setToolTip("'Real Memory' usage of this Nuke Session")
    self.memoryImageButton.clicked.connect(lambda: self.show_button_clicked(self.memoryString))

    # CPU SECTION
    self.cpuImageButton = QtWidgets.QPushButton(QPixmap((self.cpuIconPath)).scaledToHeight(20, Qt.SmoothTransformation),"")
    self.cpuImageButton.setObjectName("show_button_cpu")
    self.cpuImageButton.setToolTip("Click to toggle monitoring of CPU usage of this Nuke Session")
    self.cpuString = QtWidgets.QLabel("CPU (%)")
    self.cpuString.setToolTip("CPU usage of this Nuke Session")
    self.cpuImageButton.clicked.connect(lambda: self.show_button_clicked(self.cpuString))

    # DISK SECTION
    self.diskImageButton = QtWidgets.QPushButton(QPixmap((self.diskReadIconPath)).scaledToHeight(20, Qt.SmoothTransformation),"")
    self.diskImageButton.setObjectName("show_button_disk")
    self.diskImageButton.setToolTip("Click to toggle monitoring of Disk Read+Write usage for this machine")
    self.diskString = QtWidgets.QLabel("DISK (MB/s)")
    self.diskImageButton.clicked.connect(lambda: self.show_button_clicked(self.diskString))
    self.diskString.setToolTip("Disk Read+Write usage for this machine")

    # NETWORK SECTION
    self.networkImageButton = QtWidgets.QPushButton(QPixmap((self.networkReadIconPath)).scaledToHeight(20, Qt.SmoothTransformation),"")
    self.networkImageButton.setObjectName("show_button_network")
    self.networkImageButton.setToolTip("Click to toggle monitoring of Network Read+Write traffic")
    self.networkString = QtWidgets.QLabel("NETWORK (MB/s)")
    self.networkString.setToolTip("Total Network Read+Write traffic for this machine")
    self.networkImageButton.clicked.connect(lambda: self.show_button_clicked(self.networkString))

    # Settings Button - Displays what options should be shown in the Status Bar
    self.settingsButton = QtWidgets.QPushButton()
    self.settingsButton.setIcon(QIcon("icons:Settings.png"))
    self.settingsButton.clicked.connect(self.showSettings)

    # Build the layout based on Preferences
    #self.cpuWidget.setVisible(self.infoSettings['showCPU'])
    #self.memoryWidget.setVisible(self.infoSettings['showMemory'])
    #self.diskWidget.setVisible(self.infoSettings['showDisk'])
    #self.networkWidget.setVisible(self.infoSettings['showNetwork'])

    self.restartServerButton = QtWidgets.QPushButton(QPixmap("icons:TransformRotateRight.png").scaledToHeight(20, Qt.SmoothTransformation),"")
    self.restartServerButton.setFixedHeight(16)    
    self.restartServerButton.clicked.connect(self.restartServer)
    self.restartServerButton.setHidden(True)
    self.restartServerButton.setFlat(True)
    self.restartServerButton.setToolTip("Click here to restart the Nuke Frameserver")
    self.frameServerIsRendering = False

    self.spinnerMovie = QMovie("icons:RenderingSpinner.gif")
    self.spinnerMovie.start()

    self.bar.addPermanentWidget(self.cpuImageButton)
    self.bar.addPermanentWidget(self.cpuString)
    self.bar.addPermanentWidget(self.memoryImageButton)
    self.bar.addPermanentWidget(self.memoryString)
    self.bar.addPermanentWidget(self.diskImageButton)
    self.bar.addPermanentWidget(self.diskString)
    self.bar.addPermanentWidget(self.networkImageButton)
    self.bar.addPermanentWidget(self.networkString)
    self.bar.addPermanentWidget(self.frameserverStatusLabel)
    self.bar.addPermanentWidget(self.restartServerButton)
    self.bar.addPermanentWidget(self.settingsButton)

  def show_button_clicked(self, sender):
    sender.setVisible(not sender.isVisible())

  def _updateUIForServerIsRunning(self):
    """Updates the UI for when the server is reachable"""
    #self.frameserverStatusLabel.setToolTip("Nuke Frame Server is reachable")
    self.getFrameServerWorkers()
    self.frameserverStatusLabel.setPixmap(QPixmap("icons:OK.png"))
    self.restartServerButton.setHidden(True)

  def showSettings(self):
      dialog = SettingsDialog()
      dialog.show()

  # Returns a nicely formatted list of Frame Server workers
  def getFrameServerWorkers(self):
    statusString = str(self.frameServerInstance.getStatus(1000))
    workers = re.findall("workerStatus \{.*?\}", statusString)

    if len(workers) == 0:
        self.frameserverStatusLabel.setToolTip("Unable to determine number of frame server workers.")
        return

    prettyWorkersString = "Frame Server Status (%i workers):\n" % len(workers) + "\n".join(workers)
    self.frameserverStatusLabel.setToolTip(prettyWorkersString)

  def updateStatusBar(self):
    """Updates the Status bar widgets depending on whether the frameServer is reachable"""

    #print "Status: ", str(self.frameServerInstance.getStatus(10))

    # DEBUG - Stylesheet Changes can be applied here and seen live
    #self.bar.setStyleSheet( self.getLatestStyleSheet() )

    try:
      isRunning = self.frameServerInstance.isRunning(0.25)

      if isRunning and not self.rendersExistInQueue():
        self._updateUIForServerIsRunning()
        self.frameServerIsRendering = False

      elif isRunning and self.rendersExistInQueue():
        if self.frameServerIsRendering == False:
          self.frameServerIsRendering = True
          self.frameserverStatusLabel.setPixmap(None)
          self.frameserverStatusLabel.setMovie(self.spinnerMovie)

      else:
        self._handleServerUnreachable()

      self.updateResourcesStatusLabel()

    except:
      self._handleServerUnreachable()
      self.updateResourcesStatusLabel()

  def startMonitoring(self):
    """This timer fires every X milliseconds to update the status."""
    self.timer.start(self.updateMonitorIntervalMS)
    self.isMonitoring = True

  def stopMonitoring(self):
    """Stops the monitoring process"""
    self.timer.stop()
    self.isMonitoring = False

# Register this to hiero.ui.mainStatusBar
if not hasattr(hiero.ui, 'mainStatusBar'):
  hiero.ui.mainStatusBar = InfoBar()