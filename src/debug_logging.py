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

import os
import sys
import json
from datetime import datetime
from aqt import mw
import time


try:
    from .state import get_index
except:
    from state import get_index
import utility.misc


def log(text):
    dir = utility.misc.get_addon_base_folder_path()
    try:
        with open(dir + 'log.txt', 'a', encoding="utf-8") as out:
            out.write(text + '\n')
    except:
        pass

def start_watch():
    return time.time() * 1000

def stop_watch(t_start):
    return time.time() * 1000 - t_start

def persist_index_info(search_index):
    """ Save some info on the search index in data.json, 
    which can be used on next startup to determine if the index should be rebuilt. """

    if search_index is None:
        return

    config                              = mw.addonManager.getConfig(__name__)
    c_json                              = _get_data_file_content() 

    if c_json is None:
        c_json                          = { "index": {}, "notes": {} }

    c_json["index"]["timestamp"]        = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c_json["index"]["type"]             = search_index.type 
    c_json["index"]["size"]             = search_index.get_number_of_notes()
    # not used yet
    c_json["index"]["lastInsertedId"]   = -1
    c_json["index"]["fieldsToExclude"]  = search_index.creation_info["fields_to_exclude_original"]
    c_json["index"]["decks"]            = search_index.creation_info["decks"]
    c_json["index"]["stopwordsSize"]    = search_index.creation_info["stopwords_size"]
    # not used yet
    c_json["index"]["shouldRebuild"]    = False

    _write_to_data_file(c_json)


def persist_notes_db_checked():
    """ Update "notes" - "db_last_checked" with current timestamp. """

    stamp                               = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    c_json                              = _get_data_file_content()

    if not "notes" in c_json:
        c_json["notes"] = {}

    c_json["notes"]["db_last_checked"]  = stamp

    _write_to_data_file(c_json)


def get_index_info():
    c_json = _get_data_file_content()
    if c_json is None:
        return None
    return c_json["index"]

def get_notes_info():
    c_json = _get_data_file_content()
    if "notes" in c_json:
        return c_json["notes"]
    return None

def _get_data_file_content():
    dir = utility.misc.get_user_files_folder_path()
    f = dir + "data.json"
    if not utility.misc.file_exists(f):
        return None
    try:
        with open(f, "r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except:
        # if it failed to read, probably for some encoding reason, create the file again
        os.remove(f)
        return None

def _write_to_data_file(c_json):
    f = utility.misc.get_user_files_folder_path() + "data.json"
    with open(f, "w", encoding="utf-8") as json_file:
        json.dump(c_json, json_file, indent=2)
        
def toggle_should_rebuild():
    c_json                              = _get_data_file_content() 
    c_json["index"]["shouldRebuild"]    = not c_json["index"]["shouldRebuild"]
    _write_to_data_file(c_json)


