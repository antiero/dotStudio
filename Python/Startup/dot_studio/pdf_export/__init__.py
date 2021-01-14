# PDF Exporter for Nuke Studio's Export Preset Dialog and Quick Export Bin View UI
import sys
import os
cwd = os.path.dirname(os.path.realpath(__file__))

# Append reportlab thirdParty module to the sys path 
# http://www.reportlab.com
thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)
import FnPdfExporter

# Add the right-click action
action = FnPdfExporter.ExportPdfAction()

# Add the Export Task for the Export dialog
import FnPdfExportTask
import FnPdfExportTaskUI