import core
import ui
import comp
import sys
import os
import nuke
cwd = os.path.dirname(os.path.realpath(__file__))
rootDir = os.path.abspath(os.path.join(cwd))
# Add requests module to sys path 
# https://github.com/kennethreitz/requests
sys.path.append(rootDir)

thirdPartyDir = os.path.abspath(os.path.join(cwd, "thirdParty"))
sys.path.append(thirdPartyDir)

ENV = nuke.env

# For Hiero and Nuke Studio, add the Exporters and UI elements
if ENV['hiero'] or ENV['studio']:
	from timeline.FnFrameioDelegate import FrameioDelegate
	nuke.frameioDelegate = FrameioDelegate()	
	from timeline.ui import FnTimelineFrameioMenu
	timelineFrameioMenu = FnTimelineFrameioMenu()
	import exporters

# Now add comp actions

toolbar = nuke.menu('Nodes')
m = toolbar.addMenu('frame.io', icon='frameio.png')
m.addCommand('Upload selected', 'comp.nuke2frameio.uploadSelected()')
m.addCommand('Load comments', 'comp.nuke2frameio.loadSelectedcomments()')