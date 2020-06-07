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
from typing import List, Tuple

from ..state import get_index, check_index
from ..notes import  get_note, _get_priority_list, get_avg_pages_read, get_all_tags, get_related_notes, get_priority, dynamic_sched_to_str
from ..feeds import read
from ..internals import perf_time
from ..config import get_config_value_or_default as conf_or_def
import utility.misc
import utility.tags
import utility.text


def getSynonymEditor() -> str:
    synonymEditor = """
    <b>Sets (Click inside to edit)</b>
    <div style='max-height: 300px; overflow-y: auto; padding-right: 10px; margin-top: 4px;'>
        <table id='synTable' style='width: 100%%; border-collapse: collapse;' class='striped'>
            <thead><tr style='margin-bottom: 20px;'><th style='word-wrap: break-word; max-width: 100px;'></th><th style='width: 100px; text-align: center;'></th></thead>
            %s
        </table>
    </div>
    <br/>
    <span>Input a set of terms, separated by ',' and hit enter.</span>
    <input type='text' id='siac-syn-inp' onkeyup='synInputKeyup(event, this)'/>
    """
    synonyms    = loadSynonyms()
    st          = ""
    for c, sList in enumerate(synonyms):
        st += """<tr>
                    <td>
                        <div contenteditable='true' onkeydown='synonymSetKeydown(event, this, %s)'>%s</div>
                    </td>
                    <td style='text-align: right; height: 20px;'>
                        <div class='siac-btn-smaller' onclick='pycmd(\"siac-delete-synonyms %s\")'>Del</div>
                        <div class='siac-btn-smaller' style='margin-left: 4px;' onclick='searchSynset(this)'>Search</div>
                    </td>
                </tr>""" % (c, ", ".join(sList), c)
    if not synonyms:
        return """No synonyms defined yet. Input a set of terms, separated by ',' and hit enter.<br/><br/>
        <input type='text' id='siac-syn-inp' onkeyup='synInputKeyup(event, this)'/>
        """
    return synonymEditor % st

def saveSynonyms(synonyms):
    config              = mw.addonManager.getConfig(__name__)
    filtered            = []

    for sList in synonyms:
        filtered.append(sorted(sList))

    config["synonyms"]  = filtered
    mw.addonManager.writeConfig(__name__, config)

def newSynonyms(sListStr):
    existing    = loadSynonyms()
    sList       = [utility.text.clean_synonym(s) for s in sListStr.split(",") if len(utility.text.clean_synonym(s)) > 1]
    if not sList:
        return
    found = []
    foundIndex = []
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
    saveSynonyms(existing)

def deleteSynonymSet(cmd: str):
    index = int(cmd.strip())
    existing = loadSynonyms()
    if index >= 0 and index < len(existing):
        existing.pop(index)
    saveSynonyms(existing)

def editSynonymSet(cmd: str):
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
    saveSynonyms(existing)

def loadSynonyms() -> List[List[str]]:
    config = mw.addonManager.getConfig(__name__)
    try:
        synonyms = config['synonyms']
    except KeyError:
        synonyms = []
    return synonyms


