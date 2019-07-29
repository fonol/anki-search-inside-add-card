#!/usr/bin/env python
# -*- coding: utf-8 -*-
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import runHook, addHook, wrap
import aqt
import aqt.webview
from aqt.addcards import AddCards
from anki.find import Finder
import aqt.editor
from aqt.editor import Editor, EditorWebView
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
import webbrowser
import platform
import functools
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
    from .whoosh.support.charset import accent_map
    from .whoosh.qparser import QueryParser
    from .whoosh.analysis import StandardAnalyzer, CharsetFilter, StemmingAnalyzer
    from .whoosh import classify, highlight, query, scoring, qparser, reading

from .logging import log
from .web import *
from .special_searches import *
from .fts_index import FTSIndex
from .whoosh_index import SearchIndex
from .output import Output
from .textutils import clean, trimIfLongerThan, replaceAccentsWithVowels, expandBySynonyms, remove_fields
from .editor import openEditor, EditDialog
from .tag_find import findBySameTag, buildTagInfo
from .stats import calculateStats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval, getTrueRetentionOverTime

searchingDisabled = config['disableNonNativeSearching'] 
delayWhileTyping = max(500, config['delayWhileTyping'])

contextEvt = None
searchIndex = None
corpus = None
deckMap = None
output = None
edit = None


def initAddon():
    global corpus, output
    global oldOnBridge, origAddNote, origTagKeypress, origSaveAndClose, origEditorContextMenuEvt
    
    oldOnBridge = Editor.onBridgeCmd
    Editor.onBridgeCmd = myOnBridgeCmd
    #todo: Find out if there is a better moment to start index creation
    addHook("profileLoaded", buildIndex)
    origAddNote = AddCards.addNote
    origEditorContextMenuEvt = EditorWebView.contextMenuEvent

    AddCards.addNote = addNoteAndUpdateIndex
    origTagKeypress = TagEdit.keyPressEvent
    TagEdit.keyPressEvent = tagEditKeypress
     
    setupTagEditTimer()
    EditorWebView.contextMenuEvent = editorContextMenuEventWrapper

    origSaveAndClose = EditDialog.saveAndClose
    EditDialog.saveAndClose = editorSaveWithIndexUpdate

    addHook("setupEditorShortcuts", addHideShowShortcut)



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
    aqt.editor._html += getScriptPlatformSpecific(config["addToResultAreaHeight"], delayWhileTyping)
    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    addHook("loadNote", onLoadNote)
   
def editorSaveWithIndexUpdate(dialog):
    origSaveAndClose(dialog)
    # update index
    if searchIndex is not None and dialog.editor is not None and dialog.editor.note is not None:
        searchIndex.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        searchIndex.output.edited[str(dialog.editor.note.id)] = time.time()
 
def checkIndex():
    return searchIndex is not None and searchIndex.output is not None and searchIndex.output.editor is not None and searchIndex.output.editor.web is not None
   
