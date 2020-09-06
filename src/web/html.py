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
from ..stats import getRetentions
from ..state import get_index, check_index
from ..notes import  get_note, _get_priority_list, get_avg_pages_read, get_all_tags, get_related_notes, get_priority, dynamic_sched_to_str
from ..feeds import read
from ..internals import perf_time
from ..config import get_config_value_or_default as conf_or_def
from ..models import IndexNote
import utility.misc
import utility.tags
import utility.text


""" Html.py - various HTML-building functions. 
    Bigger UI components like the reading modal (reading_modal.py) or the sidebar (sidebar.py) contain their own HTML producing functions.
"""


def get_synonym_dialog() -> str:
    """ Returns the html for the dialog that allows input / editing of synonym sets (Settings & Info > Synonyms). """

    synonyms    = loadSynonyms()

    if not synonyms:
        return """
            <b>Synonym sets</b>
            <hr class='siac-modal-sep'/>
            <br>
            No synonyms defined yet. Input a set of terms, separated by ',' and hit enter.<br>
            If a search is triggered that at least contains one word from a synonym set, all the other words in the set will be inserted in the search query too. 
            <br/><br/>

            <input type='text' id='siac-syn-inp' onkeyup='synInputKeyup(event, this)'/>
        """

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
    return f"""
    <b>Synonym sets ({len(synonyms)})</b>
    <hr class='siac-modal-sep'/>
    If a search is triggered that at least contains one word from a synonym set, all the other words in the set will be inserted in the search query too. 
    Click inside a set to edit it.
    <br><br>
    <div style='max-height: 300px; overflow-y: auto; padding-right: 10px; margin-top: 4px;'>
        <table id='synTable' style='width: 100%; border-collapse: collapse;' class='striped'>
            <thead><tr style='margin-bottom: 20px;'><th style='word-wrap: break-word; max-width: 100px;'></th><th style='width: 100px; text-align: center;'></th></thead>
            {st}
        </table>
    </div>
    <br/>
    <span>Input a set of terms, separated by ',' and hit enter.</span>
    <input type='text' id='siac-syn-inp' onkeyup='synInputKeyup(event, this)'/>
    """

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
    search_bar_mode     = "Add-on" if not get_index() else get_index().searchbar_mode

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
        <div class='siac-col' style='width: %s%%; flex-grow: 1;' id='siac-right-side'>
            <div id='siac-second-col-wrapper'>
                <div id="greyout"></div>
                <div id="a-modal" class="modal">
                    <div class="modal-content">
                        <div id="modalText"></div>
                        <div id="modal-subpage">
                            <div style='flex: 0 0 auto;'>
                                <button class='modal-close siac-btn-small' onclick='hideModalSubpage()'>&#8592; Back</button>
                            </div>
                            <div id="modal-subpage-inner"></div>
                        </div>
                        <div style='flex: 0 0 auto; text-align: right; padding-top:15px;'>
                            <button class='modal-close siac-btn-small' onclick='$("#a-modal").hide(); hideModalSubpage();'>Close</button>
                        </div>
                    </div>
                </div>
                <div id='siac-search-modal'>
                    <div id='siac-search-modal-wrapper'>
                        <div id='siac-search-modal-header'></div>
                        <input type='text' id='siac-search-modal-inp'/>
                        <div style='text-align: center; margin-top: 10px;'>
                            <span id='siac-search-modal-close' class='siac-btn-small' onclick='document.getElementById("siac-search-modal").style.display = "none";'>&nbsp;Close &times;</span>
                        </div>
                    </div>
                </div>
                <div class="flexContainer" id="topContainer">
                    <div class='flexCol' style='margin-left: 0px; padding-bottom: 7px; padding-left: 0px;'>
                        <div id='siac-switch-deck-btn' class='siac-btn-small'  onmouseleave='$(this).removeClass("expanded")' style='display: inline-block; position: relative; min-width: 200px; width: calc(100%% - 1px); text-align: center; box-sizing: border-box;' >
                        <div class='siac-switch-deck-btn-inner' onclick="pycmd('siac-fill-deck-select')"><b>Decks</b></div>
                        <div class='siac-switch-deck-btn-inner right' onclick="pycmd('siac-fill-tag-select')"><b>Tags</b></div>
                            <div class='siac-btn-small-dropdown click'>
                                <div id='deckSelWrapper'>
                                    <div id='deck-sel-info-lbl' style='flex: 0 1 auto; margin: 5px 0 4px 5px;'><b>Only selected decks are used when searching</b></div>
                                    <div id='siac-deck-sel-btn-wrapper' style='flex: 0 1 auto; margin-top: 3px; margin-bottom: 5px; white-space: nowrap; font-size: 0;'>
                                        <div class='deck-list-button' onclick='selectAllDecks(); event.stopPropagation();'>All</div>
                                        <div class='deck-list-button' onclick='unselectAllDecks(); event.stopPropagation();'>None</div>
                                        <div class='deck-list-button' onclick="pycmd('siac-decks-select-current'); event.stopPropagation();">Current</div>
                                        <div class='deck-list-button' onclick="pycmd('siac-decks-select-current-and-subdecks'); event.stopPropagation();">Current and Subdecks</div>
                                    </div>
                                    <div id='deckSelQuickWrapper' style='flex: 0 0 auto; overflow-y: auto; max-height: 120px;'>
                                        <div style='font-weight: bold; margin: 4px 0 4px 4px;'>Recent:</div>
                                        <table id='deckSelQuick'></table>
                                    </div>
                                    <div id='siac-deck-sel-q-sep' style='display: none;'>
                                        <hr style='margin: 5px 5px 5px 5px'/>
                                    </div>
                                    <div style='flex: 1 1 auto; overflow-y: auto; margin-bottom: 10px;'>
                                        <table id='deckSel'></table>
                                    </div>
                                </div>
                             
                            </div>
                        </div>
                    </div>
                    <div class='flexCol right' style="position: relative; padding-bottom: 7px; padding-right: 0px; white-space: nowrap;">
                            <div id='siac-timetable-icn' class='siac-btn-small' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='position: relative; display:inline-block; margin-right: 6px;' onmouseenter='pycmd("siac-user-note-update-btns")' onclick='pycmd("siac-create-note");'><b>&nbsp;&nbsp;&nbsp; &#9998; Notes &nbsp;&nbsp;&nbsp;</b>
                                <div class='siac-btn-small-dropdown click'>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-create-note"); event.stopPropagation();'>&nbsp;<b>Create</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-r-user-note-newest"); event.stopPropagation();'>&nbsp;Newest</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-random"); event.stopPropagation();'>&nbsp;Random</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-search"); event.stopPropagation();'>&nbsp;Search ...</div>
                                        <hr>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-r-user-note-queue"); event.stopPropagation();' id='siac-queue-btn'>&nbsp;<b>Queue</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-head"); event.stopPropagation();'>&nbsp;<b>Read Next</b></div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-random"); event.stopPropagation();'>&nbsp;Read [Rnd]</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-url-dialog"); event.stopPropagation();'>&nbsp;Url to PDF</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-picker -1"); event.stopPropagation();'>&nbsp;Queue Man.</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-zotero-import"); event.stopPropagation();'>&nbsp;Zotero Imp.</div>
                                        <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-r-user-note-queue-random"); event.stopPropagation();'>&nbsp;List [Rnd]</div>
                                </div>
                            </div>
                            <div id='siac-settings-icn' class='siac-btn-small' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='position: relative; display:inline-block; min-width: 140px; text-align: center;'><b>&nbsp; Settings & Info &nbsp;</b>
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
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-r-show-tips");'>&nbsp;Tips</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-synonyms");'>&nbsp;Synonyms</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-styling");'>&nbsp;Settings</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='$("#a-modal").hide(); pycmd("siac_rebuild_index")'>&nbsp;Rebuild Index</div>
                                        </div>
                            </div>
                            <div id='siac-switch-lr-btn' class='siac-btn-small' onclick='switchLeftRight();' style='float: right;'>&#8596;</div>
                    </div>
                </div>
                <div id="icns-large">
                    <div class='rnd-icon' title='Read First in Queue' onclick='pycmd("siac-user-note-queue-read-head")'><i class="fa fa-inbox"></i></div>
                    <div class='rnd-icon' title='PDF Notes' onclick='pycmd("siac-r-show-pdfs")'> <i class="fa fa-file-pdf-o"></i></div>
                    <div class='rnd-icon' title='Text Notes' onclick='pycmd("siac-r-show-text-notes")'> <i class="fa fa-file-text-o"></i></div>
                    <div class='rnd-icon' title='Video Notes' onclick='pycmd("siac-r-show-video-notes")'> <i class="fa fa-file-video-o"></i></div>
                    <div class='rnd-icon' title='Toggle Sidebar' onclick='toggleNoteSidebar();'><i class="fa fa-bars"></i></div>
                    <div class='rnd-icon' title='Search for fields content' onclick='fieldsBtnClicked()'> <span class='icns-add'>FIELDS </span><i class="fa fa-search"></i></div>
                    <div class='rnd-icon' title='Random Anki Notes' onclick='pycmd("siac-r-random-notes " + siacState.selectedDecks.toString())'><i class="fa fa-random"></i></div>
                    <div class='freeze-icon' title='Freeze results' onclick='toggleFreeze(this)'> <span class='icns-add'>FREEZE </span>&#10052; </div>
                    <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                </div>
                <div id="resultsArea" style="">
                    <div id='loader' style='%s'> 
                        <div class='signal'></div>
                        <br><span style='font-size: 15px; margin-top: 20px;'>Preparing index...</span>
                    </div>
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
                                                <option value='remSuspended'>Remove Suspended</option>
                                                <option value='remUnsuspended'>Remove Unsuspended</option>
                                            </select>
                                        </div>
                                        <div class='siac-table-cell'>
                                            <div class='siac-table-cell-btn' style='margin-left: 5px;' onclick='sort();' title='%s'>GO</div>
                                        </div>
                                    </div>
                                </fieldset>

                                <fieldset id="searchMaskCol" style="flex: 1 1 auto; font-size: 0.85em;">
                                    <legend id="siac-search-inp-mode-lbl" onclick='toggleSearchbarMode(this);'>Mode: %s</legend>
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
                                                <option value='longestText'>Longest HTML</option>
                                                <option value='lastUntagged'>Newest Untagged</option>
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
                                            <div class='siac-table-cell-btn' onclick='predefSearch();' title='%s'>GO</div>
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
        onWindowResize();
         
        } else {
           var there = true;
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
        return there; 
        
        })();

    """ % (
    leftSideWidth,
    rightSideWidth,
    conf_or_def("noteScale", 1.0),
    conf_or_def("leftSideWidthInPercent", 40),
    "display: none;" if indexIsLoaded else "",
    "hidden" if hideSidebar else "",
    get_calendar_html() if conf_or_def("showTimeline", True) else "",
    conf_or_def("shortcuts.trigger_current_filter", "CTRL+K"),
    search_bar_mode,
    conf_or_def("shortcuts.trigger_predef_search", "ALT+K"),
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

def get_calendar_html() -> str:
    """ Html for the timeline at the bottom of the search pane. """

    html                    = """<div id='cal-row' style="width: 100%%; height: 8px;" onmouseleave='calMouseLeave()'>%s</div> """
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

def read_counts_card_body(counts: Dict[int, int]) -> str:
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

def topic_card_body(topics: List[Tuple[str, float]]) -> str:
    html = """
                <div style='display: flex; width: 100%; margin-top: 20px;'>
                    <div style='width: 50%; flex: 0 1 auto;'>
                        <div style='width: 100%; text-align:center;'><b>All PDFs</b></div>
                        <div id='siac-read-stats-topics-pc_1' style='width: 100%; height: 400px;'></div>
                    </div> 
                    <div style='width: 50%; flex: 0 1 auto;'>
                        <div style='width: 100%; text-align:center;'><b>Read last 7 days</b></div>
                        <div id='siac-read-stats-topics-pc_2' style='width: 100%; height: 400px;'></div>
                    </div> 
                </div> 
                """
    return html

def search_results(db_list: List[IndexNote], query_set: List[str]) -> str:
    """ Prints a list of index notes. Used e.g. in the pdf viewer. """
    html                        = ""
    epochTime                   = int(time.time() * 1000)
    timeDiffString              = ""
    newNote                     = ""
    lastNote                    = ""
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

        lastNote    = newNote
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

        text        = utility.text.cleanFieldSeparators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
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


def read_counts_by_date_card_body(counts: Dict[str, int]) -> str:
    """ Html for the card that displays read pages / day (heatmap). """

    if counts is None or len(counts) == 0:
        return """
            <center style='margin-top: 15px;'>
                <b>Nothing marked as read.</b>
            </center>
        """

    html = """<div id='siac-read-time-ch' style='width: 100%; margin: 30px auto 10px auto;'></div>"""
    return html


def get_note_delete_confirm_modal_html(nid: int) -> Optional[str]:
    """ Html for the modal that pops up when clicking on the trash icon on an add-on note. """

    note            = get_note(nid)
    if not note:
        return None
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
            <div style='text-align: center;'><div class='siac-btn-small bold' onclick='deleteNote(%s);' style='margin-right: 10px;'><div class='siac-trash-icn'></div>&nbsp;Delete&nbsp;</div><div class='siac-btn-small bold' onclick='$(this.parentNode.parentNode.parentNode).remove(); $("#greyout").hide();'>&nbsp;Cancel&nbsp;</div></div>
       </div>
    </div>
    """ % (title, creation_date, nid)


