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
        self.searchWhileTyping = True
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
            text = re.sub('([^a-zA-ZÀ-ÖØ-öø-ÿ]|^)(' + re.escape(token) + ')([^a-zA-ZÀ-ÖØ-öø-ÿ]|$)', r"\1<mark>\2</mark>\3", text,  flags=re.I)
        
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