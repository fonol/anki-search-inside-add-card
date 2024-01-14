# anki-search-inside-add-card
# Copyright (C) 2019 - 2021 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import aqt
from aqt.qt import *
from ..notes import get_all_tags
from ..config import get_config_value_or_default, update_config
from ..utility.tag_tree import TagTree
import utility.misc

class TagChooserDialog(QDialog):
    """Dialog for choosing the appropriate tag from the note editor"""

    def __init__(self, tag_string, parent):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.mw             = aqt.mw
        self.parent         = parent
        self.tag_string     = tag_string

        self.setup_ui()
        self.setWindowTitle("Tag Chooser")

    def setup_ui(self):
        include_anki_tags   = get_config_value_or_default("notes.editor.include_anki_tags", False)
        tag_sort            = get_config_value_or_default("notes.editor.tag_sort", "a-z")

        vbox = QVBoxLayout()

        tag_lbl = QLabel()
        tag_icn = QPixmap(utility.misc.get_web_folder_path() + "icons/icon-tag-24.png").scaled(14,14)
        tag_lbl.setPixmap(tag_icn)

        tag_hb = QHBoxLayout()
        tag_hb.setAlignment(Qt.AlignmentFlag.AlignLeft)
        tag_hb.addWidget(tag_lbl)
        tag_hb.addWidget(QLabel("Tags (Click to Add)"))

        vbox.addLayout(tag_hb)

        self.tree = TagTree(include_anki_tags = include_anki_tags, only_tags = True, knowledge_tree = False, sort=tag_sort)
        self.tree.itemClicked.connect(self.tree_item_clicked)

        vbox.addWidget(self.tree)

        self.all_tags_cb = QCheckBox("Include Anki Tags")
        self.all_tags_cb.setChecked(include_anki_tags)
        self.all_tags_cb.stateChanged.connect(self.tag_cb_changed)
        hbox_tag_b = QHBoxLayout()
        hbox_tag_b.addWidget(self.all_tags_cb)

        self.tag_sort = QComboBox()
        self.tag_sort.addItem("A-Z")
        self.tag_sort.addItem("Recency")
        self.tag_sort.currentTextChanged.connect(self.on_tag_sort_change)
        self.tag_sort.setCurrentText(tag_sort)
        hbox_tag_b.addStretch(10)
        hbox_tag_b.addWidget(QLabel("Sort: "))
        hbox_tag_b.addWidget(self.tag_sort)


        hbox_tag_b.addStretch(1)
        vbox.addLayout(hbox_tag_b)

        self.tag = QLineEdit()
        tags = get_all_tags()
        if tags:
            completer = QCompleter(tags)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.tag.setCompleter(completer)
        vbox.addWidget(self.tag)
        if self.tag_string is not None:
            self.tag.setText(self.tag_string)


        vbox.addSpacing(15)

        hbox_bot = QHBoxLayout()
        self.accept_btn = QPushButton("Set Tags")
        self.accept_btn.setShortcut("Ctrl+Return")
        self.accept_btn.clicked.connect(self.accept_clicked)

        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        hbox_bot.addWidget(self.accept_btn)
        hbox_bot.addWidget(self.reject_btn)
        vbox.addLayout(hbox_bot)

        self.setLayout(vbox)

    def tree_item_clicked(self, item, col):
        tag = item.data(1, 1)
        self.add_tag(tag)

        def add_tag(self, tag):
            if tag is None or len(tag.strip()) == 0:
                return
            existing = self.tag.text().split()
            if tag in existing:
                return
            existing.append(tag)
            existing = sorted(existing)
            self.tag.setText(" ".join(existing))

    def tag_cb_changed(self, state):
        self.tree.include_anki_tags = (state == Qt.CheckState.Checked)
        self.tree.rebuild_tree()
        update_config("notes.editor.include_anki_tags", state == Qt.CheckState.Checked)

    def on_tag_sort_change(self, new_sort: str):
        self.tree.sort = new_sort.lower()
        self.tree.rebuild_tree()
        update_config("notes.editor.tag_sort", new_sort)

    def add_tag(self, tag):
        if tag is None or len(tag.strip()) == 0:
            return
        existing = self.tag.text().split()
        if tag in existing:
            return
        existing.append(tag)
        existing = sorted(existing)
        self.tag.setText(" ".join(existing))


    def accept_clicked(self):
        self.chosen_tag = self.tag.text()
        self.accept()
