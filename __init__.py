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
from .whoosh.index import create_in
from .whoosh.fields import Schema, TEXT, NUMERIC, KEYWORD
from .whoosh.qparser import QueryParser
from .whoosh.analysis import StandardAnalyzer
from .whoosh import classify, highlight, query, scoring, qparser, reading
from .wikipedia import summary, DisambiguationError
from .web import getScriptPlatformSpecific


searchIndex = None
sugIndex = None
corpus = None
editorO = None
deckMap = None
sugRequestRunning = False
TAG_RE = re.compile(r'<[^>]+>')
SP_RE = re.compile(r'&nbsp;| {2,}')
SEP_RE = re.compile(r'(\u001f){2,}')


def initAddon():
    global corpus
    global oldOnBridge
    oldOnBridge = Editor.onBridgeCmd
    Editor.onBridgeCmd = myOnBridgeCmd
    #todo: Find out if there is a better moment to start index creation
    addHook("profileLoaded", buildIndex)
    
    #main functions to search
    aqt.editor._html += """
        <script>
        function sendContent(event) {
           if ((event && event.repeat) || isFrozen)
                return;
           let html = "";
           $fields.each(function(index, elem) {
                html += $(elem).html() + "\u001f";
           });
           pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
        }
        function sendSearchFieldContent() {
           html = $('#searchMask').val() + "\u001f";
           pycmd('srchDB ' + selectedDecks.toString() + ' ~ ' + html);
        }

        function searchFor(text) {
           text += "\u001f";
           pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + text);
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
    if (cmd.startswith("fldChgd ")):
        rerenderInfo(self, cmd[8:])
    elif (cmd.startswith("srchDB ")):
        rerenderInfo(self, cmd[7:], searchDB = True)
    elif (cmd.startswith("fldSlctd ")):
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
    elif (cmd.startswith("setLimit ")):
        searchIndex.limit = int(cmd[9:])
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
    global corpus, editorO

    #only display in add cards dialog
    if (editor.addMode):
        editor.web.eval(""" 
            
            //check if ui has been rendered already
            if (!$('#outerWr').length) {
       
            $(`#fields`).wrap(`<div class='coll' style='min-width: 200px; width: 50%;  flex-grow: 1 '></div>`);
            $(`
            <div class='coll secondCol' style='flex-grow: 1; width: 50%; height: 100%; border-left: 2px solid #2496dc; margin-top: 20px; padding: 20px; margin-left: 30px; position: relative;' id='infoBox'>
             
                  <div class="flexContainer" id="topContainer">
                        <div class='flexCol'>
                            <div id='deckSelWrapper'> 
                                <table id='deckSel'></table>
                            </div>
                        </div>
                        <div class='flexCol right'>
                            <table>
                                <tr><td class='tbLb'>Search on selection</td><td><input type='checkbox' checked onchange='searchOnSelection = $(this).is(":checked");'/></td></tr>
                                <tr><td class='tbLb'>Highlight results</td><td><input id="highlightCb" type='checkbox' checked onchange='setHighlighting(this)'/></td></tr>
                                <tr><td class='tbLb'>(WIP) Infobox</td><td><input type='checkbox' onchange='useInfoBox = $(this).is(":checked");'/></td></tr>
                                <tr><td class='tbLb'>Freeze</td><td><input type='checkbox' id='freezeBox' onchange='isFrozen = $(this).is(":checked");'/></td></tr>
                            </table>
                       </div>
                  </div>
                  
                 <div id="resultsArea" style="height: calc(var(--vh, 1vh) * 100 - 250px); width: 100%; border-top: 1px solid grey; border-bottom: 1px solid grey;">
                    <div id='loader'> <div class='signal'></div><br/>Preparing index...</div>
                    <div style='height: 100%; padding-bottom: 10px; padding-top: 10px;' id='resultsWrapper'>
                        <div id='searchResults' style='display: none; height: 95%; overflow-y: auto; padding-right: 10px;'></div>
                    </div>
                 </div>
                     <div style="">
                        <div class="flexContainer">
                     
                            <div class='flexCol' style='padding-left: 0px;'> 
                                <div class='flexContainer' style="flex-wrap: nowrap;">
                                     <div class='tooltip tooltip-blue' onclick="toggleTooltip(this);">i
                                         <div class='tooltiptext'>
                                            <table>
                                                <tr><td> dog cat </td><td> must contain both, "dog" and "cat" </td></tr>
                                                <tr><td>dog or cat </td><td> either "dog" or "cat"  </td></tr>
                                                <tr><td>dog (cat or mouse)  </td><td>  dog and cat, or dog and mouse </td></tr>
                                                <tr><td> -cat </td><td> without the word "cat" </td></tr>
                                                <tr><td> -cat -mouse  </td><td>  neither "cat" nor "mouse"  </td></tr>
                                                <tr><td> "a dog" </td><td>  exact phrase </td></tr>
                                                <tr><td> -"a dog" </td><td> without the exact phrase</td></tr>
                                                <tr><td>d_g  </td><td>    d, <a letter>, g, e.g. dog, dig, dug   </td></tr>
                                                <tr><td> d*g </td><td> d, <zero or more letters>, g, like dg, dog, dung </td></tr>
                                            </table>
                                         </div>
                                     </div>
                                    <input id='searchMask' placeholder='Search here works like in the browser...' onkeyup='searchMaskKeypress(event)'></input> 
                                    <button id='searchBtn' onclick='sendSearchFieldContent()'>Search</button>
                                </div>
                            </div>
                           
                        </div>
                      </div>
                 </div>`).insertAfter('#fields');
            $(`.coll`).wrapAll('<div id="outerWr" style="width: 100%; display: flex; height: 100%;"></div>');    
            
            
            $(`.field`).attr("onkeyup", "fieldKeypress(event, this);"); 
            $(`.field`).attr("onkeydown", "moveInHover(event, this);" + $(`.field`).attr("onkeydown")); 
            $('.field').attr('onmouseup', 'getSelectionText()');
            $('.field').attr('onfocusout', 'hideHvrBox()');
            var $fields = $('.field');
            
            window.addEventListener('resize', onResize, true);
            onResize();
           }
        """)
    

    if searchIndex is not None:
        showSearchResultArea(editor)
        if not searchIndex.highlighting:
            editor.web.eval("$('#highlightCb').prop('checked', false);")


    fillDeckSelect(editor)
    if corpus is None:
        corpus = getCorpus()
    editorO = editor

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

def displayLastNote():
    editorO.web.eval("document.getElementById('hvrBoxSub').innerHTML = `" + getLastCreatedNote() + "`;")

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
    editorO.web.eval(cmd)




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

    def search(self, text, decks):
        """
        Search for the given text.

        Args: 
        text - string to search, typically fields content
        decks - list of deck ids, if -1 is contained, all decks are searched
        """
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
                        rList.append((r["content"], r["tags"], r["did"], r["nid"]))
            return rList

    def searchDB(self, text, decks):
        """
        WIP: this shall be used for searches in the search mask,
        doesn't use the index, instead use the traditional anki search (which is more powerful for single keywords)
        """
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
                    rList.append((r[1], r[2], r[3], r[0]))
            return rList
        return []

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
        highlights = cleanQueryString(highlights)
        if len(highlights) == 0:
            return text
        for token in set(highlights.split("...")):
            if token == "mark":
                continue
            token = token.strip()
            text = re.sub('([^A-Za-zöäü]|^)(' + re.escape(token) + ')([^A-Za-zöäü]|$)', r"\1<mark>\2</mark>\3", text,  flags=re.I)
        #combine adjacent highlights (very basic, won't work in all cases)
        reg = re.compile('<mark>[^<>]+</mark> ?<mark>[^<>]+</mark>')
        found = reg.findall(text)
        while len(found) > 0:
            for f in found:
                text = text.replace(f, "<mark>%s</mark>" %(f.replace("<mark>", "").replace("</mark>", "")))
            found = reg.findall(text)
        return text

class SuggestionIndex:
    """
    Not used atm, can be utilized for autocomplete functionality in the fields
    """
    def __init__(self, n2Index, n3Index):
        self.n2Index = n2Index
        self.n3Index = n3Index
        self.initializationTime = 0

    def getSuggestions(self, text):
        html = ""
        found = None
        lastW = ""
        count = 0

        if removeTags(text)[-1:] == ' ':
            #search based on trigram
            found = self.n3Index.reader().most_distinctive_terms(fieldname='phrases', number=8, prefix=self._getTrigram(removeTags(text)))
            if not found:
                #search based on bigram
                found = self.n2Index.reader().most_distinctive_terms(fieldname='phrases', number=8, prefix=self._getBigram(removeTags(text)))
        else: 
            #search based on word beginning
            text = cleanQueryString(text)
            lastW = self._lastWord(text)
            found = searchIndex.index.reader().most_distinctive_terms(fieldname='content', number=8, prefix=lastW)
        for res in found:
            if len(lastW) > 0 and str(res[1], 'utf-8') == lastW:
                continue
            if count == 0:
                html +=  "<div class='hvrLeftItem hvrSelected' id='hvrI-%s'>"%(count) + str(res[1], 'utf-8') + "</div>"
            else:    
                html +=  "<div class='hvrLeftItem' id='hvrI-%s'>"%(count) + str(res[1], 'utf-8') + "</div>"
            count += 1
        
        return (html, count)

    def _lastWord(self, text):
        if len(text) == 0:
            return ""
        return text.split(' ')[-1]

    def _getBigram(self, text):
        if not " " in text:
            return ""
        return text.strip().split(" ")[-1:][0] + "AAAA"

    def _getTrigram(self, text):
        spl = text.strip().split(" ")
        if not len(spl) > 1:
            return ""
        return spl[-2:][0] + "AAAA" + spl[-1:][0] + "AAAA"



def fillDeckSelect(editor):
    """
    Fill the selection with user's decks
    """
    global deckMap
    deckMap = dict()
    html = "<tr><td ><span style='background: #2496dc; color: white;'>&nbsp;All Decks&nbsp;</span></td><td><input class='dCheck' data-id='-1' type='checkbox' checked onchange='updateSelectedDecks();'/></td></tr>"
    config = mw.addonManager.getConfig(__name__)
    deckList = config['decks']
    for d in list(mw.col.decks.decks.values()):
       if d['name'] == 'Standard':
          continue
       if deckList is not None and len(deckList) > 0 and d['name'] not in deckList:
           continue
       deckMap[d['id']] = d['name'] 
       html += "<tr><td>&nbsp;%s</td><td><input class='dCheck' data-id='%s' type='checkbox' onchange='updateSelectedDecks();'/></td></tr>" %( d['name'], d['id'])
    cmd = "document.getElementById('deckSel').innerHTML = `" + html + "`;"
    editor.web.eval(cmd)

def setStats(nid, stats):
    """
    Insert the statistics inside the given card.
    """
    cmd = "document.getElementById('" + nid + "').innerHTML += `" + stats + "`;"
    editorO.web.eval(cmd)

def renderSuggestions(editor, content=""):
    """
    Not used atm, was used for autocomplete.
    """
    global sugRequestRunning
    if sugRequestRunning:
        return
    if sugIndex is not None:
        sugRequestRunning = True
        sugs = sugIndex.getSuggestions(content)
        if sugs[1] == 0:
            editor.web.eval("document.getElementById('hvrBox').style.display = 'none'; hvrBoxIndex = 0;")
        else:
            editor.web.eval("document.getElementById('hvrBox').style.display = 'block'; document.getElementById('hvrBox').innerHTML = `" + sugs[0] + "`; hvrBoxIndex = 0; hvrBoxLength = " + str(sugs[1]))
    sugRequestRunning = False

def rerenderInfo(editor, content="", searchDB = False):
    """
    Main function that is executed when a user has typed or manually entered a search.

    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    if (len(content) < 1):
        return
    decks = list()
    for s in content[:content.index('~')].split(','):
      decks.append(s.strip())
    content = cleanQueryString(content[content.index('~ ') + 2:])
    if searchIndex is not None and len(content) > 1:
      #distinguish between index searches and db searches
      if searchDB:
        searchRes = searchIndex.searchDB(content, decks)  
      else:
        searchRes = searchIndex.search(content, decks)
      if len(searchRes) > 0:
        printSearchResults(searchRes, editor)
      else:
        editor.web.eval("setSearchResults('')")




