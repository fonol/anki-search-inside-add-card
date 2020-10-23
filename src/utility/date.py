import typing
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import calendar
import locale

def next_instance_of_weekdays(wd: List[int], start: datetime=None) -> datetime:
    """
        Monday = 1, ...
        Today is excluded.
    """
    if start is None: 
        c = datetime.today()
    else: 
        c = start
    while True:
        c = c + timedelta(days=1)
        weekday = c.weekday() + 1
        if weekday in wd:
            return c
    
def weekday_name(wd: int) -> str:
    return list(calendar.day_name)[wd - 1]

def weekday_name_abbr(wd: int) -> str:
    return list(calendar.day_abbr)[wd - 1]

def weekday_name_from_dt(dt: datetime) -> str:
    # return calendar.day_name[dt.weekday()]
    locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
    return dt.strftime("%A")

def counts_to_timestamps(counts: Dict[str, int]) -> Dict[int, int]:
    out = {}
    for k,v in counts.items():
        out[str(int(datetime.timestamp(dt_from_date_only_stamp(k))))] = v
    return out

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

def dt_from_date_only_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, '%Y-%m-%d')

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
    
def day_of_year() -> int:
    now = datetime.now()
    return (now - datetime(now.year, 1, 1)).days + 1

def postpone_reminder(reminder: str, days_delta: int) -> str:
    new_due = dt_to_stamp(datetime.now() + timedelta(days=days_delta))
    return date_now_stamp() + "|" + new_due + "|" + reminder.split("|")[2]

def next_instance_of_schedule_verbose(sched: str) -> str:

    if sched is None or not "|" in sched:
        return "-"
    due         = sched.split("|")[1]
    due_dt      = dt_from_stamp(due)
    dd          = (datetime.now().date() - due_dt.date()).days 
    if dd == 0:
        return "Today"
    if dd == 1:
        return "Yesterday"
    if dd > 1:
        return f"{abs(dd)} days ago"
    if dd == -1:
        return "Tomorrow"
    if dd < -1:
        return f"In {abs(dd)} days"


def schedule_verbose(sched: str) -> str:
    """ Returns a natural language representation of the given schedule string. """

    created     = sched.split("|")[0]
    due         = sched.split("|")[1]
    stype       = sched.split("|")[2][0:2]
    stype_val   = sched.split("|")[2][3:]

    # weekdays
    if stype == "wd":
        days = ", ".join([weekday_name_abbr(int(c)) for c in stype_val])
        return f"Scheduled for every {days}."

    # every nth day
    if stype == "id":
        if stype_val == "2":
            return f"Scheduled for every second day."
        if stype_val == "1":
            return f"Scheduled to appear everyday."
        return f"Scheduled to appear every {stype_val} days."

    # once, in n days
    if stype == "td":
        delta_days = (datetime.now().date() - dt_from_stamp(created).date()).days
        if delta_days == 0:
            if stype_val == "1":
                return f"Scheduled today to appear tomorrow."
            else:
                return f"Scheduled today to appear in {stype_val} day(s)."
        if delta_days == 1:
            if stype_val == "1":
                return f"Scheduled yesterday to appear today."
            elif stype_val == 2:
                return f"Scheduled yesterday to appear tomorrow."
            else:
                return f"Scheduled yesterday to appear in {stype_val} day(s)."
        return f"Scheduled {delta_days} days ago to appear in {stype_val} day(s)."
    
    # growing ivl
    if stype == "gd":
        factor = stype_val.split(";")[0]
        return f"Scheduled with growing interval (factor {round(float(factor), 1)})"


def get_new_reminder(stype: str, svalue: str) -> str:
    """ Returns a new reminder with an updated due date, created date and values. """
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
    elif stype == "gd":
        # show again according to interval * factor
        factor = float(svalue.split(";")[0])
        last   = float(svalue.split(";")[1])
        new    = factor * last
        next_date_due = datetime.now() + timedelta(days=int(new))
        return f"{now}|{dt_to_stamp(next_date_due)}|gd:{factor};{new}"
        
def get_next_reminder(sched: str) -> datetime:
    """ Gets the next reminder after the given reminder. Difference to get_new_reminder: 
        This takes the current due date of the given reminder as basis, and not the actual date today. 
        So this will always return a changed reminder.
     """

    now         = date_now_stamp()
    due         = sched.split("|")[1]
    due_dt      = dt_from_stamp(due)
    stype       = sched.split("|")[2][0:2]
    svalue      = sched.split("|")[2][3:]

    if stype == "wd":
        # show again on next weekday instance
        weekdays_due = [int(d) for d in svalue]
        next_date_due = next_instance_of_weekdays(weekdays_due, start= due_dt)
        return f"{now}|{dt_to_stamp(next_date_due)}|wd:{svalue}"
    elif stype == "id":
        # show again according to interval
        next_date_due = due_dt + timedelta(days=int(svalue))
        return f"{now}|{dt_to_stamp(next_date_due)}|id:{svalue}"
    elif stype == "gd":
        # show again according to interval * factor
        factor = float(svalue.split(";")[0])
        last   = float(svalue.split(";")[1])
        new    = factor * last
        next_date_due = due_dt + timedelta(days=int(new))
        return f"{now}|{dt_to_stamp(next_date_due)}|gd:{factor};{new}"


def date_diff_to_string(diff):
    """
    Takes a datetime obj representing a difference between two dates, returns e.g.
    "5 minutes", "6 hours", ...
    """
    time_str = "%s %s"

    if diff.total_seconds() / 60 < 2.0:
        time_str = time_str % ("1", "minute")
    elif diff.total_seconds() / 3600 < 1.0:
        time_str = time_str % (int(diff.total_seconds() / 60), "minutes")
    elif diff.total_seconds() / 86400 < 1.0:
        if int(diff.total_seconds() / 3600) == 1:
            time_str = time_str % (int(diff.total_seconds() / 3600), "hour")
        else:
            time_str = time_str % (int(diff.total_seconds() / 3600), "hours")
    elif diff.total_seconds() / 86400 >= 1.0 and diff.total_seconds() / 86400 < 2.0:
        time_str = time_str % ("1", "day")
    else:
        time_str = time_str % (int(diff.total_seconds() / 86400), "days")
    return time_str