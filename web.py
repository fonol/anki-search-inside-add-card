import platform
import os
import json
import re
import datetime
import time
from aqt import mw
from .textutils import cleanSynonym

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
    <div style='max-height: 300px; overflow-y: auto; padding-right: 10px;'>
        <table id='synTable' style='width: 100%%; border-collapse: collapse; '>
            <thead><tr style='margin-bottom: 20px;'><th style='word-wrap: break-word; max-width: 100px;'>Set</th><th style='width: 100px; text-align: center;'></th></thead>
            %s
        </table>
    </div>
    <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
"""

config = mw.addonManager.getConfig(__name__)

def getSynonymEditor():
    synonyms = loadSynonyms()
    st = ""
    for c, sList in enumerate(synonyms):
        st += "<tr ><td style='border-top: 1px solid grey;'><div contenteditable='true' onkeydown='synonymSetKeydown(event, this, %s)'>%s</div></td><td style='text-align: right; border-top: 1px solid grey;'><button class='modal-close' onclick='pycmd(\"deleteSynonyms %s\")'>Delete</button></td></tr>" % (c, ", ".join(sList), c)
    if not synonyms:
        return """No synonyms defined yet. Input a set of terms, separated by ',' and hit enter.
        <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
        """
    return synonymEditor % st

def saveSynonyms(synonyms):
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
    try:
        synonyms = config['synonyms']
    except KeyError:
        synonyms = []

    return synonyms


def getScriptPlatformSpecific(addToHeight, delayWhileTyping):
    #get path 
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    
    with open(dir + "/scripts.js") as f:
        script = f.read()
    with open(dir + "/styles.css") as f:
        css = f.read().replace("%", "%%")
    script = script.replace("$del$", str(delayWhileTyping))
    # script = script.replace("$h-1$", str(116 - addToHeight))
    # script = script.replace("$h-2$", str(288 - addToHeight))
    script = script.replace("$h-1$", str(120 - addToHeight))
    script = script.replace("$h-2$", str(291 - addToHeight))
    try:
        deckSelectFontSize = config["deckSelectFontSize"]
    except KeyError:
        deckSelectFontSize = 12

    try:
        noteFontSize = config["noteFontSize"]
    except KeyError:
        noteFontSize = 12

    try: 
        noteForegroundColor = config["noteForegroundColor"]
    except KeyError:
        noteForegroundColor = "black"

    try:
        noteBackgroundColor = config["noteBackgroundColor"]
    except KeyError:
        noteBackgroundColor = "white"
   
    try:
        noteBorderColor = config["noteBorderColor"]
    except KeyError:
        noteBorderColor = "grey"

    try:
        tagBackgroundColor = config["tagBackgroundColor"]
    except KeyError:
        tagBackgroundColor = "#f0506e"
    
    try:
        tagForegroundColor = config["tagForegroundColor"]
    except KeyError:
        tagForegroundColor = "white"
    try:
        tagFontSize = config["tagFontSize"]
    except KeyError:
        tagFontSize = 12
    try:
        deckSelectForegroundColor = config["deckSelectForegroundColor"]
    except KeyError:
        deckSelectForegroundColor = "black"
    
    try:
        deckSelectBackgroundColor = config["deckSelectBackgroundColor"]
    except KeyError:
        deckSelectBackgroundColor = "white"
    try:
        deckSelectHoverForegroundColor = config["deckSelectHoverForegroundColor"]
    except KeyError:
        deckSelectHoverForegroundColor = "white"
    
    try:
        deckSelectHoverBackgroundColor = config["deckSelectHoverBackgroundColor"]
    except KeyError:
        deckSelectHoverBackgroundColor = "#5f6468"

    try:
        deckSelectButtonForegroundColor = config["deckSelectButtonForegroundColor"]
    except KeyError:
        deckSelectButtonForegroundColor = "grey"
    
    try:
        deckSelectButtonBackgroundColor = config["deckSelectButtonBackgroundColor"]
    except KeyError:
        deckSelectButtonBackgroundColor = "white"

    try:
        deckSelectButtonBorderColor = config["deckSelectButtonBorderColor"]
    except KeyError:
        deckSelectButtonBorderColor = "grey"

    try:
        modalBackgroundColor = config["modalBackgroundColor"]
    except KeyError:
        modalBackgroundColor = "white"

    try:
        modalForegroundColor = config["modalForegroundColor"]
    except KeyError:
        modalForegroundColor = "black"

    try:
        browserSearchButtonBorderColor = config["browserSearchButtonBorderColor"]
    except KeyError:
        browserSearchButtonBorderColor = "#2496dc"

    try:
        browserSearchButtonBackgroundColor = config["browserSearchButtonBackgroundColor"]
    except KeyError:
        browserSearchButtonBackgroundColor = "white"

    try:
        browserSearchButtonForegroundColor = config["browserSearchButtonForegroundColor"]
    except KeyError:
        browserSearchButtonForegroundColor = "#2496dc"

    try:
        browserSearchInputBorderColor = config["browserSearchInputBorderColor"]
    except KeyError:
        browserSearchInputBorderColor = "#2496dc"

    try:
        browserSearchInputBackgroundColor = config["browserSearchInputBackgroundColor"]
    except KeyError:
        browserSearchInputBackgroundColor = "white"

    try:
        browserSearchInputForegroundColor = config["browserSearchInputForegroundColor"]
    except KeyError:
        browserSearchInputForegroundColor = "#2496dc"
   
    try:
        infoButtonBorderColor = config["infoButtonBorderColor"]
    except KeyError:
        infoButtonBorderColor = "#2496dc"

    try:
        infoButtonBackgroundColor = config["infoButtonBackgroundColor"]
    except KeyError:
        infoButtonBackgroundColor = "white"

    try:
        infoButtonForegroundColor = config["infoButtonForegroundColor"]
    except KeyError:
        infoButtonForegroundColor = "#2496dc"


    try:
        keywordColor = config["keywordColor"]
    except KeyError:
        keywordColor = "#2496dc"

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

    css = css.replace("$noteFontSize$", str(noteFontSize) + "px")
    css = css.replace("$noteForegroundColor$", noteForegroundColor)
    css = css.replace("$noteBackgroundColor$", noteBackgroundColor)
    css = css.replace("$noteBorderColor$", noteBorderColor)
    css = css.replace("$tagBackgroundColor$", tagBackgroundColor)
    css = css.replace("$tagForegroundColor$", tagForegroundColor)
    css = css.replace("$tagFontSize$", str(tagFontSize) + "px")
    
    css = css.replace("$modalBackgroundColor$", modalBackgroundColor)
    css = css.replace("$modalForegroundColor$", modalForegroundColor)

    css = css.replace("$infoButtonBackgroundColor$", infoButtonBackgroundColor)
    css = css.replace("$infoButtonBorderColor$", infoButtonBorderColor)
    css = css.replace("$infoButtonForegroundColor$", infoButtonForegroundColor)



    css = css.replace("$browserSearchButtonBackgroundColor$", browserSearchButtonBackgroundColor)
    css = css.replace("$browserSearchButtonBorderColor$", browserSearchButtonBorderColor)
    css = css.replace("$browserSearchButtonForegroundColor$", browserSearchButtonForegroundColor)

    css = css.replace("$browserSearchInputBackgroundColor$", browserSearchInputBackgroundColor)
    css = css.replace("$browserSearchInputBorderColor$", browserSearchInputBorderColor)
    css = css.replace("$browserSearchInputForegroundColor$", browserSearchInputForegroundColor)

    css = css.replace("$keywordColor$", keywordColor)

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




def rightSideHtml(config, searchIndexIsLoaded = False):
    """
    Returns the javascript call that inserts the html that is essentially the right side of the add card dialog.
    The right side html is only inserted if not already present, so it is safe to call this function on every note load.
    """
    
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
        $(`<div class='coll secondCol' style='width: %s%%; flex-grow: 1;  height: 100%%; border-left: 2px solid #2496dc; margin-top: 20px; padding: 20px; padding-bottom: 4px; margin-left: 30px; position: relative;' id='infoBox'>

            <div id="greyout"></div>
            <div id="a-modal" class="modal">
                <div class="modal-content">
                    <div id='modal-visible'>
                    <div id="modalText"></div>
                    <div id="modal-subpage">
                        <button class='modal-close' onclick='hideModalSubpage()'>&#8592; Back</button>
                        <div id="modal-subpage-inner">

                        </div>
                    </div>
                        <div style='text-align: right; margin-top:25px;'>
                            <button class='modal-close' onclick='$("#a-modal").hide();'>Close</button>
                        </div>
                    </div>
                    <div id='modal-loader'> <div class='signal'></div><br/>Computing...</div>
                </div>
            </div>
                <div class="flexContainer" id="topContainer">
                    <div class='flexCol' style='margin-left: 0px; padding-left: 0px;'>
                        <div id='deckSelWrapper'> 
                            <table id='deckSel'></table>
                        </div>
                        <div style='margin-top: 0px; margin-bottom: 10px; white-space: nowrap;'><button class='deck-list-button' onclick='selectAllDecks();'>All</button><button class='deck-list-button center' onclick='unselectAllDecks();'>None</button><button class='deck-list-button' onclick="pycmd('selectCurrent')">Current</button><button class='deck-list-button' id='toggleBrowseMode' onclick="pycmd('toggleTagSelect')"><span class='tag-symbol'>&#9750;</span> Browse Tags</button></div>

                    </div>
                    <div class='flexCol right' style="position: relative;">
                        <table class=''>
                            <tr><td style='text-align: left; padding-bottom: 10px; white-space: nowrap;'><div id='indexInfo' onclick='pycmd("indexInfo");'>Info</div>
                            <div id='synonymsIcon' onclick='pycmd("synonyms");'>SynSets</div>
                            <div id='stylingIcon' onclick='pycmd("styling");'>Styling</div>
                           
                            </td></tr>
                            <tr><td class='tbLb'>Search on Selection</td><td><input type='checkbox' id='selectionCb' checked onchange='searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                            <tr><td class='tbLb'>Search on Typing</td><td><input type='checkbox' id='typingCb' checked onchange='setSearchOnTyping($(this).is(":checked"));'/></td></tr>
                            <tr><td class='tbLb'>Search on Tag Entry</td><td><input id="tagCb" type='checkbox' checked onchange='setTagSearch(this)'/></td></tr>
                            <tr><td class='tbLb'><mark>&nbsp;Highlighting&nbsp;</mark></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                        </table>
                        <div id="icns-large">
                            <div class='freeze-icon' onclick='toggleFreeze(this)'> <span class='icns-add'>FREEZE </span>&#10052; </div>
                            <div class='rnd-icon' onclick='pycmd("randomNotes " + selectedDecks.toString())'> <span class='icns-add'>RANDOM </span>&#9861; </div>
                            <div class='grid-icon' onclick='toggleGrid(this)'> <span class='icns-add'>Grid </span>&#9783; </div>
                        </div>
                    </div>
                </div>
               <!--height: calc(var(--vh, 1vh) * 100 - %spx) --> 
                <div id="resultsArea" style="height: 100px;  width: 100%%; border-top: 1px solid grey;">
                    <div style='position: absolute; top: 15px; right: 16px; width: 30px; z-index: 999999;'>
                        <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                    </div>
                    <div id='loader' style='%s'> <div class='signal'></div><br/>Preparing index...</div>
                    <div style='height: 100%%; padding-bottom: 15px; padding-top: 15px; z-index: 100;' id='resultsWrapper'>
                        <div id='searchInfo' class='%s'></div>
                        <div id='searchResults'></div>
                    </div>
                </div>
                <div id='bottomContainer' style='display: block;'>
                    <div style='position: relative;' id='cal-wrapper'>
                        %s
                    </div>
                    <div class="flexContainer">
                        <div class='flexCol' style='padding-left: 0px; '> 
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
                </div>`).insertAfter('#fields');
        $(`.coll`).wrapAll('<div id="outerWr" style="width: 100%%; display: flex; overflow-x: hidden; height: 100%%;"></div>');    
        updatePinned();
        } 
        $('.field').on('keyup', fieldKeypress);
        $('.field').attr('onmouseup', 'getSelectionText()');
        var $fields = $('.field');
        var $searchInfo = $('#searchInfo');
        onResize();
        window.addEventListener('resize', onResize, true);
        $('.cal-block-outer').on('mouseenter', function() { calBlockMouseEnter(this);});
        $(`<div id='cal-info' onmouseleave='calMouseLeave()'></div>`).insertAfter('#outerWr');
""" % (
    leftSideWidth,
    rightSideWidth,
    300 - addToResultAreaHeight,
    "display: none;" if searchIndexIsLoaded else "",
    "hidden" if hideSidebar else "",
    getCalendarHtml() if config["showTimeline"] else ""
       )


