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


from aqt.qt import *
import aqt.editor
import aqt
import functools
import re
import random
from aqt.utils import showInfo

from ..config import get_config_value_or_default

import utility.text
import utility.misc

class ExternalFile(QDialog):
    """ Set up a link to an external file which will be opened by the add-on. """

    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.chosen_file = None
        self.parent     = parent

        self.setup_ui()
        self.setWindowTitle("Choose external file")

    def setup_ui(self):
        # file types file://, safari://, etc
        vbox = QVBoxLayout()
        self.cb_type = QComboBox()

        fields_to_prefill = get_config_value_or_default("notes.editor.external_file_applications", [])
        
        self.cb_type.addItems(fields_to_prefill)

        vbox.addWidget(QLabel("""
            <i>Using file will open the selected file with the standard application for this file type.<br>
            Some applications allow opening of external files with the [application]:///file scheme.<br>
            You can add your own applications from the add-on config .json.</i>
        """))
        vbox.addWidget(self.cb_type)

        # choose file
        hbox = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setMinimumWidth(300)
        hbox.addWidget(self.input)
        self.but_file = QPushButton("Find File")
        self.but_file.clicked.connect(self.on_open_file)
        hbox.addWidget(self.but_file)

        vbox.addLayout(hbox)


        # accept reject button
        hbox_bot        = QHBoxLayout()
        self.accept_btn = QPushButton("Add File")
        self.accept_btn.setShortcut("Ctrl+Return")
        self.accept_btn.clicked.connect(self.accept_clicked)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addStretch(1)
        hbox_bot.addWidget(self.accept_btn)
        hbox_bot.addWidget(self.reject_btn)

        vbox.addSpacing(20)
        vbox.addLayout(hbox_bot)
        self.setLayout(vbox)

    def on_open_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Pick a File', '',"All (*)")
        if fname is not None:
            self.input.setText(fname[0])

    def accept_clicked(self):
        file_type = self.cb_type.currentText()
        source = self.input.text()

        self.chosen_file = file_type + ":///" + source
        self.accept()