def right_side_html(indexIsLoaded: bool = False) -> str:
    """
    Returns the javascript call that inserts the html that is essentially the right side of the add card dialog.
    The right side html is only inserted if not already present, so it is safe to call this function on every note load.
    """
    leftSideWidth       = conf_or_def("leftSideWidthInPercent", 40)

    if not isinstance(leftSideWidth, int) or leftSideWidth <= 0 or leftSideWidth > 100:
        leftSideWidth = 50

    rightSideWidth      = 100 - leftSideWidth
    hideSidebar         = conf_or_def("hideSidebar", False)

    if conf_or_def("switchLeftRight", False):
        insert_code = """
            $(toInsert).insertBefore('#leftSide');
            $(document.body).addClass('siac-left-right-switched');
        """
    else:
        insert_code = """
            $(toInsert).insertAfter('#leftSide');   
        """
  
    return """
        //check if ui has been rendered already
        (() => { 
        if (!$('#outerWr').length) {
        $(`#fields`).wrap(`<div class='siac-col' id='leftSide' style='flex-grow: 1; width: %s%%;'></div>`);
        document.getElementById('topbutsleft').innerHTML += "<button id='switchBtn' onclick='showSearchPaneOnLeftSide()'>&#10149; Search</button>";
        let toInsert = `
        <div class='siac-col' style='width: %s%%; flex-grow: 1; zoom: %s' id='siac-right-side'>
            <div id='siac-second-col-wrapper'>
                <div id="greyout"></div>
                <div id="a-modal" class="modal">
                    <div class="modal-content">
                        <div id="modalText"></div>
                        <div id="modal-subpage">
                            <div style='flex: 0 0 auto;'>
                                <button class='modal-close siac-btn' onclick='hideModalSubpage()'>&#8592; Back</button>
                            </div>
                            <div id="modal-subpage-inner"></div>
                        </div>
                        <div style='flex: 0 0 auto; text-align: right; padding-top:15px;'>
                            <button class='modal-close siac-btn' onclick='$("#a-modal").hide(); hideModalSubpage();'>Close</button>
                        </div>
                    </div>
                </div>
                <div id='siac-search-modal'>
                    <div id='siac-search-modal-wrapper'>
                        <div id='siac-search-modal-header'></div>
                        <input type='text' id='siac-search-modal-inp'/>
                        <span id='siac-search-modal-close' onclick='document.getElementById("siac-search-modal").style.display = "none";'>&nbsp;Close &times;</span>
                    </div>
                </div>
                <div class="flexContainer" id="topContainer">
                    <div class='flexCol' style='margin-left: 0px; padding-bottom: 7px; padding-left: 0px;'>
                        <div id='siac-switch-deck-btn' class='siac-btn-small'  onmouseleave='$(this).removeClass("expanded")' style='display: inline-block; position: relative; min-width: 200px; width: calc(100%% - 1px); text-align: center; box-sizing: border-box;' >
                        <div class='siac-switch-deck-btn-inner' onclick="pycmd('siac-fill-deck-select')"><b>Decks</b></div>
                        <div class='siac-switch-deck-btn-inner right' onclick="pycmd('siac-fill-tag-select')"><b>Tags</b></div>
                            <div class='siac-btn-small-dropdown click'>
                                <div id='deckSelWrapper'>
                                    <div id='deck-sel-info-lbl' style='margin: 5px 0 4px 5px;'><i>Only selected decks are used when searching:</i></div>
                                    <div id='deckSelQuickWrapper'>
                                        <div style='font-weight: bold; margin: 4px 0 4px 4px;'>Recent:</div>
                                        <table id='deckSelQuick'></table>
                                        <hr style='margin: 5px 5px 5px 5px'/>
                                    </div>
                                    <table id='deckSel'></table>
                                </div>
                                <div id='siac-deck-sel-btn-wrapper' style='margin-top: 3px; margin-bottom: 5px; white-space: nowrap; font-size: 0;'>
                                    <div class='deck-list-button' onclick='selectAllDecks(); event.stopPropagation();'>All</div>
                                    <div class='deck-list-button center' onclick='unselectAllDecks(); event.stopPropagation();'>None</div>
                                    <div class='deck-list-button' onclick="pycmd('selectCurrent'); event.stopPropagation();">Current</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class='flexCol right' style="position: relative; padding-bottom: 7px; padding-right: 0px; white-space: nowrap;">
                            <div id='siac-timetable-icn' class='siac-btn-small' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='position: relative; display:inline-block; margin-right: 6px;' onmouseenter='pycmd("siac-user-note-update-btns")' onclick='pycmd("siac-create-note");'>&nbsp;&nbsp;&nbsp; &#9998; Notes &nbsp;&nbsp;&nbsp;
                                <div class='siac-btn-small-dropdown click'>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-create-note"); event.stopPropagation();'>&nbsp;<b>Create</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-newest"); event.stopPropagation();'>&nbsp;Newest</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-random"); event.stopPropagation();'>&nbsp;Random</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-search"); event.stopPropagation();'>&nbsp;Search ...</div>
                                        <hr>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue"); event.stopPropagation();' id='siac-queue-btn'>&nbsp;<b>Queue</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-head"); event.stopPropagation();'>&nbsp;<b>Read Next</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-random"); event.stopPropagation();'>&nbsp;Read [Rnd]</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-url-dialog"); event.stopPropagation();'>&nbsp;Url to PDF</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-zotero-import"); event.stopPropagation();'>&nbsp;Zotero Imp.</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-random"); event.stopPropagation();'>&nbsp;List [Rnd]</div>
                                </div>
                            </div>
                            <div id='siac-settings-icn' class='siac-btn-small' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='position: relative; display:inline-block; min-width: 140px; text-align: center; '>&nbsp; Settings & Info &nbsp;
                                        <div class='siac-btn-small-dropdown click' onclick='event.stopPropagation();' >
                                                <table style='width: 100%%;'>
                                                    <tr><td class='tbLb'><label class='blue-hover' for='selectionCb'>Search on Selection</label></td><td><input type='checkbox' id='selectionCb' checked onchange='siacState.searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                                                    <tr><td class='tbLb'><label class='blue-hover' for='typingCb'>Search on Typing</label></td><td><input type='checkbox' id='typingCb' checked onchange='setSearchOnTyping($(this).is(":checked"));'/></td></tr>
                                                    <tr><td class='tbLb'><label for='highlightCb'><mark>&nbsp;Highlighting&nbsp;</mark></label></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                                                    <tr><td class='tbLb'><label class='blue-hover' for='gridCb'>Grid</label></td><td><input type='checkbox' id='gridCb' onchange='toggleGrid(this)'/></td></tr>
                                                </table>
                                                <span>Note Scale</span>
                                                <hr>
                                                <input type='range' min='0.5' max='1.5' step='0.1' value='%s' list='siac-scale-tickmarks' onfocusout='pycmd("siac-scale " + this.value)'/>
                                                <datalist id="siac-scale-tickmarks">
                                                    <option value="0.5" label="0.5"></option>
                                                    <option value="0.6"></option>
                                                    <option value="0.7"></option>
                                                    <option value="0.8"></option>
                                                    <option value="0.9"></option>
                                                    <option value="1.0" label="1.0"></option>
                                                    <option value="1.1"></option>
                                                    <option value="1.2"></option>
                                                    <option value="1.3"></option>
                                                    <option value="1.4"></option>
                                                    <option value="1.5" label="1.5"></option>
                                                </datalist>
                                                <br>
                                                <span>Fields - Add-on</span>
                                                <hr>
                                                <input id='siac-partition-slider' type='range' min='0' max='100' step='1' value='%s' onchange='pycmd("siac-left-side-width " + this.value)'/>
                                                <br>
                                                <span>Menus</span>
                                                <hr>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-index-info");'>&nbsp;Info</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-synonyms");'>&nbsp;Synonyms</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-styling");'>&nbsp;Settings</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='$("#a-modal").hide(); pycmd("siac_rebuild_index")'>&nbsp;Rebuild Index</div>
                                        </div>
                            </div>
                            <div id='siac-switch-lr-btn' class='siac-btn-small' onclick='switchLeftRight();' style='float: right;'>&#8596;</div>
                    </div>
                </div>
                <div id="icns-large">
                    <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                    <div class='freeze-icon' onclick='toggleFreeze(this)'> <span class='icns-add'>FREEZE </span>&#10052; </div>
                    <div class='rnd-icon' onclick='pycmd("siac-random-notes " + siacState.selectedDecks.toString())'> <span class='icns-add'>RANDOM </span>&#9861; </div>
                    <div class='flds-icon' onclick='fieldsBtnClicked()'> <span class='icns-add'>FIELDS </span>&#9744; </div>
                    <div class='pdf-icon' onclick='pycmd("siac-show-pdfs")'>
                        %s
                    </div>
                    <div class='rnd-icon' onclick='toggleNoteSidebar();'>NOTES</div>
                    <div class='siac-read-icn' onclick='pycmd("siac-user-note-queue-read-head")'></div>
                </div>
                <div id="resultsArea" style="">
                    <div id='loader' style='%s'> <div class='signal'></div><br/>Preparing index...</div>
                    <div id='resultsWrapper'>
                        <div id='searchResults'></div>
                        <div id='searchInfo' class='%s'></div>
                    </div>
                </div>
                <div id='bottomContainer' style='display: block;'>
                    <div id='siac-pagination'>
                        <div id='siac-pagination-status'></div>
                        <div id='siac-pagination-wrapper'>&nbsp;</div>
                        <div id='siac-cache-displ'></div>
                    </div>
                    <div style='position: relative;' id='cal-wrapper'>
                        %s
                    </div>
                    <div class="flexContainer">
                        <div class='flexCol' style='padding-left: 0px; padding-top: 3px; '>
                            <div class='flexContainer' style="flex-wrap: nowrap;">
                                <fieldset id="sortCol" style="flex: 0 0 auto; font-size: 0.85em;">
                                    <legend>Sorting & Filtering</legend>
                                    <div class='siac-table-container' style='height: 20px;'>
                                        <div class='siac-table-cell'>
                                            <select id='sortSelect' class='h-100'>
                                                <option value='newest' selected='true'>Sort By Newest</option>
                                                <option value='oldest' selected='true'>Sort By Oldest</option>
                                                <option value='remUntagged'>Remove Untagged</option>
                                                <option value='remTagged'>Remove Tagged</option>
                                                <option value='remUnreviewed'>Remove Unreviewed</option>
                                                <option value='remReviewed'>Remove Reviewed</option>
                                            </select>
                                        </div>
                                        <div class='siac-table-cell'>
                                            <div class='siac-table-cell-btn' style='margin-left: 5px;' onclick='sort();'>GO</div>
                                        </div>
                                    </div>
                                </fieldset>

                                <fieldset id="searchMaskCol" style="flex: 1 1 auto; font-size: 0.85em;">
                                    <legend id="siac-search-inp-mode-lbl" onclick='toggleSearchbarMode(this);'>Mode: Add-on</legend>
                                    <span class='siac-search-icn' style='width: 16px; height: 16px; background-size: 16px 16px;'></span>
                                    <input id='siac-browser-search-inp' placeholder='' onkeyup='searchMaskKeypress(event)'></input>
                                </fieldset>

                                <fieldset id="predefCol" style="flex: 0 0 auto; font-size: 0.85em;">
                                    <legend>Predefined Searches</legend>
                                    <div class='siac-table-container' style='height: 20px;'>
                                        <div class='siac-table-cell'>
                                            <select id='predefSearchSelect' class='h-100'>
                                                <option value='lastAdded' selected='true'>Last Added</option>
                                                <option value='firstAdded'>First Added</option>
                                                <option value='lastModified'>Last Modified</option>
                                                <option value='lastReviewed'>Last Reviewed</option>
                                                <option value='lastLapses'>Last Lapses</option>
                                                <option value='highestPerf'>Performance (desc.)</option>
                                                <option value='lowestPerf'>Performance (asc.)</option>
                                                <option value='highestRet'>Pass Rate (desc.)</option>
                                                <option value='lowestRet'>Pass Rate (asc.)</option>
                                                <option value='longestTime'>Time Taken (desc.)</option>
                                                <option value='shortestTime'>Time Taken (asc.)</option>
                                                <option value='highestInterval'>Interval (desc.)</option>
                                                <option value='lowestInterval'>Interval (asc.)</option>
                                                <option value='longestText'>Longest Text</option>
                                                <option value='randomUntagged'>Random Untagged</option>
                                            </select>
                                        </div>
                                        <div class='siac-table-cell'>
                                            <select id='predefSearchNumberSel' class='h-100'>
                                                <option value='10'>10</option>
                                                <option value='50' selected='true'>50</option>
                                                <option value='100'>100</option>
                                                <option value='200'>200</option>
                                                <option value='500'>500</option>
                                            </select>
                                        </div>
                                        <div class='siac-table-cell'>
                                            <div class='siac-table-cell-btn' onclick='predefSearch();'>GO</div>
                                        </div>
                                    </div>
                                </fieldset>
                            </div>
                        </div>
                    </div>
                </div>
                <div id='cal-info' onmouseleave='calMouseLeave()'></div>
                <div id='siac-reading-modal'></div>
            </div>
        </div>
        `;
        %s  
        $(`.siac-col`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow: hidden; height: 100%%;"></div>');
        updatePinned();
        var there = false;
         
        } else {
           var there = true;
        }
        if (siacState.searchOnTyping) {
            $('.field').off('siac').on('keyup.siac', fieldKeypress);
        } 
        $('.field').attr('onmouseup', 'getSelectionText()');
        window.$fields = $('.field');
        window.$searchInfo = $('#searchInfo');
        onWindowResize();
        window.addEventListener('resize', onWindowResize, true);
        $('.cal-block-outer').on('mouseenter', function(event) { calBlockMouseEnter(event, this);});
        $('.cal-block-outer').on('click', function(event) { displayCalInfo(this);});
        return there; 
        
        })();

    """ % (
    leftSideWidth,
    rightSideWidth,
    conf_or_def("searchpane.zoom", 1.0),
    conf_or_def("noteScale", 1.0),
    conf_or_def("leftSideWidthInPercent", 40),
    pdf_svg(15, 18),
    "display: none;" if indexIsLoaded else "",
    "hidden" if hideSidebar else "",
    getCalendarHtml() if conf_or_def("showTimeline", True) else "",
    insert_code
    )