def getCalendarHtml():
    start = time.time();
    html = """<div id='cal-row' style="width: 100%%; height: 8px;" onmouseleave='calMouseLeave()'>%s</div>
            """
    #get notes created since the beginning of the year
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    date_year_begin = datetime.datetime(year=datetime.datetime.utcnow().year, month=1, day=1, hour=0 ,minute=0)  
    nid_now = int(time.time()* 1000)
    nid_minus_day_of_year = int(date_year_begin.timestamp() * 1000)

    res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid asc" %(nid_minus_day_of_year, nid_now)).fetchall()

    counts = []
    c = 0
    notes_in_current_day = 0
    for i, r in enumerate(res):
        #date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(r[0]/1000))
        c_day_of_year = time.localtime(r[0]/1000).tm_yday
        notes_in_current_day += 1

        if c_day_of_year != c or i == len(res) - 1:
            if c != 1:
                counts.append(notes_in_current_day)
            for _ in range(0, c_day_of_year - c - 1):
                counts.append(0)
            c = c_day_of_year
            
            notes_in_current_day = 1
    if time.localtime(res[-1][0]/1000).tm_yday != day_of_year and len(counts) < day_of_year:
        counts.append(notes_in_current_day)
    while len(counts) < day_of_year:
        counts.append(0)

    html_content = ""
    size = 1
    c_sum = 0
    added = 0
    for i, notes_in_current_day in enumerate(counts):
        c_sum += notes_in_current_day
        if (i + 1) % size == 0:
            avg = c_sum / size
            if avg > 20:
                color = "cal-three"
            elif avg > 10:
                color = "cal-two"
            elif avg > 0:
                color = "cal-one"
            else: 
                color = ""
            
            html_content += "<div class='cal-block-outer'><div class='cal-block %s %s' data-index='%s'></div></div>" % ("cal-today" if i == len(counts) - 1 else "", color, added)
            c_sum = 0
            added += 1

    html = html % html_content
    taken = (time.time()- start) * 1000
    return html
        

def stylingModal(config):
    return """
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
            <div style='text-align: center'><mark>For other settings, see the <em>config.json</em> file.</mark></div>
                        """ % (config["addToResultAreaHeight"], 
                        "checked='true'" if config["renderImmediately"] else "", 
                        config["leftSideWidthInPercent"], 
                        "checked='true'" if config["hideSidebar"] else "",
                        "checked='true'" if config["showTimeline"] else "",
                        "checked='true'" if config["showTagInfoOnHover"] else ""

                        
                        )