def myOnBridgeCmd(self, cmd):
    """
    Process the various commands coming from the ui - 
    this includes users clicks on option checkboxes, on rendered results, on special searches, etc.
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
        if config["tagClickShouldSearch"]:
            if checkIndex():
                rerenderInfo(self, cmd[11:].strip(), searchByTags=True)
        else:    
            addTag(cmd[11:])
    elif (cmd.startswith("editN ")):
        openEditor(mw, int(cmd[6:]))
    elif (cmd.startswith("pinCrd")):
        setPinned(cmd[6:])
    elif (cmd.startswith("renderTags")):
        searchIndex.output.printTagHierarchy(cmd[11:].split(" "))
    elif (cmd.startswith("randomNotes ") and checkIndex()):
        res = getRandomNotes(searchIndex, [s for s in cmd[11:].split(" ") if s != ""])
        searchIndex.output.printSearchResults(res["result"], res["stamp"])
    elif cmd == "toggleTagSelect":
        if checkIndex():
            searchIndex.tagSelect = not searchIndex.tagSelect
            if searchIndex.tagSelect:
                fillTagSelect()
            else:
                fillDeckSelect(self)
    elif cmd.startswith("searchTag "):
        if checkIndex():
            rerenderInfo(self, cmd[10:].strip(), searchByTags=True)

    elif cmd.startswith("tagInfo "):
        if checkIndex():
            #this renders the popup, but the true retention graph is not yet created
            nids = buildTagInfo(self, cmd[8:], searchIndex.synonyms)
            trueRetentionOverTime = getTrueRetentionOverTime(nids)
            searchIndex.output.showTrueRetStatsForTag(trueRetentionOverTime)
    
    elif cmd.startswith("pSort "):
        if checkIndex():
            parseSortCommand(cmd[6:])
    
        
    elif cmd.startswith("addedSameDay "):
        if checkIndex():
            getCreatedSameDay(searchIndex, self, int(cmd[13:]))
    
    elif cmd == "lastTiming":
        if searchIndex is not None and searchIndex.lastResDict is not None:
            showTimingModal()


    elif cmd.startswith("calInfo "):
        if checkIndex():
            context_html = get_cal_info_context(int(cmd[8:]))
            res = get_notes_added_on_day_of_year(int(cmd[8:]), searchIndex.limit)
            searchIndex.output.print_timeline_info(context_html, res)

    #
    #   Synonyms
    #

    elif cmd == "synonyms":
        if checkIndex():
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
    
    
    elif cmd == "styling":
        showStylingModal(editor)

    elif cmd.startswith("styling "):
        updateStyling(cmd[8:])

    elif cmd == "writeConfig":
        writeConfig()

    #
    #  Index info modal
    #
    
    elif cmd == "indexInfo":
        if checkIndex():
            searchIndex.output.showInModal(getIndexInfo())
    
    #
    #   Special searches
    #
    elif cmd.startswith("predefSearch "):
        parsePredefSearchCmd(cmd, self)
   
    elif cmd.startswith("similarForCard "):
        if checkIndex():
            cid = int(cmd.split()[1])
            min_sim = int(cmd.split()[2])
            res_and_html = find_similar_cards(cid, min_sim, 20)
            searchIndex.output.show_in_modal_subpage(res_and_html[1])


    #
    #   Checkboxes
    #

    elif (cmd.startswith("highlight ")):
        if checkIndex():
            searchIndex.highlighting = cmd[10:] == "on"
    elif (cmd.startswith("searchWhileTyping ")):
        if checkIndex():
            searchIndex.searchWhileTyping = cmd[18:] == "on"
    elif (cmd.startswith("searchOnSelection ")):
        if checkIndex():
            searchIndex.searchOnSelection = cmd[18:] == "on"
    elif (cmd.startswith("tagSearch ")):
        if checkIndex():
            searchIndex.tagSearch = cmd[10:] == "on"
    elif (cmd.startswith("deckSelection")):
        if not checkIndex():
            return
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
        if checkIndex():
            searchIndex.topToggled = True
    
    elif cmd == "toggleTop off":
        if checkIndex():
            searchIndex.topToggled = False

    elif cmd == "toggleGrid on":
        if not checkIndex():
            return
        searchIndex.output.gridView = True
        tryRepeatLastSearch(self)

    elif cmd == "toggleGrid off":
        if not checkIndex():
            return
        searchIndex.output.gridView = False
        tryRepeatLastSearch(self)
    
    elif cmd == "toggleAll on":
        if checkIndex():
            searchIndex.output.uiVisible = True
    elif cmd == "toggleAll off":
        if checkIndex():
            searchIndex.output.uiVisible = False

    elif cmd == "selectCurrent":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and searchIndex is not None:
            searchIndex.output.editor.web.eval("selectDeckWithId(%s);" % deckChooser.selectedId())
    else:
        oldOnBridge(self, cmd)


def parseSortCommand(cmd):
    """
    Helper function to parse the various sort commands (newest/remove tagged/...)
    """
    if cmd == "newest":
        searchIndex.output.sortByDate("desc")
    elif cmd == "oldest":
        searchIndex.output.sortByDate("asc")
    elif cmd == "remUntagged":
        searchIndex.output.removeUntagged()
    elif cmd == "remTagged":
        searchIndex.output.removeTagged()
    elif cmd == "remUnreviewed":
        searchIndex.output.removeUnreviewed()
    elif cmd == "remReviewed":
        searchIndex.output.removeReviewed()    

def parsePredefSearchCmd(cmd, editor):
    """
    Helper function to parse the various predefined searches (last added/longest text/...)
    """
    if not checkIndex():
        return 
    cmd = cmd[13:]
    searchtype = cmd.split(" ")[0]
    limit = int(cmd.split(" ")[1])
    decks = cmd.split(" ")[2:]
    if searchtype == "lowestPerf":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestPerf")
        res = findNotesWithLowestPerformance(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestPerf":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestPerf")
        res = findNotesWithHighestPerformance(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastAdded":
        getCreatedNotesOrderedByDate(searchIndex, editor, decks, limit, "desc")
    elif searchtype == "firstAdded":
        getCreatedNotesOrderedByDate(searchIndex, editor, decks, limit, "asc")
    elif searchtype == "lastModified":
        getLastModifiedNotes(searchIndex, editor, decks, limit)
    elif searchtype == "lowestRet":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestRet")
        res = findNotesWithLowestPerformance(decks, limit, searchIndex.pinned,  retOnly = True)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestRet":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestRet")
        res = findNotesWithHighestPerformance(decks, limit, searchIndex.pinned,  retOnly = True)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "longestText":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestRet")
        res = findNotesWithLongestText(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "randomUntagged":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "randomUntagged")
        res = getRandomUntagged(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestInterval":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestInterval", limit)
        res = getSortedByInterval(decks, limit, searchIndex.pinned, "desc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lowestInterval":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestInterval", limit)
        res = getSortedByInterval(decks, limit, searchIndex.pinned, "asc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastReviewed":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lastReviewed", limit)
        res = getLastReviewed(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastLapses":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lastLapses", limit)
        res = getLastLapses(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "longestTime":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "longestTime", limit)
        res = getByTimeTaken(decks, limit, "desc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "shortestTime":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "shortestTime", limit)
        res = getByTimeTaken(decks, limit, "asc")
        searchIndex.output.printSearchResults(res, stamp)






def onLoadNote(editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    """
    global corpus, output, edit

    #only display in add cards dialog or in the review edit dialog (if enabled)
    if editor.addMode or (config["useInEdit"] and isinstance(editor.parentWindow, EditCurrent)):
        
        if searchIndex is not None and searchIndex.logging:
            log("Trying to insert html in editor")
            log("Editor.addMode: %s" % editor.addMode)

        editor.web.eval("var addToResultAreaHeight = %s; var showTagInfoOnHover = %s;" % (config["addToResultAreaHeight"], "true" if config["showTagInfoOnHover"] else "false"))

        # render the right side (search area) of the editor
        # (the script checks if it has been rendered already)
        editor.web.eval(rightSideHtml(config, searchIndex is not None))


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
            if searchIndex.output is not None and not searchIndex.output.uiVisible:
                editor.web.eval("$('#infoBox').addClass('addon-hidden')")
            if searchIndex.output is not None and searchIndex.output.gridView:
                editor.web.eval('activateGridView();')
            if searchIndex.output is not None:
                #plot.js is already loaded if a note was just added, so this is a lazy solution for now
                searchIndex.output.plotjsLoaded = False
                
        editor.web.eval("onResize()")


        if searchIndex is None or not searchIndex.tagSelect:
            fillDeckSelect(editor)
            if searchIndex is None or searchIndex.lastSearch is None:
                printStartingInfo(editor)
        if corpus is None:
            if searchIndex is not None and searchIndex.logging:
                log("loading notes from anki db...")
            corpus = get_notes_in_collection()
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


