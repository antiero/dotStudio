import hiero.core
from PySide2.QtWidgets import QAction

# Longest Shot from Sequence
# Creates a new Sequence which contains Shots with the longest range of frames used across all shots in different sequences

class LongestSequenceFromSelectionAction(QAction):
  
  def __init__(self):
    QAction.__init__(self, "Create Longest Shot Sequence", None)
    self.triggered.connect(self.doit)
    hiero.core.events.registerInterest((hiero.core.events.EventType.kShowContextMenu, hiero.core.events.EventType.kBin), self.eventHandler)
   
  def doit(self):
    selection = list(hiero.ui.activeView().selection())
    sequences = [item.activeItem() for item in selection if isinstance(item.activeItem(),hiero.core.Sequence)]
  
    # For every Sequence, we need to build a list of shots
    # This will assume that the first track is the master track, as if it were from the original EDL
    all_shots = []
    for seq in sequences:
      tracks = seq.videoTracks()
      for track in tracks:
        shots = list(track.items())
        all_shots.extend(shots)

    # We now must determine shots which have the same Source Clip across the selection of Sequences
    clipMatches = {}
    for shot in all_shots:
      print(str(shot))
      clipName = shot.source().name()
      if clipName in clipMatches.keys():
        clipMatches[clipName]+=[{'trackItem':shot,
                                 'clip':shot.source(),
                                 'duration':shot.duration(),
                                 'sourceIn':shot.sourceIn(),
                                 'sourceOut':shot.sourceOut()
                                 }]
      else:
        clipMatches[clipName]=[{'trackItem':shot,
                                 'clip':shot.source(),
                                 'duration':shot.duration(),
                                 'sourceIn':shot.sourceIn(),
                                 'sourceOut':shot.sourceOut()
                                 }]

    longestShots = []
    hiero.core.clipMatches = clipMatches
    for clipName in clipMatches.keys():
      MAX = max([item['duration'] for item in clipMatches[clipName]])
      print('Max duration for Shot: %s is %i' % (str(clipName),MAX))
      
      # Now find the dict inside clipMatches which has this duration
      longestShot = [item['trackItem'] for item in clipMatches[clipName] if item['duration']==MAX]
      longestShots.extend(longestShot)

    longestShots = hiero.core.util.uniquify(longestShots)

    # Attempt to sort the shots based on their timeline in order...
    longestShots = sorted(longestShots, key=lambda shot: shot.timelineIn())

    # Create a new Sequence
    seq2 = hiero.core.Sequence("Longest Shots")
    longestTrack = hiero.core.VideoTrack('Longest')
    seq2.addTrack(longestTrack)
    t0 = 0
    for shot in longestShots:
      newShot = shot.copy()
      newShot.setTimelineIn(t0)
      newShot.setTimelineOut(t0+shot.duration()-1)
      longestTrack.addTrackItem(newShot)
      t0 = t0+shot.duration()
    proj = seq.project()
    root = proj.clipsBin()
    root.addItem(hiero.core.BinItem(seq2))

  def eventHandler(self, event):
    if not hasattr(event.sender, 'selection'):
      return
    
    # Disable if nothing is selected
    selection = event.sender.selection()
    
    selectedSequences = [item.activeItem() for item in selection if hasattr(item, 'activeItem') and isinstance(item.activeItem(),hiero.core.Sequence)]

    self.setEnabled( len(selectedSequences) > 1 )
    event.menu.addAction(self)

action = LongestSequenceFromSelectionAction()