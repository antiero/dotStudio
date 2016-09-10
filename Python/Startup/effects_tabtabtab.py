"""
Soft-Effect Tab browser/picker thing for Hiero/NukeStudio
Modified tabtabtab-nuke code from https://github.com/dbr/tabtabtab-nuke
tabtabtab.py license: http://unlicense.org/
"""

import os
import sys

try:
    from PySide import QtCore, QtGui
    from PySide.QtCore import Qt
    from PySide.QtGui import QAction, QKeySequence, QCursor
    import hiero.core
    import hiero.ui
except ImportError:
    print "Failed To Import Qt and hiero modules"

def find_soft_effects():
    """Gets a list of soft effects registered in Hiero/NukeStudio"""

    effectActions = [action for action in hiero.ui.findRegisteredActions("foundry.timeline.effect") if action.data()]

    effectDict = {}
    # Return a dictionary, where the keys are the effect data names, action and icon are stored
    for effectAction in effectActions:
        effectName = effectAction.data()
        if effectName not in effectDict.keys():
            effectDict[effectName] = {}
        
        effectDict[effectName]["action"] = effectAction
        effectDict[effectName]["icon"] = effectAction.icon()
        effectDict[effectName]["effectName"] = effectAction.data()
        effectDict[effectName]["objectName"] = effectAction.objectName()

    return effectDict

class NodeModel(QtCore.QAbstractListModel):
    def __init__(self, mlist, num_items = 5, filtertext = ""):
        super(NodeModel, self).__init__()

        self.num_items = num_items

        self._all = mlist
        self._filtertext = filtertext

        self._allEffects = find_soft_effects()

        self._allEffectNames = sorted(self._allEffects.keys())

        # _items is the list of objects to be shown, update sets this
        self._items = []
        self.update()

    def set_filter(self, filtertext):
        self._filtertext = filtertext
        self.update()

    def update(self):
        
        filtertext = self._filtertext.lower()
        effectMatches = []
        for effect in self._allEffectNames:
            if effect.lower().find(filtertext) != -1:
                effectMatches.append(effect)

        self._items = effectMatches
        self.modelReset.emit()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return min(self.num_items, len(self._items))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            # Return text to display
            raw = self._allEffects[ self._items[index.row()] ]['effectName']
            return raw

        elif role == Qt.DecorationRole:
            icon = self._allEffects[ self._items[index.row()] ]['icon']
            pix = icon.pixmap(12, 12)
            return pix

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

        elif is_keypress and event.key() in (QtCore.Qt.Key_Escape, 167):
            self.cancelled.emit()
            return True

        else:
            return False

class TabTabTabWidget(QtGui.QDialog):
    def __init__(self, parent = None):
        super(TabTabTabWidget, self).__init__(parent = parent)

        self.setWindowFlags(Qt.FramelessWindowHint)

        # Input box
        self.input = TabyLineEdit()

        # Returns a list the soft effects registered as the "data" property of the Effect QAction.
        self.effects = find_soft_effects()

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
        """
        Close when window becomes inactive (click outside of window)
        """
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.close()
            return True
        else:
            return False            

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

        self.close()

def toggleTabTabTab():
    if hiero.ui.tabtabtab.isHidden():
        hiero.ui.tabtabtab.showAt(QCursor.pos())
    else:
        hiero.ui.tabtabtab.hide()

action = QAction("Effect Browser", None)
action.setShortcut(QKeySequence(167))
action.triggered.connect(toggleTabTabTab)
hiero.ui.addMenuAction("Window", action)

# Keep a reference to the TabTabTabWidget in hiero.ui
hiero.ui.tabtabtab = TabTabTabWidget()