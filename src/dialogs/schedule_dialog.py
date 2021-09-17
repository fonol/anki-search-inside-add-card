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

from .components import QtScheduleComponent

from aqt.qt import *
import aqt.editor
import aqt
import utility.misc
import state

class ScheduleDialog(QDialog):
    """ Edit the schedule of a note. """

    def __init__(self, note, parent):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.mw     = aqt.mw
        self.parent = parent
        self.note   = note

        self.setup_ui()
        self.setWindowTitle("Edit Schedule")
    
    def setup_ui(self):
        self.scheduler = QtScheduleComponent(self.note.reminder)

        self.setLayout(QVBoxLayout())

        c_lbl = QLabel(self)
        c_icon   = "calendar_night.png" if state.is_nightmode() else "calendar.png"
        c_pixmap  = QPixmap(utility.misc.get_web_folder_path() + f"icons/{c_icon}").scaled(QSize(35, 35), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        c_lbl.setPixmap(c_pixmap)
        hbox    = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(c_lbl)
        hbox.addStretch()
        self.layout().addSpacing(10)
        self.layout().addLayout(hbox)
        self.layout().addSpacing(16)

        self.layout().addWidget(self.scheduler)
        accept = QPushButton("Save")
        accept.clicked.connect(self.accept)
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(accept)
        self.layout().addLayout(hbox)
        
    def should_remove_schedule(self):
        return self.scheduler._get_schedule() == ""

    def schedule(self):
        return self.scheduler._get_schedule()
