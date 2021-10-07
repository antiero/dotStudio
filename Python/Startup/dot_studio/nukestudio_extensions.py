# nukestudio_extensions.py - convenience methods for accessing items in Nuke Studio
# Install for Nuke Studio by copying to ~/.nuke/Python/Startup
from compiler.ast import flatten

def _toItem(itemString):
  """
  Similar to nuke.toNode, gives access to timeline items using 'sequenceName.trackName.itemName' dot-syntax.

  Example usage: 
  --------------
  shot = nuke.toItem("Sequence 1.Video 1.Shot0010")

  @return: a TrackItem or EffectTrackItem for the address found at 'sequenceName.trackName.itemName'

  Note: It is possible that multiple items can be returned as timeline items can have duplicate names.
  """

  # Split itemString into Sequence.Track.TrackItem components
  try:
    sequenceName, trackName, trackItemName = itemString.split('.')
  except ValueError as:
    print("Please supply a string with Sequence.Track.TrackItem syntax")

  project = hiero.ui.activeSequence().project()

  sequences = project.sequences()
  items = []
  for sequence in sequences:
    if sequence.name() == sequenceName:
      # Sequence Match found.. iterate Tracks...
      tracks = sequence.items()
      for track in tracks:
        if track.name() == trackName:
          # Track Match found.. iterate TrackItems...
          trackItems = track.items()
          for trackItem in trackItems:
            if trackItem.name() == trackItemName:
              # Candidate found.. 
              items += [trackItem]

        # Handle SubTrackItems on Video Tracks
        if isinstance(track, hiero.core.VideoTrack):
          subTracks = track.subTrackItems()
          for subTrack in subTracks:
            for subTrackItem in subTrack:
              if subTrackItem.name() == trackItemName:
                # Candidate found.. 
                items += [subTrackItem]

  # Return a single item if one exists, a list otherwise
  if len(items)==1:
    return items[0]
  else:
    return items

def _selectedItems(filter=None):
  """
  Returns a list of selected items in the timeline editor for the active Sequence.
  
  Optionally allows you to filter items by Class type.

  @param filter: Optionally supply a hiero.core Class type (or list of Class types)
  @return: list of selected items.

  Example usage: 
  --------------
    selection = nuke.selectedItems()
    selectedTrackItems = nuke.selectedItems( hiero.core.TrackItem )
    selectedEffectsFades = nuke.selectedItems( [hiero.core.Transition, hiero.core.EffectTrackItem] )

    Instead of Class types you may also provide the following strings as filter argument
    'shot', 'trackitem', 'effect', 'transition', 'videotrack', 'audiotrack', 

    e.g. shots = nuke.selectedItems('shot')

  """

  selection = []
  activeEditor = hiero.ui.getTimelineEditor(hiero.ui.activeSequence())

  if not activeEditor:
    raise Exception('Unable to determine the active Timeline Editor')

  selection = activeEditor.selection()

  # Optionally return a filtered list of hiero.core Classes of interest
  if filter:
    # Treat the case where user supplies a string instead of Class type
    if isinstance(filter, str):
      filterList = []
      if 'shot' in filter.lower() or filter.lower() == 'trackitem':
        filterList+=[hiero.core.TrackItem]
      if 'effect' in filter.lower():
        filterList+=[hiero.core.EffectTrackItem]
      if 'transition' in filter.lower():
        filterList+=[hiero.core.Transition]
      if 'videotrack' in filter.lower():
        filterList+=[hiero.core.VideoTrack]
      if 'audiotrack' in filter.lower():
        filterList+=[hiero.core.AudioTrack]

      selection = [item for item in selection if isinstance(item, tuple(filterList))]

    # User might've supplied a list of Classes...need to convert to tuple...
    elif isinstance(filter, list):
      selection = [item for item in selection if isinstance(item, tuple(filter))]
    # Else, it's a single Class or tuple...  
    else:
      selection = [item for item in selection if isinstance(item, filter)]

  return selection

def _selectedTracks(filter=None):
  """
  Returns a list of currently selected Tracks for the active Sequence.

  Optionally allows you to filter Tracks by Track Class type (e.g. Video, Audio)

  @param filter: Optionally supply a hiero.core TrackBase Class type (VideoTrack, AudioTrack)
  @return: list of selected Tracks.

  Example usage:
  -------------- 
  allSelectedTracks = nuke.selectedTracks()
  selectedVideoTracks = nuke.selectedTracks(hiero.core.Video)
  selectedAudioTracks = nuke.selectedTracks("audio")
  """
  selection = _selectedItems()
  
  tracks = []
  # Iterate through items and build a unique list of Tracks
  for item in selection:
    tracks += [item.parentTrack()]

  tracks = hiero.core.util.uniquify( tracks )

  # Optionally return a filtered list of hiero.core TrackBase Classes of interest
  if filter:
    # Treat the case where user supplies string 'audio' or 'video' instead of Class type
    if isinstance(filter, str):
      filterList = []
      if 'audio' in filter.lower():
        filterList += [hiero.core.AudioTrack]
      if 'video' in filter.lower():
        filterList += [hiero.core.VideoTrack]
      tracks = [item for item in tracks if isinstance(item, tuple(filterList))]

    # User might've supplied a list of Classes...need to convert to tuple...
    elif isinstance(filter, list):
      tracks = [item for item in tracks if isinstance(item, tuple(filter))]
    # Else, it's a single Class or tuple...
    else:
      tracks = [item for item in tracks if isinstance(item, filter)]

  return tracks

def seq_annotations(self):
  """
  hiero.core.Sequence.annotations -> returns the Annotations for a Sequence
  """
  tracks = self.videoTracks()
  annotations = []
  for track in tracks:
    subTrackItems = flatten(track.subTrackItems())
    annotations += [item for item in subTrackItems if isinstance(item, hiero.core.Annotation)]

  return annotations

def clip_annotations(self):
  """
  hiero.core.Clip.annotations -> returns the Annotations for a Clip
  """
  annotations = []
  subTrackItems = flatten(self.subTrackItems())
  annotations += [item for item in subTrackItems if isinstance(item, hiero.core.Annotation)]
  return annotations

def annotation_notes(self):
  """
  hiero.core.Annotation.notes -> Returns all text notes of an Annotation
  """
  elements = self.elements()
  notes = [item.text() for item in elements if isinstance(item, hiero.core.AnnotationText)]
  return notes

# Punch methods into nuke and hiero namespaces
try:
  import hiero.core
  import hiero.ui
  import nuke
  nuke.toItem = _toItem
  nuke.selectedItems = _selectedItems
  nuke.selectedTracks = _selectedTracks
  hiero.core.Sequence.annotations = seq_annotations
  hiero.core.Clip.annotations = clip_annotations
  hiero.core.Annotation.notes = annotation_notes

except ImportError as e:
  print("Unable to add Nuke Studio extensions: " + str(e))