def editorContextMenuEventWrapper(view, evt):
    global contextEvt
    contextEvt = evt
    pos = evt.pos()
    determineClickTarget(pos)
    #origEditorContextMenuEvt(view, evt)

def determineClickTarget(pos):
    if not checkIndex():
        return
    searchIndex.output.editor.web.page().runJavaScript("sendClickedInformation(%s, %s)" % (pos.x(), pos.y()), addOptionsToContextMenu)

def addOptionsToContextMenu(clickInfo):
    if clickInfo is not None and clickInfo.startswith("img "):
        try:
            src = clickInfo[4:]
            m = QMenu(searchIndex.output.editor.web)
            a = m.addAction("Open Image in Browser")
            a.triggered.connect(lambda: openImgInBrowser(src))
            cpSubMenu = m.addMenu("Copy Image To Field...")
            for key in searchIndex.output.editor.note.keys():
                cpSubMenu.addAction("Append to %s" % key).triggered.connect(functools.partial(appendImgToField, src, key))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(searchIndex.output.editor.web, contextEvt)
    elif clickInfo is not None and clickInfo.startswith("note "):
        try:
            content = " ".join(clickInfo.split()[2:])
            nid = int(clickInfo.split()[1])
            m = QMenu(searchIndex.output.editor.web)
            a = m.addAction("Find Notes Added On The Same Day")
            a.triggered.connect(lambda: getCreatedSameDay(searchIndex, searchIndex.output.editor, nid))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(searchIndex.output.editor.web, contextEvt)
            
    # elif clickInfo is not None and clickInfo.startswith("span "):
    #     content = clickInfo.split()[1]
        
    else: 
        origEditorContextMenuEvt(searchIndex.output.editor.web, contextEvt)


