
from aqt import *
from aqt.utils import showInfo

def findBySameTag(tagStr, limit, decks, pinned):
   
    query = "where "
    for t in tagStr.split(" "):
        if len(t) > 0:
            if len(query) > 6:
                query += " or "
            query += "lower(tags) like '% " + t + " %' or lower(tags) like '%::" + t + " %' or lower(tags) like '% " + t + "::%'"

  
    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid %s and did in %s" %(query, deckQ)).fetchall()
    else:
        res = mw.col.db.execute("select distinct notes.id, flds, tags, did from notes left join cards on notes.id = cards.nid %s" %(query)).fetchall()
    rList = []
    for r in res:
        #pinned items should not appear in the results
        if not str(r[0]) in pinned:
            rList.append((r[1], r[2], r[3], r[0]))
    return { "result" : rList[:limit]}
