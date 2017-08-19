# An action which allows you to remove a Bin Item from the Project and move it to the Local Trash / Recycle bin.
import hiero.core
import hiero.ui
import time
from send2trash import send2trash

def forceDeleteBinItem(binItem = None):

	if not binItem:
		view = hiero.ui.activeView()
		if isinstance(view, hiero.ui.BinView):
			binViewSelection = view.selection()
			selection = [item for item in binViewSelection if isinstance(item, hiero.core.BinItem)]
			if len(selection) > 1:
				return
			else:
				binItem = selection[0]

	if hasattr(binItem, 'activeItem'):
		clip = binItem.activeItem()

	else:
		return

	M = clip.mediaSource()
	fileInfo = M.fileinfos()[0]
	filename = fileInfo.filename()
	hiero.ui.openInOSShell(filename)

	time.sleep(2)
	send2trash(filename)

	parentBin = binItem.parentBin()
	parentBin.removeItem(binItem)


act = hiero.ui.createMenuAction("Force Delete File", forceDeleteBinItem)
act.setShortcut("Ctrl+Shift+Backspace")
menuAction = hiero.ui.findMenuAction("Window")
menu = menuAction.menu()
menu.addAction(act)