def setStamp():
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    if checkIndex():
        stamp = searchIndex.output.getMiliSecStamp()
        searchIndex.output.latest = stamp
        return stamp
    return None


def openImgInBrowser(url):
    if len(url) > 0:
        webbrowser.open(url)

def appendNoteToField(content, key):
    if not checkIndex():
        return
    note = searchIndex.output.editor.note
    note.fields[note._fieldOrd(key)] += content
    note.flush()
    searchIndex.output.editor.loadNote()

def appendImgToField(src, key):
    if not checkIndex():
        return
    note = searchIndex.output.editor.note
    note.fields[note._fieldOrd(key)] += "<img src='%s'/>" % src
    note.flush()
    searchIndex.output.editor.loadNote()

def tryRepeatLastSearch(editor = None):
    """
    Sometimes it is useful if we can simply repeat the last search,
    e.g. the user has clicked another deck in the deck select.
    """
    if searchIndex is not None and searchIndex.lastSearch is not None:
        if editor is None and searchIndex.output.editor is not None:
            editor = searchIndex.output.editor
        
        if searchIndex.lastSearch[2] == "default":
            defaultSearchWithDecks(editor, searchIndex.lastSearch[0], searchIndex.selectedDecks)
        # elif searchIndex.lastSearch[2] == "random":
        #     res = getRandomNotes(searchIndex, searchIndex.selectedDecks)
        #     searchIndex.output.printSearchResults(res["result"], res["stamp"])
        elif searchIndex.lastSearch[2] == "lastCreated":
            getCreatedNotesOrderedByDate(searchIndex, editor, searchIndex.selectedDecks, searchIndex.lastSearch[3], "desc")
        elif searchIndex.lastSearch[2] == "firstCreated":
            getCreatedNotesOrderedByDate(searchIndex, editor, searchIndex.selectedDecks, searchIndex.lastSearch[3], "asc")



