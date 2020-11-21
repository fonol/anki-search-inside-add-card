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
import utility.misc
import state
import functools

from ..notes import get_read_today_count

class TimerElapsedDialog(QDialog):
    """ Dialog that is shown after the tomato timer finished. """

    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.FramelessWindowHint)

        self.setModal(True)
        self.mw     = aqt.mw
        self.parent = parent

        self.setup_ui()
        self.restart = None
        self.setWindowTitle("Time is up!")
    
    def setup_ui(self):
        self.setLayout(QVBoxLayout())

        c_lbl = QLabel(self)
        c_icon   = "hourglass_night.png" if state.night_mode else "hourglass.png"
        c_pixmap  = QPixmap(utility.misc.get_web_folder_path() + f"icons/{c_icon}").scaled(QSize(35, 35), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        c_lbl.setPixmap(c_pixmap)
        hbox    = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(c_lbl)
        hbox.addStretch()
        self.layout().addSpacing(15)
        self.layout().addLayout(hbox)
        self.layout().addSpacing(16)

        header = QLabel("Time is up!")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.layout().addWidget(header, Qt.AlignCenter)
        self.layout().addSpacing(10)

        read_today_count    = get_read_today_count()
        pages               = "pages" if read_today_count != 1 else "page"
        added_today_count   = utility.misc.count_cards_added_today()
        cards               = "cards" if added_today_count != 1 else "card"

        read_lbl  = QLabel(f"Read <b>{read_today_count}</b> {pages} today")
        read_lbl.setAlignment(Qt.AlignCenter)
        added_lbl = QLabel(f"Added <b>{added_today_count}</b> {cards} today")
        added_lbl.setAlignment(Qt.AlignCenter)

        self.layout().addWidget(read_lbl)
        self.layout().addWidget(added_lbl)


        gbox            = QGroupBox("Start a new timer")
        hbox_restart    = QHBoxLayout()
        for m in [5, 10, 15, 25, 30]:
            
            btn = QToolButton()
            btn.setText(str(m))
            btn.clicked.connect(functools.partial(self.set_restart, m))
            hbox_restart.addWidget(btn)

        gbox.setLayout(hbox_restart)
        self.layout().addSpacing(20)
        self.layout().addWidget(gbox)

        accept = QPushButton("Ok")
        accept.clicked.connect(self.accept)
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(accept)
        hbox.addStretch()
        self.layout().addSpacing(25)
        self.layout().addLayout(hbox)
        self.layout().addSpacing(5)
        self.layout().setContentsMargins(50,10,50, 10)

        self.setObjectName("elapsed")
        self.setStyleSheet("""
            #elapsed {
                border: 3px outset #2496dc; 
                border-radius: 5px;
            } 
        """)
        
    def set_restart(self, mins: int):
        self.restart = mins
        self.accept()

