import hiero.ui
from FnCutDetector import FnCutDetectorPanel

cutDetector = FnCutDetectorPanel()

hiero.ui.registerPanel( "uk.co.thefoundry.cutdetector", cutDetector )

wm = hiero.ui.windowManager()
wm.addWindow( cutDetector )