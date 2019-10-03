import platform
import os
import json
import re
import datetime
import time
from aqt import mw
from .textutils import cleanSynonym, trimIfLongerThan, get_stamp
from .state import get_index, checkIndex
from .notes import get_note, _get_priority_list

#css + js 
all = """
<style>
%s
</style>

<script>
%s
</script>
"""


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


def getSynonymEditor():
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
    
    # dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    # with open(dir + '/synonyms.json', 'w') as outfile:
    #     json.dump(filtered, outfile)
    config["synonyms"] = filtered
    mw.addonManager.writeConfig(__name__, config)

def newSynonyms(sListStr):
    existing = loadSynonyms()
    sList = [cleanSynonym(s) for s in sListStr.split(",") if len(cleanSynonym(s)) > 1]
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
    sList = [cleanSynonym(s) for s in cmd[len(cmd.strip().split()[0]):].split(",") if len(cleanSynonym(s)) > 1]
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


def getScriptPlatformSpecific(addToHeight, delayWhileTyping):
    #get path 
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    config = mw.addonManager.getConfig(__name__)
    
    with open(dir + "/scripts.js") as f:
        script = f.read()
    with open(dir + "/styles.css") as f:
        css = f.read().replace("%", "%%")
    script = script.replace("$del$", str(delayWhileTyping))
   
    try:
        deckSelectFontSize = config["styling"]["topBar"]["deckSelectFontSize"]
    except KeyError:
        deckSelectFontSize = 12
    try:
        noteFontSize = config["styling"]["general"]["noteFontSize"]
    except KeyError:
        noteFontSize = 12

    try: 
        noteForegroundColor = config["styling"]["general"]["noteForegroundColor"]
    except KeyError:
        noteForegroundColor = "black"

    try:
        noteBackgroundColor = config["styling"]["general"]["noteBackgroundColor"]
    except KeyError:
        noteBackgroundColor = "white"
   
    try:
        noteBorderColor = config["styling"]["general"]["noteBorderColor"]
    except KeyError:
        noteBorderColor = "grey"
    try:
        noteHoverBorderColor = config["styling"]["general"]["noteHoverBorderColor"]
    except KeyError:
        noteHoverBorderColor = "#2496dc"
    try:
        tagBackgroundColor = config["styling"]["general"]["tagBackgroundColor"]
    except KeyError:
        tagBackgroundColor = "#f0506e"
    
    try:
        tagForegroundColor = config["styling"]["general"]["tagForegroundColor"]
    except KeyError:
        tagForegroundColor = "white"
    try:
        tagFontSize = config["styling"]["general"]["tagFontSize"]
    except KeyError:
        tagFontSize = 12
    try:
        deckSelectForegroundColor = config["styling"]["topBar"]["deckSelectForegroundColor"]
    except KeyError:
        deckSelectForegroundColor = "black"
    
    try:
        deckSelectBackgroundColor = config["styling"]["topBar"]["deckSelectBackgroundColor"]
    except KeyError:
        deckSelectBackgroundColor = "white"
    try:
        deckSelectHoverForegroundColor = config["styling"]["topBar"]["deckSelectHoverForegroundColor"]
    except KeyError:
        deckSelectHoverForegroundColor = "white"
    
    try:
        deckSelectHoverBackgroundColor = config["styling"]["topBar"]["deckSelectHoverBackgroundColor"]
    except KeyError:
        deckSelectHoverBackgroundColor = "#5f6468"

    try:
        deckSelectButtonForegroundColor = config["styling"]["topBar"]["deckSelectButtonForegroundColor"]
    except KeyError:
        deckSelectButtonForegroundColor = "grey"
    
    try:
        deckSelectButtonBackgroundColor = config["styling"]["topBar"]["deckSelectButtonBackgroundColor"]
    except KeyError:
        deckSelectButtonBackgroundColor = "white"

    try:
        deckSelectButtonBorderColor = config["styling"]["topBar"]["deckSelectButtonBorderColor"]
    except KeyError:
        deckSelectButtonBorderColor = "grey"
    try:
        deckSelectCheckmarkColor = config["styling"]["topBar"]["deckSelectCheckmarkColor"]
    except KeyError:
        deckSelectCheckmarkColor = "grey"

    try:
        modalBackgroundColor = config["styling"]["modal"]["modalBackgroundColor"]
    except KeyError:
        modalBackgroundColor = "white"

    try:
        modalForegroundColor = config["styling"]["modal"]["modalForegroundColor"]
    except KeyError:
        modalForegroundColor = "black"

    try:
        browserSearchButtonBorderColor = config["styling"]["bottomBar"]["browserSearchButtonBorderColor"]
    except KeyError:
        browserSearchButtonBorderColor = "#2496dc"

    try:
        browserSearchButtonBackgroundColor = config["styling"]["bottomBar"]["browserSearchButtonBackgroundColor"]
    except KeyError:
        browserSearchButtonBackgroundColor = "white"

    try:
        browserSearchButtonForegroundColor = config["styling"]["bottomBar"]["browserSearchButtonForegroundColor"]
    except KeyError:
        browserSearchButtonForegroundColor = "#2496dc"

    try:
        browserSearchInputBorderColor = config["styling"]["bottomBar"]["browserSearchInputBorderColor"]
    except KeyError:
        browserSearchInputBorderColor = "#2496dc"

    try:
        browserSearchInputBackgroundColor = config["styling"]["bottomBar"]["browserSearchInputBackgroundColor"]
    except KeyError:
        browserSearchInputBackgroundColor = "white"

    try:
        browserSearchInputForegroundColor = config["styling"]["bottomBar"]["browserSearchInputForegroundColor"]
    except KeyError:
        browserSearchInputForegroundColor = "#2496dc"
   
    try:
        infoButtonBorderColor = config["styling"]["general"]["buttonBorderColor"]
    except KeyError:
        infoButtonBorderColor = "#2496dc"

    try:
        infoButtonBackgroundColor = config["styling"]["general"]["buttonBackgroundColor"]
    except KeyError:
        infoButtonBackgroundColor = "white"

    try:
        infoButtonForegroundColor = config["styling"]["general"]["buttonForegroundColor"]
    except KeyError:
        infoButtonForegroundColor = "#2496dc"
    try:
        highlightBackgroundColor = config["styling"]["general"]["highlightBackgroundColor"]
    except KeyError:
        highlightBackgroundColor = "yellow"
    try:
        highlightForegroundColor = config["styling"]["general"]["highlightForegroundColor"]
    except KeyError:
        highlightForegroundColor = "black"
    try:
        rankingLabelBackgroundColor = config["styling"]["general"]["rankingLabelBackgroundColor"]
    except KeyError:
        rankingLabelBackgroundColor = "#2496dc"
    try:
        rankingLabelForegroundColor = config["styling"]["general"]["rankingLabelForegroundColor"]
    except KeyError:
        rankingLabelForegroundColor = "white"
    try:
        selectBackgroundColor = config["styling"]["bottomBar"]["selectBackgroundColor"]
    except KeyError:
        selectBackgroundColor = "white"
    try:
        selectForegroundColor = config["styling"]["bottomBar"]["selectForegroundColor"]
    except KeyError:
        selectForegroundColor = "black"


    try:
        stripedTableBackgroundColor = config["styling"]["modal"]["stripedTableBackgroundColor"]
    except KeyError:
        stripedTableBackgroundColor = "#f2f2f2"
    try:
        modalBorderColor = config["styling"]["modal"]["modalBorderColor"]
    except KeyError:
        modalBorderColor = "#2496dc"
    try:
        keywordColor = config["styling"]["general"]["keywordColor"]
    except KeyError:
        keywordColor = "#2496dc"
    try:
        fieldSeparatorColor = config["styling"]["general"]["fieldSeparatorColor"]
    except KeyError:
        fieldSeparatorColor = "#2496dc"
    try:
        windowColumnSeparatorColor = config["styling"]["general"]["windowColumnSeparatorColor"]
    except KeyError:
        windowColumnSeparatorColor = "#2496dc"    


    try:
        timelineBoxBackgroundColor = config["styling"]["bottomBar"]["timelineBoxBackgroundColor"]
    except KeyError:
        timelineBoxBackgroundColor = "#595959"
    try:
        timelineBoxBorderColor = config["styling"]["bottomBar"]["timelineBoxBorderColor"]
    except KeyError:
        timelineBoxBorderColor = "#595959"
    try:
        imgMaxHeight = str(config["imageMaxHeight"]) + "px"
    except KeyError:
        imgMaxHeight = "300px"

    css = css.replace("$deckSelectFontSize$", str(deckSelectFontSize) + "px")
    css = css.replace("$deckSelectForegroundColor$", deckSelectForegroundColor)
    css = css.replace("$deckSelectBackgroundColor$", deckSelectBackgroundColor)
    css = css.replace("$deckSelectHoverForegroundColor$", deckSelectHoverForegroundColor)
    css = css.replace("$deckSelectHoverBackgroundColor$", deckSelectHoverBackgroundColor)
    css = css.replace("$deckSelectButtonForegroundColor$", deckSelectButtonForegroundColor)
    css = css.replace("$deckSelectButtonBackgroundColor$", deckSelectButtonBackgroundColor)
    css = css.replace("$deckSelectButtonBorderColor$", deckSelectButtonBorderColor)
    css = css.replace("$deckSelectCheckmarkColor$", deckSelectCheckmarkColor)

    css = css.replace("$noteFontSize$", str(noteFontSize) + "px")
    css = css.replace("$noteForegroundColor$", noteForegroundColor)
    css = css.replace("$noteBackgroundColor$", noteBackgroundColor)
    css = css.replace("$noteBorderColor$", noteBorderColor)
    css = css.replace("$noteHoverBorderColor$", noteHoverBorderColor)
    css = css.replace("$tagBackgroundColor$", tagBackgroundColor)
    css = css.replace("$tagForegroundColor$", tagForegroundColor)
    css = css.replace("$tagFontSize$", str(tagFontSize) + "px")
    
    css = css.replace("$modalBackgroundColor$", modalBackgroundColor)
    css = css.replace("$modalForegroundColor$", modalForegroundColor)

    css = css.replace("$buttonBackgroundColor$", infoButtonBackgroundColor)
    css = css.replace("$buttonBorderColor$", infoButtonBorderColor)
    css = css.replace("$buttonForegroundColor$", infoButtonForegroundColor)

    css = css.replace("$fieldSeparatorColor$", fieldSeparatorColor)
    css = css.replace("$windowColumnSeparatorColor$", windowColumnSeparatorColor)

    css = css.replace("$browserSearchButtonBackgroundColor$", browserSearchButtonBackgroundColor)
    css = css.replace("$browserSearchButtonBorderColor$", browserSearchButtonBorderColor)
    css = css.replace("$browserSearchButtonForegroundColor$", browserSearchButtonForegroundColor)

    css = css.replace("$browserSearchInputBackgroundColor$", browserSearchInputBackgroundColor)
    css = css.replace("$browserSearchInputBorderColor$", browserSearchInputBorderColor)
    css = css.replace("$browserSearchInputForegroundColor$", browserSearchInputForegroundColor)

    css = css.replace("$highlightBackgroundColor$", highlightBackgroundColor)
    css = css.replace("$highlightForegroundColor$", highlightForegroundColor)

    css = css.replace("$rankingLabelBackgroundColor$", rankingLabelBackgroundColor)
    css = css.replace("$rankingLabelForegroundColor$", rankingLabelForegroundColor)

    css = css.replace("$selectBackgroundColor$", selectBackgroundColor)
    css = css.replace("$selectForegroundColor$", selectForegroundColor)

    css = css.replace("$timelineBoxBackgroundColor$", timelineBoxBackgroundColor)
    css = css.replace("$timelineBoxBorderColor$", timelineBoxBorderColor)


    css = css.replace("$keywordColor$", keywordColor)
    css = css.replace("$stripedTableBackgroundColor$", stripedTableBackgroundColor)
    css = css.replace("$modalBorderColor$", modalBorderColor)

    css = css.replace("$imgMaxHeight$", imgMaxHeight)

    try:
        renderImmediately = str(config["renderImmediately"]).lower()
    except KeyError:
        renderImmediately = "false"
    script = script.replace("$renderImmediately$", renderImmediately)

    #replace command key with meta key for mac
    cplatform = platform.system().lower()
    if cplatform == "darwin":
        script = script.replace("event.ctrlKey", "event.metaKey")
    else:
        css = re.sub(r'/\*MAC\*/(.|\n|\r\n)*/\*ENDMAC\*/', "", css, re.S)


    return all % (css, script)


