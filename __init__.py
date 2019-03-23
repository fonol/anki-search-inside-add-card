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
import aqt.stats
from aqt.main import AnkiQt
from aqt.webview import AnkiWebPage
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
    from .whoosh.fields import Schema, TEXT, NUMERIC, KEYWORD
    from whoosh.support.charset import accent_map
    from .whoosh.qparser import QueryParser
    from .whoosh.analysis import StandardAnalyzer, CharsetFilter, StemmingAnalyzer
    from .whoosh import classify, highlight, query, scoring, qparser, reading

from .wikipedia import summary, DisambiguationError
from .web import getScriptPlatformSpecific
from .fts_index import FTSIndex
from .whoosh_index import SearchIndex
from .output import Output
from .textutils import trimIfLongerThan, replaceAccentsWithVowels
from .editor import openEditor
from .stats import calculateStats, findNotesWithLowestPerformance

searchingDisabled = config['disableNonNativeSearching'] 
delayWhileTyping = max(500, config['delayWhileTyping'])
addToResultAreaHeight = max(-500, min(500, config['addToResultAreaHeight']))

searchIndex = None
corpus = None
deckMap = None
output = None
edit = None

def initAddon():
    global corpus, output
    global oldOnBridge, origAddNote
    
    oldOnBridge = Editor.onBridgeCmd
    Editor.onBridgeCmd = myOnBridgeCmd
    #todo: Find out if there is a better moment to start index creation
    addHook("profileLoaded", buildIndex)
    origAddNote = AddCards.addNote

    AddCards.addNote = addNoteAndUpdateIndex


    #main functions to search
    if not searchingDisabled:
        aqt.editor._html += """
            <script>
            function sendContent(event) {
                if ((event && event.repeat) || isFrozen)
                    return;
                let html = "";
                $searchInfo.html("<span style='float: right;'>Searching</span>");
                $fields.each(function(index, elem) {
                    html += $(elem).html() + "\u001f";
                });
                pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
            }
            function sendSearchFieldContent() {
                $searchInfo.html("<span style='float: right;'>Searching</span>");
                html = $('#searchMask').val() + "\u001f";
                pycmd('srchDB ' + selectedDecks.toString() + ' ~ ' + html);
            }

            function searchFor(text) {
                $searchInfo.html("<span style='float: right;'>Searching</span>");
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
                $searchInfo.html("<span style='float: right;'>Searching</span>");
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
    
    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    addHook("loadNote", onLoadNote)
   
   
def myOnBridgeCmd(self, cmd):
    """
    Process the various commands coming from the ui - 
    this includes users clicks on option checkboxes, on rendered results, etc.
    """
    if (not searchingDisabled and cmd.startswith("fldChgd ")):
        rerenderInfo(self, cmd[8:])
    elif (cmd.startswith("srchDB ")):
        rerenderInfo(self, cmd[7:], searchDB = True)
    elif (not searchingDisabled and cmd.startswith("fldSlctd ")):
        rerenderInfo(self, cmd[9:])
    elif (cmd.startswith("wiki ")):
        setWikiSummary(getWikipediaSummary(cmd[5:]))
    elif (cmd.startswith("lastnote")):
        displayLastNote()
    elif (cmd.startswith("nStats ")):
        setStats(cmd[7:], calculateStats(cmd[7:]))
    elif (cmd.startswith("tagClicked ")):
        addTag(cmd[11:])
    elif (cmd.startswith("editN ")):
        openEditor(mw, int(cmd[6:]))
    elif (cmd.startswith("pinCrd")):
        setPinned(cmd[6:])
    elif (cmd.startswith("renderTags")):
        searchIndex.output.printTagHierarchy(cmd[11:].split(" "))
    elif (cmd.startswith("randomNotes ") and searchIndex is not None):
        res = getRandomNotes(cmd[11:])
        searchIndex.output.printSearchResults(res["result"], res["stamp"])
    elif cmd == "indexInfo":
        if searchIndex is not None:
            searchIndex.output.showInModal(getIndexInfo())
    elif cmd.startswith("lowestPerf "):
        if searchIndex is not None:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.output.latest = stamp
            res = findNotesWithLowestPerformance(cmd[11:].split(" "), searchIndex.limit)
            searchIndex.output.printSearchResults(res, stamp)
            searchIndex.output.hideModal()
    elif cmd.startswith("lowestRet "):
        if searchIndex is not None:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.output.latest = stamp
            res = findNotesWithLowestPerformance(cmd[10:].split(" "), searchIndex.limit, retOnly = True)
            searchIndex.output.printSearchResults(res, stamp)
            searchIndex.output.hideModal()
    elif cmd == "specialSearches":
        if searchIndex is not None:
            searchIndex.output.showInModal(getSpecialSearches())
    #used to remember settings when add dialog is closed
    elif (cmd.startswith("highlight ")):
        if searchIndex is not None:
            searchIndex.highlighting = cmd[10:] == "on"
    elif (cmd.startswith("searchWhileTyping ")):
        if searchIndex is not None:
            searchIndex.searchWhileTyping = cmd[18:] == "on"
    elif (cmd.startswith("searchOnSelection ")):
        if searchIndex is not None:
            searchIndex.searchOnSelection = cmd[18:] == "on"
    elif (cmd.startswith("deckSelection ")):
        if searchIndex is not None:
            searchIndex.selectedDecks = [d for d in cmd[14:].split(" ") if d != ""]
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
    if (editor.addMode):
        editor.web.eval(""" 
        
        //check if ui has been rendered already
        if (!$('#outerWr').length) {
    
        $(`#fields`).wrap(`<div class='coll' style='min-width: 200px; width: 50%;  flex-grow: 1 '></div>`);
        $(`
        <div class='coll secondCol' style='flex-grow: 1; width: 50%; height: 100%; border-left: 2px solid #2496dc; margin-top: 20px; padding: 20px; margin-left: 30px; position: relative;' id='infoBox'>
 
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
                        <div style='margin-top: 0px; margin-bottom: 10px;'><button class='deck-list-button' onclick='selectAllDecks();'>Select All</button><button class='deck-list-button center' onclick='unselectAllDecks();'>Select None</button><button class='deck-list-button' onclick="pycmd('selectCurrent')">Select Current</button></div>

                    </div>
                    <div class='flexCol right' style="position: relative;">
                        <table>
                            <tr><td class='tbLb'>Search on selection</td><td><input type='checkbox' id='selectionCb' checked onchange='searchOnSelection = $(this).is(":checked"); sendSearchOnSelection();'/></td></tr>
                            <tr><td class='tbLb'>Search on typing</td><td><input type='checkbox' id='typingCb' checked onchange='searchOnTyping = $(this).is(":checked"); sendSearchOnTyping();'/></td></tr>
                            <tr><td class='tbLb'><mark>Highlighting</mark></td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                            <tr><td class='tbLb'>(WIP) Infobox</td><td><input type='checkbox' onchange='useInfoBox = $(this).is(":checked");'/></td></tr>
                        </table>
                        <div>
                            <div id='freeze-icon' onclick='toggleFreeze(this)'>
                                FREEZE &#10052; 
                            </div>
                            <div id='rnd-icon' onclick='pycmd("randomNotes " + selectedDecks.toString())'>RANDOM &#9861;</div>
                        </div>
                    </div>
                </div>
                
                <div id="resultsArea" style="height: calc(var(--vh, 1vh) * 100 - $height$px); width: 100%; border-top: 1px solid grey;">
                            <div id='toggleTop' onclick='toggleTop(this)'><span class='tag-symbol'>&#10096;</span></div>
                            <div id='indexInfo' onclick='pycmd("indexInfo");'>i</div>
                
                
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
                                    <div class='tooltip tooltip-blue' onclick="toggleTooltip(this);">i
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
                                    </div>
                                <input id='searchMask' placeholder='Browser-like search...' onkeyup='searchMaskKeypress(event)'></input> 
                                <button id='searchBtn' onclick='sendSearchFieldContent()'>Search</button>
                                <button id='specialSearches' onclick='pycmd("specialSearches");'>Special</button>
                            
                            </div>
                        </div>
                    </div>
                    </div>
                </div>`).insertAfter('#fields');
        $(`.coll`).wrapAll('<div id="outerWr" style="width: 100%; display: flex; height: 100%;"></div>');    
        
        }
        $(`.field`).attr("onkeyup", "fieldKeypress(event, this);"); 
        $(`.field`).attr("onkeydown", "moveInHover(event, this);" + $(`.field`).attr("onkeydown")); 
        $('.field').attr('onmouseup', 'getSelectionText()');
        $('.field').attr('onfocusout', 'hideHvrBox()');
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
                editor.web.eval("$('#typingCb').prop('checked', false);")
            if not searchIndex.searchOnSelection:
                editor.web.eval("$('#selectionCb').prop('checked', false);")

        fillDeckSelect(editor)
        if corpus is None:
            corpus = getCorpus()

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
    searchIndex.pinned = pinned
        
