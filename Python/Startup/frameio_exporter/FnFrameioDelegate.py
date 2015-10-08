# -*- coding: utf-8 -*-


"""
Interaction with frame.io from within Nuke Studio

Usage:

nuke2frameio by Til Strobl, www.movingmedia.de
"""
import frameio
import FnFrameioUI
import hiero.core
from hiero.core import ApplicationSettings
import nuke
from PySide.QtCore import QCoreApplication
import os, logging
from FnFrameioTranscodeExporter import NukeFrameioFileReferenceTask

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

        self.frameioMainViewController = FnFrameioUI.FnFrameioDialog(delegate = self, username = self.username)

        # This tells the authentication indicator to update when the status changes
        hiero.core.events.registerInterest("kFrameioConnectionChanged", self.handleConnectionStatusChangeEvent)

    def showFrameioDialogWithSelection(self, selection):
        """Shows the dialog from the Bin View"""

        # We're not using the Export dialog, so use the normal flow
        self.frameioMainViewController.usingExportDialog = False
        self.frameioMainViewController.show(selection)

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

    def disconnectCurrentSession(self):
        """
        Disconnects the current session if authenticated]
        """
        if self.frameioSession.sessionAuthenticated:
            self.frameioSession.logout()

    def handleConnectionStatusChangeEvent(self, event):
        """Called when a change in the session authentication occurs"""
        self.frameioMainViewController.updateConnectionIndicator()
   

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

        if len(uploads.keys()) != 0:
            nukeFrameioFileReferenceTask = NukeFrameioFileReferenceTask(uploads, self.frameioSession)
            print "Preparing uploads Thread about to start"
            threading.Thread( None, nukeFrameioFileReferenceTask.prepareUploads ).start()

            return fileReferenceID