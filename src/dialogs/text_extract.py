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

import aqt
import functools
from aqt.qt import *
from typing import List
from .components import ClickableQLabel

import state

from ..output import UI


class TextExtractDialog(QDialog):
    """Dialog to pick a field to send the selected text to."""

    # currently selected highlight
    highlight_ix : int = 0

    def __init__(self, parent, field_names: List[str], selection: str):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.mw                 = aqt.mw
        self.parent             = parent
        self.field_names        = field_names
        self.selection          = selection
        self.chosen_field       = None
        self.chosen_field_ix    = None


        self.setup_ui()
        self.setup_shortcuts()
        self.setMinimumWidth(300)
        self.setWindowTitle("Send selection to field")

    def setup_ui(self):

        vbox = QVBoxLayout()

        self.sel_area = QTextEdit()
        self.sel_area.setText(self.selection)
        self.sel_area.setMaximumHeight(100)
        self.sel_area.textChanged.connect(self.selection_changed)
        vbox.addWidget(self.sel_area)
        vbox.addSpacing(20)

        gb_colors = QGroupBox("Highlight")
        gb_colors.setLayout(QHBoxLayout())
        gb_colors.layout().addStretch()
        self.color_lbls = []

        for ix, c in enumerate(["transparent", "#e65100", "#558b2f", "#2196f3", "#ffee58", "#ab47bc"]):
            lbl     = ClickableQLabel("")
            pixmap  = QPixmap(32, 32)
            qcolour = QColor(c)

            self.color_lbls.append(lbl)
            lbl.clicked.connect(functools.partial(self.highlight_clicked, ix))

            pixmap.fill(qcolour)
            lbl.setPixmap(pixmap)
            gb_colors.layout().addWidget(lbl)

        self.set_highlights()
        
        gb_colors.layout().addStretch()
        vbox.addWidget(gb_colors)


        gb_fields   = QGroupBox("Fields - Press <Number> to pick")
        gb_vbox     = QVBoxLayout()
        for ix, f in enumerate(self.field_names):
            if ix < 9:
                lbl = ClickableQLabel(f"{ix+1}. {f}")
            else:
                lbl = ClickableQLabel(f)
            lbl.clicked.connect(functools.partial(self.field_clicked, f))
            lbl.setStyleSheet("""
                ClickableQLabel {
                    padding: 2px 3px;
                }
                ClickableQLabel:hover {
                    background: #2e6286;
                    color: white;
                }
            """)
            lbl.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
            gb_vbox.addWidget(lbl)
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        container.setLayout(gb_vbox)
        sa = QScrollArea()
        sa.setWidget(container)
        sa.setMaximumHeight(250)
        gb_fields.setLayout(QVBoxLayout())
        gb_fields.layout().addWidget(sa)

        vbox.addWidget(gb_fields)

        hbox_bot = QHBoxLayout()
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        hbox_bot.addStretch(1)
        hbox_bot.addWidget(self.reject_btn)
        vbox.addLayout(hbox_bot)
        self.setLayout(vbox)

        self.reject_btn.setFocus()

    def set_highlights(self):
        for ix, lbl in enumerate(self.color_lbls):
            if ix == 0 and ix != TextExtractDialog.highlight_ix:
                if state.is_nightmode():
                    lbl.setStyleSheet(""" border: 2px solid grey; """)
                else:
                    lbl.setStyleSheet(""" border: 2px solid grey; """)

            elif ix == TextExtractDialog.highlight_ix:
                if state.is_nightmode():
                    lbl.setStyleSheet(""" border: 2px solid white; """)
                else:
                    lbl.setStyleSheet(""" border: 2px solid #0096dc; """)
            else:
                lbl.setStyleSheet(""" border: 2px solid transparent; """)


    def highlight_clicked(self, ix: int):
        TextExtractDialog.highlight_ix = ix
        self.set_highlights()

    def setup_shortcuts(self):
        for i in range(min(9,len(self.field_names))):
            QShortcut(QKeySequence(f"{i+1}"), self, activated=functools.partial(self.pick_field_and_close, i))

    def field_clicked(self, field_name: str):
        self.chosen_field_ix    = self.field_names.index(field_name)
        self.chosen_field       = field_name
        self.accept()

    def pick_field_and_close(self, ix: int):
        self.chosen_field_ix    = ix
        self.chosen_field       = self.field_names[ix]
        self.accept()

    def selection_changed(self):
        self.selection          = self.sel_area.toPlainText()


