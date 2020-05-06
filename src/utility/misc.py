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

import base64
import requests
import random
from glob import glob  
from datetime import datetime
import os
import time
from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip, showInfo
from urllib.parse import urlparse


def file_exists(full_path):
    if full_path is None or len(full_path) < 2:
        return False
    return os.path.isfile(full_path)

def base64_to_file(b64):
    """
        b64 : b64 str
        Save the image to a temp file in the user_files folder.
    """
    base_path = get_user_files_folder_path()
    # ugly
    fname = str(random.randint(10000000, 99999999))
    with open(base_path + fname + ".png", "wb") as f:
        f.write(base64.b64decode(b64))
    return base_path + fname + ".png"

    
def url_to_base64(url):
    return base64.b64encode(requests.get(url).content).decode('ascii')

def pdf_to_base64(path):
    with open(path, "rb") as pdf_file:
        encoded_string = base64.b64encode(pdf_file.read()).decode("ascii")
    return encoded_string

def count_cards_added_today():
    return len(mw.col.findCards("added:1"))

def is_dark_color(r,g,b):
    """
    Used for guessing if a dark theme (e.g. nightmode) is active.
    """
    return r*0.299 + g*0.587 + b*0.114 < 186 

def dark_mode_is_used(config):
    """
    Used for guessing if a dark theme (e.g. nightmode) is active.
    """
    

    colors = []
    colors.append(config["styling"]["modal"]["modalBackgroundColor"])
    colors.append(config["styling"]["general"]["noteBackgroundColor"])
    colors.append(config["styling"]["topBar"]["deckSelectBackgroundColor"])
    colors.append(config["styling"]["topBar"]["deckSelectButtonBackgroundColor"])
    dark_c = 0
    light_c = 0
    for c in colors:
        c = c.strip().lower()
        rgb = []
        if c.startswith("#"):
            rgb = hex_to_rgb(c) 
        elif c.startswith("rgb"): 
            rgb = [int(cs) for cs in c[3:-1].split(",")]
        if rgb != []:
            if is_dark_color(rgb[0], rgb[1], rgb[2]):
                dark_c += 1
            else:
                light_c += 1
        else:
            for w in ["dark", "grey", "gray", "black"]:
                if w in c:
                    dark_c += 1
                    break
            for w in ["white", "light"]:
                if w in c:
                    light_c += 1
                    break
    if dark_c > light_c:
        return True
    if light_c > dark_c:
        return False
    if light_c == 0 and dark_c == 0:
        return False
    return True


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

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

def marks_to_js_map(marks):
    """
        Takes a list of pdf page marks, returns a str representation of a js dict,
        that has pages as keys, and arrays of mark types as values.
    """
    d = dict()
    table = dict()
    for m in marks:
        if not m[0] in d:
            d[m[0]] = []
        if not m[4] in table:
            table[m[4]] = []
        d[m[0]].append(str(m[4]))
        table[m[4]].append(m[0])
    s = ""
    t = ""
    for k,v in d.items():
        s += ",%s:[%s]" % (k,",".join(v))
    for k,v in table.items():
        v.sort()
        t += ",%s:[%s]" % (k,",".join([str(page) for page in v]))
    s = s[1:] 
    s = "{%s}" % s
    t = t[1:] 
    t = "{%s}" % t
    return (s,t)
        


def get_milisec_stamp():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)

def get_user_files_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/user_files/"
    return dir + "user_files/"

def get_whoosh_index_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/index/"
    return dir + "index/"

def get_addon_base_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/"
    return dir

def get_web_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/web/"
    return dir + "web/"

def get_addon_id():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if dir.endswith("/"):
        dir = dir[:-1]
    return dir[dir.rfind("/")+1:]

def img_src(img_name):
    """
    Returns the src attribute for the image with the given name.
    Must be in web folder.
    """
    port = mw.mediaServer.getPort()
    return f"http://127.0.0.1:{port}/_addons/{get_addon_id()}/web/icons/{img_name}"

def img_src_base_path():
    port = mw.mediaServer.getPort()
    return f"http://127.0.0.1:{port}/_addons/{get_addon_id()}/web/icons/"

def url_to_pdf(url, output_path, cb_after_finish = None):
    """
        Save the given site as pdf. 
        output_path has to be the full path to the output file including name.
    """
    if url is None or len(url) == 0 or output_path is None or len(output_path) == 0:
        return
    valid = True
    try:
        x = urlparse(url)
        # path seems to be null on ubuntu for some reason
        valid = all([x.scheme, x.netloc])
    except:
        valid = False
    if not valid:
        tooltip("URL seems to be invalid", period=4000)
        return
    tooltip("Starting Conversion, this might take some seconds...",period=4000)
    temp = QWebEngineView()
    temp.setZoomFactor(1)
    if cb_after_finish is not None:
        temp.page().pdfPrintingFinished.connect(cb_after_finish)
    temp.load(QUrl(url))

    def save_pdf(finished):
        temp.page().printToPdf(output_path)

    temp.loadFinished.connect(save_pdf)

def get_pdf_save_full_path(path, pdfname):
    """
        path : folder where the pdf shall be saved to
        pdfname : name the pdf should be given
    """
    if path is None or len(path) == 0:
        return None
    c = 0
    if pdfname.lower().endswith(".pdf"):
        pdfname = pdfname[:-4]
    while os.path.isfile(os.path.join(path, pdfname + ".pdf")):
        pdfname += "-" + str(c) 
        c += 1 
    path = os.path.join(path, pdfname + ".pdf")
    return path

def find_pdf_files_in_dir(dir, cut_path=True):
    try:
        if not os.path.exists(dir):
            return []
        res = [f.path for f in os.scandir(dir) if f.name.endswith(".pdf")]
        if cut_path:
            res = [r[max(r.rfind("\\"),r.rfind("/"))+1:] for r in res]
        return res
    except Exception as e:
        print(e)
        return []

def find_pdf_files_in_dir_recursive(directory, cut_path=True):
    directory = directory.replace("\\", "/")
    if not directory.endswith("/"):
        directory += "/"

    if not os.path.exists(directory):
        return []
    def _find_rec(dir, cut_path):
        try:
            dir = dir.replace("\\", "/")
            if not dir.endswith("/"):
                dir += "/"
            res = [f.path for f in os.scandir(dir) if f.name.endswith(".pdf")]
            if cut_path:
                res = [r[max(r.rfind("\\"),r.rfind("/"))+1:] for r in res]
            sub_dirs = subdirs_fullpath(dir)
            for sub_dir in sub_dirs:
                res += _find_rec(sub_dir, cut_path)
            return res
        except Exception as e:
            print(e)
            return []

    result = _find_rec(directory, cut_path)

    return result

def subdirs_fullpath(path):
    return [entry.path for entry in os.scandir(path) if entry.is_dir()]

def _retToColor(retention):
    if retention < (100 / 7.0):
        return "#ff0000"
    if retention < (100 / 7.0) * 2:
        return "#ff4c00"
    if retention < (100 / 7.0) * 3:
        return "#ff9900"
    if retention < (100 / 7.0) * 4:
        return "#ffe500"
    if retention < (100 / 7.0) * 5:
        return "#cbff00"
    if retention < (100 / 7.0) * 6:
        return "#7fff00"
    return "#32ff00"


