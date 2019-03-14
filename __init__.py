#!/usr/bin/env python
# -*- coding: utf-8 -*-
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import runHook, addHook, wrap
import aqt
import aqt.webview
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
from .db import FTSIndex
from .output import Output
from .textutils import trimIfLongerThan

searchingDisabled = config['disableNonNativeSearching'] 
addToResultAreaHeight = max(-500, min(500, config['addToResultAreaHeight']))

searchIndex = None
sugIndex = None
corpus = None
deckMap = None
output = None
sugRequestRunning = False


def initAddon():
    global corpus, output
    global oldOnBridge
    oldOnBridge = Editor.onBridgeCmd
    Editor.onBridgeCmd = myOnBridgeCmd
    #todo: Find out if there is a better moment to start index creation
    addHook("profileLoaded", buildIndex)
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
    aqt.editor._html += getScriptPlatformSpecific()
    
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
    # elif (cmd.startswith("fldSg")):
    #     renderSuggestions(self, cmd[6:])
    elif (cmd.startswith("nStats ")):
        setStats(cmd[7:], calculateStats(cmd[7:]))
    elif (cmd.startswith("tagClicked ")):
        addTag(cmd[11:])
    elif (cmd.startswith("pinCrd")):
        setPinned(cmd[6:])
    elif (cmd.startswith("renderTags")):
        searchIndex.output.printTagHierarchy(cmd[11:].split(" "))
    elif (cmd.startswith("randomNotes ") and searchIndex is not None):
        res = getRandomNotes(cmd[11:])
        searchIndex.output.printSearchResults(res["result"], res["stamp"])
    elif (cmd.startswith("highlight ")):
        if searchIndex is not None:
            searchIndex.highlighting = cmd[10:] == "on"
    else:
        oldOnBridge(self, cmd)

def onLoadNote(editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    """
    global corpus, output
   
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
                        <div id="modalText">dffs</div>
                       <div style='text-align: right; margin-top:25px;'>
                         <button class='modal-close' onclick='$("#a-modal").hide();'>Close</button>
                         </div>
                    </div>
                </div>

                  <div class="flexContainer" id="topContainer">
                        <div class='flexCol'>
                            <div id='deckSelWrapper'> 
                                <table id='deckSel'></table>
                            </div>
                        </div>
                        <div class='flexCol right' style="position: relative;">
                            <table>
                                <tr><td class='tbLb'>Search on selection</td><td><input type='checkbox' checked onchange='searchOnSelection = $(this).is(":checked");'/></td></tr>
                                <tr><td class='tbLb'>Search on typing</td><td><input type='checkbox' checked onchange='searchOnTyping = $(this).is(":checked");'/></td></tr>
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
                    
                    
                    <div id='loader'> <div class='signal'></div><br/>Preparing index...</div>
                    <div style='height: 100%; padding-bottom: 15px; padding-top: 15px;' id='resultsWrapper'>
                        <div id='searchInfo'></div>
                        <div id='searchResults' style='display: none; height: 95%; overflow-y: auto; padding-right: 10px;'></div>
                    </div>
                 </div>
                     <div id='bottomContainer'>
                        <div class="flexContainer">
                            <div class='flexCol' style='padding-left: 0px; border-top: 1px solid grey;'> 
                                <div class='flexContainer' style="flex-wrap: nowrap;">
                                     <div class='tooltip tooltip-blue' onclick="toggleTooltip(this);">i
                                         <div class='tooltiptext'>
                                            <table>
                                                <tr><td> dog cat </td><td> must contain both, "dog" and "cat" </td></tr>
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
           
        """.replace("$height$", str(270 - addToResultAreaHeight)))
    

    if searchIndex is not None:
        showSearchResultArea(editor)
        if not searchIndex.highlighting:
            editor.web.eval("$('#highlightCb').prop('checked', false);")


    fillDeckSelect(editor)
    if corpus is None:
        corpus = getCorpus()

    if searchIndex is not None and searchIndex.output is not None:
        searchIndex.output.editor = editor


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




