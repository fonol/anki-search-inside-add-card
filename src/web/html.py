import platform
import os
import json
import re
import datetime
import time
from aqt import mw

from ..state import get_index, check_index
from ..notes import get_note, _get_priority_list, get_avg_pages_read, get_all_tags, get_related_notes
from ..feeds import read
from ..internals import perf_time
from ..config import get_config_value_or_default as conf_or_def
import utility.misc
import utility.tags
import utility.text


def getSynonymEditor():
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
    <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
    """
    synonyms = loadSynonyms()
    st = ""
    for c, sList in enumerate(synonyms):
        st += """<tr>
                    <td>
                        <div contenteditable='true' onkeydown='synonymSetKeydown(event, this, %s)'>%s</div>
                    </td>
                    <td style='text-align: right; height: 20px;'>
                        <div class='siac-btn-smaller' onclick='pycmd(\"deleteSynonyms %s\")'>Del</div>
                        <div class='siac-btn-smaller' style='margin-left: 4px;' onclick='searchSynset(this)'>Search</div>
                    </td>
                </tr>""" % (c, ", ".join(sList), c)
    if not synonyms:
        return """No synonyms defined yet. Input a set of terms, separated by ',' and hit enter.<br/><br/>
        <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
        """
    return synonymEditor % st

def saveSynonyms(synonyms):
    config = mw.addonManager.getConfig(__name__)
    filtered = []
    for sList in synonyms:
        filtered.append(sorted(sList))
    config["synonyms"] = filtered
    mw.addonManager.writeConfig(__name__, config)

def newSynonyms(sListStr):
    existing = loadSynonyms()
    sList = [utility.text.clean_synonym(s) for s in sListStr.split(",") if len(utility.text.clean_synonym(s)) > 1]
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

def deleteSynonymSet(cmd):
    index = int(cmd.strip())
    existing = loadSynonyms()
    if index >= 0 and index < len(existing):
        existing.pop(index)
    saveSynonyms(existing)

def editSynonymSet(cmd):
    index = int(cmd.strip().split()[0])
    existing = loadSynonyms()
    existing.pop(index)
    sList = [utility.text.clean_synonym(s) for s in cmd[len(cmd.strip().split()[0]):].split(",") if len(utility.text.clean_synonym(s)) > 1]
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

def loadSynonyms():
    config = mw.addonManager.getConfig(__name__)
    try:
        synonyms = config['synonyms']
    except KeyError:
        synonyms = []
    return synonyms


def right_side_html(indexIsLoaded = False):
    """
    Returns the javascript call that inserts the html that is essentially the right side of the add card dialog.
    The right side html is only inserted if not already present, so it is safe to call this function on every note load.
    """
    addToResultAreaHeight = int(conf_or_def("addToResultAreaHeight", 0))
    leftSideWidth = conf_or_def("leftSideWidthInPercent", 40)
    if not isinstance(leftSideWidth, int) or leftSideWidth <= 0 or leftSideWidth > 100:
        leftSideWidth = 50
    rightSideWidth = 100 - leftSideWidth
    hideSidebar = conf_or_def("hideSidebar", False)

    return """

        //check if ui has been rendered already
        if (!$('#outerWr').length) {

        $(`#fields`).wrap(`<div class='siac-col' id='leftSide' style='flex-grow: 1; width: %s%%;'></div>`);
        document.getElementById('topbutsleft').innerHTML += "<button id='switchBtn' onclick='showSearchPaneOnLeftSide()'>&#10149; Search</button>";
        $(`
        <div class='siac-col' style='width: %s%%; flex-grow: 1;  height: 100vh; zoom: %s' id='siac-right-side'>
            <div id='siac-second-col-wrapper'>
                <div id="greyout"></div>
                <div id="a-modal" class="modal">
                    <div class="modal-content">
                        <div id='modal-visible'>
                        <div id="modalText"></div>
                        <div id="modal-subpage">
                            <button class='modal-close siac-btn' onclick='hideModalSubpage()'>&#8592; Back</button>
                            <div id="modal-subpage-inner"></div>
                        </div>
                        <div style='text-align: right; margin-top:25px;'>
                            <button class='modal-close siac-btn' onclick='$("#a-modal").hide(); hideModalSubpage();'>Close</button>
                        </div>
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
                    <div class='flexCol right' style="position: relative; padding-bottom: 7px; white-space: nowrap;">
                            <div id='siac-timetable-icn' class='siac-btn-small' onclick='$(this).toggleClass("expanded")'  onmouseleave='$(this).removeClass("expanded")' style='position: relative; display:inline-block; margin-right: 6px;' onmouseenter='pycmd("siac-user-note-update-btns")' onclick='pycmd("siac-create-note");'>&nbsp;&nbsp; &#9998; Notes &nbsp;&nbsp;
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
                                                <span>Menus</span>
                                                <hr>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("indexInfo");'>&nbsp;Info</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("synonyms");'>&nbsp;Synonyms</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("styling");'>&nbsp;Settings</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='$("#a-modal").hide(); pycmd("siac_rebuild_index")'>&nbsp;Rebuild Index</div>
                                        </div>
                            </div>
                    </div>
                </div>
                <div id="resultsArea" style="height: 100px;  width: 100%%; border-top: 1px solid grey; position: relative;">
                    <div id="icns-large">
                            <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                            <div class='freeze-icon' onclick='toggleFreeze(this)'> <span class='icns-add'>FREEZE </span>&#10052; </div>
                            <div class='rnd-icon' onclick='pycmd("siac-random-notes " + siacState.selectedDecks.toString())'> <span class='icns-add'>RANDOM </span>&#9861; </div>
                            <div class='flds-icon' onclick='sendContent()'> <span class='icns-add'>FIELDS </span>&#9744; </div>
                            <div class='pdf-icon' onclick='pycmd("siac-show-pdfs")'>
                                %s
                            </div>
                            <div class='rnd-icon' onclick='toggleNoteSidebar();'>NOTES</div>
                            <div class='siac-read-icn' onclick='pycmd("siac-user-note-queue-read-head")'></div>
                        </div>
                    <div id='loader' style='%s'> <div class='signal'></div><br/>Preparing index...</div>
                    <div style='height: calc(100%% - 28px); padding-top: 28px; z-index: 100;' id='resultsWrapper'>
                        <div id='searchInfo' class='%s'></div>
                        <div id='searchResults'></div>
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
                <div id='siac-reading-modal'></div>
            </div>
        </div>
        `).insertAfter('#fields');
        $(`.siac-col`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow: hidden; height: 100%%;"></div>');
        updatePinned();
        }
        $('.field').on('keyup', fieldKeypress);
        $('.field').attr('onmouseup', 'getSelectionText()');
        var $fields = $('.field');
        var $searchInfo = $('#searchInfo');
        onResize();
        window.addEventListener('resize', onResize, true);
        $('.cal-block-outer').on('mouseenter', function(event) { calBlockMouseEnter(event, this);});
        $('.cal-block-outer').on('click', function(event) { displayCalInfo(this);});
        $(`<div id='cal-info' onmouseleave='calMouseLeave()'></div>`).insertAfter('#outerWr');
""" % (
    leftSideWidth,
    rightSideWidth,
    conf_or_def("searchpane.zoom", 1.0),
    conf_or_def("noteScale", 1.0),
    pdf_svg(15, 18),
    "display: none;" if indexIsLoaded else "",
    "hidden" if hideSidebar else "",
    getCalendarHtml() if conf_or_def("showTimeline", True) else ""
    )

def get_notes_sidebar_html():
    """
        Returns the html for the sidebar that is displayed when clicking on the notes button.
    """
    tags = get_all_tags()
    tmap = utility.tags.to_tag_hierarchy(tags)

    def iterateMap(tmap, prefix, start=False):
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in tmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); pycmd('siac-user-note-search-tag %s')\"><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='siac-tl-plus' onclick='pycmd(\"siac-create-note-tag-prefill %s\") '><b>NEW</b></span></div>%s</li>" % (full, "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), full, iterateMap(value, full, False))
        html += "</ul>"
        return html

    tag_html = iterateMap(tmap, "", True)
    html = """
        <div id='siac-notes-sidebar'>
            <div style='display: flex; flex-direction: column; height: 100%%;'>
                <div style='flex: 0 1 auto;'>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-user-note-newest");'>Newest</div>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-show-pdfs")'>PDFs</div>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-show-pdfs-unread")'>PDFs - Unread</div>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-show-pdfs-in-progress")'>PDFs - In Progress</div>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-user-note-untagged")'>Untagged</div>
                    <div class='siac-notes-sidebar-item blue-hover' onclick='pycmd("siac-user-note-random");'>Random</div>
                    <input type='text' class='siac-sidebar-inp' style='width: calc(100%% - 15px); box-sizing: border-box; border-radius: 4px; padding-left: 4px; margin-top: 10px;' onkeyup='searchForUserNote(event, this);'/>
                    <div class='w-100' style='margin-top: 20px;'><b>Tags (%s)</b></div>
                    <hr style='margin-right: 15px;'/>
                </div>
                <div style='flex: 1 1 auto; padding-right: 5px; margin-right: 5px; overflow-y: auto;'>
                    %s
                </div>
            </div>

        </div>

    """ % (len(tmap) if tmap is not None else 0, tag_html)
    return html


def get_model_dialog_html():
    """
        Returns the html for the "Fields" section in the settings modal.
    """
    all_models = sorted(mw.col.models.all(), key=lambda m : m['name'])
    index = get_index()
    config = mw.addonManager.getConfig(__name__)

    html = """
    <div style='display: flex; flex-flow: column; height: 400px;'>
    <p>Changes in <i>Show Field in Results</i> take effect immediately, changes in <i>Search in Field</i> need a rebuild of the index.</p>
    <table style='width: 100%; margin: 10px 0 5px 0;'>
        <tr>
            <td style='width: 80%; font-weight: bold;'>Field Name</td>
            <td style='width: 10%; font-weight: bold;'>Search in Field</td>
            <td style='width: 10%; font-weight: bold;'>Show Field in Results</td>
        </tr>
    </table>
    <div style='overflow-y: auto; flex-grow: 1; margin-top: 20px; width: 100%'>
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

