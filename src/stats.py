# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from aqt import mw
from aqt.qt import *
import aqt


try:
    from .models import IndexNote
except: 
    from models import IndexNote

import time
import json
import utility.misc

"""
Various statistics functions.
Mainly used for the information displayed when clicking on "i" on a note or for some of the predefined searches.
Todo: Add typing annotation
"""

def findNotesWithLowestPerformance(decks, limit, pinned, retOnly=False):
    #avgRetAndTime = getAvgTrueRetentionAndTime()
    scores  = _calcScores(decks, limit, retOnly)
    scores  = sorted(scores.items(), key=lambda x: x[1][0], reverse=False)
    rList   = []
    c       = 0
    for r in scores:
        if str(r[1][1][0]) not in pinned:
            rList.append(IndexNote((r[1][1][0], r[1][1][2], r[1][1][3], r[1][1][4], r[1][1][2], -1, r[1][1][5], "", -1)))
            c += 1
            if c >= limit:
                break
    return rList

def findNotesWithHighestPerformance(decks, limit, pinned, retOnly=False):
    scores  = _calcScores(decks, limit, retOnly)
    scores  = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
    rList   = []
    c       = 0
    for r in scores:
        if str(r[1][1][0]) not in pinned:
            rList.append(IndexNote((r[1][1][0], r[1][1][2], r[1][1][3], r[1][1][4], r[1][1][2], -1, r[1][1][5], "", -1)))
            c += 1
            if c >= limit:
                break
    return rList

def getSortedByInterval(decks, limit, pinned, sortOrder):
    if not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        res = mw.col.db.all("select notes.id, flds, tags, did, cards.nid, notes.mid FROM cards left join notes on cards.nid = notes.id where did in %s and reps > 0 group by cards.nid order by ivl %s limit %s" % (
            deckQ, sortOrder, limit))
    else:
        res = mw.col.db.all("select notes.id, flds, tags, did, cards.nid, notes.mid FROM cards left join notes on cards.nid = notes.id where reps > 0 group by cards.nid order by ivl %s limit %s" % (
        sortOrder, limit))
    rList = []
    for r in res:
        if not str(r[0]) in pinned:
           #. rList.append((r[1], r[2], r[3], r[0], 1, r[5]))
           rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))
    return rList

def _calcScores(decks, limit, retOnly):
    if not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        notes = mw.col.db.all(
            "select notes.id, cards.id, flds, tags, did, notes.mid from cards left join notes on cards.nid = notes.id where did in %s order by notes.id" % deckQ)
    else:
        notes = mw.col.db.all(
            "select notes.id, cards.id, flds, tags, did, notes.mid from cards left join notes on cards.nid = notes.id order by notes.id ")
    scores = dict()
    cardsByNotes = dict()
    for note in notes:
        if note[0] in cardsByNotes:
            cardsByNotes[note[0]][1].append(note[1])
        else:
            cardsByNotes[note[0]] = (note, [note[1]])
    for k, v in cardsByNotes.items():
        score = _get_score(v[1], retOnly)
        if score is not None:
            if retOnly:
                scores[k] = (score, v[0])
            else:
                scores[k] = (score[0], v[0])
    return scores

def getAvgTrueRetention(nids):

    query   = "select id from cards where nid in %s" % ("(%s)" % ",".join([str(nid) for nid in nids]))
    cids    = mw.col.db.all(query)
    cids    = [c[0] for c in cids]
    tret    = _get_score(cids, True)

    return tret


def getTrueRetentionOverTime(nids):

    query = "select id from cards where nid in %s" % (
        "(%s)" % ",".join([str(nid) for nid in nids]))
    cids = mw.col.db.all(query)
    cids = [c[0] for c in cids]

    return _get_true_retention_over_time(cids)

