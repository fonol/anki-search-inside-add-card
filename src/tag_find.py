# anki-search-inside-add-card
# Copyright (C) 2019 - 2021 Tom Z.

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


from aqt import *
import utility.text
from .stats import getAvgTrueRetention, getTrueRetentionOverTime, retention_stats_for_tag
from .output import UI
from .notes import find_by_tag
from .models import IndexNote
import utility.misc

def findBySameTag(tagStr, limit, decks, pinned):
   
    query = "where "
    for t in tagStr.split(" "):
        if len(t) > 0:
            t = t.replace("'", "''")
            if len(query) > 6:
                query += " or "
            query += "lower(tags) like '% " + t + " %' or lower(tags) like '% " + t + "::%' or lower(tags) like '%::" + t + " %' or lower(tags) like '% " + t + "::%' or lower(tags) like '" + t + " %' or lower(tags) like '%::" + t + "::%'"
  
    deckQ = ""
    if decks is not None and len(decks) > 0 and not "-1" in decks:
        deckQ =  "(%s)" % ",".join(decks)

    if deckQ:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid %s and did in %s" %(query, deckQ))
    else:
        res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid %s" %(query))

    rList = []
    rList.extend(find_by_tag(tagStr))

    for r in res:
        #pinned items should not appear in the results
        if not str(r[0]) in pinned:
            rList.append(IndexNote((r[0], r[1], r[2], r[3], r[1], -1, r[4], "")))

    return { "result" : rList[:limit]}

