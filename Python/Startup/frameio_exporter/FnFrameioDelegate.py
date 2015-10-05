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
import os, logging, threading

class NukeFrameioFileReferenceTask(object):

    def __init__(self, uploads, frameiosession, foldername = "NukeStudioUploads"):
        self.uploads = uploads
        self.frameiosession = frameiosession
        self.foldername = foldername
        self.progress = 1
        self.totalprogress = 1

    def prepareUploads(self):
        """Nuke task for creating the upload object and inspecting all the files"""
        self.totalprogress = len(self.uploads)*2+1
        hiero.core.frameioDelegate.frameioMainViewController.setStatus("Preparing Uploads...")
        subfolders = self.frameiosession.getSubfolderdict(self.frameiosession.getRootfolderkey())

        if self.foldername in subfolders.values():
            for id in subfolders:
                if subfolders[id] == self.foldername:
                    folderid = id
                    break
        else:
            folderid = self.frameiosession.createSubfolders([self.foldername])[0]['id']

        self.frameioUploadContext = frameio.Upload( self.uploads.keys(), self.frameiosession, folderid )
        i = 1
        for filepath in self.uploads.keys():
            hiero.core.frameioDelegate.frameioMainViewController.setStatus( "Prepare Uploads: " + str(100/self.progress*i))
            hiero.core.frameioDelegate.frameioMainViewController.setStatus('Inspecting file: ' + filepath)
            self.frameioUploadContext.inspectfile(filepath)
            i+=1
        hiero.core.frameioDelegate.frameioMainViewController.setStatus( "prepareUploads progress:" + str(100/self.totalprogress*i) )

        hiero.core.frameioDelegate.frameioMainViewController.setStatus("Creating filereferences")
        self.frameioUploadContext.filereference()
        i+=1

        hiero.core.frameioDelegate.frameioMainViewController.setStatus("Creating file references Thread about to start")

        for filepath in self.uploads.keys():
            progress = 100/self.totalprogress*i
            self.setProgress( progress )
            hiero.core.frameioDelegate.frameioMainViewController.setStatus("NukeFrameioFileReferenceTask Completion: %.1f %%" % float(progress))
            hiero.core.frameioDelegate.frameioMainViewController.setStatus('Starting upload: ' + filepath)
            self.uploads[filepath]['folderid'] = folderid
            nukeUploadTask = NukeFrameioUploadTask(self.frameioUploadContext, filepath)
            threading.Thread( None, nukeUploadTask.uploadFile).start()
            i+=1

    def progress(self):
        """
        Returns the current upload progress for the upload task as a percentage (0-100)
        """
        return self.progress

    def setProgress(self, perc):
        """
        Sets the current upload progress for the upload task as a percentage (0-100)
        """
        self.progress = perc


class NukeFrameioUploadTask(object):
    """Nuke task for uploading the parts for a specific file"""

    def __init__(self, upload, filepath):
        self.upload = upload
        self.uploadProgress = 0
        self.filepath = filepath

    def uploadFile(self):

        #task = nuke.ProgressTask('Upload to frame.io' )
        #task.setMessage('Creating filereference')
        #task.setProgress(4)
        self.setProgress(4)
        parts=self.upload.getPartcount(self.filepath)
        for i in xrange(parts):
            #task.setMessage('Uploading ' + os.path.basename(self.filepath) +  ' (part ' + str(i+1) + '/' + str(parts) + ')')
            print 'Uploading ' + os.path.basename(self.filepath) +  ' (part ' + str(i+1) + '/' + str(parts) + ')'
            self.upload.uploadpart(self.filepath,i)
            progress = 4 + 92/parts*(i+1)
            self.setProgress(float(progress))
            self.setProgress(progress)

        self.upload.mergeparts(self.filepath)
        self.setProgress(98)
        self.upload.workerthread(self.filepath)
        hiero.core.frameioDelegate.frameioMainViewController.setStatus("Upload Completed!")

    def progress(self):
        """
        Returns the current upload progress for the upload task as a percentage (0-100)
        """
        return self.uploadProgress

    def setProgress(self, perc):
        """
        Sets the current upload progress for the upload task as a percentage (0-100)
        """
        msg = "Current upload perc is %f %%" % perc
        hiero.core.frameioDelegate.frameioMainViewController.setStatus(msg)
        self.uploadProgress = perc

    def cancelUpload(self):
        """
        Cancels the current upload Task
        """
        print "Cancelling Upload task for %s" % self.filepath
        self.upload.cancel(self.filepath)
        print "Upload task for %s was cancelled" % self.filepath

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

    def showFrameioDialogWithSelection(self, selection):
        """Saves the Username to the uistate.ini"""
        print "showUploadViewController : %s" % str(selection)
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

        self.frameioMainViewController.statusLabel.setText(self.frameioMainViewController.eStatusLoggingIn)

        self.frameioSession = frameio.Session(username, password)
        result = self.frameioSession.login(username, password)

        if self.frameioSession.sessionAuthenticated:
            print "sessionAuthenticated..."
            self.setUserName(username)
            self.frameioMainViewController.showUploadView()

        return True

    def uploadFile(self, filePath, project, fileReferenceID = None):
        """Starts upload task for a given filePath"""

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

        if len(uploads.keys()) != 0:
            nukeFrameioFileReferenceTask = NukeFrameioFileReferenceTask(uploads, self.frameioSession)
            print "Preparing uploads Thread about to start"
            threading.Thread( None, nukeFrameioFileReferenceTask.prepareUploads ).start()
            #threading.Thread( None, NukeFrameioFileReferenceTasker, args = (uploads, self.frameioSession ) ).start()