from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *
from aqt.utils import showInfo
import utility.misc

from ..state import get_index

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

        self.le_search = QLineEdit()
        self.le_search.returnPressed.connect(self.search_executed)
        vbox.addWidget(self.le_search)

        self.tree = TagTree(include_anki_tags = True, only_tags = False, knowledge_tree = True)
        self.tree.itemActivated.connect(self.tree_item_clicked)

        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        #self.setSizePolicy(Qt.)
        #TODO: clever size policy for opening with y = fullscreen
        self.setMinimumHeight(700)

    def search_executed(self):
        text = self.le_search.text()
        get_index().search(text, decks = ["-1"], knowledge_tree = self)


    def get_search_results_back(self, result, stamp):
        if result is not None and len(result) > 0:
            self.tree.rebuild_tree(result["results"])
        else:
            self.tree.rebuild_tree()


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
