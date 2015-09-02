"""""
UI elements for interaction with Frame.io from within Nuke Studio

"""
from PySide import QtGui
from PySide.QtCore import Qt, QUrl, QRegExp
from PySide.QtWebKit import QWebView 
import os
cwd = os.path.dirname(os.path.realpath(__file__))
gIconPath = os.path.abspath(os.path.join(cwd, "icons"))

class FrameioUploadWindow(QtGui.QWidget):

    eStatusCheckEmail = "Checking E-mail."
    eStatusCheckCredentials = "Checking user login credentials."
    eStatusEmailInvalid = "Not a valid E-mail."

    def __init__(self, *args):
        QtGui.QWidget.__init__(self, *args)

        global gIconPath

        self.emailAddress = None

        # setGeometry(x_pos, y_pos, width, height)
        self.setGeometry(240, 160, 726, 552)
        self.setStyleSheet('QWidget {background-color: #3B3E4A;} QLineEdit {border-color:#6F757F; border-width: 1px; border-radius: 4px; border-style: solid;}')
        self.setWindowTitle("Frame.io Uploader")

        #self.setAttribute( Qt.WA_TranslucentBackground, True )  
        self.setWindowFlags( Qt.FramelessWindowHint )
        self.setMouseTracking(True)

        self.draggable = True
        self.dragging_threshold = 2
        self.__mousePressPos = None
        self.__mouseMovePos = None

        layout = QtGui.QVBoxLayout(self)

        layout.setAlignment(Qt.AlignCenter)

        pixmap = QtGui.QPixmap(os.path.join(gIconPath+"logo-64px.png"))
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

        self.emailLineEdit = QtGui.QLineEdit()
        self.emailLineEdit.setPlaceholderText("E-mail")
        self.emailLineEdit.setFont(font)
        self.emailLineEdit.setAlignment(Qt.AlignCenter)  
        self.emailLineEdit.setFixedWidth(370)
        self.emailLineEdit.setFixedHeight(60)

        # Validator for checking email address is valid
        namerx = QRegExp("\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}\\b")
        namerx.setCaseSensitivity(Qt.CaseInsensitive);
        namerx.setPatternSyntax(QRegExp.RegExp);
        self.nameval = QtGui.QRegExpValidator(namerx, self)

        self.emailLineEdit.setValidator(self.nameval)
        layout.addWidget(self.emailLineEdit)

        self.passwordLineEdit = QtGui.QLineEdit()
        self.passwordLineEdit.setStyleSheet('')
        self.passwordLineEdit.setPlaceholderText("Password")
        self.passwordLineEdit.setHidden(True)
        self.passwordLineEdit.setFont(font)
        self.passwordLineEdit.setAlignment(Qt.AlignCenter)  
        self.passwordLineEdit.setFixedWidth(370)
        self.passwordLineEdit.setFixedHeight(60)
        self.passwordLineEdit.setEchoMode(QtGui.QLineEdit.Password)
        layout.addWidget(self.passwordLineEdit)        

        self.submitButton = QtGui.QPushButton("LET'S GO")
        self.submitButton.setFlat(True)
        self.submitButton.setFont(font)
        self.submitButton.clicked.connect(self._validateEmailAddress)
        self.submitButton.setStyleSheet('QPushButton {width: 370px; height: 60px; border-width: 0px; border-radius: 4px; border-style: solid; background-color: #83DEBD; color: white;}')
        layout.addWidget(self.submitButton)

        self.webView = QWebView()
        self.webView.load( QUrl( "http://frame.io" ) )

        sizeGrip = QtGui.QSizeGrip(self)
        sizeGrip.setStyleSheet("QSizeGrip { height:12px; }")
        layout.addWidget(sizeGrip, 0, Qt.AlignBottom | Qt.AlignRight);
        self.setMinimumSize(160, 160)        
        self.setLayout(layout)
        self.emailLineEdit.setFocus()


    def _validateEmailAddress(self):
        text = self.emailLineEdit.text()
        res = self.nameval.validate(text, 0)
        if res[0] != QtGui.QValidator.State.Acceptable:
                self.statusLabel.setText(self.eStatusEmailInvalid)
                self.emailLineEdit.setFocus()
        else:
            self.statusLabel.setText(self.eStatusCheckEmail)
            self.emailAddress = text

    def keyPressEvent(self, e):
        """Close the popover if Escape is pressed"""
        if e.key() == Qt.Key_Escape:
            self.close()            

F = FrameioUploadWindow()
F.show()