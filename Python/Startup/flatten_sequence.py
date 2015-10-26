# flatten_sequence.py - creates a single-track, flattened version of multi-track timeline
# Installation: Copy to > $HIERO_PLUGIN_PATH/Python/Startup
import hiero.core
import hiero.ui
import nuke
from PySide import QtGui
from PySide import QtCore
from foundry.ui import ProgressTask

# TO-DO:
# 1) Handle retimes properly - DONE
# 2) Handle Transitions
# 3) Handle Soft-effects
# 4) Consider audio flattening?
# 5) Collapse other Tracks - BLOCKED, currently hiding instead.
# 6) Handles - DONE
# 7) progressTask bars - DONE
# 8) Blend Tracks - HA! Good luck.

class FlattenAction(QtGui.QAction):
    def __init__(self):
        """
        QAction to create a single-track, flattened version of multi-track timeline in Hiero/NukeStudio
        """
        QtGui.QAction.__init__(self, "Flatten Sequence", None)
        self.triggered.connect(self.createFlattenedTrackFromActiveSequence)
        hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
        hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)

    def createFlattenedTrackFromActiveSequence(self):

        """
        Creates a new Video track for the active Sequence with all visible Video Tracks flattened to a single Track
        """

        view = hiero.ui.activeView()

        if not hasattr(view, 'sequence'):
            return

        sequence = view.sequence()
        tracksToHide = sequence.videoTracks()

        selection = view.selection()
        includedItems = None
        if len(selection)>1:
            flattenSelection = nuke.ask("Flatten Selection Only?")
            if flattenSelection:
                includedItems = selection

        if sequence:
            proj = sequence.project()

            flattenedVideoTrack = self.makeFlattenedVideoTrackFromSequence(sequence, includedItems=includedItems)

            if flattenedVideoTrack:
                with proj.beginUndo("Add Flattened Track"):
                    sequence.addTrack(flattenedVideoTrack)

                    for track in tracksToHide:
                        track.setEnabled(False)


    def makeFlattenedVideoTrackFromSequence(self, sequence, includedItems = None, trackName = 'Flattened'):
        """
        Adds a 'Flattened' Video Track to the sequence. Returns the Flattened Track.
        """

        # Create a placeholder Video Track
        tempSequence = hiero.core.Sequence("temp")
        razorTrack = hiero.core.VideoTrack("RazorTrack")
        flattenedTrack = hiero.core.VideoTrack(trackName)
        tempSequence.addTrack(razorTrack)

        # Build a list of shots which are visible for the Sequence
        shotOccuranceDictionary = self.buildVisibleShotListForSequence(sequence, includedItems=includedItems)

        numShots = len(shotOccuranceDictionary)
        progressTask = ProgressTask("Flattening Sequence...")
        count = 1
        for shot in shotOccuranceDictionary.keys():
            shotOccurances = shotOccuranceDictionary[shot]
            for occurance in shotOccurances:
                t0 = occurance[0]
                srcIn = shot.mapTimelineToSource(t0)
                t1 = occurance[1]
                srcOut = shot.mapTimelineToSource(t1)
                originalShot = shot.copy()

                # First add the shot to a dummy Track for razor purposes
                shotToCut = razorTrack.addItem(originalShot)

                # Clear the unused ranges out...
                razorTrack.clearRange(0, t0-1, False)
                razorTrack.clearRange(t1+1, sequence.duration(), False)

                # Now move the cut shot down to the flattened Track
                shotForFlattenTrack = shotToCut.copy()

                flattenedTrack.addItem(shotForFlattenTrack)

                # And delete the shot on the razorTrack..
                for item in razorTrack.items():
                    razorTrack.removeItem(item)

            # Make the progressTask bars update
            progressTask.setProgress(int(100.0*(float(count)/float(numShots))))
            count += 1

            if progressTask.isCancelled():
                del(tempSequence)
                del(razorTrack)
                del(progressTask)
                return None         

        # Clean up unused items so they don't hang around...
        del(tempSequence)
        del(razorTrack)
        del(progressTask)

        return flattenedTrack

    def buildVisibleShotListForSequence(self, sequence, includedItems = None):

        """
        Walks the timeline and returns a list of under the playhead (including those with unconnected media)
        @param sequence: a hiero.core.Sequence object to flatten
        @param includedItems: (optional) - an optional list of included items which to consider for the flattened track
        
        @return: A dictionary of visible shot occurances in the sequence
        """

        # If in Points are set, only flatten the sequence between these values
        try:
            T0 = sequence.inTime()
        except:
            T0 = 0

        try:
            T1 = sequence.outTime()
        except:
            T1 = sequence.duration()

        # shotOccuranceDictionary structure is laid out like this:
        # {'shot1': [ [instance1_In, instance1_tOut], [instance2_In, instance2_tOut]... ] }

        shotOccuranceDictionary = {}

        # includedItems can contain either Tracks or TrackItems.
        # At present selection for Tracks AND TrackItems is not possible in the GUI.

        includedTrackItems = None
        if includedItems:
            if isinstance(includedItems[0], (hiero.core.VideoTrack)):
                # Temporarily Hide any tracks which are not in the includedSelection
                videoTracks = sequence.videoTracks()
                for track in videoTracks:
                    if track not in includedItems:
                        track.setEnabled(False)
                        sequence.editFinished()
            else:
                includedTrackItems = [item for item in includedItems if isinstance(item, hiero.core.TrackItem)]
                T0 = min([item.timelineIn() for item in includedTrackItems])
                T1 = max([item.timelineOut() for item in includedTrackItems])

        progressTask = ProgressTask("Analysing Sequence...")

        # This loop is pretty ineffecient.. just traverses every single frame. 
        # There may be large gaps with no shots etc.
        # Would be more efficient to use sets and some smarter maths.
        # We ignore the 'See through missing media' method and pick the top-most, enabled piece of media, (even missing media)
        for t in range(T0, T1):
            # This returns a tuples of possible shots at time slice t
            shotsAtT = sequence.trackItemsAt(t)

            if len(shotsAtT)>0:
                # From these, prune any shots on Tracks whichh are disabled (not visible)
                enabledShots = [shot for shot in shotsAtT if shot.parentTrack().isEnabled() and shot.isEnabled()]

                # Then sort by video track index, and pick the shot with highest index
                sortedShots = sorted(enabledShots, key=lambda shot: shot.parentTrack().trackIndex(), reverse=True)

                if len(sortedShots)>=1:
                    visibleShot = sortedShots[0]

                    # Bail out of this loop if the shot's not in the selection
                    if includedTrackItems and visibleShot not in includedTrackItems:
                        continue

                    if visibleShot not in shotOccuranceDictionary.keys():
                        shotOccuranceDictionary[visibleShot] = [[t,t]]
                    else:
                        if shotOccuranceDictionary[visibleShot][-1][1] == t-1:
                            # We are still in a concurrent shot, increase its out point to t
                            shotOccuranceDictionary[visibleShot][-1][1] = t
                        else:
                            # If we're here, we've got a new shot instance, append a new 2-digit list...
                            shotOccuranceDictionary[visibleShot].append([t,t])

            if progressTask.isCancelled():
                del(progressTask)
                return {}

            progressAmount = int(100.0*(float(t-T0)/float(T1-T0)))
            progressTask.setProgress(progressAmount)

        del(progressTask)

        return shotOccuranceDictionary


    def eventHandler(self, event):
        hiero.ui.insertMenuAction( self, event.menu )

flatten = FlattenAction()