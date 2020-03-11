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
from ..config import get_config_value_or_default
import utility.text
import utility.misc

class UrlImporter(QDialog):
    """
        Used to generate a pdf file from an url.
    """
    def __init__(self, parent, show_schedule=True):
        self.chosen_url = None
        self._chosen_name = None
        self.show_schedule = show_schedule
        self.queue_schedule = QueueSchedule.NOT_ADD.value
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        self.setup_ui()
        self.setWindowTitle("URL to PDF")

    def setup_ui(self):

        self.vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Save Path:"))

        save_path = get_config_value_or_default("pdfUrlImportSavePath", "user_files (add-on folder)")
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
            self.queue_section = QGroupBox("Queue")
            ex_v = QVBoxLayout()
            queue_lbl = QLabel("Add to Queue?")

            queue_lbl.setAlignment(Qt.AlignCenter)
            ex_v.addWidget(queue_lbl, Qt.AlignCenter)
            ex_v.addSpacing(5)

            self.q_lbl_1 = QPushButton(" Don't Add ")
            self.q_lbl_1.setObjectName("q_1")
            self.q_lbl_1.setFlat(True)
            self.q_lbl_1.setStyleSheet(btn_style_active)
            self.q_lbl_1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_1.clicked.connect(lambda: self.queue_selected(0)) 

            self.dark_mode_used = utility.misc.dark_mode_is_used(mw.addonManager.getConfig(__name__))
            if self.dark_mode_used:
                btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
                btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: lightgrey; font-weight: bold; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
            else:
                btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: grey; }"
                btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: black; font-weight: bold;}"
        
            lbl = QLabel("Priority")
            lbl.setAlignment(Qt.AlignCenter)
            ex_v.addWidget(lbl)

            self.q_lbl_2 = QPushButton("5 - Very High")
            self.q_lbl_2.setObjectName("q_2")
            self.q_lbl_2.setMinimumWidth(220)
            self.q_lbl_2.setFlat(True)
            self.q_lbl_2.setStyleSheet(btn_style)
            self.q_lbl_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_2.clicked.connect(lambda: self.queue_selected(5))
            ex_v.addWidget(self.q_lbl_2)
            ex_v.setAlignment(self.q_lbl_2, Qt.AlignCenter)


            self.q_lbl_3 = QPushButton("4 - High")
            self.q_lbl_3.setObjectName("q_3")
            self.q_lbl_3.setMinimumWidth(185)
            self.q_lbl_3.setFlat(True)
            self.q_lbl_3.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_3.setStyleSheet(btn_style)
            self.q_lbl_3.clicked.connect(lambda: self.queue_selected(4))
            ex_v.addWidget(self.q_lbl_3)
            ex_v.setAlignment(self.q_lbl_3, Qt.AlignCenter)


            self.q_lbl_4 = QPushButton("3 - Medium")
            self.q_lbl_4.setMinimumWidth(150)
            self.q_lbl_4.setObjectName("q_4")
            self.q_lbl_4.setFlat(True)
            self.q_lbl_4.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_4.setStyleSheet(btn_style)
            self.q_lbl_4.clicked.connect(lambda: self.queue_selected(3))
            ex_v.addWidget(self.q_lbl_4)
            ex_v.setAlignment(self.q_lbl_4, Qt.AlignCenter)


            self.q_lbl_5 = QPushButton("2 - Low")
            self.q_lbl_5.setMinimumWidth(115)
            self.q_lbl_5.setObjectName("q_5")
            self.q_lbl_5.setFlat(True)
            self.q_lbl_5.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_5.setStyleSheet(btn_style)
            self.q_lbl_5.clicked.connect(lambda: self.queue_selected(2))
            ex_v.addWidget(self.q_lbl_5)
            ex_v.setAlignment(self.q_lbl_5, Qt.AlignCenter)


            self.q_lbl_6 = QPushButton("1 - Very Low")
            self.q_lbl_6.setMinimumWidth(80)
            self.q_lbl_6.setObjectName("q_6")
            self.q_lbl_6.setFlat(True)
            self.q_lbl_6.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.q_lbl_6.setStyleSheet(btn_style)
            self.q_lbl_6.clicked.connect(lambda: self.queue_selected(1))
            ex_v.addWidget(self.q_lbl_6)
            ex_v.setAlignment(self.q_lbl_6, Qt.AlignCenter)

            self.queue_section.setLayout(ex_v)
            self.vbox.addWidget(self.queue_section)

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
            self.resize(350, 450)
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


