class SearchIndex:
    """
    Wraps the whoosh index object, provides method to query.
    """
    def __init__(self, index, qParser, dQParser):
        self.initializationTime = 0
        self.index = index
        self.qParser = qParser
        #used to construct deck filter
        self.dQParser = dQParser
        #contains nids of items that are currently pinned, I.e. should be excluded from results
        self.pinned = []
        self.highlighting = True
        self.limit = 10
        self.TAG_RE = re.compile(r'<[^>]+>')
        self.SP_RE = re.compile(r'&nbsp;| {2,}')
        self.SEP_RE = re.compile(r'(\u001f){2,}')

    def search(self, text, decks):
        """
        Search for the given text.

        Args: 
        text - string to search, typically fields content
        decks - list of deck ids, if -1 is contained, all decks are searched
        """
        stamp = self.output.getMiliSecStamp()
        self.output.latest = stamp
        deckQ = ""
        for d in decks:
            deckQ += d + " "
        deckQ = deckQ[:-1]
        with self.index.searcher() as searcher:
            query = self.qParser.parse(text)
            dq = self.dQParser.parse(deckQ)
            if decks is None or len(decks) == 0 or "-1" in decks:
                res = searcher.search(self.qParser.parse(text), limit=self.limit)
            else:
                res = searcher.search(self.qParser.parse(text), filter=dq, limit=self.limit)
            res.fragmenter.surround = 0
            rList = []
            for r in res:
                #pinned items should not appear in the results
                if not r["nid"] in self.pinned:
                    if self.highlighting:
                        rList.append((self._markHighlights(r["content"], r.highlights("content", top=10)), r["tags"], r["did"], r["nid"]))
                    else:
                        rList.append((r["content"].replace('`', '\\`'), r["tags"], r["did"], r["nid"]))
            
            return { "result" : rList, "stamp" : stamp }

    def searchDB(self, text, decks):
        """
        WIP: this shall be used for searches in the search mask,
        doesn't use the index, instead use the traditional anki search (which is more powerful for single keywords)
        """
        stamp = self.output.getMiliSecStamp()
        self.output.latest = stamp

        found = self.finder.findNotes(text)
        
        if len (found) > 0:
            if not "-1" in decks:
                deckQ =  "(%s)" % ",".join(decks)
            else:
                deckQ = ""
            #query db with found ids
            foundQ = "(%s)" % ",".join([str(f) for f in found])
            if deckQ:
                res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where nid in %s and did in %s" %(foundQ, deckQ)).fetchall()
            else:
                res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid where nid in %s" %(foundQ)).fetchall()
            rList = []
            for r in res:
                #pinned items should not appear in the results
                if not str(r[0]) in self.pinned:
                    #todo: implement highlighting
                    rList.append((r[1].replace('`', '\\`'), r[2], r[3], r[0]))
            return { "result" : rList[:self.limit], "stamp" : stamp }
        return { "result" : [], "stamp" : stamp }

    def _markHighlights(self, text, highlights):
        """
        Whoosh highlighting seems to interfere with html tags, 
        so we use our own here.
        
        Args: 
        highlights - whoosh highlights string ("highlight1 ... highlight2")
        text - note text

        Returns:
        text where highlights are enclosed in <mark> tags
        """
        highlights = self.clean(highlights)
        if len(highlights) == 0:
            return text
        for token in set(highlights.split("...")):
            if token == "mark" or token == "":
                continue
            token = token.strip()
            text = re.sub('([^\'a-zA-ZÀ-ÖØ-öø-ÿ]|^)(' + re.escape(token) + ')([^\'a-zA-ZÀ-ÖØ-öø-ÿ]|$)', r"\1<mark>\2</mark>\3", text,  flags=re.I)
        
        #todo: this sometimes causes problems, find out why
        
        #combine adjacent highlights (very basic, won't work in all cases)
        # reg = re.compile('<mark>[^<>]+</mark>( |-)?<mark>[^<>]+</mark>')
        # found = reg.findall(text)
        # while len(found) > 0:
        #     for f in found:
        #         text = text.replace(f, "<mark>%s</mark>" %(f.replace("<mark>", "").replace("</mark>", "")))
        #     found = reg.findall(text)
        return text

    def clean(self, text):
        """
        Clean linebreaks and some html entitíes from the query string.
        TODO: could be more sensitive
        """
        text = text.replace("\n", " ").replace("\r\n", " ").strip()
        text = self.removeTags(text)
        return text.strip()

    def removeTags(self, text):
        """
        Remove <br/> &nbsp; and multiple spaces.
        TODO: check for other html entities
        """
        text = re.sub('< ?br/ ?>|< ?br ?> ?< ?/br ?>', " ", text,  flags=re.I).replace("&nbsp;", " ").replace("\t", " ")
        return self.SP_RE.sub(' ', self.TAG_RE.sub(' ', text))





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

    def iterateMap(dmap, prefix, start=False):
        if start:
            html = "<ul class='deck-sub-list outer'><li class='deck-list-item'><div style='display: inline-block; margin-top: 2px;'><span class='blueBG'>All (%s)</span> </div><input type='checkbox' checked='true' class='dCheck' data-id='-1' onclick='updateSelectedDecks();'/></li>" % len(dmap)
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in dmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item'><div style='display: inline-block; overflow-x: hidden; white-space:nowrap;'>%s <span class='exp'>%s</span></div><input type='checkbox' style='margin-bottom: 4px;' class='dCheck' data-id='%s' onclick='event.stopPropagation(); updateSelectedDecks();'/> %s</li>" % (trimIfLongerThan(key, 35), "[+]" if value else "" , deckMap[full], iterateMap(value, full, False)) 
        html += "</ul>"
        return html

    html = iterateMap(dmap, "", True)

    cmd = """document.getElementById('deckSel').innerHTML = `%s`; 
    $('.deck-list-item').click(function(e) {
		e.stopPropagation();
        let icn = $(this).find('.exp').first();
        if (icn.text()) {
            if (icn.text() === '[+]')
                icn.text('[-]');
            else
                icn.text('[+]');
        }
        $(this).children('ul').toggle();
    });
    
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
        myAnalyzer = StemmingAnalyzer(stoplist=usersStopwords) | CharsetFilter(accent_map)
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
        end = time.time()
        initializationTime = round(end - start)
        searchIndex.initializationTime = initializationTime
        

    searchIndex.finder = Finder(mw.col)
    searchIndex.output = Output()
    searchIndex.output.stopwords = searchIndex.stopWords


    try:
        limit = config['numberOfResults']
        if limit <= 0:
            limit = 20
        elif limit > 500:
            limit = 500
    except KeyError:
        limit = 20
    searchIndex.limit = limit
    editor = aqt.mw.app.activeWindow().editor if hasattr(aqt.mw.app.activeWindow(), "editor") else None
    if editor is not None and editor.addMode:
        searchIndex.output.editor = editor
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
    


def getAvgTrueRetentionAndTime():
        eases = mw.col.db.all("select ease, time from revlog where type = 1")
        if not eases:
            return 0
        cnt = 0
        passed = 0
        failed = 0
        timeTaken = 0
        for ease, taken in eases:
            cnt += 1
            if ease != 1:
                passed += 1
            else:
                failed += 1
            timeTaken += taken / 1000.0
        retention = 100 * passed / (passed + failed) if cnt > 0 else 0
        retention = round(retention, 2)
        return (round(retention,1), round(timeTaken / cnt, 1))

def calcAbsDiffInPercent(i1, i2):
        diff = round(i1 - i2, 2)
        if diff >= 0:
            return "+ " + str(diff)
        else:
            return str(diff)

def calculateStats(nid):
        #get card ids for note
        cards = mw.col.db.all("select * from cards where nid = %s" %(nid))
        if not cards:
            return ""
        cStr = "("
        for c in cards:
            cStr += str(c[0]) + ", "
        cStr = cStr[:-2] + ")"

        entries = mw.col.db.all(
            "select cid, ease, time, type "
            "from revlog where cid in %s" %(cStr))
        if not entries:
            s = "<hr/>No card has been reviewed yet for this note."
        else:
            cnt = 0
            passed = 0
            failed = 0
            goodAndEasy = 0
            hard = 0
            timeTaken = 0
            for (cid, ease, taken, type) in reversed(entries):
                #only look for reviews
                if type != 1:
                    continue
                cnt += 1
                if ease != 1:
                    passed += 1
                    if ease == 2:
                        hard += 1
                    else:
                        goodAndEasy += 1
                else:
                    failed += 1
                
                timeTaken += taken  / 1000.0        
            retention =  100 * passed / (passed + failed) if cnt > 0 else 0
            retention = round(retention, 1)
            avgTime = round(timeTaken / cnt, 1) if cnt > 0 else 0
            score = _calcPerformanceScore(retention, avgTime, goodAndEasy, hard) if cnt > 0 else (0, 0, 0, 0)
            s = ""
            s += "<div class='smallMarginTop'><span class='score'>Performance: %s</span><span class='minorScore'>Retention: %s</span><span class='minorScore'>Time: %s</span><span class='minorScore'>Ratings: %s</span></div><hr/>" %(str(score[0]), str(score[2]), str(score[1]), str(score[3]))
            s += "<b>%s</b> card(s) found for this note.<br/><br/>" %(str(len(cards)))
            if cnt > 0:
                avgRetAndTime = getAvgTrueRetentionAndTime()
                if retention == 100.0:
                    s += "<div class='smallMarginBottom'>Your <b>retention</b> on cards of this note is <span class='darkGreen'>perfect</span>: <b>" + str(retention) + " %</b></div>"
                elif retention >= 98.0:
                    s += "<div class='smallMarginBottom'>Your <b>retention</b> on cards of this note is <span class='darkGreen'>nearly perfect</span>: <b>" + str(retention) + " %</b></div>"
                elif retention != avgRetAndTime[0]:
                    s += _compString("retention", _getCompExp("retention", retention, avgRetAndTime[0]), retention, calcAbsDiffInPercent(retention, avgRetAndTime[0]), "%")  
                else: 
                    s += "<div class='smallMarginBottom'>Your <b>retention</b> on cards of this note is equal to your average retention: <b>" + str(retention) + " %</b></div>"

          
                if avgTime != avgRetAndTime[1]:
                    s += _compString("time", _getCompExp("time", avgTime, avgRetAndTime[1]), avgTime, calcAbsDiffInPercent(avgTime, avgRetAndTime[1]), "s")  
                else:
                    s += "<div class='smallMarginBottom'>Your <b>time</b> on cards of this note is equal to your average time: <b>" + str(avgTime) + " s</b></div>"
            
        s = "<div id='i-%s' style='position: absolute; bottom: 3px; left: 0px; padding: 7px;'>%s</div>" %(nid,s) 
        
        return s

def _getCompExp(field, value, avg):
    bbb = 8
    bb = 4
    biggerIsBetter = True
    if field == 'time':
        bbb = 10
        bb = 5
        biggerIsBetter = False

    if not biggerIsBetter:
        v_h = value
        value = avg
        avg = v_h

    if value > avg and value - avg >= bbb: 
        return '<span class="darkGreen">significantly better</span>'
    elif value > avg and value - avg >= bb:
        return '<span class="green">better</span>'
    elif value > avg:
        return '<span class="lightGreen">slightly better</span>'
    elif value < avg and avg - value >= bbb:
        return '<span class="darkRed">significantly worse</span>'
    elif value < avg and avg - value >= bb:
        return '<span class="red">worse</span>'
    elif value < avg:
        return '<span class="lightRed">slightly worse</span>'
    
    
    return "n.a."


def _compString(fieldName, comp, value, diff, unit):
      return "<div class='smallMarginBottom'>Your <b>%s</b> on cards of this note is %s than your average %s: <b>%s %s</b> (%s %s)</div>" %(fieldName, comp, fieldName, value, unit,  diff, unit) 

def _calcPerformanceScore(retention, time, goodAndEasy, hard):
      if goodAndEasy == 0 and hard == 0:
          return (0,0,0,0)
      #retention is counted higher, numbers are somewhat arbitrary
      score = 0
      retentionSc = 2 * retention * (1 - ((100 - retention) / 100))
      score += retentionSc
      timeSc = 100.0 - time / 3.0  * 10.0
      if timeSc < 0:
          timeSc = 0
      score += timeSc
      ratingSc = (goodAndEasy / (goodAndEasy + hard)) * 100
      score += ratingSc
      score = round(score * 100.0 / 400.0, 1)
      return (int(score), int(timeSc), int(retentionSc * 100.0 / 200.0), int(ratingSc)) 


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



