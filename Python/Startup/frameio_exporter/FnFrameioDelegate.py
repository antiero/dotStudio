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

class FrameioDelegate(object):
    """Delegate for handling the Frame.io session and communicating with UI"""
    def __init__(self, *args, **kwargs):

        self.frameiosession = None 
        self.appSettings = ApplicationSettings()

        self.username = kwargs.get("username", None)

        # See if username exists already in uistate.ini
        if not self.username:
            savedUserPreference = self.appSettings.value("FrameioUsername")
            if savedUserPreference:
                self.username = savedUserPreference

        self.frameioMainViewController = FnFrameioUI.FrameioUploadWindow(delegate = self, username = self.username)

    def showUploadViewController(self):
        """Saves the Username to the uistate.ini"""
        self.frameioMainViewController.show()

    def setUserName(self, username):
        """Saves the Username to the uistate.ini"""
        self.username = username
        self.appSettings.setValue("FrameioUsername", self.username)

    def attemptLogin(self, username = '', password = ""):
        """Triggered when Login button pressed. Attempts to Login to frame.io and store the session in global variable"""

        self.frameiosession = frameio.Session(username, password)
        """if project:
            self.frameiosession.setProject(project)
            return False
        """
        result = self.frameiosession.login(username, password)

        if self.frameiosession.sessionAuthenticated:
            print "sessionAuthenticated..."
            print str(self.frameiosession.projectdict().values())
            projects = self.frameiosession.projectdict().values()
            self.frameioMainViewController._updateProjectsList(projects)
            self.frameioMainViewController.showUploadView()

        return True
    
def addFrameioroottab():
    """Adds frame.io settings tab to the nukescript"""
    nukeroot = nuke.root()
    if not 'frameio' in nukeroot.knobs():
        nukeroot.addKnob( nuke.Tab_Knob('frameio' , 'frame.io') )
        nukeroot.addKnob( nuke.String_Knob('frameiousername' , 'Username') )
        nukeroot.addKnob( nuke.Enumeration_Knob('frameioproject' , 'Project' , [] ) )
        
def addFrameionodetab(node):
    """Adds frame.io settings tab to the node"""
    if not 'frameio' in node.knobs():
        node.addKnob( nuke.Tab_Knob('frameio' , 'frame.io') )
        node.addKnob( nuke.Link_Knob('frameiousername' , 'Username') )
        node.addKnob( nuke.Link_Knob('frameioproject' , 'Project' , ) )
        node['frameiousername'].setLink('root.frameiousername')
        node['frameioproject'].setLink('root.frameioproject')
        openbrowser = 'import webbrowser\nurl = "https://app.frame.io/?f=" + nuke.thisNode()["filereferenceid"].value()\nwebbrowser.open_new_tab(url)'
        node.addKnob(nuke.PyScript_Knob( 'openbrowser', 'Open upload in browser',openbrowser ))
        node.addKnob( nuke.Text_Knob('line1' , '') )
        node.addKnob( nuke.String_Knob('filereferenceid' , 'filereferenceid') )
        node.addKnob( nuke.String_Knob('folderid' , 'folderid') )
        node.addKnob( nuke.String_Knob('projectid' , 'projectid') )
        node['openbrowser'].setFlag(nuke.STARTLINE)
        node['filereferenceid'].setEnabled(False)
        node['folderid'].setEnabled(False)
        node['projectid'].setEnabled(False)
    
