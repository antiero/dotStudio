import json, os, sys, urllib2
import xml.etree.ElementTree as ET

class FlixConnection(object):

    """A Flix Connection object for communicating to the Flix server"""

    def __init__(self):
        self.port = int(os.environ.get('FLIX_PORT', 35980))
        self.baseUrl = os.environ.get('FLIX_IP_ADDRESS', "http://127.0.0.1")
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