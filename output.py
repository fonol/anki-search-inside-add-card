import re
import json
from datetime import datetime
from aqt.utils import showInfo
from .textutils import clean, trimIfLongerThan, deleteChars

class Output:

    def __init__(self):
        self.editor = None
        self.SEP_RE = re.compile(r'(\u001f){2,}|(\u001f[\s\r\n]+\u001f)')
        self.SEP_END = re.compile(r'</div>\u001f$')
        self.SOUND_TAG = re.compile(r'sound[a-zA-Z0-9]*mp')
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
                                <div class='editLbl' onclick='edit(%s)'>Edit</div> 
                               <div class='srchLbl' onclick='searchCard(this)'>Search</div> 
                                <div id='pin-%s' class='pinLbl unselected' onclick='pinCard(this, %s)'><span>&#128204;</span></div> 
                                <div id='rem-%s' class='remLbl' onclick='$("#cW-%s").parents().first().remove(); updatePinned();'><span>&times;</span></div> 
                            </div>
                            <div class='cardR' onclick='expandCard(this);' onmouseenter='cardMouseEnter(this, %s)' onmouseleave='cardMouseLeave(this, %s)' id='%s' data-nid='%s'>%s</div> 
                            <div style='position: absolute; bottom: 0px; right: 0px; z-index:9999'>%s</div>     
                        </div>
                        """ %(res[3], counter + 1, res[3],res[3],res[3],res[3], res[3], res[3], res[3], res[3], res[3], res[3], self._cleanFieldSeparators(res[0]).replace("\\", "\\\\"), self.buildTagString(res[1]))  
            tags = self._addToTags(tags, res[1])
            if counter < 20:
                allText += " " + res[0]
        tags.sort()
        infoMap = {
            "Took" :  "<b>%s</b> ms" % str(self.getMiliSecStamp() - stamp) if stamp is not None else "?",
            "Found" :  "<b>%s</b> notes" % str(len(searchResults))
        }
        infoStr = self.buildInfoTable(infoMap, tags, allText) 
        cmd = "setSearchResults(`" + html.replace("`", "\\`") + "`, `" + infoStr.replace("`", "\\`") + "`);"
        if editor is None:
            if self.editor is not None and self.editor.web is not None:
                self.editor.web.eval(cmd)
        else:
            editor.web.eval(cmd)

    def buildTagString(self, tags):
        """
        Builds the html for the tags that are displayed at the bottom right of each rendered search result.
        """
        html = ""
        tm = self.getTagMap(tags.split(' '))
        totalLength = sum([len(k) for k,v in tm.items()])
        if len(tm) <= 3 or totalLength < 50:
            for t, s in tm.items():
                if len(s) > 0:
                    tagData = " ".join(self.iterateTagmap({t : s}, ""))
                    html += "<div class='tagLbl' data-tags='%s' onclick='tagClick(this);'>%s</div>" %(tagData, trimIfLongerThan(t, 40) + " (+%s)"% len(s))
                else:
                    html += "<div class='tagLbl' data-name='%s' onclick='tagClick(this);'>%s</div>" %(t, trimIfLongerThan(t, 40))
        else:
            tagData = " ".join(self.iterateTagmap(tm, ""))
            html += "<div class='tagLbl' data-tags='%s' onclick='tagClick(this);'>%s</div>" %(tagData, str(len(tm)) + " tags ...")
        
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
        infoStr += "</table><br/><div class='searchInfoTagSep'><span class='tag-symbol'>&#9750;</span>&nbsp;Tags:</div><div style='max-height: 200px; overflow-y: auto;'>"
        if len(tags) == 0:
            infoStr += "No tags in the results."
        for key, value in self.getTagMap(tags).items():
            if len(value)  == 0:
                infoStr += "<span class='searchInfoTagLbl' data-name='%s' onclick='tagClick(this);'>%s</span>" % (key,trimIfLongerThan(key, 19))
            else:
                tagData = " ".join(self.iterateTagmap({key : value}, ""))
                infoStr += "<span class='searchInfoTagLbl' data-tags='%s' onclick='tagClick(this);'>%s&nbsp; %s</span>" % (tagData, trimIfLongerThan(key,12), "(+%s)"% len(value))

        infoStr += "</div><br style='clear:both'/><div><div class='searchInfoTagSep bottom'>Keywords:</div>"
        infoStr += self._mostCommonWords(allText) + "</div>"
        return infoStr

    def _cleanFieldSeparators(self, text):
        text = self.SEP_RE.sub("\u001f", text)
        #text = self.SEP_END.sub("\u001f", text)
        if text.endswith("\u001f"):
            text = text[:-1]
        text = text.replace("\u001f", "<span class='fldSep'>|</span>")
        return text

    def _mostCommonWords(self, text):
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
            html += "<a href='#' onclick='event.preventDefault(); searchFor($(this).text())'>%s</a>, " % entry[1][0]
        return html[:-2]

   
    def showInModal(self, text):
        cmd = "$('#a-modal').show(); document.getElementById('modalText').innerHTML = `%s`;" % text
        if self.editor is not None:
            self.editor.web.eval(cmd)


    def hideModal(self):
        if self.editor is not None:
            self.editor.web.eval("toggleModalLoader(false);$('#a-modal').hide();")

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


    

    def getMiliSecStamp(self):
        return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)