def get_model_dialog_html() -> str:
    """ Returns the html for the "Fields" section in the settings modal. """

    all_models  = sorted(mw.col.models.all(), key=lambda m : m['name'])
    index       = get_index()
    config      = mw.addonManager.getConfig(__name__)

    html        = """
    <div style='flex: 0 0 auto;'>
        <p>Changes in <i>Show Field in Results</i> take effect immediately, changes in <i>Search in Field</i> need a rebuild of the index.</p>
    </div>
    <div style='flex: 0 0 auto;'>
        <table style='width: 100%; margin: 10px 0 5px 0;'>
            <tr>
                <td style='width: 80%; font-weight: bold;'>Field Name</td>
                <td style='width: 10%; font-weight: bold;'>Search in Field</td>
                <td style='width: 10%; font-weight: bold;'>Show Field in Results</td>
            </tr>
        </table>
    </div>
    <div style='overflow-y: auto; flex: 1 1 auto; width: 100%'><div class='h-100'>
    """
    for m in all_models:
        html += "<div class='siac-model-name'>%s</div>" % utility.text.trim_if_longer_than(m["name"], 40)
        flds = "<table class='siac-model-table'>"
        for f in m["flds"]:
            flds += """<tr>
                            <td style='width: 80%%' class='siac-model-field'>%s</td>
                            <td style='width: 10%%; text-align: center;'><input type='checkbox' onchange='updateFieldToExclude(this, "%s", %s)' %s/></td>
                            <td style='width: 10%%; text-align: center;'><input type='checkbox' onchange='updateFieldToHideInResult(this, "%s", %s)' %s/></td>
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

def getCalendarHtml() -> str:
    """ Html for the timeline at the bottom of the search pane. """

    html                    = """<div id='cal-row' style="width: 100%%; height: 8px;" onmouseleave='calMouseLeave()'>%s</div> """
    #get notes created since the beginning of the year
    day_of_year             = datetime.datetime.now().timetuple().tm_yday
    date_year_begin         = datetime.datetime(year=datetime.datetime.utcnow().year, month=1, day=1, hour=0, minute=0)
    nid_now                 = int(time.time() * 1000)
    nid_minus_day_of_year   = int(date_year_begin.timestamp() * 1000)

    res                     = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc" %(nid_minus_day_of_year, nid_now))

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
            notes_in_current_day = 1
            for _ in range(0, c_day_of_year - c - 1):
                counts.append(0)

        c = c_day_of_year
    while len(counts) < day_of_year:
        counts.append(0)

    html_content = ""
    added = 0
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

def get_note_delete_confirm_modal_html(nid: int) -> str:
    """ Html for the modal that pops up when clicking on the trash icon on an add-on note. """

    note            = get_note(nid)
    creation_date   = note.created
    title           = utility.text.trim_if_longer_than(note.get_title(), 100) 

    return """

    <div id='siac-del-modal' style='position: absolute; left: 0; right: 0; top: 0; bottom: 0; z-index: 5; height: 100%%; text-align: center; background: rgba(0,0,0,0.4); display:flex; align-items: center; justify-content: center; border-radius: 5px;'>
       <div class='siac-modal-small'>
            <p style='text-align: center; font-size: 14px;'><b>Delete the following note?</b></p>
            <hr class='siac-modal-sep'/>
            <br>
            <div style='text-align: center; font-size: 14px; margin-bottom: 4px;'><b>%s</b></div>
            <div style='text-align: center; font-size: 14px;'><i>%s</i></div>
            <br><br>
            <div style='text-align: center;'><div class='siac-btn' onclick='removeNote(%s);deleteNote(%s);' style='margin-right: 10px;'><div class='siac-trash-icn'></div>&nbsp;Delete&nbsp;</div><div class='siac-btn' onclick='$(this.parentNode.parentNode.parentNode).remove(); $("#greyout").hide();'>&nbsp;Cancel&nbsp;</div></div>
       </div>
    </div>
    """ % (title, creation_date, nid, nid)


def stylingModal(config):
    html = """
            <fieldset>
                <span>Exclude note fields from search or display.</span>
                <button class='siac-btn siac-btn-small' style='float: right;' onclick='pycmd("siac-model-dialog")'>Set Fields</button>
            </fieldset>
            <br/>
            <fieldset>
            <span><mark>Important:</mark> Modify this value to scale the whole search pane. Useful e.g. when working on a small screen.</span>
                <table style="width: 100%%">
                    <tr><td><b>Zoom</b></td><td style='text-align: right;'><input placeholder="" type="number" step="0.1" style='width: 60px;' onchange="pycmd('siac-styling searchpane.zoom ' + this.value)" value="%s"/></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>Controls whether the results are faded in or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Render Immediately</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling renderImmediately ' + this.checked)" %s/></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls how the window is split into search pane and field input. A value of 40 means the left side will take 40%% and the right side will take 60%%.</span>
                <table style="width: 100%%">
                    <tr><td><b>Left Side Width</b></td><td style='text-align: right;'><input placeholder="Value in px" type="number" min="0" max="100" style='width: 60px;' onchange="pycmd('siac-styling leftSideWidthInPercent ' + this.value)" value="%s"/> %%</td></tr>
                </table>
            </fieldset>
             <br/>
            <fieldset>
                <span>This controls whether the sidebar (containing the tags and found keywords) is visible or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Hide Sidebar</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling hideSidebar ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
             <br/>
              <fieldset>
                <span>This controls whether the timeline row (added notes over the year) is visible or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Show Timeline</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling showTimeline ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
              <fieldset>
                <span>This controls whether the small info box will be shown when a tag is hovered over with the mouse. Currently only works with the default scaling.</span>
                <table style="width: 100%%">
                    <tr><td><b>Show Tag Info on Hover</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling showTagInfoOnHover ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls how long you have to hover over a tag until the info box is shown. Allowed values are 0 (not recommended) to 10000.</span>
                <table style="width: 100%%">
                    <tr><td><b>Tag Hover Delay in Miliseconds</b></td><td style='text-align: right;'><input placeholder="Value in ms" type="number" min="0" max="10000" style='width: 60px;' onchange="pycmd('siac-styling tagHoverDelayInMiliSec ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>If the number of notes that would go into the index (only notes from the included decks are counted) is lower than this value the index should always be rebuilt.</span>
                <table style="width: 100%%">
                    <tr><td><b>Always Rebuild Index If Smaller Than</b></td><td style='text-align: right;'><input placeholder="Value in ms" type="number" min="0" max="100000" style='width: 60px;' onchange="pycmd('siac-styling alwaysRebuildIndexIfSmallerThan ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>If you have problems with the display of search results (e.g. notes nested into each other), most likely, your note's html contains at least one unmatched opening/closing &lt;div&gt; tag. If set to true, this setting will remove all div tags from the note html before displaying.</span>
                <table style="width: 100%%">
                    <tr><td><b>Remove &lt;div&gt; Tags from Output</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling removeDivsFromOutput ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This is the absolute path to the folder where the addon should store its notes. If not present already, the addon will create a file named <i>siac-notes.db</i> in that folder. If empty, user_files will be used.
                <br>If you have existing data, after changing this value, you should close Anki, copy your existing <i>siac-notes.db</i> to that new location, and then start again.
                </span>
                <table style="width: 100%%">
                    <tr><td><b>Addon Note DB Folder Path</b></td><td style='text-align: right;'><input type="text"  style='min-width: 250px;' onfocusout="pycmd('siac-styling addonNoteDBFolderPath ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This is the location where PDFs generated from URLs will be saved. This needs to be set for the URL import to work.</span>
                <table style="width: 100%%">
                    <tr><td><b>PDF Url-Import Save Path</b></td><td style='text-align: right;'><input type="text" style='min-width: 250px;' onfocusout="pycmd('siac-styling pdfUrlImportSavePath ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls if the addon's notes shall be displayed with their source field (on the bottom: "Source: ..."), or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Notes - Show Source</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling notes.showSource ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls if the add-on is displayed in the edit dialog ("Edit Current" from the reviewer) too.</span>
                <table style="width: 100%%">
                    <tr><td><b>Use in Edit</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling useInEdit ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <div style='text-align: center'><mark>For other settings, see the <em>config.json</em> file.</mark></div>
                        """ % (
                        config["searchpane.zoom"],
                        "checked='true'" if config["renderImmediately"] else "",
                        config["leftSideWidthInPercent"],
                        "checked='true'" if config["hideSidebar"] else "",
                        "checked='true'" if config["showTimeline"] else "",
                        "checked='true'" if config["showTagInfoOnHover"] else "",
                        config["tagHoverDelayInMiliSec"],
                       config["alwaysRebuildIndexIfSmallerThan"],
                       "checked='true'" if config["removeDivsFromOutput"] else "",
                       config["addonNoteDBFolderPath"],
                       config["pdfUrlImportSavePath"],
                       "checked='true'" if config["notes.showSource"] else "",
                       "checked='true'" if config["useInEdit"] else ""
                        )
    html += """
    <br/> <br/>
    <mark>&nbsp;Important:&nbsp;</mark> At the moment, if you reset your config.json to default, your custom stopwords and synsets will be deleted. If you want to do that, I recommend saving them somewhere first.
    <br/> <br/>
    If you want to use the add-on with Anki's <b>built-in night mode</b> the <b>night mode</b> add-on, you have to adapt the styling section.
    <br/> <br/>
    <b>Sample night mode color scheme:</b> <div class='siac-btn' style='margin-left: 15px;' onclick='pycmd("siac-styling default night");'>Apply</div><br/><br/>
    <div style='width: 100%%; overflow-y: auto; max-height: 150px; opacity: 0.7;'>
    "styling": %s,
    </div>
    <br/> <br/>
    <b>Default color scheme:</b><div class='siac-btn' style='margin-left: 15px;' onclick='pycmd("siac-styling default day")'>Apply</div><br/><br/>
    <div style='width: 100%%; overflow-y: auto; max-height: 150px; opacity: 0.7;'>
    "styling": %s,
    </div>

    """ % (default_night_mode_styles(), default_styles())
    return html


def get_loader_html(text):
    html = """
        <div class='siac-modal-small'>
            <div> <div class='signal'></div><br/>%s</div>
        </div>
    """ % text
    return html

def default_styles():
    return """
        {
        "modal" : {
            "stripedTableBackgroundColor": "#f2f2f2",
            "modalForegroundColor": "black",
            "modalBackgroundColor": "white",
            "modalBorderColor": "#2496dc"
        },
        "general" : {
            "tagForegroundColor": "white",
            "tagBackgroundColor": "#f0506e",
            "tagFontSize" : 12,
            "buttonBackgroundColor": "white",
            "buttonForegroundColor": "#404040",
            "buttonBorderColor":"#404040",
            "keywordColor": "#2496dc",
            "highlightBackgroundColor": "yellow",
            "highlightForegroundColor": "black",
            "fieldSeparatorColor" : "#2496dc",
            "windowColumnSeparatorColor" : "lightseagreen",
            "rankingLabelBackgroundColor": "lightseagreen",
            "rankingLabelForegroundColor": "white",
            "noteFontSize": 12,
            "noteForegroundColor": "black",
            "noteBackgroundColor": "white",
            "noteBorderColor": "lightseagreen",
            "noteHoverBorderColor": "#2496dc"
        },
        "topBar": {
            "deckSelectFontSize": 11,
            "deckSelectForegroundColor": "black",
            "deckSelectBackgroundColor": "white",
            "deckSelectHoverForegroundColor": "white",
            "deckSelectHoverBackgroundColor": "#5f6468",
            "deckSelectButtonForegroundColor": "grey",
            "deckSelectButtonBorderColor": "grey",
            "deckSelectButtonBackgroundColor": "white",
            "deckSelectCheckmarkColor" : "green"
        },
        "bottomBar" : {
            "browserSearchInputForegroundColor": "black",
            "browserSearchInputBackgroundColor": "white",
            "browserSearchInputBorderColor": "grey",
            "selectForegroundColor" : "black",
            "selectBackgroundColor": "white",
            "timelineBoxBackgroundColor": "#595959",
            "timelineBoxBorderColor": "#595959"
        }
    }
    """

def default_night_mode_styles():
    return """
        {
        "bottomBar": {
            "browserSearchInputBackgroundColor": "#2f2f31",
            "browserSearchInputBorderColor": "grey",
            "browserSearchInputForegroundColor": "beige",
            "selectBackgroundColor": "#2f2f31",
            "selectForegroundColor": "white",
            "timelineBoxBackgroundColor": "#2b2b30",
            "timelineBoxBorderColor": "darkorange"
        },
        "general": {
            "buttonBackgroundColor": "#2f2f31",
            "buttonBorderColor": "grey",
            "buttonForegroundColor": "lightgrey",
            "fieldSeparatorColor": "white",
            "highlightBackgroundColor": "SpringGreen",
            "highlightForegroundColor": "Black",
            "keywordColor": "SpringGreen",
            "noteBackgroundColor": "#2f2f31",
            "noteBorderColor": "lightseagreen",
            "noteFontSize": 12,
            "noteForegroundColor": "beige",
            "noteHoverBorderColor": "#62C9C3",
            "rankingLabelBackgroundColor": "darkorange",
            "rankingLabelForegroundColor": "Black",
            "tagBackgroundColor": "darkorange",
            "tagFontSize": 12,
            "tagForegroundColor": "Black",
            "windowColumnSeparatorColor": "darkorange"
        },
        "modal": {
            "modalBackgroundColor": "#2f2f31",
            "modalBorderColor": "darkorange",
            "modalForegroundColor": "beige",
            "stripedTableBackgroundColor": "#2b2b30"
        },
        "topBar": {
            "deckSelectBackgroundColor": "#2f2f31",
            "deckSelectButtonBackgroundColor": "#2f2f31",
            "deckSelectButtonBorderColor": "grey",
            "deckSelectButtonForegroundColor": "beige",
            "deckSelectCheckmarkColor": "LawnGreen",
            "deckSelectFontSize": 11,
            "deckSelectForegroundColor": "beige",
            "deckSelectHoverBackgroundColor": "darkorange",
            "deckSelectHoverForegroundColor": "Black"
        }
    }
    """

def get_pdf_list_first_card():
    """
        Returns the html for the body of a card that is displayed at first position when clicking on "PDFs".
    """
    html = """
        <div style='width: calc(50%% - 30px); box-sizing: border-box; display: inline-block;'>
            <a class='keyword' onclick='pycmd("siac-pdf-last-read")'>Order by Last Read</a><br>
            <a class='keyword' onclick='pycmd("siac-pdf-last-added")'>Order by Last Added</a><br>
            <a class='keyword' onclick='pycmd("siac-pdf-find-invalid")'>Find Invalid Paths</a>
        </div>
        <div style='width: calc(50%%- 30px); box-sizing: border-box; display: inline-block;'>
            <p>
            Avg. Pages Read (Last 7 Days): <b>%s</b>
            </p>
        </div>
    """ % (get_avg_pages_read(7))
    return html

def get_unsuspend_modal(nid):
    """
        Returns the html content for the modal that is opened when clicking on a SUSPENDED label.
    """
    cards = mw.col.db.all(f"select id, ivl, queue, ord from cards where nid = {nid}")
    note = mw.col.getNote(nid)
    templates = mw.col.findTemplates(note)
    cards_html = ""
    unsuspend_all = ""
    for c in cards:
        if c[2] == -1:
            unsuspend_all += str(c[0]) + " "
        for t in templates:
            if t["ord"] == c[3]:
                temp_name = utility.text.trim_if_longer_than(t["name"], 60)
                break
        susp = "<span style='background: orange; color: black; border-radius: 3px; padding: 2px 3px 2px 3px;'>SUSPENDED</span>" if c[2] == -1 else ""
        btn = f"<div class='siac-btn' onclick='pycmd(\"siac-unsuspend {nid} {c[0]}\");'>Unsuspend</div>" if c[2] == -1 else ""
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
            <center>
                <b>{len(cards)}</b> Card(s) for Note <b>{nid}</b> 
                <table style='min-width: 500px; margin-top: 20px;'>
                    {cards_html}
                </table>
            </center>
            <hr style='margin-top: 20px; margin-bottom: 20px;'>
            <center>
                <div class='siac-btn' onclick='pycmd(\"siac-unsuspend {nid} {unsuspend_all[:-1]}\")'>Unsuspend All</div> 
            </center>
            """


