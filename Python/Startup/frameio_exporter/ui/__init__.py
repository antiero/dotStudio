"""
A shared user interface library for both Nuke timeline and comp modes
"""

from PySide.QtGui import QAction
# This method exists in hiero.ui but we need to share it with Nuke
def createMenuAction(title, method, icon=None):
    action = QAction(title, None)
    action.triggered.connect( method )
    if icon:
    	action.setIcon(icon)
    return action

import FnFrameioUI