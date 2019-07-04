import datetime
import time
from aqt import mw

def get_notes_added_on_day_of_year(day_of_year : int, limit: int):
    
    day_now = datetime.datetime.now().timetuple().tm_yday
    # nid_now = int(time.time()* 1000)
    # nid_then = nid_now - (day_now - day_of_year) * (24 * 60 * 60 * 1000)
    date_now = datetime.datetime.utcnow() 
    date_year_begin = datetime.datetime(year=date_now.year, month=1, day=1, hour=0 ,minute=0)    
    date_then = date_year_begin + datetime.timedelta(day_of_year)
    nid_midnight = int(date_then.timestamp() * 1000)
    nid_next_midnight = nid_midnight + 24 * 60 * 60 * 1000
    res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc" % (nid_midnight, nid_next_midnight)).fetchall()
    return to_print_list(res)


def get_cal_info_context(day_of_year : int):
    date_now = datetime.datetime.utcnow() 
    oneday = 24 * 60 * 60 * 1000
    date_year_begin = datetime.datetime(year=date_now.year, month=1, day=1, hour=0 ,minute=0)    
    date_then = date_year_begin + datetime.timedelta(day_of_year)
    nid_midnight = int(date_then.timestamp() * 1000)
    date_then_str = time.strftime('%a, %d %B, %Y', time.localtime((nid_midnight + 1000) / 1000))
    nid_midnight_three_days_before = nid_midnight - 3 * oneday
    nid_midnight_three_days_after = nid_midnight + 4 * oneday
    res = mw.col.db.execute("select distinct notes.id from notes where id > %s and id < %s order by id asc" % (nid_midnight_three_days_before, nid_midnight_three_days_after)).fetchall()
    context = [0, 0, 0, 0, 0, 0, 0]
    for nid in res:
        context[int((nid[0] - nid_midnight_three_days_before) / oneday)] += 1
    html_content = ""
    for i, cnt in enumerate(context):
        if cnt > 20:
            color = "cal-three"
        elif cnt > 10:
            color = "cal-two"
        elif cnt > 0:
            color = "cal-one"
        else: 
            color = ""
        html_content += """<div class='cal-block-week %s %s' data-index='%s' onclick='pycmd("calInfo %s")'>%s</div>""" % (color, "cal-lg" if i == 3 else "", day_of_year - (3 - i),day_of_year - (3 - i), cnt)
    html = """
    
    <div style='text-align: center; margin-bottom: 4px;'>
        <span>%s</span> 
    </div>
    <div style='width: 100%%; text-align: center;'>%s</div>""" % (date_then_str, html_content)    


    return html


def to_print_list(db_list):
    rList = []
    for r in db_list:
        rList.append((r[1], r[2], r[3], r[0]))
    return rList