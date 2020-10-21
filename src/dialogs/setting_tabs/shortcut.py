from aqt.qt import *
from aqt import mw

from aqt.utils import showInfo

from config import get_config_value, update_config

class GrabKey(QDialog):
    """
    Grab the key combination to paste the resized image

    Largely based on ImageResizer by searene
    (https://github.com/searene/Anki-Addons)
    """

    def __init__(self, parent):
        QDialog.__init__(self, parent=parent)
        self.parent = parent
        #self.key = parent.hotkey
        self
        # self.active is used to trace whether there's any key held now
        self.active = 0
        self.ctrl = False
        self.alt = False
        self.shift = False
        self.extra = None
        self.setupUI()

    def setupUI(self):
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        label = QLabel('Please press the new key combination')
        mainLayout.addWidget(label)

        self.setWindowTitle('Grab key combination')

    def keyPressEvent(self, evt):
        self.active += 1
        if evt.key() > 0 and evt.key() < 127:
            self.extra = chr(evt.key())
        elif evt.key() == Qt.Key_Control:
            self.ctrl = True
        elif evt.key() == Qt.Key_Alt:
            self.alt = True
        elif evt.key() == Qt.Key_Shift:
            self.shift = True

    def keyReleaseEvent(self, evt):
        self.active -= 1

        if self.active != 0:
            return
        if not (self.shift or self.ctrl or self.alt):
            showInfo("Please use at least one keyboard "
                     "modifier (Ctrl, Alt, Shift)")
            return
        if (self.shift and not (self.ctrl or self.alt)):
            showInfo("Shift needs to be combined with at "
                     "least one other modifier (Ctrl, Alt)")
            return
        if not self.extra:
            showInfo("Please press at least one key "
                     "that is not a keyboard modifier (not Ctrl/Alt/Shift)")
            return

        combo = []
        if self.ctrl:
            combo.append("Ctrl")
        if self.shift:
            combo.append("Shift")
        if self.alt:
            combo.append("Alt")
        combo.append(self.extra)

        #self.parent.updateHotkey("+".join(combo))
        self.close()

class setting_tab_shortcut(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.vbox = QVBoxLayout()

        self.b1 = QPushButton("Create!")
        self.b2 = QPushButton("Test2")

        self.b1.clicked.connect(self.showGrabKey)

        self.vbox.addWidget(self.b1)
        self.vbox.addWidget(self.b2)

        self.setLayout(self.vbox)

    def showGrabKey(self):
        """Invoke key grabber"""
        win = GrabKey(self)
        win.exec_()
