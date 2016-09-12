# -*- coding: utf-8 -*-


"""
This module offers functions for file and data exchange with the frame.io services via python.
API code contributors Til Strobl (www.movingmedia.de)
"""
import sys
import urllib2put
import json, os, mimetypes, urllib, logging
from urllib2 import Request, urlopen, HTTPError, URLError
from frameio_exporter.auth import check_email_type, AUTH_MODE_EMAIL, AUTH_MODE_OAUTH, BasicLoginHandler, OAuthLoginHandler

class UserSession:
    """Defines an established frame.io API User Session."""
    
    def __init__(self, email):
        """
        A Frame.io User Session object, constructed via an email address.
        A UserSession has a LoginHandler object, to handle authentication
        """

        # A UserSession is initialised with an Email address
        self.email = email

        # This is either a Basic or OAuth type of Login handler.
        self.loginHandler = None
        self.sessionHasValidCredentials = False

        # The Email type is either google or non-google, determines which LoginHandler to use
        self.email_type = None
        

        # This is a Dictionary of userdata,
        #Request('https://api.frame.io/users/user_id/data', data=values, headers=headers)
        self.userdata = {}

        # This needs to be refactored - a User can access multiple Projects
        self.projectid = ""

        # Data pertaining to the User
        self.name = ""
        self.first_name = ""
        self.last_name = ""
        self.link = ""
        self.location = ""
        self.bio = ""
        self.profile_image = ""
        self.role = ""

        # A user owns at least one team. 
        # Each team owns 0 or more projects. 
        # From either a user or project or team object you can always retrieve it´s relationship. 
        # The most interesting attributes in the teams array are: 
        #   members - Get basic data of all users that participate in the team.
        #   projects- Contains the root_folder_key required for uploads to the top level folder.
        #   account - Compare the plan_data with the usage_data to check if a exceeds the account limits.
        self.teams = {}
        self.shared_projects = {}

        
    def __str__(self):
        return json.dumps(self.userdata , indent=4, separators=(',', ': ') )
    
    def getUsername(self):
        """Returns the user user name. """
        return self.email
        
    def get_user_id(self):
        """
        Gets the current user id from the loginHandler.
        """
        return self.loginHandler.frameio_user_id
        
    def get_token(self):
        """
        Gets the current user token from the loginHandler. 
        """
        return self.loginHandler.frameio_token
        
    def get_root_folder_key(self, projectid = ''):
        """Returns the root folder key for the given projectid or the current project of the session. """
        if projectid == '':
            projectid = self.projectid
        for p in self.getProjects():
            if p['id'] == projectid:
                return p['root_folder_key']
    
    def get_project_name(self):
        """Returns the current project name. """
        return self.projectdict()[self.projectid]

    def getTeamMembers(self, teamindex=0):
        # user > teams[index] > members[index] 
        if self.userdata == {}:
            self.reloadUserdata()
        members = self.userdata['user']['teams'][teamindex][members]
        return members
    
    def get_project_id(self):
        """Returns the current project id. """
        return self.projectid
    
    def setProjectid(self, projectid):
        """Sets the current project of the session based on the given id. """
        self.projectid = projectid
    
    def setProject(self, projectname):
        """Sets the current project of the session based on the given name. """
        projectdict = self.projectdict()
        for p in projectdict:
            if projectdict[p] == projectname:
                self.projectid = p

    def reloadUserdata(self):
        """Reloads the userdata from the server"""
        values = {'mid' : self.loginHandler.frameio_user_id, 't': self.loginHandler.frameio_token }
        request = Request('https://api.frame.io/users/%s/data' % self.loginHandler.frameio_user_id, data=json.dumps(values), headers=jsonheader())
        response_body = urlopen(request).read()
        self.userdata = json.loads(response_body)

    def getProjects(self , teamindex = 0):
        """Returns the projectdata for the given teamindex. """
        if self.userdata == {}:
            self.reloadUserdata()
        projects = self.userdata['user']['teams'][teamindex]['projects']
        return projects

    def getTeams(self):
        """Returns the projectdata for the given teamindex. """
        if self.userdata == {}:
            self.reloadUserdata()
        self.teams = self.userdata['user']['teams']
        return self.teams

    def getSharedProjects(self):
        """Returns the projectdata for the given teamindex. """
        if self.userdata == {}:
            self.reloadUserdata()
        self.sharedProjects = self.userdata['user']['shared_projects']
        return self.sharedProjects
        
    def projectdict(self, teamindex = 0):
        """Returns a dict containing { projectid : projectname } for the given teamindex. """
        projects = self.getProjects(teamindex)
        projectdict = {}
        for p in projects:
            projectdict[ p['id'] ] = p['name']
        return projectdict
    
    def createSubfolders(self, namelist, folderid = ''):
        """Creates subfolders to a given folder.
        Args:
            namelist (list): names of the folders to create
            folderid (string): where the subfolders are created.
                Defaults to the current project's root folder 
        Returns:
            list: Dataobjects of the folders created
        """
        if folderid == '':
            folderid = self.get_root_folder_key()
        folders = {}
        i = 0
        for name in namelist:
            folders[str(i)] = {'name' : name}
            i+=1
        values = { 'mid' : self.loginHandler.frameio_user_id , 't' :  self.loginHandler.frameio_token , 'aid' : self.projectid , 'folders' : folders}
        request = Request('https://api.frame.io/folders/%s/folders' % folderid , data=json.dumps(values), headers=jsonheader())
        response_body = urlopen(request).read()
        folderdata = json.loads(response_body)
        return folderdata['folders']


    def getFolderdata(self , folderid):
        """Returns the folderdata for the given folderid """
        values = { 'mid' : self.loginHandler.frameio_user_id , 't' :  self.loginHandler.frameio_token , 'aid' : self.projectid }
        request = Request('https://api.frame.io/folders/%s' % folderid , data=json.dumps(values), headers=jsonheader())
        response_body = urlopen(request).read()
        folderdata = json.loads(response_body)
        return folderdata['folder']
    
    def getSubfolderdict(self, folderid):
        """Returns a dict containing { folderid : foldername } for the given folderid. """
        folderdata = self.getFolderdata(folderid)
        subfolders = {}
        for folder in folderdata['folders']:
            subfolders[folder['id']] = folder['name']
        return subfolders

    def getFileReference(self, FileReferenceID):
        """Returns data for the given FileReferenceID"""
        FileReference = FileReference(FileReferenceID,self)
        return FileReference
     
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
            request = Request('https://api.frame.io/projects/%s/collaborators' % self.projectid , data=json.dumps(values), headers=jsonheader())
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
        
    def writeCommentcsv(self, csvpath):
        csvpath = os.path.abspath(csvpath)
        commentdict = self.getComments()
        csvfile = open(csvpath, 'w')
        for timestamp in sorted(commentdict.keys()):
            for commment in commentdict[timestamp]:
                commentline = ';'.join([str(timestamp)] + commment)
                csvfile.write(commentline.encode('utf-8') + '\n')
        csvfile.close()
        
