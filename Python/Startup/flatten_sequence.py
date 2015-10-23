# flatten.py - creates a single-track, flattened version of multi-track timeline
import hiero.core
import hiero.ui
import nuke
from PySide import QtGui
from PySide import QtCore

# To do:
# 1) Handle retimes properly - DONE
# 2) Handle Transitions
# 3) Handle Soft-effects
# 4) Consider audio
# 5) Collapse Tracks
# 6) Handles
# 7) progressTask bars - DONE
# 8) Blend Tracks

# Consider usign hiero.core.VideoTrack.clearRange to razor on any clips straddling the start and end, and a delete of everything else.
class FlattenAction(QtGui.QAction):
	def __init__(self):
		QtGui.QAction.__init__(self, "Flatten Sequence", None)
		self.triggered.connect(self.createFlattenedTrackFromActiveSequence)
		hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)

	def createFlattenedTrackFromActiveSequence(self):

		"""
		Creates a new Video track for the active Sequence with all visible Video Tracks flattened to a single Track
		"""

		view = hiero.ui.activeView()

		if not hasattr(view, 'sequence'):
			return

		sequence = view.sequence()
		tracksToHide = sequence.videoTracks()

		if sequence:
			flattenedVideoTrack = self.makeFlattenedVideoTrackFromSequence(sequence)

			if flattenedVideoTrack:
				sequence.addTrack(flattenedVideoTrack)

				for track in tracksToHide:
					track.setEnabled(False)


	def makeFlattenedVideoTrackFromSequence(self, sequence, trackName = 'Flattened'):
		"""
		Adds a 'Flattened' Video Track to the sequence. Returns the Flattened Track.
		"""

		# Create a placeholder Video Track
		razorTrack = hiero.core.VideoTrack("RazorTrack")
		flattenedTrack = hiero.core.VideoTrack(trackName)
		sequence.addTrack(razorTrack)

		# Build a list of shots which are visible for the Sequence
		shotOccuranceDictionary = self.buildVisibleShotListForSequence(sequence)

		numShots = len(shotOccuranceDictionary)
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
			count += 1


		# Delete the razorTrack, it's no longer needed...
		sequence.removeTrack(razorTrack)

		return flattenedTrack

	def buildVisibleShotListForSequence(self, sequence):

		"""
		Walks the timeline and returns a list of visible shots.
		Note, at present media which is offline will be treated as translucent, and the shot visible will be used.
		"""
		T = sequence.duration()

		# shotOccuranceDictionary structure is laid out like this:
		# {'shot1': [ [instance1_In, instance1_tOut], [instance2_In, instance2_tOut]... ] }

		shotOccuranceDictionary = {}
		shotList = []

		# We will ignore the See through missing media method and pick the top-most, enabled piece of media, (even missing media)
		for t in range(0, T):
			# This returns a tuples of possible shots at time slice t
			shotsAtT = sequence.trackItemsAt(t)

			if len(shotsAtT)>0:
				# From these, prune any shots on Tracks whichh are disabled (not visible)
				enabledShots = [shot for shot in shotsAtT if shot.parentTrack().isEnabled() and shot.isEnabled()]

				# Then sort by video track index, and pick the shot with highest index
				sortedShots = sorted(enabledShots, key=lambda shot: shot.parentTrack().trackIndex(), reverse=True)

				if len(sortedShots)>=1:
					visibleShot = sortedShots[0]

					if visibleShot not in shotOccuranceDictionary.keys():
						shotOccuranceDictionary[visibleShot] = [[t,t]]
					else:
						if shotOccuranceDictionary[visibleShot][-1][1] == t-1:
							# We are still in a concurrent shot, increase its out point to t
							shotOccuranceDictionary[visibleShot][-1][1] = t
						else:
							# If we're here, we've got a new shot instance, append a new 2-digit list...
							shotOccuranceDictionary[visibleShot].append([t,t])

					if visibleShot not in shotList:
						shotList.append(visibleShot)

		return shotOccuranceDictionary


	def eventHandler(self, event):
		hiero.ui.insertMenuAction( self, event.menu )

flatten = FlattenAction()