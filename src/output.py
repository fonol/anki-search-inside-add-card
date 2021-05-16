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

import re
import time
import json
import os
import math
import aqt
from datetime import datetime
from aqt import mw
from aqt.utils import tooltip
import typing
from typing import Tuple, List, Optional, Dict, Callable

from .notes import get_pdf_info
from .special_searches import get_suspended
from .web.sidebar import Sidebar
from .config import get_config_value_or_default
from .web.templating import filled_template
from .web.note_templates import *
from .models import SiacNote, IndexNote
from .internals import HTML, JS
from .stats import getRetentions
from .state import get_index, set_deck_map

import utility.tags
import utility.text
import utility.misc
import state

try:
    utility.misc.load_rust_lib()
    from siacrs import *
    state.rust_lib = True
except:
    state.rust_lib = False



class UI:
    """
        Component which is mainly responsible for rendering search results.
    """
    #
    # Components
    #
    _editor                     = None
    sidebar                     = Sidebar()

    # Todo: move to text utils
    EXCLUDE_KEYWORDS            = re.compile(r'(?:sound|mp3|c[0-9]+)')

    #
    # State / Settings
    #
    latest                      = -1
    gridView                    = False
    plotjsLoaded                = False
    showRetentionScores         = True
    lastResults                 = None
    hideSidebar                 = False
    uiVisible                   = True
    frozen                      = False
    highlighting                = get_config_value_or_default("highlighting", True)
    show_clozes                 = not get_config_value_or_default("results.hide_cloze_brackets", False)

    fields_to_hide_in_results   = {}
    remove_divs                 = False

    # saved to display the same time taken when clicking on a page other than 1
    last_took                   = None
    last_had_timing_info        = False
    #determines the zoom factor of rendered notes
    scale                       = 1.0
    #cache previous calls
    previous_calls              = []


    @classmethod
    def set_editor(cls, editor: aqt.editor.Editor):
        """
            An editor instance is needed to communicate to the web view, so the ui should always hold one.
            All included children should have a ref to the instance too.
        """
        cls._editor = editor
        cls.sidebar.set_editor(editor)

    @classmethod
    def show_page(cls, editor: aqt.editor.Editor, page: int):
        """
            Results are paginated, this will display the results for the given page.
        """
        if cls.lastResults is not None:
            header = cls.previous_calls[-1][0]
            cls.print_search_results(header, cls.lastResults, None, editor, cls.last_had_timing_info, page, query_set = cls.last_query_set)

    @classmethod
    def try_rerender_last(cls):
        if cls.previous_calls is not None and len(cls.previous_calls) > 0:
            c = cls.previous_calls[-1]
            cls.print_search_results(*c, is_cached=True)

    @classmethod
    def print_search_results(cls, header, notes, stamp, editor=None, timing_info=False, page=1, query_set=None, is_cached=False):
        """
        This is the html that gets rendered in the search results div.
        This will always print the first page.
        """

        if stamp is not None:
            if stamp != cls.latest:
                return

        # if we were on e.g. on page 2 which contains exactly one note (nr. 51 of 51 search results), and deleted that note, the
        # refresh call would still be to rerender page 2 with the updated search results,
        # but page 2 would not exist anymore, so we have to check for that:
        if (page - 1) * 50 > len(notes):
            page = page - 1

        # if this is true, avoid scrolling to the top of the search results again
        is_rerender                 = False

        if not is_cached and len(notes) > 0:

            # roughly check if current call equals the last one, to set is_rerender to True
            if len(cls.previous_calls) > 0:
                nids = [n.id for n in cls.previous_calls[-1][1][:30]]
                if query_set == cls.previous_calls[-1][6] and page == cls.previous_calls[-1][5] and nids == [n.id for n in notes[:30]]:
                    is_rerender = True

            # cache all calls to be able to repeat them
            cls.previous_calls.append([header, notes, None, editor, timing_info, page, query_set])

            if len(cls.previous_calls) > 11:
                cls.previous_calls.pop(0)

        html                        = ""
        allText                     = ""
        tags                        = []
        epochTime                   = int(time.time() * 1000)
        timeDiffString              = ""
        newNote                     = ""
        ret                         = 0
        cls.last_had_timing_info   = timing_info

        if notes is not None and len(notes) > 0:
            cls.lastResults        = notes
            cls.last_query_set     = query_set


        meta_notes_cnt              = 0
        while meta_notes_cnt < len(notes) and notes[meta_notes_cnt].note_type == "user" and notes[meta_notes_cnt].is_meta_note():
            meta_notes_cnt          += 1
        searchResults               = notes[(page- 1) * 50 + min(page - 1, 1) * meta_notes_cnt: page * 50 + meta_notes_cnt]
        nids                        = [r.id for r in searchResults]

        if cls.showRetentionScores:
            retsByNid               = getRetentions(nids)

        # various time stamps to collect information about rendering performance
        start                       = time.time()
        highlight_start             = None
        build_user_note_start       = None

        highlight_total             = 0.0
        build_user_note_total       = 0.0

        remaining_to_highlight      = {}
        highlight_boundary          = 15 if cls.gridView else 10

        # for better performance, collect all notes that are .pdfs, and
        # query their reading progress after they have been rendered
        pdfs                        = []

        check_for_suspended         = []

        meta_card_counter           = 0
        for counter, res in enumerate(searchResults):
            nid     = res.id
            counter += (page - 1)* 50
            try:
                timeDiffString = cls._get_time_diff_lbl(nid, epochTime)
            except:
                timeDiffString = "Could not determine creation date"
            ret = retsByNid[int(nid)] if cls.showRetentionScores and int(nid) in retsByNid else None

            if ret is not None:
                retMark = "border-color: %s;" % (utility.misc._retToColor(ret))
                retInfo = """<div class='retMark' style='%s'>Pass Rate: %s</div>""" % (retMark, int(ret))
            else:
                retInfo = ""

            # non-anki notes should be displayed differently, we distinguish between title, text and source here
            # confusing: 'source' on notes from the index means the original note content (without stopwords removed etc.),
            # on SiacNotes, it means the source field.
            build_user_note_start   = time.time()
            text                    = res.get_content()
            progress                = ""
            pdf_class               = ""
            if res.note_type == "user":
                icon = "book"
                if res.is_pdf():
                    pdfs.append(nid)
                    p_html              = "<div class='siac-prog-sq'></div>" * 10
                    progress            = f"<div id='ptmp-{nid}' class='siac-prog-tmp'>{p_html} <span>&nbsp;0 / ?</span></div><div style='display: inline-block;' id='siac-ex-tmp-{nid}'></div>"
                    pdf_class           = "pdf"
                elif int(res.id) < 0:
                    # meta card
                    pdf_class           = "meta"

                elif res.is_yt():
                    icon = "film"
                elif res.is_md():
                    icon = "book"
                elif res.is_file():
                    icon = "external-link"
            elif res.note_type == "index" and res.did and res.did > 0:
                check_for_suspended.append(res.id)

            build_user_note_total   += time.time() - build_user_note_start

            # hide fields that should not be shown
            if str(res.mid) in cls.fields_to_hide_in_results:
                text                = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in cls.fields_to_hide_in_results[str(res.mid)]])

            # remove double fields separators
            text                    = utility.text.clean_field_separators(text).replace("\\", "\\\\")

            # try to remove image occlusion fields
            text                    = utility.text.try_hide_image_occlusion(text)

            # if set in config, try to remove cloze brackets
            if not cls.show_clozes:
                text                = utility.text.hide_cloze_brackets(text)

            # try to put fields that consist of a single image in their own line
            text                    = utility.text.newline_before_images(text)

            #remove <div> tags if set in config
            if cls.remove_divs and res.note_type != "user":
                text                = utility.text.remove_divs(text, " ")

            #highlight
            highlight_start         = time.time()
            if query_set is not None:
                if counter - (page -1) * 50 < highlight_boundary:
                    text            = utility.text.mark_highlights(text, query_set)
                else:
                    remaining_to_highlight[nid] = ""
            highlight_total += time.time() - highlight_start

            if query_set is not None and counter - (page -1) * 50 >= highlight_boundary:
                remaining_to_highlight[nid] = text

            gridclass = "grid" if cls.gridView else ""

            if cls.scale != 1.0:
                gridclass = ' '.join([gridclass, "siac-sc-%s" % str(cls.scale).replace(".", "-")])

            # use either the template for addon's notes or the normal
            if res.note_type == "user":

                template    = NOTE_TMPL_SIAC
                if res.is_meta_note():
                    template            = NOTE_TMPL_META
                    meta_card_counter   += 1
                    text                = f"<b>{res.get_title()}</b><hr class='mb-5 siac-note-hr'>{text}"

                newNote     = template.format(
                    grid_class  = gridclass,
                    counter     = counter + 1 - meta_card_counter,
                    nid         = nid,
                    text        = text,
                    title       = res.get_title(),
                    tags        = utility.tags.build_tag_string(res.tags, cls.gridView),
                    progress    = progress,
                    icon        = icon,
                    pdf_class   = pdf_class,
                    ret         = retInfo)

            else:
                newNote = NOTE_TMPL.format(
                    grid_class  = gridclass,
                    counter     = counter + 1 - meta_card_counter,
                    nid         = nid,
                    creation    = "&#128336; " + timeDiffString,
                    edited      = "" if str(nid) not in cls.edited else "<i class='fa fa-pencil ml-10 mr-5'></i> " + cls._build_edited_info(cls.edited[str(nid)]),
                    mouseup     = "getSelectionText()",
                    text        = text,
                    tags        = utility.tags.build_tag_string(res.tags, cls.gridView),
                    ret         = retInfo)

            html = f"{html}{newNote}"
            tags = cls._addToTags(tags, res.tags)
            if counter - (page - 1) * 50 < 20:
                # todo: title for user notes
                allText = f"{allText} {res.text[:5000]}"
                if res.note_type == "user":
                    allText = f"{allText} {res.title}"


        tags.sort()
        html    = html.replace("`", "&#96;").replace("$", "&#36;")
        pageMax = math.ceil(len(notes) / 50.0)

        if get_index() is not None and get_index().lastResDict is not None:
            index                                           = get_index()
            index.lastResDict["time-html"]                  = int((time.time() - start) * 1000)
            index.lastResDict["time-html-highlighting"]     = int(highlight_total * 1000)
            index.lastResDict["time-html-build-user-note"]  = int(build_user_note_total * 1000)
        if stamp is None and cls.last_took is not None:
            took = cls.last_took
            stamp = -1
        elif stamp is not None:
            took = utility.misc.get_milisec_stamp() - stamp
            cls.last_took = took
        else:
            took = "?"
        timing      = "true" if timing_info else "false"
        rerender    = "true" if is_rerender else "false"

        header      = [h.replace('`', "") for h in header] if header else []

        if not cls.hideSidebar:
            infoMap = {
                "Took" :  "<b>%s</b> ms %s" % (took, "&nbsp;<b style='cursor: pointer' onclick='pycmd(`siac-last-timing`)'><i class='fa fa-info-circle'></i></b>" if timing_info else ""),
                "Found" :  "<b>%s</b> notes" % (len(notes) if len(notes) > 0 else "<span style='color: red;'>0</span>")
            }
            info = cls.build_info_table(infoMap, tags, allText)
            cmd = "setSearchResults(%s, `%s`, `%s`, %s, page=%s, pageMax=%s, total=%s, cacheSize=%s, stamp=%s, printTiming=%s, isRerender=%s);" % (json.dumps(header), html, info[0].replace("`", "&#96;"), json.dumps(info[1]), page, pageMax, len(notes), len(cls.previous_calls), stamp, timing, rerender)
        else:
            cmd = "setSearchResults(%s, `%s`, ``, null, page=%s , pageMax=%s, total=%s, cacheSize=%s, stamp=%s, printTiming=%s, isRerender=%s);" % (json.dumps(header), html, page, pageMax, len(notes), len(cls.previous_calls), stamp, timing, rerender)

        cls._js(cmd, editor)

        if len(remaining_to_highlight) > 0:
            cmd = ""
            for nid,text in remaining_to_highlight.items():
                cmd = ''.join((cmd, "document.getElementById('siac-inner-card-%s').innerHTML = `%s`;" % (nid, utility.text.mark_highlights(text, query_set))))
            cls._js(cmd, editor)

        if len(check_for_suspended) > 0:
            susp = get_suspended(check_for_suspended)
            if len(susp) > 0:
                cmd = ""
                for nid in susp:
                    cmd = f"{cmd}$('#siac-susp-dsp-{nid}').html(`<span id='siac-susp-lbl-{nid}' onclick='pycmd(\"siac-unsuspend-modal {nid}\")' class='siac-susp-lbl'>&nbsp;SUSPENDED&nbsp;</span>`);"
                cls._js(cmd, editor)

        if len(pdfs) > 0:
            pdf_info_list = get_pdf_info(pdfs)

            if pdf_info_list is not None and len(pdf_info_list) > 0:
                cmd = ""
                for i in pdf_info_list:

                    perc        = int(i[1] * 10.0 / i[2])
                    prog_bar    = ""

                    for x in range(0, 10):
                        if x < perc:
                            prog_bar = ''.join((prog_bar, "<div class='siac-prog-sq-filled'></div>"))
                        else:
                            prog_bar = ''.join((prog_bar, "<div class='siac-prog-sq'></div>"))
                    cmd = ''.join((cmd, "document.querySelector('#ptmp-%s').innerHTML = `%s <span>%s / %s</span>`;" % (i[0], prog_bar, i[1], i[2])))

                    extract             = ""
                    ext_start           = i[3]
                    ext_end             = i[4]
                    if ext_end and ext_start == ext_end:
                        extract         = f"<span class='siac-extract-mark'> [{ext_start}]</span>"
                    elif ext_start:
                        extract         = f"<span class='siac-extract-mark'> [{ext_start} - {ext_end}]</span>"
                    if extract != "":
                        cmd = ''.join((cmd, "document.querySelector('#siac-ex-tmp-%s').innerHTML = `%s`;" % (i[0], extract)))

                cls._js(cmd, editor)

        return (highlight_total * 1000, build_user_note_total)

    @classmethod
    def js(cls, js: JS):
        """
            Use webview's eval function to execute the given js.
        """
        if cls._editor is None or cls._editor.web is None or not js:
            return
        cls._editor.web.eval(js)

    @classmethod
    def js_with_cb(cls, js: JS, cb: Callable):
        if cls._editor is None or cls._editor.web is None:
            return
        cls._editor.web.evalWithCallback(js, cb)

    @classmethod
    def _js(cls, js: JS, editor: aqt.editor.Editor):
        """ Try to eval the given js, prefer if editor ref is given (through cmd parsing). """
        if editor is None or editor.web is None:
            if cls._editor is not None and cls._editor.web is not None:
                cls._editor.web.eval(js)
        else:
            editor.web.eval(js)

    ### Sorting & Filtering

    @classmethod
    def sort_by_date(cls, mode: str):
        """ Rerenders the last search results, but sorted by creation date. """
        if cls.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        cls.latest = stamp
        sortedByDate = list(sorted(cls.lastResults, key=lambda x: int(x.id)))
        if mode == "desc":
            sortedByDate = list(reversed(sortedByDate))
        header = cls.previous_calls[-1][0]
        cls.print_search_results(header, sortedByDate, stamp)


    @classmethod
    def remove_untagged(cls):
        if cls.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        cls.latest = stamp
        filtered = []
        for r in cls.lastResults:
            if r.tags is None or len(r.tags.strip()) == 0:
                continue
            filtered.append(r)
        header = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    @classmethod
    def remove_tagged(cls):
        if cls.lastResults is None:
            return
        stamp = utility.misc.get_milisec_stamp()
        cls.latest = stamp
        filtered = []
        for r in cls.lastResults:
            if r.tags is None or len(r.tags.strip()) == 0:
                filtered.append(r)
        header = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    @classmethod
    def remove_unreviewed(cls):
        if cls.lastResults is None:
            return
        stamp       = utility.misc.get_milisec_stamp()
        cls.latest  = stamp
        nids        = [str(r.id) for r in cls.lastResults]
        nidStr      =  "(%s)" % ",".join(nids)
        unreviewed  = [r[0] for r in mw.col.db.all("select nid from cards where nid in %s and reps = 0" % nidStr)]
        filtered    = [r for r in cls.lastResults if int(r.id) not in unreviewed]
        header      = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    @classmethod
    def remove_reviewed(cls):
        if cls.lastResults is None:
            return
        stamp       = utility.misc.get_milisec_stamp()
        cls.latest  = stamp
        nids        = [str(r.id) for r in cls.lastResults]
        nidStr      = "(%s)" % ",".join(nids)
        reviewed    = [r[0] for r in mw.col.db.all("select nid from cards where nid in %s and reps > 0" % nidStr)]
        filtered    = [r for r in cls.lastResults if int(r.id) not in reviewed]
        header      = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    @classmethod
    def remove_suspended(cls):
        if cls.lastResults is None: return
        stamp       = utility.misc.get_milisec_stamp()
        cls.latest  = stamp
        susp        = get_suspended([r.id for r in cls.lastResults])
        filtered    = [r for r in cls.lastResults if int(r.id) not in susp]
        header      = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    @classmethod
    def remove_unsuspended(cls):
        if cls.lastResults is None: return
        stamp       = utility.misc.get_milisec_stamp()
        cls.latest  = stamp
        susp        = get_suspended([r.id for r in cls.lastResults])
        filtered    = [r for r in cls.lastResults if int(r.id) in susp]
        header      = cls.previous_calls[-1][0]
        cls.print_search_results(header,  filtered, stamp)

    ### End Sorting & Filtering


    @classmethod
    def _build_edited_info(cls, timestamp: int) -> str:
        diffInSeconds = time.time() - timestamp
        if diffInSeconds < 60:
            return "Edited just now"
        if diffInSeconds < 120:
            return "Edited 1 minute ago"
        if diffInSeconds < 3600:
            return "Edited %s minutes ago" % int(diffInSeconds / 60)
        return "Edited today"

    @classmethod
    def _get_time_diff_lbl(cls, nid: int, now: int) -> str:
        """
            Helper function that builds the string that is displayed when clicking on the result number of a note.
        """
        diffInMinutes   = (now - int(nid)) / 1000 / 60
        diffInDays      = diffInMinutes / 60 / 24

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


    @classmethod
    def build_info_table(cls, infoMap: Dict[str, str], tags: List[str], allText: str) -> Tuple[HTML, Dict[str, HTML]]:
        """ Right hand side of the result pane, shows some information about the current results (tags, keywords, time taken). """

        infoStr             = "<table>"

        for key, value in infoMap.items():
            infoStr         = f"{infoStr}<tr><td>{key}</td><td id='info-{key}'>{value}</td></tr>"

        infoStr             = f"{infoStr}</table><div class='searchInfoTagSep'><i class='fa fa-tags'></i>&nbsp; Tags:</div><div id='tagContainer'>"
        tagStr              = ""
        if len(tags) == 0:
            infoStr         += "No tags in the results."
            infoMap["Tags"] = "No tags in the results."
        else:
            for key, value in utility.tags.to_tag_hierarchy(tags).items():
                stamp = f"siac-tg-{utility.text.get_stamp()}"
                if len(value)  == 0:
                    tagStr = f"{tagStr}<span class='tagLbl' data-stamp='{stamp}' data-name='{key}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(key, 19)}</span>"
                else:
                    tagData = " ".join(cls.iter_tag_map({key : value}, ""))
                    if len(value) == 1 and tagData.count("::") < 2 and not key in tags:
                        tagStr = f"{tagStr}<span class='tagLbl' data-stamp='{stamp}' data-name='{tagData.split(' ')[1]}' data-tags='{tagData}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(tagData.split()[1],16)}</span>"
                    else:
                        tagStr = f"{tagStr}<span class='tagLbl' data-stamp='{stamp}' data-name='{tagData}' data-tags='{tagData}' onclick='tagClick(this);' onmouseenter='tagMouseEnter(this)' onmouseleave='tagMouseLeave(this)'>{utility.text.trim_if_longer_than(key,12)}&nbsp; (+{len(value)})</span>"

            infoStr += tagStr
            infoMap["Tags"] = tagStr

        infoStr             = f"{infoStr}</div><div class='searchInfoTagSep bottom' >Keywords:</div><div id='keywordContainer'>"
        mostCommonWords     = cls._most_common_words(allText)
        infoStr             = f"{infoStr}{mostCommonWords}</div>"
        infoMap["Keywords"] = mostCommonWords

        return (infoStr, infoMap)



    @classmethod
    def _most_common_words(cls, text: str) -> HTML:
        """ Returns the html that is displayed in the right sidebar containing the clickable keywords. """

        if text is None or len(text) == 0:
            return "No keywords for empty result."

        text            = utility.text.clean(text)
        counts          = {}
        for token in text.split():
            if token == "" or len(token) == 1 or cls.EXCLUDE_KEYWORDS.match(token):
                continue
            if token.lower() in counts:
                counts[token.lower()][1] += 1
            else:
                counts[token.lower()] = [token, 1]

        sortedCounts    = sorted(counts.items(), key=lambda kv: kv[1][1], reverse=True)
        html            = ""

        for entry in sortedCounts[:15]:
            k       = utility.text.trim_if_longer_than(entry[1][0], 25)
            kd      = entry[1][0].replace("'", "")
            html    = f"{html}<a class='keyword' href='#' data-keyword='{kd}' onclick='event.preventDefault(); searchFor($(this).data(\"keyword\"));'>{k}</a>, "

        if len(html) == 0:
            return "No keywords for empty result."

        return html[:-2]

    @classmethod
    def get_result_html_simple(cls, db_list, tag_hover = True, search_on_selection = True, query_set = None) -> HTML:

        html            = ""
        nids            = [r.id for r in db_list]

        if cls.showRetentionScores:
            retsByNid   = getRetentions(nids)

        for counter, res in enumerate(db_list):
            ret = retsByNid[int(res.id)] if cls.showRetentionScores and int(res.id) in retsByNid else None

            if ret is not None:
                retMark = "border-color: %s;" % (utility.misc._retToColor(ret))
                retInfo = """<div class='retMark' style='%s'>PR: %s</div> """ % (retMark, int(ret))
            else:
                retInfo = ""

            text = res.get_content()

            # hide fields that should not be shown
            if str(res.mid) in cls.fields_to_hide_in_results:
                text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in cls.fields_to_hide_in_results[str(res.mid)]])

            # hide cloze brackets if set in config
            if not cls.show_clozes:
                text = utility.text.hide_cloze_brackets(text)

            #remove <div> tags if set in config
            if cls.remove_divs and res.note_type != "user":
                text = utility.text.remove_divs(text)

            if cls.highlighting and query_set is not None:
                text = utility.text.mark_highlights(text, query_set)

            text        = utility.text.clean_field_separators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
            text        = utility.text.try_hide_image_occlusion(text)
            #try to put fields that consist of a single image in their own line
            text        = utility.text.newline_before_images(text)
            template    = NOTE_TMPL_SIMPLE if res.note_type == "index" else NOTE_TMPL_SIAC_SIMPLE
            title       = res.get_title() if res.note_type == "user" else ""
            newNote     = template.format(
                counter = counter+1,
                title   = title,
                nid     = res.id,
                edited  = "" if str(res.id) not in cls.edited else "<i class='fa fa-pencil ml-10 mr-5'></i> " + cls._build_edited_info(cls.edited[str(res.id)]),
                mouseup = "getSelectionText()" if search_on_selection else "",
                text    = text,
                ret     = retInfo,
                tags    = utility.tags.build_tag_string(res.tags, tag_hover, maxLength = 25, maxCount = 2))
            html        += newNote

        return html


    @classmethod
    def print_timeline_info(cls, context_html, db_list):

        html = cls.get_result_html_simple(db_list, tag_hover= False)

        if len(html) == 0:
            html = "%s <div style='text-align: center; line-height: 100px;'>No notes added on that day.</div><div style='text-align: center;'> Tip: Hold Ctrl and hover over the timeline for faster navigation</div>" % (context_html)
        else:
            html = """
                %s
                <div id='cal-info-notes' style='overflow-y: auto; overflow-x: hidden; height: 190px; margin: 10px 0 5px 0; padding-left: 4px; padding-right: 8px;'>%s</div>
            """ % (context_html, html)

        cls._editor.web.eval("document.getElementById('cal-info').innerHTML = `%s`;" % html)

    @classmethod
    def print_in_meta_cards(cls, html_list: List[Tuple[str, str]]):
        """ Print the given list of (title, body) pairs each as its own card. """

        if html_list is None or len(html_list) == 0:
            return

        stamp = utility.misc.get_milisec_stamp()
        cls.latest = stamp
        notes = []
        for (title, body) in html_list:
            notes.append(SiacNote.mock(title, body, "Meta"))
        cls.print_search_results(None,  notes, stamp)


    @classmethod
    def show_in_modal(cls, title: str, body: HTML):
        modal = filled_template("modal", dict(title=title, body=body))
        cmd = f"$('#siac-modal').remove(); $('#siac-right-side').append(`{modal}`);"
        cls.js(cmd)

    @classmethod
    def show_in_large_modal(cls, html: HTML):
        """ Atm used for the reader only. """
        html = html.replace("`", "&#96;")
        js = """
            $('#siac-reading-modal').html(`%s`);
            document.getElementById('siac-reading-modal').style.display = 'flex';
            document.getElementById('resultsArea').style.display = 'none';
            document.getElementById('bottomContainer').style.display = 'none';
            document.getElementById('topContainer').style.display = 'none';
        """ % (html)
        cls.js(js)

    @classmethod
    def empty_result(cls, message: str):
        if cls._editor is None or cls._editor.web is None:
            return
        cls._editor.web.eval("setSearchResults(null, '', `%s`, null, 1, 1, 50, %s)" % (message, len(cls.previous_calls) + 1))

    @classmethod
    def show_search_modal(cls, on_enter_attr: JS, header: HTML):
        cls._editor.web.eval("""
            document.getElementById('siac-search-modal').style.display = 'block';
            document.getElementById('siac-search-modal-header').innerHTML = `%s`;
            document.getElementById('siac-search-modal-inp').setAttribute('onkeyup', '%s');
            document.getElementById('siac-search-modal-inp').focus();
        """ % (header,on_enter_attr))

    @classmethod
    def show_stats(cls, text, reviewPlotData, ivlPlotData, timePlotData):

        cls.show_in_modal("Note Info", text)

        cmd = ""
        c   = 0
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
                                    $(this).css("color", "#f0506e");
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

        cls.js(cmd)

    @classmethod
    def hide_modal(cls):
        cls.js("$('#siac-modal').remove();")

    @classmethod
    def _addToTags(cls, tags, tagStr):
        if tagStr == "":
            return tags
        for tag in tagStr.split(" "):
            if tag == "":
                continue
            if tag in tags:
                continue
            tags.append(tag)
        return tags

    @classmethod
    def print_tag_hierarchy(cls, tags: List[str]):
        html = cls.build_tag_hierarchy(tags)
        cls.show_in_modal("Tags", html)

        cmd = """
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
        """
        cls.js(cmd)

    @classmethod
    def build_tag_hierarchy(cls, tags: List[str]) -> HTML:
        tmap    = utility.tags.to_tag_hierarchy(tags)
        config  = mw.addonManager.getConfig(__name__)

        def iterateMap(tmap, prefix, start=False):
                if start:
                    html = "<ul class='tag-list outer'>"
                else:
                    html = "<ul class='tag-list'>"
                for key, value in tmap.items():
                    full = prefix + "::" + key if prefix else key
                    html += "<li class='tag-list-item'><span class='tag-btn'>%s %s</span><div class='tag-add' data-name=\"%s\" data-target='%s' onclick='event.stopPropagation(); tagClick(this)'>%s</div>%s</li>" % (
                        utility.text.trim_if_longer_than(key, 25),
                        "[-]" if value else "" ,
                        utility.text.delete_chars(full, ["'", '"', "\n", "\r\n", "\t", "\\"]),
                        key,
                        "+" if not config["tagClickShouldSearch"] else "<div class='siac-modal-btn'>Search</div>",
                    iterateMap(value, full))
                html += "</ul>"
                return html

        html = iterateMap(tmap, "", True)
        return html


    @classmethod
    def iter_tag_map(cls, tmap, prefix):
        if len(tmap) == 0:
            return []
        res = []
        if prefix:
            prefix = prefix + "::"
        for key, value in tmap.items():
            if type(value) is dict:
                if len(value) > 0:
                    res.append(prefix + key)
                    res +=  cls.iter_tag_map(value, prefix + key)
                else:
                    res.append(prefix + key)
        return res

    @classmethod
    def update_single(cls, note):
        """
        Used after note has been edited. The edited note should be rerendered.
        To keep things simple, only note text and tags are replaced.
        """
        if cls._editor is None or cls._editor.web is None:
            return

        tags    = note[2]
        tagStr  = utility.tags.build_tag_string(tags, cls.gridView)
        nid     = note[0]
        text    = note[1]

             # hide fields that should not be shown
        if len(note) > 4 and str(note[4]) in cls.fields_to_hide_in_results:
            text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in cls.fields_to_hide_in_results[str(note[4])]])

        text    = utility.text.clean_field_separators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
        text    = utility.text.try_hide_image_occlusion(text)

        # hide clozes if set in config
        if not cls.show_clozes:
            text    = utility.text.hide_cloze_brackets(text)

        text    = utility.text.newline_before_images(text)

        if cls.remove_divs:
            text    = utility.text.remove_divs(text, " ")

        #find rendered note and replace text and tags
        cls._editor.web.eval("""
            document.getElementById('siac-inner-card-%s').innerHTML = `%s`;
            document.getElementById('tags-%s').innerHTML = `%s`;
        """ % (nid, text, nid, tagStr))

        cls._editor.web.eval(f"""$('#siac-edited-dsp-{nid}').html(`<i class='fa fa-pencil mr-5 ml-10'></i> Edited just now`); """)

    @classmethod
    def show_tooltip(cls, text):
        if mw.addonManager.getConfig(__name__)["hideSidebar"]:
            tooltip("Query was empty after cleaning.")

    @classmethod
    def print_pdf_search_results(cls, results, query_cleaned, raw_query):
        
        limit       = get_config_value_or_default("pdfTooltipResultLimit", 50)
        tt_height   = get_config_value_or_default("pdfTooltipMaxHeight", 300)
        tt_width    = get_config_value_or_default("pdfTooltipMaxWidth", 300) + 100

        if results is not None and len(results) > 0:
            qset        = set([t.lower().strip() for t in query_cleaned.split() if len(t.strip()) > 0]) if query_cleaned is not None else set()
            sr_html     = cls.get_result_html_simple(results[:limit], False, False, qset)
            query       = query_cleaned
        else:
            if query_cleaned is None or len(query_cleaned) == 0:
                query   = raw_query
                sr_html = "<center class='mt-5 mb-5'>Query was empty after cleaning.</center>"
            else:
                query   = query_cleaned
                sr_html = "<center class='mt-5 mb-5'>Nothing found for query.</center>"

        html        = filled_template("rm/tooltip_search", dict(search_results = sr_html, query = query))

        cls._editor.web.eval("""
            (() => {
                document.getElementById('siac-pdf-tooltip').innerHTML = `%s`;
                document.getElementById('siac-pdf-tooltip-results-area').scrollTop = 0;
                let total_height = document.getElementById('siac-reading-modal').offsetHeight;
                let h_diff = total_height - $('#siac-pdf-tooltip').data('top');
                let needed = %s + 100;
                if (h_diff < needed && needed - h_diff < 300) {
                    document.getElementById("siac-pdf-tooltip-results-area").style.maxHeight = (h_diff - 120) + "px";
                    document.getElementById("siac-pdf-tooltip").style.maxWidth = "%spx";
                } else {
                    document.getElementById("siac-pdf-tooltip-results-area").style.removeProperty('max-height');
                    document.getElementById("siac-pdf-tooltip").style.removeProperty('max-width');
                }
                setTimeout(refreshMathJax, 10);
            })();
        """ % (html, tt_height, tt_width))

        

    @classmethod
    def setup_ui_after_index_built(cls, editor: Optional[aqt.editor.Editor], index, init_time=None):
        #editor is None if index building finishes while add dialog is not open
        
        if editor is None:
            return
        cls.set_editor(editor)

        config = mw.addonManager.getConfig(__name__)
        cls.show_search_result_area(editor, init_time)
        #restore previous settings
        cmd = ""
        cmd += f"$('#highlightCb').prop('checked', {str(cls.highlighting).lower()});"
        if not get_config_value_or_default("searchOnTyping", True):
            cmd += "$('#typingCb').prop('checked', false); setSearchOnTyping(false);"
        if not get_config_value_or_default("searchOnSelection", True):
            cmd += "$('#selectionCb').prop('checked', false); SIAC.State.searchOnSelection = false;"
        if index is not None and not UI.uiVisible:
            cmd += "$('#siac-right-side').addClass('addon-hidden');"
        if config["gridView"]:
            cmd += "activateGridView();"
        editor.web.eval(cmd)
        if index is not None:
            #plot.js is already loaded if a note was just added, so this is a lazy solution for now
            cls.plotjsLoaded = False
        if config["notes.sidebar.visible"]:
            cls.sidebar.display()

        editor.web.eval("""pycmd('siac-initialised-editor');""")


    @classmethod
    def show_search_result_area(cls, editor=None, initializationTime=0):
        """ Toggle between the loader and search result area when the index has finished building. """

        js = """
            if (document.getElementById('searchResults')) {
                document.getElementById('searchResults').style.display = 'block';
            }
            if (document.getElementById('loader')) {
                document.getElementById('loader').style.display = 'none';
            }"""

        if cls._editor:
            cls.js(js)
        elif editor is not None and editor.web is not None:
            cls._editor = editor
            editor.web.eval(js)


    @classmethod
    def print_starting_info(cls):
        """ Displays the information that is visible after the first start of the add-on. """

        config  = mw.addonManager.getConfig(__name__)
        index   = get_index()

        notes   = []

        html    = "<h3>Search is <span style='color: #32d296'>ready</span>. (%s)</h3>" %  index.type if index is not None else "?"
        if not index.creation_info["index_was_rebuilt"]:
            html += "Initalized in <b>%s</b> s (no changes detected)." % index.initializationTime
        else:
            html += "Initalized in <b>%s</b> s." % index.initializationTime

        html += "<br/>Index contains <b>%s</b> notes." % index.get_number_of_notes()
        html += "<br/><i>Search on typing</i> delay is set to <b>%s</b> ms." % config["delayWhileTyping"]
        html += "<br/>Window split is <b>%s / %s</b>." % (config["leftSideWidthInPercent"], 100 - int(config["leftSideWidthInPercent"]))
        html += "<br/>Layout Shortcuts:<br> <b>%s</b> (toggle left), <b>%s</b> (toggle right), <b>%s</b> (show both)." % (config["shortcuts.window_mode.show_left"], config["shortcuts.window_mode.show_right"], config["shortcuts.window_mode.show_both"])

        if not state.db_file_existed:
            html += "<br><br><b><i>siac-notes.db</i> was not existing, created a new one.</b>"

        if index is None:
            html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"

        notes.append(("Status", html))

        html    = ""
        changes = UI.changelog()
        if changes:
            for ix, c in enumerate(changes):
                html += f"{ix + 1}. {c}<br>"
        notes.append(("Changelog", html))

        chr_v   = utility.misc.chromium_version()
        if chr_v is not None and chr_v < "73":
            notes.append(("Notice", f"""It seems like your Anki version is using an older version of Chromium ({chr_v}).
                It might happen that parts of the layout behave incorrectly.
                If you experience UI issues, consider updating to a newer Anki version (or if you are on Windows, using the standard installer instead of the alternate installer, 
                which uses an older toolkit version).
            """))

        html    = """
            This add-on has grown so large, that it is now infeasible for a single person to test all features on every update (and the large number of possible combinations of config settings makes this even more difficult).
            So if you think you spotted an error, an inconsistency or even just some UI part that doesn't seem right, please report it.
            <br><br>
            <a href='https://github.com/fonol/anki-search-inside-add-card/issues' title='Github issue tracker'>Github issue tracker</a>
            <br><br>
            Thanks in advance.


        """
        notes.append(("Community Debugging", html))

        html    = ""
        issues  = UI.known_issues()
        if issues:
            for ix, i in enumerate(issues):
                html += f"{ix + 1}. {i}<br>"
        notes.append(("Known Issues", html))

        html = f"""
            <div class='ta_center'>
                <div class='flex-row mt-10' style='margin-bottom: 20px; justify-content: center;'>
                    <div class='ta_center'>
                        <div class='siac-caps' style='opacity: 0.8; margin-bottom: 15px;'>BUGS & FEEDBACK</div>
                        <a href='https://github.com/fonol/anki-search-inside-add-card/issues' title='Github repository'><img src='{utility.misc.img_src("github_light.png" if state.night_mode else "github_dark.png")}' style='height: 32px;'/></a>
                    </div>
                    <div class='ta_center' style='margin-left: 30px;'>
                        <div class='siac-caps' style='opacity: 0.8; margin-bottom: 15px;'>BECOME A PATRON</div>
                        <a href='https://www.patreon.com/tomtomtom' title='Patreon site'><img src='{utility.misc.img_src("patreon.png")}' style='height: 32px;'/></a>
                    </div>
                </div>
                <span class='siac-caps' style='opacity: 0.8;'>
                    Thanks to all supporters!
                </span>
            </div>
            """
        notes.append(("Bugs, Feedback, Support", html))
        cls.print_in_meta_cards(notes)

    @classmethod
    def fillDeckSelect(cls, editor: Optional[aqt.editor.Editor] = None, expanded= False, update = True):
        """ Fill the selection with user's decks """

        deckMap     = dict()
        config      = mw.addonManager.getConfig(__name__)
        deckList    = config['decks']
        index       = get_index()
        if editor is None:
            if cls._editor is not None:
                editor = cls._editor
            else:
                return
            
        if hasattr(mw.col.decks, "all_names_and_ids"):
            for d in mw.col.decks.all_names_and_ids():
                if d.name == 'Standard':
                    continue
                if deckList is not None and len(deckList) > 0 and d.name not in deckList:
                    continue
                deckMap[d.name] = d.id
        else:
            for d in list(mw.col.decks.decks.values()):
                if d['name'] == 'Standard':
                    continue
                if deckList is not None and len(deckList) > 0 and d['name'] not in deckList:
                    continue
                deckMap[d['name']] = d['id']

        set_deck_map(deckMap)
        dmap        = {}
        for name, id in deckMap.items():
            dmap = cls.addToDecklist(dmap, id, name)

        dmap        = dict(sorted(dmap.items(), key=lambda item: item[0].lower()))
        def iterateMap(dmap, prefix, start=False):
            decks = index.selectedDecks if index is not None else []
            if start:
                html = "<ul class='deck-sub-list outer'>"
            else:
                html = "<ul class='deck-sub-list'>"
            for key, value in dmap.items():
                full = prefix + "::" + key if prefix else key
                if full in deckMap:
                    did = deckMap[full]
                elif len(deckMap) == 1:
                    did = list(deckMap.values())[0]
                html += "<li class='deck-list-item %s' data-id='%s' onclick='event.stopPropagation(); updateSelectedDecks(this);'><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % ( 
                    "selected" if str(did) in decks or decks == ["-1"] else "", 
                    did,  "[+]" if value else "", 
                    utility.text.trim_if_longer_than(key, 35), 
                    iterateMap(value, full, False))
            html += "</ul>"
            return html

        html        = iterateMap(dmap, "", True)
        expanded_js = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""
        update_js   = "updateSelectedDecks();" if update else ""

        cmd         = """
        document.getElementById('deck-sel-info-lbl').style.display = 'block';
        document.getElementById('deckSel').innerHTML = `%s`;
        $('#deckSelWrapper .exp').click(function(e) {
            e.stopPropagation();
            let icn = $(this);
            if (icn.text()) {
                if (icn.text() === '[+]')
                    icn.text('[-]');
                else
                    icn.text('[+]');
            }
            $(this).parent().parent().children('ul').toggle();
        });
        %s
        $("#siac-deck-sel-btn-wrapper").show();
        %s
        """ % (html, expanded_js, update_js)
        editor.web.eval(cmd)

    @classmethod
    def addToDecklist(cls, dmap, id, name):
        names = [s for s in name.split("::") if s != ""]
        for c, d in enumerate(names):
            found = dmap
            for i in range(c):
                found = found.setdefault(names[i], {})
            if not d in found:
                found.update({d : {}})
        return dmap


    @classmethod
    def try_select_deck(cls, deck: str) -> bool:
        """ Try to select a deck with the given name. """

        if not deck or len(deck.strip()) == 0:
            return False

        win = aqt.mw.app.activeWindow()
        # dont trigger keypress in edit dialogs opened within the add dialog
        if not isinstance(win, aqt.addcards.AddCards):
            return False

        try:
            win.deckChooser.setDeckName(deck)
            # win.deckChooser.onDeckChange()
            return True
        except:
            return False


    @staticmethod
    def changelog() -> List[str]:
        """ Returns recent add-on changes. """

        return [
            "Possible fix for incorrect field input font-sizing",
            "Display 'Created x days ago' as tooltip on hover over note number",
        ]

    @staticmethod
    def known_issues() -> List[str]:
        """ Returns currently known issues/bugs. """

        return [
            "Tag autocomplete in Create/Update note modal only works on first tag",
            "PDF text may be blurry if Zoom (next to 'Theme') is set to non-100% value",
            "PDF reader \"Loading PDF\" message positioned wrong on older Anki versions",
            "Highlights in PDFs not working on some platforms/Anki versions, workaround: set 'pdf.highlights.use_alt_render' to true in the config",
        ]
