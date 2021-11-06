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
import io
import typing
from aqt import mw
from aqt.utils import showInfo
from typing import List, Tuple, Dict, Optional, Any

from .note_templates import *
from .templating import filled_template
from ..state import get_index, check_index
from ..notes import  PDFMark, get_note, _get_priority_list, get_avg_pages_read, get_all_tags, get_related_notes, get_priority, dynamic_sched_to_str, get_read_today_count
from ..internals import perf_time, HTML, JS
from ..config import get_config_value_or_default as conf_or_def
from ..models import IndexNote
import utility.misc
import utility.tags
import utility.text
import utility.date


""" Html.py - various HTML-building functions. 
    Bigger UI components like the reading modal (reading_modal.py) or the sidebar (sidebar.py) contain their own HTML producing functions.
"""


def get_synonym_dialog() -> HTML:
    """ Returns the html for the dialog that allows input / editing of synonym sets (Settings & Info > Synonyms). """

    synonyms    = loadSynonyms()

    if not synonyms:
        return filled_template("synonyms_empty", {})

    st          = ""
    for c, sList in enumerate(synonyms):
        st += """<tr>
                    <td>
                        <div contenteditable='true' onkeydown='synonymSetKeydown(event, this, %s)'>%s</div>
                    </td>
                    <td class='ta_right' style='height: 20px;'>
                        <i class='fa fa-trash blue-hover' onclick='pycmd(\"siac-delete-synonyms %s\")'></i>
                        <i class='fa fa-search blue-hover' style='margin-left: 4px;' onclick='searchSynset(this)'></i>
                    </td>
                </tr>""" % (c, ", ".join(sList), c)
    
    params = dict(len = len(synonyms), sets = st)
    return filled_template("synonyms", params)

def save_synonyms(synonyms: List[List[str]]):
    config              = mw.addonManager.getConfig(__name__)
    filtered            = []

    for sList in synonyms:
        filtered.append(sorted(sList))

    config["synonyms"]  = filtered
    mw.addonManager.writeConfig(__name__, config)

def new_synonyms(syn_input: str):
    """ Save/merge input synonyms. """

    existing    = loadSynonyms()
    sList       = [utility.text.clean_synonym(s) for s in syn_input.split(",") if len(utility.text.clean_synonym(s)) > 1]
    if not sList:
        return
    found       = []
    foundIndex  = []
    for c, eList in enumerate(existing):
        for s in sList:
            if s in eList:
                found += eList
                foundIndex.append(c)
    if found:
        existing = [i for j, i in enumerate(existing) if j not in foundIndex]
        existing.append(list(set(sList + found)))
    else:
        existing.append(sList)
    save_synonyms(existing)

def delete_synonym_set(ix: int):

    existing    = loadSynonyms()
    if ix >= 0 and ix < len(existing):
        existing.pop(ix)
    save_synonyms(existing)

def edit_synonym_set(cmd: str):
    index       = int(cmd.strip().split()[0])
    existing    = loadSynonyms()
    existing.pop(index)
    sList       = [utility.text.clean_synonym(s) for s in cmd[len(cmd.strip().split()[0]):].split(",") if len(utility.text.clean_synonym(s)) > 1]
    if not sList:
        return
    found       = []
    foundIndex  = []
    for c, eList in enumerate(existing):
        for s in sList:
            if s in eList:
                found += eList
                foundIndex.append(c)
    if found:
        existing = [i for j, i in enumerate(existing) if j not in foundIndex]
        existing.append(list(set(sList + found)))
    else:
        existing.append(sList)
    save_synonyms(existing)

def loadSynonyms() -> List[List[str]]:
    config = mw.addonManager.getConfig(__name__)
    try:
        synonyms = config['synonyms']
    except KeyError:
        synonyms = []
    return synonyms