def showSearchResultArea(editor=None, initializationTime=0):
    """
    Toggle between the loader and search result area when the index has finished building.
    """
    js = """
        if (document.getElementById('searchResults')) {
            document.getElementById('searchResults').style.display = 'block'; 
        } 
        if (document.getElementById('loader')) { 
            document.getElementById('loader').style.display = 'none'; 
        }"""
    if checkIndex():
        get_index().output.editor.web.eval(js)
    elif editor is not None and editor.web is not None:
        editor.web.eval(js)

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
                        <div id='siac-switch-deck-btn' class='siac-btn-small' style='display: inline-block; position: relative; min-width: 200px; width: calc(100%% - 1px); text-align: center;' onclick="pycmd('toggleTagSelect')"><span><b>Decks</b> (Click to Switch to Tags)</span>
                            <div class='siac-btn-small-dropdown'>
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
                            <div id='siac-timetable-icn' class='siac-btn-small' style='position: relative; display:inline-block; margin-right: 6px;' onmouseenter='pycmd("siac-user-note-update-btns")'>&nbsp;&nbsp; &#9998; Notes &nbsp;&nbsp;
                                        <div class='siac-btn-small-dropdown'>
                                                <div class='siac-dropdown-item' style='width: 100%%;'>&nbsp;<b>WIP!</b></div>


                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-create-note");'>&nbsp;<b>Create</b></div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-newest");'>&nbsp;Newest</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-random");'>&nbsp;Random</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-search");'>&nbsp;Search ...</div>
                                                <hr>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue");' id='siac-queue-btn'>&nbsp;<b>Queue</b></div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-head");'>&nbsp;<b>Read 1st</b></div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-read-random");'>&nbsp;Read [Rnd]</div>
                                                <div class='siac-dropdown-item' style='width: 100%%;' onclick='pycmd("siac-user-note-queue-random");'>&nbsp;List [Rnd]</div>

                                </div>
                            </div>
                            <div id='siac-settings-icn' class='siac-btn-small' style='position: relative; display:inline-block; min-width: 140px; text-align: center; '>&nbsp; Settings & Info &nbsp;
                                        <div class='siac-btn-small-dropdown'>
                                                <table style='width: 100%%'>
                                                    <tr><td class='tbLb'>Search on Selection</td><td><input type='checkbox' id='selectionCb' checked onchange='searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                                                    <tr><td class='tbLb'>Search on Typing</td><td><input type='checkbox' id='typingCb' checked onchange='setSearchOnTyping($(this).is(":checked"));'/></td></tr>
                                                    <tr><td class='tbLb'><mark>&nbsp;Highlighting&nbsp;</mark></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                                                    <tr><td class='tbLb'>Grid</td><td><input type='checkbox' id='gridCb' onchange='toggleGrid(this)'/></td></tr>
                                                 </table>
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
                                    <legend>Browser Search</legend>
                                    <input id='searchMask' placeholder='' onkeyup='searchMaskKeypress(event)'></input> 
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
    "display: none;" if searchIndexIsLoaded else "",
    "hidden" if hideSidebar else "",
    getCalendarHtml() if config["showTimeline"] else ""
    )

