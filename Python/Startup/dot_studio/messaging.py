# messaging.py
# Adds some methods to hiero.ui for presenting dialogs and setting status bar messages
# Antony Nasce Feb 14th 2014 - http://github.com/antiero
import hiero.ui
from hiero.core import log
from PySide2 import QtCore, QtGui, QtWidgets

def statusBar():
  """Returns an instance of the MainWindow's status bar, displayed at the bottom of the main window()"""
  return hiero.ui.mainWindow().statusBar()

# The status bar comes for free with the Mainwindow... 
hiero.ui.statusBar = statusBar

# Message Dialogs
def showInfo(prompt):
  """
  showInfo(prompt) -> Show an info dialog box with prompt and an OK button.
    
    @param prompt: Information text to display.
    @return: None
  """
  hiero.core.log.info(prompt)
  dialog = QtWidgets.QMessageBox.information( hiero.ui.mainWindow(), "Info", unicode(prompt) )
  
def showWarning(prompt):
  """
  showWarning(prompt) -> Show a warning dialog box with prompt and an OK button.
    
    @param prompt: Present user with this warning message.
    @return: None
  """
  hiero.core.log.info(prompt)
  dialog = QtWidgets.QMessageBox.warning( hiero.ui.mainWindow(), "Warning", unicode(prompt))
  
def showError(prompt):
  """
  showError(prompt) -> Show a critical error dialog box with prompt and an OK button.
    
    @param prompt: Present user with this error message.
    @return: None
  """
  hiero.core.log.error(prompt)
  dialog = QtWidgets.QMessageBox.critical( hiero.ui.mainWindow(), "Error", unicode(prompt) )

def clearStatusMessage():
  """
  clearStatusMessage() -> Removes any message being shown in the Mainwindow's statusbar.
  """
  hiero.ui.statusBar().clearMessage()

def statusMessage():
  """
  statusMessage() -> returns the current status message displayed in the Hiero statusbar.
  """
  return unicode(hiero.ui.statusBar().currentMessage())

def setStatusMessage(message, time = 0, showBarIfHidden = True):
  """
  setStatusMessage(message, time = 0) -> Shows a message in the Mainwindow's statusbar.
    Displays the given message for the specified number of milliseconds, specified by time keyword argument.
    If time is 0 (default), the message remains displayed until hiero.ui.clearStatusMessage() is called or until setStatusMesssage() is called again to change the message.
    
    @param message: string to display in the Mainwindow statusbar
    @param time: (optional) - a duration value in milliseconds, after which which the status message will be hidden.
    @param showBarIfHidden (optional) - If 'True' and the statusbar is hidden, this will force the statusbar to be shown. 'False' will keep it hidden.
    @return: None 
  """
  mBar = hiero.ui.statusBar()
  if showBarIfHidden:
    if not mBar.isVisible():
      mBar.show()
  mBar.showMessage(message, timeout = time)

def toggleStatusBar():
  """Toggles the visibility of the Mainwindow StatusBar"""
  mBar = hiero.ui.statusBar()
  mBar.setHidden( mBar.isVisible() )

# Punch these all in to hiero.ui
hiero.ui.showInfo = showInfo
hiero.ui.showWarning = showWarning
hiero.ui.showError = showError
hiero.ui.setStatusMessage = setStatusMessage
hiero.ui.statusMessage = statusMessage
hiero.ui.clearStatusMessage = clearStatusMessage
hiero.ui.toggleStatusBar = toggleStatusBar