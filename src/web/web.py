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


import platform
import os
import json
import re
import datetime
import time
import sys
import aqt
import typing
from typing import List, Tuple
from aqt import mw
from aqt.editor import Editor

import utility.tags
import utility.text
import utility.misc
import state


from ..tag_find import get_most_active_tags
from ..state import get_index, check_index, set_deck_map
from ..notes import get_note, _get_priority_list, get_all_tags, get_read_pages, get_pdf_marks, insert_pages_total, get_read_today_count
from .html import *
from ..internals import js, requires_index_loaded, perf_time
from ..config import get_config_value_or_default

@js
def toggleAddon():
    return "toggleAddon();"


def getScriptPlatformSpecific():
    """
        Returns the css and js used by the add-on in <style>/<script> tags.
        Some placeholders in the scripts.js file and in the styles.css file are replaced
        by config values.

        They could be exposed on the internal web server, but as they contain placeholders for config-defined styles,
        it is easier for now that way.
    """

    icon_vars = """
    :root {
        --c-search-icn: url("data:image/svg+xml,%3Csvg width='12' height='12' xmlns='http://www.w3.org/2000/svg'%3E%3Cg%3E%3Crect fill='none' id='canvas_background' height='14' width='14' y='-1' x='-1'/%3E%3Cg display='none' overflow='visible' y='0' x='0' height='100%25' width='100%25' id='canvasGrid'%3E%3Crect fill='url(%23gridpattern)' stroke-width='0' y='0' x='0' height='100%25' width='100%25'/%3E%3C/g%3E%3C/g%3E%3Cg%3E%3Cellipse stroke='black' ry='2.301459' rx='2.317666' id='svg_10' cy='4.004963' cx='4.055105' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3Cline stroke='black' stroke-linecap='null' stroke-linejoin='null' id='svg_11' y2='9.969307' x2='10.003241' y1='5.722954' x1='5.497568' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3C/g%3E%3C/svg%3E");
        --c-trash-icn: url("data:image/svg+xml,%3Csvg width='12' height='12' xmlns='http://www.w3.org/2000/svg'%3E%3Cg%3E%3Crect fill='none' id='canvas_background' height='14' width='14' y='-1' x='-1'/%3E%3Cg display='none' overflow='visible' y='0' x='0' height='100%25' width='100%25' id='canvasGrid'%3E%3Crect fill='url(%23gridpattern)' stroke-width='0' y='0' x='0' height='100%25' width='100%25'/%3E%3C/g%3E%3C/g%3E%3Cg%3E%3Cpath stroke='black' transform='rotate(179.51019287109375 6.166921615600586,6.9911985397338885) ' id='svg_4' d='m2.799955,10.675048l1.262613,-7.3677l4.208709,0l1.262612,7.3677l-6.733934,0z' fill-opacity='null' stroke-opacity='null' stroke-width='1.5' fill='none'/%3E%3Crect stroke='black' id='svg_7' height='0.638096' width='1.884984' y='0.823103' x='5.256614' fill-opacity='null' stroke-opacity='null' stroke-width='0.7' fill='none'/%3E%3Cline stroke='black' transform='rotate(2.7647311687469482 6.056345462799075,1.717745661735527) ' stroke-linecap='null' stroke-linejoin='null' id='svg_9' y2='1.451854' x2='10.882708' y1='1.983638' x1='1.229983' fill-opacity='null' stroke-opacity='null' fill='none'/%3E%3C/g%3E%3C/svg%3E");
        --c-pdf-icn: url("data:image/svg+xml,%3Csvg version='1.0' xmlns='http://www.w3.org/2000/svg' width='17px' height='17px' viewBox='0 0 225.000000 225.000000' preserveAspectRatio='xMidYMid meet'%3E%3Cg transform='translate(0.000000,225.000000) scale(0.100000,-0.100000)'%0Afill='black' stroke='none'%3E%3Cpath d='M690 2099 c-29 -12 -67 -45 -83 -74 -8 -14 -14 -134 -17 -380 l-5%0A-360 -120 -5 c-107 -4 -125 -8 -166 -32 -59 -35 -96 -90 -110 -163 -14 -76 -7%0A-389 10 -430 15 -37 75 -101 116 -123 21 -12 65 -18 150 -22 l120 -5 5 -125%0Ac3 -69 11 -136 17 -150 14 -32 51 -66 86 -79 19 -7 231 -11 639 -11 l610 0 40%0A22 c21 12 49 38 61 58 l22 35 0 695 c0 578 -2 699 -14 720 -29 50 -363 409%0A-396 424 -29 14 -92 16 -487 15 -276 0 -463 -4 -478 -10z m890 -268 c0 -226%0A-15 -210 205 -213 l170 -3 3 -664 c2 -607 1 -666 -14 -683 -16 -17 -48 -18%0A-619 -18 -548 0 -604 1 -616 17 -19 22 -26 208 -9 228 11 13 76 15 434 15%0Al422 0 53 26 c64 32 105 86 120 155 16 73 13 385 -3 432 -22 59 -64 107 -120%0A133 l-51 24 -421 0 c-349 0 -424 2 -433 14 -18 22 -11 667 8 689 12 15 56 17%0A442 17 l429 0 0 -169z m-906 -765 c51 -21 76 -60 76 -118 0 -43 -5 -55 -33%0A-83 -19 -19 -46 -36 -60 -39 -15 -3 -38 -8 -52 -11 -23 -5 -25 -10 -25 -64 0%0A-53 -2 -59 -23 -65 -12 -3 -33 -3 -45 1 -22 5 -22 8 -22 192 0 103 3 191 7%0A194 12 13 143 7 177 -7z m400 -15 c96 -60 102 -247 11 -319 -55 -43 -198 -67%0A-246 -42 -18 10 -19 23 -19 188 0 129 3 182 13 191 9 9 39 12 107 9 79 -3 102%0A-8 134 -27z m366 14 c7 -8 10 -25 6 -39 -5 -22 -12 -25 -64 -28 l-57 -3 0 -35%0A0 -35 52 -3 c47 -3 54 -6 59 -27 11 -43 -1 -54 -58 -57 l-53 -3 -3 -72 c-3%0A-64 -5 -72 -25 -77 -13 -3 -33 -3 -45 1 -22 5 -22 8 -22 193 0 141 3 190 13%0A193 6 3 51 6 98 6 65 1 90 -3 99 -14z'/%3E%3Cpath d='M928 994 c-5 -4 -8 -56 -8 -116 l0 -108 36 0 c26 0 43 8 66 30 28 29%0A30 35 26 91 -3 42 -10 66 -24 80 -21 21 -84 36 -96 23z'/%3E%3C/g%3E%3C/svg%3E%0A");

        --c-search-icn-night: url("data:image/svg+xml,%3Csvg width='12' height='12' xmlns='http://www.w3.org/2000/svg'%3E%3Cg%3E%3Crect fill='none' id='canvas_background' height='14' width='14' y='-1' x='-1'/%3E%3Cg display='none' overflow='visible' y='0' x='0' height='100%25' width='100%25' id='canvasGrid'%3E%3Crect fill='url(%23gridpattern)' stroke-width='0' y='0' x='0' height='100%25' width='100%25'/%3E%3C/g%3E%3C/g%3E%3Cg%3E%3Cellipse stroke='white' ry='2.301459' rx='2.317666' id='svg_10' cy='4.004963' cx='4.055105' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3Cline stroke='white' stroke-linecap='null' stroke-linejoin='null' id='svg_11' y2='9.969307' x2='10.003241' y1='5.722954' x1='5.497568' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3C/g%3E%3C/svg%3E");
        --c-trash-icn-night: url("data:image/svg+xml,%3Csvg width='12' height='12' xmlns='http://www.w3.org/2000/svg'%3E%3Cg%3E%3Crect fill='none' id='canvas_background' height='14' width='14' y='-1' x='-1'/%3E%3Cg display='none' overflow='visible' y='0' x='0' height='100%25' width='100%25' id='canvasGrid'%3E%3Crect fill='url(%23gridpattern)' stroke-width='0' y='0' x='0' height='100%25' width='100%25'/%3E%3C/g%3E%3C/g%3E%3Cg%3E%3Cpath stroke='white' transform='rotate(179.51019287109375 6.166921615600586,6.9911985397338885) ' id='svg_4' d='m2.799955,10.675048l1.262613,-7.3677l4.208709,0l1.262612,7.3677l-6.733934,0z' fill-opacity='null' stroke-opacity='null' stroke-width='1.5' fill='none'/%3E%3Crect stroke='white' id='svg_7' height='0.638096' width='1.884984' y='0.823103' x='5.256614' fill-opacity='null' stroke-opacity='null' stroke-width='0.7' fill='none'/%3E%3Cline stroke='black' transform='rotate(2.7647311687469482 6.056345462799075,1.717745661735527) ' stroke-linecap='null' stroke-linejoin='null' id='svg_9' y2='1.451854' x2='10.882708' y1='1.983638' x1='1.229983' fill-opacity='null' stroke-opacity='null' fill='none'/%3E%3C/g%3E%3C/svg%3E");
        --c-pdf-icn-night: url("data:image/svg+xml,%3Csvg version='1.0' xmlns='http://www.w3.org/2000/svg' width='17px' height='17px' viewBox='0 0 225.000000 225.000000' preserveAspectRatio='xMidYMid meet'%3E%3Cg transform='translate(0.000000,225.000000) scale(0.100000,-0.100000)'%0Afill='white' stroke='none'%3E%3Cpath d='M690 2099 c-29 -12 -67 -45 -83 -74 -8 -14 -14 -134 -17 -380 l-5%0A-360 -120 -5 c-107 -4 -125 -8 -166 -32 -59 -35 -96 -90 -110 -163 -14 -76 -7%0A-389 10 -430 15 -37 75 -101 116 -123 21 -12 65 -18 150 -22 l120 -5 5 -125%0Ac3 -69 11 -136 17 -150 14 -32 51 -66 86 -79 19 -7 231 -11 639 -11 l610 0 40%0A22 c21 12 49 38 61 58 l22 35 0 695 c0 578 -2 699 -14 720 -29 50 -363 409%0A-396 424 -29 14 -92 16 -487 15 -276 0 -463 -4 -478 -10z m890 -268 c0 -226%0A-15 -210 205 -213 l170 -3 3 -664 c2 -607 1 -666 -14 -683 -16 -17 -48 -18%0A-619 -18 -548 0 -604 1 -616 17 -19 22 -26 208 -9 228 11 13 76 15 434 15%0Al422 0 53 26 c64 32 105 86 120 155 16 73 13 385 -3 432 -22 59 -64 107 -120%0A133 l-51 24 -421 0 c-349 0 -424 2 -433 14 -18 22 -11 667 8 689 12 15 56 17%0A442 17 l429 0 0 -169z m-906 -765 c51 -21 76 -60 76 -118 0 -43 -5 -55 -33%0A-83 -19 -19 -46 -36 -60 -39 -15 -3 -38 -8 -52 -11 -23 -5 -25 -10 -25 -64 0%0A-53 -2 -59 -23 -65 -12 -3 -33 -3 -45 1 -22 5 -22 8 -22 192 0 103 3 191 7%0A194 12 13 143 7 177 -7z m400 -15 c96 -60 102 -247 11 -319 -55 -43 -198 -67%0A-246 -42 -18 10 -19 23 -19 188 0 129 3 182 13 191 9 9 39 12 107 9 79 -3 102%0A-8 134 -27z m366 14 c7 -8 10 -25 6 -39 -5 -22 -12 -25 -64 -28 l-57 -3 0 -35%0A0 -35 52 -3 c47 -3 54 -6 59 -27 11 -43 -1 -54 -58 -57 l-53 -3 -3 -72 c-3%0A-64 -5 -72 -25 -77 -13 -3 -33 -3 -45 1 -22 5 -22 8 -22 193 0 141 3 190 13%0A193 6 3 51 6 98 6 65 1 90 -3 99 -14z'/%3E%3Cpath d='M928 994 c-5 -4 -8 -56 -8 -116 l0 -108 36 0 c26 0 43 8 66 30 28 29%0A30 35 26 91 -3 42 -10 66 -24 80 -21 21 -84 36 -96 23z'/%3E%3C/g%3E%3C/svg%3E%0A");
    }
    """.replace("%", "%%")

    addon_id    = utility.misc.get_addon_id()

    # css + js
    all = """
    <style>
        %s
    </style>
    <style id='siac-styles'>
        %s
    </style>

    <script type='text/javascript'>
        window.renderImmediately = %s;
        window.ADDON_ID = '%s';
    </script>
    """
    css                 = styles()
    render_immediately  = str(get_config_value_or_default("renderImmediately", False)).lower()

    return all % (icon_vars, css, render_immediately, addon_id)

