# Python equivalents of the Photoshop to FLIX functions
import os
import platform
import time
import random
import socket
import hashlib
import re
from hiero.ui import currentViewer
import nuke

def getActiveDocumentFilename():
    name = '';
    try:
        name = currentViewer().player().sequence().name()
        name = name.split('\\').join('/');
        name = re.escape(name)
    except:
    	name = "ns_viewer" + "_%i" % int(time.time())

    return name

def getUniqueString( *args ):
    """
    Generates a universally unique ID.
    Any arguments only create more randomness.
    """
    t = long( time.time() * 1000 )
    r = long( random.random()*100000000000000000L )
    try:
        a = socket.gethostbyname( socket.gethostname() )
    except:
        # if we can't get a network address, just imagine one
        a = random.random()*100000000000000000L
    data = str(t)+' '+str(r)+' '+str(a)+' '+str(args)
    data = hashlib.md5(data).hexdigest()

    return data

def getFlixTempFolder():
    system = platform.system()
    paths = []
    user = os.getenv('USER')
    if system.lower() == "darwin":
    	paths.append('/flixtmp/flix/')

        if user:
          paths.append('/Users/Shared/flix_'+user+'/')
          paths.append('/Users/Shared/flix/')

    elif system.lower().startswith() == "win":
        user = os.getenv('USERNAME');
        if user:
            paths.append('c:\\temp\\flix_'+user+'\\')
    	    paths.append('c:\\flixtmp\\')
    	    paths.append('c:\\temp\\flix\\')

    for path in paths:
        if os.path.isdir(path):
            return path;            
    print 'Could not find any temp path'
    return ''

def sendFileToFlix(filePath, TCP_IP="127.0.0.1", TCP_PORT=35980 ):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    #s.send(MESSAGE)
    #data = s.recv(BUFFER_SIZE)
    #s.close() 

    s.send("GET /core/importDrawing?path="+filePath+"&deleteSource=1 HTTP/1.0\r\n\r\n")
    result = s.recv(1024) #s.recv(9999999);
    s.close()
    print "Got result: " + str(result)

def newFlixPanelFromCurrentViewerImage(nukeStudioViewer = True):
    print "Adding a new FLIX panel from current Viewer"
    uniquePath = getFlixTempFolder()+"flix_"+getUniqueString()+"_"

    lastTempNumber = "1"
    filePath = uniquePath+lastTempNumber+".xml";
    fileRef_out = open(filePath, 'w');
    dialogue = "I do not believe in fairies" #getDialogue(psdDocument);
    fileRef_out.write("<flixImport waitForSource='1' multipleSetups='1'>\n");

    # Depending on the action, we can grab the active Nuke (comp) or NukeStudio Viewer image
    if nukeStudioViewer:
        currentImage = currentViewer().image()
        tempFilePath = uniquePath+lastTempNumber+"_.FLIXTEMP.png"
        currentImage.save(tempFilePath)
    else:
        # It's the Nuke Comp image
        vn = nuke.activeViewer().node()
        frame = vn['frame'].value()
        tempFilePath = uniquePath+lastTempNumber+"_.FLIXTEMP.png"
        vn['file'].setValue(tempFilePath)
        nuke.execute(vn, frame, frame)

    fileRef_out.write("<image originalFile='"+getActiveDocumentFilename()+"' dialogue='I do not believe in Fairies' imageFile='"+tempFilePath+"'/>\n");
    fileRef_out.write("</flixImport>\n");
    fileRef_out.close()
    sendFileToFlix(filePath)

def replaceFlixPanelFromCurrentViewerImage(nukeStudioViewer = True):
    print "Replacing current FLIX panel from current Viewer image"

    uniquePath = getFlixTempFolder()+"flix_"+getUniqueString()+"_"
    lastTempNumber = "1"
    filePath = uniquePath+lastTempNumber+".xml";
    fileRef_out = open(filePath, 'w');
    dialogue = "I do not believe in fairies" #getDialogue(psdDocument);
    fileRef_out.write("<flixImport waitForSource='1' multipleSetups='1' replaceSelection='1'>\n");

    currentImage = currentViewer().image()
    tempFilePath = uniquePath+lastTempNumber+"_.FLIXTEMP.png"
    currentImage.save(tempFilePath)

    fileRef_out.write("<image originalFile='"+getActiveDocumentFilename()+"' dialogue='[FLIX_CURRENT_DIALOGUE]' imageFile='"+tempFilePath+"'/>\n");
    fileRef_out.write("</flixImport>\n");
    fileRef_out.close()
    sendFileToFlix(filePath)