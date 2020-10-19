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
from .components import QtPrioritySlider, QtScheduleComponent
from ..notes import get_note, get_priority
from ..config import get_config_value_or_default

class DoneDialog(QDialog):

    def __init__(self, parent, note_id):
        QDialog.__init__(self, parent)
        self.note_id = note_id
        self.note = get_note(note_id)
        self.priority = get_priority(note_id)
        self.add_mode = False
        self.setup_ui()

    def setup_ui(self):
        shortcut = get_config_value_or_default("pdf.shortcuts.done", "CTRL+Y")
        # title is either 'Done' or 'Add', depending on whether the note was enqueued before
        if (self.priority and self.priority > 0) or self.note.is_or_was_due():
            title = "Done"
        else: 
            title = "Add"
            self.add_mode = True

        self.setWindowTitle(f"{title} ({shortcut})")
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.done_tab = DoneTab(self)
        self.tabs.addTab(self.done_tab, "Priority")
        self.schedule_tab = ScheduleTab(self)
        if not self.add_mode:
            self.tabs.addTab(self.schedule_tab, "Schedule")
        self.layout.addWidget(self.tabs)


        self.accept_btn = QPushButton(title)
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)
        self.hbox.addWidget(self.reject_btn)

        self.layout.addLayout(self.hbox)
        self.setLayout(self.layout)
        self.setMinimumWidth(300)
            
    def on_accept(self):
        self.priority = self.done_tab.slider.value()
        self.schedule = self.schedule_tab.scheduler._get_schedule()
        self.schedule_has_changed = self.schedule_tab.scheduler.schedule_has_changed()
        self.accept()

class DoneTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()
    
    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.slider = QtPrioritySlider(self.parent.priority, self.parent.note_id, False, None)
        self.layout.addWidget(self.slider)



class ScheduleTab(QWidget):
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.scheduler = QtScheduleComponent(self.parent.note.reminder)
        self.layout.addWidget(self.scheduler)
        self.setLayout(self.layout)