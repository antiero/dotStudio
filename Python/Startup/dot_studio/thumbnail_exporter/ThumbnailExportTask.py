# Thumbnail Exporter Task
# Thumbnail image export task which can be used via the Export dialog via Shot, Clip or Sequence Processor
# To install copy the ThumbnailExportTask.py and ThumbnailExportTaskUI.py to your <HIERO_PATH>/Python/Startup directory.
# Keyword tokens exist for: 
# {frametype} - Position where the thumbnail was taken from (first/middle/last/custom)
# {srcframe} - The frame number of the original source clip file used for thumbnail
# {dstframe} - The destination frame (timeline time) number used for the thumbnail
# Antony Nasce, v1.0, 13/10/13
import os
import hiero.core
from PySide2.QtCore import Qt

class ThumbnailExportTask(hiero.core.TaskBase):
  def __init__( self, initDict ):
    """Initialize"""
    hiero.core.TaskBase.__init__( self, initDict )

  kFirstFrame = "First"
  kMiddleFrame = "Middle"
  kLastFrame = "Last"
  kCustomFrame = "Custom"

  def startTask(self):
    hiero.core.TaskBase.startTask(self)
    pass
  
  def sequenceInOutPoints(self, sequence, indefault, outdefault):
    """Return tuple (start, end) of in/out points. If either in/out is not set, return in/outdefault in its place."""
    inTime, outTime = indefault, outdefault
    try:
      inTime = sequence.inTime()
    except:
      pass
    
    try:
      outTime = sequence.outTime()
    except:
      pass
    return inTime, outTime

  def mapRetime(self, ti, timelineTime):
    """Maps the trackItem source in time to timeline in time, handling any retimes"""
    return ti.sourceIn() + int((timelineTime - ti.timelineIn()) * ti.playbackSpeed())

  def dstThumbnailFrameString(self):
    """This is the timeline time string, used by {dstframe}, based on the item and first/middle/last/custom frame type"""

    # For Clips and Sequences there's no such thing as dstTime
    if isinstance(self._item, (hiero.core.Clip,hiero.core.Sequence)):
      return self.srcThumbnailFrameString()
    # Case for Shots on the timeline (TrackItems) is trickier, because these can be retimed
    elif isinstance(self._item, hiero.core.TrackItem):
      # Get the frame type
      frameType = self._preset.properties()['frameType']

      # We need the timeline time, based on the frame type
      if frameType == self.kFirstFrame:
        T = self._item.timelineIn()
      elif frameType == self.kMiddleFrame:
        T = self._item.timelineIn()+int((self._item.timelineOut()-self._item.timelineIn())/2)
      elif frameType == self.kLastFrame:
        T = self._item.timelineIn()
      elif frameType == self.kCustomFrame:
        customOffset = int(self._preset.properties()['customFrameOffset'])
        T = self._item.timelineIn()+customOffset
        if T > self._item.timelineOut():
          T = self._item.timelineOut()

    return str(T)

  def srcThumbnailFrameString(self):
    """This does the magic to map to the source frame number to an actual dpx frame number, used by {srcframe}"""
    # Easy case for Clips and Sequences... no retimes
    if isinstance(self._item, (hiero.core.Clip,hiero.core.Sequence)):
      return str(self._item.timelineOffset()+int(self.thumbnailFrameNumber()))

    # Case for Shots on the timeline (TrackItems) is trickier, because these can be retimed
    elif isinstance(self._item, hiero.core.TrackItem):
      # Get the frame type
      clip = self._item.source()
      T = int(self.dstThumbnailFrameString())
      actualFrame = int(self.mapRetime(self._item , T)+clip.sourceIn())
      return str(int(actualFrame))

  # This determines where we take the thumbnail frame from, depending on the item and frame type
  def thumbnailFrameNumber(self):

    # Get the frame type
    frameType = self._preset.properties()['frameType']

    # Grab the custom offset value, in case its needed
    customOffset = int(self._preset.properties()['customFrameOffset'])

    # Case for Clips and Sequences
    if isinstance(self._item, (hiero.core.Clip,hiero.core.Sequence)):
      # In and out points of the Sequence
      start, end = self.sequenceInOutPoints(self._item, 0, self._item.duration() - 1)

      if frameType == self.kFirstFrame:
        thumbFrame = start
      elif frameType == self.kMiddleFrame:
        thumbFrame = start+((end-start)/2)
      elif frameType == self.kLastFrame:
        thumbFrame = end
      elif frameType == self.kCustomFrame:
        if customOffset > end:
          # If the custom offset exceeds the last frame, clamp at the last frame
          hiero.core.log.info("Frame offset exceeds the source out frame. Clamping to the last frame")
          thumbFrame = end
        else:
          thumbFrame = start+customOffset
    
    # Case for Shots on the timeline (TrackItems)
    elif isinstance(self._item, hiero.core.TrackItem):
      if frameType == self.kFirstFrame:
        thumbFrame = self._item.sourceIn()
      elif frameType == self.kMiddleFrame:
        thumbFrame = self._item.sourceIn()+int((self._item.sourceOut()-self._item.sourceIn())/2)
      elif frameType == self.kLastFrame:
        thumbFrame = self._item.sourceOut()
      elif frameType == self.kCustomFrame:
        thumbFrame = self._item.sourceIn()+customOffset
        if thumbFrame > self._item.sourceOut():
          # If the custom offset exceeds the last frame, clamp at the last frame 
          hiero.core.log.info("Frame offset exceeds the source out frame. Clamping to the last frame")
          thumbFrame = self._item.sourceOut()
    return int(thumbFrame)
     
  def taskStep(self):
    # Write out the thumbnail for each item
    if isinstance(self._item, (hiero.core.Sequence, hiero.core.Clip, hiero.core.TrackItem)):

      self._thumbFile = self.resolvedExportPath()

      # This deteremines the frame we call for the .thumbnail(frame) method, based on item and frame position      
      thumbFrame = int(self.thumbnailFrameNumber())

      # This gives us a QImage object from the Clip, Sequence or TrackItem.
      thumb = self._item.thumbnail(thumbFrame)

      try:
        thumbSize = self._preset.properties()['thumbSize']
        if thumbSize != "Default":
          # Get width and height of the image and see whether we need to add any letterboxing
          w = int(self._preset.properties()['width'])
          h = int(self._preset.properties()['height'])

          if thumbSize == 'To Box':
            # This determines whether we need to add a letterbox or not to preseve the aspect ratio
            sourceAspectRatio = float(thumb.width())/float(thumb.height())
            destAspectRatio = float(w)/float(h)

            # If the destination box aspect ratio matches our thumbnail source, don't letterbox
            if sourceAspectRatio == destAspectRatio:
              thumb = thumb.scaled(w,h, mode = Qt.SmoothTransformation)
            else:
              # If the destination box does not have the same aspect ratio as the source, we need to add a letterbox
              scaledThumb = thumb.scaledToHeight(h, mode = Qt.SmoothTransformation)
              w2 = scaledThumb.width()

              # The QImage.copy function allows us to get a new rect in which to place the image. 
              # We offset in -x to center the thumbnail, with vertical letter box, to match Hiero's thumbnails
              thumb = scaledThumb.copy(-(w-w2)/2.0, 0, w, h)
            
          elif thumbSize == 'Scaled to Width':
            thumb = thumb.scaledToWidth(w, mode = Qt.SmoothTransformation)
          elif thumbSize == 'Scaled to Height':
            thumb = thumb.scaledToHeight(h, mode = Qt.SmoothTransformation)

        thumb.save(self._thumbFile)
      except:
        print 'Unable to save thumbnail for %s' % str(self._item)

    self._finished = True
    
    return False

