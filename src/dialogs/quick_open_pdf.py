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
import aqt
import random
import typing
import os
from functools import partial
from ..notes import *
from ..web.reading_modal import ReadingModal
from ..notes import _get_priority_list
from ..internals import perf_time

from .components import ClickableQLabel

import utility.text
import utility.misc
import utility.tags




class QuickOpenNote(QDialog):
    """
        Allows to search for an add-on note and open it.
    """
    def __init__(self, parent):
        self.chosen_id = None 
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        try:
            self.dark_mode_used = utility.misc.dark_mode_is_used(aqt.mw.addonManager.getConfig(__name__))
        except:
            self.dark_mode_used = False
        self.setup_ui()
        self.setWindowTitle("Quick Open")
        
       
    def setup_ui(self):

        self.suggestions = get_pdf_quick_open_suggestions()
        self.vbox = QVBoxLayout()

        self.input = QLineEdit()
        self.vbox.addWidget(self.input)
        self.input.textChanged.connect(self.on_input)
        self.input.setFocus()

        lbl = QLabel("Ctrl + <Number>") 
        lbl.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(lbl)


        self.sug_list = QListWidget()
        self.sug_list.itemClicked.connect(self.on_suggestion_clicked)
        self.fill_result_list(self.suggestions)       

        self.vbox.addWidget(self.sug_list)

        lbl_1 = ClickableQLabel(hover_effect=True)
        lbl_1.setText("<b>Ctrl + F</b>: Open First in Queue")
        lbl_1.clicked.connect(self.open_head)
        self.vbox.addWidget(lbl_1)
        lbl_2 = ClickableQLabel(hover_effect=True)
        lbl_2.setText("<b>Ctrl + R</b>: Open Random Note")
        lbl_2.clicked.connect(self.open_random)
        self.vbox.addWidget(lbl_2)
        lbl_3 = ClickableQLabel(hover_effect=True)
        lbl_3.setText("<b>Ctrl + L</b>: Open Last Opened Note")
        lbl_3.clicked.connect(self.open_last)
        self.vbox.addWidget(lbl_3)

        self.accept_btn = QPushButton("Cancel")
        self.accept_btn.clicked.connect(self.accept)
        self.vbox.addWidget(self.accept_btn)

        self.setLayout(self.vbox)

        for i in range(min(9,len(self.suggestions))):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self, activated=partial(self.accept_nth, i))

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.open_head)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.open_random)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.open_last)


    def open_head(self):
        h = get_head_of_queue()
        if h is None or h < 0:
            tooltip("Queue is empty")
        else:
            self.chosen_id = h
            self.accept()

    def open_random(self):
        id = get_random_id()
        if id is None or id < 0:
            tooltip("You have no notes")
        else:
            self.chosen_id = id
            self.accept()

    def open_last(self):
        if ReadingModal.last_opened is None:
            tooltip("No last opened note in this session!")
        else:
            self.chosen_id = ReadingModal.last_opened
            self.accept()

    def accept_nth(self, n):
        if n == -1 or n >= len(self.displayed):
            return
        self.chosen_id = self.displayed[n].id
        self.accept()
 
        
    def fill_result_list(self, notes):
        self.sug_list.clear()
        self.displayed = notes
        if notes is None:
            self.displayed = []
            return
        for ix, note in enumerate(notes):
            if ix < 9:
                item = QListWidgetItem(f"[{ix+1}] {note.get_title()}")
            else:
                item = QListWidgetItem(f"{note.get_title()}")
            item.setData(Qt.UserRole, QVariant(note.id))
            self.sug_list.addItem(item)

    def on_suggestion_clicked(self, item):
        self.chosen_id = item.data(Qt.UserRole)
        self.accept()
    
   
    def on_input(self, text):
        if text is None or len(text.strip()) == 0:
            self.fill_result_list(self.suggestions)
        else:
            notes = find_notes(text)
            self.fill_result_list(notes)

