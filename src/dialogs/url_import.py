from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
import functools
import re
import random
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from aqt.utils import showInfo
from anki.utils import isMac
from anki.lang import _


from ..notes import *
from ..config import get_config_value_or_default
import utility.text
import utility.misc

class UrlImporter(QDialog):
    """
        Used to generate a pdf file from an url.
    """
    def __init__(self, parent):
        self.chosen_url = None
        self._chosen_name = None
        self.queue_schedule = QueueSchedule.NOT_ADD
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

        self.queue_section = QGroupBox("Queue")
        ex_v = QVBoxLayout()
        queue_lbl = QLabel("Add to Queue?")

        queue_lbl.setAlignment(Qt.AlignCenter)
        ex_v.addWidget(queue_lbl, Qt.AlignCenter)
        ex_v.addSpacing(5)

        self.q_lbl_1 = QPushButton("Don't Add to Queue")

        self.dark_mode_used = utility.misc.dark_mode_is_used(mw.addonManager.getConfig(__name__))
        if self.dark_mode_used:
            btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
            btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: lightgrey; font-weight: bold; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
        else:
            btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: grey; }"
            btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: black; font-weight: bold;}"


        self.q_lbl_1.setObjectName("q_1")
        self.q_lbl_1.setFlat(True)
        self.q_lbl_1.setStyleSheet(btn_style_active)
        self.q_lbl_1.clicked.connect(lambda: self.queue_selected(1))
        ex_v.addWidget(self.q_lbl_1)

        ex_v.addSpacing(5)
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.HLine)
        line_sep.setFrameShadow(QFrame.Sunken)
        ex_v.addWidget(line_sep)
        ex_v.addSpacing(5)

        self.q_lbl_2 = QPushButton("Head")
        self.q_lbl_2.setObjectName("q_2")
        self.q_lbl_2.setFlat(True)
        self.q_lbl_2.setStyleSheet(btn_style)
        self.q_lbl_2.clicked.connect(lambda: self.queue_selected(2))
        ex_v.addWidget(self.q_lbl_2)

        self.q_lbl_22 = QPushButton("[Rnd]")
        self.q_lbl_22.setObjectName("q_22")
        self.q_lbl_22.setFlat(True)
        self.q_lbl_22.setStyleSheet(btn_style)
        self.q_lbl_22.clicked.connect(lambda: self.queue_selected(7))
        ex_v.addWidget(self.q_lbl_22)


        self.q_lbl_3 = QPushButton("End of first 3rd")
        self.q_lbl_3.setObjectName("q_3")
        self.q_lbl_3.setFlat(True)
        self.q_lbl_3.setStyleSheet(btn_style)
        self.q_lbl_3.clicked.connect(lambda: self.queue_selected(3))
        ex_v.addWidget(self.q_lbl_3)

        self.q_lbl_33 = QPushButton("[Rnd]")
        self.q_lbl_33.setObjectName("q_33")
        self.q_lbl_33.setFlat(True)
        self.q_lbl_33.setStyleSheet(btn_style)
        self.q_lbl_33.clicked.connect(lambda: self.queue_selected(8))
        ex_v.addWidget(self.q_lbl_33)



        self.q_lbl_4 = QPushButton("End of second 3rd")
        self.q_lbl_4.setObjectName("q_4")
        self.q_lbl_4.setFlat(True)
        self.q_lbl_4.setStyleSheet(btn_style)
        self.q_lbl_4.clicked.connect(lambda: self.queue_selected(4))
        ex_v.addWidget(self.q_lbl_4)

        self.q_lbl_44 = QPushButton("[Rnd]")
        self.q_lbl_44.setObjectName("q_44")
        self.q_lbl_44.setFlat(True)
        self.q_lbl_44.setStyleSheet(btn_style)
        self.q_lbl_44.clicked.connect(lambda: self.queue_selected(9))
        ex_v.addWidget(self.q_lbl_44)

        self.q_lbl_5 = QPushButton("End")
        self.q_lbl_5.setObjectName("q_5")
        self.q_lbl_5.setFlat(True)
        self.q_lbl_5.setStyleSheet(btn_style)
        self.q_lbl_5.clicked.connect(lambda: self.queue_selected(5))
        ex_v.addWidget(self.q_lbl_5)

        self.q_lbl_6 = QPushButton("\u2685 Random")
        self.q_lbl_6.setObjectName("q_6")
        self.q_lbl_6.setFlat(True)
        self.q_lbl_6.setStyleSheet(btn_style)
        self.q_lbl_6.clicked.connect(lambda: self.queue_selected(6))
        ex_v.addWidget(self.q_lbl_6)

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

        self.resize(350, 450)
        self.setLayout(self.vbox)
        styles = """
            QPushButton#q_1,QPushButton#q_2,QPushButton#q_22,QPushButton#q_3,QPushButton#q_33,QPushButton#q_4,QPushButton#q_44,QPushButton#q_5,QPushButton#q_6 { border-radius: 5px; }
            QPushButton#q_1 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_2 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_22 { margin-left: 80px; margin-right: 80px; }
            QPushButton#q_3 { margin-left: 30px; margin-right: 30px; }
            QPushButton#q_33 { margin-left: 80px; margin-right: 80px; }
            QPushButton#q_4 { margin-left: 30px; margin-right: 30px; }
            QPushButton#q_44 { margin-left: 80px; margin-right: 80px; }
            QPushButton#q_5 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_6 { margin-left: 10px; margin-right: 10px; }


            QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: lightblue; margin-left: 7px; margin-right: 7px; }
            QPushButton:hover#q_22,QPushButton:hover#q_33,QPushButton:hover#q_44 { background-color: lightblue; margin-left: 77px; margin-right: 77px; }
            QPushButton:hover#q_3,QPushButton:hover#q_4 { background-color: lightblue; margin-left: 27px; margin-right: 27px; }

            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}

        """
        self.setStyleSheet(styles)
        

    def queue_selected(self, queue_schedule):
        for lbl in [self.q_lbl_1, self.q_lbl_2,  self.q_lbl_22,  self.q_lbl_3,  self.q_lbl_33,  self.q_lbl_4, self.q_lbl_44, self.q_lbl_5, self.q_lbl_6]:
            if self.dark_mode_used:
                lbl.setStyleSheet("QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }")
            else:
                lbl.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey; font-weight: normal;")
        [self.q_lbl_1, self.q_lbl_2,  self.q_lbl_3, self.q_lbl_4, self.q_lbl_5, self.q_lbl_6, self.q_lbl_22, self.q_lbl_33, self.q_lbl_44][queue_schedule-1].setStyleSheet("border: 2px solid #2496dc; padding: 3px; font-weight: bold;")
        self.queue_schedule = queue_schedule

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


