def styles() -> str:
    """ Returns the content of styles.css with all config values inserted. """

    dir         = utility.misc.get_web_folder_path()
    addon_id    = utility.misc.get_addon_id()
    port        = mw.mediaServer.getPort()

    with open(dir + "styles.variables.css") as f:
        css = f.read().replace("%", "%%")

    imgMaxHeight        = str(get_config_value_or_default("imageMaxHeight", 300))
    pdfTooltipMaxHeight = str(get_config_value_or_default("pdfTooltipMaxHeight", 300))
    pdfTooltipMaxWidth  = str(get_config_value_or_default("pdfTooltipMaxWidth", 250))
    tagFG               = str(get_config_value_or_default("styles.tagForegroundColor", "black"))
    tagBG               = str(get_config_value_or_default("styles.tagBackgroundColor", "#f0506e"))
    tagNightFG          = str(get_config_value_or_default("styles.night.tagForegroundColor", "black"))
    tagNightBG          = str(get_config_value_or_default("styles.night.tagBackgroundColor", "DarkOrange"))

    highlightFG         = str(get_config_value_or_default("styles.highlightForegroundColor", "black"))
    highlightBG         = str(get_config_value_or_default("styles.highlightBackgroundColor", "yellow"))
    highlightNightFG    = str(get_config_value_or_default("styles.night.highlightForegroundColor", "black"))
    highlightNightBG    = str(get_config_value_or_default("styles.night.highlightBackgroundColor", "SpringGreen"))

    suspFG              = str(get_config_value_or_default("styles.suspendedForegroundColor", "black"))
    suspBG              = str(get_config_value_or_default("styles.suspendedBackgroundColor", "coral"))

    modalBorder         = str(get_config_value_or_default("styles.modalBorderColor", "#2496dc"))
    modalBorderNight    = str(get_config_value_or_default("styles.night.modalBorderColor", "darkorange"))
    readingModalBG      = str(get_config_value_or_default("styles.readingModalBackgroundColor", "#2f2f31"))
    rm_btn_border       = str(get_config_value_or_default("styles.readingModalButtonBorderColor", "#b2b2a0"))
    rm_filter           = str(get_config_value_or_default("styles.readingModalFilter", "none"))

    rm_texture          = str(get_config_value_or_default("styles.readingModalTexture", "none"))
    url                 = f"http://127.0.0.1:{port}/_addons/{addon_id}/web/icons/"
    if re.match("url\(.+\)", rm_texture):
        rm_texture      = rm_texture.replace("url('", "url('" + url)
    rm_bg_size          = str(get_config_value_or_default("styles.readingModalBackgroundSize", "80"))

    css                 = css.replace("$imgMaxHeight$", imgMaxHeight)
    css                 = css.replace("$pdfTooltipMaxHeight$", pdfTooltipMaxHeight)
    css                 = css.replace("$pdfTooltipMaxWidth$", pdfTooltipMaxWidth)

    css                 = css.replace("$styles.suspendedForegroundColor$", suspFG)
    css                 = css.replace("$styles.suspendedBackgroundColor$", suspBG)
    css                 = css.replace("$styles.tagForegroundColor$", tagFG)
    css                 = css.replace("$styles.tagBackgroundColor$", tagBG)
    css                 = css.replace("$styles.night.tagForegroundColor$", tagNightFG)
    css                 = css.replace("$styles.night.tagBackgroundColor$", tagNightBG)
    css                 = css.replace("$styles.highlightForegroundColor$", highlightFG)
    css                 = css.replace("$styles.highlightBackgroundColor$", highlightBG)
    css                 = css.replace("$styles.night.highlightForegroundColor$", highlightNightFG)
    css                 = css.replace("$styles.night.highlightBackgroundColor$", highlightNightBG)
    css                 = css.replace("$styles.modalBorderColor$", modalBorder)
    css                 = css.replace("$styles.night.modalBorderColor$", modalBorderNight)
    css                 = css.replace("$styles.readingModalBackgroundColor$", readingModalBG)
    css                 = css.replace("$styles.readingModalButtonBorderColor$", rm_btn_border)
    css                 = css.replace("$styles.readingModalFilter$", rm_filter)
    css                 = css.replace("$styles.readingModalTexture$", rm_texture)
    css                 = css.replace("$styles.readingModalBackgroundSize$", rm_bg_size)

    return css

