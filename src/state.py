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
import typing
from typing import List, Tuple, Any, Optional, Dict
from aqt.editor import Editor

# set after create_db_file_if_not_exists has been called
db_file_existed: Optional[bool] = None

#
# Globals
#
search_index        : "FTSIndex"                        = None
note_editor_shown   : bool                              = False
contextEvt          : Any                               = None
corpus              : Optional[List[Tuple[Any, ...]]]   = None
deck_map            : Optional[Dict[str, int]]          = None
edit                : Optional[Editor]                  = None

def check_index() -> bool:
    """ Returns True if index and ui are ready to use. """
    return (search_index is not None 
            and search_index.ui is not None 
            and search_index.ui._editor is not None 
            and search_index.ui._editor.web is not None)

def set_index(index: "FTSIndex"):
    global search_index
    search_index = index

def get_index() -> "FTSIndex":
    return search_index

def corpus_is_loaded() -> bool:
    return corpus is not None

def set_corpus(c: List[Tuple[Any, ...]]):
    global corpus
    corpus = c

def get_corpus() -> Optional[List[Tuple[Any, ...]]]:
    return corpus

def set_edit(e: Editor):
    global edit
    edit = e

def get_edit() -> Editor:
    return edit

def set_deck_map(dm: Dict[str, int]):
    global deck_map
    deck_map = dm