class Upload:
    """Defines an Upload connected to an established frame.io API Session"""

    def __init__(self, filepaths, frameiosession, folderid=''):
        """"Constructs the Upload based on: 
                Args:
            filepaths (list): paths of the files to upload
            frameiosession (Session): an already established frameio Session
            folderid (string): folder to upload to
                Defaults to the session's current project's root folder"""
        self.filepaths = filepaths

        logging.info("Upload: Got filepaths: %s" % self.filepaths)
        self.projectid = frameiosession.get_project_id()
        if folderid == '':
            self.folderid = frameiosession.get_root_folder_key()
        else:
            self.folderid = folderid
        self.user_id = frameiosession.get_user_id()
        self.token = frameiosession.get_token()
        self.FileReferenceID = {}
        self.multipart_urls = {}
        self.filedata = {}
        
    def __str__(self):
        return json.dumps(self.filedata , indent=4, separators=(',', ': ') )
        
    def upload(self):
        """Invokes all steps to upload all the files given at construction """
        self.inspectfiles()
        self.FileReference()
        for path in self.multipart_urls.keys():
            for i in xrange( self.getPartcount(path) ):
                self.uploadpart(path,i)
            self.mergeparts(path)
            self.workerthread(path)
        
    def getPartcount(self, path):
        """Returns the count of the uploadparts for the given file """
        return self.filedata[path]['parts']
    
    def getFileReferenceID(self, path):
        """Returns the count of the FileReferenceID for the given file """
        return self.FileReferenceID[path]

    def chunksize(self):
        """Returns the chunksize for multipart upload """
        return 1024*1024*50

    def sizeof_fmt(self, num, suffix='B'):
        """Returns the size in a readable form"""
        for unit in ['','K','M','G','T','P','E','Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)
    
    def inspectfile(self, path):
        """Inspects the given file and saves the data internally. """
        name = os.path.basename(path)
        metadata = ''
        user_stars = {}
        filetype = mimetypes.guess_type(path)[0]
        if filetype == None:
            filetype = 'application/octet-stream'
        filesize = os.stat(path).st_size
        detail = self.sizeof_fmt(filesize)
        is_multipart = True
        parts = filesize / self.chunksize() + 1
        self.filedata[path] = { 'name' : name , 'metadata' : metadata , 'user_stars' : user_stars ,'filetype' : filetype , 'filesize' : filesize, 'detail' : detail , 'is_multipart' : is_multipart , 'parts' : parts }

    def inspectfiles(self):
        """Inspects all the files. """
        for path in self.filepaths:
            self.inspectfile(path)
        
    def FileReference(self):
        """Creates the FileReferences on the server for all the files to upload.
        Returns a FileReference dictionary, e.g. {'/path/to/movie.mov': u'TiEXNSDx'}
        """
        file_references = {}
        index = {}
        i = 0
        for path in self.filedata.keys():
            file_references[str(i)] = self.filedata[path]
            index[path] = i
            i+=1
        values = { 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid , 'file_references' : file_references  }
        request = Request('https://api.frame.io/folders/%s/file_references' % self.folderid, data=json.dumps(values), headers=jsonheader())
        response_body = urlopen(request).read()
        uploaddata = json.loads(response_body)
        logging.info(uploaddata.get('messages' , [''])[0])
        for path in self.filedata.keys():
            self.multipart_urls[path] = uploaddata['file_references'][ index[path] ]['multipart_urls']
            self.FileReferenceID[path] = uploaddata['file_references'][ index[path] ]['id']

        # Til's code originally returned the uploaddata but we're more interested in returnin the FileReference 
        #return uploaddata

        return self.FileReferenceID
        
    def uploadpart(self, path, partindex):
        """Uploads the given part of the given file. """
        in_file = open(path, "rb")
        url = self.multipart_urls[path][partindex]
        offset = partindex * self.chunksize()
        in_file.seek(offset)
        datachunk = in_file.read( self.chunksize() )
        in_file.close()
        values = { 'part_num' : partindex , 'mid' : self.user_id , 't' :  self.frameio_token , 'aid' : self.projectid  }
        try:
            urllib2put.put(urllib.unquote( url ), datachunk, self.filedata[path]['filetype'])
            request = Request('https://api.frame.io/file_references/%s/part_complete' %  self.FileReferenceID[path], data=json.dumps(values), headers=jsonheader())
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            logging.info('part completed for ' + path + ': ' + url)
            return True
        except (URLError, KeyError) as c:
            logging.info('upload failed for ' + path + ': ' + url)
            logging.info('https://api.frame.io/file_references/%s/part_complete' %  self.FileReferenceID[path] )
            logging.info(json.dumps(values , indent=4, separators=(',', ': ') ))
            logging.info(self.filedata[path]['filetype'] + ' ' + urllib.unquote( url ))
            logging.info(c)
            self.FileReferenceID.pop(path)
            return False
            
    def mergeparts(self, path):
        """Merges all the parts for a given file. """
        if not path in self.FileReferenceID.keys():
            print "mergeparts returning False"
            return False
        else:
            logging.info( 'Merging parts' ) 
            values = { 'num_parts' : 'dummy' , 'upload_id' : 'dummy' , 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid }
            request = Request('https://api.frame.io/file_references/%s/merge_parts' % self.FileReferenceID[path] , data=json.dumps(values), headers=jsonheader())
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            return True
        
    def workerthread(self, path):
        """Starts the worker thread for the given file """
        if not path in self.FileReferenceID.keys():
            print "workerthread returning False"
            return False
        else:
            logging.info( 'Starting worker thread' ) 
            values = { 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid , 'process' : 'new-upload' , 'file_reference_id' : self.FileReferenceID[path]  }
            request = Request('https://api.frame.io/worker/create_job' , data=json.dumps(values), headers=jsonheader())
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            return True
        
    def cancel(self, path):
        """Cancels the upload for the given file. """
        if not path in self.FileReferenceID.keys():
            print "cancel returning False"
            return False
        else:
            file_references = {'0' : { 'id' : self.FileReferenceID[path] }}
            values = { 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid , 'file_references' : file_references }
            request = Request('https://api.frame.io/folders/%s/file_references/delete' % self.folderid , data=json.dumps(values), headers=jsonheader())
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            return True

def jsonheader():
    return {'Content-Type': 'application/json'}

def uploadlist(path):
    uploadfile = open(path)
    uploadlist = []
    for l in uploadfile.readlines():
        l = l.replace('\\' , '\\\\').rstrip('\n')
        uploadlist.append(os.path.abspath(l))

    return uploadlist

# ANT: Command line mode will now not work as we can't do OAuth Login from command-line
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("-u",action="store", required=True,
                    help=u"frame.io Username")
    p.add_argument("-pw",action="store", required=True,
                    help=u"password")
    p.add_argument("-p",action="store", required=True,
                    help=u"project id")
    p.add_argument("-upload",action="store",
                    help=u"uploadlist as file in txt format")
    p.add_argument("-comments",action="store",
                    help=u"print comments for given FileReferenceID")
    p.add_argument("-csv",action="store",
                    help=u"store comments in given csv file")
    p.add_argument("--log",action="store_true",
                help=u"turn on logging")
    p.add_argument("--loglevel",type=int, default=logging.INFO,
                help=u"loglevel 10 (DEBUG) bis 50 (CRITICAL)")

    args=p.parse_args()

    if args.log:
        logging.basicConfig(level=args.loglevel,
                            format='%(asctime)s %(levelname)-8s %(message)s',
                            filename='frameio.log',
                            filemode='a')
        logging.info("Logging requested, loglevel=%d",args.loglevel)
            
    user = args.u
    pw = args.pw
    project = args.p 

    frameiosession = UserSession(email)
    frameiosession.setProjectid(project)
    
    if args.upload != None:
        uploads = uploadlist(os.path.abspath(args.upload))
        upload = Upload( uploads , frameiosession )
        upload.upload()
    if args.comments != None:
        FileReferenceID = args.comments
        FileReference = frameiosession.getFileReference(FileReferenceID)
        if args.csv != None:
            FileReference.writeCommentcsv(args.csv)
        else:
            print FileReference.getComments()
