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
import re
import sys
import time
import typing
import pathlib
import shutil
import importlib.util
from typing import Optional
from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip, showInfo
from urllib.parse import urlparse
from anki.utils import isMac, isLin


# region File / Folder Utils

def file_exists(full_path: str) -> bool:
    if full_path is None or len(full_path) < 2:
        return False
    full_path = re.sub("^.+:///", "", full_path)
    return os.path.isfile(full_path)

def create_folder_if_not_exists(path: str):

    if not os.path.isdir(path):
        os.mkdir(path)

def create_user_files_folder():
    """ Create the user_files folder in the add-on's folder if not existing. """
    folder = get_user_files_folder_path()
    if not os.path.isdir(folder):
        os.mkdir(folder)

def file_content(file_path: str) -> str:
    content = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except:
        return content
    return content


# endregion File / Folder Utils


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


def find_all_images(html):
    """
    Returns a list of all <img> tags contained in the html.
    """
    return re.findall("<img[^>]*?>", html, flags=re.IGNORECASE)

def try_inline_images(html: str, base_path: str) -> str:
    images_contained = find_all_images(html)
    if images_contained is None:
        return html
    for image_tag in images_contained:
        #ignore images already in base64
        if re.findall("src=['\"] *data:image/(png|jpe?g);[^;]{0,50};base64,", image_tag, flags=re.IGNORECASE):
            continue
        url = re.search("src=(\"[^\"]+\"|'[^']+')", image_tag, flags=re.IGNORECASE).group(1)[1:-1]
        try:
            if not url.startswith("http"):
                url = f"{base_path}{url}"
            base64 = url_to_base64(url)
            if base64 is None or len(base64) == 0:
                continue
            ending = ""
            if url.lower().endswith("jpg") or url.lower().endswith("jpeg"):
                ending = "jpeg"
            elif url.lower().endswith("png"):
                ending = "png"
            elif "jpg" in url.lower() or "jpeg" in url.lower():
                ending = "jpeg"
            elif "png" in url.lower():
                ending = "png"
            else:
                ending = "jpeg"
            html = html.replace(image_tag, "<img src=\"data:image/%s;base64,%s\">" % (ending,base64))
        except:
            continue

    return html

def url_to_base64(url):
    return base64.b64encode(requests.get(url).content).decode('ascii')

def pdf_to_base64(path):
    with open(path, "rb") as pdf_file:
        encoded_string = base64.b64encode(pdf_file.read()).decode("ascii")
    return encoded_string

def count_cards_added_today():
    if hasattr(mw.col, "find_cards"):
        return len(mw.col.find_cards("added:1"))
    return len(mw.col.findCards("added:1"))

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

def chromium_version() -> Optional[str]:
    try:
        user_agent      = QWebEngineProfile.defaultProfile().httpUserAgent()
        for t in user_agent.split():
            if t.startswith("Chrome/"):
                return t.split("/")[1]
    except:
        return None



def marks_to_js_map(marks):
    """
        Takes a list of pdf page marks, returns a str representation of a js dict,
        that has pages as keys, and arrays of mark types as values.
    """
    d       = dict()
    table   = dict()

    for m in marks:
        if not m[0] in d:
            d[m[0]] = []
        if not m[4] in table:
            table[m[4]] = []
        d[m[0]].append(str(m[4]))
        table[m[4]].append(m[0])

    s       = ""
    t       = ""

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

def get_milisec_stamp() -> int:
    """ UTC miliseconds. """
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)

# region Folder Paths

def get_user_files_folder_path():
    """ Path ends with / """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/user_files/"
    return dir + "user_files/"

def get_whoosh_index_folder_path():
    """ Path ends with / """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/index/"
    return dir + "index/"

def get_addon_base_folder_path():
    """ Path ends with / """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/"
    return dir

def get_web_folder_path():
    """ Path ends with / """
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/web/"
    return dir + "web/"