def getLastCreatedNote():
    res = mw.col.db.execute("select flds from notes order by id desc limit 1")
    newest = res.fetchone()[0]
    return newest

def getRandomNotes(deckStr):
    if searchIndex is None:
        return
    stamp = searchIndex.output.getMiliSecStamp()
    searchIndex.output.latest = stamp

    if not "-1" in deckStr:
        deckQ =  "(%s)" % ",".join([s for s in deckStr.split(" ") if s != ""])
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

def displayLastNote():
    searchIndex.output.editor.web.eval("document.getElementById('hvrBoxSub').innerHTML = `" + getLastCreatedNote() + "`;")

def getWikipediaSummary(query):
    try:
        return summary(query, sentences=2)
    except:
        return ""

def setWikiSummary(text):
    if len(text) < 5:
        cmd = "document.getElementById('wiki').style.display = `none`;"
    else:
        cmd = "document.getElementById('wiki').style.display = `block`; document.getElementById('wiki').innerHTML = `" + text+ "`;"
    searchIndex.output.editor.web.eval(cmd)


def getIndexInfo():
    if searchIndex is None:
        return ""
    html = """<table style='width: 100%%'>
                <tr><td>Index Used:</td><td> <b>%s</b></td></tr>
               <tr><td>Initialization:</td><td>  <b>%s s</b></td></tr>
               <tr><td>Notes in Index:</td><td>  <b>%s</b></td></tr>
             </table>
            """ % (searchIndex.type, str(searchIndex.initializationTime), searchIndex.getNumberOfNotes())
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
       

