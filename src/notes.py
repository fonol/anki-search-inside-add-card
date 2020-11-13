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
import glob
import shutil
import sqlite3
import typing
from typing import Optional, Tuple, List, Dict, Set, Any
from enum import Enum, unique
from datetime import datetime, time, date, timedelta
from aqt import mw
from aqt.utils import tooltip, showInfo
import random
import time

try:
    from .state import get_index
    from .models import SiacNote, IndexNote, NoteRelations
    from .config import get_config_value_or_default
    from .debug_logging import get_notes_info, persist_notes_db_checked
except:
    from state import get_index
    from models import SiacNote, IndexNote, NoteRelations
    from config import get_config_value_or_default
    from debug_logging import get_notes_info, persist_notes_db_checked
import utility.misc
import utility.tags
import utility.text
import utility.date

# will be set after the db file is accessed for the first time
db_path                 : Optional[str] = None

# How many times more important is a priority 100 item than a priority 1 item?
PRIORITY_SCALE_FACTOR   : int           = get_config_value_or_default("notes.queue.priorityScaleFactor", 5)

# how should priority be weighted
PRIORITY_MOD            : float         = get_config_value_or_default("notes.queue.priorityMod", 1.0)

# due notes from how many days ago shall be considered?
DUE_NOTES_BOUNDARY      : int           = get_config_value_or_default("notes.queue.due_note_boundary", 7)


@unique
class PDFMark(Enum):
    REVISIT     = 1
    HARD        = 2
    MORE_INFO   = 3
    MORE_CARDS  = 4
    BOOKMARK    = 5


def create_db_file_if_not_exists() -> bool:
    """ Called on add-on startup. """

    file_path   = _get_db_path()
    existed     = False
    if not os.path.isfile(file_path):
        conn = sqlite3.connect(file_path)

        creation_sql = """
            create table if not exists notes
            (
                id INTEGER PRIMARY KEY,
                title TEXT,
                text TEXT,
                source TEXT,
                tags TEXT,
                nid INTEGER,
                created TEXT,
                modified TEXT,
                reminder TEXT,
                lastscheduled TEXT,
                position INTEGER,
                extract_start INTEGER,
                extract_end INTEGER
            )
        """
        conn.execute(creation_sql)
    else:
        existed = True
        try:
            conn    = sqlite3.connect(file_path)
        except sqlite3.OperationalError:
            tmp = file_path.replace("siac-notes.db", "siac-notes.tmp.db")
            shutil.copyfile(file_path, tmp)
            os.remove(file_path)
            os.rename(tmp, file_path)
            conn    = sqlite3.connect(file_path)

        # check for backups
        backup_file = _get_todays_backup_path()
        if not os.path.isfile(backup_file):
            bu_folder = _backup_folder()
            if not os.path.isdir(bu_folder):
                os.mkdir(bu_folder)
            bconn = sqlite3.connect(backup_file)
            conn.backup(bconn)
            bconn.close()
            # only keep 10 newest backups, delete older ones
            limit   = 10
            backups = glob.glob(f"{bu_folder}siac-notes.backup.*")
            if len(backups) > limit:
                to_delete = sorted(backups)[:-limit]
                for f in to_delete:
                    os.remove(f)

    # disable for now
    # info_from_data_json = get_notes_info()
    # if info_from_data_json is not None and "db_last_checked" in info_from_data_json and len(info_from_data_json["db_last_checked"]) > 0:
    #     return

    conn.execute("""
        create table if not exists read
        (
            page INTEGER,
            nid INTEGER,
            pagestotal INTEGER,
            created TEXT,
            FOREIGN KEY(nid) REFERENCES notes(id)
        );

    """)
    conn.execute("""
        create table if not exists marks
        (
            page INTEGER,
            nid INTEGER,
            pagestotal INTEGER,
            created TEXT,
            marktype INTEGER,
            FOREIGN KEY(nid) REFERENCES notes(id)
        );
    """)
    conn.execute("""
        create table if not exists queue_prio_log
        (
            nid INTEGER,
            prio INTEGER,
            type TEXT,
            created TEXT
        );
    """)
    conn.execute("""
        create table if not exists highlights
        (
            nid INTEGER,
            page INTEGER,
            type INTEGER,
            grouping INTEGER,
            x0 REAL,
            y0 REAL,
            x1 REAL,
            y1 REAL,
            text TEXT,
            data TEXT,
            created TEXT
        );
    """)

    conn.execute("CREATE INDEX if not exists read_nid ON read (nid);")
    conn.execute("CREATE INDEX if not exists mark_nid ON marks (nid);")
    conn.execute("CREATE INDEX if not exists prio_nid ON queue_prio_log (nid);")
    conn.commit()

    #
    # Update code
    # For lack of some kind of versioning, simply attempt to alter the tables,
    # and ignore any sql errors thrown if the modifications did already exist.
    #
    try:
        # conn.execute(""" ALTER TABLE notes ADD COLUMN priority INTEGER; """)
        # conn.execute(""" ALTER TABLE notes ADD COLUMN last_done TEXT; """)
        # conn.execute(""" ALTER TABLE notes ADD COLUMN in_queue BOOLEAN; """)
        # conn.execute(""" ALTER TABLE notes ADD COLUMN extract_start INTEGER; """)
        # conn.execute(""" ALTER TABLE notes ADD COLUMN extract_end INTEGER;""")
        conn.commit()
    except:
        pass
    try:
        conn.execute("""
            Create table if not exists notes_pdf_page (
                nid INTEGER,
                siac_nid INTEGER,
                page INTEGER,
                type INTEGER,
                data TEXT,
                created TEXT
            )
        """)
        conn.commit()
    except:
        pass
    try:
        conn.execute(""" ALTER TABLE notes add column delay TEXT;""")
        conn.commit()
    except:
        pass
    finally:
        conn.close()

    # store a timestamp in /user_files/data.json to check next time, so we don't have to do this on every startup
    # persist_notes_db_checked()

    return existed


def create_note(title: str, text: str, source: str, tags: str, nid: int, reminder: str, queue_schedule: Optional[int], extract_start: Optional[int] = None, extract_end: Optional[int] = None) -> int:

    #clean the text
    # text    = utility.text.clean_user_note_text(text)

    if source is not None:
        source = source.strip()
    if (len(text) + len(title)) == 0:
        return
    if tags is not None and len(tags.strip()) > 0:
        tags = " %s " % tags.strip()
    else:
        tags = ""

    conn    = _get_connection()
    id      = conn.execute("""insert into notes (title, text, source, tags, nid, created, modified, reminder, lastscheduled, position, extract_start, extract_end, delay)
                values (?,?,?,?,?,datetime('now', 'localtime'),"",?,"", NULL, ?, ?, NULL)""", (title, text, source, tags, nid, reminder, extract_start, extract_end)).lastrowid
    conn.commit()
    conn.close()
    if queue_schedule is not None and queue_schedule != 0:
        update_priority_list(id, queue_schedule)
    index = get_index()
    if index is not None:
        index.add_user_note((id, title, text, source, tags, nid, ""))

    return id



#region priority queue

def _get_priority_list_with_last_prios() -> List[Tuple[Any, ...]]:
    """ Returns (nid, last prio, last prio creation, current position, schedule) """

    stp     = utility.date.date_x_days_ago_stamp(DUE_NOTES_BOUNDARY)
    sql     = f""" select notes.id, prios.prio, prios.created, notes.position, notes.reminder, notes.delay
                        from notes left join (select distinct nid, prio, max(created) as created, type from queue_prio_log group by nid) as prios on prios.nid = notes.id
                        where notes.position >= 0 or (substr(notes.reminder, 21, 10) <= '{utility.date.date_only_stamp()}' and substr(notes.reminder, 21, 10) >= '{stp}')
                        order by position asc"""
    conn    = _get_connection()
    res     = conn.execute(sql).fetchall()
    conn.close()
    return res

