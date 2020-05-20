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
    from .models import SiacNote, NoteRelations
    from .config import get_config_value_or_default
    from .debug_logging import get_notes_info, persist_notes_db_checked
except:
    from state import get_index
    from models import SiacNote, NoteRelations
    from config import get_config_value_or_default
    from debug_logging import get_notes_info, persist_notes_db_checked
import utility.misc
import utility.tags
import utility.text
import utility.date

db_path: Optional[str] = None

# How many times more important is a priority 100 item than a priority 1 item?
PRIORITY_SCALE_FACTOR: int = get_config_value_or_default("notes.queue.priorityScaleFactor", 5)

# if a note was scheduled for some time point in the past, but not done, 
# 1. schedule can be removed ('remove-schedule'), 
# 2. note can be placed in front of the queue ('place-front') or
# 3. note can be scheduled again from the missed due date on ('new-schedule')
MISSED_NOTES_HANDLING: str = get_config_value_or_default("notes.queue.missedNotesHandling", "remove-schedule")

@unique
class PDFMark(Enum):
    REVISIT = 1
    HARD = 2
    MORE_INFO = 3
    MORE_CARDS = 4
    BOOKMARK = 5


def create_db_file_if_not_exists() -> bool:
    file_path = _get_db_path()
    existed = False
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
                position INTEGER
            )
        """
        conn.execute(creation_sql)
    else:
        existed = True
        conn = sqlite3.connect(file_path)
    
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
    conn.close()

    # store a timestamp in /user_files/data.json to check next time, so we don't have to do this on every startup
    # persist_notes_db_checked()
    return existed


def create_note(title: str, text: str, source: str, tags: str, nid: int, reminder: str, queue_schedule: Optional[int]):

    #clean the text
    text = utility.text.clean_user_note_text(text)

    if source is not None:
        source = source.strip()
    if (len(text) + len(title)) == 0:
        return
    if tags is not None and len(tags.strip()) > 0:
        tags = " %s " % tags.strip()
    else: 
        tags = ""

    conn = _get_connection()
    id = conn.execute("""insert into notes (title, text, source, tags, nid, created, modified, reminder, lastscheduled, position)
                values (?,?,?,?,?,datetime('now', 'localtime'),"",?,"", NULL)""", (title, text, source, tags, nid, reminder)).lastrowid
    conn.commit()
    conn.close()
    if queue_schedule != 0:
        update_priority_list(id, queue_schedule)
    index = get_index()
    if index is not None:
        index.add_user_note((id, title, text, source, tags, nid, ""))

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
    conn = _get_connection()
    res = conn.execute(f"select rowid from queue_prio_log where nid = {nid_to_update} order by created desc limit 1").fetchone()
    if res is None or len(res) == 0:
        created = _date_now_str()
        conn.execute(f"insert into queue_prio_log (nid, prio, type, created) values ({nid_to_update}, {new_prio}, '', '{created}')")
    else:
        conn.execute(f"update queue_prio_log set prio = {new_prio} where rowid = {res[0]}")
    conn.commit()
    conn.close()

def add_to_prio_log(nid: int, prio: int):
    created = _date_now_str()
    conn = _get_connection()
    conn.execute(f"insert into queue_prio_log (nid, prio, type, created) values ({nid}, {prio}, '', '{created}')")
    conn.commit()
    conn.close()

def update_priority_list(nid_to_update: int, schedule: int) -> Tuple[int, int]:
    """
    Call this after a note has been added or updated. 
    Will read the current priority queue and update it.
    Will also insert the given priority in queue_prio_log.
    """
    # priority log entries that have to be inserted in the log
    to_update_in_log = []
    # priority log entries that have to be removed from the log, because item is no longer in the queue
    to_remove_from_log = []
    # will contain the ids in priority order, highest first
    final_list = []
    index = -1
    
    current = _get_priority_list_with_last_prios()
    scores = []
    nid_was_included = False
    now = datetime.now()
    for nid, last_prio, last_prio_creation, current_position, rem in current:
        # last prio might be null, because of legacy queue system
        if last_prio is None:
            # lazy solution: set to average priority
            last_prio = 50
            now += timedelta(seconds=1)
            ds = now.strftime('%Y-%m-%d-%H-%M-%S')
            last_prio_creation = ds
            to_update_in_log.append((nid, ds, schedule))
            
        # assert(current_position >= 0)
        
        if nid == nid_to_update:
            nid_was_included = True
            # initial score is 0 (delta_days is 0), but the note will climb up the queue faster if it has a high prio
            score = 0
            if schedule == 0:
                # if not in queue, remove from log
                to_remove_from_log.append(nid)
            else:
                now += timedelta(seconds=1)
                ds = now.strftime('%Y-%m-%d-%H-%M-%S')
                if not nid in [x[0] for x in to_update_in_log]:
                    to_update_in_log.append((nid, ds, schedule))
                scores.append((nid, ds, last_prio, score, rem))
        else:
            days_delta = max(0, (datetime.now() - _dt_from_date_str(last_prio_creation)).total_seconds() / 86400.0)
            # assert(days_delta >= 0)
            # assert(days_delta < 10000)
            score = _calc_score(last_prio, days_delta)
            scores.append((nid, last_prio_creation, last_prio, score, rem))
    # note to be updated doesn't have to be in the results, it might not have been in the queue before
    if not nid_was_included:
        if schedule == 0:
            to_remove_from_log.append(nid_to_update)
        else:
            now += timedelta(seconds=1)
            ds = now.strftime('%Y-%m-%d-%H-%M-%S')
            reminder = get_reminder(nid_to_update)
            scores.append((nid_to_update, ds, schedule, 0, reminder))
            to_update_in_log.append((nid_to_update, ds, schedule))
    sorted_by_scores = sorted(scores, key=lambda x: x[3], reverse=True)
    final_list = [s for s in sorted_by_scores if s[4] is None or len(s[4].strip()) == 0 or not _specific_schedule_is_due_today(s[4])]
    due_today = [s for s in sorted_by_scores if s[4] is not None and len(s[4].strip()) > 0 and _specific_schedule_is_due_today(s[4])]
    if len(due_today) > 0:
        due_today = sorted(due_today, key=lambda x : x[3], reverse=True)
        final_list = due_today + final_list

    # now account for specific schedules
    
    
    # assert(len(scores) == 0 or len(final_list)  >0)
    # for s in scores:
    #     assert(s[3] >= 0)
    #     assert(s[1] is not None and len(s[1]) > 0)
    # assert(len(final_list) == len(set([f[0] for f in final_list])))
        
    # assert((len(to_update_in_log) + len(to_remove_from_log)) > 0)

    # update log and positions
    conn = _get_connection()
    conn.isolation_level = None
    c = conn.cursor()
    c.execute("begin transaction")
    c.execute(f"update notes set position = NULL where position is not NULL;")
    for ix, f in enumerate(final_list):
        c.execute(f"update notes set position = {ix} where id = {f[0]};")
        if f[0] == nid_to_update:
            index = ix
    for nid in to_remove_from_log:
        c.execute(f"delete from queue_prio_log where nid = {nid};")
        c.execute(f"update notes set reminder = '' where nid = {nid};")
    for nid, created, prio in to_update_in_log:
        c.execute(f"insert into queue_prio_log (nid, prio, created) values ({nid}, {prio}, '{created}');")
    c.execute("commit")
    conn.close()
    #return new position (0-based), and length of queue, some functions need that to update the ui
    return (index, len(final_list))
    

def _specific_schedule_is_due_today(sched_str: str) -> bool:
    if not "|" in sched_str:
        return False
    dt = _dt_from_date_str(sched_str.split("|")[1])
    if MISSED_NOTES_HANDLING != "place-front":
        return dt.date() == datetime.today().date()
    return dt.date() <= datetime.today().date()

def _specific_schedule_was_due_before_today(sched_str: str) -> bool:
    if not "|" in sched_str:
        return False
    dt = _dt_from_date_str(sched_str.split("|")[1])
    return dt.date() < datetime.today().date()
        
        

def _calc_score(priority: int, days_delta: float) -> float:
    prio_factor = 1 + ((priority - 1)/99) * (PRIORITY_SCALE_FACTOR - 1)
    return days_delta * prio_factor

def get_reminder(nid: int) -> str:
    conn = _get_connection()
    res = conn.execute(f"select reminder from notes where id = {nid} limit 1").fetchone()
    if res is None:
        return None
    conn.close()
    return res[0]

def get_priority(nid: int) -> int:
    conn = _get_connection()
    res = conn.execute(f"select prio from queue_prio_log where nid = {nid} order by created desc limit 1").fetchone()
    if res is None:
        return None
    conn.close()
    return res[0]

def get_priority_as_str(nid: int) -> str:
    """ Get a str representation of the priority of the given note, e.g. 'Very high' """
    conn = _get_connection()
    res = conn.execute(f"select prio from queue_prio_log where nid = {nid} order by created desc limit 1").fetchone()
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
    conn = _get_connection()
    sql = "update notes set reminder=?, modified=datetime('now', 'localtime') where id=? "
    conn.execute(sql, (rem, nid))
    conn.commit()
    conn.close()
        
def recalculate_priority_queue():
    """
        Calculate the priority queue again, without writing anything to the 
        priority log. Has to be done at least once on startup to incorporate the changed difference in days.
    """
    for i in range(0,2):
        current = _get_priority_list_with_last_prios()
        scores = []
        to_update_in_log = []
        to_remove_schedules = []
        to_reschedule = []
        now = datetime.now()
        for nid, last_prio, last_prio_creation, current_position, reminder in current:
            # last prio might be null, because of legacy queue system
            if last_prio is None:
                # lazy solution: set to average priority
                last_prio = 50
                now += timedelta(seconds=1)
                ds = now.strftime('%Y-%m-%d-%H-%M-%S')
                last_prio_creation = ds
                to_update_in_log.append((nid, ds, last_prio))
                
            # assert(current_position >= 0)
            days_delta = max(0, (datetime.now() - _dt_from_date_str(last_prio_creation)).total_seconds() / 86400.0)
            
            # assert(days_delta >= 0)
            # assert(days_delta < 10000)
            score = _calc_score(last_prio, days_delta)
            scores.append((nid, last_prio_creation, last_prio, score, reminder))
        sorted_by_scores = sorted(scores, key=lambda x: x[3], reverse=True)
        final_list = [s for s in sorted_by_scores if s[4] is None or len(s[4].strip()) == 0 or not _specific_schedule_is_due_today(s[4])]
        due_today = [s for s in sorted_by_scores if s[4] is not None and len(s[4].strip()) > 0 and _specific_schedule_is_due_today(s[4])]
        if len(due_today) > 0:
            due_today = sorted(due_today, key=lambda x : x[3], reverse=True)
            final_list = due_today + final_list
        
        if MISSED_NOTES_HANDLING != "place-front":
            for f in final_list:
                if f[4] is None or len(f[4].strip()) == 0:
                    continue
                if _specific_schedule_was_due_before_today(f[4]):
                    n = Note([None for i in range(12)])
                    n.reminder = f[4]
                    if MISSED_NOTES_HANDLING == "remove-schedule" and n.schedule_type() == "td":
                        to_remove_schedules.append(f[0])
                    elif MISSED_NOTES_HANDLING == "new-schedule" or (n.schedule_type() == "wd" or n.schedule_type() == "id"):
                        delta = n.due_days_delta()
                        now = _date_now_str()
                        if n.schedule_type() == "td":
                            # show again in n days
                            days_delta = int(n.reminder.split("|")[2][3:])
                            next_date_due = datetime.now() + timedelta(days=days_delta)
                            new_reminder = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|td:{days_delta}"

                        elif n.schedule_type() == "wd":
                            # show again on next weekday instance
                            wd_part = n.reminder.split("|")[2]
                            weekdays_due = [int(d) for d in wd_part[3:]]
                            next_date_due = utility.date.next_instance_of_weekdays(weekdays_due)
                            new_reminder = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|{wd_part}"
                        elif n.schedule_type() == "id":
                            # show again according to interval
                            days_delta = int(n.reminder.split("|")[2][3:])
                            next_date_due = datetime.now() + timedelta(days=days_delta)
                            new_reminder = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|id:{days_delta}"
                        to_reschedule.append((f[0], new_reminder))
        
        # assert(len(scores) == 0 or len(final_list)  >0)
        # for s in scores:
            # assert(s[3] >= 0)
            # assert(s[1] is not None and len(s[1]) > 0)
        # assert(len(final_list) == len(set([f[0] for f in final_list])))
        conn = _get_connection()
        c = conn.cursor()
        c.execute(f"update notes set position = NULL where position is not NULL;")
        for ix, f in enumerate(final_list):
            c.execute(f"update notes set position = {ix} where id = {f[0]};")
        for nid, created, prio in to_update_in_log:
            c.execute(f"insert into queue_prio_log (nid, prio, created) values ({nid}, {prio}, '{created}');")
        for nid in to_remove_schedules:
            c.execute(f"update notes set reminder = '' where id = {nid};")
        for nid, new_rem in to_reschedule:
            c.execute(f"update notes set reminder = '{new_rem}' where id = {nid};")
        conn.commit()
        conn.close()


def get_notes_scheduled_for_today() -> List[SiacNote]:
    today_dt = _date_now_str()[:4] + _date_now_str()[5:7] + _date_now_str()[8:10]
    conn = _get_connection()
    res = conn.execute(f"select * from notes where position is not null and reminder like '%|%' and cast((substr(reminder, 21, 4) || substr(reminder, 26,2) || substr(reminder, 29,2)) as integer) <= {today_dt}").fetchall()
    conn.close()
    return _to_notes(res)

def get_last_done_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select notes.* from (select distinct nid from queue_prio_log group by nid order by max(created) desc) as p join notes on p.nid = notes.id").fetchall()
    conn.close()
    return _to_notes(res)


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

def toggle_pdf_mark(nid: int, page: int, pages_total: int, mark_type: int) -> List[Tuple[Any]]:
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

def get_pdf_marks(nid: int) -> List[Tuple[Any]]:
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
    return _to_notes(res)

def get_read_pages(nid: int) -> List[int]:
    """ Get read pages for the given note as list. """
    conn = _get_connection()
    res = conn.execute("select page from read where nid = %s and page > -1 order by created asc" % nid).fetchall()
    conn.close()
    if res is None:
        return []
    return [r[0] for r in res]

def get_note_tree_data() -> Dict[str, List[Tuple[int, str]]]:
    """
        Fills a map with the data for the QTreeWidget in the Create dialog.
    """
    conn = _get_connection()
    last_created = conn.execute("select id, title, created from notes order by datetime(created, 'localtime') desc limit 500").fetchall()
    conn.close()
    n_map = {}
    now = datetime.now()
    seconds_since_midnight = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

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

def get_all_notes() -> List[Tuple[Any]]:
    """ Fetch all add-on notes, used in indexing. """
    conn = _get_connection()
    res = list(conn.execute("select * from notes"))
    conn.close()
    return res

def get_untagged_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = list(conn.execute("select * from notes where tags is null or trim(tags) = ''"))
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

    text = utility.text.clean_user_note_text(text)
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

def get_read_stats(nid: int):
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

def insert_highlights(highlights: List[Tuple[Any]]):
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

def get_highlights(nid: int, page: int) -> List[Tuple[Any]]:
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

def find_by_tag(tag_str, to_output_list=True):
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
            query = f"{query}lower(tags) like '% {t} %' or lower(tags) like '% {t}::%' or lower(tags) like '%::{t} %' or lower(tags) like '{t} %' or lower(tags) like '%::{t}::%'"
    conn = _get_connection()

    res = conn.execute("select * from notes %s order by id desc" %(query)).fetchall()
    if not to_output_list:
        return res
    return _to_notes(res, pinned)

def find_by_text(text: str):
    index = get_index()
    index.search(text, [])

def find_notes(text: str) -> List[SiacNote]:
    q = ""
    for token in text.lower().split():
        if len(token) > 1:
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
        if len(token) > 0:
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else "" 
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and lower(source) like '%.pdf' and (position is null or position < 0) order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def find_unqueued_non_pdf_notes(text: str) -> Optional[List[SiacNote]]:
    q = ""
    for token in text.lower().split():
        if len(token) > 0:
            q = f"{q} or lower(title) like '%{token}%'"

    q = q[4:] if len(q) > 0 else "" 
    if len(q) == 0:
        return
    conn = _get_connection()
    res = conn.execute(f"select * from notes where ({q}) and not lower(source) like '%.pdf' and (position is null or position < 0) order by id desc").fetchall()
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

def delete_note(id: int):
    update_priority_list(id, 0)
    # s = time.time() * 1000
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
    now = datetime.today().strftime('%Y-%m-%d')
    conn = _get_connection()
    c = conn.execute("select count(*) from read where page > -1 and created like '%s%%'" % now).fetchone()
    conn.close()
    if c is None:
        return 0
    return c[0]

def get_avg_pages_read(delta_days: int) -> float:
    dt = date.today() - timedelta(delta_days)
    stamp = dt.strftime('%Y-%m-%d')
    conn = _get_connection()
    c = conn.execute("select count(*) from read where page > -1 and created >= '%s'" % stamp).fetchone()
    conn.close()
    if c is None:
        return 0.0
    return float("{0:.1f}".format(c[0] / delta_days))


def get_queue_count() -> int:
    conn = _get_connection()
    c = conn.execute("select count(*) from notes where position is not null and position >= 0").fetchone()
    conn.close()
    return c

def get_invalid_pdfs() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf'").fetchall()
    conn.close()
    filtered = list()
    c = 0
    for (_, _, _, source, _, _, _, _, _, _, _) in res:
        if not utility.misc.file_exists(source.strip()):
            filtered.append(res[c])
        c += 1
    return _to_notes(filtered) 

def get_recently_used_tags() -> List[str]:
    """
        Returns a [str] of max 10 tags, ordered by their usage desc.
    """
    counts = _get_recently_used_tags_counts(30)
    ordered = [i[0] for i in list(sorted(counts.items(), key=lambda item: item[1], reverse = True))][:10]
    return ordered

def get_recently_used_tags_with_counts() -> Dict[str, int]:
    """
        Returns a {str, int} of max 10 tags, ordered by their usage desc.
    """
    counts = _get_recently_used_tags_counts(10)
    ordered = dict(sorted(counts.items(), key=lambda item: item[1], reverse = True))
    return ordered

def _get_recently_used_tags_counts(limit: int) -> Dict[str, int]:
    conn = _get_connection()
    res = conn.execute("select tags from notes where tags is not null order by id desc limit %s" % limit).fetchall()
    conn.close()
    if res is None or len(res) == 0:
        return dict()
    counts = dict()
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
    conn = _get_connection()
    res = conn.execute(sql).fetchall()
    conn.close()
    return _to_notes(res)

def _get_priority_list_with_last_prios() -> List[Tuple[Any]]:
    """
        Returns (nid, last prio, last prio creation, current position, schedule)
    """
    sql = """ select notes.id, prios.prio, prios.created, notes.position, notes.reminder from notes left join (select distinct nid, prio, max(created) as created, type from queue_prio_log group by nid) as prios on prios.nid = notes.id where notes.position >= 0 order by position asc """
    conn = _get_connection()
    res = conn.execute(sql).fetchall()
    conn.close()
    return res


def get_priority_list() -> List[SiacNote]:
    """
        Returns all notes that have a position set.
        Result is in the form that Output.print_search_results wants.
    """
    conn = _get_connection()
    sql = """
       select * from notes where position >= 0 order by position asc
    """
    res = conn.execute(sql).fetchall()
    conn.close()
    return _to_notes(res)

def get_newest(limit: int, pinned: List[int]) -> List[SiacNote]:
    """
        Returns newest user notes ordered by created date desc.
        Result is in the form that Output.print_search_results wants.
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
    conn.close

