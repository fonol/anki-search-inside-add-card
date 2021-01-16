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
from ..web.html import loadSynonyms
from .fts_index import FTSIndex
from .indexing_data import get_notes_in_collection, get_addon_index_data
from ..notes import get_all_notes, create_or_update_md_notes
from ..output import UI
from ..web.reading_modal import Reader
import utility.misc
import state

from ..md import *


def build_index(force_rebuild = False, execute_after_end = None):

    config                  = mw.addonManager.getConfig(__name__)

    # scan for changed markdown files if a folder is set in config
    md_files          = []
    if (config["md.folder_path"] is not None 
        and len(config["md.folder_path"]) > 0
        and os.path.exists(config["md.folder_path"])):

        stamp                   = ""
        # if a last index stamp is set, we only have to look for files that are created/modified 
        # after the stamp
        if config['md.last_index_stamp']:
            stamp = config['md.last_index_stamp']
        md_files          = scan_folder_for_changed_files(config["md.folder_path"], stamp)

    # it would be more elegant to fetch the data in the index class
    # but older versions of Anki don't like the db being accessed from a different thread
    anki_index_data        = get_notes_in_collection()

    if get_index() is None:
        p               = ProcessRunnable(_build_index, anki_index_data, md_files, force_rebuild)

        if execute_after_end is not None:
            p.after_end = execute_after_end
        p.start()

def _build_index(anki_index_data, md_files, force_rebuild = False):

    """
    Builds the index. Result is stored in global var index.
    The index.type is either "SQLite FTS3"/"SQLite FTS4"/"SQLite FTS5"
    """
    start                               = time.time()
    config                              = mw.addonManager.getConfig(__name__)
    
    # if we have any .md files that are new/modified, 
    # we have to update the database ...
    if len(md_files) > 0:
        update_markdown_files(md_files)
        # ... and rebuild the index
        force_rebuild = True

    # addon notes are appended to the existing Anki notes
    addon_index_data                    = get_addon_index_data()

    index                               = FTSIndex(anki_index_data, addon_index_data, force_rebuild)

    end                                 = time.time()
    initializationTime                  = round(end - start)
 
    UI.remove_divs                      = config["removeDivsFromOutput"]
    UI.gridView                         = config["gridView"]
    UI.scale                            = config["noteScale"]
    UI.fields_to_hide_in_results        = config["fieldsToHideInResults"]
    index.selectedDecks                 = ["-1"]
    index.lastSearch                    = None
    index.lastResDict                   = None
    index.topToggled                    = True
    index.highlighting                  = config["highlighting"]
    UI.edited                           = {}
    index.initializationTime            = initializationTime
    index.synonyms                      = loadSynonyms()
    index.logging                       = config["logging"]
    index.searchbar_mode                = config["searchbar.default_mode"]
    UI.showRetentionScores              = config["showRetentionScores"]
    UI.hideSidebar                      = config["hideSidebar"]
    index.limit                         = max(10, min(5000, config["numberOfResults"]))

    editor                              = aqt.mw.app.activeWindow().editor if hasattr(aqt.mw.app.activeWindow(), "editor") else None
    if editor is not None and editor.addMode:
        UI.set_editor(editor)
        Reader.set_editor(editor)

    set_index(index)
    editor                              = editor if editor is not None else get_edit()
    if editor:
        UI.setup_ui_after_index_built(editor, index)
        UI.fillDeckSelect(editor)
        UI.print_starting_info()


def update_markdown_files(files: List[str]):
    """ Takes a list of .md files, creates/updates SIAC notes for each file. """

    fcontents = []
    config    = mw.addonManager.getConfig(__name__)
    md_folder = config["md.folder_path"].replace("\\", "/")
    flen      = len(md_folder)

    # read file contents
    for md_path in files:
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
            fcontents.append(("md:///"+md_path.strip("/"), content, f""" {"::".join(md_path[flen:].split("/")[:-1]).replace(" ", "_").strip("::")} """)) 

    # create or update SIAC notes in database
    create_or_update_md_notes(fcontents)

    # set stamp which can be used to determine md files that are changed since last index creation
    config["md.last_index_stamp"] = utility.date.date_now_stamp()
    mw.addonManager.writeConfig(__name__, config)


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