def right_side_html(indexIsLoaded: bool = False) -> HTML:
    """
    Returns the javascript call that inserts the html that is essentially the right side of the add card dialog.
    The right side html is only inserted if not already present, so it is safe to call this function on every note load.
    """

    leftSideWidth                           = conf_or_def("leftSideWidthInPercent", 40)
    if not isinstance(leftSideWidth, int) or leftSideWidth <= 0 or leftSideWidth > 100:
        leftSideWidth = 50

    html_params                             = {}
    html_params["rightSideWidth"]           = 100 - leftSideWidth
    html_params["noteScale"]                = conf_or_def("noteScale", 1.0)
    html_params["leftSideWidthInPercent"]   = leftSideWidth
    html_params["showLoader"]               = "display: none;" if indexIsLoaded else ""
    html_params["sidebarHidden"]            = "hidden" if conf_or_def("hideSidebar", False) else ""
    html_params["calendar"]                 = get_calendar_html() if conf_or_def("showTimeline", True) else ""
    html_params["shortcutFilter"]           = conf_or_def("shortcuts.trigger_current_filter", "CTRL+K")
    html_params["searchbarMode"]            = "Add-on" if not get_index() else get_index().searchbar_mode
    html_params["shortcutPredef"]           = conf_or_def("shortcuts.trigger_predef_search", "ALT+K")

    # if left and right side are switched, the insert code looks a bit different
    if conf_or_def("switchLeftRight", False):
        insert_code = """
            $(toInsert).insertBefore('#leftSide');
            $(document.body).addClass('siac-left-right-switched');
        """
    else:
        insert_code = """
            $(toInsert).insertAfter('#leftSide');   
        """

    # fill the main_ui template
    main_ui = filled_template("main_ui", html_params)
  
    # the javascript that inserts the add-on's UI. The anonymous function returns a bool indicating whether the UI was already
    # present or not.
    # $(`.siac-col`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow: hidden; height: 100%%;"></div>');
    return """
        var wfn = () => { 
            if (!document.getElementsByClassName('fields').length) {
                setTimeout(wfn, 50);
                console.log('[SIAC] right_side_html(): fields DOM element not yet rendered, timeout=50');
                return;
            }
            if (typeof($) === 'undefined') {
                setTimeout(wfn, 50);
                console.log('[SIAC] right_side_html(): jquery not yet loaded, retrying in 50ms.');
                return;
            }
            if (document.getElementById('outerWr') == null) {
                console.log('[SIAC] right_side_html(): wrapping fields.');
                let fields = document.getElementsByClassName('fields')[0];
                if (!fields) {
                    console.log('[SIAC] right_side_html: .fields DOM element not found.');
                    return;
                }
                $(fields).wrap(`<div class='siac-col' id='leftSide' onmouseenter='fieldsMouseEnter(event)' style='flex-grow: 1; width: %s%%;'></div>`);
                //$('#dupes').insertAfter('#fields');
                
                let toInsert = `%s`;
                %s  


                $(`.siac-col`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow: hidden; height: 100%%;"></div>');

                let aFn = () => {
                    if (typeof(updatePinned) === "undefined") {
                        setTimeout(aFn, 50);
                        return;
                    }
                    updatePinned();
                    onWindowResize();
                }
                aFn();
                var there = false;
            } else {
                console.log('[SIAC] right_side_html(): fields are already wrapped.');
                var there = true;
            }
            let sFn = () => {
                if (typeof(SIAC) === 'undefined' || typeof(SIAC.State) === 'undefined') {
                    console.log('[SIAC] right_side_html(): SIAC js not yet set, retrying in 50 ms.');
                    setTimeout(sFn, 50);
                    return;
                } 
                if (SIAC.State.searchOnTyping) {
                    SIAC.Fields.enableSearchOnTypingEventListener();
                } 
                SIAC.Fields.setSelectionMouseUpEventListener();
                window.addEventListener('resize', onWindowResize, true);
                $('.cal-block-outer').on('mouseenter', function(event) { calBlockMouseEnter(event, this); });
                $('.cal-block-outer').on('click', function(event) { displayCalInfo(this); });
            };
            sFn();
            return there; 
        };
        wfn();
    """ % (
    leftSideWidth,
    main_ui,
    insert_code
    )