def pdf_svg(w, h):
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

def clock_svg(greyout):
    greyout = "grey" if greyout else ""
    return f"""
<svg  class='siac-sched-icn {greyout}'  width="12" height="12" xmlns="http://www.w3.org/2000/svg">
 <g>
  <rect fill="none" id="canvas_background" height="14" width="14" y="-1" x="-1"/>
 </g>
 <g>
  <ellipse stroke="#000" ry="4.97339" rx="4.88163" id="svg_2" cy="5.91646" cx="6.192696" fill="none"/>
  <line stroke-linecap="null" stroke-linejoin="null" id="svg_3" y2="6.338556" x2="6.009176" y1="2.961789" x1="6.009176" fill-opacity="null" stroke-opacity="null" stroke="#000" fill="none"/>
  <line stroke-linecap="null" stroke-linejoin="null" id="svg_4" y2="6.522076" x2="9.606167" y1="6.55878" x1="6.04588" fill-opacity="null" stroke-opacity="null" stroke="#000" fill="none"/>
  <line stroke-linecap="null" stroke-linejoin="null" id="svg_5" y2="6.999228" x2="5.788952" y1="6.37526" x1="6.009176" fill-opacity="null" stroke-opacity="null" stroke="#000" fill="none"/>
 </g>
</svg>
    """

