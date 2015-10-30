# remove_gaps.py - removes any gaps from a Sequence, Track or selection.
# Installation: Copy to > $HIERO_PLUGIN_PATH/Python/Startup
import hiero.core
import hiero.ui
import nuke
from PySide import QtGui
from PySide import QtCore
from foundry.ui import ProgressTask

class RemoveGapsAction(QtGui.QAction):
    def __init__(self):
        """
        QAction to remove all gaps from a Timeline
        """
        QtGui.QAction.__init__(self, "Remove Gaps", None)
        self.triggered.connect(self.removeGapsFromActiveSelection)
        hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)

    def removeGapsFromActiveSelection(self):

        """
        Remove all gaps from the Active timelin selection
        If selection is:
        None - ALL gaps from unlocked tracks are removed
        Tracks(s) - ALL gaps from selected, unlocked tracks are removed
        Shots(s) - ALL gaps between selected shots, on unlocked tracks are removed
        """

        view = hiero.ui.activeView()

        if not hasattr(view, 'sequence'):
            return

        sequence = view.sequence()
        tracksToHide = sequence.videoTracks()

        selection = view.selection()

        # Determine selection type
        if len(selection):
            self.removeSpaceFromSequence(sequence)

    def removeSpaceFromSequence(self, sequence, includeLocked=False):
        """
        Removes all gaps between shots in a Sequence
        By default, will not move shots on locked tracks. 
        Set includeLocked keyword to 'True' to for ALL tracks.

        @param sequence: hiero.core.Sequence object
        @param includeLocked (optional, default=False): determines whether to remove gaps from Locked tracks (set to True)
        """

        if not includeLocked:
            tracksToInclude = [track for track in sequence.items() if not track.isLocked()]
        else:
            tracksToInclude = [track for track in sequence.items()]

        project = sequence.project()

        #seqBI = sequence.binItem()
        #seqBI.addSnapshot(sequence, "Pre-gap removal")

        for track in tracksToInclude:
            print str(track)
            lastItem = None
            lastOut = 0
            for item in track:
                print str(track)
                outTime = item.timelineOut()+1
                if lastItem != None:

                    inTransition = item.inTransition()
                    outTransition = item.outTransition()

                    gap = item.timelineIn()-lastTime
                
                    if gap != 0:
                        item.move(-gap)

                        # There is currently a bug with move() method for transitions.
                        # We need to set the in and outpoints manually instead.
                        if inTransition:
                            inT = inTransition.timelineIn()
                            outT = inTransition.timelineOut()
                            inTransition.setTimelineIn(inT - gap)
                            inTransition.setTimelineOut(outT - gap)
                        if outTransition:
                            inT = outTransition.timelineIn()
                            outT = outTransition.timelineOut()
                            outTransition.setTimelineIn(inT - gap)
                            outTransition.setTimelineOut(outT - gap)

                        outTime -= gap

                lastItem = item
                lastTime = outTime

        #sequence.editFinished()
        #seqBI.addSnapshot(sequence, "Post-Gap removal")


    def eventHandler(self, event):
        hiero.ui.insertMenuAction( self, event.menu )

flatten = RemoveGapsAction()