def getRetentions(nids):

    passedById  = dict()
    failedById  = dict()
    retsByNid   = {}
    query       = "select a.nid, ease from revlog join (select notes.id as nid, cards.id as cid from notes join cards on notes.id = cards.nid where notes.id in (%s)) as a on revlog.cid = a.cid where revlog.type = 1"
    query       = query % ",".join([str(n) for n in nids])
    res         = list(mw.col.db.all(query))

    for r in res:
        if r[0] is None:
            continue
        if r[0] not in passedById:
            passedById[r[0]] = 0
        if r[0] not in failedById:
            failedById[r[0]] = 0
        if r[1] != 1:
            passedById[r[0]] += 1
        else:
            failedById[r[0]] += 1

    for k, v in passedById.items():
        retsByNid[k] = round(100 * v / (v + failedById[k]), 0)

    return retsByNid

def getAvgTrueRetentionAndTime():
    eases       = mw.col.db.all("select ease, time from revlog where type = 1")
    if not eases:
        return 0
    cnt         = 0
    passed      = 0
    failed      = 0
    timeTaken   = 0

    for ease, taken in eases:
        cnt += 1
        if ease != 1:
            passed += 1
        else:
            failed += 1
        timeTaken += taken / 1000.0

    retention   = 100 * passed / (passed + failed) if cnt > 0 else 0
    retention   = round(retention, 2)

    return (round(retention, 1), round(timeTaken / cnt, 1))

def calc_abs_diff_in_percent(i1, i2):
    return round(i1 - i2, 2)
  
def _get_true_retention_over_time(cards):
    if not cards:
        return None
    cStr = "("
    for c in cards:
        cStr += str(c) + ", "
    cStr = cStr[:-2] + ")"

    entries = mw.col.db.all(
        "select cid, ease, time, type from revlog where cid in %s" % (cStr))
    if not entries:
        return None
    cnt = 0
    passed = 0
    failed = 0
    goodAndEasy = 0
    hard = 0

    retentionsOverTime = []

    for (_, ease, _, ty) in entries:
        # only look for reviews
        if ty != 1:
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
        if cnt > 3:
            retention = 100 * passed / (passed + failed)
            retention = round(retention, 1)
            retentionsOverTime.append(retention)
    if cnt <= 3:
        return None
    return retentionsOverTime

def _get_score(cards, onlyRet=False):
    if not cards:
        return None

    cStr        = "("
    for c in cards:
        cStr    += str(c) + ", "
    cStr        = cStr[:-2] + ")"

    entries     = mw.col.db.all("select cid, ease, time, type from revlog where cid in %s" % (cStr))
    if not entries:
        return None

    cnt         = 0
    passed      = 0
    failed      = 0
    goodAndEasy = 0
    hard        = 0
    timeTaken   = 0
    for (_, ease, taken, ty) in reversed(entries):
        # only look for reviews
        if ty != 1:
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

        timeTaken += taken / 1000.0
    if cnt <= 3:
        return None
    retention = 100 * passed / (passed + failed)
    retention = round(retention, 1)
    if onlyRet:
        return retention
    avgTime = round(timeTaken / cnt, 1)
    return _calc_performance_score(retention, avgTime, goodAndEasy, hard)