def get_reading_modal_html(note):
    """
        Main function to render the reading modal and its contents.
    """
    index = get_index()

    note_id = note.id
    text = note.text
    tags = note.tags
    created_dt = datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime.now() - created_dt

    queue = _get_priority_list()
    queue_len = len(queue)

    time_str = "Added %s ago." % utility.misc.date_diff_to_string(diff)
    # height: calc(90% - 170px); max-height: calc(100% - 260px)
    if check_index():

        title = note.get_title()
        title = utility.text.trim_if_longer_than(title, 70)
        title = title.replace("<", "&lt;").replace(">", "&gt;")
        source = note.source.strip() if note.source is not None and len(note.source.strip()) > 0 else "Empty"
        source_icn = ""

        html = """
            <div style='width: 100%; display: flex; flex-direction: column;'>
                    <div id='siac-reading-modal-top-btns'>
                        <div class='siac-btn siac-btn-dark' style='font-size: 8px;' onclick='toggleReadingModalFullscreen();'> <div class='siac-fullscreen-icn'></div> </div>
                        <div class='siac-btn siac-btn-dark' style='font-size: 8px;' onclick='pycmd("siac-left-side-width");'> / </div>
                        <div class='siac-btn siac-btn-dark' onclick='toggleReadingModalBars();'>&#x2195;</div>
                        <div class='siac-btn siac-btn-dark' style='padding-left: 7px; padding-right: 7px;' onclick='onReadingModalClose({save_on_close}, {note_id});'>&times;</div>
                    </div>
                    <div id='siac-pdf-tooltip' onclick='event.stopPropagation();' onkeyup='event.stopPropagation();'>
                        <div id='siac-pdf-tooltip-top'></div>
                        <div id='siac-pdf-tooltip-results-area' onkeyup="pdfTooltipClozeKeyup(event);"></div>
                        <div id='siac-pdf-tooltip-bottom'></div>
                        <input id='siac-pdf-tooltip-searchbar' onkeyup='if (event.keyCode === 13) {{pycmd("siac-pdf-tooltip-search " + this.value);}}'></input>
                    </div>
                    <div id='siac-reading-modal-top-bar' data-nid='{note_id}' style='min-height: 77px; width: 100%; flex: 0 0 77px; display: flex; flex-wrap: nowrap; border-bottom: 2px solid darkorange; margin-bottom: 5px; white-space: nowrap;'>
                        <div style='flex: 1 1; overflow: hidden;'>
                            <h2 style='margin: 0 0 5px 0; white-space: nowrap; overflow: hidden; vertical-align:middle;'>{title}</h2>
                            <h4 style='whitespace: nowrap; margin: 5px 0 8px 0; color: lightgrey;'>Source: <i>{source}</i></h4>
                            <div id='siac-prog-bar-wr'></div>
                        </div>
                        <div style='flex: 0 0; min-width: 130px; padding: 0 85px 0 10px;'>
                            <span class='siac-timer-btn' onclick='resetTimer(this)'>5</span><span class='siac-timer-btn' onclick='resetTimer(this)'>10</span><span class='siac-timer-btn' onclick='resetTimer(this)'>15</span><span class='siac-timer-btn' onclick='resetTimer(this)'>25</span><span class='siac-timer-btn active' onclick='resetTimer(this)'>30</span><br>
                            <span id='siac-reading-modal-timer'>30 : 00</span><br>
                            <span class='siac-timer-btn' onclick='resetTimer(this)'>45</span><span class='siac-timer-btn' onclick='resetTimer(this)'>60</span><span class='siac-timer-btn' onclick='resetTimer(this)'>90</span><span id='siac-timer-play-btn' class='inactive' onclick='toggleTimer(this);'>Start</span>
                        </div>
                    </div>
                    <div id='siac-reading-modal-center' style='flex: 1 1 auto; overflow-y: {overflow}; font-size: 13px; padding: 0 20px 0 24px; position: relative; display: flex; flex-direction: column;' >
                        {text}
                    </div>
                    <div id='siac-reading-modal-bottom-bar' style='flex: 0 0 auto; position: relative; width: 100%; border-top: 2px solid darkorange; margin-top: 5px; padding: 2px 0 0 5px; overflow: hidden; user-select: none;'>
                        <div style='width: 100%; height: calc(100% - 5px); display: inline-block; padding-top: 5px; white-space: nowrap;'>

                            <div style='padding: 5px; display: inline-block; vertical-align: top;'><div class='siac-queue-sched-btn active' onclick='toggleQueue();'>{queue_info_short}</div></div>
                            <div id='siac-queue-sched-wrapper'>
                                <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 2")'>Start</div>
                                <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 7")'>Rnd</div>
                                <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 3")'>First 3rd</div>
                                <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 8")'>Rnd</div>
                                <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 4")'>Second 3rd</div>
                                <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 9")'>Rnd</div>
                                <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 5")'>End</div>
                                <div style='display: inline-block; height: 94px; margin: 0 10px 0 10px; border-left: 2px solid lightgrey; border-style: dotted; border-width: 0 0 0 2px;'></div>
                                <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 6");'>&#9861; Random</div>
                                <div class='siac-queue-sched-btn' style='margin-left: 10px;' onclick='pycmd("siac-remove-from-queue {note_id}")'>&times; Remove</div>
                            </div>
                            <div id='siac-queue-actions' style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px; margin-top: 3px; user-select: none; z-index: 1;'>
                                <span style='vertical-align: top;' id='siac-queue-lbl'>{queue_info}</span><br>
                                <span style='margin-top: 5px; color: lightgrey;'>{time_str}</span> <br>
                                <div style='margin: 7px 0 4px 0; display: inline-block;'>Read Next: <span class='siac-queue-picker-icn' onclick='if (pdfLoading||noteLoading) {{return;}}pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span></div><br>
                                <a onclick='if (!pdfLoading) {{noteLoading = true; greyoutBottom(); destroyPDF(); pycmd("siac-user-note-queue-read-head");}}' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;'>First In Queue</a><br>
                                <a onclick='if (!pdfLoading) {{noteLoading = true; greyoutBottom(); destroyPDF(); pycmd("siac-user-note-queue-read-random");}}' class='siac-clickable-anchor'>Random In Queue</a>
                            </div>
                            {queue_readings_list}
                            <div id='siac-queue-infobox-wrapper'>
                                <div id='siac-queue-infobox' onmouseleave='leaveQueueItem();'></div>
                            </div>
                            <div id='siac-pdf-bottom-tabs' style='display: inline-block; vertical-align: top; margin-left: 16px; user-select: none;'>
                                <a class='siac-clickable-anchor tab active' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} marks")' style='margin-right: 10px;'>Marks</a>
                                <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} related")' style='margin-right: 10px;'>Related</a>
                                <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} info")'>Info</a> <br>
                                <div id='siac-pdf-bottom-tab'>
                                    <div id='siac-marks-display' onclick='markClicked(event);'></div>
                                </div>
                            </div>
                           
                        </div>
                    </div>
                    <div id='siac-timer-popup'>
                        

                    </div>
            </div>
            <script>
            destroyPDF();
            if (readingTimer != null)  {{
                 $('#siac-timer-play-btn').html('Pause').removeClass('inactive');
            }} else if (remainingSeconds !== 1800) {{
                document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
            }}
            if (pdfFullscreen) {{
                activateReadingModalFullscreen();
            }} else if (pdfBarsHidden) {{
                pdfBarsHidden = false;
                toggleReadingModalBars();
            }}
            iframeIsDisplayed = false;
            noteLoading = false;
            </script>
        """

        #check if it is a pdf or feed
        overflow = "auto"
        if note.is_pdf() and utility.misc.file_exists(source):
            editable = False
            overflow = "hidden" 
            text = get_pdf_viewer_html(note_id, source, note.get_title())
            if "/" in source:
                source = source[source.rindex("/") +1:]
        elif note.is_feed():
            text = get_feed_html(note_id, source)
            editable = False
        else:
            editable = len(text) < 100000
            text = get_text_note_html(text, note_id, editable)
        
       
        save_on_close = "true" if editable else "false"
        queue_info = "Position: <b>%s</b> / <b>%s</b>" % (note.position + 1, queue_len) if note.is_in_queue() else "Unqueued."
        queue_info_short = "<b>%s</b> / <b>%s</b>" % (note.position + 1, queue_len) if note.is_in_queue() else "Unqueued"

        queue_readings_list = get_queue_head_display(note_id, queue, editable)

        params = dict(note_id = note_id, title = title, source = source, time_str = time_str, text = text, queue_info = queue_info, queue_info_short = queue_info_short, queue_readings_list = queue_readings_list, save_on_close = save_on_close, overflow=overflow)
        html = html.format_map(params)
        return html
    return ""


