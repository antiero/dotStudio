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
from frameio_exporter.core.json_helpers import FIOJsonRequest

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
        request = FIOJsonRequest('https://api.frame.io/users/%s/data' % self.loginHandler.frameio_user_id, data = values)
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
        request = FIOJsonRequest('https://api.frame.io/folders/%s/folders' % folderid , data = values)
        response_body = urlopen(request).read()
        folderdata = json.loads(response_body)
        return folderdata['folders']


    def getFolderdata(self , folderid):
        """Returns the folderdata for the given folderid """
        values = { 'mid' : self.loginHandler.frameio_user_id , 't' :  self.loginHandler.frameio_token , 'aid' : self.projectid }
        request = FIOJsonRequest('https://api.frame.io/folders/%s' % folderid , data = values)
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
