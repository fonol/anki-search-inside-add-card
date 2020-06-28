import typing
from typing import List, Optional
from datetime import datetime, timedelta
import calendar

def next_instance_of_weekdays(wd: List[int]) -> datetime:
    """
        Monday = 1, ...
        Today is excluded.
    """
    today = datetime.today()
    while True:
        today = today + timedelta(days=1)
        weekday = today.weekday() + 1
        if weekday in wd:
            return today
    
def weekday_name(wd: int) -> str:
    return list(calendar.day_name)[wd - 1]

def weekday_name_abbr(wd: int) -> str:
    return list(calendar.day_abbr)[wd - 1]

def date_today_stamp() -> str:
    return datetime.today().strftime('%Y-%m-%d-%H-%M-%S')

def date_only_stamp() -> str:
    return datetime.today().strftime('%Y-%m-%d')

def date_now_stamp() -> str:
    return datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

def date_x_days_ago_stamp(x: int) -> str:
    return (datetime.now() - timedelta(days=x)).strftime('%Y-%m-%d')

def dt_to_stamp(dt : datetime) -> str:
    return dt.strftime('%Y-%m-%d-%H-%M-%S')

def dt_from_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, '%Y-%m-%d-%H-%M-%S')

def date_is_today(date_str: str) -> bool:
    return datetime.today().date() == dt_from_stamp(date_str).date()

def get_last_schedule_date(schedule: str) -> Optional[datetime]:
    if len(schedule.split("|")[0]) == 0:
        return None
    return dt_from_stamp(schedule.split("|")[0])

def schedule_is_due_in_the_future(schedule: str) -> bool:
    if schedule is None or len(schedule) == 0 or not "|" in schedule:
        return False
    due         = schedule.split("|")[1]
    return due[:10] > date_only_stamp()
    

def schedule_verbose(sched: str) -> str:
    """ Returns a natural language representation of the given schedule string. """

    created     = sched.split("|")[0]
    due         = sched.split("|")[1]
    stype       = sched.split("|")[2][0:2]
    stype_val   = sched.split("|")[2][3:]

    if stype == "wd":
        days = ", ".join([weekday_name_abbr(int(c)) for c in stype_val])
        return f"This note is scheduled for every {days}."

    if stype == "id":
        if stype_val == "2":
            return f"This note is scheduled for every second day."
        if stype_val == "1":
            return f"This note is scheduled to appear everyday."
        return f"This note is scheduled to appear every {stype_val} days."

    if stype == "td":
        delta_days = (datetime.now().date() - dt_from_stamp(created).date()).days
        if delta_days == 0:
            return f"This note was scheduled today to appear in {stype_val} day(s)."
        if delta_days == 1:
            return f"This note was scheduled yesterday to appear in {stype_val} day(s)."
        return f"This note was scheduled {delta_days} days ago to appear in {stype_val} day(s)."


def get_new_reminder(stype: str, svalue: str) -> str:
    now = date_now_stamp()
    if stype == "td":
        # show again in n days
        next_date_due = datetime.now() + timedelta(days=int(svalue))
        return f"{now}|{dt_to_stamp(next_date_due)}|td:{svalue}"
    elif stype == "wd":
        # show again on next weekday instance
        weekdays_due = [int(d) for d in svalue]
        next_date_due = next_instance_of_weekdays(weekdays_due)
        return f"{now}|{dt_to_stamp(next_date_due)}|wd:{svalue}"
    elif stype == "id":
        # show again according to interval
        next_date_due = datetime.now() + timedelta(days=int(svalue))
        return f"{now}|{dt_to_stamp(next_date_due)}|id:{svalue}"
        