class ThumbnailExportPreset(hiero.core.TaskPresetBase):
  def __init__(self, name, properties):
    hiero.core.TaskPresetBase.__init__(self, ThumbnailExportTask, name)

    # Set any preset defaults here
    self.properties()["format"] = "png"
    self.properties()["frameType"] = "First"
    self.properties()["customFrameOffset"] = 12
    self.properties()["thumbSize"] = "Default"
    self.properties()["width"] = 480
    self.properties()["height"] = 270

    # Update preset with loaded data
    self.properties().update(properties)

  def addCustomResolveEntries(self, resolver):
    resolver.addResolver("{ext}", "File format extension of the thumbnail", lambda keyword, task: self.properties()["format"])
    resolver.addResolver("{frametype}", "Position where the thumbnail was taken from (first/middle/last/custom)", lambda keyword, task: self.properties()["frameType"].lower())    
    resolver.addResolver("{srcframe}", "The frame number of the original source clip file used for thumbnail", lambda keyword, task: task.srcThumbnailFrameString())
    resolver.addResolver("{dstframe}", "The destination frame (timeline time) number used for the thumbnail", lambda keyword, task: task.dstThumbnailFrameString())
  
  def supportedItems(self):
    return hiero.core.TaskPresetBase.kAllItems

hiero.core.taskRegistry.registerTask(ThumbnailExportPreset, ThumbnailExportTask)