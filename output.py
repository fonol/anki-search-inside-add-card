import re
from datetime import datetime
from aqt.utils import showInfo
from .textutils import clean

class Output:

    def __init__(self):
        self.editor = None
        self.SEP_RE = re.compile(r'(\u001f){2,}')
        self.latest = -1
        self.stopwords = []


    def printSearchResults(self, searchResults, stamp, editor=None):
        """
        This is the html that gets rendered in the search results div.
        Args:
        searchResults - a list of tuples, see SearchIndex.search()
        """
        if stamp is not None:
            if stamp != self.latest:
                return
        html = ""
        allText = ""
        tags = []
        for counter, res in enumerate(searchResults):
            #todo: move in class
            html += """<div class='cardWrapper'  style='padding: 9px; margin-bottom: 10px; position: relative;'> 
                            <div id='cW-%s' class='rankingLbl'>%s</div> 
                            <div id='btnBar-%s' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                                <div class='srchLbl' onclick='searchCard(this)'>Search</div> 
                                <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div> 
                                <div id='rem-%s'  class='remLbl' onclick='$("#cW-%s").parents().first().remove(); updatePinned();'><span>&times;</span></div> 
                            </div>
                            <div class='cardR' onclick='expandCard(this);' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div> 
                            <div style='position: absolute; bottom: 0px; right: 0px; z-index:9999'>%s</div>     
                        </div>
                        """ %(res[3], counter + 1, res[3],res[3],res[3], res[3], res[3], res[3], res[3], res[3], res[3], self.SEP_RE.sub("\u001f", res[0]).replace("\u001f", "<span class='fldSep'>|</span>"), self.buildTagString(res[1]))  
            tags = self._addToTags(tags, res[1])
            if counter < 20:
                allText += " " + res[0]
        tags.sort()
        infoMap = {
            "Took" :  "<b>%s</b> ms" % str(self.getMiliSecStamp() - stamp) if stamp is not None else "?",
            "Found" :  "<b>%s</b> notes" % str(len(searchResults))
        }
        infoStr = self.buildInfoTable(infoMap, tags, allText) 
        
        cmd = "setSearchResults(`" + html + "`, `" + infoStr + "`);"
        if editor is None:
            self.editor.web.eval(cmd)
        else:
            editor.web.eval(cmd)

    def buildTagString(self, tags):
        """
        Builds the html for the tags that are displayed at the bottom right of each rendered search result.
        """
        html = ""
        for t in tags.split(' '):
            if len(t) > 0:
                html += "<div class='tagLbl' data-name='%s' onclick='tagClick(this);'>%s</div>" %(t, t)
        return html

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
            infoStr += "<tr><td>%s</td><td>%s</td></tr>" %(key, value)
        infoStr += "</table><br/><div class='searchInfoTagSep'>Tags:</div><div style='max-height: 200px; overflow-y: auto;'>"
        if len(tags) == 0:
            infoStr += "No tags in the results."
        for tag in tags:
            infoStr += "<span class='searchInfoTagLbl' data-name='%s' onclick='tagClick(this);'>%s</span>" % (tag,tag)
        infoStr += "</div><br style='clear:both'/><div class='searchInfoTagSep'>Keywords:</div>"
        infoStr += self._mostCommonWords(allText)
        return infoStr


    def _mostCommonWords(self, text):
        text = clean(text, self.stopwords)
        counts = {}
        for token in text.split():
            if token == "":
                continue
            if token.lower() in counts:
                counts[token.lower()][1] += 1
            else:
                counts[token.lower()] = [token, 1]
        sortedCounts = sorted(counts.items(), key=lambda kv: kv[1][1], reverse=True)
        html = ""
        for entry in sortedCounts[:15]:
            html += "<i>%s</i>, " % entry[1][0]
        return html[:-2]

   
       

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

    def getMiliSecStamp(self):
        return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)