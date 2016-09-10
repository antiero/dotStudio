# -*- coding: utf-8 -*-


"""
Interaction with frame.io from within Nuke Studio

Usage:

nuke2frameio by Til Strobl, www.movingmedia.de
"""
from frameio_exporter.core import frameio
from frameio_exporter.ui import FnFrameioUI
import hiero.core
import threading
from hiero.core import ApplicationSettings
import nuke
from PySide.QtCore import QCoreApplication, Slot
import os, logging
import webbrowser
from frameio_exporter.exporters.FnFrameioTranscodeExporter import NukeFrameioFileReferenceTask
from hiero.core import events
from frameio_exporter.auth import check_email_type, AUTH_MODE_EMAIL, AUTH_MODE_OAUTH, BasicLoginHandler, OAuthLoginHandler

# This will be used to communicate when a connection change event has occurred.
events.registerEventType("kFrameioConnectionChanged")

class FrameioDelegate(object):
    """Delegate for handling the Frame.io session and communicating with UI"""
    def __init__(self, *args, **kwargs):

        self.frameioSession = frameio.Session("") 
        self.appSettings = ApplicationSettings()

        self.email = kwargs.get("username", None)
        self.project = None # Populate with the last 

        # See if username exists already in uistate.ini
        if not self.email:
            savedUserPreference = self.appSettings.value("FrameioUsername")
            if savedUserPreference:
                self.email = savedUserPreference

        self.frameioMainViewController = FnFrameioUI.FnFrameioDialog(email = self.email)

        # This tells the authentication indicator to update when the status changes
        hiero.core.events.registerInterest("kFrameioConnectionChanged", self.handleConnectionStatusChangeEvent)

    def showFrameioDialogWithSelection(self, selection):
        """Shows the dialog from the Bin View"""

        # We're not using the Export dialog, so use the normal flow
        self.frameioMainViewController.usingExportDialog = False
        self.frameioMainViewController.show()

        if not self.frameioSession.sessionHasValidCredentials:
            self.frameioMainViewController.showLoginView()
        else:
            self.frameioMainViewController.showUploadView()

        self.frameioMainViewController.move(QCoreApplication.instance().desktop().screen().rect().center() - self.frameioMainViewController.rect().center())

    def setUserName(self, username):
        """Saves the Username to the uistate.ini"""
        self.email = username
        self.appSettings.setValue("FrameioUsername", self.email)

    @Slot(dict)
    def on_frameio_credentials_received(self, credentialsDict):
        print "GOT CREDS: " + str(credentialsDict)
        self.frameioSession.sessionHasValidCredentials = True
        self.frameioMainViewController.showUploadView()

    def attemptLogin(self, email = ''):
        """
        Triggered when Login button pressed. Attempts to Login to frame.io and store the session in global variable
        """
        print "Attempting login..."
        self.frameioMainViewController.statusLabel.setText(self.frameioMainViewController.eStatusLoggingIn)

        if not email:
            logging.error("No email address was specified. Please try again with an email.")
            return

        # inialise a new Frame.io Session, based on email address
        self.frameioSession = frameio.Session(email)

        # A Frame.io Session is constructed via an email address.
        # The loginHandler object of the Session handles the login process.
        print 'Email: ', email

        # Initially check the type of email and determine if it's a Google Email...
        self.frameioSession.email_type = check_email_type(email)

        if self.frameioSession.email_type == AUTH_MODE_EMAIL:
            self.frameioSession.loginHandler = BasicLoginHandler(email)

        elif self.frameioSession.email_type == AUTH_MODE_OAUTH:
            self.frameioSession.loginHandler = OAuthLoginHandler(email)
            self.frameioSession.loginHandler.loggedInSignal.connect(self.on_frameio_credentials_received)
        else:
            logging.error("Unable to determine email type")
            return

        logging.info('self.email_type: ', self.frameioSession.email_type)

        self.frameioSession.loginHandler.login()

        # We failed to get a response
        # if None in response:
        #     self.frameioMainViewController.setStatus(str(response[1][0]))
        #     return

        # events.sendEvent("kFrameioConnectionChanged", None)

        # if self.frameioSession.sessionHasValidCredentials:
        #     self.setUserName(username)
        #     self.frameioMainViewController.showUploadView()

        # return True

    def getLatestFileReferenceIDForProjectItem(self, item):
        """
        Looks for any Frame.io tags on item and returns the latest file reference
        """
        # Get Tags which contain a frameio_filereferenceid key

        filereferenceid = None
        itemTags = item.tags()
        frameIOTags = [tag for tag in itemTags if tag.metadata().hasKey("tag.description") and tag.metadata().value("tag.description") == "FrameIO Upload"]

        if len(frameIOTags)==0:
            return filereferenceid

        if len(frameIOTags)>1:
            # With multiple exports, it's possible that an item has multiple Frame.io Tags, get the one with the latest upload time
            sortedTags = sorted(frameIOTags, key=lambda k: float(k.metadata().value("tag.frameio_upload_time")), reverse=True)
            latestTag = sortedTags[0]
        else:
            latestTag = frameIOTags[0]

        if not latestTag.metadata().hasKey("tag.frameio_filereferenceid"):
            return filereferenceid

        filereferenceid = latestTag.metadata().value("tag.frameio_filereferenceid")        
        return filereferenceid

    def openFilereferenceIdInFrameIO(self, filereferenceid):
        """
        Looks to the Tag on the selected item and opens the browser to show the item
        """
        url = "https://app.frame.io/?f=" + filereferenceid
        webbrowser.open_new_tab(url)

    def createAnnotationsSubTrackItemForFileReference(self, filereferenceid):
        """
        Returns an Annotations Sub-TrackItem for a given trackItem
        """
        url = "https://app.frame.io/?f=" + filereferenceid
        webbrowser.open_new_tab(url)                

    def disconnectCurrentSession(self):
        """
        Disconnects the current session if authenticated]
        """
        if self.frameioSession.sessionHasValidCredentials:
            self.frameioSession.logout()
            events.sendEvent("kFrameioConnectionChanged", None)

    def handleConnectionStatusChangeEvent(self, event):
        """Called when a change in the session authentication occurs"""
        self.frameioMainViewController.updateConnectionIndicator()
        if not self.frameioSession.sessionHasValidCredentials:
            self.frameioMainViewController.showLoginView()
   

    def uploadFile(self, filePath, project, fileReferenceID = None):
        """Starts upload task for a given filePath. Returns a frame.io file reference"""

        uploads = {}
        if not os.path.isfile(filePath):
            return

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

        hiero.core.uploadThreads = []
        if len(uploads.keys()) != 0:
            nukeFrameioFileReferenceTask = NukeFrameioFileReferenceTask(uploads, self.frameioSession)
            print "Preparing uploads Thread about to start"
            threading.Thread( None, nukeFrameioFileReferenceTask.prepareUploads ).start()

        return fileReferenceID