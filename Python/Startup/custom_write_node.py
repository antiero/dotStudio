import hiero.exporters

# An override adding a beforeRender callback to the Write node of a Nuke Script, to alter all ScanlineRender nodes with custom values
def beforeRenderNukeWriteNode(self, framerate=None, projectsettings=None):
  """Return a Nuke Write node for this tasks's export path."""
  nodeName = None
  presetProperties = self._preset.properties()
  if "writeNodeName" in presetProperties and presetProperties["writeNodeName"]:
    nodeName = self.resolvePath(presetProperties["writeNodeName"])

  # This calls the existing createWriteNode code, to get a Write node as usual
  writeNode = hiero.exporters.FnExternalRender.createWriteNode(self.resolvedExportPath(), self._preset, nodeName, framerate=framerate, projectsettings=projectsettings)

  # Then you add your special sauce and return it, instead of the boring old Write node
  writeNode.setKnob("beforeRender", r"""exec(\"for s in nuke.allNodes('ScanlineRender'):\\n s\['samples'].setValue(50)\\n s\['antialiasing'].setValue('high')\\n s\['shutter'].setValue(.3)\")""")

  return writeNode

# Override the default behaviour for Write nodes - note that this will affect ALL Nuke Renders from Hiero
hiero.exporters.FnExternalRender.NukeRenderTask.nukeWriteNode = beforeRenderNukeWriteNode