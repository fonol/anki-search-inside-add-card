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

import csv

from ...notes import *
from ...config import get_config_value_or_default
import utility.text
import utility.misc
from ..components import QtPrioritySlider

class ZoteroImporter(QDialog):
    """ Create pdf notes from a Zotero exported CSV file. """

    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.queue_schedule = 0
        self.mw             = aqt.mw
        self.parent         = parent
        self.total_count    = 0

        self.setup_ui()
        self.setWindowTitle("Zotero Import")

    def setup_ui(self):

        self.vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Zotero CSV export file:"))
        self.file_path_disp = QLineEdit()
        self.file_path_disp.setDisabled(True)
        hbox.addWidget(self.file_path_disp)
        pick_file_btn = QPushButton("Choose File")
        pick_file_btn.clicked.connect(self.pick_file)
        hbox.addWidget(pick_file_btn)

        self.vbox.addLayout(hbox)

        self.status = QLabel("")
        self.vbox.addWidget(self.status)

        self.vbox.addWidget(QLabel("Add the following tags to all generated notes:"))
        self.tags = QLineEdit()
        self.vbox.addWidget(self.tags)

        self.oi_cb = QCheckBox("Add ISBN/ISSN/DOI to title if possible")
        self.vbox.addWidget(self.oi_cb)

        self.gb = QGroupBox("Duplicate file paths")
        gb_vbox = QVBoxLayout()
        self.dup_radio_1 = QRadioButton("Skip if duplicate")
        self.dup_radio_1.setChecked(True)
        self.dup_radio_2 = QRadioButton("Overwrite if duplicate")
        gb_vbox.addWidget(self.dup_radio_1)
        gb_vbox.addWidget(self.dup_radio_2)
        self.gb.setLayout(gb_vbox)
        self.vbox.addWidget(self.gb)

        self.slider = QtPrioritySlider(0, None)
        self.vbox.addWidget(self.slider)
        self.vbox.addSpacing(15)

        hbox_bot = QHBoxLayout()
        self.accept_btn = QPushButton("Import")
        self.accept_btn.setDisabled(True)
        self.accept_btn.setShortcut("Ctrl+Return")
        self.accept_btn.clicked.connect(self.accept_clicked)

        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addWidget(self.accept_btn)
        hbox_bot.addWidget(self.reject_btn)
        self.vbox.addLayout(hbox_bot)

        self.resize(350, 350)
        self.setLayout(self.vbox)
        btn_styles = """
        QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_3,QPushButton:hover#q_4,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: lightblue; }
        """
        styles = """
            %s
            QPushButton#q_1,QPushButton#q_2,QPushButton#q_22,QPushButton#q_3,QPushButton#q_33,QPushButton#q_4,QPushButton#q_44,QPushButton#q_5,QPushButton#q_6 { border-radius: 5px; }
            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}

        """ % btn_styles
        self.setStyleSheet(styles)

    def accept_clicked(self):
        csv_path = self.file_path_disp.text()
        assert(csv_path is not None and len(csv_path.strip()) > 0)
        self.status.setText("Importing ...")
        self.read_csv()
        self.accept()


    def pick_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Pick a Zotero export file', '',"CSV files (*.csv)")
        if fname is not None and len(fname[0].strip()) > 0:
            self.file_path_disp.setText(fname[0])
            self.scan_csv()
            self.accept_btn.setDisabled(False)
        else:
            if len(self.file_path_disp.text().strip()) == 0:
                self.accept_btn.setDisabled(True)

    def get_name(self):
        if self._chosen_name is None or len(self._chosen_name) == 0:
            name = utility.text.strip_url(self.chosen_url)
            name = utility.text.clean_file_name(name)
            return name
        name = utility.text.clean_file_name(self._chosen_name)
        return name

    def scan_csv(self):
        total_count = 0
        with open(self.file_path_disp.text(), newline='', encoding="utf-8") as zotero_csv:
            csvreader = csv.DictReader(zotero_csv, delimiter=',')

            for zot_entry in csvreader:
                attachment_string = zot_entry["File Attachments"]
                attachment_array = re.split(";", attachment_string)
                total_count += sum([1 for att in attachment_array if att.strip().endswith(".pdf")])
            if total_count > 0:
                self.status.setText(f"Found {total_count} PDF attachments in the CSV.")
                self.status.setStyleSheet('color: #2496dc')
            else:
                self.status.setText(f"Found no PDF attachments in the CSV.")
                self.status.setStyleSheet('color: red')


    def read_csv(self):

        def append_to_string(originalstring, appendstring, prefix, suffix):
            if appendstring:
                return f"{originalstring} {prefix} {appendstring} {suffix}"
            else:
                return originalstring

        tags = self.tags.text()
        prio = self.slider.value()
        schedule = ""
        if prio is not None and prio > 0:
            schedule = self.slider.schedule()
        add_oi_to_title = self.oi_cb.isChecked()
        with open(self.file_path_disp.text(), newline='', encoding="utf-8") as zotero_csv:
            # initialize the csv reader module
            csvreader = csv.DictReader(zotero_csv, delimiter=',')
            # loop through the entries of the exported list
            for zot_entry in csvreader:
                # get out attachments
                attachment_string   = zot_entry["File Attachments"]
                attachment_array    = re.split(";", attachment_string)

                # lets loop through our attachments, and if we got a PDF be happy :)
                for attachment in attachment_array:
                    #search for PDFs
                    if re.match(".*?.pdf", attachment):

                        id = get_pdf_id_for_source(attachment.strip())
                        if id >= 0:
                            if self.dup_radio_2.isChecked():
                                delete_note(id)
                            else:
                                continue

                         # now that we have a pdf, let's get all the info
                        entry_title            = zot_entry["Title"]
                        entry_publicationyear  = zot_entry["Publication Year"]
                        entry_authors          = zot_entry["Author"]
                        entry_publicationtitle = zot_entry["Publication Title"]
                        entry_isbn             = zot_entry["ISBN"]
                        entry_issn             = zot_entry["ISSN"]
                        entry_doi              = zot_entry["DOI"]
                        entry_url              = zot_entry["Url"]
                        entry_pages            = zot_entry["Pages"]
                        entry_issue            = zot_entry["Issue"]
                        entry_volume           = zot_entry["Volume"]
                        entry_edition          = zot_entry["Edition"]
                        entry_publisher        = zot_entry["Publisher"]
                        entry_mantags          = zot_entry["Manual Tags"]
                        entry_autotags         = zot_entry["Automatic Tags"]

                        # make strings ready for add-on
                        # start with the title of the note
                        note_title = entry_title

                        # add ISBN/ISSN/DOI to title if possible, but only if specified in settings
                        if add_oi_to_title:
                            note_title = append_to_string(note_title, entry_isbn, " - ", "")
                            note_title = append_to_string(note_title, entry_issn, " - ", "")
                            note_title = append_to_string(note_title, entry_doi, " - ", "")

                        # let's generate a note text with all that data we might or might not have
                        note_text = note_title + "<br>"

                        # lets add author and so on:
                        note_text = append_to_string(note_text, entry_authors, "<b>Authors:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_publicationyear, "<b>Year:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_publicationtitle, "<b>Journal:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_pages, "<b>Pages:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_issue, "<b>Issue:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_volume, "<b>Volume:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_edition, "<b>Edition:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_publisher, "<b>Publisher:</b>", "<br>")
                        note_text = append_to_string(note_text, entry_url, "<b>Url:</b>", "<br>")

                        # add tags as keywords
                        if (entry_mantags or entry_autotags): note_text = note_text + "<br><b>Keywords:</b><br>"
                        note_text = append_to_string(note_text, entry_mantags, "<b>Manual Tags:</b><br>", "<br><br>")
                        note_text = append_to_string(note_text, entry_autotags, "<b>Auto Tags:</b><br>", "<br><br>")

                        create_note(note_title, note_text, attachment, tags, None, schedule, prio, entry_authors, url = entry_url)
                        self.total_count += 1