def empty_priority_list():
    conn = _get_connection()
    conn.execute("update notes set position = null")
    conn.commit()
    conn.close()

def get_all_tags_as_hierarchy(include_anki_tags: bool) -> Dict:
    tags = None
    if include_anki_tags:
        tags = mw.col.tags.all()
        user_note_tags = get_all_tags()
        tags.extend(user_note_tags)
    else:
        tags = get_all_tags()
    return utility.tags.to_tag_hierarchy(tags)


def get_all_pdf_notes() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf'").fetchall()
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


def get_pdf_notes_last_added_first() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_notes_last_read_first() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select notes.id,notes.title,notes.text,notes.source,notes.tags,notes.nid,notes.created,notes.modified,notes.reminder,notes.lastscheduled,notes.position from notes join read on notes.id == read.nid where lower(notes.source) like '%.pdf' group by notes.id order by max(read.created) desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_notes_not_in_queue() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where lower(source) like '%.pdf' and position is null order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_non_pdf_notes_not_in_queue() -> List[SiacNote]:
    conn = _get_connection()
    res = conn.execute("select * from notes where not lower(source) like '%.pdf' and position is null order by id desc").fetchall()
    conn.close()
    return _to_notes(res)

def get_pdf_quick_open_suggestions() -> List[SiacNote]:
    conn = _get_connection()
    last_added = conn.execute("select * from notes where lower(source) like '%.pdf' order by id desc limit 8").fetchall()
    last_read = conn.execute("select notes.id,notes.title,notes.text,notes.source,notes.tags,notes.nid,notes.created,notes.modified,notes.reminder,notes.lastscheduled,notes.position from notes join read on notes.id == read.nid where lower(notes.source) like '%.pdf' group by notes.id order by max(read.created) desc limit 8").fetchall()
    conn.close()
    res = []
    used = set()
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
    sql = "select nid, pagestotal, count(*), max(created) from read where nid in (%s) and page > -1 group by nid" % (",".join([str(n) for n in nids]))
    conn = _get_connection()
    res = conn.execute(sql).fetchall()
    conn.close()
    ilist = []
    for r in res:
        ilist.append([r[0], r[2], r[1]])
    return ilist

