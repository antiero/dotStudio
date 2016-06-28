# Modified from hiero.ui.FnStatusBar
import hiero.ui
from hiero.ui.nuke_bridge import nukestudio
from PySide.QtCore import Qt, QTimer, QCoreApplication
from PySide.QtGui import QLabel, QPixmap, QIcon, QWidget, QColor, QMovie, QPushButton
try:
  import psutil
  gEnableResourceMonitoring = True
except:
  print 'Unable to import psutil. Resource monitoring will be disabled.'
  gEnableResourceMonitoring = False

import os

def _bytesToMB(bytes):
  """Returns byte value in megabytes"""
  MB = float(bytes)/float(1<<20)
  return MB

def _bytesToGB(bytes):
  """Returns byte value in gigabytes"""
  GB = float(bytes)/float(1<<30)
  return GB

class PSUtilProcessWrapper(object):
  """This is a wrapper around a psutil.Process object, for the Nuke process"""
  def __init__(self):
  
    # This should be the process of Nuke.
    self.nukeProcess = psutil.Process(os.getpid())

  def nukeMemoryUsageAsPercentage(self):
    """Returns Nuke's current memory usage as percentage of Total memory"""
    mem_percent = self.nukeProcess.memory_percent()
    return mem_percent

  def nukeCPUUsageAsPercentage(self):
    """Returns Nuke's current CPU usage as percentage"""
    cpu_percent = self.nukeProcess.cpu_percent()
    return cpu_percent

  def nukeMemoryUsageInGB(self):
    """Returns Nuke's current memory usage in GB"""
    nuke_mem_bytes = self.nukeProcess.memory_info().rss
    nuke_mem_GB = _bytesToGB(nuke_mem_bytes)
    return nuke_mem_GB

  def numOpenFiles(self):
    """Returns the number of open files. Unused at present."""
    numOpenFiles = len(self.nukeProcess.get_open_files())
    return numOpenFiles

  def totalSystemMemory(self):
    """Returns the total System memory in GigaBytes"""
    return _bytesToGB(psutil.virtual_memory().total)

class MainStatusBar(object):
  """Adds a status bar to the bottom of the main window"""
  
  def __init__(self):
  
    global gEnableResourceMonitoring
    self.enableResourceMonitoring  = gEnableResourceMonitoring
    self.bar = hiero.ui.mainWindow().statusBar()

    self.updateMonitorIntervalMS = 1000 # The monitor update time in milliseconds.
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
    QTimer.singleShot(3000, self.startMonitoring)

  def hide(self):
    """Hide the status bar"""
    self.bar.setHidden(True)

  def show(self):
    """Show the status bar"""  
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
      self.nukeResourcesLabel.setStyleSheet("QLabel { font: 10pt; color: rgba("+values+"); }")
    else:
      self.nukeResourcesLabel.setStyleSheet("QLabel { font: 10pt; }")

  def restartServerAsync(self):
    self.frameServerInstance.stop()
    self.frameServerInstance.start()
    QTimer.singleShot(3000, self.startMonitoring)

  def restartServer(self):
    """Called to restart the Nuke Frame Server, done asynchronously"""
    self.stopMonitoring()
    self.restartServerButton.setHidden(True)
    self.nukeResourcesLabel.setText("Re-Starting Frame Server...")
    QTimer.singleShot(150, self.restartServerAsync)

  def updateResourcesStatusLabel(self):
    """Updates the Memory Label String"""
    
    if self.enableResourceMonitoring:
      currentMemUsageAsPercentage = self.processHelper.nukeMemoryUsageAsPercentage()
      currentCPUUsageAsPercentatge = self.processHelper.nukeCPUUsageAsPercentage()
      currentMemUsageGB = self.processHelper.nukeMemoryUsageInGB()
      totalSystemMemoryGB = self.processHelper.totalSystemMemory()
      memRatio = currentMemUsageGB / totalSystemMemoryGB

      diskMBPerSec = self._diskMBPerSec()
      networkMBPerSec = self._networkMBPerSec()

      self.nukeResourcesLabel.setText("RAM: %.2f GB (%.1f%%) | CPU: %.1f%% | DISK: %.2f MB/s | NETWORK: %.2f MB/s" % (currentMemUsageGB, 
        currentMemUsageAsPercentage,
        currentCPUUsageAsPercentatge,
        diskMBPerSec,
        networkMBPerSec))

      # This little test makes the label red if the memory usage exceeds 90% of the maximum allowed
      self._setResourcesLabelColour( memRatio, currentCPUUsageAsPercentatge )

  def _diskMBPerSec(self):
    """Returns Total Disk Read+Write speed in MB/s"""
    oldBytes = self.currentDiskIOBytes
    DISKS = psutil.disk_io_counters(perdisk=True)
    readWriteBytes =[(DISKS[disk].read_bytes, DISKS[disk].write_bytes)  for disk in DISKS.keys()]
    newBytes = sum([sum(x) for x in zip(*readWriteBytes)])
    bytesDiff = newBytes-oldBytes
    self.currentDiskIOBytes = newBytes
    bytesPerSecond = (newBytes-oldBytes)/(self.updateMonitorIntervalMS/1000)
    MBPerSecond = _bytesToMB(bytesPerSecond)
    return MBPerSecond

  def _networkMBPerSec(self):
    """Returns Total Network Read+Write speed in MB/s"""
    oldBytes = self.currentNetworkBytesReceived

    NET = psutil.net_io_counters(pernic=True)
    readWriteBytes =[(NET[adapter].bytes_recv, NET[adapter].bytes_sent)  for adapter in NET.keys()]
    newBytes = sum([sum(x) for x in zip(*readWriteBytes)])
    bytesDiff = newBytes-oldBytes
    self.currentNetworkBytesReceived = newBytes
    bytesPerSecond = (newBytes-oldBytes)/(self.updateMonitorIntervalMS/1000)
    MBPerSecond = _bytesToMB(bytesPerSecond)
    return MBPerSecond

  def setupUI(self):
    """Initialise the UI"""
    self.bar.setStyleSheet("QStatusBar::item { border: 0px}; ")
    self.bar.setFixedHeight(16)
    self.frameserverStatusLabel = QLabel("")
    self.nukeResourcesLabel = QLabel("")
    self.restartServerButton = QPushButton(QPixmap("icons:TransformRotateRight.png").scaledToHeight(16, Qt.SmoothTransformation),"")
    self.restartServerButton.setFixedHeight(16)    
    self.restartServerButton.clicked.connect(self.restartServer)
    self.restartServerButton.setHidden(True)
    self.restartServerButton.setFlat(True)
    self.restartServerButton.setToolTip("Click here to restart the Nuke Frameserver")
    self.frameServerIsRendering = False

    self.spinnerMovie = QMovie("icons:RenderingSpinner.gif")
    self.spinnerMovie.start()

    if self.enableResourceMonitoring:
      self.bar.addPermanentWidget(self.nukeResourcesLabel)
    
    self.bar.addPermanentWidget(self.frameserverStatusLabel)
    self.bar.addPermanentWidget(self.restartServerButton)

  def _updateUIForServerIsRunning(self):
    """Updates the UI for when the server is reachable"""
    self.frameserverStatusLabel.setToolTip("Nuke Frame Server is reachable")
    self.frameserverStatusLabel.setPixmap(QPixmap("icons:OK.png"))
    self.restartServerButton.setHidden(True)

  def updateStatusBar(self):
    """Updates the Status bar widgets depending on whether the frameServer is reachable"""

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
  hiero.ui.mainStatusBar = MainStatusBar()