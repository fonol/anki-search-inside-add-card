import platform
import os
import json
import re
import datetime
import time
from aqt import mw

from ..state import get_index, checkIndex
from ..notes import get_note, _get_priority_list, get_avg_pages_read
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


def rightSideHtml(config, searchIndexIsLoaded = False):
    """
    Returns the javascript call that inserts the html that is essentially the right side of the add card dialog.
    The right side html is only inserted if not already present, so it is safe to call this function on every note load.
    """
    config = mw.addonManager.getConfig(__name__)
    addToResultAreaHeight = int(config["addToResultAreaHeight"])
    leftSideWidth = config["leftSideWidthInPercent"]
    if not isinstance(leftSideWidth, int) or leftSideWidth <= 0 or leftSideWidth > 100:
        leftSideWidth = 50
    rightSideWidth = 100 - leftSideWidth
    hideSidebar = config["hideSidebar"]

    return """

        //check if ui has been rendered already
        if (!$('#outerWr').length) {

        $(`#fields`).wrap(`<div class='coll' id='leftSide' style='min-width: 200px; flex-grow: 1; width: %s%%;'></div>`);
        document.getElementById('topbutsleft').innerHTML += "<button id='switchBtn' onclick='showSearchPaneOnLeftSide()'>&#10149; Search</button>";
        $(`<div class='coll secondCol' style='width: %s%%; flex-grow: 1;  height: 100%%;' id='infoBox'>
            <div id='siac-second-col-wrapper'>
            <div id="greyout"></div>
            <div id="a-modal" class="modal">
                <div class="modal-content">
                    <div id='modal-visible'>
                    <div id="modalText"></div>
                    <div id="modal-subpage">
                        <button class='modal-close' onclick='hideModalSubpage()'>&#8592; Back</button>
                        <div id="modal-subpage-inner"></div>
                    </div>
                    <div style='text-align: right; margin-top:25px;'>
                        <button class='modal-close' onclick='$("#a-modal").hide(); hideModalSubpage();'>Close</button>
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
                    <div class='flexCol' style='margin-left: 0px; padding-left: 0px;'>
                        <div id='siac-switch-deck-btn' class='siac-btn-small'  onmouseleave='$(this).removeClass("expanded")' style='display: inline-block; position: relative; min-width: 200px; width: calc(100%% - 1px); text-align: center;' >
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
                    <div class='flexCol right' style="position: relative; min-height: 25px; white-space: nowrap;">
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
                                                    <tr><td class='tbLb'><label for='selectionCb'>Search on Selection</label></td><td><input type='checkbox' id='selectionCb' checked onchange='searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                                                    <tr><td class='tbLb'><label for='typingCb'>Search on Typing</label></td><td><input type='checkbox' id='typingCb' checked onchange='setSearchOnTyping($(this).is(":checked"));'/></td></tr>
                                                    <tr><td class='tbLb'><label for='highlightCb'><mark>&nbsp;Highlighting&nbsp;</mark></label></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                                                    <tr><td class='tbLb'><label for='gridCb'>Grid</label></td><td><input type='checkbox' id='gridCb' onchange='toggleGrid(this)'/></td></tr>
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
                            <div class='rnd-icon' onclick='pycmd("randomNotes " + selectedDecks.toString())'> <span class='icns-add'>RANDOM </span>&#9861; </div>
                            <div class='flds-icon' onclick='sendContent()'> <span class='icns-add'>FIELDS </span>&#9744; </div>
                           <!-- <div class='flds-icon' onclick='pycmd("siac-show-pdfs")'> <span class='icns-add'>PDFs </span>&#128462; </div>-->
                            <div class='pdf-icon' onclick='pycmd("siac-show-pdfs")'>
                                %s
                            </div>
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
                                    <select id='sortSelect'>
                                        <option value='newest' selected='true'>Sort By Newest</option>
                                        <option value='oldest' selected='true'>Sort By Oldest</option>
                                        <option value='remUntagged'>Remove Untagged</option>
                                        <option value='remTagged'>Remove Tagged</option>
                                        <option value='remUnreviewed'>Remove Unreviewed</option>
                                        <option value='remReviewed'>Remove Reviewed</option>
                                    </select>
                                    <div id='sortBtn' onclick='sort();'>GO</div>
                                </fieldset>

                                <fieldset id="searchMaskCol" style="flex: 1 1 auto; font-size: 0.85em;">
                                    <legend id="siac-search-inp-mode-lbl" onclick='toggleSearchbarMode(this);'>Mode: Add-on</legend>
                                    <input id='siac-browser-search-inp' placeholder='' onkeyup='searchMaskKeypress(event)'></input>
                                </fieldset>

                                <fieldset id="predefCol" style="flex: 0 0 auto; font-size: 0.85em;">
                                    <legend>Predefined Searches</legend>
                                    <select id='predefSearchSelect'>
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
                                    <select id='predefSearchNumberSel'>
                                        <option value='10'>10</option>
                                        <option value='50' selected='true'>50</option>
                                        <option value='100'>100</option>
                                        <option value='200'>200</option>
                                        <option value='500'>500</option>
                                    </select>
                                    <div id='lastAdded' onclick='predefSearch();'>GO</div>
                                </fieldset>
                            </div>
                        </div>
                    </div>

                </div>
                </div>
                <div id='siac-reading-modal'>

                </div>
                </div>
                `).insertAfter('#fields');
        $(`.coll`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow-x: hidden; height: 100%%;"></div>');

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
    config["noteScale"],
    pdf_svg(15, 18),
    "display: none;" if searchIndexIsLoaded else "",
    "hidden" if hideSidebar else "",
    getCalendarHtml() if config["showTimeline"] else ""
    )


def get_model_dialog_html():
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

    index = get_index()

    note_id = note[0]
    title = note[1]
    text = note[2]
    source = note[3]
    tags = note[4]
    created = note[6]
    pos = note[10]
    created_dt = datetime.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime.now() - created_dt

    queue = _get_priority_list()
    queue_len = len(queue)


    time_str = "Added %s ago." % utility.misc.date_diff_to_string(diff)
    
    if checkIndex():

        title = title if title is not None and len(title.strip()) > 0 else "Untitled"
        title = utility.text.trim_if_longer_than(title, 50)
        title = title.replace("<", "&lt;").replace(">", "&gt;")
        source = source.strip() if source is not None and len(source.strip()) > 0 else "Empty"
        source_icn = ""

        html = """
            <div style='width: 100%;'>
                    <div id='siac-reading-modal-top-btns'>
                        <div class='siac-btn siac-btn-dark' style='font-size: 8px;' onclick='pycmd("siac-left-side-width");'> / </div>
                        <div class='siac-btn siac-btn-dark' onclick='swapReadingModal();'>&#8644;</div>
                        <div class='siac-btn siac-btn-dark' onclick='toggleReadingModalBars();'>&#x2195;</div>
                        <div class='siac-btn siac-btn-dark' style='padding-left: 7px; padding-right: 7px;' onclick='$("#siac-reading-modal").hide(); if (pdfDisplayed) {{ pdfDisplayed.destroy(); pdfDisplayed = null; }} {save_on_close} $("#siac-reading-modal-text").html("");'>&times;</div>
                    </div>
                    <div id='siac-pdf-tooltip' onclick='event.stopPropagation();' onkeyup='event.stopPropagation();'>
                        <div id='siac-pdf-tooltip-top'></div>
                        <div id='siac-pdf-tooltip-results-area' onkeyup="pdfTooltipClozeKeyup(event);"></div>
                        <div id='siac-pdf-tooltip-bottom'></div>
                        <input id='siac-pdf-tooltip-searchbar' onkeyup='if (event.keyCode === 13) {{pycmd("siac-pdf-tooltip-search " + this.value);}}'></input>
                    </div>
                    <div id='siac-reading-modal-top-bar' data-nid='{note_id}' style='min-height: 90px; width: 100%; display: flex; flex-wrap: nowrap; border-bottom: 2px solid darkorange; margin-bottom: 5px; white-space: nowrap;'>
                        <div style='flex: 1 1; overflow: hidden;'>
                            <h2 style='margin: 0 0 5px 0; white-space: nowrap; overflow: hidden; vertical-align:middle;'>{title}</h2>
                            <h4 style='whitespace: nowrap; margin-top: 5px; color: lightgrey;'>Source: <i>{source}</i></h4>
                            <div id='siac-prog-bar-wr'></div>
                        </div>
                        <div style='flex: 0 0; min-width: 130px; padding: 0 90px 0 10px;'>
                            <span class='siac-timer-btn' onclick='resetTimer(this)'>5</span><span class='siac-timer-btn' onclick='resetTimer(this)'>10</span><span class='siac-timer-btn' onclick='resetTimer(this)'>15</span><span class='siac-timer-btn' onclick='resetTimer(this)'>25</span><span class='siac-timer-btn active' onclick='resetTimer(this)'>30</span><br>
                            <span id='siac-reading-modal-timer'>30 : 00</span><br>
                            <span class='siac-timer-btn' onclick='resetTimer(this)'>45</span><span class='siac-timer-btn' onclick='resetTimer(this)'>60</span><span class='siac-timer-btn' onclick='resetTimer(this)'>90</span><span id='siac-timer-play-btn' class='inactive' onclick='toggleTimer(this);'>Start</span>
                        </div>
                    </div>
                    <div id='siac-reading-modal-text' style='overflow-y: {overflow}; height: calc(90% - 145px); max-height: calc(100% - 235px); font-size: 13px; padding: 20px 20px 0 20px; position: relative;' contenteditable='{is_contenteditable}' {onkeyup}>
                        {text}
                    </div>
                    <div id='siac-reading-modal-bottom-bar' style='width: 100%; border-top: 2px solid darkorange; margin-top: 5px; padding: 2px 0 0 5px; overflow: hidden; position: relative;'>
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
                                <div style='margin: 7px 0 4px 0; display: inline-block;'>Read Next: <span class='siac-queue-picker-icn' onclick='pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span></div><br>
                                <a onclick='if (!pdfLoading) {{noteLoading = true;pdfDisplayed ? pdfDisplayed.destroy() : pdfDisplayed = null; pycmd("siac-user-note-queue-read-head");}}' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;'>First In Queue</a><br>
                                <a onclick='if (!pdfLoading) {{noteLoading = true; pdfDisplayed ? pdfDisplayed.destroy() : pdfDisplayed = null; pycmd("siac-user-note-queue-read-random");}}' class='siac-clickable-anchor'>Random In Queue</a>
                            </div>
                            {queue_readings_list}
                            <div id='siac-marks-display' onclick='markClicked(event);'></div>
                            <div id='siac-queue-infobox-wrapper'>
                                <div id='siac-queue-infobox' onmouseleave='leaveQueueItem();'></div>
                            </div>
                        </div>
                    </div>
                    <div id='siac-timer-popup'>
                        <div style='text-align: center; vertical-align: middle; line-height: 90px; font-weight: bold; font-size: 20px;'>Time is up!</div>
                        <div style='text-align: center;'><div class='siac-btn siac-btn-dark' onclick='this.parentNode.parentNode.style.display="none";'>&nbsp;Ok&nbsp;</div></div>
                    </div>
            </div>
            <script>
            if (readingTimer != null)  {{
                 $('#siac-timer-play-btn').html('Pause').removeClass('inactive');
            }} else if (remainingSeconds !== 1800) {{
                document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
            }}
            iframeIsDisplayed = false;
            noteLoading = false;
            </script>
        """

        #check if it is pdf
        overflow = "auto"
        if source.lower().endswith(".pdf") and utility.misc.file_exists(source):
            editable = False
            overflow = "hidden" 
            text = get_pdf_viewer_html(note_id, source, note[1])
        else:
            editable = len(text) < 50000
        is_contenteditable = "true" if editable else "false"
        onkeyup = "onfocusout='readingModalTextKeyup(this, %s)'"  % (note_id) if len(text) < editable else ""
        save_on_close = "readingModalTextKeyup(document.getElementById(`siac-reading-modal-text`), %s);"  % (note_id) if editable else ""
        queue_info = "Position: <b>%s</b> / <b>%s</b>" % (pos + 1, queue_len) if pos is not None else "Not in Queue."
        queue_info_short = "<b>%s</b> / <b>%s</b>" % (pos + 1, queue_len) if pos is not None else "Not in Queue"

        queue_readings_list = get_queue_head_display(note_id, queue, editable)

        params = dict(note_id = note_id, title = title, source = source, time_str = time_str, text = text, queue_info = queue_info, queue_info_short = queue_info_short, queue_readings_list = queue_readings_list, onkeyup = onkeyup, is_contenteditable = is_contenteditable, save_on_close = save_on_close, overflow=overflow)
        html = html.format_map(params)
        return html
    return ""


def get_reading_modal_bottom_bar(note):
    """
        Returns only the html for the bottom bar, useful if the currently displayed pdf should not be reloaded.
    """
    index = get_index()

    note_id = note[0]
    created = note[6]
    pos = note[10]
    source = note[3]
    created_dt = datetime.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
    diff = datetime.datetime.now() - created_dt
    queue = _get_priority_list()
    queue_len = len(queue)

    time_str = "Added %s ago." % utility.misc.date_diff_to_string(diff)

       
    html = """
            <div id='siac-reading-modal-bottom-bar' style='width: 100%; border-top: 2px solid darkorange; margin-top: 5px; padding: 2px 0 0 5px; overflow: hidden;'>
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
                        <div style='margin: 7px 0 4px 0; display: inline-block;'>Read Next: <span class='siac-queue-picker-icn' onclick='pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span></div><br>
                        <a onclick='noteLoading = true;pycmd("siac-user-note-queue-read-head")' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;'>First In Queue</a><br>
                        <a onclick='noteLoading = true;pycmd("siac-user-note-queue-read-random")' class='siac-clickable-anchor'>Random In Queue</a>
                    </div>
                    {queue_readings_list}
                    <div id='siac-marks-display'  onclick='markClicked(event);'></div>
                    <div id='siac-queue-infobox-wrapper'>
                        <div id='siac-queue-infobox'  onmouseleave='leaveQueueItem();'></div>
                    </div>
                </div>
            </div>
    """
    editable = not source.lower().endswith(".pdf") and len(text) < 50000
    queue_info = "Position: <b>%s</b> / <b>%s</b>" % (pos + 1, queue_len) if pos is not None else "Not in Queue."
    queue_info_short = "<b>%s</b> / <b>%s</b>" % (pos + 1, queue_len) if pos is not None else "Not in Queue"
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

    if should_save:
        save = "readingModalTextKeyup(document.getElementById(`siac-reading-modal-text`), %s);"  % (note_id)
    else:
        save = ""
    hide = config = mw.addonManager.getConfig(__name__)["pdf.queue.hide"]
    queue_head_readings = ""
    for ix, queue_item in enumerate(queue):
        should_greyout = "greyedout" if queue_item[0] == int(note_id) else ""
        if not hide or queue_item[0] == int(note_id) :
            qi_title = utility.text.trim_if_longer_than(queue_item[1], 40) if queue_item[1] is not None and len(queue_item[1]) > 0 else "Untitled"
            qi_title = utility.text.escape_html(qi_title)
        else:
            qi_title = "???????" if queue_item[1] is None or len(queue_item[1]) == 0 else re.sub("[^ ]", "?",queue_item[1])

        hover_actions = "onmouseenter='showQueueInfobox(this, %s);' onmouseleave='leaveQueueItem(this);'" % (queue_item[0]) if not hide else ""
        #if the note is a pdf, show a loader
        should_show_loader = 'document.getElementById("siac-reading-modal-text").innerHTML = ""; showLoader(\"siac-reading-modal-text\", \"Loading Note...\");' if queue_item[3] is not None and queue_item[3].strip().lower().endswith(".pdf") else ""

        queue_head_readings +=  "<a onclick='if (!pdfLoading) {%s %s pdfDisplayed ? pdfDisplayed.destroy() : pdfDisplayed = null; noteLoading = true; pycmd(\"siac-read-user-note %s\"); hideQueueInfobox();}' class='siac-clickable-anchor %s' style='font-size: 12px; font-weight: bold;' %s >%s. %s</a><br>" % (save, should_show_loader, queue_item[0], should_greyout, hover_actions, queue_item[10] + 1, qi_title)
        if ix > 3:
            break

    if hide:
        hide_btn = """<div style='display: inline-block; margin-left: 12px;' class='siac-orange-hover' onclick='pycmd("siac-unhide-pdf-queue %s")'>Show Items</div>""" % note_id
    else:
        hide_btn = """<div style='display: inline-block; margin-left: 12px;' class='siac-orange-hover' onclick='pycmd("siac-hide-pdf-queue %s")'>Hide Items</div>""" % note_id
    html = """
     <div id='siac-queue-readings-list' style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px; user-select: none;'>
                            <div style='margin: 0px 0 3px 0; display: inline-block; color: lightgrey;'>Queue Head:</div>%s<br>
                            %s
                        </div>
    """ % (hide_btn, queue_head_readings)
    return html


def get_pdf_viewer_html(nid, source, title):
    dir = utility.misc.get_web_folder_path()


    search_sources = ""
    config = mw.addonManager.getConfig(__name__)
    urls = config["searchUrls"]
    if urls is not None and len(urls) > 0:
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


    html = """
        <div id='siac-pdf-overlay'>PAGE READ</div>
        <div id='siac-pdf-overlay-top'>
            <div id='siac-pdf-mark-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>M
                <div style='margin-left: 7px;'>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-1' onclick='pycmd("siac-pdf-mark 1 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Revisit</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-2' onclick='pycmd("siac-pdf-mark 2 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Hard</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-3' onclick='pycmd("siac-pdf-mark 3 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Info</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-4' onclick='pycmd("siac-pdf-mark 4 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Cards</div>
                    <div class='siac-mark-btn-inner siac-mark-btn-inner-5' onclick='pycmd("siac-pdf-mark 5 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Bookmark</div>
                </div> 
            </div>
            <div style='display: inline-block; vertical-align: top; margin-top: 3px;' id='siac-pdf-overlay-top-lbl-wrap'></div>
        </div>
        <div id='siac-iframe-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
            <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center;'>Note: Not all Websites allow Embedding!</div>
            <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                <br/>
               {search_sources}
            </div>
        </div>
         <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
        <div id='siac-pdf-top' data-pdfpath="{pdf_path}" data-pdftitle="{pdf_title}" onwheel='pdfMouseWheel(event);'>
            <canvas id="siac-pdf-canvas" style='z-index: 99999; display:inline-block;'></canvas>
            <div id="text-layer" onmouseup='pdfKeyup();' onclick='if (!window.getSelection().toString().length) {{$("#siac-pdf-tooltip").hide();}}' class="textLayer"></div>
        </div>
        <iframe id='siac-iframe' sandbox='allow-scripts'></iframe>
        <div style="width: 100%; text-align: center; margin-top: 15px; position: relative;">
            <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                <div class='siac-btn siac-btn-dark' style="margin-left: 2px; width: 18px;" onclick='pdfScaleChange("down");'>-</div>
                <div class='siac-btn siac-btn-dark' style="width: 22px;" onclick='pdfFitToPage()'>&#8596;</div>
                <div class='siac-btn siac-btn-dark' style="width: 18px;" onclick='pdfScaleChange("up");'>+</div>
                <div class='siac-btn siac-btn-dark' onclick='initImageSelection()' style='margin-left: 5px;'><b>&#9986;</b></div>
                <div class='siac-btn siac-btn-dark active' id='siac-pdf-tooltip-toggle' onclick='togglePDFSelect(this)' style='margin-left: 5px;'><div class='siac-search-icn-dark'></div></div>
                <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
            </div>
            <div style='user-select:none; display: inline-block; position:relative; z-index: 2; padding: 0 5px 0 5px; background: #272828;'>
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
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-read-up-to {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages); pagesRead = Array.from(Array(pdfDisplayedCurrentPage).keys()).map(x => ++x); document.getElementById("siac-pdf-overlay").style.display = "block";document.getElementById("siac-pdf-read-btn").innerHTML = "&times; Unread";updatePdfProgressBar();event.stopPropagation();'><b>Mark Read up to current Pg.</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-unread {nid}"); pagesRead = []; document.getElementById("siac-pdf-overlay").style.display = "none";document.getElementById("siac-pdf-read-btn").innerHTML = "\u2713&nbsp; Read";updatePdfProgressBar();event.stopPropagation();'><b>Mark all as Unread</b></div>
                            <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-read {nid} " + pdfDisplayed.numPages); pagesRead = Array.from(Array(pdfDisplayed.numPages).keys()).map(x => ++x); document.getElementById("siac-pdf-overlay").style.display = "block";document.getElementById("siac-pdf-read-btn").innerHTML = "&times; Unread"; updatePdfProgressBar();event.stopPropagation();'>
                                <b>Mark all as Read</b>
                            </div>
                        </div>
                    </div>
                </div>
                <input id="siac-pdf-page-inp" style="width: 50px;margin-right: 5px;" value="1" type="number" min="1" onkeyup="pdfJumpToPage(event, this);"></input>
            </div>
        </div>
       
        <script>
            showLoader('siac-pdf-top', 'Loading PDF...', -150);
            document.getElementById('siac-pdf-night-btn').innerHTML = pdfColorMode;
            if (pdfTooltipEnabled) {{
                $('#siac-pdf-tooltip-toggle').addClass('active');
            }} else {{
                $('#siac-pdf-tooltip-toggle').removeClass('active');
            }}
        </script>
    """.format_map(dict(nid = nid, pdf_title = title, pdf_path = source, search_sources=search_sources))
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

def get_note_delete_confirm_modal_html(nid):
    note = get_note(nid)
    creation_date = note[6]
    title = utility.text.trim_if_longer_than(note[1], 100) if note[1] is not None and len(note[1]) > 0 else "Untitled Note"
    return """
       <div class='siac-modal-small'>
            <p style='text-align: center;'><b>Delete the following note?</b></p>
            <hr class='siac-modal-sep'/>
            <br>
            <div style='text-align: center; font-size: 14px; margin-bottom: 4px;'><b>%s</b></div>
            <div style='text-align: center; font-size: 14px;'><i>Created: %s</i></div>
            <br><br>
            <div style='text-align: center;'><div class='siac-btn' onclick='$(this.parentNode.parentNode).remove(); removeNote(%s); $("#greyout").hide(); pycmd("siac-delete-user-note %s");' style='margin-right: 10px;'><div class='siac-trash-icn'></div>&nbsp;Delete&nbsp;</div><div class='siac-btn' onclick='$(this.parentNode.parentNode).remove(); $("#greyout").hide();'>&nbsp;Cancel&nbsp;</div></div>
       </div>


    """ % (title, creation_date, nid, nid)

def get_queue_infobox(note, read_stats):
    """
        Returns the html that is displayed in the tooltip which appears when hovering over an item in the queue head.
    """
    #(id, title, text, source, tags, nid, created, modified, reminder, _, position)
    diff = datetime.datetime.now() - datetime.datetime.strptime(note[6], '%Y-%m-%d %H:%M:%S')
    time_str = "Created %s ago." % utility.misc.date_diff_to_string(diff)
    # pagestotal might be None (it is only available if at least one page has been read)
    if read_stats[2] is not None:
        perc = int(read_stats[0] * 10.0 / read_stats[2])
        perc_100 =  int(read_stats[0] * 100.0 / read_stats[2])
        prog_bar = str(perc_100) + " % &nbsp;"
        pages_read = "<div style='width: 100%%; margin-top: 7px; font-weight: bold; text-align: center; font-size: 20px;'>%s / %s</div>" % (read_stats[0], read_stats[2])

        for x in range(0, 10):
            if x < perc:
                prog_bar += "<div class='siac-prog-sq-filled'></div>"
            else:
                prog_bar += "<div class='siac-prog-sq'></div>"
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
        <div style='width: 50px; height: 100%; padding: 5px 5px 5px 0; display: inline-block;'>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 2 "+ $("#siac-reading-modal-top-bar").data("nid"))'>Start</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 5 "+ $("#siac-reading-modal-top-bar").data("nid"))'>End</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-requeue-tt {nid} 6 "+ $("#siac-reading-modal-top-bar").data("nid"))'>Random</div>
            <div class='siac-queue-sched-btn-tt' onclick='hideQueueInfobox(); pycmd("siac-remove-from-queue-tt {nid} " + $("#siac-reading-modal-top-bar").data("nid"))'>Remove</div>
        </div>
    """.format_map(dict(title = note[1], pages_read=pages_read, time_str= time_str, prog_bar= prog_bar, nid = note[0]))
    return html

def stylingModal(config):
    html = """
            <fieldset>
                <span>Exclude note fields from search or display.</span>
                <button class='siac-btn-small' style='float: right;' onclick='pycmd("siac-model-dialog")'>Set Fields</button>
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
            "browserSearchInputBackgroundColor": "#272828",
            "browserSearchInputBorderColor": "grey",
            "browserSearchInputForegroundColor": "beige",
            "selectBackgroundColor": "#272828",
            "selectForegroundColor": "white",
            "timelineBoxBackgroundColor": "#2b2b30",
            "timelineBoxBorderColor": "DarkOrange"
        },
        "general": {
            "buttonBackgroundColor": "#272828",
            "buttonBorderColor": "grey",
            "buttonForegroundColor": "beige",
            "fieldSeparatorColor": "white",
            "highlightBackgroundColor": "SpringGreen",
            "highlightForegroundColor": "Black",
            "keywordColor": "SpringGreen",
            "noteBackgroundColor": "#272828",
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
            "modalBackgroundColor": "#272828",
            "modalBorderColor": "DarkOrange",
            "modalForegroundColor": "beige",
            "stripedTableBackgroundColor": "#2b2b30"
        },
        "topBar": {
            "deckSelectBackgroundColor": "#272828",
            "deckSelectButtonBackgroundColor": "#272828",
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