def recalculate_priority_queue(is_addon_start: bool = False):
    """
        Calculate the priority queue again, without writing anything to the
        priority log. Has to be done at least once on startup to incorporate the changed difference in days.

        Notes are marked in the DB for being in the priority queue by having a position set.
        After calling this function, the priority queue should contain:

        1. All notes that currently have a priority
        2. All notes that have a reminder (special schedule) that is due today or was due in the last <DUE_NOTES_BOUNDARY> days (older due dates are ignored)

    """

    current             = _get_priority_list_with_last_prios()
    scores              = []
    to_decrease_delay   = []
    now                 = datetime.now()

    #
    # loop once over all 'candidates' to calculate their score
    #
    for nid, last_prio, last_prio_creation, _, reminder, delay in current:

        if last_prio is None:
            # a note that has no priority and a reminder (special schedule) that is not due today or was due in
            # the last DUE_NOTES_BOUNDARY days won't appear in the queue
            if not _specific_schedule_is_due_today(reminder):
                continue
            else:
                last_prio = 50
                now                 += timedelta(seconds=1)
                ds                  = now.strftime('%Y-%m-%d-%H-%M-%S')
                last_prio_creation  = ds

        # assert(current_position >= 0)
        days_delta = max(0, (datetime.now() - _dt_from_date_str(last_prio_creation)).total_seconds() / 86400.0)

        # assert(days_delta >= 0)
        # assert(days_delta < 10000)
        score = _calc_score(last_prio, days_delta)
        scores.append((nid, last_prio_creation, last_prio, score, reminder, delay))

    sorted_by_scores    = sorted(scores, key=lambda x: x[3], reverse=True)
    final_list          = [s for s in sorted_by_scores if s[4] is None or len(s[4].strip()) == 0 or not _specific_schedule_is_due_today(s[4])]

    # put notes whose schedule is due today or was due in the last x days in front
    due_today           = [s for s in sorted_by_scores if s[4] is not None and len(s[4].strip()) > 0 and _specific_schedule_is_due_today(s[4])]
    if len(due_today) > 0:
        due_today   = sorted(due_today, key=lambda x : x[3], reverse=True)
        final_list  = due_today + final_list

    #
    # account for delays
    #

    # 1. on add-on start, check if delay was from another day, if so, it should be deleted
    if is_addon_start:
        for ix in range(0, len(final_list)):
            f = final_list[ix]
            if f[5] is not None and len(f[5]) > 0 and not utility.date.date_is_today(f[5].split("|")[0]):
                f               = list(f)
                f[5]            = f[5].split("|")[0]  + "|0"
                f               = tuple(f)
                final_list[ix]  = f

    # 2. apply delays (move items back in the list according to their delay)
    final_list = _apply_delays(final_list)

    # 3. delays have to be decreased by 1 on each calculation, so they will eventually be 0
    for ix, x in enumerate(final_list):
        if ix < _delay(x[5]):
            to_decrease_delay.append((x[0], ix))
        elif _delay(x[5]) <= 0:
            to_decrease_delay.append((x[0], 0))

    #
    # persist calculated order in db
    #
    conn    = _get_connection()
    c       = conn.cursor()

    # 1. null all positions (guarantee only the notes that are in the list calculated here will have a position (= be enqueued))
    # This will also remove notes from the queue that don't have a priority and whose scheduled due date is < today - DUE_NOTES_BOUNDARY days.
    c.execute(f"update notes set position = NULL where position is not NULL;")
    # 2. set positions (this basically marks a note as being in the queue)
    for ix, f in enumerate(final_list):
        c.execute(f"update notes set position = {ix} where id = {f[0]};")
    # 3. persist decreased delays
    for nid, new_delay in to_decrease_delay:
        if new_delay <= 0:
            c.execute(f"update notes set delay = NULL where id = {nid};")
        else:
            c.execute(f"update notes set delay = '{_date_now_str()}|{new_delay}' where id = {nid};")
    conn.commit()
    conn.close()


def update_priority_list(nid_to_update: int, schedule: int) -> Tuple[int, int]:
    """
    Call this after a note has been added or updated.
    Will read the current priority queue and update it.
    Will also insert the given priority in queue_prio_log.
    """
    # priority log entries that have to be inserted in the log
    to_update_in_log        = []
    # priority log entries that have to be removed from the log, because item is no longer in the queue
    to_remove_from_log      = []
    # notes whose delay will be decreased by one position
    to_decrease_delay       = []
    # will contain the ids in priority order, highest first
    final_list              = []
    index                   = -1

    current                 = _get_priority_list_with_last_prios()
    scores                  = []
    nid_was_included        = False
    now                     = datetime.now()

    for nid, last_prio, last_prio_creation, _, rem, delay in current:

        if last_prio is None:
            if not _specific_schedule_is_due_today(rem):
                continue
            else:
                last_prio           = 50
                now                 += timedelta(seconds=1)
                ds                  = now.strftime('%Y-%m-%d-%H-%M-%S')
                last_prio_creation  = ds

        if nid == nid_to_update:
            nid_was_included    = True
            if schedule == 0 or schedule is None:
                # if not in queue, remove from log
                to_remove_from_log.append(nid)
            else:
                score   = _calc_score(schedule, 0)
                now     += timedelta(seconds=1)
                ds      = now.strftime('%Y-%m-%d-%H-%M-%S')
                if not nid in [x[0] for x in to_update_in_log]:
                    to_update_in_log.append((nid, ds, schedule))
                scores.append((nid, ds, last_prio, score, rem, delay))
        else:
            days_delta = max(0, (datetime.now() - _dt_from_date_str(last_prio_creation)).total_seconds() / 86400.0)
            # assert(days_delta >= 0)
            # assert(days_delta < 10000)
            score = _calc_score(last_prio, days_delta)
            scores.append((nid, last_prio_creation, last_prio, score, rem, delay))
    # note to be updated doesn't have to be in the results, it might not have been in the queue before
    if not nid_was_included:
        if schedule == 0:
            to_remove_from_log.append(nid_to_update)
        else:
            now         += timedelta(seconds=1)
            ds          = now.strftime('%Y-%m-%d-%H-%M-%S')
            reminder    = get_reminder(nid_to_update)
            scores.append((nid_to_update, ds, schedule, _calc_score(schedule, 0), reminder, None))
            to_update_in_log.append((nid_to_update, ds, schedule))

    sorted_by_scores    = sorted(scores, key=lambda x: x[3], reverse=True)
    final_list          = [s for s in sorted_by_scores if s[4] is None or len(s[4].strip()) == 0 or not _specific_schedule_is_due_today(s[4])]

    due_today           = [s for s in sorted_by_scores if s[4] is not None and len(s[4].strip()) > 0 and _specific_schedule_is_due_today(s[4])]
    if len(due_today) > 0:
        due_today   = sorted(due_today, key=lambda x : x[3], reverse=True)
        final_list  = due_today + final_list

    # account for delays
    final_list = _apply_delays(final_list)

    for ix, s in enumerate(final_list):
        d = _delay(s[5])
        if d > 0 and ix <= d + 1:
            to_decrease_delay.append((s[0], d-1))

    # assert(len(scores) == 0 or len(final_list)  >0)
    # for s in scores:
    #     assert(s[3] >= 0)
    #     assert(s[1] is not None and len(s[1]) > 0)
    # assert(len(final_list) == len(set([f[0] for f in final_list])))

    # assert((len(to_update_in_log) + len(to_remove_from_log)) > 0)

    # update log and positions
    conn                    = _get_connection()
    conn.isolation_level    = None
    c                       = conn.cursor()
    c.execute("begin transaction")
    c.execute(f"update notes set position = NULL where position is not NULL;")

    for ix, f in enumerate(final_list):
        c.execute(f"update notes set position = {ix} where id = {f[0]};")
        if f[0] == nid_to_update:
            index = ix

    for nid in to_remove_from_log:
        c.execute(f"delete from queue_prio_log where nid = {nid};")
        #c.execute(f"update notes set reminder = '' where id = {nid};")

    for nid, created, prio in to_update_in_log:
        c.execute(f"insert into queue_prio_log (nid, prio, created) values ({nid}, {prio}, '{created}');")

    for nid, new_delay in to_decrease_delay:
        if new_delay <= 0:
            c.execute(f"update notes set delay = NULL where id = {nid};")
        else:
            c.execute(f"update notes set delay = '{_date_now_str()}|{new_delay}' where id = {nid};")
    c.execute("commit")
    conn.close()
    #return new position (0-based), and length of queue, some functions need that to update the ui
    return (index, len(final_list))