def get_model_dialog_html() -> HTML:
    """ Returns the html for the "Fields" section in the settings modal. """

    all_models  = sorted(mw.col.models.all(), key=lambda m : m['name'])
    config      = mw.addonManager.getConfig(__name__)

    html        = """
    <div class='mt-10 mb-10'>
        <div class='siac-modal-btn' onclick='pycmd("siac-styling")'>Back to Settings</div>
    </div>
    <div style='flex: 0 0 auto;'>
        <p>Changes in <i>Show Field in Results</i> take effect immediately, changes in <i>Search in Field</i> need a rebuild of the index.</p>
    </div>
    <div style='flex: 0 0 auto;'>
        <table class='w-100 mt-10 mb-5'>
            <tr>
                <td class='bold' style='width: 80%;'>Field Name</td>
                <td class='bold' style='width: 10%;'>Search in Field</td>
                <td class='bold' style='width: 10%;'>Show Field in Results</td>
            </tr>
        </table>
    </div>
    <div class='oflow_y_auto w-100' style='flex: 1 1 auto;'><div class='h-100'>
    """
    for m in all_models:
        html += "<div class='siac-model-name'>%s</div>" % utility.text.trim_if_longer_than(m["name"], 40)
        flds = "<table class='siac-model-table'>"
        for f in m["flds"]:
            flds += """<tr>
                            <td style='width: 80%%' class='siac-model-field'>%s</td>
                            <td style='width: 10%%;' class='ta_center'><input type='checkbox' onchange='updateFieldToExclude(this, "%s", %s)' %s/></td>
                            <td style='width: 10%%;' class='ta_center'><input type='checkbox' onchange='updateFieldToHideInResult(this, "%s", %s)' %s/></td>
                    </tr>""" % (
                    f['name'],
                    m['id'],
                    f['ord'],
                    "checked" if str(m['id']) not in config["fieldsToExclude"] or f['ord'] not in config["fieldsToExclude"][str(m['id'])] else "",
                    m['id'],
                    f['ord'],
                    "checked" if str(m['id']) not in config["fieldsToHideInResults"] or f['ord'] not in config["fieldsToHideInResults"][str(m['id'])] else "")
        flds += "</table>"
        html += "<div class='siac-model-fields'>%s</div>" % flds
    html += "</div></div>"
    return html

def get_calendar_html() -> HTML:
    """ Html for the timeline at the bottom of the search pane. """

    html                    = """<div id='cal-row' class='w-100' onmouseleave='calMouseLeave()'>%s</div> """
    #get notes created since the beginning of the year
    day_of_year             = datetime.datetime.now().timetuple().tm_yday
    date_year_begin         = datetime.datetime(year=datetime.datetime.utcnow().year, month=1, day=1, hour=0, minute=0)
    nid_now                 = int(time.time() * 1000)
    nid_minus_day_of_year   = int(date_year_begin.timestamp() * 1000)

    res                     = mw.col.db.all("select distinct notes.id from notes where id > %s and id < %s order by id asc" %(nid_minus_day_of_year, nid_now))

    counts                  = []
    c                       = 1
    notes_in_current_day    = 0

    for i, r in enumerate(res):

        c_day_of_year = time.localtime(r[0]/1000).tm_yday

        if c_day_of_year == c:
            notes_in_current_day += 1
            if i == len(res) - 1:
                counts.append(notes_in_current_day)
        else:
            counts.append(notes_in_current_day)
            notes_in_current_day    = 1
            counts                  += [0 for _ in range(0, c_day_of_year - c - 1)]
            # for _ in range(0, c_day_of_year - c - 1):
            #     counts.append(0)

        c = c_day_of_year
    while len(counts) < day_of_year:
        counts.append(0)

    html_content    = ""
    added           = 0

    for i, notes_in_current_day in enumerate(counts):
        if notes_in_current_day > 20:
            color = "cal-three"
        elif notes_in_current_day > 10:
            color = "cal-two"
        elif notes_in_current_day > 0:
            color = "cal-one"
        else:
            color = ""

        html_content = f"{html_content}<div class='cal-block-outer'><div class='cal-block %s %s' data-index='%s'></div></div>" % ("cal-today" if i == len(counts) - 1 else "", color, added)
        added += 1

    html = html % html_content
    return html