def uploadSelected():
    """Starts upload tasks for all the selected node with file knobs"""
    nodes = nuke.selectedNodes()
    nukeroot = nuke.root()
    uploads = {}
    for node in nodes:
        if not 'file' in node.knobs():
            continue
        filepath = os.path.abspath(node['file'].value())
        if not os.path.isfile(filepath):
            continue
        addFrameioroottab()
        addFrameionodetab(node)
        if nukeroot['frameioproject'].value() == '0':
            project = ''
        else:
            project = nukeroot['frameioproject'].value()
        frameiosession = login( nukeroot['frameiousername'].value() , project )
        if not frameiosession:
            return False
        nukeroot['frameiousername'].setValue(frameiosession.getUsername())
        nukeroot['frameioproject'].setValues(frameiosession.projectdict().values())
        nukeroot['frameioproject'].setValue(str(frameiosession.getProjectname()))
        if node['filereferenceid'].value() != '':
            filereferenceid = node['filereferenceid'].value()
            filereference = frameiosession.getFilereference(filereferenceid)
            if filereference.exists():
                size1 = filereference.getSize()
                size2 = os.stat(filepath).st_size
                if size1 == size2:
                    return
        uploads[filepath] = node
    if len(uploads.keys()) != 0:
        threading.Thread( None, filereferenceTask, args = (uploads , frameiosession ) ).start()
            
def filereferenceTask(uploads , frameiosession):
    """Nuke task for creating the upload object and inspecting all the files"""
    totalprogress = len(uploads)*2+1
    task = nuke.ProgressTask('Preparing uploads' )
    task.setMessage('Upload to frame.io')
    foldername = 'Nukeuploads'
    subfolders = frameiosession.getSubfolderdict(frameiosession.getRootfolderkey())
    if foldername in subfolders.values():
        for id in subfolders:
            if subfolders[id] == foldername:
                folderid = id
                break
    else:
        folderid = frameiosession.createSubfolders([foldername])[0]['id']
    upload = frameio.Upload( uploads.keys() , frameiosession , folderid )
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
        task.setProgress( 100/totalprogress*i )
        task.setMessage('Starting upload: ' + filepath)
        uploads[filepath]['folderid'].setValue(folderid)
        threading.Thread( None, uploadTask, args = (upload,filepath,uploads[filepath]) ).start()
        i+=1
        
def uploadTask(upload,filepath,node):
    """Nuke task for uploading the parts for a specific file"""
    task = nuke.ProgressTask('Upload to frame.io' )
    task.setMessage('Creating filereference')
    node['projectid'].setValue(frameiosession.getProjectid())
    node['filereferenceid'].setValue(upload.getFilereferenceid(filepath))
    task.setProgress(4)
    parts=upload.getPartcount(filepath)
    for i in xrange(parts):
        task.setMessage('Uploading ' + os.path.basename(filepath) +  ' (part ' + str(i+1) + '/' + str(parts) + ')')
        upload.uploadpart(filepath,i)
        task.setProgress(4 + 92/parts*(i+1))
        if task.isCancelled():
            node['filereferenceid'].setValue('')
            upload.cancel(filepath)
            return
    upload.mergeparts(filepath)
    task.setProgress(98)
    upload.workerthread(filepath)
    