def remove_from_priority_list(nid_to_remove: int) -> Tuple[int, int]:
    """ Sets the position field of the given note to null and recalculates queue. """

    return update_priority_list(nid_to_remove, 0)

def update_priority_without_timestamp(nid_to_update: int, new_prio: int):
    """
    Updates the priority for the given note, without adding a new entry in
    queue_prio_log, if there is already one.
    This is useful to simply change the priority of a note in the queue without having it moved
    at the end of the queue, which would happen if a new entry would be created (time delta would be 0 or very small).
    """
    conn    = _get_connection()
    res     = conn.execute(f"select rowid from queue_prio_log where nid = {nid_to_update} order by created desc limit 1").fetchone()

    if res is None or len(res) == 0:
        created = _date_now_str()
        conn.execute(f"insert into queue_prio_log (nid, prio, type, created) values ({nid_to_update}, {new_prio}, '', '{created}')")
    else:
        conn.execute(f"update queue_prio_log set prio = {new_prio} where rowid = {res[0]}")
    conn.commit()
    conn.close()


def _apply_delays(schedule_list: List[Tuple[Any]]):
    """ Modify the queue order by moving back notes that have a delay set. """
    updated_list        = []
    for ix, s in enumerate(schedule_list):
        d = _delay(s[5])
        if d > 0:
            d += 1
        updated_list.append(((ix + d, s[5].split("|")[0] if d > 0 else "9"), s))
    updated_list = sorted(updated_list, key=lambda x : x[0])
    updated_list = [x[1] for x in updated_list]
    return updated_list

def _calc_score(priority: int, days_delta: float) -> float:
    prio_score = 1 + ((priority - 1) / 99) * (PRIORITY_SCALE_FACTOR - 1)
    if days_delta < 0.5:
        return days_delta + prio_score / (PRIORITY_MOD * 10000)
    else:
        return PRIORITY_SCALE_FACTOR * days_delta + PRIORITY_MOD * prio_score

#endregion priority queue



def remove_delay(nid: int):
    """ Clear the delay field for the given note. """
    conn = _get_connection()
    conn.execute(f"update notes set delay = NULL where id={nid}")
    conn.commit()
    conn.close()

def set_delay(nid: int, delay: int):
    """ Update the delay field for the given note. """
    conn = _get_connection()
    conn.execute(f"update notes set delay = '{_date_now_str()}|{delay}' where id={nid}")
    conn.commit()
    conn.close()

def set_source(nid: int, source: str):
    """ Update the source field for the given note. """
    conn = _get_connection()
    conn.execute(f"update notes set source = ? where id={nid}", [source])
    conn.commit()
    conn.close()


def get_reminder(nid: int) -> str:
    conn    = _get_connection()
    res     = conn.execute(f"select reminder from notes where id = {nid} limit 1").fetchone()
    if res is None:
        return None
    conn.close()
    return res[0]

def get_priority(nid: int) -> Optional[int]:
    conn    = _get_connection()
    res     = conn.execute(f"select prio from queue_prio_log where nid = {nid} order by created desc limit 1").fetchone()
    if res is None or len(res) == 0:
        return None
    conn.close()
    return res[0]

def get_priorities(nids: List[int]) -> Dict[int, int]:
    d = dict()
    if nids is None or len(nids) == 0:
        return d
    nid_str = ",".join([str(nid) for nid in nids])
    conn    = _get_connection()
    res     = conn.execute(f"select nid, prio, max(created) from queue_prio_log where nid in ({nid_str}) group by nid").fetchall()
    conn.close()
    for r in res:
        d[r[0]] = r[1]
    return d

def get_avg_priority() -> float:
    conn    = _get_connection()
    res     = conn.execute(f"select avg(prio) from (select prio, max(created) from queue_prio_log group by nid)").fetchone()
    conn.close()
    if res is None or len(res) == 0:
        return 0
    if res[0] is None:
        return 0
    return res[0]


def get_priority_as_str(nid: int) -> str:
    """ Get a str representation of the priority of the given note, e.g. 'Very high' """
    conn    = _get_connection()
    res     = conn.execute(f"select prio from queue_prio_log where nid = {nid} order by created desc limit 1").fetchone()
    conn.close()
    if res is None or len(res) == 0:
        return "No priority yet"
    return dynamic_sched_to_str(res[0])

def dynamic_sched_to_str(sched: int) -> str:
    """ Get a str representation of the given priority value, e.g. 'Very high' """
    if sched >= 85 :
        return f"Very high ({sched})"
    if sched >= 70:
        return f"High ({sched})"
    if sched >= 30:
        return f"Medium ({sched})"
    if sched >= 15:
        return f"Low ({sched})"
    if sched >= 1:
        return f"Very low ({sched})"
    return "Not in Queue (0)"

def update_reminder(nid: int, rem: str):
    if rem is None:
        rem = ""
    conn    = _get_connection()
    sql     = "update notes set reminder=?, modified=datetime('now', 'localtime') where id=? "
    conn.execute(sql, (rem, nid))
    conn.commit()
    conn.close()


def get_extracts(nid: int, source: str) -> List[Tuple[int, int]]:

    c   = _get_connection()
    res = c.execute(f"select extract_start, extract_end from notes where source = '{source}' and id != {nid} and extract_start >= 1").fetchall()
    c.close()
    if res is None:
        return []
    return res

def find_notes_with_similar_prio(nid_excluded: int, prio: int) -> List[Tuple[int, int, str]]:
    conn = _get_connection()
    if nid_excluded is not None:
        res = conn.execute(f"select p.prio, notes.id, notes.title from (select nid, prio from (select distinct nid, prio from queue_prio_log group by nid order by max(created) desc) order by abs(prio - {prio}) asc limit 10) as p join notes on p.nid = notes.id where notes.id != {nid_excluded} order by p.prio desc").fetchall()
    else:
        res = conn.execute(f"select p.prio, notes.id, notes.title from (select nid, prio from (select distinct nid, prio from queue_prio_log group by nid order by max(created) desc) order by abs(prio - {prio}) asc limit 10) as p join notes on p.nid = notes.id order by p.prio desc").fetchall()
    conn.close()
    return res

def get_notes_scheduled_for_today() -> List[SiacNote]:

    boundary    = utility.date.date_x_days_ago_stamp(DUE_NOTES_BOUNDARY)
    conn        = _get_connection()
    res         = conn.execute(f"select * from notes where reminder like '%|%' and substr(notes.reminder, 21, 10) <= '{utility.date.date_only_stamp()}' and substr(notes.reminder, 21, 10) >= '{boundary}'").fetchall()
    conn.close()
    return _to_notes(res)

