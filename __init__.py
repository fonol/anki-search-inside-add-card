#!/usr/bin/env python
# -*- coding: utf-8 -*-
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import runHook, addHook, wrap
import aqt
import aqt.webview
from aqt.addcards import  AddCards
from anki.find import Finder
import aqt.editor
from aqt.editor import Editor
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.editcurrent import EditCurrent
import aqt.stats
from aqt.main import AnkiQt
from aqt.webview import AnkiWebPage
from datetime import datetime
import os
import random
import sqlite3
import re
import time
import math
import platform
import sys
import html
sys.path.insert(0, os.path.dirname(__file__))

config = mw.addonManager.getConfig(__name__)

try:
    loadWhoosh = not config['useFTS']  or config['disableNonNativeSearching'] 
except KeyError:
    loadWhoosh = True
if loadWhoosh:
    from .whoosh.index import create_in
    from .whoosh.fields import Schema, TEXT, NUMERIC, KEYWORD, ID
    from whoosh.support.charset import accent_map
    from .whoosh.qparser import QueryParser
    from .whoosh.analysis import StandardAnalyzer, CharsetFilter, StemmingAnalyzer
    from .whoosh import classify, highlight, query, scoring, qparser, reading

from .logging import log
from .web import *
from .fts_index import FTSIndex
from .whoosh_index import SearchIndex
from .output import Output
from .textutils import clean, trimIfLongerThan, replaceAccentsWithVowels, expandBySynonyms
from .editor import openEditor, EditDialog
from .tag_find import findBySameTag
from .stats import calculateStats, findNotesWithLowestPerformance

searchingDisabled = config['disableNonNativeSearching'] 
delayWhileTyping = max(500, config['delayWhileTyping'])
addToResultAreaHeight = max(-500, min(500, config['addToResultAreaHeight']))
lastTagEditKeypress = 1

searchIndex = None
corpus = None
deckMap = None
output = None
edit = None

def initAddon():
    global corpus, output
    global oldOnBridge, origAddNote, origTagKeypress, origSaveAndClose
    
    oldOnBridge = Editor.onBridgeCmd
    Editor.onBridgeCmd = myOnBridgeCmd
    #todo: Find out if there is a better moment to start index creation
    addHook("profileLoaded", buildIndex)
    origAddNote = AddCards.addNote

    AddCards.addNote = addNoteAndUpdateIndex
    origTagKeypress = TagEdit.keyPressEvent
    TagEdit.keyPressEvent = tagEditKeypress

    setupTagEditTimer()

    origSaveAndClose = EditDialog.saveAndClose
    EditDialog.saveAndClose = editorSaveWithIndexUpdate

    #main functions to search
    if not searchingDisabled:
        aqt.editor._html += """
            <script>
            function sendContent(event) {
                if ((event && event.repeat) || isFrozen)
                    return;
                let html = "";
                showLoading("Typing");
                $fields.each(function(index, elem) {
                    html += $(elem).html() + "\u001f";
                });
                pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
            }
            function sendSearchFieldContent() {
                showLoading("Browser Search");
                html = $('#searchMask').val() + "\u001f";
                pycmd('srchDB ' + selectedDecks.toString() + ' ~ ' + html);
            }

            function searchFor(text) {
                showLoading("Note Search");
                text += "\u001f";
                pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + text);
            }
            </script>
        """
    else:
        aqt.editor._html += """
            <script>
            function sendContent(event) {
                return;
            }
            function sendSearchFieldContent() {
                showLoading("Note Search");
                html = $('#searchMask').val() + "\u001f";
                pycmd('srchDB ' + selectedDecks.toString() + ' ~ ' + html);
            }

            function searchFor(text) {
                return;
            }
            </script>
        """

    #this inserts all the javascript functions in scripts.js into the editor webview
    aqt.editor._html += getScriptPlatformSpecific(addToResultAreaHeight, delayWhileTyping)
    aqt.editor._html += "<script type='text/javascript' src='http://127.0.0.1:59842/_anki/plot.js'></script>"  
    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    addHook("loadNote", onLoadNote)
   
def editorSaveWithIndexUpdate(dialog):

    # update index
    if searchIndex is not None and dialog.editor is not None and dialog.editor.note is not None:
        searchIndex.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        searchIndex.output.edited[str(dialog.editor.note.id)] = time.time()
    origSaveAndClose(dialog)
   