def reload_styles():
    """ Refresh the css variables in the editor's style tag. For use e.g. after config color options have been changed. """

    css                 = styles()
    aqt.editor._html    = re.sub("<style id='siac-styles'>(?:\r\n|\n|.)+?</style>", f"<style id='siac-styles'>{css}</style>", aqt.editor._html)
    editor              = get_index().ui._editor

    if editor is not None:
        if editor.web is not None:
            editor.web.eval(f"document.getElementById('siac-styles').innerHTML = `{css}`;")
            activate_nightmode(None, editor)



def activate_nightmode(shortcuts: List[Tuple], editor: Editor):
    """ Activate dark theme if Anki's night mode is active. """

    editor.web.eval("""
    if (document.body.classList.contains('nightMode')) {
        var props = [];
        for (var i = 0; i < document.styleSheets.length; i++){
            try {
                for (var j = 0; j < document.styleSheets[i].cssRules.length; j++){
                    try{
                        for (var k = 0; k < document.styleSheets[i].cssRules[j].style.length; k++){
                            let name = document.styleSheets[i].cssRules[j].style[k];
                            if (name.startsWith('--c-') && !name.endsWith('-night') && props.indexOf(name) == -1) {
                                props.push(name);
                            }
                        }
                    } catch (error) {}
                }
            } catch (error) {}
        }
        for (const v of props) {
            document.documentElement.style.setProperty(v, getComputedStyle(document.documentElement).getPropertyValue(v + '-night'));
        }
    }
    """)



