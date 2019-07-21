
from aqt import *
from aqt.utils import showInfo
from .textutils import trimIfLongerThan
from .stats import getAvgTrueRetention
from .output import Output

def findBySameTag(tagStr, limit, decks, pinned):
   
    query = "where "
    for t in tagStr.split(" "):
        if len(t) > 0:
            t = t.replace("'", "''")
            if len(query) > 6:
                query += " or "
            query += "lower(tags) like '% " + t + " %' or lower(tags) like '% " + t + "::%' or lower(tags) like '%::" + t + " %' or lower(tags) like '% " + t + "::%'"

  
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

def buildTagInfo(editor, tag, synonyms):
    if " " in tag:
        tagsContained = tag.split(" ")
    else:
        tagsContained = [tag]
    for synset in synonyms:
        synsetNorm = [s.lower() for s in synset]
        for tag in tagsContained:
            if tag.lower() in synsetNorm:
                tag += " " + " ".join(synset)
                break
    searchRes = findBySameTag(tag, 30000, [], [])
    tagsfound = {}
    for r in searchRes["result"]:
        spl = r[1].split()
        for s in spl:
            if s == tag or s in tag.split():
                continue
            if s in tagsfound:
                tagsfound[s] += 1
            else:
                tagsfound[s] = 1
    sortedCounts = sorted(tagsfound.items(), key=lambda kv: kv[1], reverse=True)
    html = """
        <span id='trueRetGraphLbl'>Retention for this Topic / Reviews</span>
        <div id="trueRetGraph" style='width: 250px; height: 130px; margin-right: auto; margin-left: auto;'></div>
        <table style='width: 100%%; margin-top: 5px;'>
            <tr><td style='text-align: left;'>Retention</td><td style='text-align: right;'><b>%s</b></td></tr>
            <tr><td style='text-align: left;'>Notes</td><td style='text-align: right;'><b>%s</b></td></tr>
            <tr><td style='text-align: left'>Related</td><td>%s</td></tr></table>
    """ 
    tags = ""
   
    if len(sortedCounts) < 3:
        starter = set([t[0] for t in sortedCounts])
        for t in sortedCounts:
            res = findBySameTag(t[0], 30000, [], [])
            for r in res["result"]:
                spl = r[1].split()
                for s in spl:
                    if s == tag or s in tag.split(): #or s in starter:
                        continue
                    if s in tagsfound:
                        tagsfound[s] += 1
                    else:
                        tagsfound[s] = 1
        sortedCounts = sorted(tagsfound.items(), key=lambda kv: kv[1], reverse=True)
    total_length = 0
    for k in sortedCounts[:10]:
        tags += "<div class='tagLbl smallMarginBottom' data-name='%s' onclick='tagClick(this);'>%s</div>" % (k[0], trimIfLongerThan(k[0], 40))
        total_length += len(trimIfLongerThan(k[0], 40))
        if total_length > 120:
            break
    
    nids = [r[3] for r in searchRes["result"]]
    tret = getAvgTrueRetention(nids)
    if tret is not None:
        color = Output._retToColor(tret)    
        tret = "<span style='background: %s'>&nbsp;%s&nbsp;</span>" % (color, tret)

    html = html % (tret if tret is not None else "Not enough reviews", len(searchRes["result"]), tags)
    editor.web.eval("$('.tooltiptext-tag.shouldFill').html(`%s`).show();" % html)
    return nids