def getIndexInfo():
    """
    Returns the html that is rendered in the popup that appears on clicking the "info" button
    """
    if searchIndex is None:
        return ""
    html = """<table class="striped" style='width: 100%%'>
               <tr><td>Index Used:</td><td> <b>%s</b></td></tr>
               <tr><td>Initialization:</td><td>  <b>%s s</b></td></tr>
               <tr><td>Notes in Index:</td><td>  <b>%s</b></td></tr>
               <tr><td>Stopwords:</td><td>  <b>%s</b></td></tr>
               <tr><td>Logging:</td><td>  <b>%s</b></td></tr>
               <tr><td>Render Immediately:</td><td>  <b>%s</b></td></tr>
               <tr><td>Tag Click:</td><td>  <b>%s</b></td></tr>
               <tr><td>Timeline:</td><td>  <b>%s</b></td></tr>
               <tr><td>Tag Info on Hover:</td><td>  <b>%s</b></td></tr>
               <tr><td>Show Retention in Results:</td><td>  <b>%s</b></td></tr>
               <tr><td>Window split:</td><td>  <b>%s</b></td></tr>
               <tr><td>Toggle Shortcut:</td><td>  <b>%s</b></td></tr>
             </table>
            """ % (searchIndex.type, str(searchIndex.initializationTime), searchIndex.getNumberOfNotes(), len(searchIndex.stopWords), 
            "On" if searchIndex.logging else "Off", 
            "On" if config["renderImmediately"] else "Off", 
            "Search" if config["tagClickShouldSearch"] else "Add",
            "On" if config["showTimeline"] else "Off", 
            "On" if config["showTagInfoOnHover"] else "Off", 
            "On" if config["showRetentionScores"] else "Off", 
            str(config["leftSideWidthInPercent"]) + " / " + str(100 - config["leftSideWidthInPercent"]),
            config["toggleShortcut"]

            )
    
    return html

def showTimingModal():
    """
    Builds the html and shows the modal which gives some info about the last executed search (timing, query after stopwords etc.)
    """
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


def updateStyling(cmd):
    name = cmd.split()[0]
    value = cmd.split()[1]

    if name == "addToResultAreaHeight":
        if int(value) < 501 and int(value) > -501:
            config[name] = int(value)
            searchIndex.output.editor.web.eval("addToResultAreaHeight = %s; onResize();" % value)
    
    elif name == "renderImmediately":
        m = value == "true" or value == "on"
        config["renderImmediately"] = m
        searchIndex.output.editor.web.eval("renderImmediately = %s;" % ("true" if m else "false"))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"] = m
        searchIndex.output.hideSidebar = m
        searchIndex.output.editor.web.eval("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))

    elif name == "leftSideWidthInPercent":
        config[name] = int(value)
        right = 100 - int(value)
        if checkIndex():
            searchIndex.output.editor.web.eval("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('infoBox').style.width = '%s%%';" % (value, right) )

    elif name == "showTimeline":
        config[name] = value == "true" or value == "on"
        if not config[name] and checkIndex():
            searchIndex.output.editor.web.eval("document.getElementById('cal-row').style.display = 'none'; onResize();")
        elif config[name] and checkIndex():
            searchIndex.output.editor.web.eval("""
            if (document.getElementById('cal-row')) {
                document.getElementById('cal-row').style.display = 'block';
            } else {
                document.getElementById('bottomContainer').children[0].innerHTML = `%s`;
                $('.cal-block-outer').on('mouseenter', function() { calBlockMouseEnter(this);});
            }
            onResize();
            """ % getCalendarHtml())

    elif name == "showTagInfoOnHover":
        config[name] = value == "true" or value == "on"
        if not config[name] and checkIndex():
            searchIndex.output.editor.web.eval("showTagInfoOnHover = false;")
        elif config[name] and checkIndex():
            searchIndex.output.editor.web.eval("showTagInfoOnHover = true;")

def _addToTagList(tmap, name):
    """
    Helper function to build the tag hierarchy.
    """
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = tmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}}) 
    return tmap

def writeConfig():
    mw.addonManager.writeConfig(__name__, config)
    searchIndex.output.editor.web.eval("$('.modal-close').unbind('click')")


def showStylingModal(editor):
    html = stylingModal(config)
    if checkIndex():
        searchIndex.output.showInModal(html)
        searchIndex.output.editor.web.eval("$('.modal-close').on('click', function() {pycmd(`writeConfig`) })")

    



def fillTagSelect(editor = None) :
    """
    Builds the html for the "browse tags" mode in the deck select.
    Also renders the html.
    """
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
    """
    Used if "search on tag entry" is enabled.
    Triggers a search if the user has stopped typing in the tag field.
    """
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
    if checkIndex():
        searchIndex.output.showStats(stats[0], stats[1], stats[2], stats[3])



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
        if searchIndex is not None and searchIndex.output is not None:
            searchIndex.output.updateSingle(res)


