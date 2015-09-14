# -*- coding: utf-8 -*-


"""
Interaction with frame.io from within Nuke Studio

Usage:

Bind nuke2frameio.uploadSelected() and nuke2frameio.loadSelectedcomments() to buttons in the menu.py.


written by Til Strobl
website: www.movingmedia.de

Changelog:
150901
- New feature: annotations are loaded as nuke rotopaint nodes (pen only)

"""
from hiero.core import ApplicationSettings
import os, logging, threading
import nuke
import FnFrameioUI
import frameio
from PySide.QtCore import QCoreApplication

def NukeFrameioFileReferenceTask(uploads, frameiosession, foldername = "NukeStudioUploads"):
    """Nuke task for creating the upload object and inspecting all the files"""
    totalprogress = len(uploads)*2+1
    task = nuke.ProgressTask('Preparing uploads' )
    task.setMessage('Upload to frame.io')

    subfolders = frameiosession.getSubfolderdict(frameiosession.getRootfolderkey())
    if foldername in subfolders.values():
        for id in subfolders:
            if subfolders[id] == foldername:
                folderid = id
                break
    else:
        folderid = frameiosession.createSubfolders([foldername])[0]['id']

    upload = frameio.Upload( uploads.keys(), frameiosession, folderid )
    i = 1
    for filepath in uploads.keys():
        task.setProgress( 100/totalprogress*i )
        task.setMessage('Inspecting file: ' + filepath)
        upload.inspectfile(filepath)
        i+=1
    task.setProgress( 100/totalprogress*i )
    task.setMessage('Creating filereferences')
    upload.filereference()
    i+=1

    for filepath in uploads.keys():
        progress = 100/totalprogress*i
        task.setProgress( progress )
        print "NukeFrameioFileReferenceTask Completion: %.1f %%" % float(progress)
        task.setMessage('Starting upload: ' + filepath)
        uploads[filepath]['folderid'] = folderid
        threading.Thread( None, NukeFrameioUploadTask, args = (upload,filepath,uploads[filepath]) ).start()
        i+=1
        
def NukeFrameioUploadTask(upload, filepath, node):
    """Nuke task for uploading the parts for a specific file"""
    task = nuke.ProgressTask('Upload to frame.io' )
    task.setMessage('Creating filereference')
    task.setProgress(4)
    parts=upload.getPartcount(filepath)
    for i in xrange(parts):
        task.setMessage('Uploading ' + os.path.basename(filepath) +  ' (part ' + str(i+1) + '/' + str(parts) + ')')
        print 'Uploading ' + os.path.basename(filepath) +  ' (part ' + str(i+1) + '/' + str(parts) + ')'
        upload.uploadpart(filepath,i)
        progress = 4 + 92/parts*(i+1)
        print "NukeFrameioUploadTask Completion: %.1f %%" % float(progress)
        task.setProgress(progress)
        if task.isCancelled():
            print "NukeFrameioUploadTask Cancelled"
            upload.cancel(filepath)
            return

    upload.mergeparts(filepath)
    task.setProgress(98)
    upload.workerthread(filepath)

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

        self.frameioMainViewController = FnFrameioUI.FnFrameioWidget(delegate = self, username = self.username)

    def showFrameioWidgetWithSelection(self, selection):
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

        print "username is: " + self.frameioSession.getUsername()
        print "projectDict values: " + str(self.frameioSession.projectdict().values())
        
        print "frameio.getProjectName:" + str(self.frameioSession.getProjectname())

        # TO-DO: If a project item is passed with an existing fileReferenceID, check if the fileref exists
        if fileReferenceID:
            filereference = frameiosession.getFilereference(fileReferenceID)
            if filereference.exists():
                size1 = filereference.getSize()
                size2 = os.stat(filePath).st_size
                if size1 == size2:
                    return

        uploads[filePath] = {"annotations": '', "fileReferenceID": fileReferenceID}

        if len(uploads.keys()) != 0:
            threading.Thread( None, NukeFrameioFileReferenceTask, args = (uploads, self.frameioSession) ).start()

    def uploadFiles(self, files, project, fileReferenceID = None):
        """Starts upload task for a list of files"""

        uploads = {}
        for filePath in files:
            if not os.path.isfile(filePath):
                return

            if self.frameioSession.sessionAuthenticated:
                print "Setting project to be: " + str(project)
                self.frameioSession.setProject(project)

            print "username is: " + self.frameioSession.getUsername()
            print "projectDict values: " + str(self.frameioSession.projectdict().values())
            
            print "frameio.getProjectName:" + str(self.frameioSession.getProjectname())

            # TO-DO: If a project item is passed with an existing fileReferenceID, check if the fileref exists
            if fileReferenceID:
                filereference = frameiosession.getFilereference(fileReferenceID)
                if filereference.exists():
                    size1 = filereference.getSize()
                    size2 = os.stat(filePath).st_size
                    if size1 == size2:
                        break

            uploads[filePath] = {"annotations": '', "fileReferenceID": fileReferenceID}

        if len(uploads.keys()) != 0:
            threading.Thread( None, NukeFrameioFileReferenceTask, args = (uploads, self.frameioSession) ).start()