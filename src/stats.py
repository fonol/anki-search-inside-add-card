from aqt import mw
from aqt.qt import *
import aqt

try:
    from .special_searches import *
    from .special_searches import _to_day_ivl
except: 
    from special_searches import *
    from special_searches import _to_day_ivl

import time
import json


def findNotesWithLowestPerformance(decks, limit, pinned, retOnly=False):
    #avgRetAndTime = getAvgTrueRetentionAndTime()
    scores = _calcScores(decks, limit, retOnly)
    scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=False)
    rList = []
    c = 0
    for r in scores:
        if str(r[1][1][0]) not in pinned:
            rList.append((r[1][1][2], r[1][1][3], r[1][1][4], r[1][1][0], 1, r[1][1][5]))
            c += 1
            if c >= limit:
                break
    return rList


def findNotesWithHighestPerformance(decks, limit, pinned, retOnly=False):
    scores = _calcScores(decks, limit, retOnly)
    scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
    rList = []
    c = 0
    for r in scores:
        if str(r[1][1][0]) not in pinned:
            rList.append((r[1][1][2], r[1][1][3], r[1][1][4], r[1][1][0], 1, r[1][1][5]))
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
        res = mw.col.db.execute("select notes.id, flds, tags, did, cards.nid, notes.mid FROM cards left join notes on cards.nid = notes.id where did in %s and reps > 0 group by cards.nid order by ivl %s limit %s" % (
            deckQ, sortOrder, limit)).fetchall()
    else:
        res = mw.col.db.execute("select notes.id, flds, tags, did, cards.nid, notes.mid FROM cards left join notes on cards.nid = notes.id where reps > 0 group by cards.nid order by ivl %s limit %s" % (
            sortOrder, limit)).fetchall()
    rList = []
    for r in res:
        if not str(r[0]) in pinned:
            rList.append((r[1], r[2], r[3], r[0], 1, r[5]))
    return rList


def _calcScores(decks, limit, retOnly):
    if not "-1" in decks:
        deckQ = "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        notes = mw.col.db.execute(
            "select notes.id, cards.id, flds, tags, did, notes.mid from cards left join notes on cards.nid = notes.id where did in %s order by notes.id" % deckQ).fetchall()
    else:
        notes = mw.col.db.execute(
            "select notes.id, cards.id, flds, tags, did, notes.mid from cards left join notes on cards.nid = notes.id order by notes.id ").fetchall()
    scores = dict()
    cardsByNotes = dict()
    for note in notes:
        if note[0] in cardsByNotes:
            cardsByNotes[note[0]][1].append(note[1])
        else:
            cardsByNotes[note[0]] = (note, [note[1]])
    for k, v in cardsByNotes.items():
        score = _getScore(v[1], retOnly)
        if score is not None:
            if retOnly:
                scores[k] = (score, v[0])
            else:
                scores[k] = (score[0], v[0])
    return scores


def getAvgTrueRetention(nids):
    query = "select id from cards where nid in %s" % (
        "(%s)" % ",".join([str(nid) for nid in nids]))
    cids = mw.col.db.execute(query).fetchall()
    cids = [c[0] for c in cids]
    tret = _getScore(cids, True)
    return tret


def getTrueRetentionOverTime(nids):
    query = "select id from cards where nid in %s" % (
        "(%s)" % ",".join([str(nid) for nid in nids]))
    cids = mw.col.db.execute(query).fetchall()
    cids = [c[0] for c in cids]
    return _getTrueRetentionOverTime(cids)


def getRetentions(nids):
    # for testing
    if mw is None:
        return dict()
    passedById = dict()
    failedById = dict()
    retsByNid = {}
    query = "select a.nid, ease from revlog join (select notes.id as nid, cards.id as cid from notes join cards on notes.id = cards.nid where notes.id in (%s)) as a on revlog.cid = a.cid where revlog.type = 1"
    query = query % ",".join([str(n) for n in nids])
    res = list(mw.col.db.execute(query).fetchall())

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
    return (round(retention, 1), round(timeTaken / cnt, 1))


def calcAbsDiffInPercent(i1, i2):
    diff = round(i1 - i2, 2)
    if diff >= 0:
        return "+ " + str(diff)
    else:
        return str(diff)


