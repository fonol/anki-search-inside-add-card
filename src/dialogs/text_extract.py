# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.

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
import functools
from aqt.qt import *
from typing import List
from .components import ClickableQLabel

import utility.misc

class TextExtractDialog(QDialog):
    """Dialog to pick a field to send the selected text to."""

    def __init__(self, parent, field_names: List[str]):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.mw                 = aqt.mw
        self.parent             = parent
        self.field_names        = field_names
        self.chosen_field       = None
        self.chosen_field_ix    = None

        self.setup_ui()
        self.setWindowTitle("Send selection to field")

    def setup_ui(self):

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Fields"))

        for f in self.field_names:
            lbl = ClickableQLabel(f)
            lbl.clicked.connect(functools.partial(self.field_clicked, f))
            vbox.addWidget(lbl)

        hbox_bot = QHBoxLayout()
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addStretch(1)
        hbox_bot.addWidget(self.reject_btn)
        self.vbox.addLayout(hbox_bot)
        self.setLayout(vbox)

    def field_clicked(self, field_name: str):
        self.chosen_field_ix    = self.field_names.index(field_name)
        self.chosen_field       = field_name
        self.accept()

