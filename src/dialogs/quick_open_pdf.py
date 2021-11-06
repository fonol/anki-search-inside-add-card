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
from ..notes import _get_priority_list
from ..dialogs.editor import NoteEditor
from ..web.reading_modal import Reader
from ..internals import perf_time
from ..state import get_index
from ..output import UI


import state

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
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
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
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox.addWidget(lbl)


        self.sug_list = QTableWidget()
        self.sug_list.setColumnCount(4)
        self.sug_list.setHorizontalHeaderLabels(["Title", "Type", "Prio", ""])
        self.sug_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sug_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sug_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sug_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.sug_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.sug_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sug_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sug_list.verticalHeader().setVisible(False)
        self.sug_list.setMinimumWidth(400)
        self.sug_list.setMinimumHeight(350)
        self.sug_list.setStyleSheet("""
            QTableWidget::item:hover {
                background-color: #2496dc;
                color: white;
            } 
        """)

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

        self.vbox.addSpacing(5)
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

        nid = get_last_opened_note_id()
        if nid is None:
            tooltip("No last opened note found in database!")
        else:
            self.chosen_id = nid
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
        self.sug_list.setRowCount(len(notes))
        self.sug_list.setHorizontalHeaderLabels(["Title", "Type", "Prio", ""])
        for ix, note in enumerate(notes):


            if ix < 9:
                title = QTableWidgetItem(f"{ix+1}.  {note.get_title()}")
            else:
                title = QTableWidgetItem(note.get_title())
            title.setData(Qt.ItemDataRole.UserRole, QVariant(note.id))

            ntype = QTableWidgetItem(note.get_note_type())
            if note.priority is None or note.priority == 0:
                prio  = QLabel("-")
            else:
                prio  = QLabel(str(int(note.priority)))
                prio.setStyleSheet(f"background-color: {utility.misc.prio_color(note.priority)}; color: white; font-size: 14px; text-align: center;")
            prio.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QToolButton()
            edit_btn.setText(u"\u270E")
            edit_btn.setToolTip("Edit")
            edit_btn.clicked.connect(partial(self.edit_btn_clicked, note.id))


            self.sug_list.setItem(ix, 0, title)
            self.sug_list.setItem(ix, 1, ntype)
            self.sug_list.setCellWidget(ix, 2, prio)
            self.sug_list.setCellWidget(ix, 3, edit_btn)

        self.sug_list.resizeRowsToContents()

    def edit_btn_clicked(self, nid):
        if Reader.note_id == nid:
            tooltip("Cannot edit that note: It is currently opened in the reader.")
            return
        if not state.note_editor_shown:
            NoteEditor(self.parent, nid, add_only=True, read_note_id=None)
            self.accept()

    def on_suggestion_clicked(self, item):
        self.chosen_id = self.displayed[item.row()].id
        self.accept()
    
   
    def on_input(self, text):
        if text is None or len(text.strip()) == 0:
            self.fill_result_list(self.suggestions)
        else:
            notes = find_notes(text)[:30]
            self.fill_result_list(notes)