def get_last_done_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select notes.* from (select distinct nid from queue_prio_log group by nid order by max(created) desc) as p join notes on p.nid = notes.id").fetchall()
    conn.close()
    return _to_notes(res)


def link_note_and_page(siac_nid: int, anki_nid: int, page: int):
    conn = _get_connection()
    conn.execute(f"insert into notes_pdf_page (nid, siac_nid, page, type, data, created) values ({anki_nid}, {siac_nid}, {page}, 1, '', '{_date_now_str()}')")
    conn.commit()
    conn.close()

def mark_page_as_read(nid: int, page: int, pages_total: int):
    now = _date_now_str()
    conn = _get_connection()
    conn.execute("insert or ignore into read (page, nid) values (%s, %s)" % (page, nid))
    conn.execute("update read set created = '%s', pagestotal = %s where page = %s and nid = %s" % (now, pages_total, page, nid))
    conn.commit()
    conn.close()

def mark_page_as_unread(nid: int, page: int):
    conn = _get_connection()
    conn.execute("delete from read where nid = %s and page = %s" % (nid, page))
    conn.commit()
    conn.close()

def mark_range_as_read(nid: int, start: int, end: int, pages_total: int):
    now = _date_now_str()
    conn = _get_connection()
    res = conn.execute(f"select page from read where nid={nid} and page > -1").fetchall()
    res = [r[0] for r in res]
    to_insert = []
    for p in range(start, end+1):
        if not p in res:
            to_insert.append((nid, p, now, pages_total))
    conn.executemany("insert into read (nid, page, created, pagestotal) values (?,?,?,?)", to_insert)
    conn.commit()
    conn.close()

def create_pdf_mark(nid: int, page: int, pages_total: int, mark_type: int):
    now = _date_now_str()
    conn = _get_connection()
    conn.execute("delete from marks where nid = %s and page = %s and marktype = %s" % (nid, page, mark_type))
    conn.execute("insert into marks (page, nid, pagestotal, created, marktype) values (?, ?, ?, ?, ?)", (page, nid, pages_total, now, mark_type))
    conn.commit()
    conn.close()

def toggle_pdf_mark(nid: int, page: int, pages_total: int, mark_type: int) -> List[Tuple[Any, ...]]:
    conn = _get_connection()
    if conn.execute("select nid from marks where nid = %s and page = %s and marktype = %s" % (nid, page, mark_type)).fetchone() is not None:
        conn.execute("delete from marks where nid = %s and page = %s and marktype = %s" % (nid, page, mark_type))
    else:
        now = datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
        conn.execute("insert into marks (page, nid, pagestotal, created, marktype) values (?, ?, ?, ?, ?)", (page, nid, pages_total, now, mark_type))
    res = conn.execute("select * from marks where nid = %s" % nid).fetchall()
    conn.commit()
    conn.close()
    return res

def delete_pdf_mark(nid: int, page: int, mark_type: int):
    conn = _get_connection()
    conn.execute("delete from marks where nid = %s and page %s and marktype = %s" % (nid, page, mark_type))
    conn.commit()
    conn.close()

def get_pdf_marks(nid: int) -> List[Tuple[Any, ...]]:
    conn = _get_connection()
    res = conn.execute("select * from marks where nid = %s" % nid).fetchall()
    conn.close()
    return res

def get_pdfs_by_sources(sources: List[str]) -> List[str]:
    """
    Takes a list of (full) paths, and gives back those for whom a pdf note exists with the given path.
    """
    src_str = "','".join([s.replace("'", "''") for s in sources])
    conn = _get_connection()
    res = conn.execute(f"select source from notes where source in ('{src_str}')").fetchall()
    conn.close()
    return [r[0] for r in res]

def get_pdf_id_for_source(source: str) -> int:
    """
    Takes a source and returns the id of the first note with the given source, if existing, else -1
    """
    conn = _get_connection()
    res = conn.execute(f"select id from notes where source = ?", (source,)).fetchone()
    conn.close()
    return -1 if res is None or len(res) == 0 else res[0]

def get_unqueued_notes_for_tag(tag: str) -> List[SiacNote]:
    if len(tag.strip()) == 0:
        return []
    query = ""
    for t in tag.split(" "):
        if len(t) > 0:
            t = t.replace("'", "''")
            if len(query) > 6:
                query += " or "
            query = f"{query}lower(tags) like '% {t} %' or lower(tags) like '% {t}::%' or lower(tags) like '%::{t} %' or lower(tags) like '{t} %' or lower(tags) like '%::{t}::%'"
    conn = _get_connection()
    res = conn.execute("select * from notes where (%s) and position is null order by id desc" %(query)).fetchall()
    conn.close()
    return _to_notes(res)

def get_read_pages(nid: int) -> List[int]:
    """ Get read pages for the given note as list. """
    conn = _get_connection()
    res = conn.execute("select page from read where nid = %s and page > -1 order by created asc" % nid).fetchall()
    conn.close()
    if res is None:
        return []
    return [r[0] for r in res]

def get_read(delta_days: int) -> Dict[int, Tuple[int, str]]:
    """ Get # of read pages by note ID. """
    stamp = utility.date.date_x_days_ago_stamp(abs(delta_days))
    conn = _get_connection()
    res  = conn.execute(f"select counts.c, counts.nid, notes.title from notes join (select count(*) as c, nid from read where page > -1 and created like '{stamp}%' group by nid) as counts on notes.id = counts.nid").fetchall()
    conn.close()
    d = dict()
    for c, nid, title in res:
        d[nid] = (c, title)
    return d

def get_read_last_n_days(delta_days: int) -> Dict[int, Tuple[int, str]]:
    """ Get # of read pages by note ID for the last n days. """
    stamp = utility.date.date_x_days_ago_stamp(abs(delta_days))
    conn = _get_connection()
    res  = conn.execute(f"select counts.c, counts.nid, notes.title from notes join (select count(*) as c, nid from read where page > -1 and created >= '{stamp}' group by nid) as counts on notes.id = counts.nid").fetchall()
    conn.close()
    d = dict()
    for c, nid, title in res:
        d[nid] = (c, title)
    return d

def get_read_last_n_days_by_day(delta_days: int) -> Dict[str, int]:
    """ Get # of read pages by dates. """
    stamp   = utility.date.date_x_days_ago_stamp(abs(delta_days))
    conn    = _get_connection()
    res     = conn.execute(f"select count(*) as c, substr(created, 0, 11) as date from read where page > -1 and created >= '{stamp}' group by substr(created, 0, 11)").fetchall()
    conn.close()
    d       = dict()
    for c, dt in res:
        d[dt] = c
    return d

def get_notes_by_future_due_date() -> Dict[str, List[SiacNote]]:
    """ Get notes that have a schedule due in the future. """

    conn    = _get_connection()
    res     = conn.execute(f"select * from notes where substr(reminder, 21, 10) >= '{utility.date.date_x_days_ago_stamp(DUE_NOTES_BOUNDARY)}'").fetchall()
    conn.close()
    res     = _to_notes(res)
    d       = dict()
    today   = datetime.today().date()
    for n in res:
        if n.current_due_date().date() < today:
            due = today.strftime("%Y-%m-%d")
        else:
            due = n.current_due_date().date().strftime("%Y-%m-%d")
        if not due in d:
            d[due] = []
        d[due].append(n)
    return d