def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(float(int(value[i:i + lv // 3], 16))/255 for i in range(0, lv, lv // 3))
    
def annotationNode(draw_data , width, height, frame):
    if draw_data == None:
        return False
    import nuke.rotopaint as rp
    paintNode = nuke.createNode('RotoPaint')
    paintNode['useLifetime'].setValue(True)
    paintNode['lifetimeStart'].setValue( frame )
    paintNode['lifetimeEnd'].setValue( frame )
    paintNode.hideControlPanel() 
    i=0
    for draw in draw_data:
        if draw['tool'] == 'pen':
            curvesKnob = paintNode['curves']
            stroke = rp.Stroke(curvesKnob)
            for pointindex in xrange(len(draw['xs'])):
                stroke.append(rp.AnimControlPoint(width*float( draw['xs'][pointindex] ) , height-height*float( draw['ys'][pointindex] )))
            stroke.name = 'frameio' + str(i)
            curvesKnob.rootLayer.append(stroke)
            color = hex_to_rgb( draw['color'] )
            stroke.getAttributes().set('r' , color[0])
            stroke.getAttributes().set('g' , color[1])
            stroke.getAttributes().set('b' , color[2])
            stroke.getAttributes().set('bs' , draw['size'] *2 )
            i+=1
        else:
            return False
    
def loadSelectedcomments():
    """Loads the comments for a selected node from the server. Comments are generated as text nodes inside a group"""
    nodes = nuke.selectedNodes()
    nukeroot = nuke.root()
    previouscommand = "animCurve = nuke.thisNode()['comment'].animation( 0 ) \nframe = False\nfor i in xrange(len(animCurve.keys())):\n    if nuke.frame() > animCurve.keys()[i].x:\n        frame = animCurve.keys()[i].x     \nif frame:\n    nuke.frame(frame)"
    nextcommand = "animCurve = nuke.thisNode()['comment'].animation( 0 ) \nframe = False\nfor i in xrange(len(animCurve.keys())):\n    if nuke.frame() < animCurve.keys()[i].x:\n        frame = animCurve.keys()[i].x\n        break\nif frame:\n    nuke.frame(frame)"
    for node in nodes:
        if not 'file' in node.knobs():
            continue
        filepath = os.path.abspath(node['file'].value())
        if not os.path.isfile(filepath):
            continue
        if nukeroot['frameioproject'].value() == '0':
            project = ''
        else:
            project = nukeroot['frameioproject'].value()
        frameiosession = login( nukeroot['frameiousername'].value() , project )
        projectid = node['projectid'].value()
        filereferenceid = node['filereferenceid'].value()
        frameiosession.setProjectid(projectid)
        filereference = frameiosession.getFilereference(filereferenceid)
        commentdict = filereference.getComments()
        if not commentdict:
            return False
        
        group = nuke.createNode('Group')
        
        group.addKnob( nuke.Tab_Knob('frameio' , 'frame.io') )
        group.addKnob( nuke.Int_Knob('comment' , 'Comment') )
        group.addKnob( nuke.Int_Knob('of' , 'of') )
        group.addKnob( nuke.PyScript_Knob('previous' , 'previous' , previouscommand ) )
        group.addKnob( nuke.PyScript_Knob('next' , 'next' , nextcommand ) )
        group['of'].clearFlag(nuke.STARTLINE)
        group['comment'].setAnimated()
        i = 1
        while nuke.toNode('Comments' + str(i)) != None:
            i+=1
        group['name'].setValue('Comments' + str(i))
        group['label'].setValue(os.path.basename(filepath))
        with group:
            input = nuke.createNode('Input')
            input.hideControlPanel() 
            i = 0
            for timestamps in sorted(commentdict.keys()):
                for comment in commentdict[timestamps]:
                    if node.Class() == 'Read':
                        if node['frame'].value() == '':
                            offset = 0
                        else:
                            offset = int(node['frame'].value())
                    else:
                        offset = int(nuke.root()['first_frame'].value())
                    frame = round(timestamps) + offset
                    user = comment[0]
                    text = comment[1]
                    draw_data = comment[2]
                    group['comment'].setValueAt( i+1, frame )
                    textnode = nuke.createNode('Text2')
                    textnode['box'].setValue([10,10,node.width()/2,node.height()] )
                    textnode['yjustify'].setValue('bottom')
                    textnode['global_font_scale'].setValue(.75)
                    textnode['enable_background'].setValue(True)
                    textnode['background_opacity'].setValue(0.9)
                    textnode['useLifetime'].setValue(True)
                    textnode['lifetimeStart'].setValue( frame )
                    textnode['lifetimeEnd'].setValue( frame )
                    annotationNode(draw_data , node.width(), node.height(), frame)
                    message = user
                    message += '\n\n'
                    message += text
                    textnode['message'].setValue(message.encode('utf-8'))
                    textnode.hideControlPanel() 
                    i+=1
            group['of'].setValue(i)
            output = nuke.createNode('Output')
            output.hideControlPanel() 
        group.setInput(0, node)
        nuke.autoplace(group)
        
        
def doLogging(logfile, loglevel = 50):
    logging.basicConfig(level=loglevel,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        filename=logfile,
                        filemode='a')
    logging.info("Logging requested, loglevel=%d",loglevel)