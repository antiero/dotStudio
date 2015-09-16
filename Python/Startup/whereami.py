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

      self._sequenceActions = []

      # To reduce the time needed to show the menu for large projects, create this menu dynamically when the action is shown
      self._whereAmIMenu.aboutToShow.connect(self.createSequenceUsageMenuForActiveView)

      hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
      hiero.core.events.registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)


  def makeShowSequenceActionForSequence(self, sequence):
    """This is used to populate the QAction list of Versions when a single Clip is selected in the BinView. 
    It also triggers the Version Update action based on the version passed to it. 
    (Not sure if this is good design practice, but it's compact!)"""
    action = QtGui.QAction(sequence.name(),None)
    action.setData(lambda: sequence)

    def showSequenceTimeline():
      binItem = sequence.binItem()
      hiero.ui.openInTimeline(binItem)
    
    action.triggered.connect( showSequenceTimeline )
    return action

  # This generates the Version Up Everywhere menu
  def createSequenceUsageMenuForActiveView(self):
    self._whereAmIMenu.clear()
    view = hiero.ui.activeView()
    selection = view.selection()

    if len(selection)!=1:
      return

    if isinstance(view, hiero.ui.BinView):
      selection = selection[0]
      if not hasattr(selection, 'activeItem'):
        return 
      else:
        item = selection.activeItem()
    elif isinstance(view, (hiero.ui.TimelineEditor, hiero.ui.SpreadsheetView)):
      item = selection[0]
      if not isinstance(item, hiero.core.TrackItem):
        return

    manifest = item.usageManifest()

    for sequence in manifest.keys():
      act = self.makeShowSequenceActionForSequence(sequence)
      if act not in hiero.ui.registeredActions():
        hiero.ui.registerAction(act)

      self._whereAmIMenu.addAction(act)

  # Set Tag dialog with Note and Selection info. Adds Tag to entire object, not over a range of frames
  def showTrackItemInSequence(self, item, sequence):
    """Opens a Sequence up in a new Timeline and places playhead at the position of the TrackItem"""
    T = item.timelineIn()
    editor = hiero.ui.openInTimeline(sequence.binItem())

    # Not sure this will work...
    editor.setSelection(item)
    cv = hiero.ui.currentViewer()

    t = sequence.trackItemAt
    cv.setTime(T)

  ########## EVENT HANDLERS ##########
  
  # This handles events from the Viewer View (kViewer)
  def eventHandler(self, event):
    hiero.ui.insertMenuAction(self._whereAmIMenu.menuAction(), event.menu, after = "foundry.menu.version")

menu = WhereAmIMenu()