def setup_ui_after_index_built(editor, index, init_time=None):
    #editor is None if index building finishes while add dialog is not open
    if editor is None:
        return
    config = mw.addonManager.getConfig(__name__)
    show_search_result_area(editor, init_time)
    #restore previous settings
    cmd = ""
    if not index.highlighting:
       cmd += "$('#highlightCb').prop('checked', false);"
    if not get_config_value_or_default("searchOnTyping", True):
        cmd += "$('#typingCb').prop('checked', false); setSearchOnTyping(false);"
    if not get_config_value_or_default("searchOnSelection", True):
        cmd += "$('#selectionCb').prop('checked', false); siacState.searchOnSelection = false;"
    if not index.topToggled:
        cmd += "hideTop();"
    if index.ui is not None and not index.ui.uiVisible:
        cmd += "$('#siac-right-side').addClass('addon-hidden');"
    if config["gridView"]:
        cmd += "activateGridView();"
    editor.web.eval(cmd)
    if index.ui is not None:
        #plot.js is already loaded if a note was just added, so this is a lazy solution for now
        index.ui.plotjsLoaded = False
    if config["notes.sidebar.visible"]:
        index.ui.set_editor(editor)
        index.ui.sidebar.display()

    editor.web.eval("""pycmd('siac-initialised-editor');""")


