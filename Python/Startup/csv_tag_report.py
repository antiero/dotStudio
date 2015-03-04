# This Example adds a CSV Tag Report to the right-click menu of Bin, Spreadsheet and Timeline Views.
# You can choose to export All shots / All Tagged from a Sequence, or a Selection, or Tagged Selection.
from hiero.core.events import registerInterest
from hiero.core import ApplicationSettings, Sequence, TrackItem, Timecode
from hiero.ui import createMenuAction, activeView, activeSequence, mainWindow
from PySide.QtGui import QAction, QMenu, QDesktopServices
from PySide.QtCore import QUrl
from foundry.ui import openFileBrowser
import os, csv, datetime

### Helper methods ###
def getSelectedShotsForActiveView(taggedShotsOnly=False):
  """
  Returns a list of selected shots in the active View
  Optionally returns only shots which are Tagged by setting taggedShotsOnly to True
  """
  view = activeView()
  if not hasattr(view, "selection"):
    # If we're here bail out, something has gone wron
    return

  selection = view.selection()
  # Filter the list of shots from the active selection
  if not taggedShotsOnly:
    shotSelection = [item for item in selection if isinstance(item, TrackItem)]
  else:
    shotSelection = [item for item in selection if isinstance(item, TrackItem) and len(item.tags())>0]

  return shotSelection

def getShotsForActiveSequence(taggedShotsOnly=False):
  """
  Returns a list of shots from the active sequence.
  Optionally returns only shots which are Tagged by setting taggedShotsOnly to True
  """
  sequence = None
  try:
    sequence = activeSequence()
  except:
    sequence = activeView().selection()[0].parentSequence()

  if not sequence:
    return

  # Get all Tracks in the Sequence...
  tracks = sequence.items()
  shots = []
  if not taggedShotsOnly:
    for track in tracks:
      shots+=[item for item in track.items() if isinstance(item, TrackItem)]
  else:
    for track in tracks:
      shots+=[item for item in track.items() if isinstance(item, TrackItem) and len(item.tags())>0]

  return shots

def shotMediaType(shot):
  """
  Returns the media type of a shot as a string: 'Video', 'Audio' or 'Comp'
  """
  if shot.mediaType() == TrackItem.MediaType.kAudio:
    return "Audio"    
  elif shot.mediaType() == TrackItem.MediaType.kVideo:
    if shot.source().mediaSource().filename().endswith(".nk"):
      return "Comp"
    else:
      return "Video"
  else:
    return "Unknown"

