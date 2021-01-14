# -*- coding: utf-8 -*-


"""
Interaction with frame.io from via PySide Panel

Usage:

nuke2frameio by Til Strobl, www.movingmedia.de
"""
from frameio_exporter.core import frameio
from frameio_exporter.ui import FnFrameioUI
import threading
from PySide.QtCore import QObject, QCoreApplication, Signal, Slot
import os, logging
import webbrowser
from frameio_exporter.exporters.FnFrameioTranscodeExporter import NukeFrameioFileReferenceTask
from frameio_exporter.auth import check_email_type, AUTH_MODE_EMAIL, AUTH_MODE_OAUTH, BasicLoginHandler, OAuthLoginHandler
from frameio_exporter.upload import UploadTask


class FrameioDelegate(QObject):
    """Delegate for handling the Frame.io session and communicating with UI"""

    FrameioConnectionChanged = Signal()

    def __init__(self, *args, **kwargs):

        # To-do: User QSettings Object for storing uistate.ini data.
        #self.appSettings = QSettings()
        self.frameioSession = frameio.UserSession("")
        self.frameioMainViewController = FnFrameioUI.FnFrameioDialog(self)

    def resetSession(self):
        """
        Resets the current Frame.io UserSession
        """
        self.frameioSession = frameio.UserSession("") 

    def showFrameioDialog(self):
        """Shows the dialog"""

        self.frameioMainViewController.show()

        if not self.frameioSession.sessionHasValidCredentials:
            self.frameioMainViewController.showLoginView()
        else:
            self.frameioMainViewController.showUploadFilesView()

        self.frameioMainViewController.move(QCoreApplication.instance().desktop().screen().rect().center() - self.frameioMainViewController.rect().center())

    @Slot(dict)
    def on_frameio_credentials_received(self, credentialsDict):
        logging.info("Credentials received: " + str(credentialsDict))
        self.frameioSession.sessionHasValidCredentials = True
        self.frameioMainViewController.showUploadFilesView()
        self.frameioMainViewController.topLabel.setText("Frame.io")
        self.frameioMainViewController.setStatus(self.frameioMainViewController.eStatusLoggedIn)
        self.frameioMainViewController.updateConnectionIndicator()


    @Slot(dict)
    def on_password_required(self):
        print "No password. Show password"
        self.frameioSession.sessionHasValidCredentials = True
        self.frameioMainViewController.showPasswordField()

    @Slot()
    def logout_requested(self):
        print "Logout Requested"
        self.showLoginView()

    def attemptLogin(self, email = ''):
        """
        Triggered when Login button pressed. Attempts to Login to frame.io and store the session in global variable
        """
        print "Attempting login..."
        self.frameioMainViewController.setStatus(self.frameioMainViewController.eStatusLoggingIn)

        if not email:
            logging.error("No email address was specified. Please try again with an email.")
            return

        # inialise a new Frame.io Session, based on email address
        self.frameioSession = frameio.UserSession(email)

        # A Frame.io Session is constructed via an email address.
        # The loginHandler object of the Session handles the login process.
        print 'Email: ', email

        # Initially check the type of email and determine if it's a Google Email...
        self.frameioSession.email_type = check_email_type(email)

        if self.frameioSession.email_type == AUTH_MODE_EMAIL:
            self.frameioSession.loginHandler = BasicLoginHandler(email)
            password = self.frameioMainViewController.currentPasswordText()
            if not password or len(password)<6: 
                self.frameioSession.loginHandler.passwordRequiredSignal.connect(self.on_password_required)
            else:
                self.frameioSession.loginHandler.frameio_password = password

        elif self.frameioSession.email_type == AUTH_MODE_OAUTH:
            self.frameioSession.loginHandler = OAuthLoginHandler(email)
        else:
            logging.error("Unable to determine email type")
            return

        # Connect loginHandler up to handle login success
        if self.frameioSession.loginHandler:
            self.frameioSession.loginHandler.loggedInSignal.connect(self.on_frameio_credentials_received)

        logging.info('self.email_type: ', self.frameioSession.email_type)

        self.frameioSession.loginHandler.login()


    def disconnectCurrentSession(self):
        """
        Disconnects the current session.
        """
        self.frameioSession = None
        self.userLoggedOutSignal.emit()


    def uploadFile(self, filePath, fileReferenceID = None):
        """Starts upload task for a given filePath. Returns a frame.io file reference"""

        uploads = {}
        if not os.path.isfile(filePath):
            return


        # Get Selected Project from UI
        project = self.frameioMainViewController.currentProject()

        if self.frameioSession.sessionHasValidCredentials:
            print "Setting project to be: " + str(project)
            self.frameioSession.setProject(project)

        # TO-DO: If a project item is passed with an existing fileReferenceID, check if the fileref exists
        if fileReferenceID:
            filereference = frameiosession.getFilereference(fileReferenceID)
            if filereference.exists():
                size1 = filereference.getSize()
                size2 = os.stat(filePath).st_size
                if size1 == size2:
                    return

        print "filePath: %s, fileReferenceID: %s " % (str(filePath), str(fileReferenceID))

        uploads[filePath] = {"annotations": '', "fileReferenceID": fileReferenceID}

        print "*** UPLOADS PASSED TO NukeFrameioFileReferenceTask: %s" % str(uploads)

        if len(uploads.keys()) != 0:
            frameioFileReferenceTask = UploadTask(uploads, self.frameioSession)
            print "Preparing uploads Thread about to start"
            threading.Thread( None, frameioFileReferenceTask.upload ).start()

        return fileReferenceID