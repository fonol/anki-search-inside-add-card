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

import datetime
import time
from aqt import mw
import random

import utility.misc
try:
    from .state import check_index
    from .models import SiacNote, IndexNote
except:
    from state import check_index
    from models import SiacNote, IndexNote


"""
Various functions to retrieve (Anki) notes based on special search criteria.
Todo: add typing annotation
"""

def get_notes_added_on_day_of_year(day_of_year : int, limit: int):
    
    date_now            = datetime.datetime.utcnow() 
    date_year_begin     = datetime.datetime(year=date_now.year, month=1, day=1, hour=0, minute=0)    
    date_then           = date_year_begin + datetime.timedelta(day_of_year)
    nid_midnight        = int(date_then.timestamp() * 1000)
    nid_next_midnight   = nid_midnight + 24 * 60 * 60 * 1000
    res                 = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc limit 200" % (nid_midnight, nid_next_midnight))
    return to_notes(res)


def get_cal_info_context(day_of_year : int):

    date_now                        = datetime.datetime.utcnow() 
    oneday                          = 24 * 60 * 60 * 1000
    date_year_begin                 = datetime.datetime(year=date_now.year, month=1, day=1, hour=0 ,minute=0)    
    date_then                       = date_year_begin + datetime.timedelta(day_of_year)
    nid_midnight                    = int(date_then.timestamp() * 1000)
    date_then_str                   = time.strftime('%a, %d %B, %Y', time.localtime((nid_midnight + 1000) / 1000))
    nid_midnight_three_days_before  = nid_midnight - 3 * oneday
    nid_midnight_three_days_after   = nid_midnight + 4 * oneday
    res                             = mw.col.db.all("select distinct notes.id from notes where id > %s and id < %s order by id asc" % (nid_midnight_three_days_before, nid_midnight_three_days_after))
    context                         = [0, 0, 0, 0, 0, 0, 0]

    for nid in res:
        context[int((nid[0] - nid_midnight_three_days_before) / oneday)] += 1

    html_content                    = ""

    for i, cnt in enumerate(context):
        if cnt > 20:
            color = "cal-three"
        elif cnt > 10:
            color = "cal-two"
        elif cnt > 0:
            color = "cal-one"
        else: 
            color = ""
        html_content += """<div class='cal-block-week %s %s' data-index='%s' onclick='pycmd("siac-cal-info %s")'>%s</div>""" % (color, "cal-lg" if i == 3 else "", day_of_year - (3 - i),day_of_year - (3 - i), cnt)
    html = """
    
    <div class='ta_center' style='margin-bottom: 4px;'>
        <span>%s</span> 
    </div>
    <div class='ta_center w-100'>%s</div>""" % (date_then_str, html_content)    

    return html


def get_created_same_day(nid, pinned, limit):

    try:
        nidMinusOneDay  = nid - (24 * 60 * 60 * 1000)
        nidPlusOneDay   = nid + (24 * 60 * 60 * 1000)

        res             = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid desc" %(nidMinusOneDay, nidPlusOneDay))

        dayOfNote       = int(time.strftime("%d", time.localtime(nid/1000)))
        rList           = []
        c               = 0

        for r in res:
            dayCreated = int(time.strftime("%d", time.localtime(int(r[0])/1000)))
            if dayCreated != dayOfNote:
                continue
            if not str(r[0]) in pinned:
                rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))
                c += 1
                if c >= limit:
                    break
        return rList
    except:
        return []
        

def getRandomNotes(decks, limit):

    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""

    if deckQ:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s and notes.id in (select id from notes order by random() limit %s)" % (deckQ, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id in (select id from notes order by random() limit %s)" % (limit))
    res = to_notes(res)
    if len(res) > 0:
        random.shuffle(res)

    return res

def get_last_added_anki_notes(limit):
    """ Get notes ordered by their nid descending, no decks or pinned notes excluded. """

    res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid order by nid desc limit %s" % limit)
    return to_notes(res)

