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

import time
import typing
from typing import Optional
import aqt
from aqt import mw
from anki.utils import isMac
from aqt.utils import tooltip, showInfo

from .notes import get_queue_count
from .state import get_index

_timer = None

def queue_has_items() -> bool:
    """ Check if the queue has at least one item in it. """
    return get_queue_count() > 0

def try_open_first_in_queue(message: Optional[str] = None):
    global _timer
    """ Try to open/activate the Add Cards window, then open the first item in the queue. """
    if queue_has_items():
        aqt.dialogs.open("AddCards", mw)
        try:
            win = mw.app.activeWindow()
            if isinstance(win, aqt.addcards.AddCards):
                if not isMac:
                    win.showMaximized()
                if isMac:
                    win.raise_()
            else:
                win = aqt.dialogs._dialogs["AddCards"]
                if win:
                    if not isMac:
                        win.showMaximized()
                    if isMac:
                        win.raise_()
        except:
            pass

        def _open():
            get_index().ui.reading_modal.read_head_of_queue()
            if message and len(message) > 0:
                tooltip(message, period=5000)

        _timer = aqt.qt.QTimer()
        _timer.setSingleShot(True)
        _timer.timeout.connect(_open)
        _timer.start(1500)
