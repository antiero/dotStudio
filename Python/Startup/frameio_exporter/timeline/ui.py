# -*- coding: utf-8 -*-


"""
Interaction with frame.io from within Nuke Studio

Usage:

nuke2frameio by Til Strobl, www.movingmedia.de
"""
from PySide import QtGui
from PySide.QtCore import Qt, QUrl, QRegExp, QSize
import hiero.core
from hiero.ui import activeView, createMenuAction
import os
import nuke
from frameio_exporter.core.paths import gIconPath

class FnTimelineFrameioMenu(QtGui.QMenu):
    def __init__(self):
        """
        A right-click menu that is added to the Hiero/Studio right-click menu
        """
        QtGui.QMenu.__init__(self, "Frame.io", None)
        hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)

        self._actionUploadSelection = createMenuAction("Login...", self.showFrameIODialog, icon=os.path.join(gIconPath, "logo-unconnected.png"))
        self._showSelectionInFrameIOAction = createMenuAction("Open in Frame.io", self.openSelectedInFrameIO, os.path.join(gIconPath, "frameio.png"))
                                                                
        self.addAction(self._showSelectionInFrameIOAction)
        self.addAction(self._actionUploadSelection)

    def showFrameIODialog(self):
        """
        Presents the Frame.io Widget with the active selection of Bin items
        (selection currently not used)
        """
        view = activeView()

        if not view:
            return

        selection = None
        if hasattr(view, 'selection'):
            selection = view.selection()

        nuke.frameioDelegate.showFrameioDialog()

    def addAnnotationsForSelection(self):
        """
        Adds the latest annotations stored from Frame.io for the selected items
        """
        taggedSelection = self.getFrameioTaggedItemsFromActiveView()

        for item in taggedSelection:
            commentdict = filereference.getComments()
            if not commentdict:
                return None


    def getFrameioTaggedItemsFromActiveView(self):
        """
        Returns a list of items in active Selection which are Tagged with Frame.io Tags
        """
        taggedSelection = []
        view = hiero.ui.activeView()
        if not view or not hasattr(view, 'selection'):
            return

        if isinstance(view, hiero.ui.BinView):
            taggedSelection = [item.activeItem() for item in view.selection() if hasattr(item, 'activeItem') and hasattr(item.activeItem(), 'tags')]
        else:
            taggedSelection = [item for item in view.selection() if hasattr(item, 'tags')]

        return taggedSelection


    def openSelectedInFrameIO(self):
        """
        Tries to open the selected item in Frame.io
        """

        taggedSelection = self.getFrameioTaggedItemsFromActiveView()

        # Get Tags which contain a frameio_filereferenceid key
        for item in taggedSelection:
            filereferenceid = nuke.frameioDelegate.getLatestFileReferenceIDForProjectItem(item)

            if filereferenceid:
                try:
                    nuke.frameioDelegate.openFilereferenceIdInFrameIO(filereferenceid)
                except:
                    print "Unable to open browser for filereferenceid %s" % filereferenceid


    def eventHandler(self, event):
        # Check if this actions are not to be enabled

        if not hasattr(event.sender, 'selection'):
          # Something has gone wrong, we shouldn't only be here if raised
          # by the timeline view which will give a selection.
          return

        event.menu.addMenu(self)