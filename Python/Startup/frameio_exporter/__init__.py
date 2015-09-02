import sys
import os

cwd = os.path.dirname(os.path.realpath(__file__))

# Add thirdparty requests, oauth and httplib2 modules to sys path 
# https://github.com/kennethreitz/requests
thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)