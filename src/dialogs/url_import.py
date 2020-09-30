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


from ..notes import *
from ..config import get_config_value, update_config
from .components import QtPrioritySlider
import utility.text
import utility.misc

class UrlImporter(QDialog):
    """
        Used to generate a pdf file from an url.
    """
    def __init__(self, parent, show_schedule=True):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.chosen_url     = None
        self._chosen_name   = None
        self.show_schedule  = show_schedule
        self.queue_schedule = 0
        self.mw             = aqt.mw
        self.parent         = parent

        self.setup_ui()
        self.setWindowTitle("URL to PDF")

    def setup_ui(self):

        self.vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Save Path:"))

        save_path = get_config_value("pdfUrlImportSavePath")
        if save_path is None or len(save_path.strip()) == 0:
            save_path = utility.misc.get_application_data_path() + "pdf_imports/"
            utility.misc.create_folder_if_not_exists(save_path)
            update_config("pdfUrlImportSavePath", save_path)
        save_path_disp = QLineEdit()
        save_path_disp.setText(save_path)
        save_path_disp.setDisabled(True)

        hbox.addWidget(save_path_disp)

        self.vbox.addLayout(hbox)

        url_label = QLabel("Url")
        self.url = QLineEdit()
        self.vbox.addWidget(url_label)
        self.vbox.addWidget(self.url)

        name_label = QLabel("PDF Name (Optional)")
        self.name = QLineEdit()
        self.vbox.addWidget(name_label)
        self.vbox.addWidget(self.name)
       
        if self.show_schedule:
            
            self.slider = QtPrioritySlider(0)
            self.vbox.addWidget(self.slider)

        self.vbox.addSpacing(15)

        hbox_bot = QHBoxLayout()
        self.accept_btn = QPushButton("Import")
        self.accept_btn.setShortcut("Ctrl+Return")
        self.accept_btn.clicked.connect(self.accept_clicked)

        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addWidget(self.accept_btn)
        hbox_bot.addWidget(self.reject_btn)
        self.vbox.addLayout(hbox_bot)

        # only resize if queue is shown
        if self.show_schedule:
            self.resize(350, 350)
        self.setLayout(self.vbox)
        styles = """
            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}
        """
        self.setStyleSheet(styles)
        

    def queue_selected(self, queue_schedule):
        lbls = [self.q_lbl_1, self.q_lbl_6, self.q_lbl_5, self.q_lbl_4, self.q_lbl_3, self.q_lbl_2]
        self.queue_schedule = queue_schedule
        for lbl in lbls:
            if self.dark_mode_used:
                lbl.setStyleSheet("QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }")
            else:
                lbl.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey; font-weight: normal;")
        lbls[queue_schedule].setStyleSheet("border: 2px solid #2496dc; padding: 3px; font-weight: bold;")

    def accept_clicked(self):
        self.chosen_url = self.url.text()
        self._chosen_name = self.name.text()
        self.accept()

    def get_name(self):
        if self._chosen_name is None or len(self._chosen_name) == 0:
            name = utility.text.strip_url(self.chosen_url)
            name = utility.text.clean_file_name(name) 
            return name
        name = utility.text.clean_file_name(self._chosen_name)
        return name


