def get_text_note_html(text, nid, editable):
    """
        Returns the html which is wrapped around the text of user notes inside the reading modal.
        This function is used if the note is a regular, text-only note, if the note is a pdf note, 
        get_pdf_viewer_html is used instead.
    """
    dir = utility.misc.get_web_folder_path()
    search_sources = ""
    config = mw.addonManager.getConfig(__name__)
    urls = config["searchUrls"]
    if urls is not None and len(urls) > 0:
        search_sources = iframe_dialog(urls)
    is_content_editable = "true" if editable else "false"
    # editable_notification = "<span style='margin-left: 30px; color: grey;'>(i) Note content too long to edit here.</span>" if not editable else ""
    save = "saveTextNote(%s);"  % (nid) if editable else ""
    html = """
        <div id='siac-iframe-btn' style='top: 5px; left: 0px;' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
            <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center; color: grey;'>Note: Not all sites allow embedding!</div>
            <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                <br/>
               {search_sources}
            </div>
        </div>
        <div class='siac-btn siac-btn-dark' id='siac-quick-sched-btn' onclick='$(this).toggleClass("expanded")'><div class='siac-read-icn siac-read-icn-light'></div>
            <div class='expanded-hidden white-hover' onclick='{save} pycmd("siac-move-end-read-next {nid}"); event.stopPropagation();' style='margin: 0 2px 0 5px; color: lightgrey; text-align: center;'><b>Move End, Read Next</b></div>
        </div>
        <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
        <div id='siac-text-top-wr' style='height: calc(100% - 42px);'>
            <div id='siac-text-top'>
                {text}
            </div>
        </div>
        <iframe id='siac-iframe' sandbox='allow-scripts' style='height: calc(100% - 47px);'></iframe>
        <div class="siac-reading-modal-button-bar-wrapper">
            <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
                <span id='siac-text-note-status' style='margin-left: 30px; color: grey;'></span>
            </div>
        </div>
        <script>
            {tiny_mce} 
        </script>
    """.format_map(dict(text = text, save=save, nid = nid, search_sources=search_sources , tiny_mce=tiny_mce_init_code()))
    return html


