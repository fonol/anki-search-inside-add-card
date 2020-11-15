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
from typing import List, Tuple, Dict, Optional

from .note_templates import *
from .templating import filled_template
from ..stats import getRetentions
from ..state import get_index, check_index
from ..notes import  get_note, _get_priority_list, get_avg_pages_read, get_all_tags, get_related_notes, get_priority, dynamic_sched_to_str, get_read_today_count
from ..feeds import read
from ..internals import perf_time, HTML, JS
from ..config import get_config_value_or_default as conf_or_def
from ..models import IndexNote
import utility.misc
import utility.tags
import utility.text


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
    if ix >= 0 and index < len(existing):
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
    leftSideWidth       = conf_or_def("leftSideWidthInPercent", 40)

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
    return """
        (() => { 
            if (document.getElementById('outerWr') == null) {
                $(`#fields`).wrap(`<div class='siac-col' id='leftSide' style='flex-grow: 1; width: %s%%;'></div>`);
                $('#dupes').insertAfter('#fields');
                
                document.getElementById('topbutsleft').innerHTML += "<button id='switchBtn' onclick='showSearchPaneOnLeftSide()'>&#10149; Search</button>";
                let toInsert = `%s`;
                %s  
                $(`.siac-col`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow: hidden; height: 100%%;"></div>');
                let aFn = () => {
                    if (typeof(updatePinned) === "undefined") {
                        setTimeout(aFn, 100);
                        return;
                    }
                    updatePinned();
                    onWindowResize();
                }
                aFn();
                var there = false;
            } else {
            var there = true;
            }
            let sFn = () => {
                if (typeof(siacState) === 'undefined') {
                    setTimeout(sFn, 100);
                    return;
                } 
                if (siacState.searchOnTyping) {
                    $('.field').off('siac').on('keydown.siac', fieldKeypress);
                } 
                $('.field').attr('onmouseup', 'getSelectionText()');
                window.$fields = $('.field');
                window.$searchInfo = $('#searchInfo');
                window.addEventListener('resize', onWindowResize, true);
                $('.cal-block-outer').on('mouseenter', function(event) { calBlockMouseEnter(event, this);});
                $('.cal-block-outer').on('click', function(event) { displayCalInfo(this);});
            };
            sFn();
            return there; 
        })();
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

    html                    = """<div id='cal-row' class='w-100' style="height: 8px;" onmouseleave='calMouseLeave()'>%s</div> """
    #get notes created since the beginning of the year
    day_of_year             = datetime.datetime.now().timetuple().tm_yday
    date_year_begin         = datetime.datetime(year=datetime.datetime.utcnow().year, month=1, day=1, hour=0, minute=0)
    nid_now                 = int(time.time() * 1000)
    nid_minus_day_of_year   = int(date_year_begin.timestamp() * 1000)

    res                     = mw.col.db.all("select distinct notes.id from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc" %(nid_minus_day_of_year, nid_now))

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

        html_content += "<div class='cal-block-outer'><div class='cal-block %s %s' data-index='%s'></div></div>" % ("cal-today" if i == len(counts) - 1 else "", color, added)
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

        html = f"{html}<tr><td style='min-width: 240px;'><a class='keyword' onclick='pycmd(\"siac-read-user-note {nid}\")'>{ix}. {title}</a></td><td style='padding-left: 5px; text-align: right;'><b style='vertical-align: middle;'>{c}</b></td><td style='padding-left: 5px;'>{row}</td></tr>"
    html = f"<br><table class='siac-read-stats-table'>{html}</table>"

    html += """
    """
    return html

def topic_card_body(topics: List[Tuple[str, float]]) -> HTML:
    html = """
                <div class='flex-row w-100' style='margin-top: 20px;'>
                    <div style='width: 50%; flex: 0 1 auto;'>
                        <div class='w-100 ta_center bold'>All PDFs</div>
                        <div id='siac-read-stats-topics-pc_1' class='w-100' style='height: 400px;'></div>
                    </div> 
                    <div style='width: 50%; flex: 0 1 auto;'>
                        <div class='w-100 ta_center bold'>Read last 7 days</div>
                        <div id='siac-read-stats-topics-pc_2' class='w-100' style='height: 400px;'></div>
                    </div> 
                </div> 
                """
    return html

def search_results(db_list: List[IndexNote], query_set: List[str]) -> HTML:
    """ Prints a list of index notes. Used e.g. in the pdf viewer. """
    html                        = ""
    newNote                     = ""
    nids                        = [r.id for r in db_list]
    show_ret                    = conf_or_def("showRetentionScores", True)
    fields_to_hide_in_results   = conf_or_def("fieldsToHideInResults", {})
    hide_clozes                 = conf_or_def("results.hide_cloze_brackets", False)
    remove_divs                 = conf_or_def("removeDivsFromOutput", False)
    if show_ret:
        retsByNid               = getRetentions(nids)
    ret                         = 0
    highlighting                = conf_or_def("highlighting", True)

    for counter, res in enumerate(db_list):
        ret = retsByNid[int(res.id)] if show_ret and int(res.id) in retsByNid else None
        if ret is not None:
            retMark = "background: %s; color: black;" % (utility.misc._retToColor(ret))
            retInfo = """<div class='retMark' style='%s'>%s</div>
                            """ % (retMark, int(ret))
        else:
            retInfo = ""

        text        = res.get_content()

        # hide fields that should not be shown
        if str(res.mid) in fields_to_hide_in_results:
            text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in fields_to_hide_in_results[str(res.mid)]])

        #remove <div> tags if set in config
        if remove_divs and res.note_type != "user":
            text = utility.text.remove_divs(text)

        # remove cloze brackets if set in config
        if hide_clozes and res.note_type != "user":
            text = utility.text.hide_cloze_brackets(text)

        if highlighting and query_set is not None:
            text = utility.text.mark_highlights(text, query_set)

        text        = utility.text.clean_field_separators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
        text        = utility.text.try_hide_image_occlusion(text)
        #try to put fields that consist of a single image in their own line
        text        = utility.text.newline_before_images(text)
        template    = noteTemplateSimple if res.note_type == "index" else noteTemplateUserNoteSimple
        newNote     = template.format(
            counter=counter+1,
            nid=res.id,
            edited="",
            mouseup="",
            text=text,
            ret=retInfo,
            tags=utility.tags.build_tag_string(res.tags, False, False, maxLength = 15, maxCount = 2),
            creation="")
        html += newNote
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
        <table style='margin-top: 15px;'>
            <tr>
                <td class='siac-caps'>Avg. read pages / day:</td>
                <td><b style='margin-left: 20px;'>{avg_r}</b></td>
            </tr>
            <tr>
                <td class='siac-caps'>Most read pages on a single day:</td>
                <td><b style='margin-left: 20px;'>{v_max}</b></td>
            </tr>
        </table>
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
        <li>On Anki 2.1.28+, the whole UI can be resized at once with CTRL+Mousewheel.</li>
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
    note            = mw.col.getNote(int(nid))
    cards_html      = ""
    unsuspend_all   = ""

    for c in cards:
        templates = mw.col.getCard(c[0]).model()["tmpls"]
        if c[2] == -1:
            unsuspend_all += str(c[0]) + " "
        for t in templates:
            if t["ord"] == c[3]:
                temp_name = utility.text.trim_if_longer_than(t["name"], 60)
                break
        susp = "<span class='siac-susp bold' style='border-radius: 3px; padding: 2px 3px 2px 3px;'>SUSPENDED</span>" if c[2] == -1 else ""
        btn = f"<div class='siac-btn siac-btn-small bold' onclick='pycmd(\"siac-unsuspend {nid} {c[0]}\");'>Unsuspend</div>" if c[2] == -1 else ""
        ivl = f"{c[1]} days" if c[1] >= 0 else f"{c[1]} seconds"
        cards_html += f"""
            <tr>
                <td><b>{temp_name}</b> ({c[0]})</td>
                <td>ivl: {ivl}</td>
                <td>{susp}</td>
                <td>{btn}</td>
            </tr>
        """
    return f"""
            <div style='min-height: 250px;' class='flex-col oflow_hidden'>
                <div style='flex: 1 1 auto;'>
                    <center style='margin: 10px 0 20px 0;'>
                        <span style='font-size: 18px;'><b>{len(cards)}</b> Card(s) for Note <b>{nid}</b></span>
                        <table style='min-width: 500px; margin-top: 20px;'>
                            {cards_html}
                        </table>
                    </center>
                </div>
                <div>
                    <hr style='margin-top: 20px; margin-bottom: 20px;'>
                    <center class='mb-5'>
                        <div class='siac-btn siac-btn-small bold' onclick='pycmd(\"siac-unsuspend {nid} {unsuspend_all[:-1]}\")'>Unsuspend All</div> 
                    </center>
                </div>
            </div>
            """


def pdf_svg(w: int, h: int) -> HTML:
    return """
        <svg version="1.0" xmlns="http://www.w3.org/2000/svg"
        width="%spx" height="%spx" viewBox="0 0 225.000000 225.000000"
        preserveAspectRatio="xMidYMid meet">
        <g transform="translate(0.000000,225.000000) scale(0.100000,-0.100000)"
        fill="currentColor" stroke="none">
        <path d="M690 2099 c-29 -12 -67 -45 -83 -74 -8 -14 -14 -134 -17 -380 l-5
        -360 -120 -5 c-107 -4 -125 -8 -166 -32 -59 -35 -96 -90 -110 -163 -14 -76 -7
        -389 10 -430 15 -37 75 -101 116 -123 21 -12 65 -18 150 -22 l120 -5 5 -125
        c3 -69 11 -136 17 -150 14 -32 51 -66 86 -79 19 -7 231 -11 639 -11 l610 0 40
        22 c21 12 49 38 61 58 l22 35 0 695 c0 578 -2 699 -14 720 -29 50 -363 409
        -396 424 -29 14 -92 16 -487 15 -276 0 -463 -4 -478 -10z m890 -268 c0 -226
        -15 -210 205 -213 l170 -3 3 -664 c2 -607 1 -666 -14 -683 -16 -17 -48 -18
        -619 -18 -548 0 -604 1 -616 17 -19 22 -26 208 -9 228 11 13 76 15 434 15
        l422 0 53 26 c64 32 105 86 120 155 16 73 13 385 -3 432 -22 59 -64 107 -120
        133 l-51 24 -421 0 c-349 0 -424 2 -433 14 -18 22 -11 667 8 689 12 15 56 17
        442 17 l429 0 0 -169z m-906 -765 c51 -21 76 -60 76 -118 0 -43 -5 -55 -33
        -83 -19 -19 -46 -36 -60 -39 -15 -3 -38 -8 -52 -11 -23 -5 -25 -10 -25 -64 0
        -53 -2 -59 -23 -65 -12 -3 -33 -3 -45 1 -22 5 -22 8 -22 192 0 103 3 191 7
        194 12 13 143 7 177 -7z m400 -15 c96 -60 102 -247 11 -319 -55 -43 -198 -67
        -246 -42 -18 10 -19 23 -19 188 0 129 3 182 13 191 9 9 39 12 107 9 79 -3 102
        -8 134 -27z m366 14 c7 -8 10 -25 6 -39 -5 -22 -12 -25 -64 -28 l-57 -3 0 -35
        0 -35 52 -3 c47 -3 54 -6 59 -27 11 -43 -1 -54 -58 -57 l-53 -3 -3 -72 c-3
        -64 -5 -72 -25 -77 -13 -3 -33 -3 -45 1 -22 5 -22 8 -22 193 0 141 3 190 13
        193 6 3 51 6 98 6 65 1 90 -3 99 -14z"/>
        <path d="M928 994 c-5 -4 -8 -56 -8 -116 l0 -108 36 0 c26 0 43 8 66 30 28 29
        30 35 26 91 -3 42 -10 66 -24 80 -21 21 -84 36 -96 23z"/>
        </g>
        </svg>
    """ % (w, h)
