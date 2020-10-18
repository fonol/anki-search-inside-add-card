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
import time
import os
import typing

from ..notes import get_all_notes, get_total_notes_count


def get_notes_in_collection():
    """ Reads the collection and builds a list of tuples (note id, note fields as string, note tags, deck id, model id) """

    config              = mw.addonManager.getConfig(__name__)
    deckList            = config['decks']
    deckStr             = ""

    for d in list(mw.col.decks.decks.values()):
        if d['name'] in deckList:
            deckStr += str(d['id']) + ","

    if len(deckStr) > 0:
        deckStr         = "(%s)" % (deckStr[:-1])

    if deckStr:
        oList           = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s" %(deckStr))
    else:
        oList           = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid")


    #load addon notes
    other_notes         = get_all_notes()

    index_notes = [(id, flds, t, did, str(mid), "") for (id, flds, t, did, mid) in oList]

    for (id, title, text, source, tags, nid, created, modified, reminder, _, _, _, _, _) in other_notes:

        text = title + "\u001f" + text + "\u001f" + source
        index_notes.append((id, text, tags, -1, "-1", ""))


    return index_notes


def index_data_size() -> int:
    """ Returns the amount of notes that would go into the index. """

    s = time.time() * 1000
    config              = mw.addonManager.getConfig(__name__)
    deckList            = config['decks']
    deckStr             = ""

    for d in list(mw.col.decks.decks.values()):
        if d['name'] in deckList:
            deckStr += str(d['id']) + ","

    if len(deckStr) > 0:
        deckStr         = "(%s)" % (deckStr[:-1])

    # todo: find out why count(distinct notes.id) returns slightly different number
    if deckStr:
        c_anki           = mw.col.db.scalar("select count(*) from (select distinct notes.id, did, mid from notes left join cards on notes.id = cards.nid where did in %s" %(deckStr))
    else:
        c_anki           = mw.col.db.scalar("select count(*) from (select distinct notes.id, did, mid from notes left join cards on notes.id = cards.nid)")

    if c_anki is None:
        c_anki = 0


    c_anki              = int(c_anki)
    c_addon             = get_total_notes_count()
    #load addon notes

    print(time.time() * 1000 - s)
    return c_anki + c_addon