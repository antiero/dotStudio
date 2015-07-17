import hiero.ui
import FnSceneDetector
sceneDetector = FnSceneDetector.FnSceneDetectorPanel()

hiero.ui.registerPanel( "uk.co.thefoundry.scenedetector", sceneDetector )

wm = hiero.ui.windowManager()
wm.addWindow( sceneDetector )