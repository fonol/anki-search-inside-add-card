from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *


import state
from ..notes import get_all_tags_as_hierarchy
from .misc import get_web_folder_path

class DataCol():
    Name      = 1
    Type      = 2
    Deck      = 3
    Notetype  = 4

class ItemType():
    AnkiCard = 0

class TagTree(QTreeWidget):
    def __init__(self, include_anki_tags = True, only_tags = False, knowledge_tree = False):
        super().__init__()

        self.include_anki_tags = include_anki_tags
        self.only_tags         = only_tags

        # load icon paths/icons
        web_path                = get_web_folder_path()
        icons_path              = web_path + "icons/"

        self.tag_icon           = QIcon(icons_path + "icon-tag-24.png")
        self.pdfsiac_icon       = QIcon(icons_path + "icon-pdf-24.png")
        self.ytsiac_icon        = QIcon(icons_path + "icon-yt-24.png")

        config = mw.addonManager.getConfig(__name__)
        if state.night_mode:
            tag_bg                  = config["styles.night.tagBackgroundColor"]
            tag_fg                  = config["styles.night.tagForegroundColor"]
        else:
            tag_bg                  = config["styles.tagBackgroundColor"]
            tag_fg                  = config["styles.tagForegroundColor"]

        self.build_the_tree(get_all_tags_as_hierarchy(include_anki_tags=include_anki_tags))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(150)
        self.setMinimumWidth(220)

        if knowledge_tree:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.setColumnCount(2)
            self.setHeaderLabels(["Item", "Deck"])
            self.setHeaderHidden(False)
            self.setColumnWidth(0, 300)
            self.setColumnWidth(1,80)
        else:
            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setColumnCount(1)
            self.setHeaderHidden(True)


        vline_icn = icons_path + ('vline-night' if state.night_mode else 'vline')
        branch_more_icn = icons_path + ('branch-more-night' if state.night_mode else 'branch-more')
        branch_end_icn = icons_path + ('branch-end-night' if state.night_mode else 'branch-end')
        branch_closed_icn = icons_path + ('branch-closed-night' if state.night_mode else 'branch-closed')
        branch_open_icn = icons_path + ('branch-open-night' if state.night_mode else 'branch-open')

        stylesheet = f"""
            QTreeWidget::branch:has-siblings:!adjoins-item {{
                border-image: url({vline_icn}.png) 0;
            }}
            QTreeWidget::branch:has-siblings:adjoins-item {{
                border-image: url({branch_more_icn}.png) 0;
            }}
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
                border-image: url({branch_end_icn}.png) 0;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                    border-image: none;
                    image: url({branch_closed_icn}.png);
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings  {{
                    border-image: none;
                    image: url({branch_open_icn}.png);
            }}
        """

        if not knowledge_tree:
            stylesheet += f"""
                QTreeWidget::item:hover,QTreeWidget::item:hover:selected,QTreeWidget::item:selected {{
                    border:none;
                    border-radius:5px;
                    font-weight: bold;
                    background-color: {tag_bg};
                    color: {tag_fg};
                }}
            """

        self.setStyleSheet(stylesheet)

    def build_the_tree(self, tmap):
        for t, children in tmap.items():
            ti = QTreeWidgetItem([t])
            ti.setData(DataCol.Name, 1, QVariant(t))
            ti.setIcon(0, self.tag_icon)
            ti.addChildren(self._add_to_tree(children, t + "::"))

            if not self.only_tags:
                self.add_all_cards_with_tags(ti)

            self.addTopLevelItem(ti)

    def _add_to_tree(self, map, prefix):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setData(DataCol.Name, 1, QVariant(prefix + t))
            ti.setIcon(0, self.tag_icon)
            prefix_c = prefix + t + "::"

            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            if not self.only_tags:
                self.add_all_cards_with_tags(ti)

            res.append(ti)
        return res

    def add_all_cards_with_tags(self, ti):
        tag_name = ti.data(1,1)
        ids = mw.col.find_notes(f"""tag:{tag_name} -"tag:{tag_name}::*" """)
        for id in ids:
            note = mw.col.getNote(id)
            nt = note.model()
            key = nt["flds"][mw.col.models.sortIdx(nt)]
            data = note[key["name"]]
            #text = (data[:75] + '...') if len(data) > 78 else data
            text = data
            text = text.replace('\n', ' ')

            child = QTreeWidgetItem([text, "test"])
            child.setData(DataCol.Name, 1, text)
            child.setData(DataCol.Type, 1, ItemType.AnkiCard)

            ti.addChild(child)