def printStartingInfo(editor):
    if editor is None or editor.web is None:
        return
    config = mw.addonManager.getConfig(__name__)
    searchIndex = get_index()
    html = "<h3>Search is <span style='color: green'>ready</span>. (%s)</h3>" %  searchIndex.type if searchIndex is not None else "?"
    if searchIndex is not None:
        html += "Initalized in <b>%s</b> s." % searchIndex.initializationTime
        if not searchIndex.creation_info["index_was_rebuilt"]:
            html += " No changes detected, the index was not rebuilt."
        html += "<br/>Index contains <b>%s</b> notes." % searchIndex.get_number_of_notes()
        html += "<br/>Index is always rebuilt if smaller than <b>%s</b> notes." % config["alwaysRebuildIndexIfSmallerThan"]
        html += "<br/><i>Search on typing</i> delay is set to <b>%s</b> ms." % config["delayWhileTyping"]
        html += "<br/>Logging is turned <b>%s</b>. %s" % ("on" if searchIndex.logging else "off", "You should probably disable it if you don't have any problems." if searchIndex.logging else "")
        html += "<br/>Results are rendered <b>%s</b>." % ("immediately" if config["renderImmediately"] else "with fade-in")
        html += "<br/>Tag Info on hover is <b>%s</b>.%s" % ("shown" if config["showTagInfoOnHover"] else "not shown", (" Delay: [<b>%s</b> ms]" % config["tagHoverDelayInMiliSec"]) if config["showTagInfoOnHover"] else "")
        html += "<br/>Image max height is <b>%s</b> px." % config["imageMaxHeight"]
        html += "<br/>Retention is <b>%s</b> in the results." % ("shown" if config["showRetentionScores"] else "not shown")
        html += "<br/>Window split is <b>%s / %s</b>." % (config["leftSideWidthInPercent"], 100 - int(config["leftSideWidthInPercent"]))
        html += "<br/>Shortcut is <b>%s</b>." % (config["toggleShortcut"])

    if searchIndex is None or searchIndex.output is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"
    editor.web.eval("document.getElementById('searchResults').innerHTML = `<div id='startInfo'>%s</div>`;" % html)



