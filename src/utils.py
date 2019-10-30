import base64
import requests
import random
import os, sys
from aqt import mw
from .state import get_index


def to_tag_hierarchy(tags):
    tmap = {}
    for t in sorted(tags, key=lambda t: t.lower()):
        tmap = _add_to_tag_list(tmap, t)
    tmap = dict(sorted(tmap.items(), key=lambda item: item[0].lower()))
    return tmap


def iterateTagmap(tmap, prefix):
    if len(tmap) == 0:
        return []
    res = []
    if prefix:
        prefix = prefix + "::"
    for key, value in tmap.items():
        if type(value) is dict:
            if len(value) > 0:
                res.append(prefix + key)
                res +=  iterateTagmap(value, prefix + key)
            else:
                res.append(prefix + key)
    return res


def _add_to_tag_list(tmap, name):
    """
    Helper function to build the tag hierarchy.
    """
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = tmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}}) 
    return tmap

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

def is_dark_color(r,g,b):
    """
    Used for guessing if a dark theme (e.g. nightmode) is active.
    """
    return r*0.299 + g*0.587 + b*0.114 < 186 

def dark_mode_is_used():
    """
    Used for guessing if a dark theme (e.g. nightmode) is active.
    """
    
    config = mw.addonManager.getConfig(__name__)

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


def get_user_files_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/user_files/"
    return dir + "user_files/"

def get_whoosh_index_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/index/"
    return dir + "index/"

def get_addon_base_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/"
    return dir

def get_web_folder_path():
    """
    Path ends with /
    """
    dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__))).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/web/"
    return dir + "web/"