class TagReportWriter(object):
  """
  This Example adds a CSV Tag Report to the right-click menu of Bin, Spreadsheet and Timeline Views.
  You can choose to export All shots / All Tagged from a Sequence, or a Selection, or Tagged Selection.
  If you wish to export the Nuke Project Tags added on export, set the self.includeNukeTags property to True
  """
  def __init__(self):
    registerInterest("kShowContextMenu/kBin", self.binViewEventHandler)
    registerInterest("kShowContextMenu/kSpreadsheet", self.eventHandler)
    registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
    self._tagReportMenu = QMenu('CSV Tag Report')
    self.exportAllReportAction = createMenuAction("Export All", self.writeCSVReportForAllShotsInActiveSequence)
    self.exportTaggedReportAction = createMenuAction("Export All Tagged", self.writeCSVReportForTaggedShotsInActiveSequence)
    self.exportSelectedReportAction = createMenuAction("Export Selection", self.writeCSVReportForShotSelection)
    self.exportSelectedTaggedReportAction = createMenuAction("Export Selection Tagged", self.writeCSVReportForTaggedSelection)

    # By default, the Reporter will exclude the Nuke Tags (e.g. "Nuke Project File") added on export for instance.
    # To include these False, set includeNukeTags to True
    self.includeNukeTags = False   

    # Insert the actions to the Export CSV menu
    self._tagReportMenu.addAction(self.exportAllReportAction)
    self._tagReportMenu.addAction(self.exportTaggedReportAction)
    self._tagReportMenu.addAction(self.exportSelectedReportAction)
    self._tagReportMenu.addAction(self.exportSelectedTaggedReportAction)

  def eventHandler(self, event):
    selection = event.sender.selection()
    selectionEnabled = True
    if (selection is None) or (len(selection)==0):
      selectionEnabled = False

    self.exportSelectedReportAction.setVisible(True)
    self.exportSelectedTaggedReportAction.setVisible(True)
    self.exportSelectedReportAction.setEnabled(selectionEnabled)
    self.exportSelectedTaggedReportAction.setEnabled(selectionEnabled)
    event.menu.addMenu(self._tagReportMenu)

  def binViewEventHandler(self, event):
    # In the Bin view, we only enable the exportTaggedReportAction action if a single Sequence is selected
    selection = event.sender.selection()
    if len(selection)>1:
      return

    sequences = [item.activeItem() for item in selection if isinstance(item.activeItem(), Sequence)]
    if len(sequences)!=1:
      return

    self.exportSelectedReportAction.setVisible(False)
    self.exportSelectedTaggedReportAction.setVisible(False)
    event.menu.addMenu(self._tagReportMenu)

  def buildUniqueTagsDictFromShotSelection(self, shotSelection):
    """Builds a dictionary of Tags, with keys as Tag names, values as the TrackItems with that Tag"""

    tagDict = {}
    for shot in shotSelection:
      tags = list(shot.tags())

      if not self.includeNukeTags:
        # By default prune the list of Tags that have a Nuke Icon and a 'file' metadata key
        for item in tags:
          if item.icon() =="icons:Nuke.png" and item.metadata().hasKey('tag.path'):
            tags.remove(item)

      for tag in tags:
        tagName = tag.name()
        if tagName not in tagDict.keys():
          tagDict[tagName]=[shot]
        else:
          tagDict[tagName]+=[shot]

    return tagDict

  def writeAllShotsReportCSVForActiveSequence(self):

    # Get the active Sequence
    try:
      sequence = activeSequence()
    except:
      sequence = activeView().selection()[0].parentSequence()

    # Get all Tracks in the Sequence...
    tracks = sequence.items()
    shots = []
    for track in tracks:
      shots+=[item for item in track.items() if isinstance(item, TrackItem)]

    self.writeCSVTagReportFromShotSelection(shotSelection=shots, taggedShotsOnly=False)

  def writeCSVReportForAllShotsInActiveSequence(self):
    """Exports all shots to a csv from the Active Sequence"""
    # Get the active Sequence

    shots = getShotsForActiveSequence()
    self.writeCSVReportForShotSelection(shotSelection=shots)

  def writeCSVReportForTaggedShotsInActiveSequence(self):
    """Writes shots with a tag to a csv from the Active Sequence"""
    # Get the active Sequence

    shots = getShotsForActiveSequence(taggedShotsOnly=True)
    self.writeCSVReportForShotSelection(shotSelection=shots)    


  def writeCSVReportForTaggedSelection(self):
    shots = getSelectedShotsForActiveView(taggedShotsOnly=True)
    self.writeCSVReportForShotSelection(shots)


  def writeCSVReportForShotSelection(self, shotSelection=None, savePath=None):
    """Writes a csv file from a shotSelection, optionally saves tagged shots only. If running"""

    if not shotSelection:
      shotSelection = getSelectedShotsForActiveView()

    if len(shotSelection) <= 0:
      # If we're here we have no shots to work with - bail out.
        return

    sequence = shotSelection[0].parentSequence()
    tagDict = self.buildUniqueTagsDictFromShotSelection(shotSelection)

    if not savePath:
      currentTimeString = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d_%H-%M-%S')
      saveName = "TagReport_%s_%s.csv" % (sequence.name().replace(" ", "_"), currentTimeString)
      csvSavePath = os.path.join(os.getenv('HOME'), 'Desktop', saveName)
      savePath = openFileBrowser(caption="Save Tag Report .CSV as...", initialPath=csvSavePath, mayNotExist=True, forSave=True, pattern="*.csv")
      print "Save path %s" % savePath
      # A list is returned here, we SHOULD only get one file name, but force this to be only one, then check for .csv extension.
      if len(savePath)!=1:
        return
      else:
        savePath=savePath[0]

      if not savePath.lower().endswith(".csv"):
        savePath+".csv"

    if len(savePath)==0:
      return

    # The Header row for the CSV will contain some basic info re. the shot...
    sortedTagNames = sorted(tagDict)

    ### THIS HEADER MUST MATCH THE table_data line below ###
    csvHeader = ["Shot Name", "Duration", "Source Clip", "Track", "Type", "No. Tags"]

    # Plus Tag names as columns
    if len(sortedTagNames)>0:
      csvHeader.extend(sortedTagNames)

    # Get a CSV writer object
    csvFile = open(savePath, 'w')
    csvWriter = csv.writer( csvFile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

    # Write the Header row to the CSV file
    csvWriter.writerow(csvHeader)

    for shot in shotSelection:
      currentTags = shot.tags()
      currentShotTagNames = [tag.name() for tag in currentTags]

      ### THIS LIST MUST MATCH THE csvHeader above ###
      table_data = [shot.name(), 
                    shot.duration(), 
                    shot.source().name(), 
                    shot.parentTrack().name(), 
                    shotMediaType(shot),
                    str(len(currentTags))]

      # Then add the remaining columns as TRUE/FALSE values in the tag columns
      for tag in sortedTagNames:
        if tag in currentShotTagNames:
          table_data += ["TRUE"]
        else:
          table_data += ["FALSE"]
      csvWriter.writerow(table_data)

    # Be good and close the file
    csvFile.close()
    print 'CSV Tag Report saved to: ' + str(savePath)

    # Conveniently show the CSV file in the native file browser...
    QDesktopServices.openUrl(QUrl('file:///%s' % (os.path.dirname(savePath))))    

#### Add the Menu... ####
csvActions = TagReportWriter()