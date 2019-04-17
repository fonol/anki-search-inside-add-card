import sqlite3
import os
import sys
import struct
import re
import math
from aqt import *
from aqt.utils import showInfo
from .output import *
import collections
from .textutils import *
from .logging import log

class FTSIndex:

    def __init__(self, corpus, searchingDisabled):

        self.limit = 20
        self.pinned = []
        self.highlighting = True
        self.searchWhileTyping = True
        self.searchOnSelection = True
        self.dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/db.py", "")
        self.stopWords = []
        self.threadPool = QThreadPool()
        self.output = None

        config = mw.addonManager.getConfig(__name__)
        try:
            self.stopWords = set(config['stopwords'])
        except KeyError:
            self.stopWords = []
       
       
        if not searchingDisabled:
            cleaned = self._cleanText(corpus)

            #if fts5 is compiled, use it
            self.type = self._checkIfFTS5Available(config["logging"])
            try:
                os.remove(self.dir + "/search-data.db")
            except OSError:
                pass
            conn = sqlite3.connect(self.dir + "/search-data.db")
            conn.execute("drop table if exists notes")
            if self.type == "SQLite FTS5":
                conn.execute("create virtual table notes using fts5(nid, text, tags, did, source)")
            elif self.type == "SQLite FTS4":
                conn.execute("create virtual table notes using fts4(nid, text, tags, did, source)")
            else:
                conn.execute("create virtual table notes using fts3(nid, text, tags, did, source)")
            
            conn.executemany('INSERT INTO notes VALUES (?,?,?,?,?)', cleaned)
            conn.execute("INSERT INTO notes(notes) VALUES('optimize')")
            conn.commit()
            conn.close()


    def _checkIfFTS5Available(self, logging):
        con = sqlite3.connect(':memory:')
        cur = con.cursor()
        cur.execute('pragma compile_options;')
        available_pragmas = [s[0].lower() for s in cur.fetchall()]
        con.close()
        if logging:
            log("\nSQlite compile options: " + str(available_pragmas))
        if 'enable_fts5' in available_pragmas:
            return "SQLite FTS5"
        if 'enable_fts4' in available_pragmas:
            return "SQLite FTS4"
        if 'enable_fts3' in available_pragmas:
            return "SQLite FTS3"
        return "SQLite - No FTS detected (trying to use FTS3)"
   

    def _cleanText(self, corpus):
        filtered = list()
        for row in corpus:
            filtered.append((row[0], clean(row[1], self.stopWords), row[2], row[3], row[1]))
        return filtered

    def removeStopwords(self, text):
        cleaned = ""
        for token in text.split(" "):
            if token.lower() not in self.stopWords:
                cleaned += token + " "
        if len(cleaned) > 0:
            return cleaned[:-1]
        return ""


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


    def searchProc(self, text, decks):
        if self.logging:
            log("\nFTS index - Received query: " + text)
            log("Decks (arg): " + str(decks))
            log("Self.pinned: " + str(self.pinned))
            log("Self.limit: " +str(self.limit))
        text = expandBySynonyms(text, self.synonyms)

        if len(text) < 2:
            if self.logging:
                log("Returning - Text was < 2 chars: " + text)
            return { "results" : [] }

        query = " OR ".join(["tags:" + s.strip().replace("OR", "or") for s in text.split(" ") if len(s) > 1 ])
        if self.type == "SQLite FTS5":
            query += " OR " + " OR ".join(["text:" + s.strip().replace("OR", "or") for s in text.split(" ") if len(s) > 1 ]) 
        else:
            query += " OR " + " OR ".join([s.strip().replace("OR", "or") for s in text.split(" ") if len(s) > 1 ]) 
        if query == " OR ":
            if self.logging:
                log("Returning. Query was: " + query)
            return { "results" : [] }

        c = 1
        allDecks = "-1" in decks
        rList = list()
        conn = sqlite3.connect(self.dir + "/search-data.db")
        if self.type == "SQLite FTS5":
            dbStr = "select nid, text, tags, did, source from notes where notes match '%s' order by bm25(notes)" %(query)
        elif self.type == "SQLite FTS4":
            dbStr = "select nid, text, tags, did, source, matchinfo(notes, 'pcnalx') from notes where text match '%s'" %(query)
        else:
            dbStr = "select nid, text, tags, did, source, matchinfo(notes) from notes where text match '%s'" %(query)

        try:
            res = conn.execute(dbStr).fetchall()
        except Exception as e:
            if self.logging:
                log("Executing db query threw exception: " + e.message)
            res = []
        if self.logging: 
            log("dbStr was: " + dbStr)
            log("Result length of db query: " + str(len(res)))
        for r in res:
            if not str(r[0]) in self.pinned and (allDecks or str(r[3]) in decks):
                if self.highlighting:
                    if self.type == "SQLite FTS5":
                        rList.append((self._markHighlights(r[4], text).replace('`', '\\`'), r[2], r[3], r[0]))
                    elif self.type == "SQLite FTS4":
                        rList.append((self._markHighlights(r[4], text).replace('`', '\\`'), r[2], r[3], r[0], self.bm25(r[5], 0, 1, 0, 0, 0)))
                    else:
                        rList.append((self._markHighlights(r[4], text).replace('`', '\\`'), r[2], r[3], r[0], self.simpleRank(r[5])))
                else:
                    if self.type == "SQLite FTS5":
                        rList.append((r[4], r[2], r[3], r[0]))
                    elif self.type == "SQLite FTS4":
                        rList.append((r[4], r[2], r[3], r[0], self.bm25(r[5], 0, 1, 2, 0, 0)))
                    else:
                        rList.append((r[4], r[2], r[3], r[0], self.simpleRank(r[5])))
                        
                c += 1
        conn.close()
        #if fts5 is not used, results are not sorted by score
        if not self.type == "SQLite FTS5":
            rList = sorted(rList, key=lambda x: x[4])
        if self.logging:
            log("Query was: " + query)
            log("Result length (after removing pinned and unselected decks): " + str(len(rList)))
        return { "results" : rList[:min(self.limit, len(rList))] }

    def printOutput(self, result, stamp):
        if result is not None:
            self.output.printSearchResults(result["results"], stamp, logging = self.logging)
    
    def _markHighlights(self, text, cleanedQuery):
        for token in set(cleanedQuery.split(" ")):
            if token == "mark" or token == "":
                continue
            token = token.strip()
            text = re.sub('([^a-zA-ZÀ-ÖØ-öø-ÿ]|^)(' +  replaceVowelsWithAccentedRegex(re.escape(token)) + ')([^a-zA-ZÀ-ÖØ-öø-ÿ]|$)', r"\1<mark>\2</mark>\3", text,  flags=re.I)
        #todo: find out why this doesnt work here
        #combine adjacent highlights (very basic, won't work in all cases)
        # reg = re.compile('<mark>[^<>]+</mark> ?<mark>[^<>]+</mark>')
        # found = reg.findall(text)
        # while len(found) > 0:
        #     for f in found:
        #         text = text.replace(f, "<mark>%s</mark>" %(f.replace("<mark>", "").replace("</mark>", "")))
        #     found = reg.findall(text)
       
        return text



    def searchDB(self, text, decks):
        """
        Used for searches in the search mask,
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
                    rList.append((r[1], r[2], r[3], r[0]))
            return { "result" : rList[:self.limit], "stamp" : stamp }
        return { "result" : [], "stamp" : stamp }

    def _parseMatchInfo(self, buf):
        #something is off in the match info, sometimes tf for terms is > 0 when it should not be
        bufsize = len(buf)
        return [struct.unpack('@I', buf[i:i+4])[0] for i in range(0, bufsize, 4)]

    def clean(self, text):
        return clean(text, self.stopWords)


    
    def simpleRank(self, rawMatchInfo):
        """
        Based on https://github.com/saaj/sqlite-fts-python/blob/master/sqlitefts/ranking.py
        """
        match_info = self._parseMatchInfo(rawMatchInfo)
        score = 0.0
        p, c = match_info[:2]
        for phrase_num in range(p):
            phrase_info_idx = 2 + (phrase_num * c * 3)
            for col_num in range(c):
                col_idx = phrase_info_idx + (col_num * 3)
                x1, x2 = match_info[col_idx:col_idx + 2]
                if x1 > 0:
                    score += float(x1) / x2
        return -score

    

    def bm25(self, rawMatchInfo, *args):
        match_info = self._parseMatchInfo(rawMatchInfo)
        #increase?
        K = 0.5
        B = 0.75
        score = 0.0

        P_O, C_O, N_O, A_O = range(4)
        term_count = match_info[P_O]
        col_count = match_info[C_O]
        total_docs = match_info[N_O]
        L_O = A_O + col_count
        X_O = L_O + col_count

        if not args:
            weights = [1] * col_count
        else:
            weights = [0] * col_count
            for i, weight in enumerate(args):
                weights[i] = weight

        #collect number of different matched terms
        cd = 0
        for i in range(term_count):
            for j in range(col_count):
                x = X_O + (3 * j * (i + 1))
                if float(match_info[x]) != 0.0:
                    cd += 1 

        for i in range(term_count):
            for j in range(col_count):
                weight = weights[j]
                if weight == 0:
                    continue

                avg_length = float(match_info[A_O + j])
                doc_length = float(match_info[L_O + j])
                if avg_length == 0:
                    D = 0
                else:
                    D = 1 - B + (B * (doc_length / avg_length))

                x = X_O + (3 * j * (i + 1))
                term_frequency = float(match_info[x])
                docs_with_term = float(match_info[x + 2])

                idf = max(
                    math.log(
                        (total_docs - docs_with_term + 0.5) /
                        (docs_with_term + 0.5)),
                    0)
                denom = term_frequency + (K * D)
                if denom == 0:
                    rhs = 0
                else:
                    rhs = (term_frequency * (K + 1)) / denom

                score += (idf * rhs) * weight 
        return -score - cd * 20


    def addNote(self, note):
        
        content = " \u001f ".join(note.fields)
        tags = " ".join(note.tags)
        did = str(note.model()['did'])
        conn = sqlite3.connect(self.dir + "/search-data.db")
        conn.cursor().execute("INSERT INTO notes (nid, text, tags, did, source) VALUES (?, ?, ?, ?, ?)", (str(note.id), clean(content, self.stopWords), tags, did, content))
        conn.commit()
        conn.close()
    

    def getNumberOfNotes(self):
        conn = sqlite3.connect(self.dir + "/search-data.db")
        res = conn.cursor().execute("select count(*) from notes_content").fetchone()[0]
        conn.close()
        return res


class Worker(QRunnable):
 
    def __init__(self, fn, *args):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        try:
            result = self.fn(*self.args)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            #use stamp to track time
            self.signals.result.emit(result, self.stamp)  
        finally:
            self.signals.finished.emit()

class WorkerSignals(QObject):
   
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object, object)
    progress = pyqtSignal(int)
