from hiero.exporters.FnShotProcessor import ShotProcessorPreset
from hiero.exporters.FnBinProcessor import BinProcessorPreset

### EDIT THIS LIST ###
# Metadata keys stored on Tags you wish to add as tokens should be edited here.
# This will form new keywords that can be added via the Export dialog, e.g. {tag_shotCode}
tagMetadataKeys = ["shotCode", "department", "client"]

def _addUserResolveEntries(self, resolver):
  # Allows custom resolve tokens to be added to Export processors
  def metaKey(task, metaKey):
    """
    Searches for a metadata key stored on Tags of the item.
    If multiple Tags/keys exist, the first one found is returned
    """
    item = task._item

    # As of hiero 1.9, Nuke Studio 9.0, Tag metadata keys are always prefixed with tag.*
    if not metaKey.startswith("tag."):
      metaKey = "tag." + metaKey

    # Get the Tags attached to the item and try to find metaKey
    tags = item.tags()
    value = ""
    for tag in tags:
      metadata = tag.metadata()
      if metadata.hasKey(metaKey):
        # Might need to handle non-ascii here?
        value = str(metadata.value(metaKey).encode("utf-8"))
        break

    return value

  for key in tagMetadataKeys:
    resolver.addResolver("{tag_%s}" % key, "Returns the value for %s Tag metadata key, if available." % key, lambda keyword, task: metaKey(task, key) )

# Tag tokens can be applied to Clip the Shot Processors
ShotProcessorPreset.addUserResolveEntries = _addUserResolveEntries
BinProcessorPreset.addUserResolveEntries = _addUserResolveEntries