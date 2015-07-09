#------------------------------------------------------------------------------
# serverFlixFunctions.py -
#------------------------------------------------------------------------------
# Copyright (c) 2014 The Foundry Visionmongers Ltd.  All Rights Reserved.
#------------------------------------------------------------------------------

from flix import fileServices, plugins, toEditorial, versioning, web
from flix.core.beat import Beat
from flix.core.recipe import Recipe
from flix.core.sequence import Sequence
from flix.core.show import Show
from flix.utilities.clientCommands import ClientCommands
from flix.core2.mode import Mode as Mode
from flix.editorial import AvidWorkflow
from flix.toEditorial.fromMaya import FromMaya
from flix.toEditorial.fromNukeStudio import FromNukeStudio
from flix.plugins.photoshop import Photoshop
from flix.plugins.psdUtils import PsdUtils
from flix.rendering import FlixNuke
from flix.utilities.animateSetups import AnimateSetups
from flix.utilities.copySetup import CopySetup
from flix.utilities.drawingImporter import DrawingImporter
from flix.utilities.editUtils import EditUtils
from flix.utilities.log import log
from flix.utilities.osUtils import OSUtils
from flix.utilities.xmlUtils import XMLUtils
from flix.utilities.jsonUtils import JsonUtils
import flix.utilities.commonUtils as utils
from flix.versioning.flixVersioning import FlixVersioning
from flix.web.serverSession import ServerSession
import flix.versioning.dictionaryCache
import flix.plugins.pluginRegistry
from . import restricted, restrictedMethods

from flix.toEditorial.fromMov import FromMov

import flix.utilities.email

from xml.parsers.expat import ExpatError

import cherrypy
import datetime
import itertools
import json
import os
import copy
import shutil
import sys
import re
import time
import urllib
import urllib2
import urlparse
import xml.etree.ElementTree as ET
import math
import threading
import requests
import uuid

from flix.gui.fileBrowserTypes import *

try:
    import maya.cmds as cmds
    import maya.mel as mel
    import maya
    import rsSnappy
    MAYA_VERSION = cmds.about(version=True)
except:
    cmds = None
    MAYA_VERSION = ''

pwd = None
try:
    import pwd
except:
    pass

