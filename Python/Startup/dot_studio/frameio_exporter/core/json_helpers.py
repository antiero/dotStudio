import json
def jsonheader():
    return {'Content-Type': 'application/json'}

# A wrapper around urllib2.Request to send a Dictionary of data asa JSON Dump
def FIOJsonRequest( url, data = {} ):
	return Request(url, data = json.dumps(data), headers=jsonheader())