def get_note_tree_data() -> Dict[str, List[Tuple[int, str]]]:
    """
        Fills a map with the data for the QTreeWidget in the Create dialog.
    """
    conn                    = _get_connection()
    last_created            = conn.execute("select id, title, created from notes order by datetime(created, 'localtime') desc limit 500").fetchall()
    conn.close()
    n_map                   = {}
    now                     = datetime.now()
    seconds_since_midnight  = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

    for id, title, created in last_created:
        cr = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
        diff = (now - cr).total_seconds()
        if diff < seconds_since_midnight:
            if "Today" not in n_map:
                n_map["Today"] = []
            n_map["Today"].append((id, utility.text.trim_if_longer_than(title, 100)))
        elif diff >= seconds_since_midnight and diff < (seconds_since_midnight + 86400):
            if "Yesterday" not in n_map:
                n_map["Yesterday"] = []
            n_map["Yesterday"].append((id, utility.text.trim_if_longer_than(title, 100)))
        else:
            diff_in_days = int((diff - seconds_since_midnight) / 86400.0) + 1
            if str(diff_in_days) + " days ago" not in n_map:
                n_map[str(diff_in_days) + " days ago"] = []
            n_map[str(diff_in_days) + " days ago"].append((id, utility.text.trim_if_longer_than(title, 100)))
    return n_map

def get_all_notes() -> List[Tuple[Any, ...]]:
    """ Fetch all add-on notes, used in indexing. """
    conn = _get_connection()
    res = list(conn.execute("select * from notes"))
    conn.close()
    return res

def get_total_notes_count() -> int:
    """ Returns the number of notes in the add-on's database. """
    conn    = _get_connection()
    c       = conn.execute("select count(*) from notes").fetchone()
    conn.close()
    if c is None or len(c) == 0:
        return 0
    if c[0] is None:
        return 0
    return c[0]


def get_untagged_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where tags is null or trim(tags) = '' order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_note(id: int) -> SiacNote:
    conn = _get_connection()
    res = conn.execute("select * from notes where id=" + str(id)).fetchone()
    conn.close()
    return _to_notes([res])[0]

def get_random_id_from_queue() -> int:
    conn = _get_connection()
    res = conn.execute("select id from notes where position >= 0 order by random() limit 1").fetchone()
    conn.close()
    if res is None or len(res) == 0:
        return -1
    return res[0]

def get_random_id() -> int:
    conn = _get_connection()
    res = conn.execute("select id from notes order by random() limit 1").fetchone()
    conn.close()
    if res is None or len(res) == 0:
        return -1
    return res[0]

def get_head_of_queue() -> int:
    conn = _get_connection()
    res = conn.execute("select id from notes where position >= 0 order by position asc limit 1").fetchone()
    conn.close()
    if res is None or len(res) == 0:
        return -1
    return res[0]

def update_note_text(id: int, text: str):
    conn = _get_connection()
    sql = """
        update notes set text=?, modified=datetime('now', 'localtime') where id=?
    """
    text = utility.text.clean_user_note_text(text)
    conn.execute(sql, (text, id))
    conn.commit()
    note = conn.execute(f"select title, source, tags from notes where id={id}").fetchone()
    conn.close()
    index = get_index()
    if index is not None:
        index.update_user_note((id, note[0], text, note[1], note[2], -1, ""))

def update_note_tags(id: int, tags: str):
    if not tags.endswith(" "):
        tags += " "
    if not tags.startswith(" "):
        tags = f" {tags}"
    conn = _get_connection()
    sql = """ update notes set tags=?, modified=datetime('now', 'localtime') where id=? """
    conn.execute(sql, (tags, id))
    conn.commit()
    note = conn.execute(f"select title, source, tags, text from notes where id={id}").fetchone()
    conn.close()
    index = get_index()
    if index is not None:
        index.update_user_note((id, note[0], note[3], note[1], tags, -1, ""))

def update_note(id: int, title: str, text: str, source: str, tags: str, reminder: str, priority: int):

    # text = utility.text.clean_user_note_text(text)
    tags = " %s " % tags.strip()
    mod = _date_now_str()
    sql = f"update notes set title=?, text=?, source=?, tags=?, modified='{mod}', reminder=? where id=?"
    conn = _get_connection()
    conn.execute(sql, (title, text, source, tags, reminder, id))
    conn.commit()
    conn.close()
    # a prio of -1 means unchanged, so don't update
    if priority != -1:
        update_priority_list(id, priority)
    index = get_index()
    if index is not None:
        index.update_user_note((id, title, text, source, tags, -1, ""))

def get_read_stats(nid: int) -> Tuple[Any, ...]:
    conn = _get_connection()
    res = conn.execute("select count(*), max(created), pagestotal from read where page > -1 and nid = %s" % nid).fetchall()
    res = res[0]
    if res[2] is None:
        r = conn.execute("select pagestotal from read where page = -1 and nid = %s" % nid).fetchone()
        if r is not None:
            res = (0, "", r[0])
    conn.close()
    return res

#
# highlights / annotation
#

def insert_highlights(highlights: List[Tuple[Any, ...]]):
    """
        [(nid,page,group,type,text,x0,y0,x1,y1)]
    """
    dt = _date_now_str()
    highlights = [h + (dt,) for h in highlights]
    conn = _get_connection()

    res = conn.executemany("insert into highlights(nid, page, grouping, type, text, x0, y0, x1, y1, created) values (?,?,?,?,?,?,?,?,?,?)", highlights)
    conn.commit()
    conn.close()

def delete_highlight(id: int):
    conn = _get_connection()
    conn.execute(f"delete from highlights where rowid = {id}")
    conn.commit()
    conn.close()

def get_highlights(nid: int, page: int) -> List[Tuple[Any, ...]]:
    conn = _get_connection()
    res = conn.execute(f"select rowid, * from highlights where nid = {nid} and page = {page}").fetchall()
    conn.close()
    return res

def update_text_comment_coords(id: int, x0: float, y0: float, x1: float, y1: float):
    conn = _get_connection()
    conn.execute(f"update highlights set x0 = {x0}, y0 = {y0}, x1 = {x1}, y1 = {y1} where rowid = {id}")
    conn.commit()
    conn.close()

def update_text_comment_text(id: int, text: str):
    conn = _get_connection()
    conn.execute("update highlights set text = ? where rowid = ?", (text, id))
    conn.commit()
    conn.close()


#
# end highlights
#


def get_all_tags() -> Set[str]:
    """
        Returns a set containing all tags (str) that appear in the user's notes.
    """
    conn = _get_connection()
    all_tags = conn.execute("select tags from notes where tags is not null").fetchall()
    conn.close()
    tag_set = set()
    for tag_str in all_tags:
        for t in tag_str[0].split():
            if len(t) > 0:
                if t not in tag_set:
                    tag_set.add(t)
    return tag_set

def find_by_tag(tag_str, to_output_list=True, only_explicit_tag=False):
    if len(tag_str.strip()) == 0:
        return []
    index = get_index()
    pinned = []
    if index is not None:
        pinned = index.pinned

    query = "where "
    for t in tag_str.split(" "):
        if len(t) > 0:
            t = t.replace("'", "''")
            if len(query) > 6:
                query += " or "
            if only_explicit_tag:
                query = f"{query}lower(tags) like '% {t} %' or lower(tags) like '{t} %'"
            else:
                query = f"{query}lower(tags) like '% {t} %' or lower(tags) like '% {t}::%' or lower(tags) like '%::{t} %' or lower(tags) like '{t} %' or lower(tags) like '%::{t}::%'"
    conn = _get_connection()
    res = conn.execute("select * from notes %s order by id desc" %(query)).fetchall()
    conn.close()
    if not to_output_list:
        return res
    return _to_notes(res, pinned)

def find_by_text(text: str):
    index = get_index()
    index.search(text, [])

