# Copyright (c) 2011 The Foundry Visionmongers Ltd.  All Rights Reserved.

import os.path
import os
import sys
import shutil
import re


import hiero.core

class FrameioUploadExporter(hiero.core.TaskBase):
  def __init__( self, initDict ):
    """Initialize"""
    #FnFrameExporter.FrameExporter.__init__( self, initDict )
    if self.nothingToDo():
      return
   
  def taskStep(self):
    # If this is a single file (eg r3d or mov) then we don't need to do every frame.

    if not hiero.core.frameioDelegate.frameioSession.sessionAuthenticated:
      self.setError("Frame.io session has not been authenticated! Please enter username and password")
      return

class FrameioUploadPreset(hiero.core.TaskPresetBase):
  def __init__(self, name, properties):
    hiero.core.TaskPresetBase.__init__(self, FrameioUploadExporter, name)
    # Set any preset defaults here

    # This bool will determine whether the user wants to upload source files or transcode them
    self.properties()["frameioUploadSourceFiles"] = True
    
    # Update preset with loaded data
    self.properties().update(properties)

  def supportedItems(self):
    return hiero.core.TaskPresetBase.kSequence | hiero.core.TaskPresetBase.kClip


hiero.core.taskRegistry.registerTask(FrameioUploadPreset, FrameioUploadExporter)