@restrictedMethods
class ServerFlixFunctions:
    EMPTY_ERROR = "empty"
    MARKER_BEAT = "marker"
    TEMP_EDITS_MAX = 9

    __mostRecentEdits = None
    _feedbackLock = None
    _lastPublishTime = time.time()


    def __init__(self):
        self.fileService = fileServices.FileService()
        self.fileServiceLocal = fileServices.fileLocal.FileLocal()
        self.repath = fileServices.Repath()
        self.serveFiles = web.ServeFiles().serveFiles
        self.plugins = plugins.pluginRegistry.PluginRegistry()
        self.session = ServerSession()
        self.dictionaryCache = flix.versioning.dictionaryCache.DictionaryCache()

    @cherrypy.expose
    def flixPath(self, path, **keys):
        path = "%s" % Mode().get(path, keys)
        self.fileService.copyToLocal(path)
        if self.fileServiceLocal.exists(path):
            return self.serveFiles(path, keys.get("flixErrorHandling", ""))
        elif keys.get("beat", None) == self.MARKER_BEAT:
            log('Marker has no path')
            return ""
        elif keys.get("flixErrorHandling", "") == self.EMPTY_ERROR:
            log('SFF: File does not exist %s' % path)
            return ""
        else:
            log("Error getting flix path %s" % path, isError=True)
            return ''

    @cherrypy.expose
    def getFlixPath(self, path, **keys):
        mode = Mode(keys.get('show', None), keys.get('sequence', None))
        path = "%s" % mode.get(path, keys)
        return path

    @cherrypy.expose
    def imageFullPath(self, index, urlPath, **keys):
        path = urlPath[urlPath.find("/flixPath?") + len("/flixPath?"):]
        val = urllib.unquote(path)
        splits = urlparse.urlsplit(val)

        if sys.version_info >= (2, 6):
            params = urlparse.parse_qs(splits[2])  # parse_qs does not exist in python 2.5
        else:
            import cgi  # for python 2.5
            params = cgi.parse_qs(splits[2])
        for key in params:
            params[key] = params[key][0]

        keyword = params['path']
        mode = Mode(params.get('show', None), params.get('sequence', None))
        fullPath = mode.get(keyword, params)
        return index + "\n" + fullPath

    @cherrypy.expose
    def getShows(self):
        """
        return the list of flix sequences under the show
        """
        shows = Show.showsToXMLList(Show.getShows())
        root = XMLUtils.getXMLElementForClass("Shows")
        for show in shows:
            root.append(show)
        return ET.tostring(root)

    @cherrypy.expose
    def getSequences(self, show):
        """
        return the list of flix sequences under the show
        """
        log('Getting list of sequences remotely')
        job             = flix.remote.remoteHttpCall.FlixJob('user', 'getSequences')
        proxyHttpCall   = flix.remote.remoteHttpCall.ProxyHttpCall()
        procs           = flix.remote.ProcConfig()
        maxAttempts     = 3
        request         = job.newRequest(procs.FILE, 'FlixCore.getSequences', show)
        request.timeout = 60
        try:
            result          = proxyHttpCall.makeRequest(request, job, False, maxAttempts)
        except utils.FlixException, e:
            raise utils.FlixExceptionReport(e)
        return result


    @cherrypy.expose
    def getEditData(self, show, sequence, branch, version):
        """
        Return an xml file with the breakdown of the edit for a given sequence
        """
        if (branch == Mode().get("[defaultBranch]")):
            editFilePath = "[editorialFLEFile]"
        else:
            editFilePath = "[editorialFLEBranchFile]"
        mode = Mode(show, sequence)
        xmlPath = mode.get(editFilePath, {"branch":branch, "version":version})
        return self.serveFiles(xmlPath)


    @cherrypy.expose
    def getEditDataVersions(self, show, sequence, branch=''):
        """
        Return a list with all the shot edit data versions
        """

        # create the show + sequence folder if they don't exist
        mode = flix.core2.mode.Mode(show, sequence)
        showFolder = mode.get('[showFolder]')
        if not self.fileServiceLocal.exists(showFolder):
            self.fileService.createFolder(showFolder)

        sequenceObj = Sequence(show, sequence)
        sequenceObj.prepSequence()

        configPath = mode['[sequenceOverridesFile]']
        log('Using config  %s' % self.repath.localize(configPath))
        self.fileService.copyToLocal(configPath, syncNewer=True)

        editXML = self.updateShotEditDataSummary(show, sequence, branch)
        editXMLString = ET.tostring(editXML)
        return editXMLString

    def updateShotEditDataSummary(self, show, sequence, branch=''):
        """
        Update the shot edit data summary of all the fle files
        :param show: The show name as string
        :param sequence: The sequence name as string
        :param branch: The branch name as string
        """

        log('Updating edit')

        saveNeeded = False
        sequenceObj = Sequence(show, sequence)
        if branch == '' or (branch == Mode().get("[defaultBranch]")):
            editFilesCachePath = "[editorialFLEFilesCache]"
        else:
            editFilesCachePath = "[editorialFLEBranchFilesCache]"

        editsCache = Mode(show, sequence).get(editFilesCachePath, {"branch":branch})
        self.fileService.copyToLocal(editsCache, syncNewer=True)
        editsXML = None

        lastEditParsed = 0
        self.fileService.copyToLocal(editsCache, syncNewer=True)
        if self.fileServiceLocal.exists(editsCache):
            try:
                editsXML = self.fileServiceLocal.loadXMLFile(editsCache)
                lastEditParsed = int(editsXML.attrib["lastEditParsed"])
                i = lastEditParsed + 1
            except Exception, e:
                log("error parsing Editorial file %s %s" % (e, editsCache), isError=True)
                editsXML = None

            if editsXML is None:
                try:
                    self.fileServiceLocal.removeFile(editsCache)
                except Exception, e:
                    log("error removing corrupt Editorial file %s %s" % (e, editsCache), isError=True)

        if editsXML is None:
            editsXML = XMLUtils.getXMLElementForClass("ShotEditDataVersions")
            saveNeeded = True
            i = 1

        maxEditVersions = FlixVersioning().getCurrentFlixEditVersion(show, sequence, branch)
        for i in range(i, maxEditVersions):
            editVersion = str(i)
            editorialPath = sequenceObj.getShotEditPath(branch, editVersion)

            if not self.fileService.exists(editorialPath):
                continue
            try:
                edit = self.fileService.loadXMLFile(editorialPath)
            except ExpatError, e:
                log("Skipping file. Could not parse it. File %s" % editorialPath, isError=True, email=True)
                i += 1
                continue

            editorialXML = ET.Element("ShotEditData")
            editorialXML.attrib["version"] = editVersion
            editorialXML.attrib["published"] = "false"
            editorialXML.attrib["note"] = "INCOMPLETE SAVE"

            timestamp = edit.attrib.get("utcTimestamp", None)
            if not timestamp:
                dateVal = self.fileService.getModificationTime(editorialPath)
                timestamp = int(round(dateVal))
            editorialXML.attrib["date"] = str(timestamp)
            editorialXML.attrib["utcTimestamp"] = str(timestamp)

            editorialXML.attrib["user"] = edit.attrib.get("user", "unknown")
            editorialXML.attrib["note"] = "%-30s" % edit.attrib.get("note", "")
            fromEditorial = "false"
            movPath = ""
            if 'editorial' in edit.attrib.get("createdBy", "").lower():
                fromEditorial = 'true'
                movPath = edit.attrib.get("movPath", "")
            editorialXML.attrib["fromEditorial"] = fromEditorial
            editorialXML.attrib["movPath"] = movPath

            editsXML.append(editorialXML)
            editsXML.attrib["lastEditParsed"] = str(i)
            i += 1

        if ((i > 1) and (i-1 > lastEditParsed)) or saveNeeded:
            # create a cached file
            self.fileService.saveXMLFile(editsCache, editsXML)

        return editsXML


    def __getTempEditVersionXML(self, show, sequence, branch, username, version):
        """
        Return an XML with the temp shot edit version info
        """
        # Get the tempFLE's folder
        tempFLEFolder = OSUtils.getLocalTempFolder()
        tempFLEFolder = tempFLEFolder[0:(len(tempFLEFolder) - 1)]

        # Get the tempFLE file for the version
        if (branch == Mode().get("[defaultBranch]")):
            editTempFilePath = "[editorialTempFLEFile]"
        else:
            editTempFilePath = "[editorialTempFLEBranchFile]"
        mode = Mode(show, sequence)
        tempFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":version})
        if not os.path.exists(tempFLEPath):
            return None

        dateVal = self.fileServiceLocal.getModificationTime(tempFLEPath)
        dateString = datetime.datetime.fromtimestamp(dateVal).strftime("%m/%d/%y %I:%M")

        editXML = ET.Element("ShotEditData")
        editXML.attrib["version"] = '%s' % version
        editXML.attrib["date"] = dateString
        editXML.attrib["user"] = username
        editXML.attrib["note"] = "Autosave"
        editXML.attrib["published"] = "false"

        return editXML



    @cherrypy.expose
    def getTempEditDataVersions(self, show, sequence, branch, username):
        """
        Return a list with all the temp shot edit data versions
        """
        # Get the tempFLE's folder
        tempFLEFolder = OSUtils.getLocalTempFolder()
        tempFLEFolder = tempFLEFolder[0:(len(tempFLEFolder) - 1)]

        # Get the tempFLE file's versions
        if (branch == Mode().get("[defaultBranch]")):
            editTempFilePath = "[editorialTempFLEFile]"
        else:
            editTempFilePath = "[editorialTempFLEBranchFile]"

        mode = Mode(show, sequence)
        matches = mode.getMatches(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":"*"})
        matches.sort(key=lambda match: int(match['version']))

        tempEditsXML = XMLUtils.getXMLElementForClass("TempShotEditDataVersions")
        if len(matches) > 0:
            for i in range(0, len(matches)):
                version = str(matches[i]['version'])
                tempEdit = self.__getTempEditVersionXML(show, sequence, branch, username, version)
                if tempEdit is not None:
                    tempEditsXML.append(tempEdit)

        output = ET.tostring(tempEditsXML)
        return output

    @cherrypy.expose
    def getTempEditData(self, show, sequence, branch, username, version):
        """
        Return an xml file with the breakdown of the temp edit for a given sequence
        """
        # Get the tempFLE's folder
        tempFLEFolder = OSUtils.getLocalTempFolder()
        tempFLEFolder = tempFLEFolder[0:(len(tempFLEFolder) - 1)]
        # Get the tempFLE file for the version
        if (branch == Mode().get("[defaultBranch]")):
            editTempFilePath = "[editorialTempFLEFile]"
        else:
            editTempFilePath = "[editorialTempFLEBranchFile]"
        mode = Mode(show, sequence)
        tempFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":version})
        return self.serveFiles(tempFLEPath)

    @cherrypy.expose
    def getBeats(self, show, sequence):
        """
        Return an xml file with the breakdown of all the beats
        """
        sequenceFolder = Mode(show, sequence).get('[sequenceFolder]')

        if self.fileServiceLocal.exists(sequenceFolder) == False and self.fileService.exists(sequenceFolder) == True :
            log('Initializing sequence %s' % sequence)
            sequenceObject = Sequence(show, sequence)
            sequenceObject.prepSequence()

        beats = Beat.beatsToXMLList(Beat.getBeats(show, sequence))
        beatNames = list()
        root = XMLUtils.getXMLElementForClass("Beats")
        for beat in beats:
            beatNames.append(beat.attrib.get("name"))
            root.append(beat)
        output = ET.tostring(root)
        return output

    @cherrypy.expose
    def getRecipies(self, show, sequence, beat, setup="*", version="*"):
        """
        Return an xml file with setups
        """

        mode = Mode(show, sequence)
        pathArgs = mode.getMatches(Recipe.COMP_FOLDER, {"beat":beat, "setup":setup, "version":version})

        while pathArgs:
            if not pathArgs:
                break
            foundPath = pathArgs.pop(0)
            xmlPath = mode.get(Recipe.XML_FILE, foundPath)
            if  self.fileService.exists(xmlPath):
                content = self.fileService.loadTextFile(xmlPath)
                self.addFeedback('loadSetupInLibrary', content)
        return

    @cherrypy.expose
    def getSetupsMXF(self, show, sequence):
        """
        Return an xml file with the list of setups' MXF files
        """
        setupsMXFXML = XMLUtils.getXMLElementForClass("EditorialMXFFiles")

        editMXFFolder = Mode(show, sequence).get("[editorialMXFFolder]")
        copiedMXFFolder = editMXFFolder + "/copied"

        if self.fileService.exists(copiedMXFFolder):
            # Version A using glob.glob()
            # Does not work when renaming a file's MXF extension in the OSX Finder
            # The Finder keeps the MXF extension even if it's not visible
#            pathname = copiedMXFFolder + "/" + sequence + "_*.mxf"
#            setupsMXF = setupsMXF = glob.glob(pathname)
#            if len(setupsMXF) > 0:
#                for i in range(0, len(setupsMXF)):
#                    mxfXML = ET.Element("MXFFile")
#                    mxfXML.attrib["name"] = setupsMXF[i].replace(copiedMXFFolder + "/", "")
#                    setupsMXFXML.append(mxfXML)

            # Version B using string.find()
            setupsMXF = self.fileService.listFolder(copiedMXFFolder)
            if len(setupsMXF) > 0:
                sub1 = sequence + "_"
                sub2 = ".mxf"
                for i in range(0, len(setupsMXF)):
                    if (setupsMXF[i].find(sub1) == 0) and (setupsMXF[i].find(sub2) == len(setupsMXF[i]) - 4):
                        mxfXML = ET.Element("MXFFile")
                        mxfXML.attrib["name"] = setupsMXF[i]
                        setupsMXFXML.append(mxfXML)

        output = ET.tostring(setupsMXFXML)
        return output

    @cherrypy.expose
    def saveShotEditData(self, show, sequence, branch, shotEditData):
        """
        Save the shot edit data as a new version, returns the resulting xml
        """
        shotEditPath = ''

        try:
            shotEditXML = ET.fromstring(shotEditData)
            if shotEditXML is not None:
                sequenceObj = Sequence(show, sequence)
                editorialPath = sequenceObj.getEditorialPath()

                version = FlixVersioning().flixEditVersionUp(show, sequence, branch)
                log('new version %s' % version)

                shotEditPath = sequenceObj.getShotEditPath(branch, version)

                self.fileServiceLocal.createFolder(editorialPath)

                shotEditXML.attrib["version"] = str(version)
                shotEditXML.attrib["createdBy"] = "Flix"
                audioChanged = shotEditXML.get("recordingChanged")
                if shotEditXML.get("recordingChanged") == 'true':
                    soundFilename = shotEditXML.get('sound')
                    if soundFilename is None or soundFilename.find('_imported_') > -1:
                        soundFilename = '%s_shotEdit_v%d.mp3'% (sequence, version)
                    reSound = re.match(r"^(.*_v)([0-9]*)(\.mp3)$", soundFilename)
                    soundFilename = reSound.group(1)+str(version)+reSound.group(3)
                    shotEditXML.set("sound", soundFilename)
                    cutlistPath = shotEditXML.get('cutlistPath')
                    if cutlistPath is None or cutlistPath == '':
                        cutlistPath = shotEditPath
                    reSound = re.match(r"^(.*_v)([0-9]*)(\.xml)$", cutlistPath)
                    cutlistPath = reSound.group(1)+str(version)+reSound.group(3)
                    shotEditXML.set('cutlistPath', cutlistPath)
                    shotEditXML.set('editorialRefVersion', str(version))

                self.fileService.saveXMLFile(shotEditPath, shotEditXML)
                log('saving to %s' % shotEditPath)
            output = ET.tostring(shotEditXML)
        except Exception, e:
            log('saveShotEditData:: Error Saving edit. %s %s %s' % (show, sequence, branch), isError=True, trace=True)
            self.feedErrorAlert('There was an error saving the edit\n%s' % e, 'Save Error')
            return

        try:
            self.updateShotEditDataSummary(show,sequence, branch)
        except Exception, e:
            log('saveShotEditData:: Error Updating Shot Edit %s' % shotEditPath, isError=True, trace=True)

        return output

    @cherrypy.expose
    def saveTempShotEditData(self, show, sequence, branch, username, shotEditData):
        """
        Save the shot edit data as a temp version
        """
        try:
            shotEditXML = ET.fromstring(shotEditData)
            if shotEditXML is not None:
                # Get the tempFLE's folder
                tempFLEFolder = OSUtils.getLocalTempFolder()
                tempFLEFolder = tempFLEFolder[:-1]

                # Get the tempFLE file's versions
                if (branch == Mode().get("[defaultBranch]", {})):
                    editTempFilePath = "[editorialTempFLEFile]"
                else:
                    editTempFilePath = "[editorialTempFLEBranchFile]"
                mode = Mode(show, sequence)
                matches = mode.getMatches(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":"*"})
                matches.sort(key=lambda match: int(match['version']))
                matches.reverse()


                version = 1
                # Get the new tempFLE file
                tempFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":'%s' % version})
                currentTime = time.mktime(datetime.datetime.now().timetuple())

                if self.fileServiceLocal.exists(tempFLEPath):
                    lastSaved = os.stat(tempFLEPath).st_mtime
                    lastSavedAge = (currentTime - lastSaved)
                    log('last saved %s' % lastSavedAge)

                    # If the most recent edit is less than 5 minutes then save a newer one.
                    if lastSavedAge < (5*60) and self.__mostRecentEdits is not None:
                        return self.__mostRecentEdits

                for i in range(len(matches)):
                    version = int(matches[i]['version'])
                    log('Temp Edit Renaming %s' % version)
                    dstFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":str(version + 1)})
                    srcFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":str(version)})

                    if self.fileServiceLocal.exists(srcFLEPath):
                        if version > self.TEMP_EDITS_MAX:
                            self.fileServiceLocal.removeFile(srcFLEPath)
                        else:
                            self.fileServiceLocal.rename(srcFLEPath, dstFLEPath)

                version = 1
                # Get the new tempFLE file
                tempFLEPath = mode.get(editTempFilePath, {"editorialTempFLEFolder": tempFLEFolder, "branch":branch, "username":username, "version":'%s' % version})

                # Save the tempFLE file
                shotEditXML.attrib["version"] = str(version)
                shotEditXML.attrib["createdBy"] = "Flix"

                self.fileServiceLocal.saveXMLFile(tempFLEPath, shotEditXML)

            output = self.getTempEditDataVersions(show, sequence, branch, username)
            self.__mostRecentEdits = output
        except Exception, e:
            self.feedErrorAlert('There was an error during Autosaved.\n%s'%e, 'Save Error')
        return output

    def __saveFile(self, path, content):
        """
        save a file
        """
        self.fileService.saveTextFile(path, content)

    @cherrypy.expose
    def saveSetupData(self, setupDataXMLS=None, multiTrackDataXMLS=None, renderPassesDataXMLS=None, setupAnimationOffsetXMLS=None, rigsAnimationOffsetXMLS=None, **properties):
        """
        take the data from the post and save it
        """
        self.__saveSetupData(setupDataXMLS, multiTrackDataXMLS, renderPassesDataXMLS, setupAnimationOffsetXMLS, rigsAnimationOffsetXMLS, properties)

        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        recipePath = mode.get("[recipeFile]", properties)
        # update the comp file
        FlixNuke().fromRecipe(recipePath)
        return "done"


    def __saveSetupData(self, setupDataXMLS=None, multiTrackDataXMLS=None, renderPassesDataXMLS=None, setupAnimationOffsetXMLS=None, rigsAnimationOffsetXMLS=None, properties={}):
        """
        Save the recipe data
        """
        log('saving setup data')
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        recipePath = mode.get("[recipeFile]", properties)
        multiTrackPath = mode.get("[recipeMultiTrackFile]", properties)
        renderPassPath = mode.get("[recipeRenderPassFile]", properties)
        setupAnimationOffsetPath = mode.get("[setupAnimOffsetFile]", properties)
        rigsAnimationOffsetPath = mode.get("[rigsAnimOffsetFile]", properties)

        if setupDataXMLS:
            log ("__saveSetupData:: saving setup xml")
            self.__saveFile(recipePath, setupDataXMLS)

        if multiTrackDataXMLS:
            log ("__saveSetupData:: saving multitrack xml")
            self.__saveFile(multiTrackPath, multiTrackDataXMLS)
            self.updateCacheInfoForSetup(properties)


        if renderPassesDataXMLS:
            self.__saveFile(renderPassPath, renderPassesDataXMLS)

        if setupAnimationOffsetXMLS:
            if setupAnimationOffsetXMLS == "empty":
                # remove the setup file
                if self.fileService.exists(setupAnimationOffsetPath):
                    self.fileService.removeFile(setupAnimationOffsetPath)
            else:
                self.__saveFile(setupAnimationOffsetPath, setupAnimationOffsetXMLS)

        if rigsAnimationOffsetXMLS != None:
            if rigsAnimationOffsetXMLS == "empty":
                # remove the rigs file
                if self.fileService.exists(rigsAnimationOffsetPath):
                    self.fileService.removeFile(rigsAnimationOffsetPath)
            else:
                self.__saveFile(rigsAnimationOffsetPath, rigsAnimationOffsetXMLS)

        log('done saving')
        return "done"

    def updateCacheInfoForSetup(self, setupProperties):
        mode = flix.core2.mode.Mode(setupProperties.get('show', None), setupProperties.get('sequence', None))

        setupProperties['name'] = 'panelMultiTrack'

        loadedPath       = mode.get('[dictionaryLocalFile]', setupProperties)
        changedPath      = mode.get('[dictionaryMasterFile]', setupProperties)
        setupLabel       = mode.get('[recipeLabel]', setupProperties)

        lastChangedTable = self.dictionaryCache.getMasterTableInMemory(changedPath)
        lastLoadedTable  = self.dictionaryCache.getLocalTableInMemory(loadedPath)

        currentTime = math.floor(time.time())

        lastChangedTable[setupLabel] = currentTime
        lastLoadedTable[setupLabel] = currentTime

        self.dictionaryCache.storeMasterValue(changedPath, setupLabel, currentTime)
        self.dictionaryCache.storeLocalValue(loadedPath, setupLabel, currentTime)
        return True

    @cherrypy.expose
    def compSetupData(self, setupDataXMLS=None, multiTrackDataXMLS=None, renderPassesDataXMLS=None, setupAnimationOffsetXMLS=None, rigsAnimationOffsetXMLS=None, multiFrameRange=None, recipe=None, **properties):
        """
        Take the xml data from the POST
        and resave the recipe file
        """
        # check to see if we are already locked
#        if multiTrackDataXMLS:
#            multiTrackXML = ET.fromstring(multiTrackDataXMLS)
#            if (multiTrackXML.attrib.get("locked", "0") == "1"):
#                return

        log('saving setup data')
        self.__saveSetupData(setupDataXMLS, multiTrackDataXMLS, renderPassesDataXMLS, setupAnimationOffsetXMLS, rigsAnimationOffsetXMLS, properties=properties)
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        if recipe == None:
            recipePath = mode.get("[recipeFile]", properties)
            recipe = Recipe.recipeFromFile(recipePath)
        else:
            properties = recipe.getProperties()
            recipePath = mode.get("[recipeFile]", properties)

        if properties['beat'] == 'ref':
            recipe = self.updateEditedRefImages(recipe)
            return
        else:
            multiTrackXML = self.__updateEditedImages(recipe)

            if multiTrackXML == None:
                return ''
        # Updating cache for recipe file if you leave this, caching fails to see the new nuke file.. now part of flixNuke
        self.fileServiceLocal.refreshCache(os.path.dirname(recipePath))
        FlixNuke().compRecipe(recipe, multiFrameRange, renderCallback=self.__renderCallback, updateScript=True)


        data = []
        data.append('<Recipies>')
        data.append('<Setup show="%(show)s" sequence="%(sequence)s" beat="%(beat)s" setup="%(setup)s" version="%(version)s">' % recipe.getProperties())
        data.append(ET.tostring(multiTrackXML) + "</Setup>" + "</Recipies>")
        dataString = "".join(data)

        self.feedReloadSetupsMultiTracks(dataString)

#        FlixNuke().compRecipe(recipe, multiFrameRange, fileOutNodes='fileOut_master_png')

        return "done"

    def __renderCallback(self, filesRendered=[]):
        """
        Callback from the rendering commands
        """
        # caching issues workaround
        for f in filesRendered:
            self.fileServiceLocal.refreshCache(f)
            log('__renderCallback:: Reloading image %s' %self.repath.localize(f))
        self.addFeedback("reloadImages", filesRendered)



    def __updateEditedImages(self, recipe):
        """
        Look for any images that were edited in photoshop and
        move them back to pose space.
        Also update the recipe path to reflect a new path
        for each edited pose.
        """

        recipeProperties = recipe.getProperties()
        mode = Mode(recipeProperties.get('show', None), recipeProperties.get('sequence', None))
        multiTrackPath = mode.get(Recipe.MULTITRACK_FILE, recipeProperties)

        try:
            multiTrackXML = self.fileService.loadXMLFile(multiTrackPath)
        except Exception, e:
            multiTrackXML = XMLUtils.loadAndCleanXML(multiTrackPath)

        setupName = recipeProperties["setup"]

        updatedPoses = list()

        # check to see if we have any new poses
        tempPath = mode.get(Recipe.POSE_EDITING_FOLDER, recipeProperties)

        multiTrackModified = False

        if self.fileServiceLocal.exists(tempPath):
            tempFiles = self.fileServiceLocal.listFolder(tempPath)
            log('Temp Files %s' % tempFiles)
            for f in tempFiles:
                if f.endswith(".psd"):
                    if f.startswith("."):
                        continue
                    try:
                        isPsdMultiLayerPath = f.replace(".psd", ".psd.multilayer")
                        keepPsd = False
                        if isPsdMultiLayerPath in tempFiles:
                            keepPsd = True

                        outPsdPath = tempPath + "/" + f

                        infoXMLPath = tempPath + "/" + f.replace(".psd", ".xml")
                        poseXML = self.fileService.loadXMLFile(infoXMLPath)

                        poseId = poseXML.attrib.get("id", -1)

                        poseXMLItems = self.__getMultiTrackElementWithId(multiTrackXML, poseId)
                        if poseXMLItems is None:
                            continue
                        if poseXMLItems.get("pose", None) is None:
                            continue

                        pose = poseXMLItems["pose"].attrib["file"]

                        userRigName = poseXMLItems["rig"].attrib["userRigName"]

                        posePropertiesXML = poseXML.find("Properties")

                        if posePropertiesXML is None:
                            posePropertiesXML = XMLUtils.getXMLElementForClass("Properties")
                            poseXML.append(posePropertiesXML)

                        poseProperties = posePropertiesXML.attrib

                        # determine the pose name for which to save the pose as
                        basename = poseProperties.get("pose", "")

                        if pose != "[poseFile]":
                            basename = os.path.basename(pose)
                            basename = basename.replace(".png", "")
                            if basename.rfind("_v") > 0:
                                pose = basename[0:basename.rfind("_v")]

                            if ("[" in basename) or ("]" in basename):
                                pose = "[defaultPose]"

                        # create a new pose if necessary
                        if (pose == "[clearPose]") or (pose == mode.get("[clearPose]", recipeProperties)) or (pose == "[defaultPose]") or (pose == mode.get("[defaultPose]", recipeProperties)):
                            basename = setupName + "_" + userRigName + "_" + poseXML.attrib.get("id", "")

                        # define the filename for the pose name
                        poseProperties["pose"] = basename
                        poseProperties["version"] = ">"

                        poseProperties["show"] = recipeProperties["show"]
                        poseProperties["sequence"] = recipeProperties["sequence"]
                        poseProperties["beat"] = recipeProperties["beat"]

                        # gets the latest incremental number for this pose
                        version = FlixVersioning().poseVersionUp(poseProperties["show"],
                                                                 poseProperties["sequence"],
                                                                 poseProperties["beat"],
                                                                 poseProperties["pose"])

                        if posePropertiesXML.attrib.get('poseFileExtension'):
                            del(posePropertiesXML.attrib["poseFileExtension"])

                        log('new pose version %s' % version)
                        poseProperties["version"] = str(version)

                        poseXML.attrib["file"] = "[poseFile]"
                        posePropertiesXML.attrib["version"] = poseProperties["version"]
                        posePropertiesXML.attrib["pose"] = poseProperties["pose"]

                        posePropertiesXML.attrib["show"] = recipeProperties["show"]
                        posePropertiesXML.attrib["sequence"] = recipeProperties["sequence"]
                        posePropertiesXML.attrib["beat"] = recipeProperties["beat"]

                        mode = Mode(posePropertiesXML.attrib.get("show", None), posePropertiesXML.attrib.get("sequence", None))
                        newPosePath = mode.get("[poseFile]", posePropertiesXML.attrib)

                        poseFolder = os.path.dirname(newPosePath)
                        self.fileService.createFolder(poseFolder)

                        self.fileServiceLocal.refreshCache(outPsdPath)
                        # copy the psd file if any
                        for i in range(10):
                            if keepPsd:
                                posePropertiesXML.attrib["poseFileExtension"] = '.psd'
                                newPosePath = mode.get("[poseFile]", posePropertiesXML.attrib)
                                if self.fileServiceLocal.exists(outPsdPath):
                                    self.fileServiceLocal.copy(outPsdPath, newPosePath)
                                    break
                            else:
                                # copy the poses to the pose paths.
                                posePropertiesXML.attrib["poseFileExtension"] = '.png'
                                newPosePath = mode.get("[poseFile]", posePropertiesXML.attrib)
                                outPngPath = self.__toPoseSpace(outPsdPath)
                                if self.fileServiceLocal.exists(outPngPath):
                                    self.fileServiceLocal.copy(outPngPath, newPosePath)
                                    break
                            time.sleep(0.5) # some issues with file locking on windows file servers

                        self.fileServiceLocal.removeFile(outPsdPath)
                        self.fileService.copyFromLocal(newPosePath, True)

                        updatedPoses.append({"poseXML":poseXML, "outPsdPath":outPsdPath})

                        # Update the xml to reflect the new pose
                        self.fileServiceLocal.saveXMLFile(infoXMLPath, poseXML)

                        multiTrackModified = True

                    except:
                        log("Error in updating poses", isError=True, trace=True)
                        return None


        # Update the path in the multiTrack
        if len(updatedPoses) > 0:
            for updatedPose in updatedPoses:
                poseXML = updatedPose["poseXML"]
                poseId = poseXML.attrib.get("id", -1)
                rigName = poseXML.attrib["rig"]
                billboardName = poseXML.attrib["billboard"]
                poseIndex = int(poseXML.attrib["index"])
                trackName = poseXML.attrib["track"]
                outPsdPath = updatedPose["outPsdPath"]
                foundPose = None
                # find the pose in the xml
                for rigType in multiTrackXML.getchildren():
                    for r in rigType.getchildren():
                        for rig in r.getchildren():
                            if rig.attrib["name"] != rigName:
                                continue
                            for billboard in rig.getchildren():
                                if billboard.attrib["billboard"] != billboardName:
                                    continue
                                for multiTrack in billboard.getchildren():
                                    for track in multiTrack.getchildren():
                                        if track.attrib["name"] == trackName:
                                            for cdl in track.getchildren():
                                                for clip in cdl.getchildren():
                                                    for  clipType in clip.getchildren():
                                                        for pose in clipType.getchildren():
                                                            if poseId == pose.attrib.get("id", None) or poseId == -1:
                                                                foundPose = pose

                if foundPose is not None:
                    if int(foundPose.attrib["index"]) == int(poseIndex):
                        foundPose.attrib["file"] = poseXML.attrib["file"]
                        foundPoseXML = foundPose.find("Properties")
                        if foundPoseXML is None:
                            foundPoseXML = XMLUtils.getXMLElementForClass("Properties")
                            foundPose.append(foundPoseXML)
                        foundPoseXML.attrib = poseXML.find("Properties").attrib.copy()
                        # delete the source pose
                        self.fileServiceLocal.removeFile(outPsdPath)
                        isPsdMultiLayerPath = outPsdPath.replace(".out.psd", ".out.psd.multilayer")
                        if self.fileServiceLocal.exists(isPsdMultiLayerPath):
                            self.fileServiceLocal.removeFile(isPsdMultiLayerPath)


            if multiTrackModified:
                if multiTrackXML is not None:
                    log("refreshing multitrack")
                    multiTrackXML.attrib['locked'] = '0'
                    recipeProperties['frame'] = recipeProperties.get('frame', '0001')
                    cachedProperties = recipeProperties
                    recipeProperties['pose'] = mode.get('[recipeName]', cachedProperties)
                    cachedPropertiesPath = mode.get("[poseEditingFile]", recipeProperties).replace(".psd", ".json")
                    # If this file exists, it means that it was previously being edited
                    # Once edited in photoshop, this file gets created and contains
                    # the most recent version of this setup created by flix
                    if self.fileServiceLocal.exists(cachedPropertiesPath):
                        cachedProperties = json.loads(self.fileServiceLocal.loadTextFile(cachedPropertiesPath))

                    # Publish a new version
                    recipe.updateRecipeFileData('multiTracks', multiTrackXML)
                    recipe.publishNewVersion(copyRenders=False)
                    newRecipeProperties = recipe.getProperties()
#                    multiTrackPath = Mode.getPath(Recipe.MULTITRACK_FILE, newRecipeProperties)
#                    self.fileService.saveXMLFile(multiTrackPath, multiTrackXML)

                    # Create the xml to be sent to flix
                    recipiesXML = ET.fromstring('<Recipies/>')
                    setupXML = ET.fromstring('<OldSetup show="%s" sequence="%s" beat="%s" setup="%s" version="%s" />'\
                                     % (cachedProperties["show"], cachedProperties["sequence"], cachedProperties["beat"], cachedProperties["setup"], cachedProperties["version"]))

                    newSetupXML = recipe.getMasterXML()
                    setupXML.append(newSetupXML)

                    recipiesXML.append(setupXML)

                    # Store the new version of this setup so that it can automatically be replaced in the next version
                    self.fileServiceLocal.saveTextFile(cachedPropertiesPath, json.dumps(newRecipeProperties))
                    log(['replacing setups %s' % ET.tostring(recipiesXML)])
                    self.addFeedback("replaceSetupsMultiTracks", ET.tostring(recipiesXML))

        return multiTrackXML

    def updateEditedRefImages(self, recipe):
        """
        Replace an edited ref image with a new setup
        """
        oldProperties = recipe.getProperties()

        show = oldProperties['show']
        sequence = oldProperties['sequence']
        oldMode = Mode(show, sequence)
        updatedPoses = self.__getUpdatedPoses(recipe)

        newRecipeXML = CopySetup.localizeSetup(oldProperties, show, sequence,
                                             renderCallback=self.__renderCallback,
                                             setupCallback=self.feedReloadSetupsMultiTracks,
                                             multiTrackCallback=self.feedReloadSetupsMultiTracks)

        newRecipe = Recipe.fromXMLElement(newRecipeXML)

        self.__storeUpdatedPoses(newRecipe, updatedPoses)
        self.__updatePosesInSetup(newRecipe, updatedPoses)

        oldProperties = recipe.getProperties()
        existingRecipeEditingPath = oldMode.get("[poseEditingFile]", oldProperties).replace(".psd", ".xml")

        # if a setup has been send to flix already we will now use the new recipe version
        if self.fileServiceLocal.exists(existingRecipeEditingPath):
            oldProperties = self.fileServiceLocal.loadXMLFile(existingRecipeEditingPath).find("Properties").attrib


        recipiesXML = ET.fromstring('<Recipies/>')
        newSetupXML = newRecipe.getMasterXML()

        setupXML = ET.fromstring('<OldSetup show="%s" sequence="%s" beat="%s" setup="%s" version="%s" />'\
                         % (oldProperties["show"],
                            oldProperties["sequence"],
                            oldProperties["beat"],
                            oldProperties["setup"],
                            oldProperties["version"]))


        setupXML.append(newSetupXML)
        recipiesXML.append(setupXML)
        self.addFeedback("replaceSetupsMultiTracks", recipiesXML)

        FlixNuke().fromRecipe(newRecipe)
        FlixNuke().compRecipe(newRecipe, renderCallback=self.__renderCallback)

        newProperties = newRecipe.getProperties()
        mode = Mode(newProperties.get('show', None), newProperties.get('sequence', None))
        newMultitrackFile = mode.get('[recipeMultiTrackFile]', newProperties)
        newMultitrack = self.fileServiceLocal.loadTextFile(newMultitrackFile)

        data = []
        data.append('<Recipies>')
        data.append(
                    """<Setup
                    show="%(show)s"
                    sequence="%(sequence)s"
                    beat="%(beat)s"
                    setup="%(setup)s"
                    version="%(version)s">'""" % newProperties)
        data.append(newMultitrack + "</Setup>" + "</Recipies>")
        dataString = "".join(data)

        self.feedReloadSetupsMultiTracks(dataString)

#        FlixNuke().compRecipe(newRecipe, fileOutNodes='fileOut_master_png')

        return newRecipe



    def __getUpdatedPoses(self, recipe):
        """
        return a list of updated poses
        """

        recipeProperties = recipe.getProperties()

        updatedPoses = list()

        # check to see if we have any new poses
        mode = recipe.mode
        tempPath = mode.get(Recipe.POSE_EDITING_FOLDER, recipeProperties)

        if self.fileServiceLocal.exists(tempPath):
            tempFiles = self.fileServiceLocal.listFolder(tempPath)
            for f in tempFiles:
                if f.endswith(".psd"):
                    if f.startswith("."):
                        continue

                    isPsdMultiLayerPath = f.replace(".psd", ".psd.multilayer")
                    keepPsd = False
                    if (isPsdMultiLayerPath in tempFiles):
                        keepPsd = True

                    outPsdPath = tempPath + "/" + f
                    infoXMLPath = tempPath + "/" + f.replace(".psd", ".xml")
                    poseXML = self.fileServiceLocal.loadXMLFile(infoXMLPath)
                    updatedPoses.append({'outPsdPath':outPsdPath, 'poseXML':poseXML, 'keepPsd':keepPsd, 'infoXMLPath':infoXMLPath})

        return updatedPoses

    def __storeUpdatedPoses(self, recipe, updatedPoses):

        recipeProperties = recipe.getProperties()
        mode = Mode(recipeProperties.get('show', None), recipeProperties.get('sequence', None))
        multiTrackPath = mode.get(Recipe.MULTITRACK_FILE, recipeProperties)
        try:
            multiTrackXML = self.fileServiceLocal.loadXMLFile(multiTrackPath)
        except:
            multiTrackXML = XMLUtils.loadAndCleanXML(multiTrackPath)

        for newPose in updatedPoses:
            print newPose
            poseXML = newPose['poseXML']
            outPsdPath = newPose['outPsdPath']
            keepPsd = newPose['keepPsd']
            infoXMLPath = newPose['infoXMLPath']

            poseId = poseXML.attrib.get("id", -1)

            poseXMLItems = self.__getMultiTrackElementWithId(multiTrackXML, poseId)
            if poseXMLItems is None:
                continue
            if poseXMLItems.get("pose", None) is None:
                continue

            pose = poseXMLItems["pose"].attrib["file"]

            userRigName = poseXMLItems["rig"].attrib["userRigName"]

            posePropertiesXML = poseXML.find("Properties")

            if posePropertiesXML == None:
                posePropertiesXML = XMLUtils.getXMLElementForClass("Properties")
                poseXML.append(posePropertiesXML)

            poseProperties = posePropertiesXML.attrib

            # determine the pose name for which to save the pose as
            basename = poseProperties.get("pose", "")

            if pose != "[poseFile]":
                basename = os.path.basename(pose)
                basename = basename.replace(".png", "")
                if basename.rfind("_v") > 0:
                    pose = basename[0:basename.rfind("_v")]

                if ("[" in basename) or ("]" in basename):
                    pose = "[defaultPose]"

            # create a new pose if necessary
            if (pose == "[clearPose]") or (pose == mode.get("[clearPose]", recipeProperties)) or (pose == "[defaultPose]") or (pose == mode.get("[defaultPose]", recipeProperties)):
                basename = setupName + "_" + userRigName + "_" + poseXML.attrib.get("id", "")

            # define the filename for the pose name
            poseProperties["pose"] = basename
            poseProperties["version"] = ">"

            poseProperties["show"] = recipeProperties["show"]
            poseProperties["sequence"] = recipeProperties["sequence"]
            poseProperties["beat"] = recipeProperties["beat"]

            # gets the latest incremental number for this pose
            version = FlixVersioning().poseVersionUp(poseProperties["show"],
                                                     poseProperties["sequence"],
                                                     poseProperties["beat"],
                                                     poseProperties["pose"])
            log('new pose version %s' % version)
            poseProperties["version"] = str(version)

            poseXML.attrib["file"] = "[poseFile]"
            posePropertiesXML.attrib["version"] = poseProperties["version"]
            posePropertiesXML.attrib["pose"] = poseProperties["pose"]

            posePropertiesXML.attrib["show"] = recipeProperties["show"]
            posePropertiesXML.attrib["sequence"] = recipeProperties["sequence"]
            posePropertiesXML.attrib["beat"] = recipeProperties["beat"]

            mode = Mode(posePropertiesXML.attrib.get('show', None), posePropertiesXML.attrib.get('sequence', None))
            newPosePath = mode.get("[poseFile]", posePropertiesXML.attrib)

            poseFolder = os.path.dirname(newPosePath)
            self.fileService.createFolder(poseFolder)

            # copy the poses to the pose paths.
            # self.fileServiceLocal.copy(outPsdPath, newPosePath)
            # self.fileServiceLocal.removeFile(poseSpacePath)
            # self.fileService.copyFromLocal(newPosePath, True)

            # copy the psd file if any
            newPsdPath = newPosePath.replace(".png", ".psd")

            if self.fileServiceLocal.exists(outPsdPath):
                self.fileServiceLocal.copy(outPsdPath, newPsdPath)
                self.fileService.copyFromLocal(newPsdPath, True)
            elif newPosePath != newPsdPath:
                self.fileServiceLocal.copy(newPosePath, newPsdPath)
                self.fileService.copyFromLocal(newPosePath, True)

            newPose['poseXML'] = poseXML
            newPose['outPsdPath'] = outPsdPath

            # Update the xml to reflect the new pose
            self.fileService.saveXMLFile(infoXMLPath, poseXML)

        return updatedPoses


    def __updatePosesInSetup(self, recipe, updatedPoses):
        # Update the path in the multiTrack

        if len(updatedPoses) == 0:
            return None

        recipeProperties = recipe.getProperties()
        mode = Mode(recipeProperties.get('show', None), recipeProperties.get('sequence', None))
        multiTrackPath = mode.get(Recipe.MULTITRACK_FILE, recipeProperties)
        try:
            multiTrackXML = self.fileService.loadXMLFile(multiTrackPath)
        except:
            multiTrackXML = XMLUtils.loadAndCleanXML(multiTrackPath)

        for updatedPose in updatedPoses:
            poseXML = updatedPose["poseXML"]
            pose = poseXML.attrib["file"]
            poseId = poseXML.attrib.get("id", -1)
            rigName = poseXML.attrib["rig"]
            billboardName = poseXML.attrib["billboard"]
            frame = int(poseXML.attrib["frame"])
            poseIndex = int(poseXML.attrib["index"])
            trackName = poseXML.attrib["track"]
            outPsdPath = updatedPose["outPsdPath"]

            foundPose = None
            # find the pose in the xml
            for rigType in multiTrackXML.getchildren():
                for r in rigType.getchildren():
                    for rig in r.getchildren():
                        if rig.attrib["name"] != rigName:
                            continue
                        for billboard in rig.getchildren():
                            if billboard.attrib["billboard"] != billboardName:
                                continue
                            for multiTrack in billboard.getchildren():
                                for track in multiTrack.getchildren():
                                    if track.attrib["name"] == trackName:
                                        for cdl in track.getchildren():
                                            for clip in cdl.getchildren():
                                                for  clipType in clip.getchildren():
                                                    lastFrame = -1
                                                    for pose in clipType.getchildren():
                                                        if poseId == pose.attrib.get("id", -1):
                                                            foundPose = pose


            if foundPose != None:
                if int(foundPose.attrib["index"]) == int(poseIndex):
                    foundPose.attrib["file"] = poseXML.attrib["file"]
                    foundPoseXML = foundPose.find("Properties")
                    if foundPoseXML is None:
                        foundPoseXML = XMLUtils.getXMLElementForClass("Properties")
                        foundPose.append(foundPoseXML)
                    foundPoseXML.attrib = poseXML.find("Properties").attrib.copy()
                    # delete the source pose
                    self.fileService.removeFile(outPsdPath)
                    isPsdMultiLayerPath = outPsdPath.replace(".out.psd", ".out.psd.multilayer")
                    if self.fileService.exists(isPsdMultiLayerPath):
                        self.fileService.removeFile(isPsdMultiLayerPath)


        if multiTrackXML:
            log("refreshing multitrack")
            multiTrackXML.attrib['locked'] = '0'
            recipe.publishNewVersion()  # publish a new version
            newRecipeProperties = recipe.getProperties()
            multiTrackPath = mode.get(Recipe.MULTITRACK_FILE, newRecipeProperties)
            log("new multiTrackPath %s" % multiTrackPath)
            self.fileService.saveXMLFile(multiTrackPath, multiTrackXML)
        return multiTrackXML


    def __toPoseSpace(self, pose):
        """
        Convert a pose and bring it back to pose space. This is
        used after a pose is being edited in photoshop
        """
        poseSpacePath = pose.replace(".psd", ".png")
        log('copying to pose space')
        FlixNuke().toPose(pose, poseSpacePath)

        return poseSpacePath


    def __getMultiTrackElementWithId(self, multiTrackXML, itemId):
        """
        Any item within a multitrack has a id. This function
        will return that item with with requested id.
        """

        for rigType in multiTrackXML.getchildren():
            for r in rigType.getchildren():
                for rig in r.getchildren():
                    if rig.attrib.get("id") == itemId:
                            return {"rig":rig}
                    for billboard in rig.getchildren():
                        if billboard.attrib.get("id") == itemId:
                                return {"rig":rig, "billboard":billboard}
                        for multiTrack in billboard.getchildren():
                            for track in multiTrack.getchildren():
                                if track.attrib.get("id") == itemId:
                                        return {"rig":rig, "billboard":billboard, "track":track}
                                for cdl in track.getchildren():
                                    for clip in cdl.getchildren():
                                        if clip.attrib.get("id") == itemId:
                                                return {"rig":rig, "billboard":billboard, "track":track, "clip":clip}
                                        for  clipType in clip.getchildren():
                                            for pose in clipType.getchildren():
                                                if pose.attrib.get("id") == itemId or itemId == -1:
                                                        return {"rig":rig, "billboard":billboard, "track":track, "clip":clip, "pose":pose}
        return None

    @cherrypy.expose
    def editPanels(self, panels, **properties):
        """
        Open multiple panels in photoshop
        """

        if type(panels) is not list:
            panels = [panels]

        panels.reverse()

        panelsXML = []
        for panel in panels:
            panelXML = ET.fromstring(panel)

            multiTrackXML = panelXML.find("MultiTrackElements")
            if multiTrackXML is not None:
                self.__saveSetupData(multiTrackDataXMLS=ET.tostring(multiTrackXML), properties=panelXML.attrib)

            panelsXML.append({"properties":panelXML.attrib, "multiTrackXML":multiTrackXML})

        if panelsXML:
            if (OSUtils.type == OSUtils.LINUX):
                paths = []
                for panel in panelsXML:
                    properties = panel['properties'].copy()
                    properties['frame'] = '#'
                    mode = Mode(properties.get('show', None), properties.get('sequence', None))
                    path = mode.get('[recipeCompedFile]', properties)
                    paths.append(path)
                    if not self.fileServiceLocal.exists(path):
                        raise utils.FlixException(msg="Missing File: %s"%path)
                command = Mode().get("[editImageCommand]")
                log('Edit command %s' % command)
                os.system(command + " " + ' '.join(paths))
            else:
                Photoshop().createPhotoshopFileForPanels(panelsXML)

        return "Done"

    @cherrypy.expose
    def runInKatana(self, snappyPaths):
        """
        Open a collection of shots in katana
        """
        # RUN SOME COMMAND IN KATANA
        return "Done"


    @cherrypy.expose
    def revealInFinder(self, paths=[], ** properties):
        """
        Show in finder the selected path
        """
        log('reveal in finder %s' % paths)

        if type(paths) is not list:
            paths = paths.split(",")

        # On linux show the file in the flix browser
        if flix.platform == flix.LINUX:
            self.feedErrorAlert('Original Files: \n %s'%'\n'.join(paths), 'Original Files')
        else:
            notFound = OSUtils().revealFiles(paths)

            if len(''.join(paths)) == 0:
                self.feedErrorAlert('Original file not defined.', 'File Not Found')
            if len(notFound) > 0:
                self.feedErrorAlert('Could not find: \n %s'%'\n'.join(notFound), 'File Not Found')

        return ""


    @cherrypy.expose
    def updateSetupFromPhotoshop(self, *arg, **properties):
        """
        Tell the client to reload the note images
        """
        log(["FROM PHOTOSHOP", properties])

        self.compSetupData(**properties)
        return "done"


    @cherrypy.expose
    def bringFlixToFront(self):
        """
        Bring safari to the front
        """
        if OSUtils.getType() == OSUtils.MAC:
            command = "osascript -e 'tell application \"System Events\" to set frontmost of process \"Safari\" to true'"
            OSUtils.run(command)

    @cherrypy.expose
    def editPose(self, *arg, **properties):
        """
        Edit a pose in pose space
        """
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        posePath = mode.get(arg[0], properties)

        self.fileService.copyToLocal(posePath)
        posePath = self.repath.localize(posePath)
        if not self.fileServiceLocal.exists(posePath):
            raise utils.FlixException(msg="Missing File: %s"%posePath)

        command = Mode().get("[editImageCommand]")
        command = command + " " + posePath

        if OSUtils.getType() == OSUtils.WINDOWS:
            command = command.replace("/", "\\")

        OSUtils.run(command)

        return posePath

    @cherrypy.expose
    def addFeedback(self, command, data):
        """
        Stores feedback that will be passed back to the client
        """
        # TODO: move this to server.py and call it 'publishMessage'
        # import server
        # diff = time.time() - self._lastPublishTime
        # if diff*1000 < 1:   # if we were called less than a millisecond ago, sleep for the difference
        #     try:
        #         log('addFeedback: %s: extra sleep of %f' % (command,(.0015-diff)), isInfo=True)
        #         time.sleep(.0015 - diff)
        #     except Exception:	# ignore negative sleep errors
        #         pass
        # server.publishingChannelSet.publishObject(data, 'FLIX', command)
        # self._lastPublishTime = time.time()
        """
        import server
        if self._feedbackLock is None:
            self._feedbackLock = threading.Lock()

        self._feedbackLock.acquire()
        try:
            time.sleep(.1)
            server.publishingChannelSet.publishObject(data, 'FLIX', command)
        except Exception,e:
            log('Could not feed command %s. %s' % (command, e), isError=True)
        self._feedbackLock.release()
        """

        log('addFeedback: command = %s' % command)
        self.session.addUpdate("", "", command, data)

    @cherrypy.expose
    def launchDrawingsImporter(self, show, sequence, beat="p", importAsSequence=0):
        """
        Launches the media importer
        """
        importAsSequence = int(importAsSequence)
        supportedExtensions = ['jpg', 'jpeg', 'tiff', 'tif', 'tga', 'png', 'psd', 'sgi', 'exr', 'pic', 'bmp', 'hdr', 'iff', 'xml', 'mov', 'mp4'] #, 'mp3']

        output = OSUtils.runFileBrowser(kBrowseTypeLoadFiles, 'Choose Files To Import', '/', 'import')

        log('Files from browser %s' % output, isInfo=True)
        if not output:
            raise utils.FlixException(error=output, msg='No Valid directory selected.')


        flixImportXML = XMLUtils.getXMLElementForClass("flixImport")
        flixImportXML.attrib["waitForSource"] = '0'
        flixImportXML.attrib["importMovie"] = '0'
        flixImportXML.attrib["multipleSetups"] = '%d' % (1 - int(importAsSequence))

        mode = Mode(show, sequence)

        unsupported = []

        for f in output:
            f = f.strip()
            if os.path.isfile(f):
                extension  = f.split('.')[-1].lower()
                if extension in ["mp3", "wav"] :
                    # IMPORT AUDIO
                    mp3_folder = mode.get("[editorialMPThreeFolder]")
                    log("AUDIO IMPORT - file: %s" %(f))

                    try:
                        imported_mp3_file_name = sequence + "_imported_v" + str(int(time.time() * 1000)) + ".mp3"
                        imported_mp3_path = "%s/%s" %(mp3_folder, imported_mp3_file_name)

                        # COPY IMPORTED FILE TO SERVER
                        self.fileService.copyToLocal(f)
                        # self.fileServiceLocal.copy(f, imported_mp3_path)
                        time.sleep(0.5) # thomas.helman -  added to provide a bit of latency

                        # TEMPORARY COPY FOR RESAMPLING
                        imported_mp3_temp_path = imported_mp3_path.replace(".mp3", ".TEMPORARY.%s"%extension)
                        self.fileServiceLocal.copy(f, imported_mp3_temp_path)
                        #log("AUDIO IMPORT - temporary audio file ... %s" %(imported_mp3_temp_path))

                        # RESAMPLE - TODO thomas.helman (this needs to be replaced by DK's new audio utility class
                        log("AUDIO IMPORT -  resampling ...")

                        # RESAMPLE AUDIO TO 44.1
                        mp3_resampler = FromMov().convertWavToMP3(imported_mp3_temp_path, imported_mp3_path)

                        # REMOVE TEMP COPY
                        self.fileServiceLocal.removeFile(imported_mp3_temp_path)
                        #log("AUDIO IMPORT - temporary audio file removed ... %s" %(imported_mp3_temp_path))
                        log("AUDIO IMPORT - imported audio file exists ... %s" %(imported_mp3_path))

                        output = [ imported_mp3_path ]

                        return output

                    except Exception, e:
                        log('ERROR importing audio file: %s' %(e))
                        return "IMPORT_AUDIO_ERROR"

                elif extension == 'xml':
                    p = self.importDrawing(None, None, beat, f)
                else:
                    imageXML = XMLUtils.getXMLElementForClass("image")
                    imageXML.attrib["originalFile"] = f
                    imageXML.attrib["imageFile"] = f
                    imageExtension = f.split('.')[-1].lower()
                    if imageExtension in supportedExtensions:
                        if imageExtension in ['mov', 'mp4']:
                            flixImportXML.attrib["importMovie"] = '1'
                        flixImportXML.append(imageXML)
                    else:
                        unsupported.append(os.path.basename(f))


        if len(unsupported) > 0:
            if len(unsupported) > 10:
                unsupported = unsupported[0:10]
                unsupported.append('...')
            self.feedErrorAlert('Unsupported Media Format:\n\n%s' % '\n'.join(unsupported), 'Imported Media Error')
            return

        if len(flixImportXML) > 0:
            tempFolder = OSUtils.getLocalTempFolder()
            tempFolder = tempFolder[0:(len(tempFolder) - 1)]
            fileXMLPath = tempFolder + "/flix_import_" + str(int(time.time() * 1000)) + ".xml"
            fileXML = open(fileXMLPath, "w")
            fileXML.write(ET.tostring(flixImportXML))
            fileXML.close()
            p = self.importDrawing(None, None, beat, fileXMLPath, deleteSource=2, importAsSequence=importAsSequence)

        return output

    @cherrypy.expose
    def getMayaParameters(self):
        mode = Mode()
        param = {'mayaStartFrame': mode.get('[mayaStartFrame]'),
                      'mayaKeyAnimationFormat': mode.get('[mayaKeyAnimationFormat]'),
                      'mayaDataCapture':mode.get('[mayaDataCapture]')}
        return json.dumps(param)

    @cherrypy.expose
    def updateMayaPort(self, **kargs):
        mayaPort = kargs.get('mayaPort', 35990)
        os.environ['FLIX_MAYA_PORT'] = mayaPort

    @cherrypy.expose
    def importMayaSequence(self, show=None, sequence=None, edlFile="", movieFile="", importAsStills=False, externalMetaData=""):
        """create a new sequence version from the maya edl
        """
        if None in [show, sequence]:
            serviceClass = "%s.%s"%(self.__module__,self.__class__.__name__),
            serviceMethod = 'importMayaEdit'
            ClientCommands().getSessionInfo(locals(), serviceClass, serviceMethod)
        else:
            self.importMayaEdit(locals(), locals())

    def importMayaEdit(self, sessionInfo, args):
        fromMaya = FromMaya(sessionInfo.get('show'), sessionInfo.get('sequence'), sessionInfo.get('branch'), args.get('edlFile'), args.get('movieFile', ""), "", "", importAsStills=args.get('importAsStills'))
        shotCutList = fromMaya.importToFlix()
        if Mode().get("[updateMayaSequencerShots]"):
            self.updateMayaSequencer(shotCutList)
        externalMetaData = args.get('externalMetaData')
        if externalMetaData:
            with open(externalMetaData) as dataPath:
                dataContent = JsonUtils.jsonLoadAscii(dataPath)
            panelList = [shot for shot in shotCutList if not shot.isMarker()]
            for i, shot in enumerate(panelList):
                shotMetaData = self.metaDataFromShot(dataContent, i)
                properties = shot.recipe
                self.copyMetaData(properties, shotMetaData)

    @cherrypy.expose
    def importNukeStudioSequence(self, show=None, sequence=None, branch="", edlFile="", movieFile="", comment="", username="", importAsStills=False):
        """create a new sequence version from the Nuke Studio XML
        """
        if None in [show, sequence]:
            serviceClass = "%s.%s"%(self.__module__,self.__class__.__name__),
            serviceMethod = 'importNukeStudioEdit'
            ClientCommands().getSessionInfo(locals(), serviceClass, serviceMethod)
        else:
            log("**** importNukeStudioSequence locals: %s" % str(locals()), isInfo=True)
            self.importNukeStudioEdit(locals(), locals())            

    def importNukeStudioEdit(self, sessionInfo, args):
        show = sessionInfo.get('show')
        sequence = sessionInfo.get('sequence')
        branch = sessionInfo.get('branch')
        log("**** importNukeStudioEdit sessionInfo: show %s" % str(show), isInfo=True)
        log("**** importNukeStudioEdit sessionInfo: sequence %s" % str(sequence), isInfo=True)

        fromNukeStudio = FromNukeStudio(sessionInfo.get('show'), sessionInfo.get('sequence'), sessionInfo.get('branch'), args.get('edlFile'), args.get('movieFile', ""), args.get('comment', ""), args.get('username', ""), importAsStills=args.get('importAsStills'))
        log("**** CALLED importNukeStudioEdit %s" % str(fromNukeStudio), isInfo=True)
        fromNukeStudio.importToFlix()

    def updateMayaSequencer(self, shotCutList):
        markerSetup = None
        result = []
        shotIndex = 0
        for shot in shotCutList:
            if shot.isMarker():
                markerSetup = shot.recipe.getSetupName()
                continue
            result.append((shotIndex, shot.recipe.getTapeName(), markerSetup))
            shotIndex += 1
        data = urllib.urlencode({'shotList': result})
        mayaPort = os.environ.get('FLIX_MAYA_PORT', 35990)
        host = os.environ.get('FLIX_SERVER', "127.0.0.1")
        result = requests.get('http://%s:%s/updateSequencer'%(host, mayaPort), params=data)
        if result.status_code != 200:
            raise utils.FlixException(error=result.content,
                                        msg='Maya Failed with status code: %s\nRefer to Maya shell for complete error' % result.status_code, notify=True)

    def metaDataFromShot(self, metaData, shotIndex):
        result = {'frames'  : [frame for frame in metaData.get('frames', [])
                               if int(frame.get('panelNumber')) == int(shotIndex)],
                  'software': metaData.get('software')}
        return result

    @cherrypy.expose
    def importDrawing(self, show=None, sequence=None, beat="p", path="", deleteSource=0, importAsSequence=0, selectedShot=None, username='', externalMetaData=""):
        """
        Import the drawing indicated in the path property
        """

        # for this part is passed on the client
        log(["Import drawings, importAsSequence:", importAsSequence])

        importAsSequence = int(importAsSequence)
        deleteSource = int(deleteSource)

        if show == None:
            xmlString = '<File path="' + path + '" beat="' + beat + '" deleteSource="' + str(deleteSource) + '" externalMetaData="' + str(externalMetaData) + '"/>'
            self.addFeedback("importDrawingAsSetup", ET.fromstring(xmlString))
            cherrypy.response.headers['Content-Type'] = 'text/html'
            return """<html><head> <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
<script type="text/javascript">window.focus();window.close();</script>
</head></html>"""


        # From here on, is called when the client returns where it should be imported.
        if type(path) is not list:
            path = [{"imageFile":path}]

        newSetups = []
        sources = []
        movieXml = []

        sourcesXML = None
        if importAsSequence:
            sourcesXML = ET.Element("flixImport")

        replaceSelection = 0
        toDelete = []
        for source in path:
            sourceImage = source["imageFile"]
            log('Source Image %s' % sourceImage, isInfo=True)
            toDelete.append(sourceImage)
            waitForSources = False

            if sourceImage.endswith(".xml"):
                tempXML = sourceImage + str(uuid.uuid1()) +'.tmp'

                # Rename to avoid importing twice
                try:
                    self.fileServiceLocal.rename(sourceImage, tempXML)
                except Exception, e:
                    flix.utilities.log.log("Failed to rename %s to %s\n%s"%(sourceImage, tempXML, e))
                    tempXML = sourceImage
                toDelete.append(tempXML)
                sourcesXML = self.fileService.loadXMLFile(tempXML)

                if sourcesXML.tag == 'xmeml':
                    return self.importFCPXML(show, sequence, tempXML)

                replaceSelection = int (sourcesXML.attrib.get("replaceSelection", "0"))
                waitForSource = sourcesXML.attrib["waitForSource"] == "1"
                multipleSetups = sourcesXML.attrib["multipleSetups"] == "1"
                importMovie = sourcesXML.attrib.get("importMovie") == "1"

                if importMovie:
                    for index, imageXml in enumerate(sourcesXML.getchildren()):
                        copySourceXml = copy.deepcopy(sourcesXML)
                        filter(lambda x: copySourceXml.remove(x), copySourceXml.findall('image'))
                        currentTime = time.time()
                        movPose = {}
                        movPose['beat'] = "a"
                        movPose['poseFileExtension'] = ".mov"
                        movPose["pose"]              = "imported"
                        movPose["poseFrame"]         = "%04d" % (int(currentTime) + int(index))
                        movPose["version"]           = "1"
                        tempPose = Mode(show, sequence).get('[poseSequence]', movPose)

                        movPath = imageXml.attrib['imageFile']
                        if not self.fileService.exists(os.path.dirname(tempPose)):
                            self.fileService.createFolders(os.path.dirname(tempPose))
                        self.fileService.copy(movPath, tempPose)
                        frameRange = FlixNuke().getMovFrameRange(tempPose)
                        if len(frameRange) == 2:
                            copySourceXml.attrib['minFrame'] = frameRange[0]
                            copySourceXml.attrib['maxFrame'] = frameRange[1]
                        newImageXml = XMLUtils.getXMLElementForClass("image")
                        newImageXml.attrib['imageFile'] = tempPose
                        newImageXml.attrib["originalFile"] = imageXml.attrib["originalFile"]
                        copySourceXml.append(newImageXml)
                        movieXml.append(copySourceXml)

                # temp workaround for bug in TV-Paint which creates new attributes per child element
                if sourcesXML[0].attrib.get('replaceselection', False):
                    replaceSelection = int (sourcesXML[0].attrib.get("replaceselection", "0"))
                    waitForSource = sourcesXML[0].attrib["waitforsource"] == "1"
                    multipleSetups = sourcesXML[0].attrib["multiplesetups"] == "1"
                    if multipleSetups:
                        for sourceXML in sourcesXML:
                            originalFile = sourceXML.attrib['imageFile']

                            # if there is png file instead of a psd, use the png
                            # This is a temp workaround because TV-paint does not export camera moves
                            # through flix export
                            if originalFile.endswith('.psd'):
                                pngFile = originalFile.replace('.psd', '_c.png')
                                if self.fileServiceLocal.exists(pngFile):
                                    sourceXML.attrib['imageFile'] = pngFile
                                    if self.fileServiceLocal.exists(originalFile):
                                        try:
                                            self.fileServiceLocal.removeFile(originalFile)
                                        except:
                                            pass
                    else:
                        for sourceXML in sourcesXML:
                            originalFile = sourceXML.attrib['imageFile']
                            # if there is png file instead of a psd, use the png
                            # This is a temp workaround because TV-paint does not export camera moves
                            # through flix export
                            if originalFile.endswith('.psd'):
                                pngFile = originalFile.replace('.psd', '_c.png')
                                if self.fileServiceLocal.exists(pngFile):
                                    sourceXML.attrib['imageFile'] = pngFile
                                    if self.fileServiceLocal.exists(originalFile):
                                        try:
                                            self.fileServiceLocal.removeFile(originalFile)
                                        except:
                                            pass

                if replaceSelection == 1:
                    if selectedShot is None:
                        sourcesXML = None
                        continue
                    else:
                        selectedShot = ET.fromstring(selectedShot)
                else:
                    selectedShot = None

                if waitForSource:
                    waitForSources = True

                if multipleSetups:
                    log('Importing as stills', isInfo=True)
                    if importMovie:
                        continue
                    importAsSequence = True
                    for fileXML in sourcesXML.getchildren():
                        sources.append(fileXML.attrib)
                        toDelete.append(fileXML.attrib["imageFile"])
                    sourcesXML = None
            else:
                if importAsSequence:
                    sourceXML = ET.Element("image")
                    sourceXML.attrib["imageFile"] = sourceImage
                    sourcesXML.append(sourceXML)
                else:
                    sources.append(source)

        setupCallback = self.feedImportedSetups
        setup = None
        if replaceSelection == 1:
            log('replacing shot %s ' % ET.tostring(selectedShot))
            if selectedShot is not None:
                currentBeat = selectedShot.attrib.get('beat', beat)
                if currentBeat != 'ref':
                    beat = currentBeat
                setup = selectedShot.attrib.get('setup', setup)
            setupCallback = self.feedReplaceSetups
        elif replaceSelection == 2:
            setupCallback = self.feedSmartReplaceSetups

        if sourcesXML is not None:
            log ("importing sequence")
            if beat == "p":
                beat = "a"
            if movieXml:
                sourcesXML = movieXml
            animateSetups = AnimateSetups(show, sequence, beat,
                        renderCallback=self.__renderCallback,
                        setupCallback=setupCallback,
                        multiTrackCallback=self.feedReloadSetupsMultiTracks,
                        associatedShot=selectedShot,
                        username=username)

            log('generate from sources')
            animateSetups.fromSourcesXML(sourcesXML)
            newSetups = [animateSetups.getRecipe()]
        elif sources:
            log ('Import as drawings')

            p = DrawingImporter(show, sequence, beat, sources=sources,
                                renderCallback=self.__renderCallback,
                                setupCallback=setupCallback,
                                multiTrackCallback=self.feedReloadSetupsMultiTracks,
                                waitForSources=waitForSources,
                                associatedShot=selectedShot, username=username)

            if p.job.status == flix.remote.remoteHttpCall.FlixRequest.FAIL:
                log ('Import drawing Failed', isError=True)
                self.feedErrorAlert('Import drawing Failed', 'Error Importing')


            newSetups = p.getNewSetups()

            if deleteSource == 1:  # fix back to 1
                for deletePath in toDelete:
                    try:
                        os.remove(deletePath)
                    except Exception, e:
                        log("Error removing source file %s: %s" % (deletePath, e), isError=True)
            elif deleteSource == 2:
                deletePath = path[0]["imageFile"]
                try:
                    os.remove(deletePath)
                except Exception, e:
                    log("Error removing xml file %s: %s" % (deletePath, e), isError=True)
        if externalMetaData and newSetups:
            if isinstance(newSetups[0], Recipe):
                recipe = newSetups[0]
            else:
                recipe = Recipe.fromXMLElement(ET.fromstring(newSetups[0]))
            self.copyMetaData(recipe, externalMetaData)

        return str(newSetups)

    @cherrypy.expose
    def createNewSetup(self, show, sequence, beat="p"):
        """
        creates a new panel setup
        """
        importer = DrawingImporter(show, sequence, beat,
                                [{"imageFile":DrawingImporter.BLANK_SETUP, "useClearCompImage": "1"}],
                                setupCallback=self.feedImportedSetups, saveBlankMultitrack=True)

        recipies = importer.getNewSetups()
        mode = Mode(show, sequence)
        properties = ET.fromstring(recipies[0]).find('Properties').attrib
        properties['frame'] = '0001'
        multiTrackFile = mode.get('[recipeMultiTrackFile]', properties)

        compFile = mode.get('[recipeCompedFile]', properties)
        self.addFeedback("reloadImages", [compFile])

        multiTrack = self.fileServiceLocal.loadTextFile(multiTrackFile)

        data = []
        data.append('<Recipies>')
        data.append('<Setup show="%(show)s" sequence="%(sequence)s" beat="%(beat)s" setup="%(setup)s" version="%(version)s">' % properties)
        data.append(multiTrack + "</Setup>" + "</Recipies>")
        dataString = "".join(data)

        self.feedReloadSetupsMultiTracks(dataString)

    def importFCPXML(self, show, sequence, path):
        log('Importing fcp')
        movFile = ""
        currentTime = time.localtime(time.mktime(time.localtime()))
        currentTimeString = time.strftime("%Y_%m_%d_%H_%M", currentTime)
        movieName = [filePath for filePath in self.fileService.listFolder(os.path.dirname(path)) if filePath.endswith('.mov')]
        moviePath = "%s/%s"%(os.path.dirname(path), movieName[0]) if movieName else None
        movFolder =  Mode().get('[editorialMOVFolder]', {'show':show, 'sequence':sequence})
        if moviePath:
            newMovFile = movieName[0].replace(".mov", "_%s.mov"%currentTimeString)
            if self.repath.globalize(os.path.dirname(moviePath)) == movFolder:
                movFile = moviePath
            else:
                self.fileServiceLocal.copy(moviePath, movFolder + "/" + newMovFile)
                movFile = movFolder + "/" + newMovFile
        fromFCP = flix.toEditorial.fromFCP.FromFCP(show, sequence, 'main', path, movFile, '', 'test', True, False)
        with fromFCP.mode.using({"fcpMarker":'timeline'}):
            fromFCP.parseEDL()
        fromFCP.mergeDownClips()
        sourceFiles = fromFCP.newRecipiesFromClipMedia(renderCallback=self.__renderCallback,
                                                       importSetupCallback=self.feedImportedSetups,
                                                       replaceSetupCallback=self.feedReplaceSetups,
                                                       multiTrackCallback=self.feedReloadSetupsMultiTracks)

        # remove source files from ~/flix/
        for sourceFile in self.fileServiceLocal.listFolder(os.path.dirname(path)):
            self.fileServiceLocal.removeFile("%s/%s"%(os.path.dirname(path), sourceFile))

        self.feedErrorAlert("Storyboard Pro import successful", 'Complete!')

    def validateSBPMovieName(self, movieName, edlPath):
        log("validtae sbp movie name %s %s"%(movieName, edlPath))
        edlName = os.path.basename(edlPath)
        movExtLess = os.path.splitext(movieName)[0]
        if edlName.startswith(movExtLess):
            return True

    @cherrypy.expose
    def guessRebuildMutliTrackXML(self, panels, **properties):
        """
        Launches the panels exporter
        """

        if type(panels) is not list:
            panels = [panels]

        for panel in panels:
            panelXML = ET.fromstring(panel)

            recipe = Recipe(panelXML.attrib['show'],
                            panelXML.attrib['sequence'],
                            panelXML.attrib['beat'],
                            panelXML.attrib['setup'],
                            panelXML.attrib['version'])

            setupVersion = panelXML.attrib['version']
            currentPoses = recipe.getPoses()

            if len(currentPoses) != 1:
                self.feedErrorAlert('Guess Rebuilding only works on stills')
                return

            poseXML        = currentPoses[0]['poseXML']
            propertiesXML  = poseXML.find('Properties')
            currentVersion = propertiesXML.attrib.get('version')

            if setupVersion == currentVersion:
                continue
            if setupVersion > currentVersion:
                propertiesXML.attrib['frame'] = '0001'
                propertiesXML.attrib['version'] = str(setupVersion)
                poseFile = Mode().get(poseXML.attrib['file'], propertiesXML.attrib)
                log('guessRebuildMutliTrackXML:: poseFile %s' % poseFile)
                if self.fileServiceLocal.exists(poseFile):
                    self.feedErrorAlert('Currently setup as version %s. Found pose for version %s. Updating panel to use that version' % (currentVersion, setupVersion), 'Rebuild')
                    propertiesXML.attrib['version'] = setupVersion
                    recipe.saveRecipeFiles()

                    # Updating cache for recipe file if you leave this, caching fails to see the new nuke file.. now part of flixNuke
                    FlixNuke().compRecipe(recipe, '1-1', renderCallback=self.__renderCallback, updateScript=True)

                    data = []
                    data.append('<Recipies>')
                    data.append('<Setup show="%(show)s" sequence="%(sequence)s" beat="%(beat)s" setup="%(setup)s" version="%(version)s">' % recipe.getProperties())
                    data.append(ET.tostring(recipe.getMultiTrackXML()) + "</Setup>" + "</Recipies>")
                    dataString = "".join(data)

                    self.feedReloadSetupsMultiTracks(dataString)

    def copyMetaData(self, recipe, metaData):
        applications = []
        cameraFrames = []
        if isinstance(metaData, (str, unicode)):
            with open(metaData) as dataPath:
                dataContent = JsonUtils.jsonLoadAscii(dataPath)
        else:
            dataContent = metaData
        currentApp = dataContent['software']
        currentApp['software'] = currentApp['name']
        currentApp['frames'] = []
        applications.append(currentApp)

        def buildDataDict(frame):
            dataDict = {'frame':frame['frame']}
            # this is ugly, separating camera objects from other objects
            objData = [x for x in frame['objects'] if x['type'] != 'camera']
            cameraData = [x for x in frame['objects'] if x['type'] == 'camera']
            if objData:
                dataDict['objects'] = objData
                currentApp['frames'].append(copy.copy(dataDict))
            if cameraData:
                dataDict['objects'] = cameraData
                cameraFrames.append(copy.copy(dataDict))

        map(buildDataDict, dataContent['frames'])
        metaData = {'applications':applications, 'camera':cameraFrames}

        return recipe.updateThirdPartyMetaData(metaData)

    def createNewSetupFeedReloadSetupsMultiTracks(self, multiTrackData):
        pass

    def feedErrorAlert(self, message, title='Error'):
        """
        Feed a series of setups to be imported in flix
        """
        self.addFeedback("displayMessage", [message, title])
        return ""

    @cherrypy.expose
    def feedImportedSetups(self, recipies, *args, **keys):
        """
        Feed a series of setups to be imported in flix
        """
        self.addFeedback("insertSetups", recipies)
        return ""

    @cherrypy.expose
    def feedReplaceSetups(self, recipies, *args, **keys):
        """
        Feed a series of setups to replace selected setups in flix
        """
        log("REPLACE SELECTION")
        self.addFeedback("replaceSelection", recipies)
        return ""

    @cherrypy.expose
    def feedSmartReplaceSetups(self, recipies, *args, **keys):
        """
        Feed a series of setups to replace existing setups in flix
        """
        log("SMART REPLACE SETUPS")
#        self.addFeedback("smartReplaceSetups", recipies)
        self.addFeedback("replaceSelection", recipies)
        return ""

    @cherrypy.expose
    def feedLocalizedSetups(self, recipies, sourceSetupsProperties, *args, **keys):
        """
        Feed a series of localized setups to replace existing setups in flix
        """
        self.addFeedback("replaceLocalizedSetups", [recipies, sourceSetupsProperties])
        return ""

    @cherrypy.expose
    def feedDuplicatedSetups(self, recipies, sourceSetupsProperties, *args, **keys):
        """
        Feed a series of duplicated setups to replace existing setups in flix
        """
        self.addFeedback("replaceDuplicatedSetups", [recipies, sourceSetupsProperties])
        return ""

    @cherrypy.expose
    def feedReloadSetupsMultiTracks(self, recipies, *args, **keys):
        """
        Feed a series of setup multitracks to be imported in flix
        """
        self.addFeedback("reloadSetupsMultiTracks", recipies)
        return ""


    @cherrypy.expose
    def openNukeComp(self, *arg, **keys):
        """
        Loads a nuke file based for the requested setup
        """
        mode = Mode(keys.get('show', None), keys.get('sequence', None))
        nukeCompPath = mode.get(Recipe.NUKE_FILE, keys)
        nukeCommand = mode.get("[nukeCommand]", keys)
        nukeCommand += " " + self.repath.localize(nukeCompPath) + "&"
        self.fileService.copyToLocal(nukeCompPath)

        OSUtils.run(nukeCommand)
        return

    @cherrypy.expose
    def openMayaScene(self, *arg, **keys):
        """
        Loads a maya file based for the requested setup
        """
        mode = Mode(keys.get('show', None), keys.get('sequence', None))
        mayaSceneFile = keys.get("mayaSceneFile")
        if not mayaSceneFile:
            recipePath = mode.get(Recipe.XML_FILE, keys)
            recipe = Recipe.recipeFromFile(recipePath)
            mayaSceneFile = recipe.getMayaFile()

        if not mayaSceneFile:
            return

        mayaCommand = mode.get("[mayaCommand]", keys)
        mayaCommand += " " + mayaSceneFile + "&"
        OSUtils.run(mayaCommand)
        return

    @cherrypy.expose
    def bookSetupsNumber(self, show, sequence, beat, totalSetups):
        """
        Send a request to VNP booking the specified amount of new numbers for setups
        belonging to the specified show, sequence, and beat
        """
        setups = DrawingImporter.bookPanelNumber(show, sequence, beat, int(totalSetups));

        setupsNumberXML = XMLUtils.getXMLElementForClass("BookedSetupsNumber")
        setupsNumberXML.attrib["show"] = show
        setupsNumberXML.attrib["sequence"] = sequence
        setupsNumberXML.attrib["beat"] = beat
        setupsNumberXML.attrib["totalSetups"] = str(len(setups))
        if len(setups) > 0:
            for i in range(0, len(setups)):
                setupXML = ET.Element("SetupNumber")
                setupXML.attrib["setup"] = setups[i]
                setupsNumberXML.append(setupXML)

        output = ET.tostring(setupsNumberXML)
        return output

    @cherrypy.expose
    def createVersionForSetup(self, *arg, **properties):
        """
        Create a new version of the setup/recipe
        """
#         result = DrawingImporter.createVersionForSetup(properties["show"], properties["sequence"], properties["beat"], properties["setup"]);
#         return result
        return True

    @cherrypy.expose
    def duplicateCreateBlankSetup(self, *arg, **properties):
        """
        Take the properties provided and create a new setup for the duplicate operation.
        The properties need to define the show, sequence, beat, setup  and version
        of the blank setup to create and of the setup to match the range.
        """
        recipe = CopySetup.createBlankSetupBookedMatchingSetupRange(properties,
                                                                    setupCallback=self.feedDuplicatedSetups,
                                                                    renderCallback=self.__renderCallback,
                                                                    multiTrackCallback=self.feedReloadSetupsMultiTracks,
                                                                    username=properties.get('username', ''))
        return recipe

    @cherrypy.expose
    def localize(self, *arg, **properties):
        """
        Take the properties provided and create a new setup for the paste/localize operation.
        The properties need to define the show, sequence, beat, setup  and version
        of the blank setup to create and of the setup to match the range.
        """
        recipe = CopySetup.createBlankSetupBookedMatchingSetupRange(properties,
                                                                    setupCallback=self.feedLocalizedSetups,
                                                                    renderCallback=self.__renderCallback,
                                                                    multiTrackCallback=self.feedReloadSetupsMultiTracks,
                                                                    username=properties.get('username', ''))
        return recipe

    @cherrypy.expose
    def duplicateCopySetup(self, *arg, **properties):
        """
        Copy the data of a setup to another setup passing the callback functions specific
        to the duplicate operation
        """
        log('duplicateCopySetup %s' % properties.get('username', ''))
        recipeXML = CopySetup.copySetupDataToSetup(properties,
                                                   setupCallback=self.feedDuplicatedSetups,
                                                   renderCallback=self.__renderCallback,
                                                   multiTrackCallback=self.feedReloadSetupsMultiTracks,
                                                   username=properties.get('username', ''))
        output = ET.tostring(recipeXML)
        return output

    @cherrypy.expose
    def localizeCopySetup(self, *arg, **properties):
        """
        Copy the data of a setup to another setup passing the callback functions specific
        to the paste/localize operation
        """
        recipeXML = CopySetup.copySetupDataToSetup(properties,
                                                   setupCallback=self.feedLocalizedSetups,
                                                   renderCallback=self.__renderCallback,
                                                   multiTrackCallback=self.feedReloadSetupsMultiTracks,
                                                   username=properties.get('username', ''))
        output = ET.tostring(recipeXML)
        return output


    @cherrypy.expose
    def animateShots(self, show, sequence, shotsXMLS, beat="a", *arg, **properties):
        """
        Take a series of a panels and merge them into an animatable shot
        """
        shotsXML = ET.fromstring(shotsXMLS)

        animate = AnimateSetups(show, sequence, beat,
                                renderCallback=self.__renderCallback,
                                setupCallback=None,
                                multiTrackCallback=None)

        animate.fromShotsXML(shotsXML)
        newRecipe = animate.getRecipe()

        recipies = "<Recipies>"
        recipies += self.fileServiceLocal.loadTextFile(newRecipe.getRecipeFile())
        recipies += "</Recipies>"
        self.feedImportedSetups(recipies)
        recipeProperties = newRecipe.getProperties()
        self.compSetupData(recipe=newRecipe)
        mode = Mode(recipeProperties.get('show', None), recipeProperties.get('sequence', None))
        multiTrackPath = mode.get(Recipe.MULTITRACK_FILE, recipeProperties)
        multiTrack = self.fileServiceLocal.loadTextFile(multiTrackPath)

        data = []
        data.append('<Recipies>')
        data.append('<Setup show="%(show)s" sequence="%(sequence)s" beat="%(beat)s" setup="%(setup)s" version="%(version)s">' % recipeProperties)
        data.append(multiTrack + "</Setup>" + "</Recipies>")
        dataString = "".join(data)

        self.feedReloadSetupsMultiTracks(dataString)


        return "Done"

    @cherrypy.expose
    def getMostRecentPublishedEdit(self, show, sequence, version):
        """Finds the path to the most recent published edit before the
        given version.
        """

        # grab shot edits cache path
        mode               = Mode(show, sequence)
        shotEditsCachePath = mode.get('[editorialFLEFilesCache]')

        # load the file and grab the published versions
        root           = self.fileService.loadXMLFile(shotEditsCachePath)
        isPublished    = lambda e: e.attrib['published'] == 'true'
        publishedEdits = filter(isPublished, root.getchildren())
        versions       = map(lambda e: int(e.attrib['version']), publishedEdits)

        # drop edits after the requested version
        versions.sort(reverse=True)
        versions = list(itertools.dropwhile(lambda v: v >= int(version), versions))

        # return path to fle
        if len(versions) > 0:
            return flix.core2.shotCutList.ShotCutList.getDefaultPath(mode, versions[0])

        # couldn't find a valid publisehd version
        return None


    @cherrypy.expose
    def publishSetupData(self, setupDataXMLS=None, *arg, **properties):
        """
        Take the xml data from the POST
        and publish it as new version of the recipe file
        """
        log(["publishSetupData:: new version", properties])


        recipeXML = ET.fromstring(setupDataXMLS)
        recipe = Recipe.fromXMLElement(recipeXML)

        recipe.publishNewVersion()

        recipeXMLs = recipe.toXMLElements()
        recipeXML = recipeXMLs["recipe"]

        return ET.tostring(recipeXML)


    @cherrypy.expose
    def isFile(self, path, *arg, **properties):
        """
        Return 1 if a file exists, or 0 if it does not.
        If properties are defined, dynamic path will be created
        """
        if properties:
            mode = Mode(properties.get('show', None), properties.get('sequence', None))
            path = mode.get(path, properties)
        return "%d" % (+self.fileService.exists(path))

    @cherrypy.expose
    def isFolder(self, path, *arg, **properties):
        """
        return 1 if a folder exists, or 0 if it does not.
        if properties are defined, dynamic path will be created
        """

        if properties:
            mode = Mode(properties.get('show', None), properties.get('sequence', None))
            path = mode.get(path, properties)
        return "%d" % (+self.fileService.isFolder(path))

    @cherrypy.expose
    def createFolder(self, path):
        """
        Create a folder on the shot tree. For extra security, "flix" needs to be part of the path
        """
        yield "\n"  # to avoid timeout
        log("creating folder")
        if "flix" in path:
            yield "%s" % self.fileService.createFolder(path)
            return
        yield 0
        return
    createFolder._cp_config = {'response.stream': True}

    @cherrypy.expose
    def createLink(self, source, destination):
        """
        Create a link on the shot tree. For extra security, "flix" needs to be part of the path
        """
        log("creating link")

        if "flix" in source:
            return "%s" % +OSUtils.createLink(source, destination)
        return "0"

    @cherrypy.expose
    def saveSetupNotes(self, setupNotesXMLS=None, **properties):
        """
        Take the data from the post and save it
        """
        self.__saveSetupNotes(setupNotesXMLS, properties)
        return "done"

    def __saveSetupNotes(self, setupNotesXMLS=None, properties={}):
        """
        Save the setup notes' data
        """
        if setupNotesXMLS:
            mode = Mode(properties.get('show', None), properties.get('sequence', None))
            setupNotesPath = mode.get("[recipeNotesFile]", properties)
            self.__saveFile(setupNotesPath, setupNotesXMLS)

    @cherrypy.expose
    def saveSetupNotesImage(self, **properties):
        """
        Take the data from the post and save the setup notes image's file
        """
        self.__saveSetupNotesImage(properties)
        return "done"

    def __saveSetupNotesImage(self, properties={}):
        """
        Copy the setup panel image's file to the notes image's folder
        renaming it accordingly
        """
        log('save note file')
        if properties["taskIndex"] != "":
            mode = Mode(properties.get('show', None), properties.get('sequence', None))
            # Get the panel image file's path
            panelImagePath = mode.get(Recipe.COMPED_FILE, properties)

            # Set the notes image file's path
            notesImagePath = mode.get(Recipe.NOTES_IMAGES_FILE, properties)

            # Set the notes images' folder path
            notesImageFolderPath = mode.get(Recipe.NOTES_IMAGES_FOLDER, properties)

            # Check the notes images' folder
            mode = 0
            if os.access(notesImageFolderPath, mode) == 0:
                os.mkdir(notesImageFolderPath)

            # Copy the panel image's file to the notes folder renaming it
            shutil.copy(panelImagePath, notesImagePath)

    @cherrypy.expose
    def editSetupNotesImage(self, **properties):
        """
        Take the data from the post and import the notes task
        image file in photoshop
        """
        if properties["taskIndex"] != "":
            PsdUtils().createPhotoshopFileForNote(properties)
        return "done"

    @cherrypy.expose
    def reloadSetupNotesImage(self, path):
        """
        Tell the client to reload the note images
        """
        log('reloading notes')
        self.addFeedback("reloadImages", [path])
        return "done"

    @cherrypy.expose
    def getRecipeKeyNumber(self, show, sequence, beat, setup, version):
        recipe = Recipe(show, sequence, beat, setup, version)
        return "%s" % recipe.getKeyNumber(True)

    @cherrypy.expose
    def saveGlobalError(self, globalErrorString=None):
        """
        Take the data from the post and save it
        """
        self.__saveGlobalError(globalErrorString)
        return "done"

    def __saveGlobalError(self, globalErrorString=None):
        """
        Save the global error to the log
        """
        if globalErrorString:
#            log("GLOBAL ERROR\n %s" % globalErrorXMLS, isError=True, email=True)
            log(globalErrorString.replace('\n', '\n<br>'), isError=True, email=True)

    @cherrypy.expose
    def playEditorialQuickTimeMovie(self, show, sequence, movFile):
        """
        Play the editorial quicktime's movie in the platform video's player
        """

        movFolder = Mode(show, sequence).get("[editorialMOVFolder]", )
        movPath = movFolder + "/" + movFile
        if self.fileService.exists(movPath):
            movPath = self.repath.localize(movPath)
            if os.environ["FLIX_PLATFORM"] == flix.WINDOWS:
                movPath = movPath.replace("/", "\\")

            command = Mode().get("[quickTimeCommand]")

            OSUtils.run(command + " " + movPath)

        return "done"

    @cherrypy.expose
    def getEditorialQuickTimeMoviePath(self, show, sequence, movFile):
        """
        Return the editorial quicktime's movie full path
        """
        movFolder = Mode(show, sequence).get("[editorialMOVFolder]")
        movPath = movFolder + "/" + movFile
        if self.fileService.exists(movPath):
            return movPath
        else:
            return ""

    def validateFilename(self, filename):
        if filename == '':
            return 'blank'
        valid_chars = '-_. abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        newFilename  = ''.join(c for c in filename if c in valid_chars)
        return newFilename


    @cherrypy.expose
    def getEditSetupsDifference(self, show, sequence, branch, version, versionToCompare, **properties):
        """
        Return the difference in the setups between the two edit versions
        """
        setupsDiffXML = EditUtils.getEditSetupsDifferenceXML(show, sequence, branch, version, versionToCompare)
        output = ET.tostring(setupsDiffXML)

#        print "ServerFlixFunctions - getEditSetupsDifference output:\n", output

        return output

    @cherrypy.expose
    def runInMaya(self, command, **properties):
        """
        run a command within maya
        """
#        if MAYA_VERSION is '':
#            log('Maya not running')
#            return
        c = properties['toMaya']
        maya.utils.executeInMainThreadWithResult(c)

    @cherrypy.expose
    def getFlixConnectURL(self):
        """
        Return the url to connect to the flixConnect server
        """
        output = "http://" + Mode().get("[flixConnectServer]") + ":" + Mode().get("[flixConnectPort]") + "/"

#        print "ServerFlixFunctions - getFlixConnectURL url:", output

        return output

    @cherrypy.expose
    def getPathExists(self, pathName, **properties):
        """
        Return if the pathName exists
        """
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        fullPath = mode.get(pathName, properties)
        output = str(os.path.exists(fullPath))

#        print "ServerFlixFunctions - getFlixConnectURL url:", output

        return output

    @cherrypy.expose
    def getSequenceBranches(self, show, sequence):
        """
        Return the sequence branches' list
        """
        branchesXML = XMLUtils.getXMLElementForClass("SequenceBranches")
        mode = Mode(show, sequence)
        editorialFolder = mode.get("[editorialFolder]")
        # Default Branch
        branchXML = ET.Element("Branch")
        branchXML.attrib["name"] = mode.get("[defaultBranch]")
        branchesXML.append(branchXML)

        if self.fileService.exists(editorialFolder):
            # Other branches
            matches = mode.getMatches("[editorialFLEBranchFolder]", {"branch":"*"})
            matches.sort(key=lambda match:match['branch'].lower())
            if len(matches) > 0:
                for i in range(0, len(matches)):
                    branchXML = ET.Element("Branch")
                    branchXML.attrib["name"] = str(matches[i]['branch'])
                    branchesXML.append(branchXML)

        output = ET.tostring(branchesXML)

#        print "ServerFlixFunctions - getSequenceBranches output:", output

        return output

    @cherrypy.expose
    def getNoteFileName(self, show, sequence, id):
        """
        Return the note's file name
        """
        idPadded = self.__getPaddedId(id)
        fileName = Mode(show, sequence).get("[noteBaseName]", {"id":idPadded})

#        log("getNoteFileName id: %s fileName: %s" % (id, fileName))

        return fileName


    def __getPaddedId(self, id):
        """
        Return the padded id string
        """
        paddedId = str(id).zfill(4)
        return paddedId

    @cherrypy.expose
    def getSetupNotesFilePath(self, **properties):
        """
        Return the setup notes' file path
        """
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        filePath = mode.get("[recipeNotesFile]", properties)
        return filePath

    @cherrypy.expose
    def editNote(self, **properties):
        """
        Return the setup notes' file path
        """
        mode = Mode(properties.get('show', None), properties.get('sequence', None))
        properties['name'] = 'panelNotes'

        loadedPath       = mode.get('[dictionaryLocalFile]', properties)
        changedPath      = mode.get('[dictionaryMasterFile]', properties)
        setupLabel       = mode.get('[recipeLabel]', properties)

        noteFile = mode.get("[noteBaseName]", properties) + '.png'
        compFile = mode.get("[recipeCompedFile]", properties)

        for i in range(5):
            if self.fileServiceLocal.exists(noteFile):
                psdUtils = PsdUtils()
                psdUtils.editNote(compFile, noteFile, setupLabel, changedPath, loadedPath)
                break
            time.sleep(1)

        # Update the note db that the note has been updated
        lastChangedTable = self.dictionaryCache.getMasterTableInMemory(changedPath)
        lastLoadedTable  = self.dictionaryCache.getLocalTableInMemory(loadedPath)

        currentTime = math.floor(time.time())

        lastChangedTable[setupLabel] = currentTime
        lastLoadedTable[setupLabel] = currentTime

        self.dictionaryCache.storeMasterValue(changedPath, setupLabel, currentTime)
        self.dictionaryCache.storeLocalValue(loadedPath, setupLabel, currentTime)

        flix.utilities.log.log('Updated note saved')
        return

    @cherrypy.expose
    def getMP3License(self, a, b):
        return self.getThirdPartyLicense('mp3', a, b)

    @cherrypy.expose
    def getThirdPartyLicense(self, t, a, b):
        try:
            license = flix.utilities.thirdPartyLicense.ThirdPartyLicense(t).generateLicense(a, b)
            return license
        except Exception, e:
            log('Could not generate License %s' % e, isError=True)
        return ''

    @cherrypy.expose
    def listMP3Licenses(self, a, b):
        return ''

    @cherrypy.expose
    def reloadNote(self, path, setupLabel, changedPath, loadedPath):
        log('Reloading the note %s' % path, isInfo=True)
        self.fileServiceLocal.refreshCache(path)
        self.fileService.copyFromLocal(path, True)
        self.addFeedback('reloadNote', '')

        # Update the note db that the note has been updated
        lastChangedTable = self.dictionaryCache.getMasterTableInMemory(changedPath)
        lastLoadedTable  = self.dictionaryCache.getLocalTableInMemory(loadedPath)

        currentTime = math.floor(time.time())

        lastChangedTable[setupLabel] = currentTime
        lastLoadedTable[setupLabel] = currentTime

        self.dictionaryCache.storeMasterValue(changedPath, setupLabel, currentTime)
        self.dictionaryCache.storeLocalValue(loadedPath, setupLabel, currentTime)


    @cherrypy.expose
    def testPub(self, sessionInfo):
        log(sessionInfo, isInfo=True)

    @cherrypy.expose
    def testMessages(self,count=100):
        for i in range(0, int(count)):
            self.addFeedback('testMessages', str(i))
        self.addFeedback('testMessages', '0')

    @cherrypy.expose
    def testGetInfo(self):
        # to run this test navigate to: http://127.0.0.1:35890/core/testGetInfo
        serviceClass = "%s.%s"%(self.__module__,self.__class__.__name__)
        serviceMethod = 'returnGetInfo'
        log('ServerFlixFunctions.testGetInfo: servceiClass = %s' % serviceClass, isInfo=True)
        log('ServerFlixFunctions.testGetInfo: serviceMethod = %s' % serviceMethod, isInfo=True)
        log('ServerFlixFunctions.testGetInfo: locals = %s' % str(locals()), isInfo=True)
        log('ServerFlixFunctions.testGetInfo: calling getSessionInfo', isInfo=True)
        ClientCommands().getSessionInfo(locals(), serviceClass, serviceMethod)

    def returnGetInfo(self, *kargs):
        log('ServerFlixFunctions.returnGetInfo: %s' % str(kargs))


    @cherrypy.expose
    def selectNextPanel(self):
        self.addFeedback('selectNextPanel', [])

    @cherrypy.expose
    def selectPreviousPanel(self):
        self.addFeedback('selectPreviousPanel', [])


