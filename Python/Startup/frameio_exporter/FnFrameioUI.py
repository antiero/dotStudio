"""
UI elements for interaction with Frame.io from within Nuke Studio
"""
from PySide import QtGui
from PySide.QtCore import Qt, QUrl, QRegExp, QCoreApplication
from PySide.QtWebKit import QWebView
import hiero.core 
from hiero.ui import activeView, createMenuAction, mainWindow
import frameio
import os
import webbrowser

# Global path for icons
cwd = os.path.dirname(os.path.realpath(__file__))
gIconPath = os.path.abspath(os.path.join(cwd, "icons"))
gGoogleAccountsEnabled = False # until we get oauth2 login figured out

class FnFrameioMenu(QtGui.QMenu):
    def __init__(self):
        QtGui.QMenu.__init__(self, "Frame.io", None)
        hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)

        self._actionUploadSelection = createMenuAction("Login...", self.showFrameIODialog, icon=os.path.join(gIconPath, "logo-unconnected.png"))
        self._showSelectionInFrameIOAction = createMenuAction("Open in Frame.io", self.openSelectedInFrameIO, os.path.join(gIconPath, "frameio.png"))
                                                                
        self.addAction(self._showSelectionInFrameIOAction)
        self.addAction(self._actionUploadSelection)

    def showFrameIODialog(self):
        """
        Presents the Frame.io Widget with the active selection of Bin items
        (selection currently not used)
        """
        selection = activeView().selection()
        if not selection:
            return

        hiero.core.frameioDelegate.showFrameioDialogWithSelection(selection=selection)


    def openSelectedInFrameIO(self):
        """
        Tries to open the selected item in Frame.io
        """
        view = hiero.ui.activeView()
        if not view or not hasattr(view, 'selection'):
            return

        taggedSelection = [item for item in view.selection() if hasattr(item, 'tags')]

        if len(taggedSelection)==0:
            return

        # Get Tags which contain a frameio_filereferenceid key
        for item in taggedSelection:
            itemTags = item.tags()
            # It's possible that an item has multiple Frame.io Tags, get the one with the 
            frameIOTags = [tag for tag in itemTags if tag.metadata().hasKey("tag.description") and tag.metadata().value("tag.description") == "FrameIO Upload"]
            if len(frameIOTags)>1:
                # Find the Tag with latest upload time
                sortedTags = sorted(tags, key=lambda k: float(k.metadata().value("tag.frameio_upload_time")))
                print sortedTags
                latestTag = sortedTags[0]

            else:
                latestTag = frameIOTags[0]

            filereferenceid = latestTag.metadata().value("tag.frameio_filereferenceid")
            print "filereferenceid: " + str(filereferenceid)

            try:
                print "Trying to open browser for filereferenceid %s" % filereferenceid
                self.openFilereferenceIdInFrameIO(filereferenceid)
            except:
                print "Unable to open browser for filereferenceid %s" % filereferenceid

    def openFilereferenceIdInFrameIO(self, filereferenceid):
        """
        Looks to the Tag on the selected item and opens the browser to show the item
        """
        url = "https://app.frame.io/?f=" + filereferenceid
        webbrowser.open_new_tab(url)


    def eventHandler(self, event):
        # Check if this actions are not to be enabled

        if not hasattr(event.sender, 'selection'):
          # Something has gone wrong, we shouldn't only be here if raised
          # by the timeline view which will give a selection.
          return

        event.menu.addMenu(self)

