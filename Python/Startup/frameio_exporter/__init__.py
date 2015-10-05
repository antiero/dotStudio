import sys
import os
import hiero.core
cwd = os.path.dirname(os.path.realpath(__file__))
rootDir = os.path.abspath(os.path.join(cwd))
# Add requests module to sys path 
# https://github.com/kennethreitz/requests
sys.path.append(rootDir)

thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)

import frameio
from FnFrameioDelegate import FrameioDelegate
hiero.core.frameioDelegate = FrameioDelegate()

from FnFrameioUI import FnFrameioMenu
frameioMenu = FnFrameioMenu()

#import FnFrameioUploadExporter
#import FnFrameioUploadExporterUI
import FnFrameioTranscodeExporter
import FnFrameioTranscodeExporterUI