def show_search_result_area(editor=None, initializationTime=0):
    """ Toggle between the loader and search result area when the index has finished building. """

    js = """
        if (document.getElementById('searchResults')) {
            document.getElementById('searchResults').style.display = 'block';
        }
        if (document.getElementById('loader')) {
            document.getElementById('loader').style.display = 'none';
        }"""

    if check_index():
        get_index().ui.js(js)
    elif editor is not None and editor.web is not None:
        editor.web.eval(js)




def print_starting_info(editor: Editor):
    """ Displays the information that is visible after the first start of the add-on. """

    if editor is None or editor.web is None:
        return

    config  = mw.addonManager.getConfig(__name__)
    index   = get_index()
    html    = "<h3>Search is <span style='color: green'>ready</span>. (%s)</h3>" %  index.type if index is not None else "?"

    if index is not None:


        html += "Initalized in <b>%s</b> s." % index.initializationTime
        if not index.creation_info["index_was_rebuilt"]:
            html += " (No changes detected, index was <b>not</b> rebuilt)"
        html += "<br/>Index contains <b>%s</b> notes." % index.get_number_of_notes()
        html += "<br/><i>Search on typing</i> delay is set to <b>%s</b> ms." % config["delayWhileTyping"]
        html += "<br/>Tag Info on hover is <b>%s</b>.%s" % ("shown" if config["showTagInfoOnHover"] else "not shown", (" Delay: [<b>%s</b> ms]" % config["tagHoverDelayInMiliSec"]) if config["showTagInfoOnHover"] else "")
        html += "<br/>Image max height is <b>%s</b> px." % config["imageMaxHeight"]
        html += "<br/>Retention is <b>%s</b> in the results." % ("shown" if config["showRetentionScores"] else "not shown")
        html += "<br/>Window split is <b>%s / %s</b>." % (config["leftSideWidthInPercent"], 100 - int(config["leftSideWidthInPercent"]))
        html += "<br/>Shortcut is <b>%s</b>." % (config["toggleShortcut"])

        changes = changelog()
        if changes:
            html += "<br/><br/><b>Changelog:</b><hr>"
            for ix, c in enumerate(changes):
                html += f"{ix + 1}. {c}<br>"

        issues = known_issues()
        if issues:
            html += "<br/><b>Known Issues:</b><hr>"
            for ix, i in enumerate(issues):
                html += f"{ix + 1}. {i}<br>"

        html += f"""
            <br>
            <div class='ta_center' style='width: fit-content;'>
                <div class='flex-row' style='margin-bottom: 20px;'>
                    <div class='ta_center'>
                        <div class='siac-caps' style='opacity: 0.8; margin-bottom: 15px;'>BUGS & FEEDBACK</div>
                        <a href='https://github.com/fonol/anki-search-inside-add-card/issues' title='Github repository'><img src='{utility.misc.img_src("github_light.png" if state.night_mode else "github_dark.png")}' style='height: 32px;'/></a>
                    </div>
                    <div class='ta_center' style='margin-left: 30px;'>
                        <div class='siac-caps' style='opacity: 0.8; margin-bottom: 15px;'>BECOME A PATRON</div>
                        <a href='https://www.patreon.com/tomtomtom' title='Patreon site'><img src='{utility.misc.img_src("patreon.png")}' style='height: 32px;'/></a>
                    </div>
                </div>
                <span class='siac-caps' style='opacity: 0.8;'>
                    Thanks to all supporters!
                </span>
            </div>
            """

    if not state.db_file_existed:
        html += "<br><br><b><i>siac-notes.db</i> was not existing, created a new one.</b>"

    if index is None or index.ui is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"


    editor.web.eval("""document.getElementById('searchResults').innerHTML = `
            <div id='siac-start-info'>
                %s
            </div>`;""" % html)


