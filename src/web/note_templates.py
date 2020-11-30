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

"""
HTML templates for search results.
"""
from aqt import mw
from ..internals import HTML
from ..web.templating import filled_template
import state

config                          = mw.addonManager.getConfig(__name__)
PREVIEWER                       = """<div class='srchLbl' onclick='pycmd("siac-preview {nid}")'><i class="fa fa-id-card-o"></i></div>"""

try: 
    from aqt.previewer import BrowserPreviewer
except:
    PREVIEWER                   = ""

FLOAT_BTN               : HTML  = "<div class='floatLbl' onclick='addFloatingNote({nid})'>&#10063;</div>" if config["results.showFloatButton"] else ""
NID_BTN                 : HTML  = "<div class='floatLbl' onclick='pycmd(\"siac-copy-to-cb {nid}\")'>NID</div>" if config["results.showIDButton"] else ""
CID_BTN                 : HTML  = "<div class='floatLbl' onclick='pycmd(\"siac-copy-cid-to-cb {nid}\")'>CID</div>" if config["results.showCIDButton"] else ""

NOTE_TMPL               : HTML  = filled_template("notes/note_template", dict(previewer = PREVIEWER, float_btn = FLOAT_BTN, nid_btn = NID_BTN, cid_btn = CID_BTN))
NOTE_TMPL_SIMPLE        : HTML  = filled_template("notes/note_template_simple", {})
NOTE_TMPL_SIAC_SIMPLE   : HTML  = filled_template("notes/note_template_siac_simple", {})
NOTE_TMPL_SIAC          : HTML  = filled_template("notes/note_template_siac", dict(float_btn = FLOAT_BTN, nid_btn = NID_BTN))

