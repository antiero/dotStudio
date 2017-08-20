from urllib2 import Request, urlopen
import json
from json_helpers import FIOJsonRequest

class FileReference:
    """Represents an FileReference data object within an established frame.io session"""

    def __init__(self, FileReferenceID, frameiosession):
        """Loads the data for the given id and session on construction. """
        self.FileReferenceID = FileReferenceID
        self.user_id = frameiosession.get_user_id()
        self.token = frameiosession.get_token()
        self.projectid = frameiosession.get_project_id()
        self.FileReferencedata = {}
        self.userdict = {}
        self.userdict[frameiosession.get_user_id()] = frameiosession.getUsername()
        self.messages = []
        self.errors = []
        self.loadData()
        
    def __str__(self):
        return json.dumps(self.FileReferencedata, indent=4, separators=(',', ': ') )
    
    def loadData(self):
        """Load data for the reference from the server. """
        logging.info( 'Sending request: https://api.frame.io/file_references/%s?mid=%s&t=%s&aid=%s' % (self.FileReferenceID , self.user_id, self.token, self.projectid ) ) 
        request = Request('https://api.frame.io/file_references/%s?mid=%s&t=%s&aid=%s' % (self.FileReferenceID , self.user_id, self.token, self.projectid ))
        response_body = urlopen(request).read()
        FileReferencedata = json.loads(response_body)
        self.FileReferencedata = FileReferencedata.get('file_reference', {})
        if 'messages' in FileReferencedata.keys():
            self.messages = FileReferencedata['messages']
        if 'errors' in FileReferencedata.keys():
            self.errors = FileReferencedata['errors']

    def getData(self):
        """Returns the data for the FileReference """
        return self.FileReferencedata
    
    def getSize(self):
        """Returns the size stored in the FileReferencedata """
        return int(self.FileReferencedata['filesize'].split('.')[0])
    
    def exists(self):
        """Returns True if the FileReference exists on the server"""
        return self.FileReferencedata != {}
    
    def identifyUsername(self, userid):
        """Returns the username for the given userid """
        if not userid in self.userdict.keys():
            values = { 'mid' : self.user_id, 't' :  self.token }
            request = FIOJsonRequest('https://api.frame.io/projects/%s/collaborators' % self.projectid , data=values)
            response_body = urlopen(request).read()
            userdata = json.loads(response_body)
            collaborators = userdata['collaborators']
            for collaborator in collaborators:
                self.userdict[collaborator['id']] = collaborator['name']
        return self.userdict[userid]
    
    def getComments(self):
        """Returns comments in a dict: { timestamp : [ [ username , text ] , ... ]"""
        commentdict = {}
        if self.errors != []:
            return False
        comments = self.FileReferencedata['comments']
        for comment in comments:
            timestamp = float(comment['timestamp'])
            username = self.identifyUsername( comment['master_key'] )
            text = comment['text']
            if comment['annotation_object'] == 'JTNullValue':
                draw_data = None
            else:
                draw_data = json.loads(comment['annotation_object']['draw_data'])
            if timestamp in commentdict:
                commentdict[timestamp].append([username, text, draw_data])
            else:
                commentdict[timestamp] = [[username, text, draw_data]]
        return commentdict