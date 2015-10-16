# -*- coding: utf-8 -*-


"""
Interaction with frame.io from within Nuke.

Usage:

Bind nuke2frameio.uploadSelected() and nuke2frameio.loadSelectedcomments() to buttons in the menu.py.


written by Til Strobl
website: www.movingmedia.de

Changelog:
150904
- New feature: text and annotation visiblity toggles, font slider
- Bugfix: error handling
- Bugfix: linear annotation color
150901
- New feature: annotations are loaded as nuke rotopaint nodes (pen only)

"""

import os, logging, threading
import nuke
from frameio_exporter.core import frameio

frameiosession = None

def login(username = '', project = ''):
    """Login to frame.io and store the session in global variable"""
    global frameiosession
    if frameiosession != None:
        if project:
            frameiosession.setProject(project)
        return frameiosession
    p = nuke.Panel('frame.io Login')
    p.addSingleLineInput('Username', username)
    p.addPasswordInput('Password', '')
    result = p.show()
    if result:
        user = p.value('Username')
        pw = p.value('Password')
        frameiosession = frameio.Session(user,pw)
        if frameiosession.getEligibility() == 'user-non-google':
            if project:
                frameiosession.setProject(project)
                return frameiosession
            else:
                projects = ' '.join( frameiosession.projectdict().values() )
                p.addEnumerationPulldown('Project', projects )
                result = p.show()
                if result:
                    frameiosession.setProject(p.value('Project'))
                    return frameiosession
        elif frameiosession.getEligibility() == 'user-google':
            nuke.message('Google accounts are currently not supported.')
        elif frameiosession.getEligibility() == 'user-eligible':
            nuke.message('Account not found.')
        else:
            nuke.message('Login failed.')
    return None
    
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
        if frameiosession == None:
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
        print "Nuke Uploader: uploads %s" % str(uploads)
        threading.Thread( None, filereferenceTask, args = (uploads , frameiosession ) ).start()
            
def filereferenceTask(uploads, frameiosession):
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
    return tuple((float(int(value[i:i + lv // 3], 16))/255)**2.2 for i in range(0, lv, lv // 3))
    
def annotationNode(draw_data , width, height, frame):
    if draw_data == None:
        return False
    import nuke.rotopaint as rp
    paintNode = nuke.createNode('RotoPaint')
    paintNode['useLifetime'].setValue(True)
    paintNode['lifetimeStart'].setValue( frame )
    paintNode['lifetimeEnd'].setValue( frame )
    paintNode['disable'].setExpression( '1-parent.showannotation' )
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
            continue
    
def loadSelectedcomments():
    """Loads the comments for a selected node from the server. Comments are generated as text nodes inside a group"""
    nodes = nuke.selectedNodes()
    nukeroot = nuke.root()
    previouscommand = "animCurve = nuke.thisNode()['comment'].animation( 0 ) \nframe = False\nfor i in xrange(len(animCurve.keys())):\n    if nuke.frame() > animCurve.keys()[i].x:\n        frame = animCurve.keys()[i].x     \nif frame:\n    nuke.frame(frame)"
    nextcommand = "animCurve = nuke.thisNode()['comment'].animation( 0 ) \nframe = False\nfor i in xrange(len(animCurve.keys())):\n    if nuke.frame() < animCurve.keys()[i].x:\n        frame = animCurve.keys()[i].x\n        break\nif frame:\n    nuke.frame(frame)"
    if not 'frameioproject' in nukeroot.knobs():
        return False
    if nukeroot['frameioproject'].value() == '0':
        project = ''
    else:
        project = nukeroot['frameioproject'].value()
    for node in nodes:
        if not 'file' in node.knobs():
            continue
        filepath = os.path.abspath(node['file'].value())
        if not os.path.isfile(filepath):
            continue
        frameiosession = login( nukeroot['frameiousername'].value() , project )
        if frameiosession == None:
            return False
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
        group.addKnob( nuke.Boolean_Knob('showtext' , 'Show text' , True ) )
        group.addKnob( nuke.Boolean_Knob('showannotation' , 'Show annotation' , True ) )
        group.addKnob( nuke.Double_Knob('global_font_scale' , 'Font scale' ) )
        group['global_font_scale'].setValue(.25)
        group['of'].clearFlag(nuke.STARTLINE)
        group['showtext'].setFlag(nuke.STARTLINE)
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
                    textnode['global_font_scale'].setExpression( 'parent.global_font_scale' )
                    textnode['enable_background'].setValue(True)
                    textnode['background_opacity'].setValue(0.9)
                    textnode['useLifetime'].setValue(True)
                    textnode['lifetimeStart'].setValue( frame )
                    textnode['lifetimeEnd'].setValue( frame )
                    textnode['disable'].setExpression( '1-parent.showtext' )
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