def printSearchResults(searchResults, editor):
    html = ""
    
    """
    This is the html that gets rendered in the search results div.
    
    Args:

    searchResults - a list of tuples, see SearchIndex.search()
    """
    for counter, res in enumerate(searchResults[:50]):
        #todo: move in class
        html += """<div class='cardWrapper'  style='padding: 9px; margin-bottom: 10px; position: relative;'> 
                        <div id='cW-%s' class='rankingLbl'>%s</div> 
                        <div id='btnBar-%s' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                            <div class='srchLbl' onclick='searchCard(this)'>Search</div> 
                            <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div> 
                            <div id='rem-%s'  class='remLbl' onclick='$("#cW-%s").parents().first().remove(); updatePinned();'><span>&times;</span></div> 
                        </div>
                        <div class='cardR' onclick='expandCard(this);' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div> 
                        <div style='position: absolute; bottom: 0px; right: 0px; z-index:9999'>%s</div>     
                    </div>
                    """ %(res[3], counter + 1, res[3],res[3],res[3], res[3], res[3], res[3], res[3], res[3], res[3], SEP_RE.sub("\u001f", res[0]).replace("\u001f", "<span class='fldSep'>|</span>"), buildTagString(res[1]))  
    cmd = "setSearchResults(`" + html + "`);"
    editor.web.eval(cmd)

