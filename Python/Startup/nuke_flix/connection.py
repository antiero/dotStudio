# Nuke Studio <> Connection
import json
import os
import sys
import urllib2
import urlparse
import xml.etree.ElementTree as ET

class NukeStudioFlixConnection(object):

    """A NukeStudioFlixConnection <> Flix Connection object for communicating to the Flix server"""

    def __init__(self):
        self.port = int(os.environ.get('FLIX_PORT', 35980))
        self.baseUrl = os.environ.get('FLIX_IP_ADDRESS', "http://127.0.0.1")
        self.flixURL = self.baseUrl+':'+str(self.port)
        self.flixEnv = None
        
        # Setup the envrionment variables to add FLIX to current path
        self.setupPaths()
        

    def setupPaths(self):

        """Sets up the paths required to communicate with FLIX"""
        if not getattr(sys, 'FLIX_PATH_ADDED', False):
            response = self.sendRequestGetResponse('env?format=json')
            if response:
                env = json.loads(response.read())
                self.flixEnv = env
                pysrc = env['FLIX_PYTHONSOURCE_FOLDER']
                print 'Importing flix from %s' % pysrc
                sys.path.append(pysrc)
                sys.path.append(os.path.join(pysrc, 'thirdParty'))
                sys.FLIX_PATH_ADDED = True
            else:
                print 'Unable to import flix module. Check ports are open and Flix is running'        

    def sendRequestGetResponse(self, requestURL):
        """Returns a url response"""
        url = '%s:%s/%s' % (self.baseUrl, self.port, requestURL)
        response = None
        try:
            response = urllib2.urlopen(url, timeout=1)
        except urllib2.URLError as ex:
            raise RuntimeError('Could not reach FLIX. Is it running? (%r)' % ex)
        if response.getcode() != 200:
            raise RuntimeError('Got %s response trying to contact FLIX, cannot use scripts.' % response.getcode())

        return response

    def sendRequestAndReadData(self, requestURL):
        """Conveniently just returns the read from the response object"""
        response = self.sendRequestGetResponse(requestURL)
        responseData = response.read()
        return responseData

    def getShowList(self):
        """Returns a list of available FLIX shows as a list"""
        showXML = self.sendRequestAndReadData("core/getShows")
        showNames = []        
        if showXML:
            root = ET.fromstring(showXML)
            shows = root.findall('Show')
            for show in shows:
                showNames+=[show.get('name')]

        return showNames

    def getSequencesForShow(self, show):
        """Returns a list of sequence names for a show as a list"""
        sequencesXML = self.sendRequestAndReadData("core/getSequences/%s" % show)
        sequenceNames = []
        if sequencesXML:
            root = ET.fromstring(sequencesXML)
            sequences = root.findall('Sequence')
            for sequence in sequences:
                sequenceNames+=[sequence.get('name')]

        return sequenceNames

    def getSequenceBranchesForShowAndSequence(self, show, sequence):
        """Return a sequence's branch list"""
        branchesXML = self.sendRequestAndReadData("core/getSequenceBranches/%s/%s" % (show, sequence))
        branchNames = []
        if branchesXML:
            root = ET.fromstring(branchesXML)
            branches = root.findall('Branch')
            for branch in branches:
                branchNames+=[branch.get('name')]

        return branchNames

    def makeImportSequenceRequest(self, show="", sequence="", edlPath="", moviePath="", branch="main", comment="", username=None, importAsStills=True):
        """Send a GET to the correct FLIX endpoint with suitable arguments
        for importing a FLIX sequence.

        :rtype: (str, dict)
        """
        import requests
        # show, sequence, branch, edlFile, movie, comment, username, importAsStills=True, shotgunPub=False):

        if not username:
            os.getenv('USER')

        params = dict(
            show=show,
            sequence = sequence,
            branch=branch,
            edlFile=edlPath,
            movieFile=moviePath,
            comment=comment,
            username = username,
            importAsStills=importAsStills
        )
        url = urlparse.urljoin(self.flixURL, 'core/importNukeStudioSequence')
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise RuntimeError('status code: %s' % response.status_code)
        return url, params        