@requires_index_loaded
def display_model_dialog():
    """ Called after clicking on "Set Fields" in the settings modal. """

    if check_index():
        html = get_model_dialog_html()
        get_index().ui.show_in_modal_subpage(html)

@js
def show_settings_modal(editor):
    """ Display the Settings modal. """

    config  = mw.addonManager.getConfig(__name__)
    html    = get_settings_modal_html(config)
    index   = get_index()

    index.ui.showInModal(html)
    return "$('.modal-close').on('click', function() {pycmd(`siac-write-config`); })"

@js
def show_unsuspend_modal(nid):
    """ Display the modal to unsuspend cards of a note. """

    html    = get_unsuspend_modal(nid)
    index   = get_index()

    index.ui.showInModal(html)
    return "siacState.keepPositionAtRendering = true; $('.modal-close').on('click', function() {pycmd(`siac-rerender`);$('.modal-close').off('click'); });"


@js
def display_note_del_confirm_modal(editor, nid):
    """ Display the modal that asks to confirm a (add-on) note deletion. """

    html = get_note_delete_confirm_modal_html(nid)
    if not html:
        return
    return "$('#resultsWrapper').append(`%s`);" % html


def fillTagSelect(editor = None, expanded = False) :
    """
    Builds the html for the "browse tags" mode in the deck select.
    Also renders the html.
    """
    tags            = mw.col.tags.all()
    user_note_tags  = get_all_tags()
    tags.extend(user_note_tags)
    tags            = set(tags)
    tmap            = utility.tags.to_tag_hierarchy(tags)

    most_active     = get_most_active_tags(5)
    most_active_map = dict()

    for t in most_active:
        if t in tmap:
            most_active_map[t] = tmap[t]
        else:
            most_active_map[t] = {}

    def iterateMap(tmap, prefix, start=False):
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in tmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); pycmd('siac-r-search-tag %s')\"><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % (full, "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), iterateMap(value, full, False))
        html += "</ul>"
        return html

    most_active_html    = iterateMap(most_active_map, "", True)
    html                = iterateMap(tmap, "", True)

    # the dropdown should only be expanded on user click, not on initial render
    expanded_js         = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""
    quick_disp          = "block" if len(most_active_map) > 0 else "none"

    cmd                 = """
    document.getElementById('deck-sel-info-lbl').style.display = 'none';
    document.getElementById('deckSelQuickWrapper').style.display = '%s';
    document.getElementById('siac-deck-sel-q-sep').style.display = '%s';
    document.getElementById('deckSelQuick').innerHTML = `%s`;
    document.getElementById('deckSel').innerHTML = `%s`;
    $('#deckSelWrapper .exp').click(function(e) {
		e.stopPropagation();
        let icn = $(this);
        if (icn.text()) {
            if (icn.text() === '[+]')
                icn.text('[-]');
            else
                icn.text('[+]');
        }
        $(this).parent().parent().children('ul').toggle();
    });
    $("#siac-deck-sel-btn-wrapper").hide();
    %s
    """ % (quick_disp, quick_disp, most_active_html, html, expanded_js)
    if editor is not None:
        editor.web.eval(cmd)
    else:
        get_index().ui.js(cmd)

