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

import os
import typing
from typing import List, Dict, Any
from time import mktime

import utility.date

def scan_folder_for_changed_files(folder: str, last_index_date_stamp: str) -> List[str]:
    md_files = []
    unix_ts  = 0
    if last_index_date_stamp is not None and last_index_date_stamp != "":
        unix_ts  = mktime(utility.date.dt_from_stamp(last_index_date_stamp).timetuple())
    for dirp,_,files in os.walk(folder):
        md_files += [os.path.join(dirp, f).replace("\\", "/") for f in files if f.endswith(".md") and os.path.getmtime(os.path.join(dirp, f)) >= unix_ts]

    return md_files

def get_folder_structure(folder: str) -> Dict[str, Any]:

    folder      = folder.replace("\\", "/")
    if not folder.endswith("/"):
        folder += "/"

    md_files    = []
    for dirp,_,files in os.walk(folder):
        md_files += [os.path.join(dirp, f).replace("\\", "/").replace(folder, "") for f in files if f.endswith(".md")]

    dct = {}
    for f in md_files:
        p = dct
        for x in f.split('/'):
            p = p.setdefault(x, {})

    return dct

def create_md_file(folder: str, path: str, name: str):

    name   = name.strip()
    if not name or len(name) == 0:
        return
    if not folder or len(folder) == 0:
        return

    if not folder.endswith("/"):
        folder += "/"
    if not path.endswith("/"):
        path += "/"
    if not name.lower().endswith(".md"):
        name += ".md"

    fullpath = folder + path + name
    c        = 0
    while os.path.isfile(fullpath):
        c       += 1
        if (c == 1):
            fullpath = fullpath[:-3] + "_" + str(c) + ".md"
        else:
            fullpath = fullpath[:(-4-len(str(c)))] + "_" + str(c) + ".md"
    open(fullpath, "a").close()

def delete_md_file(fullpath):

    if not fullpath.endswith(".md"):
        return
    if not os.path.isfile(fullpath):
        return
    os.remove(fullpath)
    

def update_markdown_file(fpath: str, content: str) -> bool:
    try:
        with open(fpath, "w+", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[SIAC] Failed to create or update .md file for note: {fpath}")
        print(e)
        return False

            