def myOnBridgeCmd(self, cmd):
    """
    Process the various commands coming from the ui - 
    this includes users clicks on option checkboxes, on rendered results, etc.
    """
    if searchIndex is not None and searchIndex.output.editor is None:
        searchIndex.output.editor = self


    if (not searchingDisabled and cmd.startswith("fldChgd ")):
        rerenderInfo(self, cmd[8:])
    elif (cmd.startswith("srchDB ")):
        rerenderInfo(self, cmd[7:], searchDB = True)
    elif (cmd.startswith("fldSlctd ") and not searchingDisabled and searchIndex is not None):
        if searchIndex.logging:
            log("Selected in field: " + cmd[9:])
        rerenderInfo(self, cmd[9:])
    elif (cmd.startswith("nStats ")):
        setStats(cmd[7:], calculateStats(cmd[7:], searchIndex.output.gridView))
    elif (cmd.startswith("tagClicked ")):
        addTag(cmd[11:])
    elif (cmd.startswith("editN ")):
        openEditor(mw, int(cmd[6:]))
    elif (cmd.startswith("pinCrd")):
        setPinned(cmd[6:])
    elif (cmd.startswith("renderTags")):
        searchIndex.output.printTagHierarchy(cmd[11:].split(" "))
    elif (cmd.startswith("randomNotes ") and searchIndex is not None):
        res = getRandomNotes([s for s in cmd[11:].split(" ") if s != ""])
        searchIndex.output.printSearchResults(res["result"], res["stamp"])
    elif cmd == "toggleTagSelect":
        if searchIndex is not None:
            searchIndex.tagSelect = not searchIndex.tagSelect
            if searchIndex.tagSelect:
                fillTagSelect()
            else:
                fillDeckSelect(self)
    elif cmd.startswith("searchTag "):
        if searchIndex is not None:
            rerenderInfo(self, cmd[10:].strip(), searchByTags=True)

    elif cmd == "lastAdded":
        if searchIndex is not None:
            getLastCreatedNotes(self)
        
    elif cmd.startswith("addedSameDay "):
        if searchIndex is not None:
            getCreatedSameDay(self, int(cmd[13:]))
    
    elif cmd == "lastTiming":
        if searchIndex is not None and searchIndex.lastResDict is not None:
            html = "<h4>Query (stopwords removed, checked SynSets):</h4><div style='width: 100%%; max-height: 200px; overflow-y: auto; margin-bottom: 10px;'><i>%s</i></div>" % searchIndex.lastResDict["query"]
            html += "<h4>Execution time:</h4><table style='width: 100%'>"
            html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Removing Stopwords", searchIndex.lastResDict["time-stopwords"] if searchIndex.lastResDict["time-stopwords"] > 0 else "< 1") 
            html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Checking SynSets", searchIndex.lastResDict["time-synonyms"] if searchIndex.lastResDict["time-synonyms"] > 0 else "< 1") 
            html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Executing Query", searchIndex.lastResDict["time-query"] if searchIndex.lastResDict["time-query"] > 0 else "< 1")
            if searchIndex.type == "Whoosh":
                if searchIndex.lastResDict["highlighting"]:
                    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Highlighting", searchIndex.lastResDict["time-highlighting"] if searchIndex.lastResDict["time-highlighting"] > 0 else "< 1")
                    
            
            elif searchIndex.type == "SQLite FTS5":
                if searchIndex.lastResDict["highlighting"]:
                    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Highlighting", searchIndex.lastResDict["time-highlighting"] if searchIndex.lastResDict["time-highlighting"] > 0 else "< 1")
            else:
                html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Ranking", searchIndex.lastResDict["time-ranking"] if searchIndex.lastResDict["time-ranking"] > 0 else "< 1")
                if searchIndex.lastResDict["highlighting"]:
                    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Highlighting", searchIndex.lastResDict["time-highlighting"] if searchIndex.lastResDict["time-highlighting"] > 0 else "< 1")

            html += "</table>"
            searchIndex.output.showInModal(html)

    #
    #   Synonyms
    #

    elif cmd == "synonyms":
        if searchIndex is not None:
            searchIndex.output.showInModal(getSynonymEditor())
    elif cmd.startswith("saveSynonyms "):
        newSynonyms(cmd[13:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()
    elif cmd.startswith("editSynonyms "):
        editSynonymSet(cmd[13:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()
    elif cmd.startswith("deleteSynonyms "):
        deleteSynonymSet(cmd[15:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()


    #
    #  Index info modal
    #
    
    elif cmd == "indexInfo":
        if searchIndex is not None:
            searchIndex.output.showInModal(getIndexInfo())
    
    #
    #   Special searches
    #
    
    elif cmd.startswith("lowestPerf "):
        if searchIndex is not None:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.output.latest = stamp
            searchIndex.lastSearch = (None, cmd[11:].split(" "), "lowestPerf")
            res = findNotesWithLowestPerformance(cmd[11:].split(" "), searchIndex.limit)
            searchIndex.output.printSearchResults(res, stamp)
            searchIndex.output.hideModal()
    elif cmd.startswith("lowestRet "):
        if searchIndex is not None:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.lastSearch = (None, cmd[10:].split(" "), "lowestRet")
            searchIndex.output.latest = stamp
            res = findNotesWithLowestPerformance(cmd[10:].split(" "), searchIndex.limit, retOnly = True)
            searchIndex.output.printSearchResults(res, stamp)
            searchIndex.output.hideModal()
    elif cmd == "specialSearches":
        if searchIndex is not None:
            searchIndex.output.showInModal(getSpecialSearches())


    #
    #   Checkboxes
    #

    elif (cmd.startswith("highlight ")):
        if searchIndex is not None:
            searchIndex.highlighting = cmd[10:] == "on"
    elif (cmd.startswith("searchWhileTyping ")):
        if searchIndex is not None:
            searchIndex.searchWhileTyping = cmd[18:] == "on"
    elif (cmd.startswith("searchOnSelection ")):
        if searchIndex is not None:
            searchIndex.searchOnSelection = cmd[18:] == "on"
    elif (cmd.startswith("tagSearch ")):
        if searchIndex is not None:
            searchIndex.tagSearch = cmd[10:] == "on"
    elif (cmd.startswith("deckSelection")):
        if searchIndex is not None:
            if searchIndex.logging:
                if len(cmd) > 13:
                    log("Updating selected decks: " + str( [d for d in cmd[14:].split(" ") if d != ""]))
                else:
                    log("Updating selected decks: []")
            if len(cmd) > 13:
                searchIndex.selectedDecks = [d for d in cmd[14:].split(" ") if d != ""]
            else:
                searchIndex.selectedDecks = []
            #repeat last search if default 
            tryRepeatLastSearch(self)

    elif cmd == "toggleTop on":
        if searchIndex is not None:
            searchIndex.topToggled = True
    
    elif cmd == "toggleTop off":
        if searchIndex is not None:
            searchIndex.topToggled = False

    elif cmd == "toggleGrid on":
        if searchIndex is not None and searchIndex.output is not None:
            searchIndex.output.gridView = True
            tryRepeatLastSearch(self)


    elif cmd == "toggleGrid off":
        if searchIndex is not None and searchIndex.output is not None:
            searchIndex.output.gridView = False
            tryRepeatLastSearch(self)

    elif cmd == "selectCurrent":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and searchIndex is not None:
            searchIndex.output.editor.web.eval("selectDeckWithId(%s);" % deckChooser.selectedId())
    else:
        oldOnBridge(self, cmd)

def onLoadNote(editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    """
    global corpus, output, edit
   
    #only display in add cards dialog
    if editor.addMode or (config["useInEdit"] and isinstance(editor.parentWindow, EditCurrent)):
        if searchIndex is not None and searchIndex.logging:
            log("Trying to insert html in editor")
            log("Editor.addMode: %s" % editor.addMode)
        editor.web.eval(""" 
        
        //check if ui has been rendered already
        if (!$('#outerWr').length) {
    
        $(`#fields`).wrap(`<div class='coll' style='min-width: 200px; width: 50%; flex-grow: 1; '></div>`);
        $(`
        <div class='coll secondCol' style='flex-grow: 1; width: 50%; height: 100%; border-left: 2px solid #2496dc; margin-top: 20px; padding: 20px; padding-bottom: 4px; margin-left: 30px; position: relative;' id='infoBox'>


            <div id="a-modal" class="modal">
                <div class="modal-content">
                    <div id='modal-visible'>
                    <div id="modalText"></div>
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
                        <div style='margin-top: 0px; margin-bottom: 10px;'><button class='deck-list-button' onclick='selectAllDecks();'>All</button><button class='deck-list-button center' onclick='unselectAllDecks();'>None</button><button class='deck-list-button' onclick="pycmd('selectCurrent')">Current</button><button class='deck-list-button' id='toggleBrowseMode' onclick="pycmd('toggleTagSelect')"><span class='tag-symbol'>&#9750;</span> Browse Tags</button></div>

                    </div>
                    <div class='flexCol right' style="position: relative;">
                        <table>
                            <tr><td style='text-align: left; padding-bottom: 10px; '> <div id='indexInfo' onclick='pycmd("indexInfo");'>Info</div>
                            <div id='synonymsIcon' onclick='pycmd("synonyms");'>SynSets</div>
                            <div id='lastAdded' onclick='pycmd("lastAdded");'>Last Added</div>
                            </td></tr>
                            <tr><td class='tbLb'>Search on Selection</td><td><input type='checkbox' id='selectionCb' checked onchange='searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                            <tr><td class='tbLb'>Search on Typing</td><td><input type='checkbox' id='typingCb' checked onchange='setSearchOnTyping($(this).is(":checked"));'/></td></tr>
                            <tr><td class='tbLb'>Search on Tag Entry</td><td><input id="tagCb" type='checkbox' checked onchange='setTagSearch(this)'/></td></tr>
                            <tr><td class='tbLb'><mark>&nbsp;Highlighting&nbsp;</mark></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                          <!--  <tr><td class='tbLb'>(WIP) Infobox</td><td><input type='checkbox' onchange='setUseInfoBox($(this).is(":checked"));'/></td></tr> -->
                        </table>
                        <div>
                            <div id='grid-icon' onclick='toggleGrid(this)'>Grid &#9783;</div>
                            <div id='freeze-icon' onclick='toggleFreeze(this)'>
                                FREEZE &#10052; 
                            </div>
                            <div id='rnd-icon' onclick='pycmd("randomNotes " + selectedDecks.toString())'>RANDOM &#9861;</div>
                        </div>
                    </div>
                </div>
                
                <div id="resultsArea" style="height: calc(var(--vh, 1vh) * 100 - $height$px); width: 100%; border-top: 1px solid grey;">
                        <div style='position: absolute; top: 5px; right: 7px; width: 30px;'>
                            <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                           
                        </div>
                <div id='loader'> <div class='signal'></div><br/>Preparing index...</div>
                <div style='height: 100%; padding-bottom: 15px; padding-top: 15px;' id='resultsWrapper'>
                    <div id='searchInfo'></div>
                    <div id='searchResults' style=''></div>
                </div>
                </div>
                    <div id='bottomContainer'>
                    <div class="flexContainer">
                        <div class='flexCol' style='padding-left: 0px; border-top: 1px solid grey;'> 
                            <div class='flexContainer' style="flex-wrap: nowrap;">
                                    <button class='tooltip tooltip-blue' onclick="toggleTooltip(this);">&#9432;
                                        <div class='tooltiptext'>
                                        <table>
                                            <tr><td>dog cat </td><td> must contain both, "dog" and "cat" </td></tr>
                                            <tr><td>dog or cat </td><td> either "dog" or "cat"  </td></tr>
                                            <tr><td>dog (cat or mouse)</td><td>  dog and cat, or dog and mouse </td></tr>
                                            <tr><td>-cat</td><td> without the word "cat" </td></tr>
                                            <tr><td>-cat -mouse </td><td>  neither "cat" nor "mouse"  </td></tr>
                                            <tr><td>"a dog"</td><td>exact phrase </td></tr>
                                            <tr><td>-"a dog" </td><td> without the exact phrase</td></tr>
                                            <tr><td>d_g</td><td> d, <a letter>, g, e.g. dog, dig, dug   </td></tr>
                                            <tr><td>d*g</td><td> d, <zero or more letters>, g, like dg, dog, dung </td></tr>
                                        </table>
                                        </div>
                                    </button>
                                <input id='searchMask' placeholder=' Browser-like search...' onkeyup='searchMaskKeypress(event)'></input> 
                                <button id='searchBtn' onclick='sendSearchFieldContent()'>Search</button>
                                <button id='specialSearches' onclick='pycmd("specialSearches");'>Special</button>
                            
                            </div>
                        </div>
                    </div>
                    </div>
                </div>`).insertAfter('#fields');
        $(`.coll`).wrapAll('<div id="outerWr" style="width: 100%; display: flex; overflow-x: hidden; height: 100%;"></div>');    
        updatePinned();
        } 
        $('.field').on('keyup', fieldKeypress);
        $('.field').attr('onmouseup', 'getSelectionText()');
        var $fields = $('.field');
        var $searchInfo = $('#searchInfo');
        
        window.addEventListener('resize', onResize, true);
        onResize();
        """.replace("$height$", str(280 - addToResultAreaHeight)))
    

        if searchIndex is not None:
            showSearchResultArea(editor)
            #restore previous settings
            if not searchIndex.highlighting:
                editor.web.eval("$('#highlightCb').prop('checked', false);")
            if not searchIndex.searchWhileTyping:
                editor.web.eval("$('#typingCb').prop('checked', false); setSearchOnTyping(false);")
            if not searchIndex.searchOnSelection:
                editor.web.eval("$('#selectionCb').prop('checked', false);")
            if not searchIndex.tagSearch:
                editor.web.eval("$('#tagCb').prop('checked', false);")
            if searchIndex.tagSelect:
                fillTagSelect(editor)
            if not searchIndex.topToggled:
                editor.web.eval("hideTop();")
            if searchIndex.output is not None and searchIndex.output.gridView:
                editor.web.eval('activateGridView();')
            if searchIndex.output is not None:
                #plot.js is already loaded if a note was just added, so this is a lazy solution for now
                searchIndex.output.plotjsLoaded = False


        if searchIndex is None or not searchIndex.tagSelect:
            fillDeckSelect(editor)
            if searchIndex is None or searchIndex.lastSearch is None:
                printStartingInfo(editor)
        if corpus is None:
            if searchIndex is not None and searchIndex.logging:
                log("loading notes from anki db...")
            corpus = getCorpus()
            if searchIndex is not None and searchIndex.logging:
                log("loaded notes: len(corpus): " + str(len(corpus)))

        if searchIndex is not None and searchIndex.output is not None:
            searchIndex.output.editor = editor
    if edit is None and editor is not None:
        edit = editor

def setPinned(cmd):
    """
    Update the pinned search results.
    This is important because they should not be contained in the search results.
    """
    pinned = []
    for id in cmd.split(" "):
        if len(id) > 0:
            pinned.append(id)
    if searchIndex is not None:
        searchIndex.pinned = pinned
        if searchIndex.logging:
            log("Updated pinned: " + str(searchIndex.pinned))

def getRandomNotes(decks):
    if searchIndex is None:
        return
    stamp = searchIndex.output.getMiliSecStamp()
    searchIndex.output.latest = stamp
    searchIndex.lastSearch = (None, decks, "random")

    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""

    limit = searchIndex.limit
    if deckQ:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where did in %s order by random() limit %s" % (deckQ, limit)).fetchall()
    else:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid order by random() limit %s" % limit).fetchall()
    rList = []
    for r in res:
        rList.append((r[1], r[2], r[3], r[0]))
    return { "result" : rList, "stamp" : stamp }


def getLastCreatedNotes(editor):
    stamp = searchIndex.output.getMiliSecStamp()
    searchIndex.output.latest = stamp
    decks = searchIndex.selectedDecks
    searchIndex.lastSearch = (None, decks, "lastCreated")
    if not "-1" in decks and len(decks) > 0:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if len(deckQ) > 0:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where did in %s order by nid desc limit 50" %(deckQ)).fetchall()
    else:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid order by nid desc limit 50").fetchall()
    rList = []
    for r in res:
        #pinned items should not appear in the results
        if not str(r[0]) in searchIndex.pinned:
            #todo: implement highlighting
            rList.append((r[1], r[2], r[3], r[0]))

    if editor.web is not None:
        if len(rList) > 0:
            searchIndex.output.printSearchResults(rList, stamp, editor)
        else:
            editor.web.eval("setSearchResults(``, 'No results found.')")

def tryRepeatLastSearch(editor = None):
    if searchIndex is not None and searchIndex.lastSearch is not None:
        if editor is None and searchIndex.output.editor is not None:
            editor = searchIndex.output.editor
        
        if searchIndex.lastSearch[2] == "default":
            defaultSearchWithDecks(editor, searchIndex.lastSearch[0], searchIndex.selectedDecks)
        # elif searchIndex.lastSearch[2] == "random":
        #     res = getRandomNotes(searchIndex.selectedDecks)
        #     searchIndex.output.printSearchResults(res["result"], res["stamp"])
        elif searchIndex.lastSearch[2] == "lastCreated":
            getLastCreatedNotes(editor)


def getCreatedSameDay(editor, nid):
    stamp = searchIndex.output.getMiliSecStamp()
    searchIndex.output.latest = stamp
    searchIndex.lastSearch = (nid, None, "createdSameDay")
    try:
        nidMinusOneDay = nid - (24 * 60 * 60 * 1000)
        nidPlusOneDay = nid + (24 * 60 * 60 * 1000)

        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where nid > %s and nid < %s order by nid desc" %(nidMinusOneDay, nidPlusOneDay)).fetchall()

        dayOfNote = int(time.strftime("%d", time.localtime(nid/1000)))
        rList = []
        c = 0
        for r in res:
            dayCreated = int(time.strftime("%d", time.localtime(int(r[0])/1000)))
            if dayCreated != dayOfNote:
                continue
            if not str(r[0]) in searchIndex.pinned:
                #todo: implement highlighting
                rList.append((r[1], r[2], r[3], r[0]))
                c += 1
                if c >= searchIndex.limit:
                    break
        if editor.web is not None:
            if len(rList) > 0:
                searchIndex.output.printSearchResults(rList, stamp, editor)
            else:
                editor.web.eval("setSearchResults(``, 'No results found.')")
    except:
        if editor.web is not None:
            editor.web.eval("setSearchResults('', 'Error in calculation.')")

def getIndexInfo():
    if searchIndex is None:
        return ""
    html = """<table style='width: 100%%'>
               <tr><td>Index Used:</td><td> <b>%s</b></td></tr>
               <tr><td>Initialization:</td><td>  <b>%s s</b></td></tr>
               <tr><td>Notes in Index:</td><td>  <b>%s</b></td></tr>
               <tr><td>Stopwords:</td><td>  <b>%s</b></td></tr>
               <tr><td>Logging:</td><td>  <b>%s</b></td></tr>
             </table>
            """ % (searchIndex.type, str(searchIndex.initializationTime), searchIndex.getNumberOfNotes(), len(searchIndex.stopWords), "On" if searchIndex.logging else "Off")
    
    return html

def getSpecialSearches():
    if searchIndex is None:
        return ""
    html = """
                <div class='flexContainer'> 
                    <div style='flex: 1 0'>
                        <b>Worst Performance</b><br/>
                        Find notes on whose cards you performed the worst. Score includes true retention, taken time, and how you rated the cards.
                        Only cards that have been reviewed more than 3 times are counted.
                    </div>
                    <div style='flex: 0 0; padding-left: 10px;'>
                        <button class='modal-close' style='margin-top: auto; margin-bottom: auto;' onclick='specialSearch("lowestPerf")'>Search</button>
                   </div>
                </div>
                  <div class='flexContainer' style='margin-top: 20px;'> 
                    <div style='flex: 1 0'>
                        <b>Lowest Retention</b><br/>
                        Find notes on whose cards you got the lowest retention.
                        Only cards that have been reviewed more than 3 times are counted.
                    </div>
                    <div style='flex: 0 0; padding-left: 10px;'>
                        <button class='modal-close' style='margin-top: auto; margin-bottom: auto;' onclick='specialSearch("lowestRet")'>Search</button>
                   </div>
                </div>
            """
    return html


def _addToTagList(tmap, name):
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = tmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}}) 
    return tmap


def fillTagSelect(editor = None) :
    tmap = {}
    for t in sorted(mw.col.tags.all(), key=lambda t: t.lower()):
        tmap = _addToTagList(tmap, t)
    tmap = dict(sorted(tmap.items(), key=lambda item: item[0].lower()))
    
  
    def iterateMap(tmap, prefix, start=False):
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in tmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); pycmd('searchTag %s')\"><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % (key, "[+]" if value else "", trimIfLongerThan(key, 35), iterateMap(value, full, False)) 
        html += "</ul>"
        return html

    html = iterateMap(tmap, "", True)

    cmd = """document.getElementById('deckSel').innerHTML = `%s`; 
    $('.exp').click(function(e) {
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
    $(".deck-list-button:not(#toggleBrowseMode)").prop("disabled", true);
    $('#toggleBrowseMode').text('Back to Decks');
    $('#toggleBrowseMode').click("pycmd('toggleTagSelect')");
    """ % html
    if editor is not None:
        editor.web.eval(cmd)
    else:
        searchIndex.output.editor.web.eval(cmd)

def fillDeckSelect(editor):
    """
    Fill the selection with user's decks
    """
    global deckMap
    deckMap = dict()
    config = mw.addonManager.getConfig(__name__)
    deckList = config['decks']
    for d in list(mw.col.decks.decks.values()):
       if d['name'] == 'Standard':
          continue
       if deckList is not None and len(deckList) > 0 and d['name'] not in deckList:
           continue
       deckMap[d['name']] = d['id'] 
    
    dmap = {}
    for name, id in deckMap.items():
        dmap = addToDecklist(dmap, id, name)

    dmap = dict(sorted(dmap.items(), key=lambda item: item[0].lower()))

    def iterateMap(dmap, prefix, start=False):
        decks = searchIndex.selectedDecks if searchIndex is not None else []
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in dmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item %s' data-id='%s' onclick='event.stopPropagation(); updateSelectedDecks(this);'><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % ( "selected" if str(deckMap[full]) in decks or decks == [] else "", deckMap[full],  "[+]" if value else "", trimIfLongerThan(key, 35), iterateMap(value, full, False)) 
        html += "</ul>"
        return html

    html = iterateMap(dmap, "", True)

    cmd = """document.getElementById('deckSel').innerHTML = `%s`; 
    $('.exp').click(function(e) {
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
    updateSelectedDecks();
    $('#toggleBrowseMode').html('<span class="tag-symbol">&#9750;</span> Browse Tags');
    $(".deck-list-button").prop("disabled", false);

    """ % html
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
       
def setupTagEditTimer():
    global tagEditTimer
    tagEditTimer = QTimer() 
    tagEditTimer.setSingleShot(True) # set up your QTimer


def tagEditKeypress(self, evt):
    origTagKeypress(self, evt)
    win = aqt.mw.app.activeWindow()
    # dont trigger keypress in edit dialogs opened within the add dialog
    if isinstance(win, EditDialog) or isinstance(win, Browser):
        return
    if searchIndex is not None and searchIndex.tagSearch and len(self.text()) > 0:
        text = self.text()
        try: 
            tagEditTimer.timeout.disconnect() 
        except Exception: pass
        tagEditTimer.timeout.connect(lambda: rerenderInfo(searchIndex.output.editor, text, searchByTags = True))  # connect it to your update function
        tagEditTimer.start(1000)    
              


def setStats(nid, stats):
    """
    Insert the statistics into the given card.
    """
    searchIndex.output.showStats(stats[0], stats[1])



def rerenderInfo(editor, content="", searchDB = False, searchByTags = False):
    """
    Main function that is executed when a user has typed or manually entered a search.

    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    if (len(content) < 1):
        editor.web.eval("setSearchResults(``, 'No results found for empty string')")
    decks = list()
    if "~" in content:
        for s in content[:content.index('~')].split(','):
            decks.append(s.strip())
    if searchIndex is not None:
    
        
        if searchDB:
            content = content[content.index('~ ') + 2:].strip()
            if len(content) == 0:
                editor.web.eval("setSearchResults(``, 'No results found for empty string')")
                return
            searchIndex.lastSearch = (content, decks, "db")
            searchRes = searchIndex.searchDB(content, decks)  

        elif searchByTags:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.output.latest = stamp
            searchIndex.lastSearch = (content, ["-1"], "tags")
            searchRes = findBySameTag(content, searchIndex.limit, [], searchIndex.pinned)

        else:
            if len(content[content.index('~ ') + 2:]) > 2000:
                editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
                return
            content = content[content.index('~ ') + 2:]
            searchRes = searchIndex.search(content, decks)
      
      
        if (searchDB or searchByTags) and editor is not None and editor.web is not None:
            if searchRes is not None:
                if len(searchRes["result"]) > 0:
                    searchIndex.output.printSearchResults(searchRes["result"], stamp if searchByTags else searchRes["stamp"], editor, searchIndex.logging)
                else:
                    editor.web.eval("setSearchResults(``, 'No results found.')")
            else:
                editor.web.eval("setSearchResults(``, 'No results found.')")
       

def rerenderNote(nid):
    res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid).fetchone()
    if res is not None and len(res) > 0:
        if searchIndex is not None:
            searchIndex.output.updateSingle(res)


def defaultSearchWithDecks(editor, textRaw, decks):
    """
    Uses the searchIndex to clean the input and find notes.
    
    Args:
        decks: list of deck ids (string), if "-1" is contained, all decks are searched
    """
    if len(textRaw) > 2000:
        if editor is not None:
            editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
        return
    cleaned = searchIndex.clean(textRaw)
    if len(cleaned) == 0:
        if editor is not None:
            editor.web.eval("setSearchResults(``, 'Query was empty after cleaning')")
        return
    searchIndex.lastSearch = (cleaned, decks, "default")
    searchRes = searchIndex.search(cleaned, decks)
    



def showSearchResultArea(editor=None, initializationTime=0):
    """
    Toggle between the loader and search result area when the index has finsihed building.
    """
    if searchIndex.output is not None and searchIndex.output.editor is not None and searchIndex.output.editor.web is not None:
        searchIndex.output.editor.web.eval("document.getElementById('searchResults').style.display = 'block'; document.getElementById('loader').style.display = 'none';")
    elif editor is not None and editor.web is not None:
        editor.web.eval("document.getElementById('searchResults').style.display = 'block'; document.getElementById('loader').style.display = 'none';")
        

def setInfoboxHtml(html, editor):
    """
    Render the given html inside the hovering box.
    """
    cmd = "document.getElementById('infoBox').innerHTML += `" + html + "`;"
    editor.web.eval(cmd)

def getCurrentContent(editor):
    text = ""
    for f in editor.note.fields:
        text += f
    return text

def addNoteAndUpdateIndex(dialog, note):
    res = origAddNote(dialog, note)
    addNoteToIndex(note)
    return res

def addNoteToIndex(note):
    if searchIndex is not None:
        searchIndex.addNote(note)

def buildIndex():
    global corpus
    if searchIndex is None:
        if corpus is None:
            corpus = getCorpus()
        #build index in background to prevent ui from freezing
        p = ProcessRunnable(target=_buildIndex)
        p.start()


def _buildIndex():
    
    """
    Builds the index. Result is stored in global var searchIndex.
    """
    global searchIndex
    start = time.time()

    config = mw.addonManager.getConfig(__name__)

    try:
        useFTS = config['useFTS']    
    except KeyError:
        useFTS = False
    #fts4 based sqlite reversed index
    if searchingDisabled or useFTS:
        searchIndex = FTSIndex(corpus, searchingDisabled)
        end = time.time()
        initializationTime = round(end - start)
    #whoosh index
    else:
        
        try:
            usersStopwords = config['stopwords']    
        except KeyError:
            usersStopwords = []
        myAnalyzer = StandardAnalyzer() | CharsetFilter(accent_map)
        #StandardAnalyzer(stoplist=usersStopwords)
        schema = whoosh.fields.Schema(content=TEXT(stored=True, analyzer=myAnalyzer), tags=TEXT(stored=True), did=TEXT(stored=True), nid=TEXT(stored=True), source=TEXT(stored=True))
        
        #index needs a folder to operate in
        indexDir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/__init__.py", "") + "/index"
        if not os.path.exists(indexDir):
            os.makedirs(indexDir)
        index = create_in(indexDir, schema)
        #limitmb can be set down
        writer = index.writer(limitmb=256)
        #todo: check if there is some kind of batch insert
        for note in corpus:
            writer.add_document(content=clean(note[1], usersStopwords), tags=note[2], did=str(note[3]), nid=str(note[0]), source=note[1])
        writer.commit()
        #todo: allow user to toggle between and / or queries
        og = qparser.OrGroup.factory(0.9)
        #used to parse the main query
        queryparser = QueryParser("content", index.schema, group=og)
        #used to construct a filter query, to limit the results to a set of decks
        deckQueryparser = QueryParser("did", index.schema, group=qparser.OrGroup)
        searchIndex = SearchIndex(index, queryparser, deckQueryparser)
        searchIndex.stopWords = usersStopwords
        searchIndex.type = "Whoosh"
        end = time.time()
        initializationTime = round(end - start)
        

    searchIndex.finder = Finder(mw.col)
    searchIndex.output = Output()
    searchIndex.output.stopwords = searchIndex.stopWords
    searchIndex.selectedDecks = []
    searchIndex.lastSearch = None
    searchIndex.lastResDict = None
    searchIndex.tagSearch = True
    searchIndex.tagSelect = False
    searchIndex.topToggled = True
    searchIndex.output.edited = {}
    searchIndex.initializationTime = initializationTime
    searchIndex.synonyms = loadSynonyms()
    searchIndex.logging = config["logging"]
    try:
        limit = config['numberOfResults']
        if limit <= 0:
            limit = 1
        elif limit > 500:
            limit = 500
    except KeyError:
        limit = 20
    searchIndex.limit = limit

    if searchIndex.logging:
        log("\n--------------------\nInitialized searchIndex:")
        log("""Type: %s\n# Stopwords: %s \n# Synonyms: %s \nLimit: %s \n""" % (searchIndex.type, len(searchIndex.stopWords), len(searchIndex.synonyms), limit))

    editor = aqt.mw.app.activeWindow().editor if hasattr(aqt.mw.app.activeWindow(), "editor") else None
    if editor is not None and editor.addMode:
        searchIndex.output.editor = editor
    editor = editor if editor is not None else edit    
    showSearchResultArea(editor, initializationTime=initializationTime)
    printStartingInfo(editor)

def addTag(tag):
    """
    Insert the given tag in the tag field at bottom if not already there.
    """
    if tag == "" or searchIndex is None or searchIndex.output.editor is None:
        return
    tagsExisting = searchIndex.output.editor.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return
    
    searchIndex.output.editor.tags.setText(tagsExisting + " " + tag)
    searchIndex.output.editor.saveTags()

def printStartingInfo(editor):
    if editor is None or editor.web is None:
        return
    html = "<h3>Search is <span style='color: green'>ready</span>. (%s)</h3>" %  searchIndex.type if searchIndex is not None else "?"
    if searchIndex is not None:
        html += "Initalized in <b>%s</b> s." % searchIndex.initializationTime
        html += "<br/>Index contains <b>%s</b> notes." % searchIndex.getNumberOfNotes()
        html += "<br/><i>Search on typing</i> delay is set to <b>%s</b> ms." % config["delayWhileTyping"]
        html += "<br/>Logging is turned <b>%s</b>. %s" % ("on" if searchIndex.logging else "off", "You should probably disable it if you don't have any problems." if searchIndex.logging else "")

    if searchIndex is None or searchIndex.output is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"
    editor.web.eval("document.getElementById('searchResults').innerHTML = `<div id='startInfo'>%s</div>`;" % html)


def getCorpus():  
    """
    Reads the collection and builds a list of tuples (note id, note fields as string, note tags, deck id)
    """
    config = mw.addonManager.getConfig(__name__)
    deckList = config['decks']
    deckStr = ""
    for d in list(mw.col.decks.decks.values()):
        if d['name'] in deckList:
           deckStr += str(d['id']) + ","
    if len(deckStr) > 0:
        deckStr = "(%s)" %(deckStr[:-1])
    
    if deckStr:
        oList = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where did in %s" %(deckStr))
    else:
        oList = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid")
    uList = list()
    for id, flds, t, did in oList:
        uList.append((id, flds, t, did))
    return uList
    


class ProcessRunnable(QRunnable):
    """
    Only used to build the index in background atm.
    """
    def __init__(self, target):
        QRunnable.__init__(self)
        self.t = target

    def run(self):
        self.t()

    def start(self):
        QThreadPool.globalInstance().start(self)



initAddon()



