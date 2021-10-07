import hiero.ui
from .CutDetector import CutDetectorPanel

cutDetector = CutDetectorPanel()

hiero.ui.registerPanel( "uk.co.thefoundry.cutdetector", cutDetector )

wm = hiero.ui.windowManager()
wm.addWindow( cutDetector )