def getCalendarHtml():
    html = """<div id='cal-row' style="width: 100%%; height: 8px;" onmouseleave='calMouseLeave()'>%s</div>
            """
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
        
def display_model_dialog():
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
        html += "<div class='siac-model-name'>%s</div>" % trimIfLongerThan(m["name"], 40)
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
    index.output.show_in_modal_subpage(html)


def note_edit_dialog(note_id = -1):
    """
        Returns the html for the note creation/edit dialog.
        Returns just the content, excluding the dialog window, but including any buttons.
        If a note_id is given, it will edit the selected note, else a new note will be created.
    """

    html = """
        <div style='height: 10%;'>
            <h3 style='margin-top: 5px;'>{header}</h3>
        </div>
        <div style='height: 80%; overflow-y: auto; width: 100%;'>
            <span>Title</span>
            <input id='siac-note-title-inp' style='width: 100%;' type='text' value='{title}'></input>
            <br><br>
            <span>Text</span>
            <div id='siac-note-text-inp' contenteditable='true'>{text}</div>
            <span>Source</span>
            <input id='siac-note-source-inp' style='width: 100%;' type='text' value='{source}'></input>
            <span>Tags</span>
            <input id='siac-note-tag-inp' style='width: 100%;' type='text' value='{tags}'></input>
        </div>
        <div style='height: 30px; padding-top: 5px; width: 100%; text-align: right;'>
            <div class='siac-btn-small'>Save</div>
            <div class='siac-btn-small'>Close</div>
        </div>
    """

    note = None
    if note_id >= 0:
        note = get_note(note_id)
    
    header = "Create a new Note" if note_id == -1 else "Edit Note"
    title = note[1] if note is not None else ""
    text = note[2] if note is not None else ""
    source = note[3] if note is not None else ""
    tags = note[4] if note is not None else ""
    pos = ("Position in Reading Queue: <b>%s</b>" % note[10]) if note is not None else "Not in Queue."
    params = dict(header = header, title = title, text = text, source = source, tags = tags, pos = pos)
    html = html.format_map(params)
    return html



