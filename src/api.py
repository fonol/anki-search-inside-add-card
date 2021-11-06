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

import traceback
from typing import Optional
import aqt
from aqt import mw
from anki.utils import isMac
from aqt.utils import tooltip

import state
from .notes import get_queue_count
from .state import get_index
from .web.reading_modal import Reader
from .dialogs.quick_open_pdf import QuickOpenNote
from .dialogs.queue_picker import QueuePicker
from .hooks import add_tmp_hook


def queue_has_items() -> bool:
    """ Check if the queue has at least one item in it. """
    return get_queue_count() > 0

def open_or_switch_to_editor(function):
    try:
        aqt.dialogs.open("AddCards", mw)
        win = mw.app.activeWindow()
        if isinstance(win, aqt.addcards.AddCards):
            if isMac:
                win.raise_()
            else:
                win.showMaximized()
        else:
            win = aqt.dialogs._dialogs["AddCards"]
            if win:
                if isMac:
                    win[1].raise_()
                else:
                    win[1].showMaximized()
        # mw.requireReset()
        # mw.CollectionOp()
        if state.get_bool(state.editor_is_ready, default=False):
            function()
        else:
            add_tmp_hook("editor-with-siac-initialised", lambda: function())
    except Exception as e:
        print(traceback.format_exc())
        print("Failed to open.")
        print(e)


    # mw.requireReset(reason=ResetReason.AddCardsAddNote)

def show_queue_picker():
    dialog = QueuePicker(mw.app.activeWindow())

    def _open_id():
        Reader.display(dialog.chosen_id())

    if dialog.exec_():
        if dialog.chosen_id() is not None and dialog.chosen_id() > 0:
            open_or_switch_to_editor(_open_id)
        else:
            if Reader is not None:
                Reader.reload_bottom_bar()


def show_quick_open_pdf():
    """ quick open pdf opened -> show small dialog to quickly open a PDF. """
    # dont trigger keypress if edit dialogs opened within the add dialog
    #if isinstance(win, EditDialog) or isinstance(win, Browser):
    #    return

    dialog = QuickOpenNote(mw.app.activeWindow())

    if dialog.exec_():
        if dialog.chosen_id is not None and dialog.chosen_id > 0:
            open_siac_with_id(dialog.chosen_id)

def open_siac_with_id(id, page=None):
    def _open_id():
        Reader.display(id, page=page)

    open_or_switch_to_editor(_open_id)


def try_open_first_in_queue(message: Optional[str] = None):
    global _timer
    """ Try to open/activate the Add Cards window, then open the first item in the queue. """
    if queue_has_items():
        def _open_newest_pdf():
            Reader.read_head_of_queue()
            if message and len(message) > 0:
                tooltip(message, period=5000)

        open_or_switch_to_editor(_open_newest_pdf)
