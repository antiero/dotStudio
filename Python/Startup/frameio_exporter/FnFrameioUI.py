"""
UI elements for interaction with Frame.io from within Nuke Studio

"""
from PySide import QtGui
from PySide.QtCore import Qt, QUrl, QRegExp
from PySide.QtWebKit import QWebView 
import frameio
import os
cwd = os.path.dirname(os.path.realpath(__file__))
#gIconPath = os.path.abspath(os.path.join(cwd, "icons"))
gIconPath = "/Users/ant/.nuke/Python/Startup/frameio_exporter/icons/"

gGoogleAccountsEnabled = False # until we get oauth2 login figured out

class FrameioUploadWindow(QtGui.QWidget):

    eStatusCheckEmail = "Checking E-mail."
    eStatusCheckCredentials = "Checking user login credentials."
    eStatusEmailInvalid = "Not a valid E-mail."
    eStatusGmailUnsupported =  "Google Accounts not currently supported."
    eStatusPasswordInvalid =  "Please enter a valid password."

    def __init__(self, delegate, username=None):
        super(FrameioUploadWindow, self).__init__()

        global gIconPath
        self.username = username

        # FrameioDelegate
        self.delegate = delegate #kwargs.get("delegate", None)

        # setGeometry(x_pos, y_pos, width, height)
        self.setGeometry(240, 160, 726, 552)
        self.setStyleSheet('QWidget {background-color: #3B3E4A;} QLineEdit {color: #D0D5DC; border-color:#6F757F; border-width: 1px; border-radius: 4px; border-style: solid;} QLabel {color: #D0D5DC;}')
        self.setWindowTitle("Frame.io Uploader")

        #self.setAttribute( Qt.WA_TranslucentBackground, True )  
        self.setWindowFlags( Qt.FramelessWindowHint )
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
        icon = QtGui.QIcon(os.path.join(gIconPath + "close.png"))

        self.closeButton.setIcon(icon)
        self.closeButton.clicked.connect(self.close)
        self.toolBar.addWidget(self.closeButton)
        layout.addWidget(self.toolBar)

        pixmap = QtGui.QPixmap(os.path.join(gIconPath + "logo-64px.png"))
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
        self.submitButton.setStyleSheet('QPushButton {width: 370px; height: 60px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #83DEBD; color: white;}')

        self.loginViewLayout.addWidget(self.submitButton)

        self.loginView.setLayout(self.loginViewLayout)
        self.stackView.addWidget(self.loginView)

        # Upload Screen View
        self.uploadView = QtGui.QWidget()
        self.uploadView.setStyleSheet('QPushButton {width: 100px; height: 100px; border-width: 0px; border-radius: 50px; border-style: solid; background-color: #9974BA; color: white;}')

        self.uploadViewLayout = QtGui.QVBoxLayout(self)
        self.uploadViewLayout.setAlignment(Qt.AlignCenter)

        self.uploadOptionWidget = QtGui.QWidget()
        self.uploadButtonLayout = QtGui.QHBoxLayout(self)
        self.uploadButtonLayout.setAlignment(Qt.AlignCenter)
        self.uploadTimelineOptionButton = QtGui.QPushButton("Timeline")
        self.uploadClipOptionButton = QtGui.QPushButton("Clips")
        self.uploadTimelineOptionButton.setCheckable(True)
        self.uploadTimelineOptionButton.setChecked(False)
        font.setPointSize(16)
        self.uploadTimelineOptionButton.setFont(font)
        self.uploadClipOptionButton.setCheckable(True)
        self.uploadClipOptionButton.setChecked(False)
        self.uploadClipOptionButton.setFont(font)
        self.uploadButtonLayout.addWidget(self.uploadTimelineOptionButton)
        self.uploadButtonLayout.addWidget(self.uploadClipOptionButton)
        self.uploadOptionWidget.setLayout(self.uploadButtonLayout)
        self.uploadViewLayout.addWidget(self.uploadOptionWidget)

        self.projectDropdown = QtGui.QComboBox()
        self.projectDropdown.setStyleSheet('QComboBox {width: 370px; height: 60px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #4F535F; color: white;}')

        self.uploadViewLayout.addWidget(self.projectDropdown)

        self.uploadView.setLayout(self.uploadViewLayout)

        self.stackView.addWidget(self.uploadView)

        sizeGrip = QtGui.QSizeGrip(self)
        sizeGrip.setStyleSheet("QSizeGrip { height:12px; }")

        layout.addWidget(self.stackView)
        layout.addWidget(sizeGrip, 0, Qt.AlignBottom | Qt.AlignRight);
        self.setMinimumSize(160, 160)        
        self.setLayout(layout)
        self.emailLineEdit.setFocus()

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.__mousePressPos = event.globalPos()                # global
            self.__mouseMovePos = event.globalPos() - self.pos()    # local
        super(FrameioUploadWindow, self).mousePressEvent(event)
 
    def mouseMoveEvent(self, event):
        if self.draggable and event.buttons() & Qt.LeftButton:
            globalPos = event.globalPos()
            moved = globalPos - self.__mousePressPos
            if moved.manhattanLength() > self.dragging_threshold:
                # move when user drag window more than dragging_threshold
                diff = globalPos - self.__mouseMovePos
                self.move(diff)
                self.__mouseMovePos = globalPos - self.pos()
        super(FrameioUploadWindow, self).mouseMoveEvent(event)
 
    def showLoginView(self):
        # Sets the stackView to show the Login View
        self.stackView.setCurrentWidget(self.loginView)
 
    def showUploadView(self):
        # Sets the stackView to show the Upload View
        self.stackView.setCurrentWidget(self.uploadView)

    def _updateProjectsList(self, projects):
        #Updates the Project list with list of project strings
        self.projectDropdown.clear()
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
                    self.statusLabel.setText(self.eStatusGmailUnsupported)
                    self.emailLineEdit.setFocus()
                    return

        if res[0] != QtGui.QValidator.State.Acceptable:
                self.statusLabel.setText(self.eStatusEmailInvalid)
                self.emailLineEdit.setFocus()
                return
        else:
            self.statusLabel.setText(self.eStatusCheckEmail)
            self.username = emailText
            if len(passwordText) < 6:
                self.statusLabel.setText(self.eStatusPasswordInvalid)
                return
            else:
                self.password = passwordText

        if self.username and self.password:
            self.statusLabel.setText("Logging in...")
            self.delegate.attemptLogin(self.username, self.password)

    def keyPressEvent(self, e):
        """Close the popover if Escape is pressed"""
        if e.key() == Qt.Key_Escape:
            self.close()