def read_counts_card_body(counts: Dict[int, int]) -> HTML:
    """ Html for the card that displays today's read pages. """

    if counts is None or len(counts) == 0:
        return """
            <center style='margin-top: 15px;'>
                <b>Nothing marked as read.</b>
            </center>
        """

    ordered   = [(k, counts[k]) for k in sorted(counts, key=counts.get, reverse=True)]
    html      = ""
    ix        = 0
    for nid, tup in ordered:
        row     = ""
        title   = utility.text.trim_if_longer_than(tup[1], 70)
        c       = tup[0]
        ix      += 1
        if c < 100:
            for i in range(c): 
                row = f"{row}<span class='siac-read-box'></span>" 
        else:
            for i in range(100): 
                row = f"{row}<span class='siac-read-box'></span>" 
            row = f"{row}<span class='keyword'>&nbsp; (+ {c-100})</span>"

        html = f"{html}<tr><td style='min-width: 240px;'><a class='keyword' onclick='pycmd(\"siac-read-user-note {nid}\")'>{ix}. {title}</a></td><td style='padding-left: 5px; text-align: right;'><b style='vertical-align: middle; word-break: keep-all;'>{c}</b></td><td style='padding-left: 5px;'>{row}</td></tr>"
    html = f"<br><table class='siac-read-stats-table'>{html}</table>"

    html += """
    """
    return html

def marks_card_body(marks: List[Tuple[Any, ...]]) -> HTML:
    """ Builds the HTML for the card which is displayed when clicking on PDF -> Marks """

    if marks is None or len(marks) == 0:
        return """<center class='pt-10 pb-10'>No marks have been set yet.</center>"""

    html = ""
    dnow = datetime.datetime.now()

    for created, marktype, nid, page, pagestotal, pdf_title in marks:

        marktype_str    = PDFMark.pretty(PDFMark(marktype))
        cdate           = utility.date.dt_from_stamp(created)
        diff            = utility.date.date_diff_to_string(dnow-cdate)
        html            = f"""{html}
            <tr style=''>
                <td style='white-space: nowrap;'>{diff} ago</td>
                <td style='white-space: nowrap;'>{marktype_str}</td>
                <td><a class='keyword' onclick='pycmd("siac-read-user-note {nid} {page}")'>{pdf_title}</a></td>
                <td style='white-space: nowrap;'>{page} / {pagestotal}</td>
            </tr>
        """
    html = f"""
        <table class='w-100'>
            {html}
        </table>
    """

    return html

def topic_card_body(topics: List[Tuple[str, float]]) -> HTML:
    html = """
                <div class='flex-row w-100' style='margin-top: 20px; flex-wrap: wrap;'>
                    <div style='min-width: 400px; flex: 1 1 auto;'>
                        <div class='w-100 ta_center bold'>All PDFs</div>
                        <div id='siac-read-stats-topics-pc_1' class='w-100' style='height: 400px;'></div>
                    </div> 
                    <div style='min-width: 400px; flex: 1 1 auto;'>
                        <div class='w-100 ta_center bold'>Read last 7 days</div>
                        <div id='siac-read-stats-topics-pc_2' class='w-100' style='height: 400px;'></div>
                    </div> 
                </div> 
                """
    return html

