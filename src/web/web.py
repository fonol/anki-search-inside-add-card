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


import re
import aqt
import typing
from typing import List, Tuple
from aqt import mw
from aqt.editor import Editor

import utility.tags
import utility.text
import utility.misc

from aqt.qt import *


from ..state import get_index
from ..notes import get_note, get_all_tags
from .html import *
from ..internals import js, requires_index_loaded, perf_time, JS, HTML
from ..models import SiacNote
from ..config import get_config_value_or_default
from ..output import UI


@js
def toggleAddon() -> JS:
    return "toggleAddon();"


def getScriptPlatformSpecific() -> HTML:
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

        --c-search-icn-night: url("data:image/svg+xml,%3Csvg width='12' height='12' xmlns='http://www.w3.org/2000/svg'%3E%3Cg%3E%3Crect fill='none' id='canvas_background' height='14' width='14' y='-1' x='-1'/%3E%3Cg display='none' overflow='visible' y='0' x='0' height='100%25' width='100%25' id='canvasGrid'%3E%3Crect fill='url(%23gridpattern)' stroke-width='0' y='0' x='0' height='100%25' width='100%25'/%3E%3C/g%3E%3C/g%3E%3Cg%3E%3Cellipse stroke='white' ry='2.301459' rx='2.317666' id='svg_10' cy='4.004963' cx='4.055105' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3Cline stroke='white' stroke-linecap='null' stroke-linejoin='null' id='svg_11' y2='9.969307' x2='10.003241' y1='5.722954' x1='5.497568' fill-opacity='null' stroke-opacity='null' stroke-width='1.3' fill='none'/%3E%3C/g%3E%3C/svg%3E");
    }
    """.replace("%", "%%")

    # css + js
    all = """
    <style>
        %s
    </style>
    <style id='siac-styles'>
        %s
    </style>
    """
    css                 = styles()

    return all % (icon_vars, css)

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
    primary_color       = str(get_config_value_or_default("styles.primaryColor", "#2e6286"))
    primary_color_night = str(get_config_value_or_default("styles.night.primaryColor", "#2e6286"))
    tagFG               = str(get_config_value_or_default("styles.tagForegroundColor", "black"))
    tagBG               = str(get_config_value_or_default("styles.tagBackgroundColor", "#f0506e"))
    tagNightFG          = str(get_config_value_or_default("styles.night.tagForegroundColor", "black"))
    tagNightBG          = str(get_config_value_or_default("styles.night.tagBackgroundColor", "DarkOrange"))

    highlightFG         = str(get_config_value_or_default("styles.highlightForegroundColor", "black"))
    highlightBG         = str(get_config_value_or_default("styles.highlightBackgroundColor", "yellow"))
    highlightNightFG    = str(get_config_value_or_default("styles.night.highlightForegroundColor", "black"))
    highlightNightBG    = str(get_config_value_or_default("styles.night.highlightBackgroundColor", "SpringGreen"))

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
    rm_theme            = str(get_config_value_or_default("styles.readingModalThemeColor", "darkorange"))

    css                 = css.replace("$imgMaxHeight$", imgMaxHeight)
    css                 = css.replace("$pdfTooltipMaxHeight$", pdfTooltipMaxHeight)
    css                 = css.replace("$pdfTooltipMaxWidth$", pdfTooltipMaxWidth)

    css                 = css.replace("$styles.primaryColor$", primary_color)
    css                 = css.replace("$styles.night.primaryColor$", primary_color_night)
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
    css                 = css.replace("$styles.readingModalThemeColor$", rm_theme)

    return css

def reload_styles():
    """ Refresh the css variables in the editor's style tag. For use e.g. after config color options have been changed. """

    css                 = styles()
    aqt.editor._html    = re.sub("<style id='siac-styles'>(?:\r\n|\n|.)+?</style>", f"<style id='siac-styles'>{css}</style>", aqt.editor._html)
    editor              = UI._editor

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



@requires_index_loaded
def display_model_dialog():
    """ Called after clicking on "Set Fields" in the settings modal. """

    html = get_model_dialog_html()
    UI.show_in_modal("Set Fields", html)