def setStats(nid, stats):
    """
    Insert the statistics into the given card.
    """
    cmd = "document.getElementById('" + nid + "').innerHTML += `" + stats + "`;"
    searchIndex.output.editor.web.eval(cmd)



def rerenderInfo(editor, content="", searchDB = False):
    """
    Main function that is executed when a user has typed or manually entered a search.

    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    if (len(content) < 1):
        editor.web.eval("setSearchResults('', 'No results found for empty string')")
    decks = list()
    for s in content[:content.index('~')].split(','):
      decks.append(s.strip())
    if searchIndex is not None:
      if not searchDB:
        content = searchIndex.clean(content[content.index('~ ') + 2:])
      else:
        content = content[content.index('~ ') + 2:].strip()
      if len(content) == 0:
        editor.web.eval("setSearchResults('', 'No results found for empty string')")
        return
      #distinguish between index searches and  Anki db searches
      if searchDB:
        searchRes = searchIndex.searchDB(content, decks)  
      else:
        searchRes = searchIndex.search(content, decks)
      if searchRes is not None:
        if len(searchRes["result"]) > 0:
            searchIndex.output.printSearchResults(searchRes["result"], searchRes["stamp"], editor)
        else:
            editor.web.eval("setSearchResults('', 'No results found.')")







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
        myAnalyzer = StandardAnalyzer(stoplist=usersStopwords) | CharsetFilter(accent_map)
        #StandardAnalyzer(stoplist=usersStopwords)
        schema = whoosh.fields.Schema(content=TEXT(stored=True, analyzer=myAnalyzer), tags=TEXT(stored=True), did=TEXT(stored=True), nid=TEXT(stored=True))
        
        #index needs a folder to operate in
        indexDir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/__init__.py", "") + "/index"
        if not os.path.exists(indexDir):
            os.makedirs(indexDir)
        index = create_in(indexDir, schema)
        #limitmb can be set down
        writer = index.writer(limitmb=256)
        #todo: check if there is some kind of batch insert
        for note in corpus:
            writer.add_document(content=note[1], tags=note[2], did=str(note[3]), nid=str(note[0]))
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
    searchIndex.initializationTime = initializationTime


    try:
        limit = config['numberOfResults']
        if limit <= 0:
            limit = 1
        elif limit > 500:
            limit = 500
    except KeyError:
        limit = 20
    searchIndex.limit = limit
    editor = aqt.mw.app.activeWindow().editor if hasattr(aqt.mw.app.activeWindow(), "editor") else None
    if editor is not None and editor.addMode:
        searchIndex.output.editor = editor
    editor = editor if editor is not None else edit    
    showSearchResultArea(editor, initializationTime=initializationTime)

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

def extractNgrams(noteText, n):
    """
    Not used atm, see SuggestionIndex
    """
    bigrams = list()
    for field in noteText.split("\u001f"):
        bigrams += generate_ngrams(cleanQueryString(field), n)
    return bigrams

def generateMgrams(s, n):
    """
    Not used atm, see SuggestionIndex
    """
    tokens = [token for token in s.split(" ") if token != ""]
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return ["AAAA".join(ngram) for ngram in ngrams]
 






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