def calculate_note_stats(nid):

    tables = {
        "Note"  : [],
        "Cards" : [],
        "Stats" : []
    }
    i_table = {}
    i_table["Note ID"] = f"""{nid} &nbsp;<span class='keyword' onclick='pycmd("siac-copy-to-cb {nid}")'>[Copy to Clipboard]</span>"""

    note        = mw.col.getNote(int(nid))
    model       = mw.col.models.get(note.mid)

    try:
        i_table["Created Date"] = time.strftime("%Y-%m-%d", time.localtime(int(nid)/1000)) + " &nbsp;&nbsp;<a class='keyword' href='#' style='float: right;' onclick='pycmd(\"siac-r-added-same-day %s\"); $(\"#siac-modal\").hide(); return false;'>Added Same Day</a>" % nid
        i_table["Last Modified"] = time.strftime("%Y-%m-%d", time.localtime(note.mod))
 
    except:
        pass
    if model is not None:
        i_table["Note Type"] = model["name"]
    
    i_table["Tags"] = " ".join(note.tags) if note.tags else "-"

    # get card ids for note
    cards               = mw.col.db.all("select * from cards where nid = %s" % (nid))
    if not cards:
        i_table["Result"] = "No cards found"
        tables["Note"].append(i_table)
        return _build_table(tables)

    cardOrdById         = {}
    cardTypeById        = {}
    cardEaseFactorById  = {}
    cardQueueById       = {}
    decks               = set()
    cStr                = "("

    for c in cards:
        d = mw.col.decks.get(c[2])["name"]
        if not d in decks:
            decks.add(d)
        cStr                        = f"{cStr}{c[0]}, "
        cardOrdById[c[0]]           = c[3]
        cardTypeById[c[0]]          = _card_type_str(c[6])
        cardEaseFactorById[c[0]]    = int(c[10] / 10)
        cardQueueById[c[0]]         = c[7]

    cStr                = f"{cStr[:-2]})"

    if len(decks) > 0:
        i_table["Deck(s)"] = ", ".join(decks)
    else:
        i_table["Deck(s)"] = "Could not determine decks."

    cardNameById = {}
    for k, v in cardOrdById.items():
        tmpls = mw.col.getCard(k).model()["tmpls"]
        for temp in tmpls:
            if temp['ord'] == v:
                cardNameById[k] = temp['name']

    entries = mw.col.db.all(
        "select id, cid, ease, ivl, time, type from revlog where cid in %s" % (cStr))

    hasReview = False
    if entries:
        for (_, _, _, _, _, ty) in entries:
            if ty == 1:
                hasReview = True
                break

    reviewPlotData      = {}
    ivlPlotData         = {}
    timePlotData        = {}

    i_table["Card ID(s)"]     = ", ".join([str(c[0]) + f" ({_card_type_str(c[6])}) <span class='keyword' onclick='pycmd(\"siac-copy-to-cb {c[0]}\")'>[Copy]</span>" for c in cards])

    if not entries or not hasReview:
        i_table["[Stats]"]        = "Not enough reviews to compute statistics"
        tables["Note"].append(i_table)
    else:
        cnt             = 0
        passed          = 0
        failed          = 0
        easy            = 0
        goodAndEasy     = 0
        good            = 0
        hard            = 0
        timeTaken       = 0
        intervalsByCid  = {}

        for (stamp, cid, ease, ivl, taken, ty) in entries:
            # only look for reviews
            if ty != 1:
                continue
            cnt += 1
            intervalsByCid[cid] = ivl
            if not cid in reviewPlotData:
                reviewPlotData[cid] = []
            if not cid in ivlPlotData:
                ivlPlotData[cid] = []
            if not cid in timePlotData:
                timePlotData[cid] = []
            reviewPlotData[cid].append([cnt, ease, time.strftime(
                "%Y-%m-%d", time.localtime(int(stamp)/1000))])
            ivlPlotData[cid].append([cnt, max(0, ivl), time.strftime(
                "%Y-%m-%d", time.localtime(int(stamp)/1000))])
            timePlotData[cid].append(
                [cnt, taken / 1000, time.strftime("%Y-%m-%d", time.localtime(int(stamp)/1000))])
            if ease != 1:
                passed += 1
                if ease == 2:
                    hard += 1
                else:
                    goodAndEasy += 1
                    if ease == 3:
                        good += 1
                    else:
                        easy += 1
            else:
                failed += 1

            timeTaken += taken / 1000.0

        retention               = 100 * passed / (passed + failed) if cnt > 0 else 0
        retention               = round(retention, 1)
        avgTime                 = round(timeTaken / cnt, 1) if cnt > 0 else 0
        score                   = _calc_performance_score(retention, avgTime, goodAndEasy, hard) if cnt > 0 else (0, 0, 0, 0)
        
        tables["Note"].append(i_table)
        i_table               = {}

        i_table["Cards Found"] = len(cards)
        tables["Cards"].append(i_table)

        for k, v in cardNameById.items():
            i_table   = {}
            label       = ""

            if cardQueueById[k] == -1:
                label = "<span style='background: orange; color: black;'>Suspended</span>"
            elif cardQueueById[k] == 0:
                label = "<span style='background: orange; color: black;'>NEW</span>"
            elif cardQueueById[k] == 1:
                label = "<span style='background: orange; color: black;'>LEARNING</span>"

            i_table["<b>%s</b>  &nbsp;(%s):" % (v, k)] = label

            if k in intervalsByCid:
                i_table[_get_revlog_graph(k)] = ""
                i_table["Interval"] = "%s %s" % (
                    abs(intervalsByCid[k]), "Days" if intervalsByCid[k] > 0 else "Seconds")

            if k in cardEaseFactorById:
                i_table["Ease"] = str(cardEaseFactorById[k]) + " %"

            if k in cardTypeById:
                i_table["Type"] = cardTypeById[k]

            tables["Cards"].append(i_table)
            # similar_res = find_cards_with_similar_rep_history(int(k))
            # similar_res_by_cid[int(k)] = similar_res

        i_table                                                               = {}
        i_table["<b>Reviews (Cards from this note)</b>"]                      = cnt
        i_table["<span class='ml-5 bg-red rev-lbl'>Failed</span>"]  = failed
        i_table["<span class='ml-5 rev-lbl' style='background: black; color: white;'>Hard</span>"]  = hard
        i_table["<span class='ml-5 rev-lbl bg-green' style='color: black;'>Good</span>"]  = good
        i_table["<span class='ml-5 rev-lbl bg-blue'>Easy</span>"]   = easy
        tables["Stats"].append(i_table)

        if cnt > 0:
            avgRetAndTime = getAvgTrueRetentionAndTime()
            i_table = {}
            i_table["<b>Pass Rate (Successful Reviews * 100 / Reviews)</b>"] = ""
            i_table["Cards from this note"] = str(retention) + " %"
            i_table["Collection"] = str(avgRetAndTime[0]) + " %"
            diff = calc_abs_diff_in_percent(retention, avgRetAndTime[0]) 
            if diff > 0:
                i_table["Difference"] = f"{diff} % <span style='color: green'>better</span>"
            elif diff < 0:
                i_table["Difference"] = f"{diff} % <span style='color: red'>worse</span>"

            
            tables["Stats"].append(i_table)

            i_table                                       = {}
            i_table["<b>Average Time (Reviews Only)</b>"] = ""
            i_table["Cards from this note"]               = str(avgTime) + " seconds"
            i_table["Collection"]                         = str(avgRetAndTime[1]) + " seconds"
            diff                                            = calc_abs_diff_in_percent(avgTime, avgRetAndTime[1])

            if diff > 0:
                i_table["Difference"]                     = f"{diff} seconds <span style='color: red'>slower</span>"
            elif diff < 0:
                i_table["Difference"]                     = f"{abs(diff)} seconds <span style='color: green'>faster</span>"
        
            tables["Stats"].append(i_table)

        i_table                       = {}
        i_table["Retention Score"]    = score[2]
        i_table["Time Score"]         = score[1]
        i_table["Rating Score"]       = score[3]
        i_table["<b>Performance</b>"] = score[0]
        tables["Stats"].append(i_table)

    html = _build_table(tables, reviewPlotData, ivlPlotData,
                       timePlotData, cardNameById)
    return(html, reviewPlotData, ivlPlotData, timePlotData)