def read_counts_by_date_card_body(counts: Dict[str, int]) -> HTML:
    """ Html for the card that displays read pages / day (heatmap). """

    if counts is None or len(counts) == 0:
        return """
            <center style='margin-top: 15px;'>
                <b>Nothing marked as read.</b>
            </center>
        """

    doy     = utility.date.day_of_year()
    v_sum   = sum(counts.values())
    v_max   = max(counts.values())
    avg_r   = round(v_sum / doy, 1)

    html = f"""
        <div id='siac-read-time-ch' class='w-100' style='margin: 30px auto 10px auto;'></div>
        <div class='w-100 flex-row' style='margin-top: 15px;align-items: center; justify-content: center;'>
            <table>
                <tr>
                    <td class='siac-caps'>Avg. read pages / day:</td>
                    <td><b style='margin-left: 20px;'>{avg_r}</b></td>
                </tr>
                <tr>
                    <td class='siac-caps'>Most read pages on a single day:</td>
                    <td><b style='margin-left: 20px;'>{v_max}</b></td>
                </tr>
            </table>
        </div>
    """
    return html


def get_note_delete_confirm_modal_html(nid: int) -> Optional[HTML]:
    """ Html for the modal that pops up when clicking on the trash icon on an add-on note. """

    note            = get_note(nid)
    if not note:
        return None
    title           = utility.text.trim_if_longer_than(note.get_title(), 100) 
    priority        = note.priority

    if priority is None or priority == 0:
        priority    = "-"
        fg          = "black"
        bg          = "transparent"

    else:
        priority    = int(priority)
        fg          = "white"
        bg          = utility.misc.prio_color(priority)
        priority    = f"<span style='padding: 0 3px 0 3px; color: {fg} ;background: {bg}'>{priority}</span>"

    return filled_template("note_delete", dict(title = title, creation_date = note.created, priority = priority, nid = nid))


def get_settings_modal_html(config) -> HTML:
    """ Returns the HTML for the settings/styling modal. """

    params = dict(
        zoom                        = config["searchpane.zoom"],
        left_side_width             = config["leftSideWidthInPercent"],
        hide_sidebar                = "checked='true'" if config["hideSidebar"] else "",
        show_timeline               = "checked='true'" if config["showTimeline"] else "",
        show_tag_info_on_hover      = "checked='true'" if config["showTagInfoOnHover"] else "",
        tag_hover_delay             = config["tagHoverDelayInMiliSec"],
        rebuild_ix_if_smaller_than  = config["alwaysRebuildIndexIfSmallerThan"],
        remove_divs                 = "checked='true'" if config["removeDivsFromOutput"] else "",
        hide_clozes                 = "checked='true'" if config["results.hide_cloze_brackets"] else "",
        note_db_folder              = config["addonNoteDBFolderPath"],
        pdf_url_import_folder       = config["pdfUrlImportSavePath"],
        show_source                 = "checked='true'" if config["notes.showSource"] else "",
        use_in_edit                 = "checked='true'" if config["useInEdit"] else "",
        show_float_btn              = "checked='true'" if config["results.showFloatButton"] else "",
        show_id_btn                 = "checked='true'" if config["results.showIDButton"] else "",
        show_cid_btn                = "checked='true'" if config["results.showCIDButton"] else "",
        tag_fg                      = utility.misc.color_to_hex(config["styles.tagForegroundColor"]), 
        tag_bg                      = utility.misc.color_to_hex(config["styles.tagBackgroundColor"]),
        tag_fg_night                = utility.misc.color_to_hex(config["styles.night.tagForegroundColor"]),
        tag_bg_night                = utility.misc.color_to_hex(config["styles.night.tagBackgroundColor"]),
        hl_fg                       = utility.misc.color_to_hex(config["styles.highlightForegroundColor"]),
        hl_bg                       = utility.misc.color_to_hex(config["styles.highlightBackgroundColor"]),
        hl_fg_night                 = utility.misc.color_to_hex(config["styles.night.highlightForegroundColor"]),
        hl_bg_night                 = utility.misc.color_to_hex(config["styles.night.highlightBackgroundColor"]),
        susp_fg                     = utility.misc.color_to_hex(config["styles.suspendedForegroundColor"]), 
        susp_bg                     = utility.misc.color_to_hex(config["styles.suspendedBackgroundColor"]),
        modal_border                = utility.misc.color_to_hex(config["styles.modalBorderColor"]), 
        modal_border_night          = utility.misc.color_to_hex(config["styles.night.modalBorderColor"]),
    )
    return filled_template("settings_modal", params)

