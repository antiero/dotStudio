# PDF Exporter for Nuke Studio's Export Preset Dialog and Quick Export Bin View UI
import sys
import os
cwd = os.path.dirname(__file__)
sys.path.append(cwd)
# Append reportlab thirdParty module to the sys path 
# http://www.reportlab.com
thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)

import AnPdfExporter
# Add the Export Task for the Export dialog
import AnPdfExportTask
import AnPdfExportTaskUI

# Add the right-click action
action = AnPdfExporter.ExportPdfAction()