def get_related_notes(id: int) -> NoteRelations:
    note = get_note(id)
    title = note.title
    if title is not None and len(title.strip()) > 1:
        related_by_title = find_notes(title)
    else:
        related_by_title = []
    related_by_tags = []
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
        related_by_tags = _to_notes(related_by_tags)
        conn.close()
    return NoteRelations(related_by_title, related_by_tags)


def mark_all_pages_as_read(nid: int, num_pages: int):
    now = _date_now_str()
    conn = _get_connection()
    existing = [r[0] for r in conn.execute("select page from read where page > -1 and nid = %s" % nid).fetchall()]
    to_insert = [(p, nid, num_pages, now) for p in range(1, num_pages +1) if p not in existing]
    conn.executemany("insert into read (page, nid, pagestotal, created) values (?, ?, ?, ?)", to_insert)
    conn.commit()
    conn.close()

def mark_as_read_up_to(nid: int, page: int, num_pages: int):
    now = _date_now_str()
    conn = _get_connection()
    existing = [r[0] for r in conn.execute("select page from read where page > -1 and nid = %s" % nid).fetchall()]
    to_insert = [(p, nid, num_pages, now) for p in range(1, page +1) if p not in existing]
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
    file_path = mw.addonManager.getConfig(__name__)["addonNoteDBFolderPath"]
    if file_path is None or len(file_path) == 0:
        file_path = utility.misc.get_user_files_folder_path()
    file_path += "siac-notes.db"
    file_path.strip()
    db_path = file_path
    return file_path

def _to_notes(db_list: List[Tuple[Any]], pinned: List[int] = []) -> List[SiacNote]:
    notes = list()
    for tup in db_list:
        if not str([tup[0]]) in pinned:
            notes.append(SiacNote(tup))
    return notes

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

    