def find_notes(text: str) -> List[SiacNote]:
    q = ""
    for token in text.lower().split():
        if len(token) > 0:
            token = token.replace("'", "")
            q = f"{q} or lower(title) like '%{token}%'"
    q = q[4:] if len(q) > 0 else ""
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def find_pdf_notes_by_title(text: str) -> List[SiacNote]:
    q = ""
    for token in text.lower().split():
        if len(token) > 0:
            token = token.replace("'", "")
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else ""
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and lower(source) like '%.pdf' order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def find_unqueued_pdf_notes(text: str) -> Optional[List[SiacNote]]:
    q = ""
    for token in text.lower().split():
        token = token.replace("'", "")
        if len(token) > 0:
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else ""
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and lower(source) like '%.pdf' and (position is null or position < 0) order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def find_unqueued_text_notes(text: str) -> Optional[List[SiacNote]]:
    q = ""
    for token in text.lower().split():
        token = token.replace("'", "")
        if len(token) > 0:
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else ""
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and not lower(source) like '%.pdf' and not lower(source) like '%youtube.com/watch%' and (position is null or position < 0) order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def find_unqueued_video_notes(text: str) -> Optional[List[SiacNote]]:
    q = ""
    for token in text.lower().split():
        token = token.replace("'", "")
        if len(token) > 0:
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else ""
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and lower(source) like '%youtube.com/watch%' and (position is null or position < 0) order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_most_used_pdf_folders() -> List[str]:
    sql = """
        select replace(source, replace(source, rtrim(source, replace(source, '/', '')), ''), '') from notes where lower(source) like '%.pdf'
        group by replace(source, replace(source, rtrim(source, replace(source, '/', '')), ''), '') order by count(*) desc limit 50
    """
    conn = _get_connection()
    res = conn.execute(sql).fetchall()
    conn.close()
    return [r[0] for r in res]

def get_position(nid: int) -> Optional[int]:
    conn = _get_connection()
    res = conn.execute("select position from notes where id = %s" % nid).fetchone()
    conn.close()
    if res is None or res[0] is None:
        return None
    return res[0]

def null_position(nid: int):
    conn = _get_connection()
    conn.execute("update notes set position = null where id = %s" % nid)
    conn.commit()
    conn.close()

def delete_note(id: int):
    update_priority_list(id, 0)
    conn = _get_connection()
    conn.executescript(f"""delete from read where nid ={id};
                            delete from marks where nid ={id};
                            delete from notes where id={id};
                            delete from queue_prio_log where nid={id};
                            delete from highlights where nid={id};
                            """)
    conn.commit()
    conn.close()

def get_read_today_count() -> int:
    now     = datetime.today().strftime('%Y-%m-%d')
    conn    = _get_connection()
    c       = conn.execute("select count(*) from read where page > -1 and created like '%s%%'" % now).fetchone()
    conn.close()
    if c is None:
        return 0
    return c[0]

def get_avg_pages_read(delta_days: int) -> float:
    dt      = date.today() - timedelta(delta_days)
    stamp   = dt.strftime('%Y-%m-%d')
    conn    = _get_connection()
    c       = conn.execute("select count(*) from read where page > -1 and created >= '%s'" % stamp).fetchone()
    conn.close()
    if c is None:
        return 0.0
    return float("{0:.1f}".format(c[0] / delta_days))


def get_queue_count() -> int:
    conn    = _get_connection()
    c       = conn.execute("select count(*) from notes where position is not null and position >= 0").fetchone()
    conn.close()
    return c[0]

def get_invalid_pdfs() -> List[SiacNote]:
    conn        = _get_connection()
    res         = conn.execute("select * from notes where lower(source) like '%.pdf'").fetchall()
    conn.close()
    filtered    = list()
    c           = 0
    for (_, _, _, source, _, _, _, _, _, _, _, _, _, _) in res:
        if not utility.misc.file_exists(source.strip()):
            filtered.append(res[c])
        c += 1
    return _to_notes(filtered)

def get_recently_used_tags() -> List[str]:
    """ Returns a [str] of max 20 tags, ordered by their usage desc. """

    counts  = _get_recently_used_tags_counts(100)
    ordered = [i[0] for i in list(sorted(counts.items(), key=lambda item: item[1], reverse = True))][:20]
    return ordered

def get_recently_used_tags_with_counts() -> Dict[str, int]:
    """ Returns a {str, int} of max 10 tags, ordered by their usage desc. """

    counts  = _get_recently_used_tags_counts(10)
    ordered = dict(sorted(counts.items(), key=lambda item: item[1], reverse = True))
    return ordered

def _get_recently_used_tags_counts(limit: int) -> Dict[str, int]:

    conn    = _get_connection()
    res     = conn.execute("select tags from notes where tags is not null order by id desc limit %s" % limit).fetchall()
    conn.close()
    if res is None or len(res) == 0:
        return dict()
    counts  = dict()
    for r in res:
        spl = r[0].split()
        for tag in spl:
            if tag in counts:
                counts[tag] += 1
            else:
                counts[tag] = 1
    return counts

def _get_priority_list(nid_to_exclude: int = None) -> List[SiacNote]:
    if nid_to_exclude is not None:
        sql = """
            select * from notes where position >= 0 and id != %s order by position asc
        """ % nid_to_exclude
    else:
        sql = """
            select * from notes where position >= 0 order by position asc
        """
    conn    = _get_connection()
    res     = conn.execute(sql).fetchall()
    conn.close()
    return _to_notes(res)


def get_priority_list() -> List[SiacNote]:
    """
        Returns all notes that have a position set.
    """
    conn    = _get_connection()
    sql     = """ select * from notes where position >= 0 order by position asc """
    res     = conn.execute(sql).fetchall()
    conn.close()
    return _to_notes(res)

def get_newest(limit: int, pinned: List[int]) -> List[SiacNote]:
    """
        Returns newest user notes ordered by created date desc.
    """
    conn = _get_connection()
    sql = """
       select * from notes order by datetime(created) desc limit %s
    """ % limit
    res = conn.execute(sql).fetchall()
    conn.close()
    return _to_notes(res, pinned)

def get_random(limit: int, pinned: List[int]) -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes order by random() limit %s" % limit).fetchall()
    conn.close()
    return _to_notes(res, pinned)

def get_queue_in_random_order() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where position is not null order by random()").fetchall()
    conn.close()
    return _to_notes(res)

def set_priority_list(ids: List[int]):
    ulist = list()
    for ix,id in enumerate(ids):
        ulist.append((ix, id))
    conn = _get_connection()
    conn.execute('update notes set position = NULL;')
    conn.executemany('update notes set position = ? where id = ?', ulist)
    conn.commit()
    conn.close()

def empty_priority_list():
    conn = _get_connection()
    conn.execute("update notes set position = null")
    conn.commit()
    conn.close()

def shuffle_queue():
    """ 
    This will 'shuffle' the queue by setting the last done date (created column in queue_prio_log) to some random value. 
    Priorities and schedules are unchanged.
    This will also recalculate the queue.
    """

    now     = datetime.now()
    conn    = _get_connection()
    nids    = conn.execute("select distinct nid, prio, max(created) from queue_prio_log group by nid").fetchall()
    conn.execute("delete from queue_prio_log")
    inserts = [(t[0], t[1], (now + timedelta(days= - random.randint(1, 365))).strftime('%Y-%m-%d-%H-%M-%S')) for t in nids]
    conn.executemany("insert into queue_prio_log (nid, prio, created) values(?,?,?)", inserts) 
    conn.commit()
    conn.close()
    recalculate_priority_queue()

def spread_priorities():

    conn    = _get_connection()
    vals    = conn.execute("select distinct nid, rowid, prio, max(created) from queue_prio_log group by nid").fetchall()
    max_p   = max([t[2] for t in vals])
    spread  = [(t[0], max(1, min(int((t[2] * 100) / max_p), 100)), t[3]) for t in vals]
    row_ids = ",".join([str(t[1]) for t in vals])
    conn.execute(f"delete from queue_prio_log where rowid in ({row_ids})")
    conn.executemany("insert into queue_prio_log (nid, prio, created) values(?,?,?)", spread) 
    conn.commit()
    conn.close()
    recalculate_priority_queue()

