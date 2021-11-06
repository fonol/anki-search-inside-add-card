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


from aqt.qt import *
import aqt.editor
import aqt
import functools
import typing
from typing import List

import utility.text
import utility.misc

class TagAssignDialog(QDialog):
    """ Fetch a URL to load the page into the note text. """

    def __init__(self, parent, nids: List[int]):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.tags       = None
        self.parent     = parent

        self.setup_ui()
        self.setWindowTitle("Tag Assign")

    def setup_ui(self):

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(QLabel("This will assign the given tag(s) to all selected notes (if not already present)."))
        self.vbox.addSpacing(10)

        self.vbox.addWidget(QLabel("Tags(s):"))
        self.input = QLineEdit()
        self.input.setMinimumWidth(300)
        self.vbox.addWidget(self.input)
        self.vbox.addSpacing(15)

        hbox_bot = QHBoxLayout()
        self.accept_btn = QPushButton("Ok")
        self.accept_btn.setShortcut("Ctrl+Return")
        self.accept_btn.clicked.connect(self.accept_clicked)

        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addStretch(1)
        hbox_bot.addWidget(self.accept_btn)
        hbox_bot.addWidget(self.reject_btn)
        self.vbox.addLayout(hbox_bot)

        self.setLayout(self.vbox)
      
    def accept_clicked(self):
        self.tags = self.input.text()
        self.accept()


