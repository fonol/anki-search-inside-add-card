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
import os
from ..config import get_config_value_or_default
from .components import ClickableQLabel

import utility.misc
import state

class PostponeDialog(QDialog):
    """ Values can be 0 (later today), or 1+ (in x days) """

    def __init__(self, parent, note_id):
        QDialog.__init__(self, parent, Qt.FramelessWindowHint)
        self.note_id    = note_id
        self.value      = 0    
        self.setup_ui()

    def setup_ui(self):

        shortcut = get_config_value_or_default("pdf.shortcuts.later", "CTRL+Shift+Y")
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30,20,30,10)

        header      = QLabel(f"Postpone ({shortcut})")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.layout.addSpacing(5)
        self.layout.addWidget(header)
        self.layout.addSpacing(10)


        self.later_rb       = QRadioButton("Later Today")
        self.tomorrow_rb    = QRadioButton("")
        self.days_rb        = QRadioButton("")
        self.group          = QButtonGroup()
        for ix, b in enumerate([self.later_rb, self.tomorrow_rb, self.days_rb]):
            self.group.addButton(b, ix)

        c_lbl = QLabel(self)
        a_lbl = QLabel(self)
        c_icon   = "clock_night.png" if state.is_nightmode() else "clock.png"
        a_icon   = "rarrow_night.png" if state.is_nightmode() else "rarrow.png"
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

        icon = "calendar_night" if state.is_nightmode() else "calendar"
        pmap = QPixmap(utility.misc.get_web_folder_path() + f"icons/{icon}").scaled(QSize(13, 13), Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Tomorrow radio button + label
        t_hb = QHBoxLayout()
        t_hb.addWidget(self.tomorrow_rb)
        t_icn = ClickableQLabel()
        t_icn.setPixmap(pmap)
        t_icn.clicked.connect(self.toggle_tomorrow_rb)
        t_hb.addWidget(t_icn)
        t_lbl = ClickableQLabel("Tomorrow")
        t_lbl.clicked.connect(self.toggle_tomorrow_rb)
        t_hb.addWidget(t_lbl)
        t_hb.addStretch()
        self.layout.addLayout(t_hb)


        # In ... days radio button + label
        d_hb = QHBoxLayout()
        d_lbl = ClickableQLabel("In ")
        d_lbl.clicked.connect(self.toggle_days_rb)
        d_hb.addWidget(self.days_rb)
        d_icn = ClickableQLabel()
        d_icn.setPixmap(pmap)
        d_icn.clicked.connect(self.toggle_days_rb)
        d_hb.addWidget(d_icn)
        d_hb.addWidget(d_lbl)
        self.days_inp = QDoubleSpinBox()
        self.days_inp.setSingleStep(1)
        self.days_inp.setValue(3)
        self.days_inp.setMinimum(1)
        self.days_inp.setMaximum(10000)
        self.days_inp.setDecimals(0)
        self.days_inp.setSuffix(" day(s)")
        d_hb.addWidget(self.days_inp)
        d_hb.addStretch()
        self.layout.addLayout(d_hb)

        self.later_rb.setChecked(True)

        self.accept_btn = QPushButton("Postpone")
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)    
        self.hbox.addWidget(self.reject_btn)
        self.hbox.addStretch()

        self.layout.addSpacing(30)
        self.layout.addLayout(self.hbox)
        self.layout.addSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(self.layout)
        self.setMinimumWidth(300)

        self.setObjectName("postpone")
        self.setStyleSheet("""
            #postpone {
                border: 3px outset #2496dc; 
                border-radius: 5px;
            } 
        """)
            
    def toggle_tomorrow_rb(self):
        self.tomorrow_rb.setChecked(not self.tomorrow_rb.isChecked())

    def toggle_days_rb(self):
        self.days_rb.setChecked(not self.days_rb.isChecked())
        
    def on_accept(self):
        if self.later_rb.isChecked():
            self.value = 0
        elif self.tomorrow_rb.isChecked():
            self.value = 1
        elif self.days_rb.isChecked():
            self.value = int(self.days_inp.value())

        self.accept()
