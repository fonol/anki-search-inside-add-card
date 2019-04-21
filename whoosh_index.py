from aqt.qt import *
from aqt import mw
from anki.hooks import runHook, addHook, wrap
import aqt
import aqt.webview
from anki.find import Finder
import aqt.editor
from aqt.editor import Editor
import aqt.stats
from aqt.main import AnkiQt
import sqlite3
import re
import time
from .textutils import *
from .fts_index import Worker, WorkerSignals


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
        self.threadPool = QThreadPool()
        self.highlighting = True
        self.searchWhileTyping = True
        self.wordToken = re.compile("[a-zA-ZÀ-ÖØ-öø-ÿāōūēīȳǒ]", flags = re.I)
        self.searchOnSelection = True
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
        worker = Worker(self.searchProc, text, decks) 
        worker.stamp = self.output.getMiliSecStamp()
        self.output.latest = worker.stamp
        worker.signals.result.connect(self.printOutput)
        
        self.threadPool.start(worker)




        #stamp = self.output.getMiliSecStamp()
        #self.output.latest = stamp
        
    def searchProc(self, text, decks):    
        resDict = {}
        start = time.time()
        text = self.clean(text)
        resDict["time-stopwords"] = int((time.time() - start) * 1000)
        self.lastSearch = (text, decks, "default")
        if len(text) == 0:
            self.output.editor.web.eval("setSearchResults('', 'Query was empty after cleaning')")
            return
        start = time.time()
        text = expandBySynonyms(text, self.synonyms)
        resDict["time-synonyms"] = int((time.time() - start) * 1000)
        resDict["query"] = text


        start = time.time()
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
            resDict["time-query"] = int((time.time() - start) * 1000)
            resDict["highlighting"] = self.highlighting
            if self.highlighting:
                start = time.time()
                querySet = set(replaceAccentsWithVowels(s).lower() for s in text.split(" "))
                for r in res:
                    if not r["nid"] in self.pinned:
                        rList.append((self._markHighlights(r["source"], querySet), r["tags"], r["did"], r["nid"]))
                resDict["time-highlighting"] = int((time.time() - start) * 1000)
            else:
                for r in res:
                    if not r["nid"] in self.pinned:
                        rList.append((r["source"].replace('`', '\\`'), r["tags"], r["did"], r["nid"]))

                

            self.lastResDict = resDict
            
            return { "results" : rList }

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


    def _markHighlights(self, text, querySet):
     
        currentWord = ""
        currentWordNormalized = ""
        textMarked = ""
        lastIsMarked = False
        for char in text:
            if self.wordToken.match(char):
                currentWordNormalized += asciiFoldChar(char).lower()
                currentWord += char
            else:
                #check if word is empty
                if currentWord == "":
                    textMarked += char
                else:
                    if currentWordNormalized in querySet:
                        if lastIsMarked:
                            textMarked = textMarked[0: textMarked.rfind("</mark>")] + textMarked[textMarked.rfind("</mark>") + 7 :]
                            textMarked += currentWord + "</mark>" + char
                        else:
                            textMarked += "<mark>" + currentWord + "</mark>" + char
                        lastIsMarked = True
                        
                    else:
                        textMarked += currentWord + char
                        lastIsMarked = False

                    currentWord = ""
                    currentWordNormalized = ""
        if currentWord != "":
            if currentWordNormalized in querySet and currentWord != "mark":
                textMarked += "<mark>" + currentWord + "</mark>"
            else:
                textMarked += currentWord
        return textMarked


   

    def cleanHighlights(self, text):
        """
        Clean linebreaks and some html entitíes from the highlights string.
        """
        text = text.replace("\n", " ").replace("\r\n", " ").strip()
        text = self.removeTags(text)
        return text.strip()

    def clean(self, text):
        return clean(text, self.stopWords)


    def printOutput(self, result, stamp):
        if result is not None:
            self.output.printSearchResults(result["results"], stamp, logging = self.logging, printTimingInfo = True)

    def removeTags(self, text):
        """
        Remove <br/> &nbsp; and multiple spaces.
        TODO: check for other html entities
        """
        text = re.sub('< ?br/ ?>|< ?br ?> ?< ?/br ?>', " ", text,  flags=re.I).replace("&nbsp;", " ").replace("\t", " ")
        return self.SP_RE.sub(' ', self.TAG_RE.sub(' ', text))

    def addNote(self, note):
        
        content = " \u001f ".join(note.fields)
        tags = " ".join(note.tags)
        did = str(note.model()['did'])
        writer = self.index.writer()
        writer.add_document(content=content, tags=tags, did=did, nid=str(note.id))
        writer.commit()
        return note
    
    def getNumberOfNotes(self):
        res = self.index.searcher().doc_count_all()
        return res