def fillDeckSelect(editor = None, expanded= False, update = True):
    """ Fill the selection with user's decks """

    deckMap     = dict()
    config      = mw.addonManager.getConfig(__name__)
    deckList    = config['decks']
    index       = get_index()
    if editor is None:
        if index is not None and index.ui is not None and index.ui._editor is not None:
            editor = index.ui._editor
        else:
            return

    for d in list(mw.col.decks.decks.values()):
       if d['name'] == 'Standard':
          continue
       if deckList is not None and len(deckList) > 0 and d['name'] not in deckList:
           continue
       deckMap[d['name']] = d['id']
    set_deck_map(deckMap)
    dmap        = {}
    for name, id in deckMap.items():
        dmap = addToDecklist(dmap, id, name)

    dmap        = dict(sorted(dmap.items(), key=lambda item: item[0].lower()))
    def iterateMap(dmap, prefix, start=False):
        decks = index.selectedDecks if index is not None else []
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in dmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item %s' data-id='%s' onclick='event.stopPropagation(); updateSelectedDecks(this);'><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % ( "selected" if str(deckMap[full]) in decks or decks == ["-1"] else "", deckMap[full],  "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), iterateMap(value, full, False))
        html += "</ul>"
        return html

    html        = iterateMap(dmap, "", True)
    expanded_js = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""
    update_js   = "updateSelectedDecks();" if update else ""

    cmd         = """
    document.getElementById('deck-sel-info-lbl').style.display = 'block';
    document.getElementById('deckSelQuickWrapper').style.display = 'none';
    document.getElementById('siac-deck-sel-q-sep').style.display = 'none';
    document.getElementById('deckSel').innerHTML = `%s`;
    $('#deckSelWrapper .exp').click(function(e) {
		e.stopPropagation();
        let icn = $(this);
        if (icn.text()) {
            if (icn.text() === '[+]')
                icn.text('[-]');
            else
                icn.text('[+]');
        }
        $(this).parent().parent().children('ul').toggle();
    });
    %s
    $("#siac-deck-sel-btn-wrapper").show();
    %s
    """ % (html, expanded_js, update_js)
    editor.web.eval(cmd)