def get_rust_folder_path():
    dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/src/rs/siacrs/"
    return dir + "src/rs/siacrs/"

def get_application_data_path() -> str:
    """ Get a path to an application data folder for the current OS. """
    try:
        home = pathlib.Path.home()
        path = ""
        if sys.platform == "win32":
            path = f"{home}/AppData/Local/"
        elif sys.platform.startswith("linux"):
            # path = "/usr/local/share"
            # if not os.path.isdir(path)
            path =  f"{home}/.local/share/"
            if not os.path.isdir(path) or not os.access(path, os.W_OK):
                path = f"{home}/usr/share/"
        elif sys.platform == "darwin":
            path = f"{home}/Library/Application Support/"
            if not os.path.isdir(path) or not os.access(path, os.W_OK):
                path = os.getenv("HOME")
        if not path:
            return get_user_files_folder_path()
        if not path.endswith("/"):
            path += "/"
        return path.replace("\\", "/") + ".anki-siac-addon-data/"
    except:
        # if all fails, use the user_files folder
        return get_user_files_folder_path()

# endregion Folder Paths

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

def qlabel_image(icon_name, w, h):
    """ Return a QLabel with the given icon as pixmap. """
    lbl     = QLabel()
    pixmap  = QPixmap(get_web_folder_path() + f"icons/{icon_name}").scaled(QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    lbl.setPixmap(pixmap)
    return lbl

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
        printer = QPrinter()
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
        printer.setPageSize(QPrinter.A3)
        printer.setPageOrientation(QPageLayout.Portrait)
        temp.page().printToPdf(output_path, printer.pageLayout())

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
    except Exception:
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
        except Exception:
            return []

    result = _find_rec(directory, cut_path)

    return result

def load_rust_lib():
    """ Attempt to load the Rust library which should be in the addon data folder. """

    if isLin:
        # no built lib for linux yet
        return
    lib  = "siacrs.so" if isMac else "siacrs.pyd"
    path = get_application_data_path()
    if not os.path.isdir(path):
        os.mkdir(path)
    rs_file = os.path.join(get_rust_folder_path(), lib)
    # if the lib is not there yet, copy it from the add-on folder to the add-on data folder
    if not os.path.isfile(os.path.join(path, lib)):
        shutil.copyfile(rs_file, os.path.join(path, lib))

    spec = importlib.util.spec_from_file_location("siacrs", os.path.join(path, lib))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

def subdirs_fullpath(path):
    return [entry.path for entry in os.scandir(path) if entry.is_dir()]

def to_day_ivl(ivl):
    if ivl < 0:
        return abs(ivl) / (24 * 60 * 60)
    return ivl

# region Color Utils

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def color_to_hex(cs):
    cs = cs.strip()
    if cs.startswith("#"):
        return cs
    if cs.lower().startswith("rgb"):
        r = int(cs[4:-1].split(",")[0])
        g = int(cs[4:-1].split(",")[1])
        b = int(cs[4:-1].split(",")[2])
        return rgb_to_hex(r, g, b)
    return color_name_to_hex(cs)

def is_dark_color(r,g,b):
    """
    Used for guessing if a dark theme (e.g. nightmode) is active.
    """
    return r*0.299 + g*0.587 + b*0.114 < 186

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

def color_name_to_hex(cs):

    colors = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370d8",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#d87093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32"
    }
    if not cs.lower() in colors:
        return None
    return colors[cs.lower()]

def prio_color(prio):
        if prio > 90:
            return "#7c0101"
        if prio > 80:
            return "#761900"
        if prio > 70:
            return "#6e2600"
        if prio > 60:
            return "#653000"
        if prio > 50:
            return "#5b3800"
        if prio > 40:
            return "#503f00"
        if prio > 30:
            return "#444400"
        if prio > 20:
            return "#374900"
        if prio > 10:
            return "#294d00"
        return "#155001"


# endregion Color Utils
