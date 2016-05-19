"""Alternative "tab node creator thingy" for The Foundry's Nuke

homepage: https://github.com/dbr/tabtabtab-nuke
license: http://unlicense.org/
"""

__version__ = "1.8-dev"

import os
import sys

try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import Qt
    from PySide.QtGui import QAction, QKeySequence, QCursor
    import hiero.core
    import hiero.ui
except ImportError:
    # import sip
    # for mod in ("QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"):
    #     sip.setapi(mod, 2)

    # from PyQt4 import QtCore, QtGui
    # from PyQt4.QtCore import Qt
    # QtCore.Signal = QtCore.pyqtSignal
    print "Failed To Import Qt and hiero modules"

def find_soft_effects():
    """Gets a list of soft effects registered in Hiero/NukeStudio"""

    effects = [action.data() for action in hiero.ui.findRegisteredActions("foundry.timeline.effect") if action.data()]

    return effects

class NodeModel(QtCore.QAbstractListModel):
    def __init__(self, mlist, num_items = 15, filtertext = ""):
        super(NodeModel, self).__init__()

        self.num_items = num_items

        self._all = mlist
        self._filtertext = filtertext

        # _items is the list of objects to be shown, update sets this
        self._items = []
        self.update()

    def set_filter(self, filtertext):
        self._filtertext = filtertext
        self.update()

    def update(self):
        # filtertext = self._filtertext.lower()

        # # Two spaces as a shortcut for [
        # filtertext = filtertext.replace("  ", "[")

        # scored = []
        # for n in self._all:
        #     # Turn "3D/Shader/Phong" into "Phong [3D/Shader]"
        #     menupath = n['menupath'].replace("&", "")
        #     uiname = "%s [%s]" % (menupath.rpartition("/")[2], menupath.rpartition("/")[0])

        # # Store based on scores (descending), then alphabetically
        # s = sorted(scored, key = lambda k: (-k['score'], k['text']))

        self._items = find_soft_effects()#s
        self.modelReset.emit()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return min(self.num_items, len(self._items))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Return text to display
            raw = self._items[index.row()]
            return raw

        elif role == Qt.DecorationRole:
            return
            # weight = self._items[index.row()]['score']

            # hue = 0.4
            # sat = weight

            # if index.row() % 2 == 0:
            #     col = QtGui.QColor.fromHsvF(hue, sat, 0.9)
            # else:
            #     col = QtGui.QColor.fromHsvF(hue, sat, 0.8)

            # pix = QtGui.QPixmap(6, 12)
            # pix.fill(col)
            # return pix

        elif role == Qt.BackgroundRole:
            return
            # weight = self._items[index.row()]['score']

            # hue = 0.4
            # sat = weight ** 2 # gamma saturation to make faster falloff

            # sat = min(1.0, sat)

            # if index.row() % 2 == 0:
            #     return QtGui.QColor.fromHsvF(hue, sat, 0.9)
            # else:
            #     return QtGui.QColor.fromHsvF(hue, sat, 0.8)
        else:
            # Ignore other roles
            return None

    def getorig(self, selected):
        # TODO: Is there a way to get this via data()? There's no
        # Qt.DataRole or something (only DisplayRole)

        if len(selected) > 0:
            # Get first selected index
            selected = selected[0]

        else:
            # Nothing selected, get first index
            selected = self.index(0)

        # TODO: Maybe check for IndexError?
        selected_data = self._items[selected.row()]
        return selected_data


class TabyLineEdit(QtGui.QLineEdit):
    pressed_arrow = QtCore.Signal(str)
    cancelled = QtCore.Signal()


    def event(self, event):
        """Make tab trigger returnPressed

        Also emit signals for the up/down arrows, and escape.
        """

        is_keypress = event.type() == QtCore.QEvent.KeyPress

        if is_keypress and event.key() == QtCore.Qt.Key_Tab:
            # Can't access tab key in keyPressedEvent
            self.returnPressed.emit()
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Up:
            # These could be done in keyPressedEvent, but.. this is already here
            self.pressed_arrow.emit("up")
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Down:
            self.pressed_arrow.emit("down")
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Escape:
            self.cancelled.emit()
            return True

        else:
            return super(TabyLineEdit, self).event(event)