def addToDecklist(dmap, id, name):
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = dmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}})
    return dmap

def try_select_deck(deck: str) -> bool:
    """ Try to select a deck with the given name. """

    if not deck or len(deck.strip()) == 0:
        return False

    win = aqt.mw.app.activeWindow()
    # dont trigger keypress in edit dialogs opened within the add dialog
    if not isinstance(win, aqt.addcards.AddCards):
        return False

    try:
        win.deckChooser.setDeckName(deck)
        # win.deckChooser.onDeckChange()
        return True
    except:
        return False



def changelog() -> List[str]:
    """ Returns recent add-on changes. """

    return [
        "Added menu item to access add-on's dialogs from outside the Add window (thanks to p4nix)",
        "Added settings dialog, accessible from menu (thanks to p4nix)",
        "Added Quick Youtube Import dialog, accessible from menu (thanks to p4nix)",
        "Extended 'Theme' dialog in the PDF reader a bit",
        "Page forward/backward shortcuts can be set in config now",
        "Display title of currently read item in the Add window's title bar",
        "Fix: Bug when hitting Area Highlight shortcut multiple times"
    ]

def known_issues() -> List[str]:
    """ Returns currently known issues/bugs. """

    return [
        "Tag autocomplete in Create/Update note modal only works on first tag",
        "PDF reader \"Loading PDF\" message positioned wrong on older Anki versions",
        "Highlights in PDFs not working on some platforms/Anki versions, workaround: set 'pdf.highlights.use_alt_render' to true in the config",
        "PDFs are not scrollable on Anki installs with older Qt versions (i.e. OS X - alternate (!) build)"
    ]
