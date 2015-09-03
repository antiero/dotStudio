import sys
import os
import hiero.core

cwd = os.path.dirname(os.path.realpath(__file__))
print "CWD: " + str(cwd)
rootDir = os.path.abspath(os.path.join(cwd))
# Add requests module to sys path 
# https://github.com/kennethreitz/requests
sys.path.append(rootDir)

thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)

import frameio
from FnFrameioDelegate import FrameioDelegate
#import FnFrameioUI

hiero.core.frameioDelegate = FrameioDelegate()

# Google Auth Details
GOOGLE_CLIENT_ID = "633379315148-1hvjtjqkg2st6ovsgflgasoimnr0piel.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "kVptxPJ8CwpxCqXGBeLnFSy6"