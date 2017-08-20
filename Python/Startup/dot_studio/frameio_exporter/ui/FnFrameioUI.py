"""
UI elements for interaction with Frame.io from within Nuke Studio
"""
from PySide2 import QtGui
from PySide2 import QtWidgets
# QtWebKit missing from Nuke 11?
from PySide2.QtWebKit import QWebView
from PySide2.QtCore import Qt, QUrl, QRegExp, QSize, Signal, Slot
from frameio_exporter.core import frameio
from frameio_exporter.ui import createMenuAction
from frameio_exporter.core.paths import gIconPath
from frameio_exporter import auth
import os
import json
import urllib2
import json
from urllib2 import Request, urlopen
from oauth2client.client import flow_from_clientsecrets
import httplib2

class FnFrameioDialog(QtWidgets.QDialog):
    """
    A shared Frame.io dialog for handling authentication and interaction with Frame.io
    """

    userLoggedOutSignal = Signal()

    eStatusCheckEmail = "Checking E-mail."
    eStatusCheckCredentials = "Checking user login credentials."
    eStatusEmailInvalid = "Not a valid E-mail."
    eStatusGmailUnsupported =  "Google Accounts not currently supported."
    eStatusPasswordInvalid =  "Please enter a valid password."
    eStatusLoggingIn = "Logging in..."
    eStatusLoggedIn = "Logged In"
    eConnectionError = "Connection error. Check internet access!"

    def __init__(self, delegate, usingExportDialog=False):
        QtWidgets.QDialog.__init__(self)
        self._clips = []
        self._sequences = []
        self.filePathsForUpload = []

        # The Main FrameIOPySide AppDelegate
        self.delegate = delegate

        # The Dialog can work in two modes, as a popover from the Bin View or via the main App Export window
        self.usingExportDialog = usingExportDialog

        self.email = ""

        # setGeometry(x_pos, y_pos, width, height)
        self.setGeometry(240, 160, 726, 552)
        self.setStyleSheet('QWidget {background-color: #3B3E4A;} QLineEdit {color: #D0D5DC; border-color:#6F757F; border-width: 1px; border-radius: 4px; border-style: solid;} QLabel {color: #D0D5DC;}')
        self.setWindowTitle("Frame.io Uploader")

        #self.setAttribute( Qt.WA_TranslucentBackground, True )
        self.setWindowFlags( Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint )
        self.setMouseTracking(True)
        self.draggable = True
        self.dragging_threshold = 0
        self.__mousePressPos = None
        self.__mouseMovePos = None

        layout = QtWidgets.QVBoxLayout(self)

        layout.setAlignment(Qt.AlignCenter)

        self.toolBar = QtWidgets.QToolBar()
        self.toolBar.setStyleSheet('QToolBar {background-color: #3B3E4A; border-width: 0px; border-radius: 0px; border-style: none; text-align: center}')
        self.toolBar.setIconSize( QSize(24,24) )
        
        self.closeButton = QtWidgets.QPushButton("")
        self.closeButton.setStyleSheet('QPushButton {border: none;}')
        iconClose = QtGui.Icon(os.path.join(gIconPath, "close.png"))
        self.closeButton.setIcon(iconClose)
        self.closeButton.clicked.connect(self.close)
      
        iconLogout = QtGui.Icon(os.path.join(gIconPath, "logout.png"))
        self.logoutToolBarAction = createMenuAction("", self.logoutPressed, icon=iconLogout)
        self.logoutToolBarAction.setVisible(False)
        self.logoutToolBarAction.setToolTip("Click here to Log out")

        self.unconnectedIndicatorPixmap = QtGui.QPixmap(os.path.join(gIconPath, "logo-unconnected.png"))
        self.connectedIndicatorPixmap = QtGui.QPixmap(os.path.join(gIconPath, "logo-connected.png"))
        self.connectionIndicatorLabel = QtWidgets.QLabel("Unconnected")

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.toolBar.addWidget(self.closeButton)
        self.toolBar.addWidget(spacer)
        self.toolBar.addWidget(self.connectionIndicatorLabel)
        self.toolBar.addAction(self.logoutToolBarAction)
        layout.addWidget(self.toolBar)

        pixmap = QtGui.QPixmap(os.path.join(gIconPath, "frameio.png"))
        lbl = QtWidgets.QLabel("")
        lbl.setPixmap(pixmap)
        lbl.setAlignment(Qt.AlignCenter)    
        layout.addWidget(lbl)

        font = QtGui.QFont()
        font.setPointSize(20)
        self.topLabel = QtWidgets.QLabel("Login")
        self.topLabel.setFont(font)
        self.topLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.topLabel)

        self.statusLabel = QtWidgets.QLabel("")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.statusLabel)


        self.stackView = QtWidgets.QStackedWidget(self)

        # Login Screen View
        self.loginView = QtWidgets.QWidget()
        self.loginViewLayout = QtWidgets.QVBoxLayout(self)
        self.loginViewLayout.setAlignment(Qt.AlignCenter)        

        self.emailLineEdit = QtWidgets.QLineEdit()
        self.emailLineEdit.setPlaceholderText("E-mail")
        self.emailLineEdit.setFont(font)
        self.emailLineEdit.setAlignment(Qt.AlignCenter)  
        self.emailLineEdit.setFixedWidth(370)
        self.emailLineEdit.setFixedHeight(60)
        if self.email:
            self.emailLineEdit.setText(self.email)

        self.emailLineEdit.setText("")

        # Validator for checking email address is valid
        namerx = QRegExp("\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}\\b")
        namerx.setCaseSensitivity(Qt.CaseInsensitive);
        namerx.setPatternSyntax(QRegExp.RegExp);
        self.nameval = QtWidgets.QRegExpValidator(namerx, self)
        self.emailLineEdit.setValidator(self.nameval)

        self.loginViewLayout.addWidget(self.emailLineEdit)

        self.passwordLineEdit = QtWidgets.QLineEdit()
        self.passwordLineEdit.setStyleSheet('')
        self.passwordLineEdit.setPlaceholderText("Password")
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setAlignment(Qt.AlignCenter)  
        self.passwordLineEdit.setFixedWidth(370)
        self.passwordLineEdit.setFixedHeight(60)
        self.passwordLineEdit.setEchoMode(QtWidgets.QLineEdit.Password)

        # Initially hide the password field, as we typically log in as Google Auth
        self.passwordLineEdit.setVisible(False)

        self.loginViewLayout.addWidget(self.passwordLineEdit)        

        self.submitButton = QtWidgets.QPushButton("LET'S GO")
        self.submitButton.setFlat(True)
        self.submitButton.setFont(font)
        self.submitButton.clicked.connect(self._submitButtonPressed)
        self.submitButton.setStyleSheet('QPushButton {width: 370px; height: 60px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #83DEBD; color: white;}'
                                        'QPushButton:hover{background-color: #9974BA; }'
                                        'QPushButton:pressed{background-color: #404040; border-width: 1px}')

        self.loginViewLayout.addWidget(self.submitButton)

        # This WebView is used for Google OAuth2 Login
        self.webView = QWebView(parent=self)
        self.loginViewLayout.addWidget(self.webView)
        self.webView.setVisible(False)
        self.loginView.setLayout(self.loginViewLayout)

        self.stackView.addWidget(self.loginView)

        ### TO-DO - handle uploading of Clips via drag-drop into a dropzone
        self.uploadFilesView = QtWidgets.QWidget()
        self.uploadFilesView.setAcceptDrops(True) # Not hooked up.

        self.uploadDropzoneLayout = QtWidgets.QVBoxLayout(self)
        self.uploadDropzoneLayout.setAlignment(Qt.AlignCenter)

        pixmap = QtGui.QPixmap(os.path.join(gIconPath, "uploadDropzone-64px.png"))
        uploadIcon = QtWidgets.QLabel("")
        uploadIcon.setPixmap(pixmap)
        uploadIcon.setAlignment(Qt.AlignCenter)
        self.uploadDropzoneLayout.addWidget(uploadIcon)

        self.uploadDropzoneLabel1 = QtWidgets.QLabel("Upload your files")
        self.uploadDropzoneLabel1.setAlignment(Qt.AlignCenter)
        self.uploadDropzoneLabel1.setFont(font)
        self.uploadDropzoneLabel2 = QtWidgets.QLabel("Or choose files from picker...")
        self.uploadDropzoneLabel1.setAlignment(Qt.AlignCenter)
        self.uploadDropzoneLayout.addWidget(self.uploadDropzoneLabel1)
        font.setPointSize(16)
        self.uploadDropzoneLabel2.setFont(font)
        self.uploadDropzoneLayout.addWidget(self.uploadDropzoneLabel2)

        self.selectFilesButton = QtWidgets.QPushButton("Choose Files...")
        self.selectFilesButton.clicked.connect(self.showFilePicker)
        self.uploadDropzoneLayout.addWidget(self.selectFilesButton)

        self.uploadFilesView.setLayout(self.uploadDropzoneLayout)
        self.stackView.addWidget(self.uploadFilesView)

        ### View to handle uploading into a Project
        self.projectUploadView = QtWidgets.QWidget()
        self.projectUploadView.setStyleSheet('QPushButton {width: 100px; height: 100px; border-width: 0px; border-radius: 50px; border-style: solid; background-color: #9974BA; color: white;}')

        self.projectUploadViewLayout = QtWidgets.QVBoxLayout(self)
        self.projectUploadViewLayout.setAlignment(Qt.AlignCenter)

        self.uploadTopButtonWidget = QtWidgets.QWidget()
        self.uploadTopButtonLayout = QtWidgets.QHBoxLayout(self)
        self.uploadTopButtonLayout.setAlignment(Qt.AlignCenter)
        self.uploadTimelineOptionButton = QtWidgets.QPushButton("Timeline")
        self.uploadClipOptionButton = QtWidgets.QPushButton("Clips")
        self.uploadTimelineOptionButton.setCheckable(True)
        self.uploadTimelineOptionButton.setChecked(False)
        self.uploadTimelineOptionButton.setFont(font)
        self.uploadClipOptionButton.setCheckable(True)
        self.uploadClipOptionButton.setChecked(False)
        self.uploadClipOptionButton.setFont(font)
        self.uploadTopButtonLayout.addWidget(self.uploadTimelineOptionButton)
        self.uploadTopButtonLayout.addWidget(self.uploadClipOptionButton)
        self.uploadTopButtonWidget.setLayout(self.uploadTopButtonLayout)

        self.uploadBottomButtonWidget = QtWidgets.QWidget()
        self.uploadBottomButtonLayout = QtWidgets.QHBoxLayout(self)
        self.uploadBottomButtonLayout.setAlignment(Qt.AlignCenter)
        self.uploadCancelButton = QtWidgets.QPushButton("Cancel")
        self.uploadCancelButton.setStyleSheet('QPushButton {width: 170px; height: 70px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #767C8E; color: white;}')
        self.uploadCancelButton.clicked.connect(self.close)

        self.uploadTaskButton = QtWidgets.QPushButton("Done")
        self.uploadTaskButton.setStyleSheet('QPushButton {width: 170px; height: 70px; border-width: 0px; border-radius: 4px; border-style: solid; color: white;}')
        self.uploadTaskButton.clicked.connect(self._uploadButtonPushed)
        font.setPointSize(20)
        self.uploadCancelButton.setFont(font)
        self.uploadTaskButton.setFont(font)
        self.uploadBottomButtonLayout.addWidget(self.uploadCancelButton)
        self.uploadBottomButtonLayout.addWidget(self.uploadTaskButton)
        self.uploadBottomButtonWidget.setLayout(self.uploadBottomButtonLayout)

        self.projectWidget = QtWidgets.QWidget()
        self.projectWidgetLayout = QtWidgets.QHBoxLayout(self)

        self.projectDropdown = QtWidgets.QComboBox()
        self.projectDropdown.setFont(font)
        self.projectDropdown.setEditable(True)
        self.projectDropdown.lineEdit().setAlignment(Qt.AlignCenter)
        self.projectDropdown.setEditable(False)
        self.projectDropdown.setStyleSheet('QComboBox {width: 350px; height: 50px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #4F535F; color: white;}')

        self.projectRefreshButton = QtWidgets.QPushButton("Refresh")
        self.projectRefreshButton.setStyleSheet('QPushButton {width: 50px; height: 50px; border-width: 0px; border-radius: 25px; border-style: solid; background-color: #767C8E; color: white;}')
        self.projectRefreshButton.clicked.connect(self._refreshProjectList)
        self.projectWidgetLayout.addWidget(self.projectDropdown)

        #self.projectWidgetLayout.addWidget(self.projectRefreshButton)
        self.projectWidget.setLayout(self.projectWidgetLayout)

        self.projectUploadViewLayout.addWidget(self.projectWidget)
        self.projectUploadViewLayout.addWidget(self.uploadBottomButtonWidget)

        self.projectUploadView.setLayout(self.projectUploadViewLayout)

        self.stackView.addWidget(self.projectUploadView)

        sizeGrip = QtWidgets.QSizeGrip(self)
        sizeGrip.setStyleSheet("QSizeGrip { height:12px; }")

        layout.addWidget(self.stackView)
        layout.addWidget(sizeGrip, 0, Qt.AlignBottom | Qt.AlignRight);
        self.setMinimumSize(160, 160)        
        self.setLayout(layout)
        self.emailLineEdit.setFocus()

    def showFilePicker(self):
        """
        Presents the File Chooser for Uploads
        """
        #fname, _ = QtWidgets.QFileDialog.getOpenFileName(self.toolBar, 'Choose Files for Upload', '/')
        self.fileOpenDialog = QtWidgets.QFileDialog(self)
        self.fileOpenDialog.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Popup)
        #(fileNames, selectedFilter) = self.fileOpenDialog.getOpenFileName(caption="Choose Files for Upload")
        if self.fileOpenDialog.exec_():
            fileNames = self.fileOpenDialog.selectedFiles()
            print "Got Files: " + str(fileNames)

            # Store File Paths
            self.filePathsForUpload = fileNames

            self.showProjectUploadView()
            #self.delegate.uploadFile(fileNames[0])

    def updateConnectionIndicator(self):
        """Updates the frame.io session authenticated indicator label"""

        if self.delegate.frameioSession.sessionHasValidCredentials:
            self.connectionIndicatorLabel.setText('Connected (%s)' % self.delegate.frameioSession.email )
            self.logoutToolBarAction.setVisible(True)
        else:
            print "Frame.io session unconnected!"
            self.connectionIndicatorLabel.setText('Not Connected')
            self.logoutToolBarAction.setVisible(False)

    def show(self):

        self.updateConnectionIndicator()

        # If we're using the Export dialog, we always just show the Login view, not the Project view
        if self.usingExportDialog:
            self.showLoginView()

        return super(FnFrameioDialog, self).show()

    def logoutPressed(self):
        print "logoutPressed"
        self.userLoggedOutSignal.emit()
        self.delegate.resetSession()
        self.showLoginView()

    def keyPressEvent(self, e):
        """Close the popover if Escape is pressed"""
        if e.key() == Qt.Key_Escape:
            self.close()        
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._submitButtonPressed()


    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.__mousePressPos = event.globalPos()                # global
            self.__mouseMovePos = event.globalPos() - self.pos()    # local
        super(FnFrameioDialog, self).mousePressEvent(event)
 
    def mouseMoveEvent(self, event):
        if self.draggable and event.buttons() & Qt.LeftButton:
            globalPos = event.globalPos()
            if globalPos and self.__mousePressPos:
                moved = globalPos - self.__mousePressPos
                diff = globalPos - self.__mouseMovePos
                self.move(diff)
                self.__mouseMovePos = globalPos - self.pos()
        super(FnFrameioDialog, self).mouseMoveEvent(event)

    def setStatus(self, text, debug=False):
        self.statusLabel.setText(text)
        if debug:
            print str(text)

    def currentProject(self):
        """Returns the currently selected Project name"""
        return self.projectDropdown.currentText()

    def _uploadButtonPushed(self):
        # Not currently implemented
        print "uploadPushed, trying to upload: " + str(self.filePathsForUpload[0])
        self.delegate.uploadFile(self.filePathsForUpload[0])

 
    def showLoginView(self):
        # Sets the stackView to show the Login View
        self.stackView.setCurrentWidget(self.loginView)
        self.hidePasswordField()


    def showUploadFilesView(self):
        # Sets the stackView to show the Upload Files view

        # If the dialog is launched from the Export dialog don't progress to the next screen, just exit.
        if not self.usingExportDialog:
            self.stackView.setCurrentWidget(self.uploadFilesView)
        else:
            self.close()

    def showProjectUploadView(self):
        # Sets the stackView to show the Project Picker View, allowing upload process
        self._updateProjectsList()
        self.stackView.setCurrentWidget(self.projectUploadView)

    def showPasswordField(self):
        self.passwordLineEdit.setVisible(True)

    def hidePasswordField(self):
        self.passwordLineEdit.setVisible(False)

    def currentEmailText(self):
        return self.emailLineEdit.text()

    def currentPasswordText(self):
        return self.passwordLineEdit.text()

    def _refreshProjectList(self):
        # Refreshes the user data
        self.delegate.frameioSession.reloadUserdata()
        self._updateProjectsList()

    def _updateProjectsList(self):
        #Updates the Project list with list of project strings
        self.projectDropdown.clear()
        projects = self.delegate.frameioSession.projectdict().values()
        for project in projects:
            self.projectDropdown.addItem(project)

    def _submitButtonPressed(self):
        """Called when Submit button is pressed."""
        email = self.currentEmailText()

        self.delegate.attemptLogin(email)

        email_type = None
        if self.delegate.frameioSession.loginHandler:
            email_type = self.delegate.frameioSession.email_type


        if not email_type:
            print 'Email type not received...'
            return
        else:
            print "Email type: ", str(email_type)
            return

        if email_type == auth.AUTH_MODE_OAUTH:
            print "Email type is OAuth"
            return

        if self.passwordLineEdit.isVisible():
            self.password = self.passwordLineEdit.text()
        res = self.nameval.validate(emailText, 0)

        if res[0] != QtWidgets.QValidator.State.Acceptable:
                self.setStatus(self.eStatusEmailInvalid)
                self.emailLineEdit.setFocus()
                return
        else:
            self.setStatus(self.eStatusCheckEmail)
            self.email = emailText
            if len(passwordText) < 6:
                self.setStatus(self.eStatusPasswordInvalid)
                return
            else:
                self.password = passwordText

        if self.email and self.password:
            self.delegate.attemptLogin()

