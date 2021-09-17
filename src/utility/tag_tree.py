from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *


import state
from ..notes import get_all_tags_as_hierarchy, get_tags_and_nids_from_search, find_by_tag
from .misc import get_web_folder_path
import utility.tags

class DataCol():
    Name      = 1
    Type      = 2
    Deck      = 3
    Notetype  = 4
    NoteID    = 5

class ItemType():
    AnkiCard  = 0
    SiacNote  = 1

class TagTree(QTreeWidget):
    def __init__(self, include_anki_tags = True, only_tags = False, knowledge_tree = False, sort="a-z"):
        super().__init__()

        self.include_anki_tags = include_anki_tags
        self.only_tags         = only_tags
        self.knowledge_tree    = knowledge_tree
        self.sort              = sort


        self.map                = get_all_tags_as_hierarchy(include_anki_tags=include_anki_tags, sort=self.sort)

        # only show selected notes
        self.nids_anki_whitelist = None
        self.nids_siac_whitelist = None

        # load icon paths/icons
        web_path                = get_web_folder_path()
        icons_path              = web_path + "icons/"

        self.tag_icon           = QIcon(icons_path + "icon-tag-24.png")
        self.pdfsiac_icon       = QIcon(icons_path + "icon-pdf-24.png")
        self.ytsiac_icon        = QIcon(icons_path + "icon-yt-24.png")
        self.mdsiac_icon        = QIcon(icons_path + "icon-markdown-24.png")
        self.cards_icon         = QIcon(icons_path + "icon-cards-24.png")

        config = mw.addonManager.getConfig(__name__)
        if state.is_nightmode():
            tag_bg                  = config["styles.night.tagBackgroundColor"]
            tag_fg                  = config["styles.night.tagForegroundColor"]
        else:
            tag_bg                  = config["styles.tagBackgroundColor"]
            tag_fg                  = config["styles.tagForegroundColor"]

        self.recursive_build_tree(self.map)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(150)
        self.setMinimumWidth(220)

        if self.knowledge_tree:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)
            self.setColumnCount(2)
            self.setHeaderLabels(["Item", "Deck"])
            self.setHeaderHidden(False)
            self.setColumnWidth(0, 300)
            self.setColumnWidth(1,80)

            self.itemExpanded.connect(self.item_expanded)
        else:
            self.setSelectionMode(QAbstractItemView.NoSelection)
            self.setColumnCount(1)
            self.setHeaderHidden(True)


        vline_icn         = icons_path + ('vline-night'         if state.is_nightmode() else 'vline')
        branch_more_icn   = icons_path + ('branch-more-night'   if state.is_nightmode() else 'branch-more')
        branch_end_icn    = icons_path + ('branch-end-night'    if state.is_nightmode() else 'branch-end')
        branch_closed_icn = icons_path + ('branch-closed-night' if state.is_nightmode() else 'branch-closed')
        branch_open_icn   = icons_path + ('branch-open-night'   if state.is_nightmode() else 'branch-open')

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

        # add cool hover effect with user-defined tag colour when used in note editor
        if not self.knowledge_tree:
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

    def rebuild_tree(self, notes = None):
        self.clear()
        self.nids_anki_whitelist = None
        self.nids_siac_whitelist = None
        
        if notes == None:
            self.map = get_all_tags_as_hierarchy(include_anki_tags = self.include_anki_tags, sort=self.sort)
            self.recursive_build_tree(self.map)
        else:
            tags, self.nids_anki_whitelist, self.nids_siac_whitelist = get_tags_and_nids_from_search(notes)
            tag_hierarchy = utility.tags.to_tag_hierarchy(tags)
            self.map = tag_hierarchy
            self.recursive_build_tree(tag_hierarchy)

    def recursive_build_tree(self, map, prefix = "", toplevel = True):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setData(DataCol.Name, 1, QVariant(prefix + t))
            ti.setIcon(0, self.tag_icon)
            prefix_c = prefix + t + "::"

            # if we are on toplevel, we insert an empty placeholder
            # the child items of a top level item are loaded on expansion
            # better performance
            if self.knowledge_tree and toplevel:
                c = QTreeWidgetItem([""])
                c.setHidden(True)
                ti.addChildren([c])
            else:
                for c,m in children.items():
                    ti.addChildren(self.recursive_build_tree({c: m}, prefix_c, toplevel = False))
                self.add_siacnotes_and_anki_cards(ti, prefix, t)

            res.append(ti)

            if toplevel:
                self.addTopLevelItem(ti)

        return res

    def item_expanded(self, item):
        """ Load the children of an expanded item on expansion,
            only applies if the item is a toplevel (root) item,
            only applies if knowledge tree.
         """

        if not self.knowledge_tree:
            return
        if item.childCount() == 1 and item.child(0).text(0) == "":
            item.takeChild(0)
            prefix = item.data(DataCol.Name, 1)
            children = self.map[prefix]
            for c,m in children.items():
                item.addChildren(self.recursive_build_tree({c: m}, prefix + "::", toplevel = False))
            self.add_siacnotes_and_anki_cards(item, "", prefix)

    def add_siacnotes_and_anki_cards(self, ti, prefix, t):
        if self.knowledge_tree:
            self._add_siac_with_tag(ti)

            ac = QTreeWidgetItem()
            ac.setData(DataCol.Name, 1, prefix + t)

            if self._add_anki_with_tag(ac):
                ti.addChild(ac)

    def _add_siac_with_tag(self, ti):
        tag_name = ti.data(DataCol.Name, 1)

        notes = find_by_tag(tag_name, only_explicit_tag = True)

        for note in notes:
            if self.nids_siac_whitelist and note.id not in self.nids_siac_whitelist:
                continue
            title = note.title
            id = note.id
            child = QTreeWidgetItem([title])

            child.setData(DataCol.Name, 1, title)
            child.setData(DataCol.Type, 1, ItemType.SiacNote)
            child.setData(DataCol.NoteID, 1, id)

            if note.is_pdf():
                child.setIcon(0, self.pdfsiac_icon)
            elif note.is_yt():
                child.setIcon(0, self.ytsiac_icon)
            else:
                child.setIcon(0, self.mdsiac_icon)


            ti.addChild(child)

    def _add_anki_with_tag(self, ti):
        tag_name = ti.data(DataCol.Name,1)
        ids = mw.col.find_notes(f"""tag:{tag_name} -"tag:{tag_name}::*" """)
        i = 0

        for id in intersect_nids(ids, self.nids_anki_whitelist):
            i += 1
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
            child.setData(DataCol.NoteID, 1, id)

            ti.addChild(child)
        if i == 0:
            return False

        ti.setText(0, f"""All Notes ({i})""")
        ti.setIcon(0, self.cards_icon)
        return True


# helper function
def intersect_nids(nids1_keep, nids2_ifnotempty):
    if nids2_ifnotempty is None:
        return nids1_keep
    else:
        return set(nids1_keep).intersection(nids2_ifnotempty)
