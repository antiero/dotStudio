from fcpxml_parser import fcpxml_wrapper
import hiero.ui
from hiero.core.events import registerInterest, unregisterInterest, EventType
import os

class BinViewDropHandler:
  kTextMimeType = "text/plain"
  
  def __init__(self):
    # hiero doesn't deal with drag and drop for text/plain data, so tell it to allow it
    hiero.ui.registerBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)
    
    # register interest in the drop event now
    registerInterest((EventType.kDrop, EventType.kBin), self.dropHandler)

  def isSequenceFile(self, f, extension = '.fcpxml'):
    return f.lower().endswith( extension )

  def dropHandler(self, event):
    
    # get the mime data
    #print "mimeData: ", dir(event.mimeData)
    urls = [url.toLocalFile() for url in event.mimeData.urls()]

    # Build a list of possible XML/EDL files
    sequenceFiles = []
    for url in urls:
      if os.path.isdir(url):
        for root, dirs, files in os.walk(url):
          FILES = [os.path.join(root, file) for file in files]
          for f in FILES: 
            if self.isSequenceFile(f):
              sequenceFiles+=[f]    

      elif self.isSequenceFile(url):
        sequenceFiles+=[url]

    # Now we should have a list of Sequences. We should now import them
    proj = hiero.core.projects()[-1]
    root = proj.clipsBin()
    assetsBin = hiero.core.Bin("assets")
    root.addItem(assetsBin)
    print 'GOT THESE' + str(sequenceFiles)
    for seq in sequenceFiles:
      wrapper = fcpxml_wrapper(seq)
      clipPaths = wrapper.assets
      for clip in clipPaths:
        C = hiero.core.Clip(clip.filepath)
        assetsBin.addItem(hiero.core.BinItem(C))
      
  def unregister(self):
    unregisterInterest((EventType.kDrop, EventType.kBin), self.dropHandler)
    hiero.ui.unregisterBinViewCustomMimeDataType(BinViewDropHandler.kTextMimeType)

# Instantiate the handler to get it to register itself.
dropHandler = BinViewDropHandler()