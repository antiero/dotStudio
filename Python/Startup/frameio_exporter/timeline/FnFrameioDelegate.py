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
from PySide.QtCore import QCoreApplication
import os, logging
import webbrowser
from frameio_exporter.exporters.FnFrameioTranscodeExporter import NukeFrameioFileReferenceTask



class FrameioDelegate(object):
    """Delegate for handling the Frame.io session and communicating with UI"""
    def __init__(self, *args, **kwargs):

        self.frameioSession = frameio.Session("", "") 
        self.appSettings = ApplicationSettings()

        self.username = kwargs.get("username", None)
        self.project = None # Populate with the last 

        # See if username exists already in uistate.ini
        if not self.username:
            savedUserPreference = self.appSettings.value("FrameioUsername")
            if savedUserPreference:
                self.username = savedUserPreference

        self.frameioMainViewController = FnFrameioUI.FnFrameioDialog(username = self.username)

        # This tells the authentication indicator to update when the status changes
        hiero.core.events.registerInterest("kFrameioConnectionChanged", self.handleConnectionStatusChangeEvent)

    def showFrameioDialogWithSelection(self, selection):
        """Shows the dialog from the Bin View"""

        # We're not using the Export dialog, so use the normal flow
        self.frameioMainViewController.usingExportDialog = False
        self.frameioMainViewController.show()

        if not self.frameioSession.sessionAuthenticated:
            self.frameioMainViewController.showLoginView()
        else:
            self.frameioMainViewController.showUploadView()

        self.frameioMainViewController.move(QCoreApplication.instance().desktop().screen().rect().center() - self.frameioMainViewController.rect().center())

    def setUserName(self, username):
        """Saves the Username to the uistate.ini"""
        self.username = username
        self.appSettings.setValue("FrameioUsername", self.username)

    def attemptLogin(self, username = '', password = ""):
        """Triggered when Login button pressed. Attempts to Login to frame.io and store the session in global variable"""
        print "Attempting login..."
        self.frameioMainViewController.statusLabel.setText(self.frameioMainViewController.eStatusLoggingIn)

        self.frameioSession = frameio.Session(username, password)
        result = self.frameioSession.login(username, password)

        if self.frameioSession.sessionAuthenticated:
            self.setUserName(username)
            self.frameioMainViewController.showUploadView()

        return True

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
        if self.frameioSession.sessionAuthenticated:
            self.frameioSession.logout()

    def handleConnectionStatusChangeEvent(self, event):
        """Called when a change in the session authentication occurs"""
        self.frameioMainViewController.updateConnectionIndicator()
        if not self.frameioSession.sessionAuthenticated:
            self.frameioMainViewController.showLoginView()
   

    def uploadFile(self, filePath, project, fileReferenceID = None):
        """Starts upload task for a given filePath. Returns a frame.io file reference"""

        uploads = {}
        if not os.path.isfile(filePath):
            return

        if self.frameioSession.sessionAuthenticated:
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