def defaultSearchWithDecks(editor, textRaw, decks):
    """
    Uses the searchIndex to clean the input and find notes.
    
    Args:
        decks: list of deck ids (string), if "-1" is contained, all decks are searched
    """
    if len(textRaw) > 2000:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
        return
    cleaned = searchIndex.clean(textRaw)
    if len(cleaned) == 0:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>')" % trimIfLongerThan(textRaw, 100))
        return
    searchIndex.lastSearch = (cleaned, decks, "default")
    searchRes = searchIndex.search(cleaned, decks)
    

def addHideShowShortcut(shortcuts, editor):
    if not "toggleShortcut" in config:
        return
    QShortcut(QKeySequence(config["toggleShortcut"]), editor.widget, activated=toggleAddon)


def toggleAddon():
    if checkIndex():
        searchIndex.output.editor.web.eval("toggleAddon();")


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
            corpus = get_notes_in_collection()
        #build index in background to prevent ui from freezing
        p = ProcessRunnable(target=_buildIndex)
        p.start()


def _buildIndex():
    
    """
    Builds the index. Result is stored in global var searchIndex.
    The index.type is either "Whoosh"/"SQLite FTS3"/"SQLite FTS4"/"SQLite FTS5"
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

        try:
            fld_dict = config['fieldsToExclude']
            fields_to_exclude = {}
            for note_templ_name, fld_names in fld_dict.items():
                model = mw.col.models.byName(note_templ_name)
                if model is None:
                    continue
                fields_to_exclude[model['id']] = []
                for fld in model['flds']:
                    if fld['name'] in fld_names:
                        fields_to_exclude[model['id']].append(fld['ord'])
        except KeyError:
            fields_to_exclude = {} 


        myAnalyzer = StandardAnalyzer(stoplist= None, minsize=1) | CharsetFilter(accent_map)
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
        text = ""
        for note in corpus:
            #if the notes model id is in our filter dict, that means we want to exclude some field(s)
            text = note[1]
            if note[4] in fields_to_exclude:
                text = remove_fields(text, fields_to_exclude[note[4]])
            text = clean(text, usersStopwords)
            writer.add_document(content=text, tags=note[2], did=str(note[3]), nid=str(note[0]), source=note[1])
        writer.commit()
        #todo: allow user to toggle between and / or queries
        og = qparser.OrGroup.factory(0.9)
        #used to parse the main query
        queryparser = QueryParser("content", index.schema, group=og)
        #used to construct a filter query, to limit the results to a set of decks
        deckQueryparser = QueryParser("did", index.schema, group=qparser.OrGroup)
        searchIndex = SearchIndex(index, queryparser, deckQueryparser)
        searchIndex.stopWords = usersStopwords
        searchIndex.fieldsToExclude = fields_to_exclude
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

    try:
        showRetentionScores = config["showRetentionScores"]
    except KeyError:
        showRetentionScores = True
    searchIndex.output.showRetentionScores = showRetentionScores
    try:
        hideSidebar = config["hideSidebar"]
    except KeyError:
        hideSidebar = False
    searchIndex.output.hideSidebar = hideSidebar

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
        html += "<br/>Results are rendered <b>%s</b>." % ("immediately" if config["renderImmediately"] else "with fade-in")
        html += "<br/>Retention is <b>%s</b> in the results." % ("shown" if config["showRetentionScores"] else "not shown")
        html += "<br/>Window split is <b>%s / %s</b>." % (config["leftSideWidthInPercent"], 100 - int(config["leftSideWidthInPercent"]))
        html += "<br/>Shortcut is <b>%s</b>." % (config["toggleShortcut"])

    if searchIndex is None or searchIndex.output is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"
    editor.web.eval("document.getElementById('searchResults').innerHTML = `<div id='startInfo'>%s</div>`;" % html)


def get_notes_in_collection():  
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
        oList = mw.col.db.execute("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where did in %s" %(deckStr))
    else:
        oList = mw.col.db.execute("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid")
    uList = list()
    for id, flds, t, did, mid in oList:
        uList.append((id, flds, t, did, mid))
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