def get_all_tags_as_hierarchy(include_anki_tags: bool) -> Dict:
    tags = None
    if include_anki_tags:
        tags = mw.col.tags.all()
        user_note_tags = get_all_tags()
        tags.extend(user_note_tags)
    else:
        tags = get_all_tags()
    return utility.tags.to_tag_hierarchy(tags)

def get_all_text_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where not lower(source) like '%.pdf' and not lower(source) like '%youtube.com/watch%' order by rowid desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_all_video_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%youtube.com/watch%' order by rowid desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_all_pdf_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' order by rowid desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_all_unread_pdf_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' and id not in (select distinct nid from read where page >= 0) order by created desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_in_progress_pdf_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' and id in (select nid from (select nid, pagestotal, max(created) from read where page > -1  group by nid having count(nid) < pagestotal)) order by created desc").fetchall()
    conn.close()
    return _to_notes(res)


def get_pdf_notes_last_added_first(limit : int = None) -> List[SiacNote]:
    if limit:
        limit = f"limit {limit}"
    else:
        limit = ""
    conn = _get_connection()
    res = conn.execute(f"select * from notes where lower(source) like '%.pdf' order by id desc {limit}").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_notes_last_read_first() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select notes.id,notes.title,notes.text,notes.source,notes.tags,notes.nid,notes.created,notes.modified,notes.reminder,notes.lastscheduled,notes.position,notes.extract_start,notes.extract_end,notes.delay from notes join read on notes.id == read.nid where lower(notes.source) like '%.pdf' group by notes.id order by max(read.created) desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_notes_ordered_by_size(order: str) -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute(f"select notes.id,notes.title,notes.text,notes.source,notes.tags,notes.nid,notes.created,notes.modified,notes.reminder,notes.lastscheduled,notes.position,notes.extract_start,notes.extract_end,notes.delay from notes join read on notes.id == read.nid where lower(notes.source) like '%.pdf' group by notes.id order by max(read.pagestotal) {order}").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_notes_not_in_queue() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' and position is null order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_text_notes_not_in_queue() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where not lower(source) like '%.pdf' and not lower(source) like '%youtube.com/watch%' and position is null order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_video_notes_not_in_queue() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%youtube.com/watch%' and position is null order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_quick_open_suggestions() -> List[SiacNote]:
    conn        = _get_connection()
    last_added  = conn.execute("select * from notes where lower(source) like '%.pdf' order by id desc limit 8").fetchall()
    last_read   = conn.execute("select notes.id,notes.title,notes.text,notes.source,notes.tags,notes.nid,notes.created,notes.modified,notes.reminder,notes.lastscheduled,notes.position,notes.extract_start,notes.extract_end,notes.delay from notes join read on notes.id == read.nid where lower(notes.source) like '%.pdf' group by notes.id order by max(read.created) desc limit 8").fetchall()
    conn.close()
    res         = []
    used        = set()
    for nt in zip(last_read, last_added):
        if nt[0] is not None and not nt[0][0] in used:
            res.append(nt[0])
            used.add(nt[0][0])
        if nt[1] is not None and not nt[1][0] in used:
            res.append(nt[1])
            used.add(nt[1][0])
        if len(res) >= 8:
            break
    return _to_notes(res)

def get_pdf_info(nids: List[int]) -> List[Tuple[int, int, int]]:
    """ Returns tuples of (nid, read pages, pages total) for all the given note IDs. """

    nids    = ",".join([str(n) for n in nids])
    sql     = f"""select nid, pagestotal,
                case count(*)
                    when 1 then
                        case page when -1 then 0 else 1 end
                    else count(*) - 1
                end, max(created) from read where nid in ({nids}) and page >= -1 group by nid"""
    conn    = _get_connection()
    res     = conn.execute(sql).fetchall()
    conn.close()
    ilist   = [(r[0], r[2], r[1]) for r in res]
    return ilist

def get_related_notes(id: int) -> NoteRelations:
    """ Find note suggestions for the given note. """

    note                = get_note(id)
    title               = note.title

    if title is not None and len(title.strip()) > 1:
        related_by_title = find_notes(title)
    else:
        related_by_title = []

    related_by_tags     = []
    related_by_folder   = []

    if note.tags is not None and len(note.tags.strip()) > 0:
        tags = note.tags.strip().split(" ")
        tags = sorted(tags, key=lambda x: x.count("::"), reverse=True)
        #begin with most specific tag
        conn = _get_connection()
        for t in tags:
            if len(t) > 0:
                t = t.replace("'", "''")
                query = f"where lower(tags) like '% {t} %' or lower(tags) like '% {t}::%' or lower(tags) like '%::{t} %' or lower(tags) like '{t} %' or lower(tags) like '%::{t}::%'"
                res = conn.execute("select * from notes %s order by id desc" %(query)).fetchall()
                if len(res) > 0:
                    related_by_tags += res
                if len(related_by_tags) >= 10:
                    break
        conn.close()
        related_by_tags = _to_notes(related_by_tags)

    if note.is_pdf() and note.get_containing_folder():
        conn    = _get_connection()
        res     = conn.execute(f"select * from notes where id != {id} and source glob '{note.get_containing_folder()}[^/]*' order by created desc limit 5").fetchall()
        conn.close()
        if res:
            related_by_folder += res
            related_by_folder = _to_notes(related_by_folder)

    return NoteRelations(related_by_title, related_by_tags, related_by_folder)

def mark_all_pages_as_read(note: SiacNote, num_pages: int):
    now         = _date_now_str()
    conn        = _get_connection()
    existing    = [r[0] for r in conn.execute("select page from read where page > -1 and nid = %s" % note.id).fetchall()]
    start       = note.extract_start if note.extract_start is not None else 1
    to_insert   = [(p, note.id, num_pages, now) for p in range(start, num_pages +1) if p not in existing]
    conn.executemany("insert into read (page, nid, pagestotal, created) values (?, ?, ?, ?)", to_insert)
    conn.commit()
    conn.close()

def mark_as_read_up_to(note: SiacNote, page: int, num_pages: int):
    now         = _date_now_str()
    start       = note.extract_start if note.extract_start is not None else 1
    end         = min(note.extract_end + 1,page + 1) if note.extract_start is not None else page + 1
    if end <= start:
        return
    conn        = _get_connection()
    existing    = [r[0] for r in conn.execute("select page from read where page > -1 and nid = %s" % note.id).fetchall()]
    to_insert   = [(p, note.id, num_pages, now) for p in range(start, end) if p not in existing]
    conn.executemany("insert into read (page, nid, pagestotal, created) values (?, ?, ?, ?)", to_insert)
    conn.commit()
    conn.close()

def mark_all_pages_as_unread(nid: int):
    conn = _get_connection()
    conn.execute("delete from read where nid = %s and page > -1" % nid)
    conn.commit()
    conn.close()

def insert_pages_total(nid: int, pages_total: int):
    """
        Inserts a special page entry (page = -1), that is used to save the number of pages even if no page has been read yet.
    """
    conn = _get_connection()
    existing = conn.execute("select * from read where page == -1 and nid = %s" % nid).fetchone()
    if existing is None or len(existing) == 0:
        conn.execute("insert into read (page, nid, pagestotal, created) values (-1,%s,%s, datetime('now', 'localtime'))" % (nid, pages_total))
    conn.commit()
    conn.close()

#region stats