def _build_table(tables, reviewPlotData, ivlPlotData, timePlotData, namesByCid):
    s = "<div style='width: calc(100%% - 5px); overflow-y: auto; padding-right: 5px;'>%s</div>"
    rows = ""
    for k, v in tables.items():
        if len(v) > 0:
            rows += "<fieldset class='mb-10' style='font-size: 11px;'><legend>%s</legend>" % k
            rows += "<table class='striped w-100 mb-5'>"
        scount = 0
        for table in v:
            scount += 1
            if scount > 1:
                rows += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
            for key, value in table.items():
                rows += "<tr class='w-100'><td>%s</td><td><b>%s</b></td></tr>" % (
                    key, value)
        #     if scount != len(v):
        #         rows += "<tr><td> </td><td></td> </tr>"
        if len(v) > 0:
            rows += "</table>"
            rows += "</fieldset>"
    c = 0
    s = s % rows

    hasGraph = False
    for k, v in reviewPlotData.items():
        if len(v) > 1:
            hasGraph = True
            break
    if not hasGraph:
        for k, v in ivlPlotData.items():
            if len(v) > 1:
                hasGraph = True
                break
    if not hasGraph:
        for k, v in timePlotData.items():
            if len(v) > 1:
                hasGraph = True
                break
    if hasGraph:
        currentWindow = aqt.mw.app.activeWindow()
        w = currentWindow.geometry().width()
        if w <= 450:
            graphWidth = "90%"
            graphHeight = "180px"
        else:
            graphWidth = "68%"
            graphHeight = "250px"

        for k, v in reviewPlotData.items():
            if k in namesByCid and len(v) > 1:
                c += 1
                s += "<div class='ta_center w-100'><h3 style='margin-top: 10px;'>Reviews over time for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
        for k, v in ivlPlotData.items():
            if k in namesByCid and len(v) > 1:
                c += 1
                s += "<div class='ta_center w-100'><h3 style='margin-top: 10px;'>Interval over time for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
        for k, v in timePlotData.items():
            if k in namesByCid and len(v) > 1:
                c += 1
                s += "<div class='ta_center w-100'><h3 style='margin-top: 10px;'>Answer times for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
    return s

