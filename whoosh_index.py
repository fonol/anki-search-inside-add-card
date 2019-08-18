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
from .logging import log, persist_index_info
from .textutils import *
from .fts_index import Worker, WorkerSignals
from .output import Output
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

class WhooshSearchIndex:
    """
    Wraps the whoosh index object, provides method to query.
    """
    def __init__(self, corpus, searchingDisabled, index_up_to_date):
        self.initializationTime = 0
        #contains nids of items that are currently pinned, I.e. should be excluded from results
        self.pinned = []
        self.threadPool = QThreadPool()
        self.highlighting = True
        self.searchWhileTyping = True
        self.searchOnSelection = True
        self.limit = 10
        self.TAG_RE = re.compile(r'<[^>]+>')
        self.SP_RE = re.compile(r'&nbsp;| {2,}')
        self.SEP_RE = re.compile(r'(\u001f){2,}')
        self.output = Output()
        self.creation_info = {}
        
        config = mw.addonManager.getConfig(__name__)

        try:
            self.fields_to_exclude = config['fieldsToExclude']
            self.creation_info["fields_to_exclude_original"] = self.fields_to_exclude 
        except KeyError:
            self.fields_to_exclude = {} 
        self.output.fields_to_exclude = self.fields_to_exclude
        
        try:
            self.stopWords = set(config['stopwords'])
        except KeyError:
            self.stopWords = []
        self.creation_info["stopwords_size"] = len(self.stopWords)
        self.creation_info["decks"] = config["decks"]
        self.creation_info["index_was_rebuilt"] = not index_up_to_date

        myAnalyzer = StandardAnalyzer(stoplist= None, minsize=1) | CharsetFilter(accent_map)
        #StandardAnalyzer(stoplist=usersStopwords)
        schema = Schema(content=TEXT(stored=True, analyzer=myAnalyzer), tags=TEXT(stored=True), did=TEXT(stored=True), nid=TEXT(stored=True), source=TEXT(stored=True), mid=TEXT(stored=True))
        
        #index needs a folder to operate in
        indexDir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/whoosh_index.py", "") + "/index"
        if not os.path.exists(indexDir):
            os.makedirs(indexDir)
        self.index = create_in(indexDir, schema)
        if not index_up_to_date:
            
            #limitmb can be set down
            writer = self.index.writer(limitmb=256)
            #todo: check if there is some kind of batch insert
            text = ""
            for note in corpus:
                #if the notes model id is in our filter dict, that means we want to exclude some field(s)
                text = note[1]
                if note[4] in self.fields_to_exclude:
                    text = remove_fields(text, self.fields_to_exclude[note[4]])
                text = clean(text, self.stopWords)
                writer.add_document(content=text, tags=note[2], did=str(note[3]), nid=str(note[0]), source=note[1], mid=str(note[4]))
            writer.commit()
        #todo: allow user to toggle between and / or queries
        og = qparser.OrGroup.factory(0.9)
        #used to parse the main query
        self.qParser = QueryParser("content", self.index.schema, group=og)
        #used to construct a filter query, to limit the results to a set of decks
        self.dQParser = QueryParser("did", self.index.schema, group=qparser.OrGroup)
        self.type = "Whoosh"
        persist_index_info(self)




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
        #cs = self.searchProc(text, decks) 
        self.threadPool.start(worker)


        
    def searchProc(self, text, decks):    
        resDict = {}
        start = time.time()
        orig = text
        text = self.clean(text)
        resDict["time-stopwords"] = int((time.time() - start) * 1000)
        self.lastSearch = (text, decks, "default")
        if len(text) == 0:
            self.output.editor.web.eval("setSearchResults(``, 'Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>')" % trimIfLongerThan(orig, 100))
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
          
            for r in res:
                if not r["nid"] in self.pinned:
                    rList.append((r["source"].replace('`', '\\`'), r["tags"], r["did"], r["nid"], 1, r["mid"]))

                

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
                res = mw.col.db.execute("select distinct notes.id, flds, tags, did, notes.mid from notes left join cards on notes.id = cards.nid where nid in %s and did in %s" %(foundQ, deckQ)).fetchall()
            else:
                res = mw.col.db.execute("select distinct notes.id, flds, tags, did, notes.mid from notes left join cards on notes.id = cards.nid where nid in %s" %(foundQ)).fetchall()
            rList = []
            for r in res:
                #pinned items should not appear in the results
                if not str(r[0]) in self.pinned:
                    #todo: implement highlighting
                    rList.append((r[1].replace('`', '\\`'), r[2], r[3], r[0], 1, r[4]))
            return { "result" : rList[:self.limit], "stamp" : stamp }
        return { "result" : [], "stamp" : stamp }

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
            query_set = None
            if self.highlighting and self.lastResDict is not None and "query" in self.lastResDict and self.lastResDict["query"] is not None:
                query_set = set(replaceAccentsWithVowels(s).lower() for s in text.split(" "))
            self.output.printSearchResults(result["results"], stamp, logging = self.logging, printTimingInfo = True, query_set=query_set)

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
        did = mw.col.db.execute("select distinct did from notes left join cards on notes.id = cards.nid where nid = %s" % note.id).fetchone()
        if did is None or len(did) == 0:
            return
        did = did[0]
        if note.mid in self.fields_to_exclude:
            content = remove_fields(content, self.fields_to_exclude[note.mid])
        writer = self.index.writer()
        writer.add_document(content=clean(content, self.stopWords), tags=tags, did=str(did), nid=str(note.id), source=content, mid=str(note.mid))
        writer.commit()
        persist_index_info(self)
        return note
    
    def updateNote(self, note):
        
        # not supported until I find out what is going wrong here
        #pass
     
        writer = self.index.writer()
        c = writer.delete_by_term("nid", str(note.id))
        content = " \u001f ".join(note.fields)
        tags = " ".join(note.tags)
        did = mw.col.db.execute("select distinct did from notes left join cards on notes.id = cards.nid where nid = %s" % note.id).fetchone()
        if did is None or len(did) == 0:
            return
        did = did[0]
        #writer.update_document(content=clean(content, self.stopWords), tags=tags, did=did, nid=str(note.id), source=content)
        if note.mid in self.fields_to_exclude:
            content = remove_fields(content, self.fields_to_exclude[note.mid])
        writer.add_document(content=clean(content, self.stopWords), tags=tags, did=str(did), nid=str(note.id), source=content, mid=str(note.mid))
        persist_index_info(self)
        writer.commit()
   

    def get_number_of_notes(self):
        res = self.index.searcher().doc_count_all()
        return res