def get_notes_by_created_date(index, editor, decks, limit, sortOrder):

    if sortOrder == "desc":
        index.lastSearch = (None, decks, "lastCreated", limit)
    else:
        index.lastSearch = (None, decks, "firstCreated", limit)

    if not "-1" in decks and len(decks) > 0:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if len(deckQ) > 0:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s order by nid %s limit %s" %(deckQ, sortOrder, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid order by nid %s limit %s" % (sortOrder, limit))
    rList = []
    for r in res:
        #pinned items should not appear in the results
        if not str(r[0]) in index.pinned:
            rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))

    return rList


def getLastReviewed(decks, limit):
    if decks is not None and len(decks) > 0 and not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""

    if deckQ:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.id as rid from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid from notes join cr on notes.id = cr.nid where cr.did in %s order by cr.rid desc limit %s" % (deckQ, limit)
    else:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.id as rid from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid from notes join cr on notes.id = cr.nid order by cr.rid desc limit %s" % limit
    res = mw.col.db.all(cmd)
    return to_notes(res)

def getLastLapses(decks, limit):
    if decks is not None and len(decks) > 0 and not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""

    if deckQ:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.id as rid, revlog.ease from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid from notes join cr on notes.id = cr.nid where cr.ease = 1 and cr.did in %s order by cr.rid desc limit %s" % (deckQ, limit)
    else:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.id as rid, revlog.ease from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid from notes join cr on notes.id = cr.nid where cr.ease = 1 order by cr.rid desc limit %s" % limit
    res = mw.col.db.all(cmd)
    return to_notes(res)

def getRandomUntagged(decks, limit):
    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s and (tags is null or tags = '') order by random() limit %s" % (deckQ, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where tags is null or tags = '' order by random() limit %s" % limit)
    return to_notes(res) 
    
def get_last_untagged(decks, limit):
    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s and (tags is null or tags = '') order by notes.id desc limit %s" % (deckQ, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where tags is null or tags = '' order by notes.id desc limit %s" % limit)
    return to_notes(res) 

def findNotesWithLongestText(decks, limit, pinned):
    if not "-1" in decks and len(decks) > 0:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if pinned is None:
        pinned = []
    if len(deckQ) > 0:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s order by length(replace(trim(flds), '\u001f', '')) desc limit %s" %(deckQ, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid order by length(replace(trim(flds), '\u001f', '')) desc limit %s" % (limit ))
    rList = []
    for r in res:
        #pinned items should not appear in the results
        if not str(r[0]) in pinned:
            rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))
    return rList

def getByTimeTaken(decks, limit, mode):
    if decks is not None and len(decks) > 0 and not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""

    if deckQ:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.time, revlog.id as rid, revlog.ease from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid, avg(cr.time) as timeavg from notes join cr on notes.id = cr.nid where cr.ease = 1 and cr.did in %s group by cr.nid order by timeavg %s limit %s" % (deckQ, mode, limit)
    else:
        cmd = "with cr as (select cards.nid, cards.id, cards.did, revlog.time, revlog.id as rid, revlog.ease from revlog join cards on cards.id = revlog.cid) select distinct notes.id, flds, tags, cr.did, notes.mid, avg(cr.time) as timeavg from notes join cr on notes.id = cr.nid where cr.ease = 1 group by cr.nid order by timeavg %s limit %s" % (mode, limit)
    res = mw.col.db.all(cmd)
    rList = []
    for r in res:
        #rList.append((r[1], r[2], r[3], r[0], 1, r[4], ""))
        rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))

    return rList

def get_last_modified_notes(index, editor, decks, limit):

    if not "-1" in decks and len(decks) > 0:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if len(deckQ) > 0:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, notes.mid, notes.mod from notes left join cards on notes.id = cards.nid where did in %s order by notes.mod desc limit %s" %(deckQ, limit))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, notes.mid, notes.mod from notes left join cards on notes.id = cards.nid order by notes.mod desc limit %s" % (limit))
    rList = []
    for r in res:
        if not str(r[0]) in index.pinned:
            rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))
    
    return rList


def get_suspended(nids):
    res = mw.col.db.all("select distinct nid from cards where nid in (%s) and queue = -1" % ",".join([str(nid) for nid in nids]))
    res = [r[0] for r in res]
    return res


def to_notes(db_list):
    return list(map(lambda r : IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")), db_list))