@js
def show_settings_modal(editor) -> JS:
    """ Display the Settings modal. """

    config  = mw.addonManager.getConfig(__name__)
    html    = get_settings_modal_html(config)
    index   = get_index()

    UI.show_in_modal("Settings", html)
    return "$('.modal-close').on('click', function() {pycmd(`siac-write-config`); })"

@js
def show_unsuspend_modal(nid) -> JS:
    """ Display the modal to unsuspend cards of a note. """

    html    = get_unsuspend_modal(nid)
    index   = get_index()

    UI.show_in_modal("Unsuspend Cards", html)
    return "SIAC.State.keepPositionAtRendering = true; $('.siac-modal-close').on('click', function() { pycmd(`siac-rerender`);$('.siac-modal-close').off('click'); });"


@js
def display_note_del_confirm_modal(editor, nid) -> JS:
    """ Display the modal that asks to confirm a (add-on) note deletion. """

    html = get_note_delete_confirm_modal_html(nid)
    if not html:
        return
    return "$('#resultsWrapper').append(`%s`);" % html

def display_note_linking(web, linked_note: Tuple[SiacNote, int]):

    (note, page)    = linked_note
    if page is None or page <= 0:
        page_dsp = "-"
    else:
        page_dsp = page
    html = f"""
        <div id='siac-link-modal' style='display: none; min-width: 235px; position: absolute; bottom: 20px; right: 20px; padding: 15px; box-shadow: 0 0 7px 1px #dcdcdc; background: #fffef7; color: black; '>
            <div style='font-size: 13px !important; margin-bottom: 10px !important;'>{utility.text.trim_if_longer_than(note.get_title().replace('`', ''), 80)}</div>
            <div style='font-size: 13px !important; text-align: left;'><span style='opacity: 0.8;'>Page: {page_dsp}</span><a href="" style='float: right; color: #0096dc !important; font-size: 13px !important;' onclick='pycmd("siac-open-linked-note {note.id} {page}"); return false;'>Open in Add dialog</a></div>
        </div>
        """
    js = f"""
        if (document.getElementById('siac-link-modal')) {{
            $('#siac-link-modal').remove();
        }}
        $(document.body).append(`{html}`);
        if (document.body.classList.contains('night-mode') || document.body.classList.contains('nightMode')) {{
            $('#siac-link-modal').css({{ 'box-shadow' : '0 0 7px 1px #202020', 'background': 'rgb(53,53,53)', 'color': 'white' }});
        }}
        $('#siac-link-modal').show();
        """
    web.eval(js)

def display_file(fname: str):

    if not fname.lower().endswith(".md"):
        print("[SIAC] Trying to open non-md file: " + fname)
        return

    md_folder = get_config_value_or_default("md.folder_path", None).replace("\\", "/")
    if not md_folder.endswith("/"):
        md_folder += "/"

    fpath_full = md_folder + fname

    UI.js("""
        if (!byId('siac-md-edit')) {
            $('#siac-right-side').append(`
                <div id='siac-md-edit-wrapper'>
                    <div id='siac-md-edit'>
                        <textarea id='siac-md-edit-ta'></textarea>

                    </div> 
                </div>
            `);
        }
        editorMDInit(byId('siac-md-edit-ta'));
    """)

    


def fillTagSelect(editor = None, expanded = False):
    """
    Builds the html for the "browse tags" mode in the deck select.
    Also renders the html.
    """
    tags            = mw.col.tags.all()
    user_note_tags  = get_all_tags()
    tags.extend(user_note_tags)
    tags            = set(tags)
    tmap            = utility.tags.to_tag_hierarchy(tags)

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

    html                = iterateMap(tmap, "", True)

    # the dropdown should only be expanded on user click, not on initial render
    expanded_js         = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""

    cmd                 = """
    document.getElementById('deck-sel-info-lbl').style.display = 'none';
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
    """ % (html, expanded_js)
    if editor is not None:
        editor.web.eval(cmd)
    else:
        UI.js(cmd)






