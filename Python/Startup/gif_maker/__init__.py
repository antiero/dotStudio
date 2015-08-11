# GIF Exporter for Hiero+Nuke Studio
import sys
import os
cwd = os.path.dirname(os.path.realpath(__file__))

# Append PIL thirdParty module to the sys path 
# http://www.pythonware.com/products/pil
thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty", "PIL"))
platform = sys.platform

if platform.startswith("darwin"):
	sys.path.append(os.path.join(thirdPartyDir, "mac"))
elif platform.startswith("win"):
	sys.path.append(os.path.join(thirdPartyDir, "win"))
elif platform.startswith("linux"):
	sys.path.append(os.path.join(thirdPartyDir, "linux"))

import FnGIFMaker
# Add the right-click action
action = FnGIFMaker.MakeGIFAction()