def get_timer_elapsed_html() -> HTML:
    read_today_count    = get_read_today_count()
    added_today_count   = utility.misc.count_cards_added_today()
    params              = dict(pages_read = read_today_count, 
                                cards_added = added_today_count, 
                                pages="page" if read_today_count == 1 else "pages", 
                                cards="card" if added_today_count == 1 else "cards")

    return filled_template("timer_elapsed", params)

def get_loader_html(text: HTML) -> HTML:
    html = """
        <div class='siac-modal-small'>
            <div> <div class='signal'></div><br/>%s</div>
        </div>
    """ % text
    return html

def file_tree(tree: Dict[str, Any]) -> HTML:

    def _subtree(t, pre="") -> HTML:
        html = ""
        for k, v in t.items():
            sub     = ""
            fcls    = "file"
            path    = ""
            pre_u   = pre + k + "/"
            if v is not None and len(v) > 0:
                sub     = f"<ul>{_subtree(v, pre_u)}</ul>"
                fcls    = "folder" 
            else:
                path    = pre + k
                path    = utility.text.b64_encode_str(path) 

            html = f"{html}<li class='siac-ft-item {fcls}' data-path='{path}' onclick='SIAC.Filetree.itemClicked(event, this)'><span>{k}</span>{sub}</li>"

        return html
    html = f"<ul class='siac-file-tree'>{_subtree(tree)}</ul>"
    return html





def get_pdf_list_first_card() -> HTML:
    """
        Returns the html for the body of a card that is displayed at first position when clicking on "PDFs".
    """
    html = """
        <div style='user-select: none;'>
            <a class='keyword' onclick='pycmd("siac-r-pdf-last-read")'>Order by Last Read</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-last-added")'>Order by Last Added</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-size desc")'>Order by Size (Descending)</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-size asc")'>Order by Size (Ascending)</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-find-invalid")'>Find Invalid Paths</a>
        </div>
       
    """
    return html

def get_tips_html() -> List[Tuple[str, HTML]]:
    """ Settings & Info -> Tips:  Returns a list of (title, body) pairs of html to print. """

    return [("General Tips", """
    <ol>
        <li>Look up available shortcuts in the 'Info' dialog. Most of them can be set in the config.</li>
        <li>A convenient way to quickly open a certain PDF is to use CTRL+O.</li>
        <li>Drag and drop a PDF file on the add-on pane to open the Create Note modal with that file path.</li>
        <li>CTRL/Meta + Click on a tag in the notes sidebar opens the Create Note modal with that tag.</li>
        <li>Not all settings are in the "Settings" dialog, some can be set only through Anki's add-on config dialog.</li>
        <li>If something happens to the add-on's DB file ('siac-notes.db'): Backups are created once each day (last 10 days), in the same folder as the 
        'siac-notes.db' file. Remove the corrupted 'siac-notes.db' file, replace it with a backup file and rename it to 'siac-notes.db'.
        </li>
    </ol>
        
"""), ("Markdown in Notes", """
Supported elements are, besides the standard markdown:<br>
    <ol>
        <li>Fenced Code Blocks (```)</li>
        <li>Definition Lists (: )</li>
        <li>Blockquotes (>)</li>
    </ol>

Newlines can be done with two trailing spaces at the end of a line.
"""),
("How to add PDFs or Youtube videos", """
In general, it is the "Source" field that determines how the note is opened. If you put the path to a PDF file in the source field, 
e.g. <i>C:/Path/to/file.pdf</i>, the add-on will attempt to open it as a PDF. 
For embedding YouTube videos, you simply have to paste the URL of the video into the source field.
"""),
("Shortcuts", """
Some of the default shortcuts might not work on every Anki installation, e.g. when I did the "Toggle Page Read" shortcut (Ctrl+Space), I didn't know that
this is reserved on Mac OS for the finder, so you might want to try out different values.
"""),
("Bugs", """
    If you find anything that does not seem to work correctly, please notify me, and don't wait for me to publish a fix
    on my own. As there are a lot of configuration options and features at this point, it is infeasible for me to test every single feature and
    combination of settings after every update. So if nobody notifies me, it might happen that bugs remain for weeks before I randomly stumble upon them.
<br><br>
<a href='https://github.com/fonol/anki-search-inside-add-card/issues'>Issue page on the Github repository</a>
""")
]