def get_feed_html(nid, source):
    #extract feed url
    try:
        feed_url = source[source.index(":") +1:].strip()
    except:
        return "<center>Could not load feed. Please check the URL.</center>"
    res = read(feed_url)
    dir = utility.misc.get_web_folder_path()
    search_sources = ""
    config = mw.addonManager.getConfig(__name__)
    urls = config["searchUrls"]
    if urls is not None and len(urls) > 0:
        search_sources = iframe_dialog(urls)
    text = ""
    templ = """
        <div class='siac-feed-item' >
            <div><span class='siac-blue-outset'>%s</span> &nbsp;<a href="%s" class='siac-ul-a'>%s</a></div>
            <div><i>%s</i> <span style='margin-left: 15px;'>%s</span></div> 
            <div style='margin: 15px;'>%s</div>
        </div>
    """
    for ix, message in enumerate(res[:25]):
        if len(message.categories) > 0:
            if len(message.categories) == 1:
                cats = f"<span class='blue-underline'>{message.categories[0]}</span>"
            else:
                cats = "<span class='blue-underline'>" + "</span> &nbsp;<span class='blue-underline'>".join(message.categories) + "</span>"
        else:
            cats = ""
        text = ''.join((text, templ % (ix + 1, message.link, message.title, message.date, cats, message.text)))
    html = """
        <div id='siac-iframe-btn' style='top: 5px; left: 0px;' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
            <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center; color: grey;'>Note: Not all sites allow embedding!</div>
            <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                <br/>
               {search_sources}
            </div>
        </div>
        <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
        <div id='siac-text-top' contenteditable='false' onmouseup='nonPDFKeyup();' onclick='if (!window.getSelection().toString().length) {{$("#siac-pdf-tooltip").hide();}}'>
            {text}
        </div>
        <iframe id='siac-iframe' sandbox='allow-scripts' style='height: calc(100% - 47px);'></iframe>
        <div class="siac-reading-modal-button-bar-wrapper">
            <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
            </div>
        </div>
        <script>
            if (pdfTooltipEnabled) {{
                $('#siac-pdf-tooltip-toggle').addClass('active');
            }} else {{
                $('#siac-pdf-tooltip-toggle').removeClass('active');
            }}
            ungreyoutBottom();
        </script>
    """.format_map(dict(text = text, nid = nid, search_sources=search_sources))
    return html


def get_reading_modal_bottom_bar(note):
    """
        Returns only the html for the bottom bar, useful if the currently displayed pdf should not be reloaded, but the queue display has to be refreshed.
    """
    index = get_index()
    text = note.text
    note_id = note.id
    source = note.source
    created_dt = datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime.now() - created_dt
    queue = _get_priority_list()
    queue_len = len(queue)

    time_str = "Added %s ago." % utility.misc.date_diff_to_string(diff)
       
    html = """
            <div id='siac-reading-modal-bottom-bar' style='width: 100%; flex: 0 0 auto; position: relative; border-top: 2px solid darkorange; margin-top: 5px; padding: 2px 0 0 5px; overflow: hidden; user-select: none;'>
                <div style='width: 100%; height: calc(100% - 5px); display: inline-block; padding-top: 5px; white-space: nowrap; display: relative;'>

                    <div style='padding: 5px; display: inline-block; vertical-align: top;'><div class='siac-queue-sched-btn active' onclick='toggleQueue();'>{queue_info_short}</div></div>
                    <div id='siac-queue-sched-wrapper'>

                        <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 2")'>Start</div>
                        <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 7")'>Rnd</div>
                        <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 3")'>First 3rd</div>
                        <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 8")'>Rnd</div>
                        <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 4")'>Second 3rd</div>
                        <div class='siac-queue-sched-btn-hor' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 9")'>Rnd</div>
                        <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 5")'>End</div>
                        <div style='display: inline-block; height: 94px; margin: 0 10px 0 10px; border-left: 2px solid lightgrey; border-style: dotted; border-width: 0 0 0 2px;'></div>
                        <div class='siac-queue-sched-btn' onclick='queueSchedBtnClicked(this); pycmd("siac-requeue {note_id} 6");'>&#9861; Random</div>
                        <div class='siac-queue-sched-btn' style='margin-left: 10px;' onclick='pycmd("siac-remove-from-queue {note_id}")'>&times; Remove</div>
                    </div>
                    <div  id='siac-queue-actions'  style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px; margin-top: 3px; user-select: none; z-index: 1;'>
                        <span style='vertical-align: top;' id='siac-queue-lbl'>{queue_info}</span><br>
                        <span style='margin-top: 5px; color: lightgrey;'>{time_str}</span> <br>
                        <div style='margin: 7px 0 4px 0; display: inline-block;'>Read Next: <span class='siac-queue-picker-icn' onclick='if (pdfLoading||noteLoading) {{return;}}pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span></div><br>
                        <a onclick='noteLoading = true; greyoutBottom(); pycmd("siac-user-note-queue-read-head")' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;'>First In Queue</a><br>
                        <a onclick='noteLoading = true; greyoutBottom(); pycmd("siac-user-note-queue-read-random")' class='siac-clickable-anchor'>Random In Queue</a>
                    </div>
                    {queue_readings_list}
                    <div id='siac-queue-infobox-wrapper'>
                        <div id='siac-queue-infobox' onmouseleave='leaveQueueItem();'></div>
                    </div>
                    <div id='siac-pdf-bottom-tabs' style='display: inline-block; vertical-align: top; margin-left: 16px; user-select: none;'>
                        <a class='siac-clickable-anchor tab active' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} marks")' style='margin-right: 10px;'>Marks</a>
                        <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} related")' style='margin-right: 10px;'>Related</a>
                        <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} info")'>Info</a> <br>
                        <div id='siac-pdf-bottom-tab'>
                            <div id='siac-marks-display' onclick='markClicked(event);'></div>
                        </div>
                    </div>
                </div>
            </div>
    """
    editable = not note.is_feed() and not note.is_pdf() and len(text) < 50000
    queue_info = "Position: <b>%s</b> / <b>%s</b>" % (note.position + 1, queue_len) if note.is_in_queue() else "Unqueued."
    queue_info_short = "<b>%s</b> / <b>%s</b>" % (note.position + 1, queue_len) if note.is_in_queue() else "Unqueued"
    queue_readings_list = get_queue_head_display(note_id, queue, editable)

    params = dict(note_id = note_id, time_str = time_str, queue_info = queue_info, queue_info_short = queue_info_short, queue_readings_list = queue_readings_list )
    html = html.format_map(params)
    return html