def buildTagString(tags):
    """
    Builds the html for the tags that are displayed at the bottom right of each rendered search result.
    """
    html = ""
    for t in tags.split(' '):
      if len(t) > 0:
        html += "<div class='tagLbl' data-name='%s' onclick='tagClick(this);'>%s</div>" %(t, t)
    return html

def showSearchResultArea(editor=None, initializationTime=0):
    """
    Toggle between the loader and search result area when the index has finsihed building.
    """
    if editorO is not None and editorO.web is not None:
        editorO.web.eval("document.getElementById('searchResults').style.display = 'block'; document.getElementById('loader').style.display = 'none';")
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
    
    global searchIndex, sugIndex
    start = time.time()

    config = mw.addonManager.getConfig(__name__)
    try:
        usersStopwords = config['stopwords']    
    except KeyError:
        usersStopwords = []
    if usersStopwords is not None and len(usersStopwords) > 0:
        schema = whoosh.fields.Schema(content=TEXT(stored=True, analyzer=StandardAnalyzer(stoplist=usersStopwords)), tags=TEXT(stored=True), did=TEXT(stored=True), nid=TEXT(stored=True))
    else:
        schema = whoosh.fields.Schema(content=TEXT(stored=True), tags=TEXT(stored=True), did=TEXT(stored=True), nid=TEXT(stored=True))
    
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
    end = time.time()
    initializationTime = round(end - start)
    searchIndex = SearchIndex(index, queryparser, deckQueryparser)
    searchIndex.finder = Finder(mw.col)
    searchIndex.initializationTime = initializationTime
    try:
        limit = config['numberOfResults']
        if limit <= 0:
            limit = 20
        elif limit > 500:
            limit = 500
    except KeyError:
        limit = 20
    searchIndex.limit = limit

    showSearchResultArea(initializationTime=initializationTime)

    # autocomplete still WIP

    # start = time.time()
    # n2Index = create_in(", whoosh.fields.Schema(phrases = KEYWORD(commas=True, lowercase=False)))
    # n2Writer = n2Index.writer()
    # n3Index = create_in(", whoosh.fields.Schema(phrases = KEYWORD(commas=True, lowercase=False)))
    # n3Writer = n3Index.writer()
    # for note in corpus:
    #     for bigr in extractNgrams(note[1], 2):
    #         n2Writer.add_document(phrases=bigr)
    #     for bigr in extractNgrams(note[1], 3):
    #         n3Writer.add_document(phrases=bigr)
    # n2Writer.commit()
    # n3Writer.commit()
    # end = time.time()
    # initializationTime = round(end - start)
    # sugIndex = SuggestionIndex(n2Index, n3Index)
    # sugIndex.initializationTime = initializationTime
    # setMinorStatus("Prediction is ready. (Took %s s)"%(round(initializationTime)))
    

def addTag(tag):
    """
    Insert the given tag in the tag field at bottom if not already there.
    """
    if tag == "" or editorO is None:
        return
    tagsExisting = editorO.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return
    
    editorO.tags.setText(tagsExisting + " " + tag)
    editorO.saveTags()

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
 
def cleanQueryString(text):
    """
    Clean linebreaks and some html entitíes from the query string.
    TODO: could be more sensitive
    """
    text = text.replace("\n", " ").replace("\r\n", " ").strip()
    text = removeTags(text)
    return text.strip()

def removeTags(text):
    """
    Remove <br/> &nbsp; and multiples spaces.
    TODO: check for other html entities
    """
    text = re.sub('< ?br/ ?>|< ?br ?> ?< ?/br ?>', " ", text,  flags=re.I).replace("&nbsp;", " ").replace("\t", " ")
    return SP_RE.sub(' ', TAG_RE.sub(' ', text))





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



