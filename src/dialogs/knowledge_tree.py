from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *
from aqt.utils import showInfo
import utility.misc

import state
from ..notes import get_all_tags_as_hierarchy
from ..api import open_siac_with_id
from ..utility.tag_tree import TagTree, DataCol, ItemType
from aqt.previewer import BrowserPreviewer as PreviewDialog
from aqt.previewer import Previewer

class KnowledgeTree(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Knowledge Tree")
        self.mw = mw
        vbox = QVBoxLayout()

        self.tree = TagTree(include_anki_tags = True, only_tags = False, knowledge_tree = True)
        self.tree.itemActivated.connect(self.tree_item_clicked)

        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setMinimumHeight(300)


    def tree_item_clicked(self, item, col):
        item_type = item.data(DataCol.Type, 1)

        # do not remove readily, enables smooth switching to tabbed Editor window on
        # macOS split-fullscreen
        self.mw.app.setActiveWindow(self.mw)

        if item_type == ItemType.AnkiCard:
            tag = item.data(DataCol.Name, 1)
            id = item.data(DataCol.NoteID, 1)
            note = mw.col
            note = mw.col.getNote(id)
            cards = note.cards()
            showInfo("Test")
        elif item_type == ItemType.SiacNote:


            id = item.data(DataCol.NoteID, 1)
            open_siac_with_id(id)
