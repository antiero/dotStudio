from urllib2put import put
from urllib2 import Request, urlopen, HTTPError, URLError
import os
import json
import mimetypes
import urllib
import logging
from frameio_exporter.core import FIOJsonRequest

class UploadTask:
    """Defines an Upload connected to an established frame.io API Session"""

    def __init__(self, filepaths, frameioUserSession, folderid=''):
        """"Constructs the Upload based on: 
                Args:
            filepaths (list): paths of the files to upload
            frameiosession (Session): an already established frameio Session
            folderid (string): folder to upload to
                Defaults to the session's current project's root folder"""
        self.filepaths = filepaths

        logging.info("Upload: Got filepaths: %s" % self.filepaths)

        self.session = frameioUserSession
        self.projectid = self.session.get_project_id()
        if folderid == '':
            self.folderid = self.session.get_root_folder_key()
        else:
            self.folderid = folderid

        self.user_id = self.session.get_user_id()
        self.token = self.session.get_token()
        self.FileReferenceID = {}
        self.multipart_urls = {}
        self.filedata = {}
        
    def __str__(self):
        return json.dumps(self.filedata , indent=4, separators=(',', ': ') )
        
    def upload(self):
        """Invokes all steps to upload all the files given at construction """
        self.inspectFiles()
        self.createFileReference()
        for path in self.multipart_urls.keys():
            for i in xrange( self.getPartcount(path) ):
                self.uploadpart(path,i)
            self.mergeparts(path)
            self.workerthread(path)
        
    def getPartcount(self, path):
        """Returns the count of the uploadparts for the given file """
        return self.filedata[path]['parts']

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
    
    def inspectFile(self, path):
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

    def inspectFiles(self):
        """Inspects all the files. """
        for path in self.filepaths:
            self.inspectFile(path)
        
    def createFileReference(self):
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

        print "Sending file_references request with Dict: ", str(values)

        request = FIOJsonRequest('https://api.frame.io/folders/%s/file_references' % self.folderid, data=values)
        response_body = urlopen(request).read()

        print "File Reference Response:" + str(response_body)

        uploaddata = json.loads(response_body)
        logging.info(uploaddata.get('messages' , [''])[0])
        for path in self.filedata.keys():
            self.multipart_urls[path] = uploaddata['file_references'][ index[path] ]['multipart_urls']
            self.FileReferenceID[path] = uploaddata['file_references'][ index[path] ]['id']

        return self.FileReferenceID
        
    def uploadpart(self, path, partindex):
        """Uploads the given part of the given file. """
        in_file = open(path, "rb")
        url = self.multipart_urls[path][partindex]
        offset = partindex * self.chunksize()
        in_file.seek(offset)
        datachunk = in_file.read( self.chunksize() )
        in_file.close()
        values = { 'part_num' : partindex , 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid  }
        try:
            put(urllib.unquote( url ), datachunk, self.filedata[path]['filetype'])
            request = FIOJsonRequest('https://api.frame.io/file_references/%s/part_complete' %  self.FileReferenceID[path], data=values)
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            print 'UPLOAD PART COMPLETED FOR: ' + path + ': ' + url
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
            request = FIOJsonRequest('https://api.frame.io/file_references/%s/merge_parts' % self.FileReferenceID[path], data=values)
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
            request = FIOJsonRequest('https://api.frame.io/worker/create_job', data=values)
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            return True
        
    def cancel(self, path):
        """
        Cancels the upload for the given file.
        The cancellation of an upload is very easy. 
        folders/{id}/file_references/delete (id = id of the folder that contains the file_refs) 
        This is is a batch delete method, so a dictionary of file_references can be passed.
        {
        "mid": user id,
        "t": token,
        "aid": project id,
        "file_references" :{"0":{"id":file_ref id},
                            "1":{"id":file_ref id},
                            }
        }        

        """
        if not path in self.FileReferenceID.keys():
            print "cancel returning False"
            return False
        else:
            file_references = {'0' : { 'id' : self.FileReferenceID[path] }}
            values = { 'mid' : self.user_id , 't' :  self.token , 'aid' : self.projectid , 'file_references' : file_references }
            request = FIOJsonRequest('https://api.frame.io/folders/%s/file_references/delete' % self.folderid, data=values)
            response_body = urlopen(request).read()
            responsedata = json.loads(response_body)
            logging.info(responsedata.get('messages' , [''])[0])
            return True