def pdf_topic_distribution() -> List[Tuple[str, float]]:
    """ Counts the tags used in PDF notes and returns an ordered list of tag - percentage share pairs. """

    conn    = _get_connection()
    res     = conn.execute("select tags from notes where trim(tags, ' ') != '' and lower(source) like '%.pdf'").fetchall()
    conn.close()
    if not res:
        return []
    d = dict()
    for r in res:
        for t in r[0].split():
            if len(t) > 0:
                if t in d:
                    d[t] += 1
                else:
                    d[t] = 1

    total_c     = sum(d.values())
    res_list    = [(utility.text.trim_if_longer_than(k, 60), v * 100 / total_c) for k,v in d.items()]
    res_list    = sorted(res_list, key=lambda x: x[1])
    return res_list

def pdf_topic_distribution_recently_read(delta_days: int) -> List[Tuple[str, float]]:
    """ Counts the tags used in PDF notes which where recently read and returns an ordered list of tag - percentage share pairs. """

    stamp   = utility.date.date_x_days_ago_stamp(abs(delta_days))
    conn    = _get_connection()
    res     = conn.execute(f"select notes.tags from notes join read on notes.id = read.nid where read.created > '{stamp}' and trim(notes.tags, ' ') != ''").fetchall()
    conn.close()
    if not res:
        return []
    d = dict()
    for r in res:
        for t in r[0].split():
            if len(t) > 0:
                if t in d:
                    d[t] += 1
                else:
                    d[t] = 1

    total_c     = sum(d.values())
    res_list    = [(utility.text.trim_if_longer_than(k, 60), v * 100 / total_c) for k,v in d.items()]
    res_list    = sorted(res_list, key=lambda x: x[1])
    return res_list

#endregion stats

#region page-note linking

def get_linked_anki_notes_for_pdf_page(siac_nid: int, page: int) -> List[IndexNote]:
    """ Query to retrieve the Anki notes that were created while on a given pdf page. """

    conn = _get_connection()
    nids = conn.execute(f"select nid from notes_pdf_page where siac_nid = {siac_nid} and page = {page}").fetchall()
    if not nids or len(nids) == 0:
        return []
    nids_str = ",".join([str(nid[0]) for nid in nids])
    res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id in (%s)" % nids_str)
    if len(res) != len(nids):
        anki_nids = [r[0] for r in res]
        siac_nids = [r[0] for r in nids]
        for snid in siac_nids:
            if snid not in anki_nids:
                conn.execute(f"delete from notes_pdf_page where nid = {snid}")
        conn.commit()
    conn.close()
    return _anki_to_index_note(res)

def get_linked_anki_notes_around_pdf_page(siac_nid: int, page: int) -> List[Tuple[int, int]]:
    conn = _get_connection()
    nps  = conn.execute(f"select page from notes_pdf_page where siac_nid = {siac_nid} and page >= {page-6} and page <= {page + 6}").fetchall()
    conn.close()
    if not nps or len(nps) == 0:
        return []
    return [n[0] for n in nps]

def get_deck_mostly_linked_to_note(siac_nid: int) -> Optional[str]:
    """ Count which deck was most common among Anki notes that have been created while reading the given note. """

    conn = _get_connection()
    nids = conn.execute(f"select nid from notes_pdf_page where siac_nid = {siac_nid} order by rowid desc limit 50").fetchall()
    conn.close()
    if len(nids) == 0:
        return None
    nids = ",".join([str(nid[0]) for nid in nids])
    res = mw.col.db.first(f"select did, count(did) as cnt from (select did from cards where nid in ({nids})) group by did order by cnt desc limit 1")
    if res is None:
        return None
    did = res[0]
    try:
        d = mw.col.decks.get(did)["name"]
        return d
    except:
        return None

def get_last_linked_notes(siac_nid: int, limit: int = 10) -> List[int]:
    """ Returns the last linked Anki note IDs for the given add-on note. """
    conn = _get_connection()
    nids = conn.execute(f"select nid from notes_pdf_page where siac_nid = {siac_nid} order by rowid desc limit {limit}").fetchall()
    conn.close()
    if not nids:
        return []
    return [nid[0] for nid in nids]


#endregion page-note linking

#
# helpers
#

def _get_connection() -> sqlite3.Connection:
    file_path = _get_db_path()
    return sqlite3.connect(file_path)

def _get_db_path() -> str:
    global db_path
    if db_path is not None:
        return db_path
    config    = mw.addonManager.getConfig(__name__)
    file_path = config["addonNoteDBFolderPath"]
    # if db file path is not set yet, pick application data folder
    if file_path is None or len(file_path.strip()) == 0:
        file_path = utility.misc.get_application_data_path()
        config["addonNoteDBFolderPath"] = file_path
        mw.addonManager.writeConfig(__name__, config)
        if not os.path.isdir(file_path):
            os.mkdir(file_path)
        ex = utility.misc.get_user_files_folder_path() + "siac-notes.db"
        # there might be an existing file in user_files, if so, copy it to new location
        try:
            if os.path.isfile(ex):
                shutil.copyfile(ex, file_path + "siac-notes.db")
                if os.path.isfile(file_path + "siac-notes.db"):
                    os.remove(ex)
        except:
            pass

    if not os.path.isdir(file_path):
        os.mkdir(file_path)
    file_path += "siac-notes.db"
    file_path.strip()
    db_path = file_path
    return file_path

def _get_todays_backup_path() -> str:
    """ Get the path to the timestamped backup db file. """

    file_path = mw.addonManager.getConfig(__name__)["addonNoteDBFolderPath"]
    if file_path is None or len(file_path) == 0:
        file_path = utility.misc.get_user_files_folder_path()
    file_path += f"siac_backups/siac-notes.backup.{utility.date.date_only_stamp()}.db"
    return file_path.strip()

def _backup_folder() -> str:
    """ Get the full path to the backup folder. """
    if db_path:
        return db_path.replace("siac-notes.db", "siac_backups/")
    file_path = mw.addonManager.getConfig(__name__)["addonNoteDBFolderPath"]
    if file_path is None or len(file_path) == 0:
        file_path = utility.misc.get_user_files_folder_path()
    file_path += f"siac_backups/"
    return file_path.strip()



def _to_notes(db_list: List[Tuple[Any, ...]], pinned: List[int] = []) -> List[SiacNote]:
    notes = list()
    for tup in db_list:
        if not str([tup[0]]) in pinned:
            notes.append(SiacNote(tup))
    return notes

def _specific_schedule_is_due_today(sched_str: str) -> bool:
    if not "|" in sched_str:
        return False
    dt = _dt_from_date_str(sched_str.split("|")[1])
    return dt.date() <= datetime.today().date() and dt.date() >= (datetime.today() - timedelta(days=DUE_NOTES_BOUNDARY)).date()

def _specific_schedule_was_due_before_today(sched_str: str) -> bool:
    if not "|" in sched_str:
        return False
    dt = _dt_from_date_str(sched_str.split("|")[1])
    return dt.date() < datetime.today().date()

def _delay(delay_str: str) -> int:
    if delay_str is None or len(delay_str.strip()) == 0 or not "|" in delay_str:
        return 0
    return int(delay_str.split("|")[1])

def _date_now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

def _dt_from_date_str(dtst) -> datetime:
    return datetime.strptime(dtst, '%Y-%m-%d-%H-%M-%S')

def _table_exists(name) -> bool:
    conn = _get_connection()
    res = conn.execute(f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{name}'").fetchone()
    conn.close()
    if res[0]==1:
        return True
    return False

def _anki_to_index_note(db_list: List[Tuple[Any, ...]]) -> List[IndexNote]:
    return list(map(lambda r : IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")), db_list))

def _convert_manual_prio_to_dynamic(prio: int) -> int:
    if prio == 2 or prio == 7:
        return 5
    if prio == 3:
        return 4
    if prio == 8 or prio == 4:
        return 3
    if prio == 0:
        return 2
    # count random as average
    if prio == 6:
        return 3
    return 1
