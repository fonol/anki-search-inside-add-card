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
from aqt.utils import tooltip
import typing
import os
from .components import QtPrioritySlider
from ..notes import get_priority

class PriorityDialog(QDialog):

    def __init__(self, parent, note_id):
        QDialog.__init__(self, parent)
        self.note_id        = note_id
        self.initial_prio   = get_priority(note_id)
        if self.initial_prio is None or self.initial_prio == 0:
            self.initial_prio = 50
            self.setWindowTitle("Choose a priority")
        else:
            self.setWindowTitle("Edit priority")
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.slider = QtPrioritySlider(self.initial_prio, self.note_id, False, None)
        self.layout.addWidget(self.slider)

        self.accept_btn = QPushButton("Ok")
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)
        self.hbox.addWidget(self.reject_btn)

        self.layout.addLayout(self.hbox)
        self.setMinimumWidth(300)
            
            
    def on_accept(self):
        if self.slider.value() == 0:
            tooltip("Value must be > 0")
        else:
            self.value = self.slider.value()
            self.accept()