def display_note_reading_modal(note_id):
    note = get_note(note_id)
    index = get_index()

    title = note[1]
    text = note[2]
    source = note[3]
    tags = note[4]
    created = note[6]
    pos = note[10]
    created_dt = datetime.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
    now = datetime.datetime.now()
    diff = now - created_dt

    queue = _get_priority_list()
    queue_len = len(queue)
      
    time_str = "Added %s %s ago."

    if diff.total_seconds() / 60 < 2.0:
        time_str = time_str % ("1", "minute")
    elif diff.total_seconds() / 3600 < 1.0:
        time_str = time_str % (int(diff.total_seconds() / 60), "minutes")
    elif diff.total_seconds() / 86400 < 1.0:
        time_str = time_str % (int(diff.total_seconds() / 3600), "hours")
    elif diff.total_seconds() / 86400 >= 1.0 and diff.total_seconds() / 86400 < 2.0:
        time_str = time_str % ("1", "day")
    else:
        time_str = time_str % (int(diff.total_seconds() / 86400), "days")

    if checkIndex():
        tag_str = ""
        tags_split = tags.split()
        tm = index.output.getTagMap(tags_split)
        totalLength = sum([len(k) for k,v in tm.items()])
        maxLength = 50
        maxCount = 7 
        if len(tm) <= maxCount or totalLength < maxLength:
            for t, s in tm.items():
                if len(s) > 0:
                    tagData = " ".join(iterateTagmap({t : s}, ""))
                    if len(s) == 1 and tagData.count("::") < 2 and not t in tags_split:
                        tag_str += "<div class='tagLbl' style='display: inline; margin: 0 5px 0 0;'>%s</div>" %(trimIfLongerThan(tagData.split(" ")[1], maxLength))
                    else:
                        tag_str += "<div class='tagLbl' style='display: inline;margin: 0 5px 0 0;'>%s</div>" %(trimIfLongerThan(t, maxLength) + " (+%s)"% len(s))
                else:
                    tag_str += "<div class='tagLbl' style='display: inline;margin: 0 5px 0 0;'>%s</div>" %(trimIfLongerThan(t, maxLength))
        else:
            tagData = " ".join(iterateTagmap(tm, ""))
            tag_str += "<div class='tagLbl' style='display: inline;margin: 0 5px 0 0;'>%s</div>" %(str(len(tm)) + " tags ...")

        source = source if source is not None and len(source.strip()) > 0 else "Empty"
        title = title if title is not None and len(title.strip()) > 0 else "Untitled"
        title = trimIfLongerThan(title, 50)

        html = """
            <div style='width: 100%;'>
                <div style='height: 10%; min-height: 90px; width: 100%; border-bottom: 2px solid darkorange; margin-bottom: 5px; white-space: nowrap;'>
                    <div style='display: inline-block; width: calc(100%-154px);'>   
                        <span class='reading-modal-close-icn' onclick='$("#siac-reading-modal").hide();{save_on_close}'>&times;</span>
                        <h2 style='margin: 0 0 5px 0;'>{title}</h2>
                        <h4 style='whitespace: nowrap; margin-top: 5px;'>Source: <i>{source}</i></h4> 
                    </div>
                    <div style='width: 150px; float: right;'>
                        <span class='siac-timer-btn' onclick='resetTimer(this)'>5</span><span class='siac-timer-btn' onclick='resetTimer(this)'>10</span><span class='siac-timer-btn' onclick='resetTimer(this)'>15</span><span class='siac-timer-btn' onclick='resetTimer(this)'>25</span><span class='siac-timer-btn active' onclick='resetTimer(this)'>30</span><br>
                        <span id='siac-reading-modal-timer'>30 : 00</span><br>
                        <span class='siac-timer-btn' onclick='resetTimer(this)'>45</span><span class='siac-timer-btn' onclick='resetTimer(this)'>60</span><span class='siac-timer-btn' onclick='resetTimer(this)'>90</span><span id='siac-timer-play-btn' class='inactive' onclick='toggleTimer(this);'>Start</span>
                    </div>
                </div>
                <div id='siac-reading-modal-text' style='overflow-y: auto; height: calc(90% - 140px); max-height: calc(100% - 230px); font-size: 13px; padding: 20px 20px 0 20px;' contenteditable='{is_contenteditable}' {onkeyup}>
                    {text}
                </div>
                <div style='width: 100%; border-top: 2px solid darkorange; margin-top: 5px; padding: 5px 0 0 5px;'>
                    <div style='width: 100%; height: calc(100% - 5px); display: inline-block; padding-top: 5px; white-space: nowrap;'>
                       
                        <div class='siac-queue-sched-btn active' onclick='queueSchedBtnClicked(this);'>Keep Position</div>
                        <div style='display: inline-block; height: 90px; margin: 0 10px 0 10px; border: 0 0 0 2px solid lightgrey; border-style: dotted;'></div>
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
                        <div style='display: inline-block; height: 90px; vertical-align: top; margin-left: 20px;'>
                            <span style='vertical-align: top;' id='siac-queue-lbl'>{queue_info}</span><br>
                            <span style='margin-top: 5px;'>{time_str}</span> <br>
                            <div style='margin: 7px 0 4px 0; display: inline-block;'>Read Next:</div><br>
                            <a onclick='pycmd("siac-user-note-queue-read-head")' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;'>First In Queue</a><br>
                            <a onclick='pycmd("siac-user-note-queue-read-random")' class='siac-clickable-anchor'>Random In Queue</a>
                        </div>
                    </div>
                </div>
                <div id='siac-timer-popup'>
                    <div style='text-align: center; vertical-align: middle; line-height: 90px; font-weight: bold; font-size: 20px;'>Time is up!</div>
                    <div style='text-align: center;'><div class='siac-btn-small' onclick='this.parentNode.parentNode.style.display="none";'>&nbsp;Ok&nbsp;</div></div>
                </div>
            </div>

        """
        editable = len(text) < 50000
        is_contenteditable = "true" if editable else "false"
        onkeyup = "onfocusout='readingModalTextKeyup(this, %s)'"  % (note_id) if len(text) < editable else ""
        save_on_close = "readingModalTextKeyup(document.getElementById(`siac-reading-modal-text`), %s)'"  % (note_id) if editable else ""
        queue_info = "Position in Queue: <b>%s</b> / <b>%s</b>" % (pos + 1, queue_len) if pos is not None else "Not in Queue."

        params = dict(note_id = note_id, title = title, source = source, time_str = time_str, text = text, queue_info = queue_info, pos = pos , queue_len = queue_len, tag_str = tag_str, onkeyup = onkeyup, is_contenteditable = is_contenteditable, save_on_close = save_on_close)
        html = html.format_map(params)
        index.output.show_in_large_modal(html)
        index.output.editor.web.eval("clearInterval(readingTimer);")

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
                <span>This controls whether the small info box will be shown when a tag is hovered over with the mouse.</span> 
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
            <div style='text-align: center'><mark>For other settings, see the <em>config.json</em> file.</mark></div>
                        """ % (config["addToResultAreaHeight"], 
                        "checked='true'" if config["renderImmediately"] else "", 
                        config["leftSideWidthInPercent"], 
                        "checked='true'" if config["hideSidebar"] else "",
                        "checked='true'" if config["showTimeline"] else "",
                        "checked='true'" if config["showTagInfoOnHover"] else "",
                        config["tagHoverDelayInMiliSec"],
                       config["alwaysRebuildIndexIfSmallerThan"],
                       "checked='true'" if config["removeDivsFromOutput"] else ""
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
            "windowColumnSeparatorColor" : "#2496dc",
            "rankingLabelBackgroundColor": "#2496dc",
            "rankingLabelForegroundColor": "white",
            "noteFontSize": 12,
            "noteForegroundColor": "black",
            "noteBackgroundColor": "white",
            "noteBorderColor": "grey",
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
