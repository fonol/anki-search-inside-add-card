import re
import time
import json
import os
from datetime import datetime
from aqt import mw
from aqt.utils import showInfo
from .textutils import clean, trimIfLongerThan, deleteChars, asciiFoldChar, isChineseChar
from .logging import log
from .stats import getRetentions

class Output:

    def __init__(self):
        self.editor = None
        self.SEP_RE = re.compile(r'(\u001f){2,}|(\u001f[\s\r\n]+\u001f)')
        self.SEP_END = re.compile(r'</div>\u001f$')
        self.SOUND_TAG = re.compile(r'sound[a-zA-Z0-9]*mp')
        self.IO_REPLACE = re.compile('<img src="[^"]+(-\d+-Q|-\d+-A|-(<mark>)?oa(</mark>)?-[OA]|-(<mark>)?ao(</mark>)?-[OA])\.svg" ?/?>(</img>)?')
        self.latest = -1
        self.wordToken = re.compile(u"[a-zA-ZÀ-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.I | re.U)
        self.gridView = False
        self.stopwords = []
        self.plotjsLoaded = False
        self.showRetentionScores = True
        self.lastResults = None
        self.hideSidebar = False
        self.uiVisible = True


        self.noteTemplate = """<div class='cardWrapper %s' id='nWr-%s'> 
                            <div class='topLeftWr'>
                                <div id='cW-%s' class='rankingLbl' onclick="expandRankingLbl(this)">%s<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div> 
                                %s
                            </div>
                            <div id='btnBar-%s' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='editLbl' onclick='edit(%s)'>Edit</div> 
                                <div class='srchLbl' onclick='searchCard(this)'>Search</div> 
                                <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div> 
                                <div class='floatLbl' onclick='addFloatingNote(%s)'>&#10063;</div> 
                                <div id='rem-%s' class='remLbl' onclick='removeNote(%s)'><span>&times;</span></div> 
                            </div>
                            <div class='cardR' onmouseup='getSelectionText()' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div> 
                            <div id='tags-%s'  style='position: absolute; bottom: 0px; right: 0px;'>%s</div>     
                            <div class='cardLeftBot' onclick='expandCard(%s, this)'>&nbsp;INFO&nbsp;</div>     
                        </div>"""

        self.noteTemplateSimple = """<div class='cardWrapper' style="display: block;"> 
                            <div class='topLeftWr'>
                                <div class='rankingLbl' onclick="expandRankingLbl(this)">%s<div class='rankingLblAddInfo'>%s</div><div class='editedStamp'>%s</div></div> 
                                %s
                            </div>
                            <div class='btnBar' id='btnBarSmp-%s' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='editLbl' onclick='edit(%s)'>Edit</div> 
                            </div>
                            <div class='cardR' onmouseup='getSelectionText()'  onmouseenter='cardMouseEnter(this, %s, "simple")' onmouseleave='cardMouseLeave(this, %s, "simple")'>%s</div> 
                            <div style='position: absolute; bottom: 0px; right: 0px;'>%s</div>     
                            <div class='cardLeftBot' onclick='expandCard(%s, this)'>&nbsp;INFO&nbsp;</div>     
                        </div>"""


    def printSearchResults(self, searchResults, stamp, editor=None, logging=False, printTimingInfo=False):
        """
        This is the html that gets rendered in the search results div.
        Args:
        searchResults - a list of tuples, see SearchIndex.search()
        """
        if stamp is not None:
            if stamp != self.latest:
                if logging:
                    log("PrintSearchResults: Aborting because stamp != latest")
                return
        if logging:
            log("Entering printSearchResults")
            log("Length (searchResults): " + str(len(searchResults)))
        html = ""
        allText = ""
        tags = []
        epochTime = int(time.time() * 1000)
        timeDiffString = ""
        newNote = ""
        lastNote = "" 
        nids = [r[3] for r in searchResults]

        self.lastResults = searchResults

        if self.showRetentionScores:
            retsByNid = getRetentions(nids)
        ret = 0
        for counter, res in enumerate(searchResults):
            try:
                timeDiffString = self._getTimeDifferenceString(res[3], epochTime)
            except:
                if logging:
                    log("Failed to determine creation date: " + str(res[3]))
                timeDiffString = "Could not determine creation date"
            ret = retsByNid[int(res[3])] if self.showRetentionScores and int(res[3]) in retsByNid else None

            if ret is not None:
                retMark = "background: %s; color: black;" % (self._retToColor(ret)) 
                if str(res[3]) in self.edited:
                    retMark += "max-width: 20px;"
                retInfo = """<div class='retMark' style='%s'>%s</div>
                             """ % (retMark, int(ret))
            else:
                retInfo = ""

            lastNote = newNote
            text = self._cleanFieldSeparators(res[0]).replace("\\", "\\\\")
            text = self.tryHideImageOcclusion(text)
            newNote = self.noteTemplate % ("" if not self.gridView else "grid", counter + 1, res[3], counter + 1, 
                        "&nbsp;&#128336; " + timeDiffString,
                        "" if str(res[3]) not in self.edited else "&nbsp;&#128336; " + self._buildEditedInfo(self.edited[str(res[3])]),
                        retInfo, res[3],res[3],res[3],res[3], res[3], res[3], res[3], res[3], res[3], res[3], res[3], 
                        text, 
                        res[3], self.buildTagString(res[1]), res[3])  
            if self.gridView:
                if counter % 2 == 1:
                    html += "<div class='gridRow'>%s</div>" % (lastNote + newNote)
                elif counter == len(searchResults) - 1:
                    html += "<div class='gridRow'>%s</div>" % (newNote)
            else:
                html += newNote
            tags = self._addToTags(tags, res[1])
            if counter < 20:
                allText += " " + res[0]
        tags.sort()
        html = html.replace("`", "&#96;").replace("$", "&#36;")
        if not self.hideSidebar:
            infoMap = {
                "Took" :  "<b>%s</b> ms %s" % (str(self.getMiliSecStamp() - stamp) if stamp is not None else "?", "&nbsp;<b style='cursor: pointer' onclick='pycmd(`lastTiming`)'>&#9432;</b>" if printTimingInfo else ""),
                "Found" :  "<b>%s</b> notes" % (len(searchResults) if len(searchResults) > 0 else "<span style='color: red;'>0</span>")
            }
            info = self.buildInfoTable(infoMap, tags, allText) 
            cmd = "setSearchResults(`" + html + "`, `" + info[0].replace("`", "&#96;") + "`, %s);" % json.dumps(info[1])
        else:
            cmd = "setSearchResults(`" + html + "`, ``);"
        cmd += "updateSwitchBtn(%s)" % len(searchResults)
        if editor is None or editor.web is None:
            if self.editor is not None and self.editor.web is not None:
                if logging:
                    log("printing the result html...")
                self.editor.web.eval(cmd)
        else:
            if logging:
                log("printing the result html...")
            editor.web.eval(cmd)


    def buildTagString(self, tags, hover = True, maxLength = -1, maxCount = -1):
        """
        Builds the html for the tags that are displayed at the bottom right of each rendered search result.
        """
        html = ""
        tm = self.getTagMap(tags.split(' '))
        totalLength = sum([len(k) for k,v in tm.items()])
        if maxLength == -1:
            maxLength = 40 if not self.gridView else 30
        if maxCount == -1:
            maxCount = 3 if not self.gridView else 2
        if len(tm) <= maxCount or totalLength < maxLength:
            for t, s in tm.items():
                if len(s) > 0:
                    tagData = " ".join(self.iterateTagmap({t : s}, ""))
                    html += "<div class='tagLbl tooltip' data-tags='%s' data-name='%s' %s onclick='tagClick(this);'><div class='tooltiptext-tag' onclick='event.stopPropagation();'></div>%s</div>" %(tagData, tagData, "onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'" if hover else "", trimIfLongerThan(t, maxLength) + " (+%s)"% len(s))
                else:
                    html += "<div class='tagLbl tooltip' %s data-name='%s' onclick='tagClick(this);'><div class='tooltiptext-tag' onclick='event.stopPropagation();'></div>%s</div>" %("onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'" if hover else "", t, trimIfLongerThan(t, maxLength))
        else:
            tagData = " ".join(self.iterateTagmap(tm, ""))
            html += "<div class='tagLbl' data-tags='%s' onclick='tagClick(this);'>%s</div>" %(tagData, str(len(tm)) + " tags ...")
        
        return html



    def sortByDate(self, mode):
        """
        Rerenders the last search results, but sorted by creation date.
        """
        if self.lastResults is None:
            return
        stamp = self.getMiliSecStamp()
        self.latest = stamp
        sortedByDate = list(sorted(self.lastResults, key=lambda x: x[3]))
        if mode == "desc":
            sortedByDate = list(reversed(sortedByDate))
        self.printSearchResults(sortedByDate, stamp)


    def removeUntagged(self):
        if self.lastResults is None:
            return
        stamp = self.getMiliSecStamp()
        self.latest = stamp
        filtered = []
        for r in self.lastResults:
            if r[1] is None or len(r[1]) == 0:
                continue
            filtered.append(r)
        self.printSearchResults(filtered, stamp)

    def removeTagged(self):
        if self.lastResults is None:
            return
        stamp = self.getMiliSecStamp()
        self.latest = stamp
        filtered = []
        for r in self.lastResults:
            if r[1] is None or len(r[1]) == 0:
                filtered.append(r)
        self.printSearchResults(filtered, stamp)

    def removeUnreviewed(self):
        if self.lastResults is None:
            return
        stamp = self.getMiliSecStamp()
        self.latest = stamp
        filtered = [] 
        nids = []
        for r in self.lastResults:
            nids.append(str(r[3]))
        nidStr =  "(%s)" % ",".join(nids)
        unreviewed = [r[0] for r in mw.col.db.execute("select nid from cards where nid in %s and reps = 0" % nidStr).fetchall()]
        for r in self.lastResults:
            if int(r[3]) not in unreviewed:
                filtered.append(r)
        self.printSearchResults(filtered, stamp)

    def removeReviewed(self):
        if self.lastResults is None:
            return
        stamp = self.getMiliSecStamp()
        self.latest = stamp
        filtered = [] 
        nids = []
        for r in self.lastResults:
            nids.append(str(r[3]))
        nidStr =  "(%s)" % ",".join(nids)
        reviewed = [r[0] for r in mw.col.db.execute("select nid from cards where nid in %s and reps > 0" % nidStr).fetchall()]
        for r in self.lastResults:
            if int(r[3]) not in reviewed:
                filtered.append(r)
        self.printSearchResults(filtered, stamp)

    def _buildEditedInfo(self, timestamp):
        diffInSeconds = time.time() - timestamp
        if diffInSeconds < 60:
            return "Edited just now"
        if diffInSeconds < 120:
            return "Edited 1 minute ago"
        if diffInSeconds < 3600:
            return "Edited %s minutes ago" % int(diffInSeconds / 60)
        return "Edited today"

    def _getTimeDifferenceString(self, nid, now):
        diffInMinutes = (now - int(nid)) / 1000 / 60
        diffInDays = diffInMinutes / 60 / 24

        if diffInDays < 1:
            if diffInMinutes < 2:
                return "Created just now"
            if diffInMinutes < 60:
                return "Created %s minutes ago" % int(diffInMinutes)
            return "Created %s hours ago" % int(diffInMinutes / 60)
            

        if diffInDays >= 1 and diffInDays < 2:
            return "Created yesterday"
        if diffInDays >= 2:
            return "Created %s days ago" % int(diffInDays)
        return ""


    def setSearchInfo(self, text, editor = None):
        if editor is not None:
            editor.web.eval('document.getElementById("searchInfo").innerHTML = `%s`;' % text)
            return
        
        if self.editor is None: 
            return 
        self.editor.web.eval('document.getElementById("searchInfo").innerHTML = `%s`;' % text)

    def buildInfoTable(self, infoMap, tags, allText):
        infoStr = "<table>"
        for key, value in infoMap.items():
            infoStr += "<tr><td>%s</td><td id='info-%s'>%s</td></tr>" %(key, key, value)
        infoStr += "</table><div class='searchInfoTagSep'><span class='tag-symbol'>&#9750;</span>&nbsp;Tags:</div><div id='tagContainer' style='max-height: 180px; overflow-y: auto;'>"
        tagStr = ""
        if len(tags) == 0:
            infoStr += "No tags in the results."
            infoMap["Tags"] = "No tags in the results."
        else:
            for key, value in self.getTagMap(tags).items():
                if len(value)  == 0:
                    tagStr += "<span class='searchInfoTagLbl' data-name='%s' onclick='tagClick(this);'>%s</span>" % (key,trimIfLongerThan(key, 19))
                else:
                    tagData = " ".join(self.iterateTagmap({key : value}, ""))
                    tagStr += "<span class='searchInfoTagLbl' data-tags='%s' onclick='tagClick(this);'>%s&nbsp; %s</span>" % (tagData, trimIfLongerThan(key,12), "(+%s)"% len(value))

            infoStr += tagStr
            infoMap["Tags"] = tagStr

        infoStr += "</div><div class='searchInfoTagSep bottom' >Keywords:</div><div id='keywordContainer'>"
        mostCommonWords = self._mostCommonWords(allText)
        infoStr += mostCommonWords + "</div>"
        infoMap["Keywords"] = mostCommonWords
        return (infoStr, infoMap)

    def _cleanFieldSeparators(self, text):
        text = self.SEP_RE.sub("\u001f", text)
        if text.endswith("\u001f"):
            text = text[:-1]
        text = text.replace("\u001f", "<span class='fldSep'>|</span>")
        return text

    def tryHideImageOcclusion(self, text):
        """
        Image occlusion cards take up too much space, so we try to hide all images except for the first.
        """
        if not text.count("<img ") > 1:
            return text
        text = self.IO_REPLACE.sub("(IO - image hidden)", text)
        return text


    def _mostCommonWords(self, text):
        if len(text) == 0:
            return "No keywords for empty result."
        text = clean(text, self.stopwords)
        counts = {}
        for token in text.split():
            if token == "" or len(token) == 1 or self.SOUND_TAG.match(token):
                continue
            if token.lower() in counts:
                counts[token.lower()][1] += 1
            else:
                counts[token.lower()] = [token, 1]
        sortedCounts = sorted(counts.items(), key=lambda kv: kv[1][1], reverse=True)
        html = ""
        for entry in sortedCounts[:15]:
            html += "<a class='keyword' href='#' onclick='event.preventDefault(); searchFor($(this).text())'>%s</a>, " % entry[1][0]
        return html[:-2]

    def print_timeline_info(self, context_html, db_list):
        html = ""
        epochTime = int(time.time() * 1000)
        timeDiffString = ""
        newNote = ""
        lastNote = "" 
        nids = [r[3] for r in db_list]
        if self.showRetentionScores:
            retsByNid = getRetentions(nids)
        ret = 0
        for counter, res in enumerate(db_list):
            try:
                timeDiffString = self._getTimeDifferenceString(res[3], epochTime)
            except:
                timeDiffString = "Could not determine creation date"
            ret = retsByNid[int(res[3])] if self.showRetentionScores and int(res[3]) in retsByNid else None

            if ret is not None:
                retMark = "background: %s; color: black;" % (self._retToColor(ret)) 
                if str(res[3]) in self.edited:
                    retMark += "max-width: 20px;"
                retInfo = """<div class='retMark' style='%s'>%s</div>
                             """ % (retMark, int(ret))
            else:
                retInfo = ""

            lastNote = newNote
            text = self._cleanFieldSeparators(res[0]).replace("\\", "\\\\").replace("`", "\\`")
            text = self.tryHideImageOcclusion(text)
            newNote = self.noteTemplateSimple % ( counter + 1,
                        "&nbsp;&#128336; " + timeDiffString,
                        "" if str(res[3]) not in self.edited else "&nbsp;&#128336; " + self._buildEditedInfo(self.edited[str(res[3])]),
                        retInfo, res[3],res[3],res[3],res[3],
                        text, 
                        self.buildTagString(res[1], False, maxLength = 25, maxCount = 2), res[3]) 
           
            html += newNote
        
        if len(html) == 0:
            html = "%s <div style='vertical-align:center; text-align: center; line-height: 200px;'>No notes added on that day.</div>" % (context_html)
        else:
            html = """
                %s
                <div style='overflow-y: auto; height: 190px; margin: 10px 0 5px 0; padding-left: 4px; padding-right: 8px;'>%s</div> 
            """ % (context_html, html)
        self.editor.web.eval("document.getElementById('cal-info').innerHTML = `%s`;" % html)

   
    def showInModal(self, text):
        cmd = "$('#a-modal').show(); document.getElementById('modalText').innerHTML = `%s`;" % text
        
        if self.editor is not None:
            self.editor.web.eval(cmd)
        
    def _loadPlotJsIfNotLoaded(self):
        if not self.plotjsLoaded:
            dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/output.py", "")
            with open(dir + "/plot.js") as f:
                plotjs = f.read()
            self.editor.web.eval(plotjs)
            self.plotjsLoaded = True


    def showTrueRetStatsForTag(self, trueRetOverTime):
        
        if trueRetOverTime is None or len(trueRetOverTime) < 2:
            cmd = "$('#trueRetGraph,#trueRetGraphLbl').hide();"
        else:
            self._loadPlotJsIfNotLoaded()
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
            rawData = [[i,t] for i, t in enumerate(trueRetOverTime)]
            cmd = "$.plot($('#trueRetGraph'), [ %s ],  %s);" % (json.dumps(rawData), options)
        if self.editor is not None:
            cmd += "$('.t-inverted').css('margin-bottom', '-' + ($('.t-inverted').first().height() + 23) + 'px');"
            self.editor.web.eval(cmd)

    def showStats(self, text, reviewPlotData, ivlPlotData, timePlotData):
        
        self._loadPlotJsIfNotLoaded()
        
        cmd = "$('#a-modal').show(); document.getElementById('modalText').innerHTML = `%s`; document.getElementById('modalText').scrollTop = 0; " % (text)
        c = 0
        for k,v in reviewPlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: { 
                            lines: { show: true, fillColor: "#2496dc" }, 
                            points: { show: true, fillColor: "#2496dc" } 
                    }, 
                    label: "Ease", 
                    yaxis: { max: 5, min: 0, ticks: [[0, ''], [1, 'Failed'], [2, 'Hard'], [3, 'Good'], [4, 'Easy']],    
                                tickFormatter: function (v, axis) {
                                if (v == 1) {
                                    $(this).css("color", "red");
                                }
                                return v;
                                }
                    } , 
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"] 
                    }
    
                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)
        for k,v in ivlPlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: { 
                            lines: { show: true, fillColor: "#2496dc" }, 
                            points: { show: true, fillColor: "#2496dc" } 
                    }, 
                    label: "Interval", 
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"] 
                    }
    
                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)            

        for k,v in timePlotData.items():
            if v is not None and len(v) > 0:
                c += 1
                rawData = [[r[0], r[1]] for r in v]
                xlabels = [[r[0], r[2]] for r in v]
                if len(xlabels) > 30:
                    xlabels = xlabels[0::2]
                options = """
                    {  series: { 
                            lines: { show: true, fillColor: "#2496dc" }, 
                            points: { show: true, fillColor: "#2496dc" } 
                    }, 
                    label: "Answer Time", 
                    xaxis: { ticks : %s },
                    colors: ["#2496dc"] 
                    }
    
                """ % json.dumps(xlabels)
            cmd += "$.plot($('#graph-%s'), [ %s ],  %s);" % (c, json.dumps(rawData), options)    

        if self.editor is not None:
            self.editor.web.eval(cmd)

    def hideModal(self):
        if self.editor is not None:
            self.editor.web.eval("$('#a-modal').hide();")

    def _addToTags(self, tags, tagStr):
        if tagStr == "":
            return tags
        for tag in tagStr.split(" "):
            if tag == "":
                continue
            if tag in tags:
                continue
            tags.append(tag)
        return tags

    def printTagHierarchy(self, tags):
        cmd = """document.getElementById('modalText').innerHTML = `%s`; 
         $('.tag-list-item').click(function(e) {
		e.stopPropagation();
        let icn = $(this).find('.tag-btn').first();
        let text = icn.text();
        if (text.endsWith(']')) {
            if (text.endsWith('[+]'))
                icn.text(text.substring(0, text.length - 3) + '[-]');
            else
                icn.text(text.substring(0, text.length - 3) + '[+]');
        }
        $(this).children('ul').toggle();
         });
    
        """ % self.buildTagHierarchy(tags)
        self.editor.web.eval(cmd)

    def buildTagHierarchy(self, tags):
        tmap = self.getTagMap(tags)

        def iterateMap(tmap, prefix, start=False):
            if start:
                html = "<ul class='tag-list outer'>"
            else:
                html = "<ul class='tag-list'>"
            for key, value in tmap.items():
                full = prefix + "::" + key if prefix else key
                html += "<li class='tag-list-item'><span class='tag-btn'>%s %s</span><div class='tag-add' data-name=\"%s\" onclick='event.stopPropagation(); tagClick(this)'>+</div>%s</li>" % (trimIfLongerThan(key, 25), "[-]" if value else "" ,  deleteChars(full, ["'", '"', "\n", "\r\n", "\t", "\\"]), iterateMap(value, full)) 
            html += "</ul>"
            return html

        html = iterateMap(tmap, "", True)
        return html

    def getTagMap(self, tags):
        tmap = {}
        for name in tags:
            tmap = self._addToTaglist(tmap, name)
        return tmap

    def _addToTaglist(self, tmap, name):
        names = [s for s in name.split("::") if s != ""]
        for c, d in enumerate(names):
            found = tmap
            for i in range(c):
                found = found.setdefault(names[i], {})
            if not d in found:
                found.update({d : {}}) 
        return tmap    

    def iterateTagmap(self, tmap, prefix):
        if len(tmap) == 0:
            return []
        res = []
        if prefix:
            prefix = prefix + "::"
        for key, value in tmap.items():
            if type(value) is dict:
                if len(value) > 0:
                    res.append(prefix + key)
                    res +=  self.iterateTagmap(value, prefix + key)
                else:
                    res.append(prefix + key)
        return res
    
    def updateSingle(self, note):
        """
        Used after note has been edited. The edited note should be rerendered.
        To keep things simple, only note text and tags are replaced. 
        """
        if self.editor is None or self.editor.web is None:
            return
        tags = note[2]
        tagStr =  self.buildTagString(tags)  
        nid = note[0]
        text = self._cleanFieldSeparators(note[1])
        #find rendered note and replace text and tags
        self.editor.web.eval("""
            document.getElementById('%s').innerHTML = `%s`; 
            document.getElementById('tags-%s').innerHTML = `%s`;
        """ % (nid, text, nid, tagStr))

        self.editor.web.eval("$('#cW-%s').find('.rankingLblAddInfo').hide();" % nid)
        self.editor.web.eval("fixRetMarkWidth(document.getElementById('cW-%s'));" % nid)
        self.editor.web.eval("$('#cW-%s .editedStamp').html(`&nbsp;&#128336; Edited just now`).show();" % nid)

    def _markHighlights(self, text, querySet):
     
        currentWord = ""
        currentWordNormalized = ""
        textMarked = ""
        lastIsMarked = False
        for char in text:
            if self.wordToken.match(char):
                currentWordNormalized += asciiFoldChar(char).lower()
                if isChineseChar(char) and str(char) in querySet:
                    currentWord += "<mark>%s</mark>" % char
                else:
                    currentWord += char
                
            else:
                #we have reached a word boundary
                #check if word is empty
                if currentWord == "":
                    textMarked += char
                else:
                    #if the word before the word boundary is in the query, we want to highlight it
                    if currentWordNormalized in querySet:
                        #we check if the word before has been marked too, if so, we want to enclose both, the current word and 
                        # the word before in the same <mark></mark> tag (looks better)
                        if lastIsMarked:
                            textMarked = textMarked[0: textMarked.rfind("</mark>")] + textMarked[textMarked.rfind("</mark>") + 7 :]
                            textMarked += currentWord + "</mark>" + char
                        else:
                            textMarked += "<mark>" + currentWord + "</mark>" + char
                        lastIsMarked = True
                    #if the word is not in the query, we simply append it unhighlighted
                    else:
                        textMarked += currentWord + char
                        lastIsMarked = False
                    currentWord = ""
                    currentWordNormalized = ""
        if currentWord != "":
            if currentWordNormalized in querySet and currentWord != "mark":
                textMarked += "<mark>" + currentWord + "</mark>"
            else:
                textMarked += "%s" % currentWord
        
        return textMarked




    @staticmethod
    def _retToColor(retention):
        if retention < (100 / 7.0):
            return "#ff0000"
        if retention < (100 / 7.0) * 2:
            return "#ff4c00"
        if retention < (100 / 7.0) * 3:
            return "#ff9900"
        if retention < (100 / 7.0) * 4:
            return "#ffe500"
        if retention < (100 / 7.0) * 5:
            return "#cbff00"
        if retention < (100 / 7.0) * 6:
            return "#7fff00"
        return "#32ff00"


    def getMiliSecStamp(self):
        return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)