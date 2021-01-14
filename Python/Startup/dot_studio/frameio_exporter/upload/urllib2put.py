'''
Created on 21.08.2015

@author: Til Strobl (www.movingmedia.de)
'''

import urllib2, base64

class PutRequest(urllib2.Request):
    def get_method(self):
        return "PUT"
    
def put(url,data,contenttype):
    url = bytes(url)
    data = bytes(data)
    headers = { 'Content-Type' : contenttype , 'x-amz-acl' : 'private' }
    putrequest=PutRequest(url,data=data , headers=headers)
    response_body = urllib2.urlopen(putrequest).read()
    return response_body