def retention_stats_for_tag(true_ret_over_time, graph_div_id, graph_div_lbl_id):
    """
    Assumes that the tag info box ('#siac-tag-info-box') is already rendered.
    The box contains a div that is the placeholder for the retention graph.
    """
    if true_ret_over_time is None or len(true_ret_over_time) < 2:
        cmd = "$('#%s,#%s').hide();" % (graph_div_id, graph_div_lbl_id)
    else:
        options = """
                    {  series: { 
                            lines: { show: true, fillColor: "#2496dc" }, 
                    }, 
                    label: "True Retention", 
                    yaxis: { max: 100, min: 0
                    } , 
                    colors: ["#2496dc"] 
                    }
                """
        raw_data = [[i,t] for i, t in enumerate(true_ret_over_time)]
        cmd = "if ($.plot) { $.plot($('#%s'), [ %s ],  %s); }" % (graph_div_id, json.dumps(raw_data), options)
    return cmd


def _get_revlog_graph(cid):
    entries = mw.col.db.all("select * from revlog where cid = %s and (type = 1 or type = 2)" % cid)
    html = "<div class='w-100'>%s</div>"
    blocks = ""
    for _,_,_,ease,ivl,_,_,_,type in entries:
        ease = ease + 1 if type == 2 and ease > 1 else ease
        sivl = int(utility.misc.to_day_ivl(ivl)) if int(utility.misc.to_day_ivl(ivl)) > 0 else "<1"
        blocks += "<div class='revlog-block revlog-block-%s %s'>%s</div>" % (ease, "larger" if ivl > 1000 else "",  sivl)
    
    return html % blocks



def _calc_performance_score(retention, time, goodAndEasy, hard):
    if goodAndEasy == 0 and hard == 0:
        return (0, 0, 0, 0)

    # retention is counted higher, numbers are somewhat arbitrary
    score       = 0
    retentionSc = 2 * retention * (1 - ((100 - retention) / 100))
    score       += retentionSc
    timeSc      = 100.0 - time / 3.0 * 10.0
    if timeSc < 0:
        timeSc  = 0
    score       += timeSc
    ratingSc    = (goodAndEasy / (goodAndEasy + hard)) * 100
    score       += ratingSc
    score       = round(score * 100.0 / 400.0, 1)

    return (int(score), int(timeSc), int(retentionSc * 100.0 / 200.0), int(ratingSc))


def _card_type_str(typeNumber):
    if typeNumber == 0:
        return "New"
    if typeNumber == 1:
        return "Learning"
    if typeNumber == 2:
        return "Due"
    if typeNumber == 3:
        return "Filtered"
    return "?"