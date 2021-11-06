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
import os

from ..api import *
from ..notes import get_read_today_count
import state
import utility.misc

class ReviewReadInterruptDialog(QDialog):
    """ Dialog that asks if the user wants to switch from review to reading. """

    def __init__(self, parent):

        QDialog.__init__(self, parent)

        self.mw             = aqt.mw
        self.parent         = parent
        self.setup_ui()
        self.setWindowTitle("Review / Read")
        
       
    def setup_ui(self):

        self.vbox = QVBoxLayout()
        self.vbox.addSpacing(15)
        icon = utility.misc.qlabel_image("graduation_cap_night.png" if state.is_nightmode() else "graduation_cap.png", 50, 50)
        hb_icon = QHBoxLayout()
        hb_icon.addStretch()
        hb_icon.addWidget(icon)
        hb_icon.addStretch()
        self.vbox.addLayout(hb_icon)
        self.vbox.addSpacing(15)
        lbl = QLabel("Open first item in the queue?")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 20px;")
        lbl.setMargin(15)

        cnt = get_read_today_count()
        s   = "s" if cnt != 1 else ""
        sub = QLabel(f"Read today: <b>{cnt}</b> page{s}")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size: 15px; color: grey;")

        at  = utility.misc.count_cards_added_today()
        s   = "s" if at != 1 else ""
        sub_1 = QLabel(f"Added today: <b>{at}</b> card{s}")
        sub_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_1.setStyleSheet("font-size: 15px; color: grey;")

        self.vbox.addWidget(lbl)
        self.vbox.addWidget(sub)
        self.vbox.addWidget(sub_1)
        self.vbox.addSpacing(30)
        self.vbox.addStretch()

        bhb = QHBoxLayout()
        bhb.addStretch(1)
        
        self.read_btn = QPushButton("Yes")
        self.read_btn.clicked.connect(self.read_clicked)
        bhb.addWidget(self.read_btn)

        self.later_btn = QPushButton("Later")
        self.later_btn.clicked.connect(self.later_clicked)
        bhb.addWidget(self.later_btn)

        self.stop_btn = QPushButton("Enough for today!")
        self.stop_btn.clicked.connect(self.stop_clicked)
        bhb.addWidget(self.stop_btn)

        self.vbox.addLayout(bhb)

        self.setLayout(self.vbox)
        self.show()
    
    def read_clicked(self):
        self.accept()

    def stop_clicked(self):
        state.rr_mix_disabled = True
        self.reject()
    
    def later_clicked(self):
        self.reject()



