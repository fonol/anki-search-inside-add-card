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
from aqt.utils import tooltip
import typing
from typing import Optional
import functools
import os
from .components import QtPrioritySlider, QtScheduleComponent, NoteSelectorMode, NoteSelector
from ..notes import get_note, get_priority, get_last_priority, len_enqueued_with_tag
from ..config import get_config_value_or_default

class DoneDialog(QDialog):

    last_tag_filter : Optional[str] = None

    def __init__(self, parent, note_id):
        QDialog.__init__(self, parent)

        self.note_id            = note_id
        self.note               = get_note(note_id)
        self.priority           = get_priority(note_id)

        last_priority           = get_last_priority(note_id)

        if self.priority is None:
            self.priority = last_priority

        self.add_mode           = False
        self.enqueue_next_ids   = []
        self.enqueue_next_prio  = -1
        self.tag_filter         = ""
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

        self.layout         = QVBoxLayout()
        self.tabs           = QTabWidget()
        self.done_tab       = DoneTab(self)
        self.tabs.addTab(self.done_tab, "Priority")
        self.schedule_tab   = ScheduleTab(self)
        if not self.add_mode:
            self.tabs.addTab(self.schedule_tab, "Schedule")
            self.enqueue_next_tab = EnqueueNextTab(self)
            self.tabs.addTab(self.enqueue_next_tab, "Enqueue Next")
        self.layout.addWidget(self.tabs)


        self.accept_btn = QPushButton(title)
        self.accept_btn.clicked.connect(self.on_accept)

        self.accept_btn.setShortcut(QKeySequence("Ctrl+Return"))
        self.accept_btn.setToolTip("Ctrl+Return")

        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)
        self.hbox.addWidget(self.reject_btn)

        self.layout.addLayout(self.hbox)
        self.setLayout(self.layout)
        self.accept_btn.setFocus()
        self.setMinimumWidth(300)

    def on_accept(self):
        self.priority               = self.done_tab.slider.value()
        self.tag_filter             = self.done_tab.tag_filter_inp.text()
        self.schedule               = self.schedule_tab.scheduler._get_schedule()
        self.schedule_has_changed   = self.schedule_tab.scheduler.schedule_has_changed()
        if not self.add_mode:
            self.enqueue_next_ids   = self.enqueue_next_tab.note_selector.selected_ids
            self.enqueue_next_prio  = self.enqueue_next_tab.slider.value()

        DoneDialog.last_tag_filter  = self.tag_filter
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

        #
        # Tag filter
        #
        box                 = QGroupBox("Filter: Tags")
        box.setObjectName("tag_filter_gb")
        box.setStyleSheet("QGroupBox#tag_filter_gb { }")
        tag_filter_hb       = QHBoxLayout()
        self.tag_filter_inp = QLineEdit()
        self.tag_filter_cb  = QPushButton("Tags...")
        menu                = QMenu(self.tag_filter_cb)

        tag_filter_hb.addWidget(self.tag_filter_inp)
        tag_filter_hb.setSpacing(0)
        tags                = self.parent.note.tags
        used                = []

        self.tag_filter_inp.textChanged.connect(self.on_tag_filter_change)

        if tags is not None:
            for t in tags.split(" "):
                if len(t.strip()) == 0:
                    continue
                t   = t.strip()
                subtags = t.split("::")
                for n in range(1, max(2, len(subtags))):
                    l = [subtags[0:i+n] for i in range(len(subtags)-n+1)]
                    for sl in l:
                        joined = "::".join(sl)
                        if not joined in used:
                            used.append(joined)

            for t in used:
                a = menu.addAction(t)
                a.triggered.connect(functools.partial(self.add_tag_to_filter, t))

        self.tag_filter_cb.setMenu(menu)

        clear_btn = QToolButton()
        clear_btn.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        clear_btn.clicked.connect(self.clear_tag_filter)
        tag_filter_hb.addSpacing(2)
        tag_filter_hb.addWidget(clear_btn)
        tag_filter_hb.addSpacing(8)

        tag_filter_hb.addWidget(self.tag_filter_cb)
        tag_filter_vb = QVBoxLayout()
        tag_filter_vb.addLayout(tag_filter_hb)
        self.tag_filter_lbl = QLabel("If set, next opened note must have at least one matching tag.")
        tag_filter_vb.addSpacing(5)
        tag_filter_vb.addWidget(self.tag_filter_lbl)
        box.setLayout(tag_filter_vb)
        self.layout.addStretch()
        self.layout.addWidget(box)

        self.tf_box = box

        if DoneDialog.last_tag_filter is not None and len(DoneDialog.last_tag_filter.strip()) > 0:
            self.tag_filter_inp.setText(DoneDialog.last_tag_filter)
        else:
            self.tag_filter_inp.setText("") # to trigger on_tag_filter_change

    def on_tag_filter_change(self):
        value = self.tag_filter_inp.text()
        if value and len(value.strip()) > 0:
            c = len_enqueued_with_tag([t.strip() for t in value.split(" ") if len(t.strip()) > 0])
            self.tag_filter_lbl.setText(f"<b>{c}</b> queued note(s) with at least one matching tag.")
            if c > 0:
                self.tf_box.setStyleSheet("QGroupBox#tag_filter_gb::title { color: white; background: #0496dc; border-radius: 3px; padding: 2px; }")
            else:
                self.tf_box.setStyleSheet("QGroupBox#tag_filter_gb::title { color: black; background: #f0506e; border-radius: 3px; padding: 2px; }")
        else:
            self.tag_filter_lbl.setText(f"If set, next opened note must have at least one matching tag.")
            self.tf_box.setStyleSheet("QGroupBox#tag_filter_gb::title {  border-radius: 3px; padding: 2px; }")

    def clear_tag_filter(self):
        self.tag_filter_inp.setText("")

    def add_tag_to_filter(self, tag):
        current = self.tag_filter_inp.text()
        if not current:
            self.tag_filter_inp.setText(tag + " ")
        else:
            tags = [t.strip() for t in current.split(" ") if len(t.strip()) > 0]
            if not tag in tags:
                self.tag_filter_inp.setText(current.strip() + " " + tag)



class EnqueueNextTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.layout         = QVBoxLayout()
        self.setLayout(self.layout)
        self.note_selector  = NoteSelector(self, NoteSelectorMode.UNQUEUED, nid=self.parent.note_id)
        self.layout.addWidget(self.note_selector)
        self.slider         = QtPrioritySlider(self.parent.priority, None, False, None)
        self.slider.slider.setMinimum(1)
        self.layout.addWidget(self.slider)


class ScheduleTab(QWidget):
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.layout.addSpacing(15)
        self.scheduler = QtScheduleComponent(self.parent.note.reminder)
        self.layout.addWidget(self.scheduler)
        self.setLayout(self.layout)
