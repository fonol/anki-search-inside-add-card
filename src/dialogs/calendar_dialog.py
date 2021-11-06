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
import typing
import os


class CalendarDialog(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.date = None
        self.setup_ui()

    def setup_ui(self):

        self.setWindowTitle("Pick a date")
        self.layout = QVBoxLayout()

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumDate(QDate.currentDate().addDays(1))
        self.calendar.setMaximumDate(QDate.currentDate().addYears(10))
        self.layout.addWidget(self.calendar)

        self.accept_btn = QPushButton("Ok")
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)

        self.hbox = QHBoxLayout()
        self.hbox.addStretch()
        self.hbox.addWidget(self.accept_btn)
        self.hbox.addWidget(self.reject_btn)

        self.layout.addLayout(self.hbox)

        self.setLayout(self.layout)
        self.setMinimumWidth(300)
            
    def on_accept(self):
        self.date = self.calendar.selectedDate().toPyDate()
        self.accept()