def get_queue_head_display(note_id, queue = None, should_save = False):
    """
    This returns the html for the little list at the bottom of the reading modal which shows the first 5 items in the queue.
    """
    if queue is None:
        queue = _get_priority_list()
    if queue is None or len(queue) == 0:
        return "<div id='siac-queue-readings-list' style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px; user-select: none;'></div>"

    note = get_note(note_id)
    if not note.is_pdf() and not note.is_feed():
        should_save = True

    if should_save:
        save = "saveTextNote(%s);"  % (note_id)
    else:
        save = ""
    hide = config = mw.addonManager.getConfig(__name__)["pdf.queue.hide"]
    queue_head_readings = ""
    for ix, queue_item in enumerate(queue):
        should_greyout = "greyedout" if queue_item.id == int(note_id) else ""
        if not hide or queue_item.id == int(note_id) :
            qi_title = utility.text.trim_if_longer_than(queue_item.get_title(), 40) 
            qi_title = utility.text.escape_html(qi_title)
        else:
            qi_title = re.sub("[^ ]", "?",queue_item.get_title())

        hover_actions = "onmouseenter='showQueueInfobox(this, %s);' onmouseleave='leaveQueueItem(this);'" % (queue_item.id) if not hide else ""
        #if the note is a pdf or feed, show a loader
        pdf_or_feed = queue_item.is_feed() or queue_item.is_pdf()
        should_show_loader = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showLoader(\"siac-reading-modal-center\", \"Loading Note...\");' if pdf_or_feed else ""
        queue_head_readings +=  "<a onclick='if (!pdfLoading) {%s %s  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note %s\"); hideQueueInfobox();}' class='siac-clickable-anchor %s' style='font-size: 12px; font-weight: bold;' %s >%s. %s</a><br>" % (save, should_show_loader, queue_item.id, should_greyout, hover_actions, queue_item.position + 1, qi_title)
        if ix > 3:
            break

    if hide:
        hide_btn = """<div style='display: inline-block; margin-left: 12px; color: grey;' class='blue-hover' onclick='unhideQueue(%s)'>(Show Items)</div>""" % note_id
    else:
        hide_btn = """<div style='display: inline-block; margin-left: 12px; color: grey;' class='blue-hover' onclick='hideQueue(%s)'>(Hide Items)</div>""" % note_id
    html = """
     <div id='siac-queue-readings-list' style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px; user-select: none;'>
          <div style='margin: 0px 0 3px 0; display: inline-block; color: lightgrey;'>Queue Head:</div>%s<br>
            %s
     </div>
    """ % (hide_btn, queue_head_readings)
    return html

def get_related_notes_html(note_id):
    r = get_related_notes(note_id)
    note = get_note(note_id)
    if not note.is_pdf() and not note.is_feed():
        save = "saveTextNote(%s);"  % (note_id)
    else:
        save = ""
    html = "" 
    ids = set()
    res = []
    if r.related_by_tags is not None:
        for r1 in r.related_by_tags:
            res.append(r1) 
            ids.add(r1.id)
            if len(r.related_by_title) > 0:
                i = r.related_by_title.pop(0)
                if not i.id in ids:
                    res.append(i)
            if len(res) > 20:
                break
    if len(res) < 20 and len(r.related_by_title) > 0:
        for r2 in r.related_by_title:
            if not r2.id in ids:
                res.append(r2)
                if len(res) >= 20:
                    break
    for rel in res[:20]:
        if rel.id == note_id:
            continue
        title = utility.text.trim_if_longer_than(rel.get_title(), 100)
        pdf_or_feed = rel.is_pdf() or rel.is_feed()
        should_show_loader = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showLoader(\"siac-reading-modal-center\", \"Loading Note...\");' if pdf_or_feed else ""
        html = f"{html}<div class='siac-related-notes-item' onclick='if (!pdfLoading) {{ {save} {should_show_loader}  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note {rel.id}\"); }}'>{title}</div>"
    return html

def get_note_info_html(note_id):
    """
        Returns the html that is displayed in the "Info" tab in the bottom bar of the reading modal.
    """
    note = get_note(note_id)
    created = note.created
    tags = note.tags
    if tags.startswith(" "):
        tags = tags[1:]
    html = f"""
        <table style='color: grey; min-width: 190px;'>
            <tr><td>ID</td><td><b>{note.id}</b></td></tr>
            <tr><td>Created</td><td><b>{created}</b></td></tr>
        </table>
        <br>
        <label style='color: grey;'>Tags:</label>
        <input type='text' style='width: 210px; background: #2f2f31; margin-left: 4px; padding-left: 4px; border: 1px solid grey; border-radius: 4px; color: lightgrey;' onfocusout='pycmd("siac-update-note-tags {note.id} " + this.value)' value='{tags}'></input>
    """
    return html

def iframe_dialog(urls):
    search_sources = "<table style='margin: 10px 0 10px 0; cursor: pointer; box-sizing: border-box; width: 100%;' onclick='event.stopPropagation();'>"
    ix = 0
    direct_links = ""
    for url in urls:
        name = os.path.dirname(url)
        if "[QUERY]" in url:
            search_sources += "<tr><td><label for='%s'>%s</label></td><td><input type='radio' name='url-radio' id='%s' data-url='%s' %s/></td></tr>" % ("url-rd-%d" % ix, name, "url-rd-%d" % ix, url, "checked" if ix == 0 else "")
            ix += 1
        else:
            direct_links += """<div class="siac-url-ch" onclick='event.stopPropagation(); $("#siac-iframe-btn").removeClass("expanded"); pycmd("siac-url-srch $$$dummy$$$%s");'>%s</div>""" % (url, name)

    search_sources += "</table>"
    if len(direct_links) > 0:
        search_sources += "<div style='margin-bottom: 5px;'>Direct Links:</div>"
        search_sources += direct_links
    return search_sources



def get_pdf_viewer_html(nid, source, title):
    
    dir = utility.misc.get_web_folder_path()
    search_sources = ""
    config = mw.addonManager.getConfig(__name__)
    urls = config["searchUrls"]
    if urls is not None and len(urls) > 0:
        search_sources = iframe_dialog(urls)

    marks_img_src = utility.misc.img_src("mark-star-24px.png")
    marks_grey_img_src = utility.misc.img_src("mark-star-lightgrey-24px.png")
    html = """
        <div id='siac-pdf-overlay'>PAGE READ</div>
        <div id='siac-pdf-overlay-top'>
            <div id='siac-pdf-mark-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'><img src='{marks_img_src}' style='width: 17px; height: 17px; margin: 0;'/>
                <div style='margin-left: 7px;'>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-1' onclick='pycmd("siac-pdf-mark 1 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Revisit</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-2' onclick='pycmd("siac-pdf-mark 2 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Hard</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-3' onclick='pycmd("siac-pdf-mark 3 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Info</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-4' onclick='pycmd("siac-pdf-mark 4 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Cards</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-5' onclick='pycmd("siac-pdf-mark 5 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Bookmark</div>
                </div> 
            </div>
            <div style='display: inline-block; vertical-align: top;' id='siac-pdf-overlay-top-lbl-wrap'></div>
        </div>
        <div id='siac-iframe-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
            <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center;'>Note: Not all Websites allow Embedding!</div>
            <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                <br/>
               {search_sources}
            </div>
        </div>
        <div class='siac-btn siac-btn-dark' id='siac-mark-jump-btn' onclick='$(this).toggleClass("expanded"); onMarkBtnClicked(this);'><img src='{marks_grey_img_src}' style='width: 16px; height: 16px;'/>
            <div id='siac-mark-jump-btn-inner' class='expanded-hidden white-hover' style='margin: 0 2px 0 5px; color: lightgrey; text-align: center;'></div>
        </div>
        <div class='siac-btn siac-btn-dark' id='siac-quick-sched-btn' onclick='$(this).toggleClass("expanded")'><div class='siac-read-icn siac-read-icn-light'></div>
            <div class='expanded-hidden white-hover' onclick='pycmd("siac-move-end-read-next {nid}"); event.stopPropagation();' style='margin: 0 2px 0 5px; color: lightgrey; text-align: center;'><b>Move End, Read Next</b></div>
        </div>
        <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
        <div id='siac-pdf-top' data-pdfpath="{pdf_path}" data-pdftitle="{pdf_title}" data-pdfid="{nid}" onwheel='pdfMouseWheel(event);' style='overflow-y: hidden;'>
            <div id='siac-pdf-loader-wrapper' style='display: flex; justify-content: center; align-items: center; height: 100%;'>
                <div class='siac-pdf-loader' style=''>
                    <div> <div class='signal' style='margin-left: auto; margin-right: auto;'></div><br/><div id='siac-loader-text'>Loading PDF</div></div>
                </div>
            </div>
            <canvas id="siac-pdf-canvas" style='z-index: 99999; display:inline-block;'></canvas>
            <div id="text-layer" onmouseup='pdfKeyup();' onclick='if (!window.getSelection().toString().length) {{$("#siac-pdf-tooltip").hide();}}' class="textLayer"></div>
        </div>
        <iframe id='siac-iframe' sandbox='allow-scripts'></iframe>
        <div class='siac-reading-modal-button-bar-wrapper' style="">
            <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                <div class='siac-btn siac-btn-dark' style="margin-left: 2px; width: 18px;" onclick='pdfScaleChange("down");'>-</div>
                <div class='siac-btn siac-btn-dark' style="width: 22px;" onclick='pdfFitToPage()'>&#8596;</div>
                <div class='siac-btn siac-btn-dark' style="width: 18px;" onclick='pdfScaleChange("up");'>+</div>
                <div class='siac-btn siac-btn-dark' onclick='initImageSelection()' style='margin-left: 5px;'><b>&#9986;</b></div>
                <div class='siac-btn siac-btn-dark active' id='siac-pdf-tooltip-toggle' onclick='togglePDFSelect(this)' style='margin-left: 5px;'><div class='siac-search-icn-dark'></div></div>
                <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
            </div>
            <div style='user-select:none; display: inline-block; position:relative; z-index: 2; padding: 0 5px 0 5px; background: #2f2f31;'>
                <div class='siac-btn siac-btn-dark' onclick='pdfPageLeft();'><b>&lt;</b></div>
                <span style='display: inline-block; text-align: center; width: 70px; user-select: none;' id='siac-pdf-page-lbl'>Loading...</span>
                <div class='siac-btn siac-btn-dark' onclick='pdfPageRight();'><b>&gt;</b></div>
            </div>

            <div style='position: absolute; right: 0; display: inline-block; user-select: none;'>
                <div id="siac-pdf-night-btn" class='siac-btn siac-btn-dark' style='margin-right: 10px; width: 50px;' onclick='togglePDFNightMode(this);'>Day</div>
                <div id="siac-pdf-read-btn" class='siac-btn' style='margin-right: 7px; width: 65px;' onclick='togglePageRead({nid});'>\u2713&nbsp; Read</div>
                <div style='position: relative; display: inline-block; width: 30px; margin-right: 7px;'>
                    <div id='siac-pdf-more-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'  onmouseleave='$(this).removeClass("expanded")' style='width: calc(100% - 14px)'>...
                        <div class='siac-btn-small-dropdown-inverted click'>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-jump-last-read {nid}"); event.stopPropagation();'><b>Jump to Last Read Page</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-jump-first-unread {nid}"); event.stopPropagation();'><b>Jump to First Unread Page</b></div>
                            <hr>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-read-up-to {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages); pagesRead = Array.from(Array(pdfDisplayedCurrentPage).keys()).map(x => ++x); pdfShowPageReadMark();updatePdfProgressBar();event.stopPropagation();'><b>Mark Read up to current Pg.</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-display-range-input {nid} " + pdfDisplayed.numPages); event.stopPropagation();'><b>Mark Range ...</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-unread {nid}"); pagesRead = []; pdfHidePageReadMark(); updatePdfProgressBar();event.stopPropagation();'><b>Mark all as Unread</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-read {nid} " + pdfDisplayed.numPages); pagesRead = Array.from(Array(pdfDisplayed.numPages).keys()).map(x => ++x); pdfShowPageReadMark(); updatePdfProgressBar();event.stopPropagation();'>
                                <b>Mark all as Read</b>
                            </div>
                        </div>
                    </div>
                </div>
                <input id="siac-pdf-page-inp" style="width: 50px;margin-right: 5px;" value="1" type="number" min="1" onkeyup="pdfJumpToPage(event, this);"></input>
            </div>
        </div>
       
        <script>
            greyoutBottom();
            document.getElementById('siac-pdf-night-btn').innerHTML = pdfColorMode;
            if (pdfTooltipEnabled) {{
                $('#siac-pdf-tooltip-toggle').addClass('active');
            }} else {{
                $('#siac-pdf-tooltip-toggle').removeClass('active');
            }}
        </script>
    """.format_map(dict(nid = nid, pdf_title = title, pdf_path = source, search_sources=search_sources, marks_img_src=marks_img_src, marks_grey_img_src=marks_grey_img_src))
    return html


def getCalendarHtml():
    html = """<div id='cal-row' style="width: 100%%; height: 8px;" onmouseleave='calMouseLeave()'>%s</div> """
    #get notes created since the beginning of the year
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    date_year_begin = datetime.datetime(year=datetime.datetime.utcnow().year, month=1, day=1, hour=0 ,minute=0)
    nid_now = int(time.time()* 1000)
    nid_minus_day_of_year = int(date_year_begin.timestamp() * 1000)

    res = mw.col.db.execute("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc" %(nid_minus_day_of_year, nid_now)).fetchall()

    counts = []
    c = 1
    notes_in_current_day = 0
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


def pdf_prog_bar(read, read_total):
    if read is not None and read_total is not None:
        perc = int(read * 10.0 / read_total)
        perc_100 =  int(read * 100.0 / read_total)
        prog_bar = str(perc_100) + " % &nbsp;"
        for x in range(0, 10):
            if x < perc:
                prog_bar = f"{prog_bar}<div class='siac-prog-sq-filled'></div>"
            else:
                prog_bar = f"{prog_bar}<div class='siac-prog-sq'></div>"
        return prog_bar
    else:
        return ""

def get_note_delete_confirm_modal_html(nid):
    note = get_note(nid)
    creation_date = note.created
    title = utility.text.trim_if_longer_than(note.get_title(), 100) 
    return """
       <div class='siac-modal-small'>
            <p style='text-align: center; font-size: 14px;'><b>Delete the following note?</b></p>
            <hr class='siac-modal-sep'/>
            <br>
            <div style='text-align: center; font-size: 14px; margin-bottom: 4px;'><b>%s</b></div>
            <div style='text-align: center; font-size: 14px;'><i>%s</i></div>
            <br><br>
            <div style='text-align: center;'><div class='siac-btn' onclick='$(this.parentNode.parentNode).remove(); removeNote(%s); $("#greyout").hide(); pycmd("siac-delete-user-note %s");' style='margin-right: 10px;'><div class='siac-trash-icn'></div>&nbsp;Delete&nbsp;</div><div class='siac-btn' onclick='$(this.parentNode.parentNode).remove(); $("#greyout").hide();'>&nbsp;Cancel&nbsp;</div></div>
       </div>


    """ % (title, creation_date, nid, nid)

def get_queue_infobox(note, read_stats):
    """
        Returns the html that is displayed in the tooltip which appears when hovering over an item in the queue head.
    """
    diff = datetime.datetime.now() - datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
    time_str = "Created %s ago." % utility.misc.date_diff_to_string(diff)
    # pagestotal might be None (it is only available if at least one page has been read)
    if read_stats[2] is not None:
        prog_bar = pdf_prog_bar(read_stats[0], read_stats[2])
        pages_read = "<div style='width: 100%%; margin-top: 7px; font-weight: bold; text-align: center; font-size: 20px;'>%s / %s</div>" % (read_stats[0], read_stats[2])
    else:
        prog_bar = ""
        pages_read = ""

    html = """
        <div style='width: calc(100% - 81px); height: 100%; padding: 10px; display: inline-block; position: relative; vertical-align: top;'>
            <div style='width: calc(100%); text-align:center; white-space: nowrap; overflow: hidden; font-weight: bold; vertical-align: top; text-overflow: ellipsis;'>{title}</div>
            <div style='width: calc(100%); text-align:center; white-space: nowrap; overflow: hidden; color: lightgrey;vertical-align: top;'>{time_str}</div>
            {pages_read}
            <div style='position: absolute; bottom: 20px; left: 0px; right: 0px; width: calc(100% - 20px); padding: 10px; text-align: center;'>
                <div style='display: inline-block; vertical-align: bottom;'>
                    {prog_bar}
                </div>
            </div>
        </div>
        <div style='width: 50px; height: 100%; padding: 2px 5px 2px 0; display: inline-block;'>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 2 "+ $("#siac-reading-modal-top-bar").data("nid"))'>Start</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 5 "+ $("#siac-reading-modal-top-bar").data("nid"))'>End</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 6 "+ $("#siac-reading-modal-top-bar").data("nid"))'>Random</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-remove-from-queue-tt {nid} " + $("#siac-reading-modal-top-bar").data("nid"))'>Remove</div>
        </div>
    """.format_map(dict(title = note.get_title(), pages_read=pages_read, time_str= time_str, prog_bar= prog_bar, nid = note.id))
    return html

def stylingModal(config):
    html = """
            <fieldset>
                <span>Exclude note fields from search or display.</span>
                <button class='siac-btn siac-btn-small' style='float: right;' onclick='pycmd("siac-model-dialog")'>Set Fields</button>
            </fieldset>
            <br/>
            <fieldset>
            <span><mark>Important:</mark> Modify this value if the bottom bar (containing the predefined searches and the browser search) sits too low or too high. (Can be negative)</span>
                <table style="width: 100%%">
                    <tr><td><b>Add To Result Area Height</b></td><td style='text-align: right;'><input placeholder="Value in px" type="number" style='width: 60px;' onchange="pycmd('styling addToResultAreaHeight ' + this.value)" value="%s"/> px</td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
            <span><mark>Important:</mark> Modify this value to scale the whole search pane. Useful e.g. when working on a small screen. If this is not 1.0, the <i>Add To Result Area Height</i> option needs to be modified too.</span>
                <table style="width: 100%%">
                    <tr><td><b>Zoom</b></td><td style='text-align: right;'><input placeholder="" type="number" step="0.1" style='width: 60px;' onchange="pycmd('styling searchpane.zoom ' + this.value)" value="%s"/></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>Controls whether the results are faded in or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Render Immediately</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('styling renderImmediately ' + this.checked)" %s/></td></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls how the window is split into search pane and field input. A value of 40 means the left side will take 40%% and the right side will take 60%%.</span>
                <table style="width: 100%%">
                    <tr><td><b>Left Side Width</b></td><td style='text-align: right;'><input placeholder="Value in px" type="number" min="0" max="100" style='width: 60px;' onchange="pycmd('styling leftSideWidthInPercent ' + this.value)" value="%s"/> %%</td></tr>
                </table>
            </fieldset>
             <br/>
            <fieldset>
                <span>This controls whether the sidebar (containing the tags and found keywords) is visible or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Hide Sidebar</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('styling hideSidebar ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
             <br/>
              <fieldset>
                <span>This controls whether the timeline row (added notes over the year) is visible or not.</span>
                <table style="width: 100%%">
                    <tr><td><b>Show Timeline</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('styling showTimeline ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
              <fieldset>
                <span>This controls whether the small info box will be shown when a tag is hovered over with the mouse. Currently only works with the default scaling.</span>
                <table style="width: 100%%">
                    <tr><td><b>Show Tag Info on Hover</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('styling showTagInfoOnHover ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This controls how long you have to hover over a tag until the info box is shown. Allowed values are 0 (not recommended) to 10000.</span>
                <table style="width: 100%%">
                    <tr><td><b>Tag Hover Delay in Miliseconds</b></td><td style='text-align: right;'><input placeholder="Value in ms" type="number" min="0" max="10000" style='width: 60px;' onchange="pycmd('styling tagHoverDelayInMiliSec ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>If the number of notes that would go into the index (only notes from the included decks are counted) is lower than this value the index should always be rebuilt.</span>
                <table style="width: 100%%">
                    <tr><td><b>Always Rebuild Index If Smaller Than</b></td><td style='text-align: right;'><input placeholder="Value in ms" type="number" min="0" max="100000" style='width: 60px;' onchange="pycmd('styling alwaysRebuildIndexIfSmallerThan ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>If you have problems with the display of search results (e.g. notes nested into each other), most likely, your note's html contains at least one unmatched opening/closing &lt;div&gt; tag. If set to true, this setting will remove all div tags from the note html before displaying.</span>
                <table style="width: 100%%">
                    <tr><td><b>Remove &lt;div&gt; Tags from Output</b></td><td style='text-align: right;'><input type="checkbox" onclick="pycmd('styling removeDivsFromOutput ' + this.checked)" %s/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This is the absolute path to the folder where the addon should store its notes. If not present already, the addon will create a file named "siac-notes.db" in that folder. If empty, user_files will be used.</span>
                <table style="width: 100%%">
                    <tr><td><b>Addon Note DB Folder Path</b></td><td style='text-align: right;'><input type="text" onfocusout="pycmd('styling addonNoteDBFolderPath ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <fieldset>
                <span>This is the location where PDFs generated from URLs will be saved. This needs to be set for the URL import to work.</span>
                <table style="width: 100%%">
                    <tr><td><b>PDF Url-Import Save Path</b></td><td style='text-align: right;'><input type="text" onfocusout="pycmd('styling pdfUrlImportSavePath ' + this.value)" value="%s"/></tr>
                </table>
            </fieldset>
            <br/>
            <div style='text-align: center'><mark>For other settings, see the <em>config.json</em> file.</mark></div>
                        """ % (config["addToResultAreaHeight"],
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
                       config["pdfUrlImportSavePath"]
                        )
    html += """
    <br/> <br/>
    <mark>&nbsp;Important:&nbsp;</mark> At the moment, if you reset your config.json to default, your custom stopwords and synsets will be deleted. If you want to do that, I recommend saving them somewhere first.
    <br/> <br/>
    If you want to use the add-on with the <b>night mode</b> add-on, you have to adapt the styling section.
    <br/> <br/>
    <b>Sample night mode configuration (copy and replace the <i>styling</i> section in your config with it):</b><br/><br/>
    <div style='width: 100%; overflow-y: auto; max-height: 130px;'>
    "styling": {
        "bottomBar": {
            "browserSearchInputBackgroundColor": "#2f2f31",
            "browserSearchInputBorderColor": "grey",
            "browserSearchInputForegroundColor": "beige",
            "selectBackgroundColor": "#2f2f31",
            "selectForegroundColor": "white",
            "timelineBoxBackgroundColor": "#2b2b30",
            "timelineBoxBorderColor": "DarkOrange"
        },
        "general": {
            "buttonBackgroundColor": "#2f2f31",
            "buttonBorderColor": "grey",
            "buttonForegroundColor": "beige",
            "fieldSeparatorColor": "white",
            "highlightBackgroundColor": "SpringGreen",
            "highlightForegroundColor": "Black",
            "keywordColor": "SpringGreen",
            "noteBackgroundColor": "#2f2f31",
            "noteBorderColor": "lightseagreen",
            "noteFontSize": 12,
            "noteForegroundColor": "beige",
            "noteHoverBorderColor": "#62C9C3",
            "rankingLabelBackgroundColor": "DarkOrange",
            "rankingLabelForegroundColor": "Black",
            "tagBackgroundColor": "DarkOrange",
            "tagFontSize": 12,
            "tagForegroundColor": "Black",
            "windowColumnSeparatorColor": "DarkOrange"
        },
        "modal": {
            "modalBackgroundColor": "#2f2f31",
            "modalBorderColor": "DarkOrange",
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
            "deckSelectHoverBackgroundColor": "DarkOrange",
            "deckSelectHoverForegroundColor": "Black"
        }
    },
    </div>
    <br/> <br/>
    <b>Default configuration, to reset the styling without resetting the whole config file:</b><br/><br/>
    <div style='width: 100%; overflow-y: auto; max-height: 130px;'>
    "styling": {
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
    },
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


def tiny_mce_init_code():
    return """
        tinymce.init({
            selector: '#siac-text-top',
            plugins: 'preview paste importcss searchreplace autolink directionality code visualblocks visualchars image link media codesample table charmap hr nonbreaking toc insertdatetime advlist lists wordcount imagetools textpattern noneditable charmap quickbars',
            menubar: 'edit view insert format tools table',
            toolbar: 'undo redo | bold italic underline strikethrough | fontselect fontsizeselect formatselect | alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | forecolor backcolor removeformat | charmap | image codesample | ltr rtl',
            toolbar_sticky: true,
            resize: false,
            skin: "oxide-dark",
            content_css: "dark",
            image_advtab: true,
            importcss_append: true,
            image_caption: true,
            quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote quickimage quicktable',
            noneditable_noneditable_class: "mceNonEditable",
            toolbar_drawer: 'sliding',
            contextmenu: "link image imagetools table",
            setup: function (ed) {
                ed.on('init', function(args) {
                    setTimeout(function() { $('.tox-notification__dismiss').first().trigger('click'); }, 200);
                });
            }
        });
    """