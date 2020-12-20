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

import typing
from typing import List, Tuple
import utility.text


def to_tag_hierarchy(tags, sep="::"):
    tmap = {}
    for t in sorted(tags, key=lambda t: t.lower()):
        tmap = _add_to_tag_list(tmap, t, sep)
    tmap = dict(sorted(tmap.items(), key=lambda item: item[0].lower()))
    return tmap

def to_tag_hierarchy_by_recency(tags: List[Tuple[str, str]], sep: str ="::"):
    """ Returns a tag tree like to_tag_hierarchy, but ordered by timestamps. """
    tmap    = {}
    tsorted = [t[0] for t in sorted(tags, key=lambda t: t[1], reverse=True)]
    for t in tsorted:
        tmap = _add_to_tag_list(tmap, t, sep)
    # tmap = dict(sorted(tmap.items(), key=lambda item: item[0].lower()))
    return tmap



def iter_tag_map(tmap, prefix):
    if len(tmap) == 0:
        return []
    res = []
    if prefix:
        prefix = prefix + "::"
    for key, value in tmap.items():
        if type(value) is dict:
            if len(value) > 0:
                res.append(prefix + key)
                res +=  iter_tag_map(value, prefix + key)
            else:
                res.append(prefix + key)
    return res

def flatten_map(map, sep):
    changed = True

    while changed:
        changed = False
        updated = dict()
        for key, value in map.items():
            if len(value) == 1:
                changed = True
                new_key = key + sep + next(iter(value))
                updated[new_key] = value[next(iter(value))]
            else:
                updated[key] = value
        map = updated
    return map


def _add_to_tag_list(tmap, name, sep="::"):
    """
    Helper function to build the tag hierarchy.
    """
    names = [s for s in name.split(sep) if s != ""]
    for c, d in enumerate(names):
        found = tmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}}) 
    return tmap


def build_tag_string(tags, gridView, hover = True, maxLength = -1, maxCount = -1):
    """
    Builds the html for the tags that are displayed at the bottom right of each rendered search result.
    """
    html = ""
    tags_split = tags.split()
    tm = to_tag_hierarchy(tags_split)
    totalLength = sum([len(k) for k,v in tm.items()])
    if maxLength == -1:
        maxLength = 40 if not gridView else 30
    if maxCount == -1:
        maxCount = 3 if not gridView else 2
    if len(tm) <= maxCount or totalLength < maxLength:
        hover = "onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'" if hover else ""
        for t, s in tm.items():
            stamp = "siac-tg-" + utility.text.get_stamp()
            if len(s) > 0:
                tagData = " ".join(iter_tag_map({t : s}, ""))
                if len(s) == 1 and tagData.count("::") < 2 and not t in tags_split:
                    html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData.split(' ')[1]}' {hover} onclick='tagClick(this);'>{utility.text.trim_if_longer_than(tagData.split(' ')[1], maxLength)}</div>"
                else:
                    html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData}' {hover} onclick='tagClick(this);'>{utility.text.trim_if_longer_than(t, maxLength)} (+{len(s)})</div>" 
            else:
                html = f"{html}<div class='tagLbl' data-stamp='{stamp}' {hover} data-name='{t}' onclick='tagClick(this);'>{utility.text.trim_if_longer_than(t, maxLength)}</div>"
    else:
        stamp = "siac-tg-" + utility.text.get_stamp()
        tagData = " ".join(iter_tag_map(tm, ""))
        html = f"{html}<div class='tagLbl' data-stamp='{stamp}' data-tags='{tagData}' data-name='{tagData}' onclick='tagClick(this);'>{len(tm)} tags ...</div>" 

    return html