def _getTrueRetentionOverTime(cards):
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


def _getScore(cards, onlyRet=False):
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
    timeTaken = 0
    for (cid, ease, taken, ty) in reversed(entries):
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
    return _calcPerformanceScore(retention, avgTime, goodAndEasy, hard)


def calculateStats(nid, gridView):

    tables = {
        "Note": [],
        "Cards": [],
        "Stats": []
    }
    infoTable = {}
    infoTable["Note ID"] = nid

    note = mw.col.getNote(nid)
    model = mw.col.models.get(note.mid)
    templates = mw.col.findTemplates(note)

    try:
        infoTable["Created Date"] = time.strftime("%Y-%m-%d", time.localtime(int(nid)/1000)) + " &nbsp;&nbsp;<a class='keyword' href='#' style='float: right;' onclick='pycmd(\"addedSameDay %s\"); $(\"#a-modal\").hide(); return false;'>Added Same Day</a>" % nid
        infoTable["Last Modified"] = time.strftime(
            "%Y-%m-%d", time.localtime(note.mod))
    except:
        pass
    if model is not None:
        infoTable["Note Type"] = model["name"]

    # get card ids for note
    cards = mw.col.db.all("select * from cards where nid = %s" % (nid))
    if not cards:
        infoTable["Result"] = "No cards found"
        tables["Note"].append(infoTable)
        return _buildTable(tables)
    cardOrdById = {}
    cardTypeById = {}
    cardEaseFactorById = {}
    cardQueueById = {}
    cStr = "("
    for c in cards:
        cStr += str(c[0]) + ", "
        cardOrdById[c[0]] = c[3]
        cardTypeById[c[0]] = _cardTypeStr(c[6])
        cardEaseFactorById[c[0]] = int(c[10] / 10)
        cardQueueById[c[0]] = c[7]
    cStr = cStr[:-2] + ")"

    cardNameById = {}
    for k, v in cardOrdById.items():
        for temp in templates:
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

    reviewPlotData = {}
    ivlPlotData = {}
    timePlotData = {}
    similar_res_by_cid = {}

    if not entries or not hasReview:
        infoTable["Result"] = "No cards have been reviewed yet for this note"
        tables["Note"].append(infoTable)
    else:
        cnt = 0
        passed = 0
        failed = 0
        easy = 0
        goodAndEasy = 0
        good = 0
        hard = 0
        timeTaken = 0
        intervalsByCid = {}
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

        retention = 100 * passed / (passed + failed) if cnt > 0 else 0
        retention = round(retention, 1)
        avgTime = round(timeTaken / cnt, 1) if cnt > 0 else 0
        score = _calcPerformanceScore(
            retention, avgTime, goodAndEasy, hard) if cnt > 0 else (0, 0, 0, 0)
        
        tables["Note"].append(infoTable)
        infoTable = {}



        infoTable["Cards Found"] = len(cards)
        tables["Cards"].append(infoTable)


        for k, v in cardNameById.items():
            infoTable = {}
            label = ""
            if cardQueueById[k] == -1:
                label = "<span style='background: orange; color: black;'>Suspended</span>"
            elif cardQueueById[k] == 0:
                label = "<span style='background: orange; color: black;'>NEW</span>"
            elif cardQueueById[k] == 1:
                label = "<span style='background: orange; color: black;'>LEARNING</span>"
            infoTable["<b>%s</b>  &nbsp;(%s):" % (v, k)] = label
            if k in intervalsByCid:
                infoTable[_get_revlog_graph(k)] = ""
                infoTable["Interval"] = "%s %s" % (
                    abs(intervalsByCid[k]), "Days" if intervalsByCid[k] > 0 else "Seconds")
            if k in cardEaseFactorById:
                infoTable["Ease"] = str(cardEaseFactorById[k]) + " %"
            if k in cardTypeById:
                infoTable["Type"] = cardTypeById[k]
            tables["Cards"].append(infoTable)
            # similar_res = find_cards_with_similar_rep_history(int(k))
            # similar_res_by_cid[int(k)] = similar_res

        infoTable = {}
        infoTable["<b>Reviews (Cards from this note)</b>"] = cnt
        infoTable["&nbsp;&nbsp;&nbsp; <span style='color: red'>Failed</span>"] = failed
        infoTable["&nbsp;&nbsp;&nbsp; <span style='color: black'>Hard</span>"] = hard
        infoTable["&nbsp;&nbsp;&nbsp; <span style='color: green'>Good</span>"] = good
        infoTable["&nbsp;&nbsp;&nbsp; <span style='color: blue'>Easy</span>"] = easy
        tables["Stats"].append(infoTable)

        if cnt > 0:
            avgRetAndTime = getAvgTrueRetentionAndTime()
            infoTable = {}
            infoTable["<b>Pass Rate (Successful Reviews * 100 / Reviews)</b>"] = ""
            infoTable["Cards from this note"] = str(retention) + " %"
            infoTable["Collection"] = str(avgRetAndTime[0]) + " %"
            infoTable["Difference"] = str(
                calcAbsDiffInPercent(retention, avgRetAndTime[0])) + " %"
            tables["Stats"].append(infoTable)

            infoTable = {}
            infoTable["<b>Average Time (Reviews Only)</b>"] = ""
            infoTable["Cards from this note"] = str(avgTime) + " seconds"
            infoTable["Collection"] = str(avgRetAndTime[1]) + " seconds"
            infoTable["Difference"] = str(calcAbsDiffInPercent(
                avgTime, avgRetAndTime[1])) + " seconds"
            tables["Stats"].append(infoTable)

        infoTable = {}
        infoTable["Retention Score"] = score[2]
        infoTable["Time Score"] = score[1]
        infoTable["Rating Score"] = score[3]
        infoTable["<b>Performance</b>"] = score[0]
        tables["Stats"].append(infoTable)

    html = _buildTable(tables, reviewPlotData, ivlPlotData,
                       timePlotData, cardNameById)
    # if similar_res_by_cid:
    #     html += _build_similarity_table(similar_res_by_cid, intervalsByCid)
    return(html, reviewPlotData, ivlPlotData, timePlotData)


