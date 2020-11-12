from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *
from aqt.utils import showInfo
import utility.misc

import state
from ..notes import get_all_tags_as_hierarchy
from ..utility.tag_tree import TagTree, DataCol, ItemType

class KnowledgeTree(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Knowledge Tree")
        vbox = QVBoxLayout()

        self.tree = TagTree(include_anki_tags = True, only_tags = False, knowledge_tree = True)
        self.tree.itemActivated.connect(self.tree_item_clicked)

        vbox.addWidget(self.tree)
        self.setLayout(vbox)
        self.setMinimumHeight(300)


    def tree_item_clicked(self, item, col):
        tag = item.data(DataCol.Name, 1)
        if item.data(DataCol.Type, 1) == ItemType.AnkiCard:
            showInfo(tag)
