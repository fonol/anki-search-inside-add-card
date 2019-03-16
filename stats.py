from aqt import mw


def findNotesWithLowestPerformance(decks, limit, retOnly = False):
    #avgRetAndTime = getAvgTrueRetentionAndTime()
    if not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)
    else:
        deckQ = ""
    if deckQ:
        notes = mw.col.db.execute("select notes.id, cards.id, flds, tags, did from cards left join notes on cards.nid = notes.id where did in %s order by notes.id" % deckQ).fetchall()
    else:
        notes = mw.col.db.execute("select notes.id, cards.id, flds, tags, did from cards left join notes on cards.nid = notes.id order by notes.id ").fetchall()
    scores = dict()
    cardsByNotes = dict()
    for note in notes:
        if note[0] in cardsByNotes:
            cardsByNotes[note[0]][1].append(note[1])
        else:
            cardsByNotes[note[0]] = (note, [note[1]])
    for k,v in cardsByNotes.items():
        score = _getScore(v[1], retOnly)
        if score is not None:
            if retOnly:
                    scores[k] = (score, v[0]) 
            else:
                scores[k] = (score[0], v[0]) 
    scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=False)
    rList = []
    for r in scores[:limit]:
        rList.append((r[1][1][2], r[1][1][3],r[1][1][4], r[1][1][0]))
    return rList


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


def _getScore(cards, onlyRet = False):
    if not cards:
        return None
    cStr = "("
    for c in cards:
        cStr += str(c) + ", "
    cStr = cStr[:-2] + ")"

    entries = mw.col.db.all( "select cid, ease, time, type from revlog where cid in %s" %(cStr))
    if not entries:
        return None
    cnt = 0
    passed = 0
    failed = 0
    goodAndEasy = 0
    hard = 0
    timeTaken = 0
    for (cid, ease, taken, ty) in reversed(entries):
        #only look for reviews
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
        
        timeTaken += taken  / 1000.0    
    if cnt <= 3:
        return None
    retention =  100 * passed / (passed + failed)
    retention = round(retention, 1)
    if onlyRet:
        return retention
    avgTime = round(timeTaken / cnt, 1)
    return _calcPerformanceScore(retention, avgTime, goodAndEasy, hard)


def calculateStats(nid, avgRetAndTime = None):
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
        for (cid, ease, taken, ty) in reversed(entries):
            #only look for reviews
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
            
            timeTaken += taken  / 1000.0        
        retention =  100 * passed / (passed + failed) if cnt > 0 else 0
        retention = round(retention, 1)
        avgTime = round(timeTaken / cnt, 1) if cnt > 0 else 0
        score = _calcPerformanceScore(retention, avgTime, goodAndEasy, hard) if cnt > 0 else (0, 0, 0, 0)
        s = ""
        s += "<div class='smallMarginTop'><span class='score'>Performance: %s</span><span class='minorScore'>Retention: %s</span><span class='minorScore'>Time: %s</span><span class='minorScore'>Ratings: %s</span></div><hr/>" %(str(score[0]), str(score[2]), str(score[1]), str(score[3]))
        s += "<b>%s</b> card(s) found for this note.<br/><br/>" %(str(len(cards)))
        if cnt > 0:
            if avgRetAndTime is None:
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