def _build_similarity_table(similar_res_by_cid, card_ivl_by_id):
    html = """
            <br/>
            <h3 class='full-width' style='text-align: center;'>Similar Cards</h3>
            Cards whose review history is similar to the given card one's. Similarity is measured among the interval steps (only in reviews) 
            that a card went through. If our card has an interval of 95 days at the 4th review, and another card has 90 days at the 4th review, 
            the similarity at this step is <br/>
            (95 / 100) * 90 = 85.5 %.<br/> 
            Similarities at each interval step are summed up and averaged to get the total similarity.
            <br/>
            <br/>
            <b>Sample:</b> Cards, whose review history is as close as possible to the given card.<br/>
            <b>Estimated Success Chance:</b> All cards in the given sample must have at least one more review than our card. Success chance is then <i>Number of Successful Next Reviews</i> / <i>Sample Size</i><br/>
            <b>Average Interval:</b> Average Interval in the sample at our cards current step.<br/>
            <b>Average Pass Rate:</b> <i>Sum of each sample's pass rate</i> / <i>Sample Size</i><br/>
            """
    for cid, similar_res in similar_res_by_cid.items():
        html += "<br/><div class='full-width' style='text-align: center; margin-bottom: 10px;'>Similar cards for " + str(cid) + ":</div>"
        
        if len(similar_res[0]) == 1 and 50 in similar_res[0] and similar_res[0][50]["sample_size"] == 0:
            html += "Could not find any samples that have at least an average similarity of 50%."
            continue
        html += """<table class='striped full-width'>
                        <thead>
                            <tr>
                                <td><b>Sample</b></td>
                                <td><b>Est. Succ. Chance</b></td>
                                <td><b>Avg. Ivl</b></td>
                                <td><b>Avg. Pass Rate</b></td>
                            </tr> 
                        </thead>
                        <tbody>
                        """
        rows = ""
        for k, v in similar_res[0].items():
            rows += """<tr class='sa-blue-hover sa-cursor-pointer' onclick='pycmd("similarForCard %s %s")'>
                                <td style='%s'>%s Cards w. Similarity > %s %%</td>
                                <td style='%s'>%s %%</td>
                                <td>%s %s</td>
                                <td>%s %%</td>
                            </tr>""" % (
                                cid, k,
                "color: grey;" if v["sample_size"] <= 1 else "", v["sample_size"], k,
                "color: grey;text-decoration:line-through;" if v["sample_size"] <= 1 else "" , round(v["avg_next_success_chance"], 1),
                int(v["avg_current_ivl"]), _get_ivl_diff_str(card_ivl_by_id[cid], int(v["avg_current_ivl"])),
                round(v["avg_pass_rate"], 1)
            )
        html += rows
        html += "</tbody></table>"
    return html



