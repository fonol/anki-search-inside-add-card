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


# set after create_db_file_if_not_exists has been called
db_file_existed = None



search_index = None
contextEvt = None
corpus = None
deck_map = None
edit = None

old_on_bridge = None

def check_index():
    return search_index is not None and search_index.ui is not None and search_index.ui._editor is not None and search_index.ui._editor.web is not None

def set_index(index):
    global search_index
    search_index = index

def get_index():
    return search_index

def corpus_is_loaded():
    return corpus is not None

def set_corpus(c):
    global corpus
    corpus = c

def get_corpus():
    return corpus

def set_edit(e):
    global edit
    edit = e

def get_edit():
    return edit

def set_deck_map(dm):
    global deck_map
    deck_map = dm
