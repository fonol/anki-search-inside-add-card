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
import aqt
import random
import os
from functools import partial
from ..notes import *
from ..notes import _get_priority_list
from ..internals import perf_time
import utility.text
import utility.misc
import utility.tags




class QuickOpenPDF(QDialog):
    """
        Allows to search for a pdf note and open it.
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
        self.setWindowTitle("Quick Open: PDF")
        
       
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

        self.accept_btn = QPushButton("Cancel")
        self.accept_btn.clicked.connect(self.accept)
        self.vbox.addWidget(self.accept_btn)

        self.setLayout(self.vbox)

        for i in range(min(9,len(self.suggestions))):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self, activated=partial(self.accept_nth, i))


    def accept_nth(self, n):
        self.chosen_id = self.displayed[n].id
        self.accept()
 
        
    def fill_result_list(self, notes):
        self.sug_list.clear()
        self.displayed = notes
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
            notes = find_pdf_notes_by_title(text)
            self.fill_result_list(notes)