def display_tag_info(editor, stamp, tag, index):
    synonyms = index.synonyms

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
    searchRes               = findBySameTag(tag, 30000, [], [])
    tagsfound               = _extract_tags(searchRes["result"], tag)

    if len(tagsfound) <= 2 and "::" in tag:
        for s in tag.split("::"):
            res = findBySameTag(s, 30000, [], [])
            tagsfound = _extract_tags(res["result"], tag)
            if len(tagsfound) > 0:
                break

    sortedCounts            = sorted(tagsfound.items(), key=lambda kv: kv[1], reverse=True)
    time_stamp_for_graph    = utility.text.get_stamp()
    window                  = mw.app.activeWindow()
    should_hide_left_side   = window is not None and window.width() < 1000
    html                    = ""

    if should_hide_left_side:
        html = """
                <span id='siac-tag-graph-lbl-%s'>Retention for this Topic / Reviews</span>
                <div id="siac-tag-graph-%s" style='width: 230px; height: 130px; margin-right: auto; margin-left: auto; margin-bottom: 15px;'></div>
                <table class='w-100'>
                    <tr><td style='text-align: left;'>Retention</td><td style='text-align: right;'><b>%s</b></td></tr>
                    <tr><td style='text-align: left;'>Notes</td><td style='text-align: right;'><b>%s</b></td></tr>
                    <tr><td style='text-align: left'>Related</td><td>%s</td></tr></table>
        """ 
    else:
        html = """
            <div class='w-100 flex-row'>
            <div style='flex: 1 1; flex-basis: 50%%; padding: 5px; max-width: 50%%;'>
                    <span>Newest for <b>%s</b></span>
                    <div class='siac-tag-info-box-left' style='%s' id='siac-tag-info-box-left-%s'>
                        %s
                    </div>
            </div>
            <div style='flex: 1 1; flex-basis: 50%%;'>
                <span id='siac-tag-graph-lbl-%s'>Retention for this Topic / Reviews</span>
                <div id="siac-tag-graph-%s" style='width: 230px; height: 130px; margin-right: auto; margin-left: auto; margin-bottom: 15px;'></div>
                <table class='w-100'>
                    <tr><td style='text-align: left;'>Retention</td><td style='text-align: right;'><b>%s</b></td></tr>
                    <tr><td style='text-align: left;'>Notes</td><td style='text-align: right;'><b>%s</b></td></tr>
                    <tr><td style='text-align: left'>Related</td><td>%s</td></tr></table>
            </div>
            </div>
        """ 
    tags = ""
   
    if len(sortedCounts) < 3:
        starter = set([t[0] for t in sortedCounts])
        for t in sortedCounts:
            res = findBySameTag(t[0], 30000, [], [])
            for r in res["result"]:
                spl = r.tags.split()
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
        if should_hide_left_side:
            tags += "<div data-stamp='siac-tg-%s' class='tagLbl' style='margin-bottom: 4px;' data-name='%s' onclick='tagClick(this); event.stopPropagation();'>%s</div>" % (utility.text.get_stamp(), k[0], utility.text.trim_if_longer_than(k[0], 40))
        else:
            tags += "<div data-stamp='siac-tg-%s' class='tagLbl' style='margin-bottom: 4px;' data-name='%s' onmouseenter='tagMouseEnter(this)' onclick='tagClick(this); event.stopPropagation();' onmouseleave='tagMouseLeave(this)'>%s</div>" % (utility.text.get_stamp(), k[0], utility.text.trim_if_longer_than(k[0], 40))
        total_length += len(utility.text.trim_if_longer_than(k[0], 40))
        if total_length > 120:
            break

    if len(tags) == 0:
        tags = "Could not find any related tags. Related tags are determined by looking for tags that appear on the same notes as the given tag."

    nids = [r.id for r in searchRes["result"]]
    tret = getAvgTrueRetention(nids)

    if tret is not None:
        color   = utility.misc._retToColor(tret)    
        tret    = "<span style='background: %s; color: black;'>&nbsp;%s&nbsp;</span>" % (color, tret)

    if not should_hide_left_side:
        sorted_db_list              = sorted(searchRes["result"], key=lambda x: x.id, reverse=True)
        note_html                   = UI.get_result_html_simple(sorted_db_list[:100])
        enlarge_note_area_height    = "max-height: 320px" if total_length > 120 and tret is not None else ""
        tag_name                    = tag

        if " " in tag_name:
            base                    = tag_name.split()[0]
            tag_name                = utility.text.trim_if_longer_than(base, 25) + " (+%s)" % len(tag_name.split()[1:])
        else:
            tag_name                = utility.text.trim_if_longer_than(tag_name, 28)

        html                        = html % (tag_name, enlarge_note_area_height, stamp, note_html, time_stamp_for_graph, time_stamp_for_graph, tret if tret is not None else "Not enough Reviews", len(searchRes["result"]), tags)

    else:
        html    = html % (time_stamp_for_graph, time_stamp_for_graph, tret if tret is not None else "Not enough Reviews", len(searchRes["result"]), tags)

    ret_data    = getTrueRetentionOverTime(nids)
    graph_js    = retention_stats_for_tag(ret_data, "siac-tag-graph-" + time_stamp_for_graph, "siac-tag-graph-lbl-" + time_stamp_for_graph)
   
    id_for_box  = "siac-tag-info-box-" + stamp
    params      = {      "stamp": stamp,
                         "id" : id_for_box, 
                         "html" : html,
                         "graph_js": graph_js,
                         "should_be_small": "siac-tag-info-box-small" if should_hide_left_side else ""
                     }
    # we have to adjust the 'top' css property if the element has the class '.siac-tag-info-box-inverted'
    # we can only do this after the content has been rendered since we have to know the actual height.
    editor.web.eval(""" $(`<div class='siac-tag-info-box {should_be_small}' id='{id}' data-stamp='{stamp}' onclick='tagInfoBoxClicked(this)' onmouseleave='tagMouseLeave(this)'></div>`).insertAfter('#outerWr');
                        $('#{id}').html(`{html}`);
                       {graph_js} 
                        showTagInfo(document.querySelectorAll(".tagLbl[data-stamp='{stamp}']")[0]);

                     """.format(**params))
    return nids



def _extract_tags(db_list, tag_searched):
    tagsfound = {}
    for r in db_list:
        spl = r.tags.split()
        for s in spl:
            if s == tag_searched or s in tag_searched.split():
                continue
            if s in tagsfound:
                tagsfound[s] += 1
            else:
                tagsfound[s] = 1
    return tagsfound


            
                
