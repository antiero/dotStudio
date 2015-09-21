import hiero.core
import hiero.ui
from PySide import QtGui
from PySide.QtCore import Qt

def whereAmI(self, searchType='TrackItem'):
  """returns a list of objects where this Clip is used.
  By default this will return a list of TrackItems where the Clip is used in its project.
  You can return a list of Sequences by specifying the searchType to be 'Sequence'.

  Example usage:

  shotsForClip = clip.whereAmI('TrackItem')
  sequencesForClip = clip.whereAmI('Sequence')
  """
  proj = self.project()

  if searchType not in ('TrackItem','Sequence'):
    print "searchType argument must be 'TrackItem' or 'Sequence'"
    return None

  # Find items in the project with specified searchType 
  searches = hiero.core.findItemsInProject(proj, searchType)

  if len(searches)==0:
    hiero.core.log.info('Unable to find %s in any items of type: %s' % (str(self),str(searchType)))
    return None
  
  # Case 1: Looking for Shots (trackItems)
  clipUsedIn = []
  if isinstance(searches[0],hiero.core.TrackItem):
    for shot in searches:
      if isinstance(self, hiero.core.Clip):
        if shot.source().binItem() == self.binItem():
          clipUsedIn.append(shot)

      elif isinstance(self, hiero.core.TrackItem):
        if shot.source().binItem() == self.source().binItem():
          clipUsedIn.append(shot)

  # Case 2: Looking for Sequence Usage
  elif isinstance(searches[0],hiero.core.Sequence):
      for seq in searches:
        # Iterate tracks > shots...
        tracks = seq.items()
        for track in tracks:
          shots = track.items()
          for shot in shots:
            if isinstance(self, hiero.core.Clip):
              if shot.source().binItem() == self.binItem():
                clipUsedIn.append(seq)
            elif isinstance(self, hiero.core.TrackItem):
              if shot.source().binItem() == self.source().binItem():
                clipUsedIn.append(seq)

  return clipUsedIn

def shots(self):
  return whereAmI(self, searchType="TrackItem")

def sequences(self):
  return whereAmI(self, searchType="Sequence")


def _sequenceShotManifest(self):
  """
  For a Clip or TrackItem, returns a dictionary whose keys are Sequences, 
  and values are TrackItems where the object's source Clip can be found.
  """
  proj = self.project()

  # Find items in the project with specified searchType 
  searches = hiero.core.findItemsInProject(proj, 'Sequence')

  if len(searches)==0:
    hiero.core.log.info('Unable to find %s in any items of type: %s' % (str(self),str(searchType)))
    return {}
  
  manifest = {}
  for seq in searches:
    # Iterate tracks > shots...
    tracks = seq.items()
    for track in tracks:
      shots = track.items()
      for shot in shots:
        if isinstance(self, hiero.core.Clip):
          if shot.source().binItem() == self.binItem():
            if seq not in manifest.keys():
              manifest[seq] = [shot]
            else:
              manifest[seq].append(shot)

        elif isinstance(self, hiero.core.TrackItem):
          if shot.source().binItem() == self.source().binItem():
            if seq not in manifest.keys():
              manifest[seq] = [shot]
            else:
              manifest[seq].append(shot) 

  return manifest

hiero.core.Clip.usageManifest = _sequenceShotManifest
hiero.core.TrackItem.usageManifest = _sequenceShotManifest


# Add shots and sequences method to Clip object
hiero.core.Clip.shots = shots
hiero.core.Clip.sequences = sequences

# Add shots and sequences method to TrackItem object
hiero.core.TrackItem.shots = shots
hiero.core.TrackItem.sequences = sequences


class WhereAmIMenu(object):

  def __init__(self):
      """
      A Where Am I? Menu to the Bin, Timeline/Spreadsheet views, to show where Clips/TrackItems are found in the projcet
      """
      self._whereAmIMenu = QtGui.QMenu("Show in Sequence...")

      # To reduce the right-click show time for large projects, create this menu dynamically when user hovers over menu
      self._whereAmIMenu.aboutToShow.connect(self._createSequenceUsageMenuForActiveView)

      hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)


  def _createShowSequenceActionForSequenceShotList(self, sequenceShotList):
    """
    This is used to populate the QAction list with Sequence names for a single Clip or TrackItem selection.
    sequenceShotList is a list whose first element is a Sequence, and second is a list of TrackItems
    """
    sequence = sequenceShotList[0]
    shot = sequenceShotList[1][0]

    action = QtGui.QAction(sequence.name(), None)
    action.setData(lambda: sequence)

    def _showSequenceTimeline():
      binItem = sequence.binItem()

      if hiero.ui.activeSequence() != sequence:
        hiero.ui.openInViewer(binItem)
      editor = hiero.ui.getTimelineEditor(sequence)
      editor.setSelection(shot)
      cv = hiero.ui.currentViewer()
      T = shot.timelineIn()
      cv.setTime(T)
    
    action.triggered.connect( _showSequenceTimeline )
    return action

  # This generates the Version Up Everywhere menu
  def _createSequenceUsageMenuForActiveView(self):
    self._whereAmIMenu.clear()
    view = hiero.ui.activeView()
    activeSequence = hiero.ui.activeSequence()

    selection = view.selection()

    if isinstance(view, hiero.ui.BinView):
      if len(selection) != 1:
        return      
      selection = selection[0]
      if not hasattr(selection, 'activeItem'):
        return 
      else:
        item = selection.activeItem()
    elif isinstance(view, (hiero.ui.TimelineEditor, hiero.ui.SpreadsheetView)):
      # Some filtering is needed to ensure linked audio/soft effects don't stop us from finding a shot
      # TO-DO: Handle the logic for linked video tracks properly
      videoTrackItemSelection = [item for item in selection if isinstance(item, hiero.core.TrackItem) and item.mediaType() == hiero.core.TrackItem.MediaType.kVideo]

      if len(videoTrackItemSelection) != 1:
        return
      else:
        item = videoTrackItemSelection[0]

    manifest = item.usageManifest()

    # Create a list of actions sorted alphabetically
    for sequenceShotList in sorted( manifest.items(), key = lambda seq: seq[0].name()):
      # 1st element of sequenceShotLost is a Sequence, 2nd is a list of Shots in that Sequence
      # If the Sequence is the currently active one, don't add it to the list, just show other Sequences
      if (sequenceShotList[0] != activeSequence) or (not activeSequence):     
        act = self._createShowSequenceActionForSequenceShotList(sequenceShotList)
        if act not in hiero.ui.registeredActions():
          hiero.ui.registerAction(act)

        self._whereAmIMenu.addAction(act)
  
  # This handles events from the Bin and Timeline/Spreadsheet
  def eventHandler(self, event):
    hiero.ui.insertMenuAction(self._whereAmIMenu.menuAction(), event.menu, after = "foundry.menu.version")

menu = WhereAmIMenu()