def get_unsuspend_modal(nid: int) -> HTML:
    """ Returns the html content for the modal that is opened when clicking on a SUSPENDED label. """

    cards           = mw.col.db.all(f"select id, ivl, queue, ord from cards where nid = {nid}")
    cards_html      = ""
    unsuspend_all   = ""

    note            = mw.col.getNote(int(nid))
    flds            = "<br>".join([utility.text.trim_if_longer_than(f, 100) for f in note.fields])

    for c in cards:
        templates = mw.col.getCard(c[0]).model()["tmpls"]
        if c[2] == -1:
            unsuspend_all += str(c[0]) + " "
        for t in templates:
            if t["ord"] == c[3]:
                temp_name = utility.text.trim_if_longer_than(t["name"], 60)
                break

        susp        = "<span class='bold fg-red'>Suspended</span>" if c[2] == -1 else "<span class='bold fg-green'>Not suspended</span>"
        btn         = f"<div class='siac-modal-btn' onclick='pycmd(\"siac-unsuspend {nid} {c[0]}\");'>Unsuspend</div>" if c[2] == -1 else ""
        ivl         = f"{c[1]} days" if c[1] >= 0 else f"{c[1]} seconds"
        cards_html  = f"""{cards_html}
            <tr>
                <td class='p-10 ta_center'><b>{temp_name}</b></td>
                <td class='p-10 ta_center'>{c[0]}</td>
                <td class='p-10 ta_center'>{ivl}</td>
                <td class='p-10 ta_center'>{susp}</td>
                <td class='p-10 ta_center'>{btn}</td>
            </tr>
        """
    return f"""
            <div class='flex-col oflow_hidden' style='flex: 1 0 auto; font-size: 15px;'>
                <div style='flex: 1 1 auto;'>
                    <center style='margin: 10px 0 20px 0;'>
                        <table style='margin-bottom: 50px; width: 80%;'>
                            <tr>
                                <td class='bold p-10'>Note ID</td>
                                <td>{nid}</td>
                            </tr>
                            <tr>
                                <td class='bold p-10'>Fields</td>
                                <td>{flds}</td>
                            </tr>
                        <table>
                        <table style='min-width: 500px; margin-top: 20px; width: 80%;'>
                            <thead style='border-bottom: 1px solid'>
                                <tr>
                                    <th class='p-10 ta_center'>Card template name</th>
                                    <th class='p-10 ta_center'>CID</th>
                                    <th class='p-10 ta_center'>Interval</th>
                                    <th class='p-10 ta_center'>Status</th>
                                    <th class='p-10 ta_center'>Actions</th>
                                </tr>
                            </thead>
                            <tbody style='border-bottom: 1px solid'>
                                {cards_html}
                            </tbody>
                        </table>
                        <div class='ta_right mt-10' style='width: 80%'>
                            <div class='siac-modal-btn mr-10' onclick='pycmd(\"siac-unsuspend {nid} {unsuspend_all[:-1]}\")'>Unsuspend All</div>
                        </div>
                    </center>
                </div>
            </div>
            """

