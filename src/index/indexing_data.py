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

from ..notes import get_all_notes, get_total_notes_count


def get_notes_in_collection():
    """ Reads the collection and builds a list of tuples (note id, note fields as string, note tags, deck id, model id) """

    deck_q = _deck_query() 
  
    if deck_q:
        oList           = mw.col.db.all("select notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s group by notes.id" %(deck_q))
    else:
        oList           = mw.col.db.all("select notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid group by notes.id")

    index_notes = [(id, flds, t, did, str(mid), "") for (id, flds, t, did, mid) in oList]

    return index_notes


def get_addon_index_data():
    #load addon notes
    addon_notes         = get_all_notes()
    return [
        (id, title + "\u001f" + text[:3000] + "\u001f" + source + "\u001f" + (author if author else "") + "\u001f" + (url if url else ""), tags, -1, "-1", "") for 
        (id, title, text, source, tags, _, _, _, _, _, _, _, _, _, author, _, _, url) in addon_notes
    ]

def index_data_size() -> int:
    """ Returns the amount of notes that would go into the index. """

   
    deck_q = _deck_query() 

    # todo: find out why count(distinct notes.id) returns slightly different number
    if deck_q:
        c_anki           = mw.col.db.scalar("select count(*) from (select notes.id, did, mid from notes left join cards on notes.id = cards.nid where did in %s group by notes.id)" %(deck_q))
    else:
        c_anki           = mw.col.db.scalar("select count(*) from (select notes.id, did, mid from notes left join cards on notes.id = cards.nid group by notes.id)")

    if c_anki is None:
        c_anki = 0


    c_anki              = int(c_anki)
    c_addon             = get_total_notes_count()

    return c_anki + c_addon

def _deck_query():

    config              = mw.addonManager.getConfig(__name__)
    deck_list           = config['decks']
    q                   = ""

    if hasattr(mw.col.decks, "all_names_and_ids"):
        q =  ",".join([str(d.id) for d in mw.col.decks.all_names_and_ids() if d.name in deck_list])
    else:
        q = ",".join([str(d["id"]) for d in mw.col.decks.decks.values() if d['name'] in deck_list])

    if len(q) > 0:
        q               = "(%s)" % (q[:-1])
    return q