def stylingModal(config):
    html = """
            <fieldset>
                <span>Exclude note fields from search or display.</span>
                <button class='siac-btn siac-btn-small' style='float: right;' onclick='pycmd("siac-model-dialog")'>Set Fields</button>
            </fieldset>
            <br/>
            <fieldset>
            <span><mark>Important:</mark> Modify this value to scale the editor. Useful e.g. when working on a small screen. This is essentially the same as zooming in a web browser with CTRL+Mousewheel.</span>
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
                <span>Try to hide Cloze brackets in the rendered results, instead show only their contained text.</span>
                <table style="width: 100%%">
                    <tr><td><b>Hide {{c1:: ... }} Cloze brackets in output</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling results.hide_cloze_brackets ' + this.checked)" %s/></tr>
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
                <span>This controls if the add-on is displayed in the edit dialog ("Edit" from the reviewer) too. <b>Please notice</b>: This add-on does not work with multiple instances. So if you have an Add Card dialog open while you are reviewing, and then open the Edit dialog, this add-on will not work properly anymore. So if you use this option, make sure the Add Card dialog is closed during review.</span>
                <table style="width: 100%%">
                    <tr><td><b>Use in Edit</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling useInEdit ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>Show the float note button (&#10063;) in the rendered search results. <b>Needs a restart to apply.</b></span>
                <table style="width: 100%%">
                    <tr><td><b>Show Float Note Button</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling results.showFloatButton ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>Show NID/CID button (to copy the note's ID / ID of its (first) card on click) in the rendered search results. <b>Needs a restart to apply</b></span>
                <table style="width: 100%%">
                    <tr><td><b>Show NID Button</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling results.showIDButton ' + this.checked)" %s/></tr>
                </table>
                <table style="width: 100%%">
                    <tr><td><b>Show CID Button</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('siac-styling results.showCIDButton ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span class='tagLbl' style='float: none; margin-left: 0;'>Tag Colors</span>
                <table style="width: 100%%">
                    <tr><td><b>Tag Foreground Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.tagForegroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Tag Background Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.tagBackgroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Tag Foreground Color (Night Mode)</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.night.tagForegroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Tag Background Color (Night Mode)</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.night.tagBackgroundColor ' + this.value)" type="color" value="%s"></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <mark>Highlight Colors</mark>
                <table style="width: 100%%">
                    <tr><td><b>Highlight Foreground Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.highlightForegroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Highlight Background Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.highlightBackgroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Highlight Foreground Color (Night Mode)</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.night.highlightForegroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Highlight Background Color (Night Mode)</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.night.highlightBackgroundColor ' + this.value)" type="color" value="%s"></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span class='siac-susp-lbl' style='position: static; margin-left: 0;'>Suspended Label Colors</span>
                <table style="width: 100%%">
                    <tr><td><b>Suspended Foreground Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.suspendedForegroundColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Suspended Background Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.suspendedBackgroundColor ' + this.value)" type="color" value="%s"></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>Modal Border Color</span>
                <table style="width: 100%%">
                    <tr><td><b>Modal Border Color</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.modalBorderColor ' + this.value)" type="color" value="%s"></td></tr>
                    <tr><td><b>Modal Border Color (Night)</b></td><td style='text-align: right;'><input onchange="pycmd('siac-styling styles.night.modalBorderColor ' + this.value)" type="color" value="%s"></td></tr>
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
                       "checked='true'" if config["results.hide_cloze_brackets"] else "",
                       config["addonNoteDBFolderPath"],
                       config["pdfUrlImportSavePath"],
                       "checked='true'" if config["notes.showSource"] else "",
                       "checked='true'" if config["useInEdit"] else "",
                       "checked='true'" if config["results.showFloatButton"] else "",
                       "checked='true'" if config["results.showIDButton"] else "",
                       "checked='true'" if config["results.showCIDButton"] else "",
                       utility.misc.color_to_hex(config["styles.tagForegroundColor"]), 
                       utility.misc.color_to_hex(config["styles.tagBackgroundColor"]),
                       utility.misc.color_to_hex(config["styles.night.tagForegroundColor"]),
                       utility.misc.color_to_hex(config["styles.night.tagBackgroundColor"]),
                       utility.misc.color_to_hex(config["styles.highlightForegroundColor"]),
                       utility.misc.color_to_hex(config["styles.highlightBackgroundColor"]),
                       utility.misc.color_to_hex(config["styles.night.highlightForegroundColor"]),
                       utility.misc.color_to_hex(config["styles.night.highlightBackgroundColor"]),
                       utility.misc.color_to_hex(config["styles.suspendedForegroundColor"]), 
                       utility.misc.color_to_hex(config["styles.suspendedBackgroundColor"]),
                       utility.misc.color_to_hex(config["styles.modalBorderColor"]), 
                       utility.misc.color_to_hex(config["styles.night.modalBorderColor"]),
                        )
    html += """
    <br/> <br/>
    <mark>&nbsp;Important:&nbsp;</mark> At the moment, if you reset your config.json to default, your custom stopwords and synsets will be deleted. If you want to do that, I recommend saving them somewhere first.
    </div>
    """
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
        <div>
            <a class='keyword' onclick='pycmd("siac-r-pdf-last-read")'>Order by Last Read</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-last-added")'>Order by Last Added</a><br>
            <a class='keyword' onclick='pycmd("siac-r-pdf-find-invalid")'>Find Invalid Paths</a>
        </div>
       
    """
    return html

def get_tips_html() -> List[Tuple[str, str]]:
    """ Settings & Info -> Tips:  Returns a list of (title, body) pairs of html to print. """

    return [("General Tips", """
    <ol>
        <li>Look up available shortcuts in the 'Info' dialog. Most of them can be set in the config.</li>
        <li>A convenient way to quickly open a certain PDF is to use CTRL+O.</li>
        <li>Drag and drop a PDF file on the add-on pane to open the Create Note modal with that file path.</li>
        <li>CTRL/Meta + Click on a tag in the notes sidebar opens the Create Note modal with that tag.</li>
        <li>Not all settings are in the "Settings" dialog, some can be set only through Anki's add-on config dialog.</li>
        <li>On Anki 2.1.28+, the whole UI can be resized at once with CTRL+Mousewheel.</li>
        <li>There is no automatic backup function, but it is sufficient to simply copy the 'siac-notes.db' file somewhere else.</li>
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

def get_unsuspend_modal(nid):
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
        susp = "<span class='siac-susp' style='border-radius: 3px; padding: 2px 3px 2px 3px; font-weight: bold;'>SUSPENDED</span>" if c[2] == -1 else ""
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
            <center style='margin: 10px 0 20px 0;'>
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