class FnFrameioDialog(QtGui.QDialog):
    """
    Main Frame.io dialog for handling interaction with
    Frame.io
    """

    eStatusCheckEmail = "Checking E-mail."
    eStatusCheckCredentials = "Checking user login credentials."
    eStatusEmailInvalid = "Not a valid E-mail."
    eStatusGmailUnsupported =  "Google Accounts not currently supported."
    eStatusPasswordInvalid =  "Please enter a valid password."
    eStatusLoggingIn = "Logging in..."
    eConnectionError = "Connection error. Check internet access!"

    def __init__(self, delegate, username=None, usingExportDialog=False):
        QtGui.QDialog.__init__(self)
        global gIconPath
        self._clips = []
        self._sequences = []

        # The Dialog can work in two modes, as a popover from the Bin View or via the main App Export window
        self.usingExportDialog = usingExportDialog

        self.username = username

        # FrameioDelegate
        self.delegate = delegate

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

        layout = QtGui.QVBoxLayout(self)

        layout.setAlignment(Qt.AlignCenter)

        self.toolBar = QtGui.QToolBar()
        self.toolBar.setStyleSheet('QToolBar {background-color: #3B3E4A; border-width: 0px; border-radius: 0px; border-style: none;}')
        
        self.closeButton = QtGui.QPushButton("")
        self.closeButton.setStyleSheet('QPushButton {border: none;}')
        icon = QtGui.QIcon(os.path.join(gIconPath, "close.png"))

        self.closeButton.setIcon(icon)
        self.closeButton.clicked.connect(self.close)
        self.toolBar.addWidget(self.closeButton)
        layout.addWidget(self.toolBar)

        self.unconnectedIndicatorPixmap = QtGui.QPixmap(os.path.join(gIconPath, "logo-unconnected.png"))
        self.connectedIndicatorPixmap = QtGui.QPixmap(os.path.join(gIconPath, "logo-connected.png"))
        self.connectionIndicatorLabel = QtGui.QLabel("Unconnected")

        self.toolBar.addWidget(self.connectionIndicatorLabel)

        pixmap = QtGui.QPixmap(os.path.join(gIconPath, "frameio.png"))
        lbl = QtGui.QLabel("")
        lbl.setPixmap(pixmap)
        lbl.setAlignment(Qt.AlignCenter)    
        layout.addWidget(lbl)

        font = QtGui.QFont()
        font.setPointSize(20)
        self.topLabel = QtGui.QLabel("Sign In")
        self.topLabel.setFont(font)
        self.topLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.topLabel)

        self.statusLabel = QtGui.QLabel("")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.statusLabel)


        self.stackView = QtGui.QStackedWidget(self)

        # Login Screen View
        self.loginView = QtGui.QWidget()
        self.loginViewLayout = QtGui.QVBoxLayout(self)
        self.loginViewLayout.setAlignment(Qt.AlignCenter)        

        self.emailLineEdit = QtGui.QLineEdit()
        self.emailLineEdit.setPlaceholderText("E-mail")
        self.emailLineEdit.setFont(font)
        self.emailLineEdit.setAlignment(Qt.AlignCenter)  
        self.emailLineEdit.setFixedWidth(370)
        self.emailLineEdit.setFixedHeight(60)
        if self.username:
            self.emailLineEdit.setText(self.username)

        # Validator for checking email address is valid
        namerx = QRegExp("\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}\\b")
        namerx.setCaseSensitivity(Qt.CaseInsensitive);
        namerx.setPatternSyntax(QRegExp.RegExp);
        self.nameval = QtGui.QRegExpValidator(namerx, self)
        self.emailLineEdit.setValidator(self.nameval)

        self.loginViewLayout.addWidget(self.emailLineEdit)

        self.passwordLineEdit = QtGui.QLineEdit()
        self.passwordLineEdit.setStyleSheet('')
        self.passwordLineEdit.setPlaceholderText("Password")
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setAlignment(Qt.AlignCenter)  
        self.passwordLineEdit.setFixedWidth(370)
        self.passwordLineEdit.setFixedHeight(60)
        self.passwordLineEdit.setEchoMode(QtGui.QLineEdit.Password)

        self.loginViewLayout.addWidget(self.passwordLineEdit)        

        self.submitButton = QtGui.QPushButton("LET'S GO")
        self.submitButton.setFlat(True)
        self.submitButton.setFont(font)
        self.submitButton.clicked.connect(self._submitButtonPressed)
        self.submitButton.setStyleSheet('QPushButton {width: 370px; height: 60px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #83DEBD; color: white;}'
                                        'QPushButton:hover{background-color: #9974BA; }'
                                        'QPushButton:pressed{background-color: #404040; border-width: 1px}')

        self.loginViewLayout.addWidget(self.submitButton)
        self.loginView.setLayout(self.loginViewLayout)

        self.stackView.addWidget(self.loginView)

        ### TO-DO - handle uploading of Clips via drag-drop into a dropzone
        # self.uploadDropzoneView = QtGui.QWidget()
        # self.uploadDropzoneView.setAcceptDrops(True) # Not hooked up.

        # self.uploadDropzoneLayout = QtGui.QVBoxLayout(self)
        # self.uploadDropzoneLayout.setAlignment(Qt.AlignCenter)

        # pixmap = QtGui.QPixmap(os.path.join(gIconPath, "uploadDropzone-64px.png"))
        # uploadIcon = QtGui.QLabel("")
        # uploadIcon.setPixmap(pixmap)
        # uploadIcon.setAlignment(Qt.AlignCenter)
        # self.uploadDropzoneLayout.addWidget(uploadIcon)

        # self.uploadDropzoneLabel1 = QtGui.QLabel("Upload your files")
        # self.uploadDropzoneLabel1.setAlignment(Qt.AlignCenter)
        # self.uploadDropzoneLabel1.setFont(font)
        # self.uploadDropzoneLabel2 = QtGui.QLabel("Drag 'n Drop your files or Clips/Sequences here.")
        # self.uploadDropzoneLabel1.setAlignment(Qt.AlignCenter)
        # self.uploadDropzoneLayout.addWidget(self.uploadDropzoneLabel1)
        # font.setPointSize(16)
        # self.uploadDropzoneLabel2.setFont(font)
        # self.uploadDropzoneLayout.addWidget(self.uploadDropzoneLabel2)

        # self.uploadDropzoneView.setLayout(self.uploadDropzoneLayout)
        # self.stackView.addWidget(self.uploadDropzoneView)

        ### View to handle uploading of Clips and Timelines View
        self.uploadView = QtGui.QWidget()
        self.uploadView.setStyleSheet('QPushButton {width: 100px; height: 100px; border-width: 0px; border-radius: 50px; border-style: solid; background-color: #9974BA; color: white;}')

        self.uploadViewLayout = QtGui.QVBoxLayout(self)
        self.uploadViewLayout.setAlignment(Qt.AlignCenter)

        self.uploadTopButtonWidget = QtGui.QWidget()
        self.uploadTopButtonLayout = QtGui.QHBoxLayout(self)
        self.uploadTopButtonLayout.setAlignment(Qt.AlignCenter)
        self.uploadTimelineOptionButton = QtGui.QPushButton("Timeline")
        self.uploadClipOptionButton = QtGui.QPushButton("Clips")
        self.uploadTimelineOptionButton.setCheckable(True)
        self.uploadTimelineOptionButton.setChecked(False)
        self.uploadTimelineOptionButton.setFont(font)
        self.uploadClipOptionButton.setCheckable(True)
        self.uploadClipOptionButton.setChecked(False)
        self.uploadClipOptionButton.setFont(font)
        self.uploadTopButtonLayout.addWidget(self.uploadTimelineOptionButton)
        self.uploadTopButtonLayout.addWidget(self.uploadClipOptionButton)
        self.uploadTopButtonWidget.setLayout(self.uploadTopButtonLayout)

        # This will control whether annotations are uploaded into Frame.io for the item
        self.exportAnnotationsCheckbox = QtGui.QCheckBox("Export Tags+Annotations Text comments")

        self.uploadBottomButtonWidget = QtGui.QWidget()
        self.uploadBottomButtonLayout = QtGui.QHBoxLayout(self)
        self.uploadBottomButtonLayout.setAlignment(Qt.AlignCenter)
        self.uploadCancelButton = QtGui.QPushButton("Cancel")
        self.uploadCancelButton.setStyleSheet('QPushButton {width: 170px; height: 70px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #767C8E; color: white;}')
        self.uploadCancelButton.clicked.connect(self.close)

        self.uploadTaskButton = QtGui.QPushButton("Done")
        self.uploadTaskButton.setStyleSheet('QPushButton {width: 170px; height: 70px; border-width: 0px; border-radius: 4px; border-style: solid; color: white;}')
        self.uploadTaskButton.clicked.connect(self._uploadButtonPushed)
        font.setPointSize(20)
        self.uploadCancelButton.setFont(font)
        self.uploadTaskButton.setFont(font)
        self.uploadBottomButtonLayout.addWidget(self.uploadCancelButton)
        self.uploadBottomButtonLayout.addWidget(self.uploadTaskButton)
        self.uploadBottomButtonWidget.setLayout(self.uploadBottomButtonLayout)

        self.projectWidget = QtGui.QWidget()
        self.projectWidgetLayout = QtGui.QHBoxLayout(self)

        self.projectDropdown = QtGui.QComboBox()
        self.projectDropdown.setFont(font)
        self.projectDropdown.setEditable(True)
        self.projectDropdown.lineEdit().setAlignment(Qt.AlignCenter)
        self.projectDropdown.setEditable(False)
        self.projectDropdown.setStyleSheet('QComboBox {width: 350px; height: 50px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #4F535F; color: white;}')

        self.projectRefreshButton = QtGui.QPushButton("Refresh")
        self.projectRefreshButton.setStyleSheet('QPushButton {width: 50px; height: 50px; border-width: 0px; border-radius: 25px; border-style: solid; background-color: #767C8E; color: white;}')
        self.projectRefreshButton.clicked.connect(self._refreshProjectList)
        self.projectWidgetLayout.addWidget(self.projectDropdown)
        self.projectWidgetLayout.addWidget(self.projectRefreshButton)
        self.projectWidget.setLayout(self.projectWidgetLayout)
        
        ### Enable when annotation uploads are supported
        #self.uploadViewLayout.addWidget(self.exportAnnotationsCheckbox)
        
        self.uploadViewLayout.addWidget(self.projectWidget)
        self.uploadViewLayout.addWidget(self.uploadBottomButtonWidget)

        self.uploadView.setLayout(self.uploadViewLayout)

        self.stackView.addWidget(self.uploadView)

        sizeGrip = QtGui.QSizeGrip(self)
        sizeGrip.setStyleSheet("QSizeGrip { height:12px; }")

        layout.addWidget(self.stackView)
        layout.addWidget(sizeGrip, 0, Qt.AlignBottom | Qt.AlignRight);
        self.setMinimumSize(160, 160)        
        self.setLayout(layout)
        self.emailLineEdit.setFocus()


    def updateConnectionIndicator(self):
        """Updates the frame.io session authenticated indicator label"""
        if self.delegate.frameioSession.sessionAuthenticated:
            print "Frame.io session connected!"
            self.connectionIndicatorLabel.setText('Connected.')
        else:
            print "Frame.io session unconnected!"
            self.connectionIndicatorLabel.setText('Not Connected.')

    def show(self, selection=None):
        if selection:
            self._clips = [item.activeItem() for item in selection if hasattr(item, 'activeItem') and isinstance(item.activeItem(), hiero.core.Clip)]
            self._sequences = [item.activeItem() for item in selection if hasattr(item, 'activeItem') and isinstance(item.activeItem(), hiero.core.Sequence)]

        self.updateConnectionIndicator()

        # If we're usint the Export dialog, we always just show the Login view, not the Project view
        if self.usingExportDialog:
            self.showLoginView()

        return super(FnFrameioDialog, self).show()

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
        project = self.currentProject()
        self.setStatus("Clips: %s\n, Sequences %s" % (str(self._clips), str(self._sequences)))

        # Should move logic below out of UI here and just pass the items
        movieClips = []
        nonMovieClips = []
        
        if len(self._clips) > 0:
            # Find out which Clips do not need to be transcoded
            movieClips = [clip for clip in self._clips if hiero.core.isQuickTimeFileExtension(os.path.splitext(clip.mediaSource().filename())[-1])]
            nonMovieClips = [clip for clip in self._clips if clip not in movieClips]

        self.setStatus("Movie Clips: %s, nonMovieClips %s" % (str(movieClips), str(nonMovieClips)))
        filesToUpload = []
        for movClip in movieClips:
            filesToUpload += [ movClip.mediaSource().fileinfos()[0].filename() ]

        for filePath in filesToUpload:
            self.delegate.uploadFile(filePath, project)
 
    def showLoginView(self):
        # Sets the stackView to show the Login View
        self.stackView.setCurrentWidget(self.loginView)

    # def showDropzoneUploadView(self):
    #     # Sets the stackView to show the Dropzone Upload View
    #     self.stackView.setCurrentWidget(self.uploadDropzoneView)

    def showUploadView(self):
        # Sets the stackView to show the Upload View
        self._updateProjectsList()

        # If the dialog is launched from the Export dialog don't progress to the next screen, just exit.
        if not self.usingExportDialog:
            self.stackView.setCurrentWidget(self.uploadView)
        else:
            self.close()


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
        emailText = self.emailLineEdit.text()
        passwordText = self.passwordLineEdit.text()
        res = self.nameval.validate(emailText, 0)

        # If Gmail oauth2 is not implemented...
        if not gGoogleAccountsEnabled:
            if "gmail.com" in emailText or "googlemail.com" in emailText:
                    self.setStatus(self.eStatusGmailUnsupported)
                    self.emailLineEdit.setFocus()
                    return

        if res[0] != QtGui.QValidator.State.Acceptable:
                self.setStatus(self.eStatusEmailInvalid)
                self.emailLineEdit.setFocus()
                return
        else:
            self.setStatus(self.eStatusCheckEmail)
            self.username = emailText
            if len(passwordText) < 6:
                self.setStatus(self.eStatusPasswordInvalid)
                return
            else:
                self.password = passwordText

        if self.username and self.password:
            self.delegate.attemptLogin(self.username, self.password)

