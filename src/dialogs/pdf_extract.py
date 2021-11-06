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
import aqt
import json

from ..output import UI
from ..notes import create_note, get_priority, get_extracts
from ..hooks import run_hooks
from ..web.reading_modal import Reader
from .components import QtPrioritySlider

class PDFExtractDialog(QDialog):
    """ Allows to specify a range of pages to create an pdf extract of. """

    def __init__(self, parent, current_page, pages_total, note):

        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.extract_start  = None
        self.extract_end    = None
        self.current_page   = current_page
        self.pages_total    = pages_total
        self.note           = note
        self.prio_default   = get_priority(note.id)
        self.mw             = aqt.mw
        self.parent         = parent
        self.setup_ui()
        self.setWindowTitle("Extract")


    def setup_ui(self):

        self.vbox = QVBoxLayout()

        self.vbox.addWidget(QLabel("Title"))
        self.title_inp = QLineEdit()
        self.title_inp.setText(self.note.title)
        self.vbox.addWidget(self.title_inp)

        self.vbox.addWidget(QLabel("Tags"))
        self.tags_inp = QLineEdit()
        self.tags_inp.setText(self.note.tags)
        self.vbox.addWidget(self.tags_inp)

        self.start_inp = QSpinBox()
        self.start_inp.setMinimum(1)
        self.start_inp.setMaximum(max(1, self.pages_total - 1))
        self.start_inp.setValue(self.current_page)

        self.end_inp    = QSpinBox()
        self.end_inp.setMinimum(1)
        self.end_inp.setMaximum(self.pages_total)
        self.end_inp.setValue(self.current_page)

        self.start_inp.valueChanged.connect(self.start_value_changed)
        self.end_inp.valueChanged.connect(self.end_value_changed)

        hb = QHBoxLayout()
        hb.addStretch(1)
        hb.addWidget(QLabel("Pages (end inclusive): "))
        hb.addWidget(self.start_inp)
        hb.addWidget(QLabel(" - "))
        hb.addWidget(self.end_inp)
        hb.addStretch(1)
        self.vbox.addSpacing(10)
        self.vbox.addLayout(hb)

        self.scheduler = QtPrioritySlider(self.prio_default, self.note.id, True, self.note.reminder)
        self.vbox.addWidget(self.scheduler)

        bhb = QHBoxLayout()
        bhb.addStretch(1)

        self.accept_btn = QPushButton("Create")
        self.accept_btn.clicked.connect(self.accept_clicked)
        bhb.addWidget(self.accept_btn)
        self.vbox.addLayout(bhb)

        self.setLayout(self.vbox)
        self.show()

    def start_value_changed(self, new_value: int):
        if self.end_inp.value() < new_value:
            self.end_inp.setValue(new_value)

    def end_value_changed(self, new_value: int):
        if self.start_inp.value() > new_value:
            self.start_inp.setValue(new_value)

    def accept_clicked(self):
        self.extract_start  = self.start_inp.value()
        self.extract_end    = self.end_inp.value()

        if self.extract_end < self.extract_start:
            tooltip("Invalid range!")
            return

        self.create_extract()

        # if we have a pdf displayed, send the updated extract info to the js,
        # and reload the page
        if Reader.note_id and Reader.note.is_pdf():
            extracts = get_extracts(Reader.note_id, Reader.note.source)
            UI.js(f"pdf.extractExclude={json.dumps(extracts)}; refreshPDFPage();")

        run_hooks("user-note-created")
        run_hooks("updated-schedule")
        self.accept()

    def create_extract(self):

        title = self.title_inp.text()
        new_id = create_note(title, "", self.note.source, self.note.tags, self.note.nid, self.scheduler.schedule(), self.scheduler.value(), self.note.author, url = self.note.url, extract_start = self.extract_start, extract_end = self.extract_end)