def _get_ivl_diff_str(ivl_base, ivl_cmp):
    diff = ivl_cmp - ivl_base
    if diff < 0:
        return "<span style='color: red;'>(- %s)</span>" % abs(diff)
    if diff == 0:
        return "<span>(+0)</span>"
    return "<span style='color: green;'>(+ %s)</span>" % abs(diff)


def _buildTable(tables, reviewPlotData, ivlPlotData, timePlotData, namesByCid):
    s = "<div style='width: calc(100%% - 5px); overflow-y: auto; padding-right: 5px;'>%s</div>"
    rows = ""
    for k, v in tables.items():
        if len(v) > 0:
            rows += "<fieldset style='margin-bottom: 10px; font-size: 11px;'><legend>%s</legend>" % k
            rows += "<table class='striped' style='width: 100%; margin-bottom: 5px;'>"
        scount = 0
        for table in v:
            scount += 1
            if scount > 1:
                rows += "<tr><td>&nbsp;</td><td>&nbsp;</td></tr>"
            for key, value in table.items():
                rows += "<tr style='width: 100%%'><td>%s</td><td><b>%s</b></td></tr>" % (
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
            if len(v) > 1:
                c += 1
                s += "<div style='text-align: center; width: 100%%;'><h3 style='margin-top: 10px;'>Reviews over time for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
        for k, v in ivlPlotData.items():
            if len(v) > 1:
                c += 1
                s += "<div style='text-align: center; width: 100%%;'><h3 style='margin-top: 10px;'>Interval over time for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
        for k, v in timePlotData.items():
            if len(v) > 1:
                c += 1
                s += "<div style='text-align: center; width: 100%%;'><h3 style='margin-top: 10px;'>Answer times for <i>%s</i>:</h3>" % namesByCid[
                    k]
                s += "<div id='graph-" + \
                    str(c) + "' style='width: %s; height: %s; margin-left: auto; margin-right: auto; margin-top: 5px; margin-bottom: 55px;'></div></div>" % (graphWidth, graphHeight)
    return s


def _cardTypeStr(typeNumber):
    if typeNumber == 0:
        return "new"
    if typeNumber == 1:
        return "learning"
    if typeNumber == 2:
        return "due"
    if typeNumber == 3:
        return "filtered"
    return "?"

def _get_revlog_graph(cid):
    entries = mw.col.db.execute("select * from revlog where cid = %s and (type = 1 or type = 2)" % cid).fetchall()
    html = "<div class='full-width'>%s</div>"
    blocks = ""
    for _,_,_,ease,ivl,_,_,_,type in entries:
        ease = ease + 1 if type == 2 and ease > 1 else ease
        sivl = int(_to_day_ivl(ivl)) if int(_to_day_ivl(ivl)) > 0 else "<1"
        blocks += "<div class='revlog-block revlog-block-%s %s'>%s</div>" % (ease, "larger" if ivl > 1000 else "",  sivl)
    
    return html % blocks



def _calcPerformanceScore(retention, time, goodAndEasy, hard):
    if goodAndEasy == 0 and hard == 0:
        return (0, 0, 0, 0)
    # retention is counted higher, numbers are somewhat arbitrary
    score = 0
    retentionSc = 2 * retention * (1 - ((100 - retention) / 100))
    score += retentionSc
    timeSc = 100.0 - time / 3.0 * 10.0
    if timeSc < 0:
        timeSc = 0
    score += timeSc
    ratingSc = (goodAndEasy / (goodAndEasy + hard)) * 100
    score += ratingSc
    score = round(score * 100.0 / 400.0, 1)
    return (int(score), int(timeSc), int(retentionSc * 100.0 / 200.0), int(ratingSc))


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