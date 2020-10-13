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
from ..config import get_config_value_or_default

import utility.misc
import state

class PostponeDialog(QDialog):
    """ Values can be 0 (later today), or 1+ (in x days) """

    def __init__(self, parent, note_id):
        QDialog.__init__(self, parent)
        self.note_id    = note_id
        self.value      = 0    
        self.setup_ui()
        # self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

    def setup_ui(self):

        shortcut = get_config_value_or_default("pdf.shortcuts.later", "CTRL+Shift+Y")
        self.setWindowTitle(f"Postpone ({shortcut})")
        self.layout = QVBoxLayout()

        self.later_rb       = QRadioButton("Later Today")
        self.tomorrow_rb    = QRadioButton("Tomorrow")
        self.days_rb        = QRadioButton("In ")
        self.group          = QButtonGroup()
        for ix, b in enumerate([self.later_rb, self.tomorrow_rb, self.days_rb]):
            self.group.addButton(b, ix)

        c_lbl = QLabel(self)
        a_lbl = QLabel(self)
        c_icon   = "clock_night.png" if state.night_mode else "clock.png"
        a_icon   = "rarrow_night.png" if state.night_mode else "rarrow.png"
        c_pixmap  = QPixmap(utility.misc.get_web_folder_path() + f"icons/{c_icon}")
        c_lbl.setPixmap(c_pixmap)
        a_pixmap  = QPixmap(utility.misc.get_web_folder_path() + f"icons/{a_icon}")
        a_lbl.setPixmap(a_pixmap)
        hbox    = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(c_lbl)
        hbox.addWidget(a_lbl)
        hbox.addStretch()
        self.layout.addSpacing(10)
        self.layout.addLayout(hbox)
        self.layout.addSpacing(20)

        self.layout.addWidget(self.later_rb)
        self.layout.addWidget(self.tomorrow_rb)
        self.days_container = QHBoxLayout()
        self.days_inp = QDoubleSpinBox()
        self.days_inp.setSingleStep(1)
        self.days_inp.setValue(3)
        self.days_inp.setMinimum(1)
        self.days_inp.setMaximum(10000)
        self.days_inp.setDecimals(0)
        self.days_inp.setSuffix(" day(s)")
        self.days_container.addWidget(self.days_rb)
        self.days_container.addWidget(self.days_inp)
        self.days_container.addStretch()
        self.layout.addLayout(self.days_container)

        self.later_rb.setChecked(True)

        self.accept_btn = QPushButton("Postpone")
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)
        self.hbox.addWidget(self.reject_btn)

        self.layout.addSpacing(20)
        self.layout.addLayout(self.hbox)
        self.layout.setAlignment(Qt.AlignHCenter)
        self.setLayout(self.layout)
        self.setMinimumWidth(300)
            
    def on_accept(self):
        if self.later_rb.isChecked():
            self.value = 0
        elif self.tomorrow_rb.isChecked():
            self.value = 1
        elif self.days_rb.isChecked():
            self.value = self.days_inp.value()

        self.accept()
