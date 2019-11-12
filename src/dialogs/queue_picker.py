from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
import functools
import re
import random
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from aqt.utils import showInfo
from anki.utils import isMac
from anki.lang import _


from ..notes import *
import utility.text
import utility.misc

class QueuePicker(QDialog):
    """
    Can be used to select a single note from the queue.
    """
    def __init__(self, parent, note_list):
        self.chosen_id = None 
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        self.setup_ui(note_list)
        self.setWindowTitle("Choose a Note")

    def setup_ui(self, note_list):

        self.t_view = QListWidget()

        for ix, n in enumerate(note_list):
            title = n[1] if n[1] is not None and len(n[1]) > 0 else "Untitled"
            title_i = QListWidgetItem(str(ix + 1) + ".  " + title)
            title_i.setData(Qt.UserRole, QVariant(n[0]))
            self.t_view.insertItem(ix, title_i)

        self.t_view.setSelectionMode(QAbstractItemView.SingleSelection);
        self.t_view.itemClicked.connect(self.item_clicked)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.t_view)
        
        bottom_box = QHBoxLayout()
        self.accept_btn = QPushButton("Ok")
        self.accept_btn.clicked.connect(self.accept)
        bottom_box.addStretch(1)
        bottom_box.addWidget(self.accept_btn)
        bottom_box.addSpacing(8)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        bottom_box.addWidget(self.reject_btn)
        self.vbox.addLayout(bottom_box)

        self.setLayout(self.vbox)
        self.resize(400, 420)

    def item_clicked(self, item):
        self.chosen_id = item.data(Qt.UserRole)