import sys
import os

cwd = os.path.dirname(os.path.realpath(__file__))

# Append reportlab thirdParty module to the sys path 
# http://www.reportlab.com
thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)
import FnPdfExporter