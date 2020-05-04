import typing
from typing import List
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

def date_today_stamp() -> str:
    return datetime.today().strftime('%Y-%m-%d-%H-%M-%S')

def date_now_stamp() -> str:
    return datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

def dt_to_stamp(dt : datetime) -> str:
    return dt.strftime('%Y-%m-%d-%H-%M-%S')