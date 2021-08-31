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

from aqt import mw
import aqt
import typing

from enum import Enum, unique
from typing import List, Tuple, Any, Optional, Dict
from aqt.editor import Editor
from aqt.editcurrent import EditCurrent

import utility.misc

@unique
class WindowMode(Enum):
    Both        = 1,
    Fields      = 2,
    Addon       = 3,
    Autohide    = 4

# set after create_db_file_if_not_exists has been called
db_file_existed     : Optional[bool]                    = None

#
# Globals
#
search_index        : "FTSIndex"                        = None
note_editor_shown   : bool                              = False
contextEvt          : Any                               = None
corpus              : Optional[List[Tuple[Any, ...]]]   = None
deck_map            : Optional[Dict[str, int]]          = None
edit                : Optional[Editor]                  = None
night_mode          : Optional[bool]                    = None
editor_is_ready     : bool                              = False
interrupted_review  : bool                              = False

# Determines whether the both, the fields and the add-on pane, or only one of them are visible
window_mode         : WindowMode                        = WindowMode.Both

# Indicates whether the Rust lib has been successfully loaded or not
rust_lib            : Optional[bool]                    = None

# for developing, if True, HTML templates won't be cached
dev_mode            : bool                              = False

# if mix_reviews_and_reading is set to true in config, this counts the done reviews
review_counter      : int                               = 0
rr_mix_disabled     : bool                              = False

# last cmd send from the web view, see command_parsing.py
last_cmd            : Optional[str]                     = None

# last cmd send from the web view that triggers any kind of search
last_search_cmd     : Optional[str]                     = None

# last page cmd from the web view that triggers a page load
last_page_requested : Optional[int]                     = None

shortcuts_failed    : List[str]                         = []


def check_index() -> bool:
    """ Returns True if index and ui are ready to use. """
    return search_index is not None

def set_index(index: "FTSIndex"):
    global search_index
    search_index = index

def get_index() -> "FTSIndex":
    return search_index

def set_edit(e: Editor):
    global edit
    edit = e

def get_edit() -> Editor:
    return edit

def set_deck_map(dm: Dict[str, int]):
    global deck_map
    deck_map = dm

def set_window_mode(mode: str, editor):
    """ Set the window mode and update the UI. """
    global window_mode
    window_mode = WindowMode[mode]

    mod                     = utility.misc.get_addon_id()
    config                  = mw.addonManager.getConfig(mod)
    config["window_mode"]   = mode

    mw.addonManager.writeConfig(mod, config)
    editor.web.eval(f"setWindowMode('{mode}')")

    if hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, aqt.addcards.AddCards):
        win = aqt.dialogs._dialogs["AddCards"][1]
    elif hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, EditCurrent):
        if not config["useInEdit"]:
            return
        win = aqt.dialogs._dialogs["EditCurrent"][1]
    else:
        win = aqt.dialogs._dialogs["AddCards"][1]

    if win is None:
        return
    box                     = win.form.buttonBox
    box.switch_btn.setText(mode)

def switch_window_mode(direction: str, editor):

    global window_mode

    mod                     = utility.misc.get_addon_id()
    config                  = mw.addonManager.getConfig(mod)
    switched                = config["switchLeftRight"]

    if direction in ["left", "right"]:
        if window_mode == WindowMode.Both:
            if direction == "left" and switched:
                window_mode = WindowMode.Fields
            elif direction == "left":
                window_mode = WindowMode.Addon
            elif switched:
                window_mode = WindowMode.Addon
            else:
                window_mode = WindowMode.Fields
        elif window_mode == WindowMode.Fields:
            window_mode = WindowMode.Addon
        elif window_mode == WindowMode.Addon:
            window_mode = WindowMode.Fields

    else:
        if window_mode == WindowMode.Both:
            return
        window_mode = WindowMode.Both

    config["window_mode"]   = window_mode.name
    mw.addonManager.writeConfig(mod, config)
    editor.web.eval(f"setWindowMode('{window_mode.name}')")

    if hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, aqt.addcards.AddCards):
        win = aqt.dialogs._dialogs["AddCards"][1]
    elif hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, EditCurrent):
        if not config["useInEdit"]:
            return
        win = aqt.dialogs._dialogs["EditCurrent"][1]
    else:
        win = aqt.dialogs._dialogs["AddCards"][1]

    if win is None:
        return
    box                     = win.form.buttonBox
    box.switch_btn.setText(window_mode.name)
