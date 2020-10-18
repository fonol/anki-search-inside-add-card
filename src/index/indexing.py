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
from aqt.utils import showInfo
from aqt.qt import *
import aqt
import time
import os
import sqlite3

from ..state import get_index, set_index, get_edit
from ..debug_logging import *
from ..web.web import show_search_result_area, print_starting_info, fillDeckSelect, setup_ui_after_index_built
from ..web.html import loadSynonyms
from .fts_index import FTSIndex
from .indexing_data import get_notes_in_collection, index_data_size
from ..notes import get_all_notes
import utility.misc
import state


def build_index(force_rebuild = False, execute_after_end = None):

    state.index_data        = get_notes_in_collection()
    state.index_data_size   = index_data_size()
    if get_index() is None:
        p               = ProcessRunnable(_build_index, force_rebuild)

        if execute_after_end is not None:
            p.after_end = execute_after_end
        p.start()

def _build_index(force_rebuild = False):

    """
    Builds the index. Result is stored in global var index.
    The index.type is either "Whoosh"/"SQLite FTS3"/"SQLite FTS4"/"SQLite FTS5"
    """
    start                               = time.time()
    config                              = mw.addonManager.getConfig(__name__)
    
    index                               = FTSIndex(force_rebuild)
    end                                 = time.time()
    initializationTime                  = round(end - start)
 
    index.ui.remove_divs                = config["removeDivsFromOutput"]
    index.ui.gridView                   = config["gridView"]
    index.ui.scale                      = config["noteScale"]
    index.ui.fields_to_hide_in_results  = config["fieldsToHideInResults"]
    index.selectedDecks                 = ["-1"]
    index.lastSearch                    = None
    index.lastResDict                   = None
    index.topToggled                    = True
    index.highlighting                  = config["highlighting"]
    index.ui.edited                     = {}
    index.initializationTime            = initializationTime
    index.synonyms                      = loadSynonyms()
    index.logging                       = config["logging"]
    index.searchbar_mode                = config["searchbar.default_mode"]
    index.ui.showRetentionScores        = config["showRetentionScores"]
    index.ui.hideSidebar                = config["hideSidebar"]
    index.limit                         = max(10, min(5000, config["numberOfResults"]))

    editor                              = aqt.mw.app.activeWindow().editor if hasattr(aqt.mw.app.activeWindow(), "editor") else None
    if editor is not None and editor.addMode:
        index.ui.set_editor(editor)

    set_index(index)
    # set_corpus(None)
    editor                              = editor if editor is not None else get_edit()
    setup_ui_after_index_built(editor, index)
    fillDeckSelect(editor)
    print_starting_info(editor)





class ProcessRunnable(QRunnable):
    """ Only used to build the index in background atm. """

    def __init__(self, target, *args):
        QRunnable.__init__(self)
        self.t          = target
        self.args       = args
        self.after_end  = None

    def run(self):
        self.t(*self.args)
        if self.after_end is not None:
            self.after_end()

    def start(self):
        QThreadPool.globalInstance().start(self)