class TabTabTabWidget(QtGui.QDialog):
    def __init__(self, on_create = None, parent = None, winflags = None):
        super(TabTabTabWidget, self).__init__(parent = parent)
        if winflags is not None:
            self.setWindowFlags(winflags)

        self.setMinimumSize(200, 300)
        self.setMaximumSize(200, 300)

        # Store callback
        self.cb_on_create = on_create

        # Input box
        self.input = TabyLineEdit()

        # Node weighting
        # self.weights = NodeWeights(os.path.expanduser("~/.nuke/tabtabtab_weights.json"))
        # self.weights.load() # weights.save() called in close method

        # Returns a list the soft effects registered as the "data" property of the Effect QAction.
        self.effects = find_soft_effects()

        #nodes = find_menu_items(nuke.menu("Nodes")) + find_menu_items(nuke.menu("Nuke"))

        # List of stuff, and associated model
        self.things_model = NodeModel(self.effects) #NodeModel(nodes)
        self.things = QtGui.QListView()
        self.things.setModel(self.things_model)

        # Add input and items to layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.things)

        # Remove margins
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Update on text change
        self.input.textChanged.connect(self.update)

        # Reset selection on text change
        self.input.textChanged.connect(lambda: self.move_selection(where="first"))
        self.move_selection(where = "first") # Set initial selection

        # Create node when enter/tab is pressed, or item is clicked
        self.input.returnPressed.connect(self.create)
        self.things.clicked.connect(self.create)

        # When esc pressed, close
        self.input.cancelled.connect(self.close)

        # Up and down arrow handling
        self.input.pressed_arrow.connect(self.move_selection)

    def under_cursor(self):
        def clamp(val, mi, ma):
            return max(min(val, ma), mi)

        # Get cursor position, and screen dimensions on active screen
        cursor = QtGui.QCursor().pos()
        screen = QtGui.QDesktopWidget().screenGeometry(cursor)

        # Get window position so cursor is just over text input
        xpos = cursor.x() - (self.width()/2)
        ypos = cursor.y() - 13

        # Clamp window location to prevent it going offscreen
        xpos = clamp(xpos, screen.left(), screen.right() - self.width())
        ypos = clamp(ypos, screen.top(), screen.bottom() - (self.height()-13))

        # Move window
        self.move(xpos, ypos)

    def showAt(self, pos):
        # BUILD DATA WHEN SHOWN - is this the best time to do this?
        #self.updateTableView()
        self.move(pos.x()-self.width()/2, pos.y()-self.height()/2)
        self.show()        

    def move_selection(self, where):
        if where not in ["first", "up", "down"]:
            raise ValueError("where should be either 'first', 'up', 'down', not %r" % (
                    where))

        first = where == "first"
        up = where == "up"
        down = where == "down"

        if first:
            self.things.setCurrentIndex(self.things_model.index(0))
            return

        cur = self.things.currentIndex()
        if up:
            new = cur.row() - 1
            if new < 0:
                new = self.things_model.rowCount() - 1
        elif down:
            new = cur.row() + 1
            count = self.things_model.rowCount()
            if new > count-1:
                new = 0

        self.things.setCurrentIndex(self.things_model.index(new))

    def event(self, event):
        """Close when window becomes inactive (click outside of window)
        """
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.close()
            return True
        else:
            return super(TabTabTabWidget, self).event(event)

    def update(self, text):
        """On text change, selects first item and updates filter text
        """
        self.things.setCurrentIndex(self.things_model.index(0))
        self.things_model.set_filter(text)

    def show(self):
        """Select all the text in the input (which persists between
        show()'s)

        Allows typing over previously created text, and [tab][tab] to
        create previously created node (instead of the most popular)
        """

        # Load the weights everytime the panel is shown, to prevent
        # overwritting weights from other Nuke instances
        #self.weights.load()

        # Select all text to allow overwriting
        self.input.selectAll()
        self.input.setFocus()

        super(TabTabTabWidget, self).show()

    def close(self):
        """Save weights when closing
        """
        #self.weights.save()
        super(TabTabTabWidget, self).close()

    def create(self):
        # Get selected item
        selected = self.things.selectedIndexes()
        if len(selected) == 0:
            return

        effect = self.things_model.getorig(selected)

        seq = hiero.ui.activeSequence()
        if not seq:
            self.close()
            return

        timelineEditor = hiero.ui.getTimelineEditor(seq)
        activeSelection = timelineEditor.selection()


        if activeSelection:
            print("Got an active Selection in the Timeline editor, will add a %s effect.." % effect)
            for item in activeSelection:
                hiero.core.log.info("Adding to item: %s" % str(item))
                tIn = item.timelineIn()
                tOut = item.timelineOut()
                track = item.parentTrack()

                if isinstance(track, hiero.core.VideoTrack):
                    effectItem = hiero.core.EffectTrackItem(effect)
                    effectItem.setTimelineIn(tIn)
                    effectItem.setTimelineOut(tOut)
                    track.addSubTrackItem(effectItem, 0)

        #self.weights.increment(thing['menupath'])
        self.close()


_tabtabtab_instance = None
def main():
    global _tabtabtab_instance

    if _tabtabtab_instance is not None:
        # TODO: Is there a better way of doing this? If a
        # TabTabTabWidget is instanced, it goes out of scope at end of
        # function and disappers instantly. This seems like a
        # reasonable "workaround"

        _tabtabtab_instance.under_cursor()
        _tabtabtab_instance.show()
        _tabtabtab_instance.raise_()
        return

    def on_create(thing):
        try:
            thing['menuobj'].invoke()
        except ImportError:
            print "Error creating %s" % thing

    # t = TabTabTabWidget(on_create = on_create, winflags = Qt.FramelessWindowHint)

    # # Make dialog appear under cursor, as Nuke's builtin one does
    # t.under_cursor()

    # # Show, and make front-most window (mostly for OS X)
    # t.show()
    # t.raise_()

    # # Keep the TabTabTabWidget alive, but don't keep an extra
    # # reference to it, otherwise Nuke segfaults on exit. Hacky.
    # # https://github.com/dbr/tabtabtab-nuke/issues/4
    # #import weakref
    # hiero.ui.tabtabtab = t
    #_tabtabtab_instance = weakref.proxy(t)

print("Calling TabTabTabWidget main()")
_popover = None
_popoverShown = False

def toggleTabTabTab():
    global _popover
    global _popoverShown
    if not _popoverShown:
        _popover = TabTabTabWidget(winflags = Qt.FramelessWindowHint)
        v = hiero.ui.activeView()
        _popover.showAt(QCursor.pos())
        _popoverShown = True
    else:
        _popover.hide()
        _popoverShown = False

action = QAction("Effect Browser", None)
#action.setShortcut("Tab")
action.setShortcut(QKeySequence("?"))
action.triggered.connect(toggleTabTabTab)
hiero.ui.addMenuAction("Window", action)