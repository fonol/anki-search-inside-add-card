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


import platform
import os
import json
import re
import time
from datetime import datetime as dt
import sys
import typing
from typing import List, Optional, Tuple, Any
import aqt
import uuid
import html as ihtml
from aqt import mw
from aqt.editor import Editor
from aqt.utils import showInfo, tooltip

import utility.tags
import utility.text
import utility.misc
import utility.date

from ..tag_find import get_most_active_tags
from ..state import get_index, check_index, set_deck_map
from ..notes import *
from ..notes import _get_priority_list
from ..models import SiacNote, IndexNote, Printable
from .html import *
from .note_templates import *
from ..internals import js, requires_index_loaded, perf_time
from ..config import get_config_value_or_default
from ..web_import import import_webpage
from ..stats import getRetentions


class ReadingModal:
    """ Used to display text and PDF notes. """

    last_opened : Optional[int] = None

    def __init__(self):
        self.note_id            : Optional[int]         = None
        self.note               : Optional[SiacNote]    = None
        self._editor            : Optional[Editor]      = None

        self.highlight_color    : str                   = "#e65100"
        self.highlight_type     : int                   = 1

        self.sidebar            : ReadingModalSidebar   = ReadingModalSidebar()

    def set_editor(self, editor):
        self._editor            = editor
        self.sidebar.set_editor(editor)

    def reset(self):
        self.note_id            = None
        self.note               = None

    @requires_index_loaded
    def display(self, note_id: int):

        index                   = get_index()
        note                    = get_note(note_id)

        if ReadingModal.last_opened is None or (self.note_id is not None and note_id != self.note_id):
            ReadingModal.last_opened = self.note_id

        self.note_id            = note_id
        self.note               = note

        html                    = self.html()

        index.ui.show_in_large_modal(html)

        # wrap fields in tabs
        index.ui.js("""
            $(document.body).addClass('siac-reading-modal-displayed');
            //remove modal animation to prevent it from being triggered when switching left/right or CTRL+F-ing
            setTimeout(() => { document.getElementById("siac-reading-modal").style.animation = "none"; }, 1000);
            if (!document.getElementById('siac-reading-modal-tabs-left')) {
                $('#siac-left-tab-browse,#siac-left-tab-pdfs,#siac-reading-modal-tabs-left').remove();
                document.getElementById('leftSide').innerHTML += `
                    <div id='siac-reading-modal-tabs-left'>
                        <div class='siac-btn siac-btn-dark active' onclick='modalTabsLeftClicked("flds", this);'>Fields</div>
                        <div class='siac-btn siac-btn-dark' onclick='modalTabsLeftClicked("browse", this);'>Browse</div>
                        <div class='siac-btn siac-btn-dark' onclick='modalTabsLeftClicked("pdfs", this);'>PDFs</div>
                    </div>
                `;
            }
        """)

        # if source is a pdf file path, try to display it
        if note.is_pdf():
            if utility.misc.file_exists(note.source):
                self._display_pdf(note.source.strip(), note_id)
            else:
                message = "Could not load the given PDF.<br>Are you sure the path is correct?"
                self.notification(message)

        # auto fill tag entry if pdf has tags and config option is set
        if note.tags is not None and len(note.tags.strip()) > 0 and get_config_value_or_default("pdf.onOpen.autoFillTagsWithPDFsTags", True):
            self._editor.tags.setText(" ".join(mw.col.tags.canonify(mw.col.tags.split(note.tags))))

        # auto fill user defined fields
        fields_to_prefill = get_config_value_or_default("pdf.onOpen.autoFillFieldsWithPDFName", [])
        if len(fields_to_prefill) > 0:
            for f in fields_to_prefill:
                title = note.get_title().replace("`", "&#96;")
                if f in self._editor.note:
                    i = self._editor.note._fieldOrd(f)
                    self._editor.web.eval(f"$('.field').eq({i}).text(`{title}`);")

    def display_head_of_queue(self):
        recalculate_priority_queue()
        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            self.display(nid)
        else:
            tooltip("Queue is empty.")

    @js
    def show_width_picker(self):
        html = """
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 10")'><b>10 - 90</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 15")'><b>15 - 85</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 20")'><b>20 - 80</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 25")'><b>25 - 75</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 33")'><b>33 - 67</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 40")'><b>40 - 60</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 50")'><b>50 - 50</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 60")'><b>60 - 40</b></div>
            <div class='w-100 siac-rm-main-color-hover' onclick='pycmd("siac-left-side-width 67")'><b>67 - 33</b></div>
        """

        modal = """
            <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                <b>Width (%%)</b><br>
                <b>Fields - Add-on</b>
                    <br><br>
                <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div>
                    <br><br>
                <div style='width: 100%%; text-align: right;'>
                    <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode.parentNode).remove();">Close</div>
                </div>
            </div>
        """ % html
        return "$('#siac-reading-modal-center').append(`%s`)" % modal

    @js
    def display_read_range_input(self, note_id: int, num_pages: int):
        on_confirm= """ if (document.getElementById('siac-range-input-min').value && document.getElementById('siac-range-input-max').value) {
        pycmd('siac-user-note-mark-range %s ' + document.getElementById('siac-range-input-min').value
                + ' ' + document.getElementById('siac-range-input-max').value
                + ' ' + numPagesExtract()
                + ' ' + pdfDisplayedCurrentPage);
        }
        """ % note_id
        modal = f""" <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                            Input a range of pages to mark as read (end incl.)<br><br>
                            <input id='siac-range-input-min' style='width: 60px; background: #222; color: lightgrey; border-radius: 4px;' type='number' min='1' max='{num_pages}'/> &nbsp;-&nbsp; <input id='siac-range-input-max' style='width: 60px;background: #222; color: lightgrey; border-radius: 4px;' type='number' min='1' max='{num_pages}'/>
                            <br/> <br/>
                            <div class="siac-btn siac-btn-dark" onclick="{on_confirm} $(this.parentNode).remove();">&nbsp; Ok &nbsp;</div>
                            &nbsp;
                            <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                        </div> """
        return "$('#siac-pdf-tooltip').hide();$('.siac-modal-small').remove(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")


    @js
    def reload_bottom_bar(self, note_id: int = None):
        """
            Called after queue picker dialog has been closed without opening a new note.
        """
        if note_id is not None:

            note = get_note(note_id)
            html = self.bottom_bar(note)
            html = html.replace("`", "\\`")
            return "$('#siac-reading-modal-bottom-bar').replaceWith(`%s`); updatePdfDisplayedMarks();" % html

        else:
            return """if (document.getElementById('siac-reading-modal').style.display !== 'none' && document.getElementById('siac-reading-modal-top-bar')) {
                        pycmd('siac-reload-reading-modal-bottom '+ $('#siac-reading-modal-top-bar').data('nid'));
                    }"""


    def _display_pdf(self, full_path: str, note_id: int):
        base64pdf       = utility.misc.pdf_to_base64(full_path)
        blen            = len(base64pdf)

        #pages read are stored in js array [int]
        pages_read      = get_read_pages(note_id)
        pages_read_js   = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])

        #marks are stored in two js maps, one with pages as keys, one with mark types (ints) as keys
        marks           = get_pdf_marks(note_id)
        js_maps         = utility.misc.marks_to_js_map(marks)
        marks_js        = "pdfDisplayedMarks = %s; pdfDisplayedMarksTable = %s;" % (js_maps[0], js_maps[1])

        # pdf might be an extract (should only show a range of pages)
        extract_js      = f"pdfExtract = [{self.note.extract_start}, {self.note.extract_end}];" if self.note.extract_start is not None else "pdfExtract = null;"

        # pages read are ordered by date, so take last
        last_page_read  = pages_read[-1] if len(pages_read) > 0 else 1 

        if self.note.extract_start is not None:
            if len(pages_read) > 0:
                read_in_extract = [p for p in pages_read if p >= self.note.extract_start and p <= self.note.extract_end]
                last_page_read = read_in_extract[-1] if len(read_in_extract) > 0 else self.note.extract_start
            else:
                last_page_read  = self.note.extract_start

        title           = utility.text.trim_if_longer_than(self.note.get_title(), 50).replace('"', "")
        addon_id        = utility.misc.get_addon_id()
        port            = mw.mediaServer.getPort()

        init_code = """

            pdfLoading = true;
            var bstr = atob(b64);
            var n = bstr.length;
            var arr = new Uint8Array(n);
            while(n--){
                arr[n] = bstr.charCodeAt(n);
            }
            pagesRead = [%s];
            %s
            %s
            var loadFn = function(retry) {
                if (retry > 4) {
                    $('#siac-pdf-loader-wrapper').remove();
                    document.getElementById('siac-pdf-top').style.overflowY = 'auto';
                    $('#siac-timer-popup').html(`<br><center>PDF.js could not be loaded from CDN.</center><br>`).show();
                    pdfDisplayed = null;
                    ungreyoutBottom();
                    fileReader = null;
                    pdfLoading = false;
                    noteLoading = false;
                    return;
                }
                if (typeof(pdfjsLib) === 'undefined') {
                    window.setTimeout(() => { loadFn(retry + 1);}, 800);
                    document.getElementById('siac-loader-text').innerHTML = `PDF.js was not loaded. Retrying (${retry+1} / 5)`;
                    return;
                }
                if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
                    pdfjsLib.GlobalWorkerOptions.workerSrc = 'http://127.0.0.1:%s/_addons/%s/web/pdfjs/pdf.worker.min.js';
                }
                var canvas = document.getElementById("siac-pdf-canvas");
                var loadingTask = pdfjsLib.getDocument(arr, {nativeImageDecoderSupport: 'display'});
                loadingTask.promise.catch(function(error) {
                        console.log(error);
                        $('#siac-pdf-loader-wrapper').remove();
                        document.getElementById('siac-pdf-top').style.overflowY = 'auto';

                        $('#siac-timer-popup').html(`<br><center>Could not load PDF - seems to be invalid.</center><br>`).show();
                        pdfDisplayed = null;
                        ungreyoutBottom();
                        fileReader = null;
                        pdfLoading = false;
                        noteLoading = false;
                });
                loadingTask.promise.then(function(pdf) {
                        pdfDisplayed = pdf;
                        pdfDisplayedCurrentPage = %s;
                        pdfHighDPIWasUsed = false;
                        $('#siac-pdf-loader-wrapper').remove();
                        document.getElementById('siac-pdf-top').style.overflowY = 'auto';
                        document.getElementById('text-layer').style.display = 'block'; 
                        if (pagesRead.length === pdf.numPages) {
                            pdfDisplayedCurrentPage = 1;
                            queueRenderPage(1, true, true, true);
                        } else {
                            queueRenderPage(pdfDisplayedCurrentPage, true, true, true);
                        }
                        updatePdfProgressBar();
                        if (pdfBarsHidden) {
                            showPDFBottomRightNotification("%s", 4000);
                        }
                        setTimeout(refreshCanvas, 50);
                        if (pagesRead.length === 0) { pycmd('siac-insert-pages-total %s ' + numPagesExtract()); }
                        fileReader = null;
                });
            };
            loadFn();
            b64 = ""; arr = null; bstr = null; file = null;
        """ % (pages_read_js, marks_js, extract_js, port, addon_id, last_page_read, title, note_id)
        #send large files in multiple packets
        page = self._editor.web.page()
        chunk_size = 10000000
        if blen > chunk_size:
            page.runJavaScript(f"var b64 = `{base64pdf[0: chunk_size]}`;")
            sent = chunk_size
            while sent < blen:
                page.runJavaScript(f"b64 += `{base64pdf[sent: min(blen,sent + chunk_size)]}`;")
                sent += min(blen - sent, chunk_size)
            page.runJavaScript(init_code)
        else:
            page.runJavaScript("""
                var b64 = `%s`;
                    %s
            """ % (base64pdf, init_code))
      

    def show_fields_tab(self):
        self.sidebar.show_fields_tab()

    def show_browse_tab(self):
        self.sidebar.show_browse_tab()

    def show_pdfs_tab(self):
        self.sidebar.show_pdfs_tab()

    def html(self) -> str:
        """ Builds the html which has to be inserted into the webview to display the reading modal. """

        index       = get_index()
        note        = self.note
        note_id     = self.note_id
        text        = note.text
        tags        = note.tags
        created_dt  = datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
        diff        = datetime.datetime.now() - created_dt
        queue       = _get_priority_list()
        queue_len   = len(queue)
        time_str    = "Added %s ago." % utility.misc.date_diff_to_string(diff)

        if check_index():

            title           = note.get_title()
            title           = utility.text.trim_if_longer_than(title, 70)
            title           = ihtml.escape(title)
            source          = note.source.strip() if note.source is not None and len(note.source.strip()) > 0 else "Empty"
            source_icn      = ""
            priority        = get_priority(note_id)
            schedule_btns   = self.schedule_btns(priority)
            img_folder      = utility.misc.img_src_base_path()

            if note.is_in_queue():
                queue_btn_text      = "Done!"
                queue_btn_action    = "siac-user-note-done"
                active              = "active" if note.is_due_sometime() else ""
                schedule_dialog_btn = f"""<span id='siac-schedule-dialog-btn' class='siac-queue-picker-icn {active}' onclick='pycmd("siac-schedule-dialog")'>{clock_svg(False)}</span>"""
                delay_btn           = """&nbsp;&nbsp;&nbsp;&nbsp; <a onclick='if (!pdfLoading && !modalShown) { pycmd("siac-delay-note"); }' class='siac-clickable-anchor'>Later</a>"""

            else:
                queue_btn_text      = "First in Queue"
                queue_btn_action    = "siac-user-note-queue-read-head"
                schedule_dialog_btn = ""
                delay_btn           = ""

            html = """
                <script>destroyTinyMCE();</script>
                <div style='width: 100%; display: flex; flex-direction: column;'>
                        <div id='siac-reading-modal-top-btns'>
                            <div class='siac-btn siac-btn-dark' style='background-image: url("{img_folder}switch_layout.png");' onclick='switchLeftRight();'></div>
                            <div class='siac-btn siac-btn-dark' style='background-image: url("{img_folder}fullscreen.png");' onclick='toggleReadingModalFullscreen();'></div>
                            <div class='siac-btn siac-btn-dark' style='background-image: url("{img_folder}partition.png");' onclick='pycmd("siac-left-side-width");'></div>
                            <div class='siac-btn siac-btn-dark' style='background-image: url("{img_folder}toggle_bars.png");' onclick='toggleReadingModalBars();'></div>
                            <div class='siac-btn siac-btn-dark' style='background-image: url("{img_folder}close.png");' onclick='onReadingModalClose({note_id});'></div>
                        </div>
                    
                        <div id='siac-pdf-tooltip' onclick='event.stopPropagation();' onkeyup='event.stopPropagation();'>
                            <div id='siac-pdf-tooltip-top'></div>
                            <div id='siac-pdf-tooltip-results-area' onkeyup="pdfTooltipClozeKeyup(event);"></div>
                            <div id='siac-pdf-tooltip-bottom'></div>
                            <input id='siac-pdf-tooltip-searchbar' onkeyup='if (event.keyCode === 13) {{pycmd("siac-pdf-tooltip-search " + this.value);}}'></input>
                        </div>
                        <div id='siac-reading-modal-top-bar' data-nid='{note_id}' style=''>
                            <div style='flex: 1 1; overflow: hidden;'>
                                <h2 style='margin: 0 0 5px 0; white-space: nowrap; overflow: hidden; vertical-align:middle;'>{title}</h2>
                                <h4 style='whitespace: nowrap; margin: 5px 0 8px 0; color: lightgrey;'>Source: <i>{source}</i></h4>
                                <div id='siac-prog-bar-wr'></div>
                            </div>
                            <div style='flex: 0 0; min-width: 130px; padding: 0 120px 0 10px;'>
                                <span class='siac-timer-btn' onclick='resetTimer(this)'>5</span><span class='siac-timer-btn' onclick='resetTimer(this)'>10</span><span class='siac-timer-btn' onclick='resetTimer(this)'>15</span><span class='siac-timer-btn' onclick='resetTimer(this)'>25</span><span class='siac-timer-btn active' onclick='resetTimer(this)'>30</span><br>
                                <span id='siac-reading-modal-timer'>30 : 00</span><br>
                                <span class='siac-timer-btn' onclick='resetTimer(this)'>45</span><span class='siac-timer-btn' onclick='resetTimer(this)'>60</span><span class='siac-timer-btn' onclick='resetTimer(this)'>90</span><span id='siac-timer-play-btn' class='inactive' onclick='toggleTimer(this);'>Start</span>
                            
                            </div>
                            <div id='siac-reading-modal-change-theme'>
                                <a onclick='pycmd("siac-eval index.ui.reading_modal.show_theme_dialog()")'>Change Theme</a>
                            </div>
                            
                        </div>
                        <div id='siac-reading-modal-center' style='flex: 1 1 auto; overflow-y: {overflow}; font-size: 13px; padding: 0 20px 0 24px; position: relative; display: flex; flex-direction: column;' >
                            <div id='siac-rm-greyout'></div>
                            {text}
                        </div>
                        <div id='siac-reading-modal-bottom-bar'>
                            <div style='width: 100%; height: calc(100% - 5px); display: inline-block; padding-top: 5px; white-space: nowrap;'>
                                <div style='padding: 5px; display: inline-block; vertical-align: top;'><div class='siac-queue-sched-btn active' onclick='toggleQueue();'>{queue_info_short}</div></div>
                                {schedule_btns}
                                <div id='siac-queue-actions' style='display: inline-block; vertical-align: top; margin-left: 20px; margin-top: 3px; user-select: none; z-index: 1;'>
                                    <span style='vertical-align: top;' id='siac-queue-lbl'>{queue_info}</span><br>
                                    <span style='margin-top: 5px; color: lightgrey;'>{time_str}</span> <br>
                                    <div style='margin: 7px 0 4px 0; display: inline-block;'>Actions: <span class='siac-queue-picker-icn' onclick='if (pdfLoading||noteLoading||pdfSearchOngoing) {{return;}}pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span>{schedule_dialog_btn}</div><br>
                                    <a onclick='if (!pdfLoading && !modalShown) {{ noteLoading = true; greyoutBottom(); destroyPDF(); pycmd("{queue_btn_action}");}}' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;' id='siac-first-in-queue-btn'>{queue_btn_text}</a>
                                    {delay_btn}<br>
                                    <a onclick='if (!pdfLoading && !modalShown) {{ noteLoading = true; greyoutBottom(); destroyPDF(); pycmd("siac-user-note-queue-read-random");}}' class='siac-clickable-anchor'>Random</a><span style='color: grey; user-select: none;'>&nbsp;|&nbsp;</span>
                                    <a onclick='if (!pdfLoading && !modalShown) {{ modalShown = true; greyoutBottom(); pycmd("siac-eval index.ui.reading_modal.show_remove_dialog()");}}' class='siac-clickable-anchor'>Remove</a>
                                </div>
                                {queue_readings_list}
                                <div id='siac-queue-infobox-wrapper'>
                                    <div id='siac-queue-infobox' onmouseleave='leaveQueueItem();'></div>
                                </div>
                                <div id='siac-pdf-bottom-tabs' style='display: inline-block; vertical-align: top; margin-left: 16px; user-select: none;'>
                                    <a class='siac-clickable-anchor tab active' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} marks")' style='margin-right: 10px;'>Marks</a>
                                    <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} related")' style='margin-right: 10px;'>Related</a>
                                    <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} info")'>Info</a> <br>
                                    <div id='siac-pdf-bottom-tab'>
                                        <div id='siac-marks-display' onclick='markClicked(event);'></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div id='siac-timer-popup'>
                        </div>
                </div>
                <script>
                destroyPDF();
                if (readingTimer != null)  {{
                    $('#siac-timer-play-btn').html('Pause').removeClass('inactive');
                }} else if (remainingSeconds !== 1800) {{
                    document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
                }}
                if (pdfFullscreen) {{
                    activateReadingModalFullscreen();
                }} else if (pdfBarsHidden) {{
                    pdfBarsHidden = false;
                    toggleReadingModalBars();
                }}
                iframeIsDisplayed = false;
                noteLoading = false;
                modalShown = false;
                </script>
            """

            #check if it is a pdf or feed
            overflow = "auto"
            if note.is_pdf() and utility.misc.file_exists(source):
                editable    = False
                overflow    = "hidden" 
                text        = self.pdf_viewer_html(source, note.get_title(), priority)
                if "/" in source:
                    source  = source[source.rindex("/") +1:]
            elif note.is_feed():
                text        = self.get_feed_html(note_id, source)
                editable    = False
            else:
                editable    = len(text) < 100000
                text        = self.text_note_html(editable, priority)
            
        
            queue_info          = "Priority: %s" % (dynamic_sched_to_str(priority)) if note.is_in_queue() else "Unqueued."
            queue_info_short    = f"Priority" if note.is_in_queue() else "Unqueued"
            queue_readings_list = self.get_queue_head_display(queue, editable)

            params              = dict(note_id = note_id, title = title, source = source, time_str = time_str, img_folder = img_folder, queue_btn_text = queue_btn_text, queue_btn_action = queue_btn_action, text = text, queue_info = queue_info, 
            queue_info_short    = queue_info_short, schedule_btns=schedule_btns, queue_readings_list = queue_readings_list, overflow=overflow, schedule_dialog_btn=schedule_dialog_btn, delay_btn=delay_btn)
            html                = html.format_map(params)

            return html
        return ""


    def text_note_html(self, editable: bool, priority: int) -> str:
        """
            Returns the html which is wrapped around the text of user notes inside the reading modal.
            This function is used if the note is a regular, text-only note, if the note is a pdf note, 
            pdf_viewer_html is used instead.
        """

        nid                     = self.note_id
        dir                     = utility.misc.get_web_folder_path()
        text                    = self.note.text
        search_sources          = ""
        config                  = mw.addonManager.getConfig(__name__)
        urls                    = config["searchUrls"]

        if urls is not None and len(urls) > 0:
            search_sources = self.iframe_dialog(urls)

        is_content_editable     = "true" if editable else "false"
        title                   = utility.text.trim_if_longer_than(self.note.get_title(), 50).replace('"', "")
        quick_sched             = self.quick_sched_btn(priority)

        html                    = """
            <div id='siac-iframe-btn' style='top: 5px; left: 0px;' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
                <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center; color: grey;'>Note: Not all sites allow embedding!</div>
                <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                    <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                    <br/>
                {search_sources}
                </div>
            </div>
            {quick_sched_btn}
            <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
            <div id='siac-text-top-wr' style='height: calc(100% - 42px);'>
                <div id='siac-text-top'>
                    {text}
                </div>
            </div>
            <iframe id='siac-iframe' sandbox='allow-scripts' style='height: calc(100% - 47px);'></iframe>
            <div class="siac-reading-modal-button-bar-wrapper">
                <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                    <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                    <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
                    <div class='siac-btn siac-btn-dark' id='siac-extract-text-btn' onclick='tryExtractTextFromTextNote()' style='margin-left: 5px;'><b>Copy to new Note</b></div>
                    <div class='siac-btn siac-btn-dark' onclick='saveTextNote({nid}, remove=false)' style='margin-left: 5px;'><b>&nbsp; Save &nbsp;</b></div>
                    <span id='siac-text-note-status' style='margin-left: 30px; color: grey;'></span>
                </div>
            </div>
            <div id='siac-pdf-br-notify'>
            </div>
            <script>
                if (pdfBarsHidden) {{
                    showPDFBottomRightNotification("{title}", 4000);
                }}
                pdfDisplayedMarks = null;
                pdfDisplayedMarksTable = null;
                {tiny_mce} 
            </script>
        """.format_map(dict(text = text, nid = nid, search_sources=search_sources, quick_sched_btn=quick_sched, title=title, tiny_mce=self.tiny_mce_init_code()))
        return html

    def quick_sched_btn(self, priority: int) -> str:
        """ The button at the left side of the pdf/note pane, which allows to quickly mark as done and/or update the priority. """

        nid         = self.note_id
        value       = 0 if priority is None or priority < 0 else priority

        if value == 0: 
            current_btn = ""
        else:
            current_btn = f"""<div class='siac-btn siac-btn-dark-smaller' onclick='pycmd("siac-user-note-done");'><b>Current</b></div>"""
        return f"""
            <div class='siac-btn siac-btn-dark' id='siac-quick-sched-btn' onclick='onQuickSchedBtnClicked(this);'><div class='siac-read-icn siac-read-icn-light'></div>
                <div class='expanded-hidden white-hover' style='margin: 0 0 0 6px; color: lightgrey; text-align: center;'>
                    <input id='siac-prio-slider-small' type='range' class='siac-prio-slider-small' max='100' min='0' value='{value}' oninput='schedSmallChange(this)' onchange='schedSmallChanged(this, {nid})'/>
                    <span id='siac-slider-small-lbl' style='margin: 0 5px 0 5px;'>{value}</span>
                    {current_btn}
                </div>
            </div>
        """

    def get_feed_html(self, nid, source):
        """ Not used currently. """

        #extract feed url
        try:
            feed_url    = source[source.index(":") +1:].strip()
        except:
            return "<center>Could not load feed. Please check the URL.</center>"
        res             = read(feed_url)
        dir             = utility.misc.get_web_folder_path()
        search_sources  = ""
        config          = mw.addonManager.getConfig(__name__)
        urls            = config["searchUrls"]
        if urls is not None and len(urls) > 0:
            search_sources = self.iframe_dialog(urls)
        text            = ""
        templ           = """
                <div class='siac-feed-item'>
                    <div><span class='siac-blue-outset'>%s</span> &nbsp;<a href="%s" class='siac-ul-a'>%s</a></div>
                    <div><i>%s</i> <span style='margin-left: 15px;'>%s</span></div> 
                    <div style='margin: 15px;'>%s</div>
                </div> """

        for ix, message in enumerate(res[:25]):
            if len(message.categories) > 0:
                if len(message.categories) == 1:
                    cats = f"<span class='blue-underline'>{message.categories[0]}</span>"
                else:
                    cats = "<span class='blue-underline'>" + "</span> &nbsp;<span class='blue-underline'>".join(message.categories) + "</span>"
            else:
                cats = ""
            text = ''.join((text, templ % (ix + 1, message.link, message.title, message.date, cats, message.text)))
        html = """
            <div id='siac-iframe-btn' style='top: 5px; left: 0px;' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
                <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center; color: grey;'>Note: Not all sites allow embedding!</div>
                <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                    <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                    <br/>
                {search_sources}
                </div>
            </div>
            <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
            <div id='siac-text-top' contenteditable='false' onmouseup='nonPDFKeyup();' onclick='if (!window.getSelection().toString().length) {{$("#siac-pdf-tooltip").hide();}}'>
                {text}
            </div>
            <iframe id='siac-iframe' sandbox='allow-scripts' style='height: calc(100% - 47px);'></iframe>
            <div class="siac-reading-modal-button-bar-wrapper">
                <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                    <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                    <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
                </div>
            </div>
            <script>
                if (pdfTooltipEnabled) {{
                    $('#siac-pdf-tooltip-toggle').addClass('active');
                }} else {{
                    $('#siac-pdf-tooltip-toggle').removeClass('active');
                }}
                ungreyoutBottom();
            </script>
        """.format_map(dict(text = text, nid = nid, search_sources=search_sources))
        return html


    def bottom_bar(self, note):
        """ Returns only the html for the bottom bar, useful if the currently displayed pdf should not be reloaded, but the queue display has to be refreshed. """

        index           = get_index()
        text            = note.text
        note_id         = note.id
        source          = note.source
        created_dt      = datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
        diff            = datetime.datetime.now() - created_dt
        queue           = _get_priority_list()
        queue_len       = len(queue)
        priority        = get_priority(note_id)
        schedule_btns   = self.schedule_btns(priority)
        time_str        = "Added %s ago." % utility.misc.date_diff_to_string(diff)

        if note.is_in_queue():
            queue_btn_text      = "Done!"
            queue_btn_action    = "siac-user-note-done"
            active              = "active" if note.is_due_sometime() else ""
            schedule_dialog_btn = f"""<span id='siac-schedule-dialog-btn' class='siac-queue-picker-icn {active}' onclick='pycmd("siac-schedule-dialog")'>{clock_svg(False)}</span>"""
            delay_btn           = """&nbsp;&nbsp;&nbsp;&nbsp; <a onclick='if (!pdfLoading && !modalShown) { pycmd("siac-delay-note"); }' class='siac-clickable-anchor'>Later</a>"""
        else:
            queue_btn_text      = "First in Queue"
            queue_btn_action    = "siac-user-note-queue-read-head"
            schedule_dialog_btn = ""
            delay_btn           = ""

        html = """
                <div id='siac-reading-modal-bottom-bar' style=''>
                    <div style='width: 100%; height: calc(100% - 5px); display: inline-block; padding-top: 5px; white-space: nowrap; display: relative;'>

                        <div style='padding: 5px; display: inline-block; vertical-align: top;'><div class='siac-queue-sched-btn active' onclick='toggleQueue();'>{queue_info_short}</div></div>
                        {schedule_btns} 
                        <div  id='siac-queue-actions'  style='display: inline-block; vertical-align: top; margin-left: 20px; margin-top: 3px; user-select: none; z-index: 1;'>
                            <span style='vertical-align: top;' id='siac-queue-lbl'>{queue_info}</span><br>
                            <span style='margin-top: 5px; color: lightgrey;'>{time_str}</span> <br>
                            <div style='margin: 7px 0 4px 0; display: inline-block;'>Actions: <span class='siac-queue-picker-icn' onclick='if (pdfLoading||noteLoading||pdfSearchOngoing) {{return;}}pycmd("siac-user-note-queue-picker {note_id}")'>\u2630</span>{schedule_dialog_btn}</div><br>
                            <a onclick='if (!pdfLoading && !modalShown) {{ noteLoading = true; greyoutBottom(); pycmd("{queue_btn_action}") }}' class='siac-clickable-anchor' style='font-size: 16px; font-weight: bold;' id='siac-first-in-queue-btn'>{queue_btn_text}</a>
                            {delay_btn}<br>
                            <a onclick='if (!pdfLoading && !modalShown) {{ noteLoading = true; greyoutBottom(); pycmd("siac-user-note-queue-read-random") }}' class='siac-clickable-anchor'>Random</a><span style='color: grey; user-select: none;'>&nbsp;|&nbsp;</span>
                            <a onclick='if (!pdfLoading && !modalShown) {{ modalShown = true; greyoutBottom(); pycmd("siac-eval index.ui.reading_modal.show_remove_dialog()");}}' class='siac-clickable-anchor'>Remove</a>
                        </div>
                        {queue_readings_list}
                        <div id='siac-queue-infobox-wrapper'>
                            <div id='siac-queue-infobox' onmouseleave='leaveQueueItem();'></div>
                        </div>
                        <div id='siac-pdf-bottom-tabs' style='display: inline-block; vertical-align: top; margin-left: 16px; user-select: none;'>
                            <a class='siac-clickable-anchor tab active' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} marks")' style='margin-right: 10px;'>Marks</a>
                            <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} related")' style='margin-right: 10px;'>Related</a>
                            <a class='siac-clickable-anchor tab' onclick='pycmd("siac-pdf-show-bottom-tab {note_id} info")'>Info</a> <br>
                            <div id='siac-pdf-bottom-tab'>
                                <div id='siac-marks-display' onclick='markClicked(event);'></div>
                            </div>
                        </div>
                    </div>
                </div>
        """

        editable            = not note.is_feed() and not note.is_pdf() and len(text) < 50000
        queue_info          = "Priority: %s" % (dynamic_sched_to_str(priority)) if note.is_in_queue() else "Unqueued."
        # queue_info_short = f"Queue [{note.position + 1}]" if note.is_in_queue() else "Unqueued"
        queue_info_short    = f"Priority" if note.is_in_queue() else "Unqueued"
        queue_readings_list = self.get_queue_head_display(queue, editable)

        params              = dict(note_id = note_id, time_str = time_str, queue_btn_text = queue_btn_text, queue_btn_action = queue_btn_action, queue_info = queue_info, queue_info_short = queue_info_short, 
        queue_readings_list = queue_readings_list, schedule_btns=schedule_btns, schedule_dialog_btn=schedule_dialog_btn, delay_btn=delay_btn )

        html                = html.format_map(params)

        return html

    def get_queue_head_display(self, queue: Optional[List[SiacNote]] = None, should_save: bool = False) -> str:
        """ This returns the html for the little list at the bottom of the reading modal which shows the first 5 items in the queue. """

        if queue is None:
            queue = _get_priority_list()
        if queue is None or len(queue) == 0:
            return "<div id='siac-queue-readings-list' style='display: inline-block; vertical-align: top; margin-left: 20px; user-select: none;'></div>"

        note_id             = self.note_id
        note                = self.note

        if not note.is_pdf() and not note.is_feed():
            should_save     = True

        config              = mw.addonManager.getConfig(__name__)
        hide                = config["pdf.queue.hide"]
        queue_head_readings = ""

        for ix, queue_item in enumerate(queue):

            should_greyout = "greyedout" if queue_item.id == int(note_id) else ""
            if not hide or queue_item.id == int(note_id) :
                qi_title = utility.text.trim_if_longer_than(queue_item.get_title(), 40) 
                qi_title = ihtml.escape(qi_title)
            else:
                qi_title = utility.text.trim_if_longer_than(re.sub("[^ ]", "?",queue_item.get_title()), 40)

            hover_actions       = "onmouseenter='showQueueInfobox(this, %s);' onmouseleave='leaveQueueItem(this);'" % (queue_item.id) if not hide else ""
            #if the note is a pdf or feed, show a loader on click
            pdf_or_feed         = queue_item.is_feed() or queue_item.is_pdf()
            clock               = clock_svg(len(should_greyout) > 0) if queue_item.is_scheduled() else ""
            should_show_loader  = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showLoader(\"siac-reading-modal-center\", \"Loading Note...\");' if pdf_or_feed else ""
            queue_head_readings +=  "<a oncontextmenu='queueLinkContextMenu(event, %s)' onclick='if (!pdfLoading && !modalShown) {%s  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note %s\"); hideQueueInfobox();}' class='siac-clickable-anchor %s' style='font-size: 12px; font-weight: bold;' %s >%s.%s %s</a><br>" % (queue_item.id, should_show_loader, queue_item.id, should_greyout, hover_actions, queue_item.position + 1, clock, qi_title)
            if ix > 3:
                break

        if hide:
            hide_btn = """<div style='display: inline-block; margin-left: 12px; color: grey;' class='blue-hover' onclick='unhideQueue(%s)'>(Show Items)</div>""" % note_id
        else:
            hide_btn = """<div style='display: inline-block; margin-left: 12px; color: grey;' class='blue-hover' onclick='hideQueue(%s)'>(Hide Items)</div>""" % note_id

        html = """
        <div id='siac-queue-readings-list' style='display: inline-block; vertical-align: top; margin-left: 20px; user-select: none;'>
            <div style='margin: 0px 0 1px 0; display: inline-block; color: lightgrey;'>Queue Head:</div>%s<br>
                %s
        </div>
        """ % (hide_btn, queue_head_readings)

        return html

    def schedule_btns(self, priority: int) -> str:
        """ Returns the html for the buttons that allow to quickly reschedule the current item in the reading modal. """

        note_id         = self.note_id
        priority        = 0 if priority is None else priority
        prio_verbose    = dynamic_sched_to_str(priority).replace("(", "(<b>").replace(")", "</b>)")

        return f"""
        <div id='siac-queue-sched-wrapper'>
            <div class='w-100' style='text-align: center; color: lightgrey; margin-top: 5px;'>
                Release to mark as <b>done.</b><br>
                <input type="range" min="0" max="100" value="{priority}" oninput='schedChange(this)' onchange='schedChanged(this, {note_id})' class='siac-prio-slider' style='margin-top: 12px;'/>
            </div>
            <div class='w-100' style='text-align: center; padding-top: 10px;'>
                <span style='font-size: 16px;' id='siac-sched-prio-val'>{prio_verbose}</span><br>
                <span style='font-size: 12px; color: grey;' id='siac-sched-prio-lbl'></span>
            </div>
        </div>
        """

    def pdf_viewer_html(self, source: str, title: str, priority: int) -> str:
        """ Returns the center area of the reading modal. Use this if the displayed note is a pdf. """
        
        nid                 = self.note_id
        dir                 = utility.misc.get_web_folder_path()
        config              = mw.addonManager.getConfig(__name__)
        urls                = config["searchUrls"]
        search_sources      = self.iframe_dialog(urls) if urls else ""
        marks_img_src       = utility.misc.img_src("mark-star-24px.png")
        marks_grey_img_src  = utility.misc.img_src("mark-star-lightgrey-24px.png")
        pdf_search_img_src  = utility.misc.img_src("magnify-24px.png")
        quick_sched         = self.quick_sched_btn(priority)
        extract             = ""
        
        if self.note.extract_start:
            if self.note.extract_start == self.note.extract_end:
                extract = f"<div class='siac-extract-marker'> Extract: P. {self.note.extract_start} </div>"
            else:
                extract = f"<div class='siac-extract-marker'> Extract: P. {self.note.extract_start} - {self.note.extract_end} </div>"

        html = """
            <div id='siac-pdf-overlay'>PAGE READ</div>
            <div id='siac-pdf-overlay-top'>
                <div id='siac-pdf-mark-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'><img src='{marks_img_src}' style='width: 17px; height: 17px; margin: 0;'/>
                    <div style='margin-left: 7px;'>
                        <div class='siac-mark-btn-inner siac-mark-btn-inner-1' onclick='pycmd("siac-pdf-mark 1 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Revisit</div>
                        <div class='siac-mark-btn-inner siac-mark-btn-inner-2' onclick='pycmd("siac-pdf-mark 2 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Hard</div>
                        <div class='siac-mark-btn-inner siac-mark-btn-inner-3' onclick='pycmd("siac-pdf-mark 3 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Info</div>
                        <div class='siac-mark-btn-inner siac-mark-btn-inner-4' onclick='pycmd("siac-pdf-mark 4 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>More Cards</div>
                        <div class='siac-mark-btn-inner siac-mark-btn-inner-5' onclick='pycmd("siac-pdf-mark 5 {nid} " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages)'>Bookmark</div>
                    </div> 
                </div>
                {extract}
                <div style='display: inline-block; vertical-align: top;' id='siac-pdf-overlay-top-lbl-wrap'></div>
            </div>
            <div id='siac-iframe-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")'>W
                <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 40px); text-align: center;'>Note: Not all sites allow embedding!</div>
                <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                    <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input> 
                    <br/>
                {search_sources}
                </div>
            </div>
            <div style='position: absolute; left: 0; bottom: 150px; text-align: center;'>
                <div style='color: lightgrey; border-color: grey; text-align:center;' data-id="0" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'>A</div>
                <br>
                <div style='background: #e65100;' data-id="1" data-color="#e65100" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'></div>
                <div style='background: #558b2f;' data-id="2" data-color="#558b2f" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'></div>
                <div style='background: #2196f3;' data-id="3" data-color="#2196f3" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'></div>
                <div style='background: #ffee58;' data-id="4" data-color="#ffee58" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'></div>
                <div style='background: #ab47bc;' data-id="5" data-color="#ab47bc" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-color-btn'></div>
                <br> 
                <div style='background: #e65100;' data-id="6" data-color="#e65100" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-ul-btn'></div>
                <div style='background: #558b2f;' data-id="7" data-color="#558b2f" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-ul-btn'></div>
                <div style='background: #2196f3;' data-id="8" data-color="#2196f3" onclick="Highlighting.onColorBtn(this)" class='siac-pdf-ul-btn'></div>
            </div>

            <div class='siac-btn siac-btn-dark' id='siac-pdf-search-btn' onclick='$(this).toggleClass("expanded"); onPDFSearchBtnClicked(this);'><img src='{pdf_search_img_src}' style='width: 16px; height: 16px;'/>
                <div id='siac-pdf-search-btn-inner' class='expanded-hidden white-hover' style='margin: 0 2px 0 5px; color: lightgrey; text-align: center;'>
                    <input style='width: 200px; border:none; background-color: #2f2f31; color: lightgrey; padding-left: 2px;' onclick='event.stopPropagation();' onkeyup='onPDFSearchInput(this.value, event);'/>
                    <div class='siac-btn siac-btn-dark' onclick='event.stopPropagation(); showPDFBottomRightNotification("Searching..."); nextPDFSearchResult(dir="left");'><b>&lt;</b></div>
                    <div class='siac-btn siac-btn-dark' onclick='event.stopPropagation(); showPDFBottomRightNotification("Searching..."); nextPDFSearchResult(dir="right");'><b>&gt;</b></div>
                </div>
            </div>
            <div class='siac-btn siac-btn-dark' id='siac-mark-jump-btn' onclick='$(this).toggleClass("expanded"); onMarkBtnClicked(this);'><img src='{marks_grey_img_src}' style='width: 16px; height: 16px;'/>
                <div id='siac-mark-jump-btn-inner' class='expanded-hidden white-hover' style='margin: 0 2px 0 5px; color: lightgrey; text-align: center;'></div>
            </div>
            {quick_sched_btn} 
            <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark' onclick='pycmd("siac-close-iframe")'>&times; &nbsp;Close Web</div>
            <div id='siac-pdf-top' data-pdfpath="{pdf_path}" data-pdftitle="{pdf_title}" data-pdfid="{nid}" onwheel='pdfMouseWheel(event);' style='overflow-y: hidden;'>
                <div id='siac-pdf-loader-wrapper' style='display: flex; justify-content: center; align-items: center; height: 100%; z-index: 7;'>
                    <div class='siac-pdf-loader' style=''>
                        <div> <div class='signal' style='margin-left: auto; margin-right: auto;'></div><br/><div id='siac-loader-text'>Loading PDF</div></div>
                    </div>
                </div>
                <canvas id="siac-pdf-canvas" style='z-index: 99999; display:inline-block;'></canvas>
                <div id="text-layer" style='display: none;' onmouseup='pdfKeyup(event);' onkeyup='pdfTextLayerMetaKey = false;' onclick='textlayerClicked(event, this);' class="textLayer"></div>
            </div>
            <iframe id='siac-iframe' sandbox='allow-scripts'></iframe>
            <div class='siac-reading-modal-button-bar-wrapper' style="">
                <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                    <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleReadingModalBars();'>&#x2195;</div>
                    <div class='siac-btn siac-btn-dark' style="margin-left: 2px; width: 18px;" onclick='pdfScaleChange("down");'>-</div>
                    <div class='siac-btn siac-btn-dark' style="width: 22px;" onclick='pdfFitToPage()'>&#8596;</div>
                    <div class='siac-btn siac-btn-dark' style="width: 18px;" onclick='pdfScaleChange("up");'>+</div>
                    <div class='siac-btn siac-btn-dark' onclick='initImageSelection()' style='margin-left: 5px;'><b>&#9986;</b></div>
                    <div class='siac-btn siac-btn-dark active' id='siac-pdf-tooltip-toggle' onclick='togglePDFSelect(this)' style='margin-left: 5px;'><div class='siac-search-icn-dark'></div></div>
                    <div class='siac-btn siac-btn-dark' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")' style='margin-left: 5px;'><b>&#9998; Note</b></div>
                </div>
                <div style='user-select:none; display: inline-block; position:relative; z-index: 2; padding: 0 5px 0 5px; background: #2f2f31;'>
                    <div class='siac-btn siac-btn-dark' onclick='pdfPageLeft();'><b>&lt;</b></div>
                    <span style='display: inline-block; text-align: center; width: 78px; user-select: none;' id='siac-pdf-page-lbl'>Loading...</span>
                    <div class='siac-btn siac-btn-dark' onclick='pdfPageRight();'><b>&gt;</b></div>
                </div>

                <div style='position: absolute; right: 0; display: inline-block; user-select: none;'>
                    <div style='position: relative; display: inline-block; width: 70px; margin-right: 7px;'>
                        <div id='siac-pdf-color-mode-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='width: calc(100% - 14px)'><span>Day</span>
                            <div class='siac-btn-small-dropdown-inverted click' style='height: 140px; top: -118px; left: -42px; width: 100px;'>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Day")'><b>Day</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Night")'><b>Night</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Sand")'><b>Sand</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Peach")'> <b>Peach</b> </div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Rose")'> <b>Rose</b> </div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Moss")'> <b>Moss</b> </div>
                                <div class='siac-dropdown-inverted-item' onclick='setPDFColorMode("Coral")'> <b>Coral</b> </div>
                            </div>
                        </div>
                    </div>
                    
                    <div id="siac-pdf-read-btn" class='siac-btn' style='margin-right: 7px; width: 65px;' onclick='togglePageRead({nid});'>\u2713&nbsp; Read</div>
                    <div style='position: relative; display: inline-block; width: 30px; margin-right: 7px;'>
                        <div id='siac-pdf-more-btn' class='siac-btn siac-btn-dark' onclick='$(this).toggleClass("expanded")' onmouseleave='$(this).removeClass("expanded")' style='width: calc(100% - 14px)'>...
                            <div class='siac-btn-small-dropdown-inverted click'>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-create-pdf-extract " + pdfDisplayed.numPages); event.stopPropagation();'><b>Extract ...</b></div>
                                <hr>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-jump-last-read {nid}"); event.stopPropagation();'><b>Last Read Page</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-jump-first-unread {nid}"); event.stopPropagation();'><b>First Unread Page</b></div>
                                <hr>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-read-up-to {nid} " + pdfDisplayedCurrentPage + " " + numPagesExtract()); markReadUpToCurrent();updatePdfProgressBar();event.stopPropagation();'><b>Mark Read up to current Pg.</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-display-range-input {nid} " + numPagesExtract()); event.stopPropagation();'><b>Mark Range ...</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-unread {nid}"); pagesRead = []; pdfHidePageReadMark(); updatePdfProgressBar();event.stopPropagation();'><b>Mark all as Unread</b></div>
                                <div class='siac-dropdown-inverted-item' onclick='pycmd("siac-mark-all-read {nid} " + numPagesExtract()); setAllPagesRead(); updatePdfProgressBar();event.stopPropagation();'>
                                    <b>Mark all as Read</b>
                                </div>
                            </div>
                        </div>
                    </div>
                    <input id="siac-pdf-page-inp" style="width: 50px;margin-right: 5px;" value="1" type="number" min="1" onkeyup="pdfJumpToPage(event, this);"></input>
                </div>
            </div>
            <div id='siac-pdf-br-notify'>
            </div>
            <script>
                greyoutBottom();
                $('#siac-pdf-color-mode-btn > span').first().text(pdfColorMode);
                $('#siac-pdf-top').addClass("siac-pdf-" + pdfColorMode.toLowerCase());
                if (pdfTooltipEnabled) {{
                    $('#siac-pdf-tooltip-toggle').addClass('active');
                }} else {{
                    $('#siac-pdf-tooltip-toggle').removeClass('active');
                }}
                $('.siac-pdf-color-btn[data-id=' + Highlighting.colorSelected.id + ']').addClass('active');
                $('.siac-pdf-ul-btn[data-id=' + Highlighting.colorSelected.id + ']').addClass('active');
            </script>
        """.format_map(dict(nid = nid, pdf_title = title, pdf_path = source, quick_sched_btn=quick_sched, search_sources=search_sources, marks_img_src=marks_img_src, 
        marks_grey_img_src=marks_grey_img_src, pdf_search_img_src=pdf_search_img_src, extract=extract))

        return html

    def tiny_mce_init_code(self) -> str:
        """ Code that should be executed when a text note is opened. """

        return """
            tinymce.init({
                selector: '#siac-text-top',
                plugins: 'preview paste importcss searchreplace autolink directionality code visualblocks visualchars link codesample table charmap hr nonbreaking toc insertdatetime advlist lists wordcount imagetools textpattern noneditable charmap quickbars',
                menubar: 'edit view insert format tools table',
                toolbar: 'undo redo | bold italic underline strikethrough | fontselect fontsizeselect formatselect | alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | forecolor backcolor removeformat | charmap | codesample | ltr rtl',
                toolbar_sticky: true,
                contextmenu: false,
                resize: false,
                statusbar: false,
                skin: "oxide-dark",
                content_css: "dark",
                importcss_append: true,
                quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote quickimage quicktable',
                noneditable_noneditable_class: "mceNonEditable",
                toolbar_drawer: 'sliding',
                setup: function (ed) {
                    ed.on('init', function(args) {
                        setTimeout(function() { $('.tox-notification__dismiss').first().trigger('click'); }, 200);
                        $('#siac-text-top_ifr').contents().find('body').css({
                                background: '#2f2f31'
                        });
                    });
                }
            });
        """


    def get_note_info_html(self) -> str:
        """ Returns the html that is displayed in the "Info" tab in the bottom bar of the reading modal. """

        note    = self.note
        created = note.created
        tags    = note.tags

        if note.reminder is None or len(note.reminder.strip()) == 0:
            schedule = "No Schedule"
        else:
            schedule = utility.date.schedule_verbose(note.reminder)

        if tags.startswith(" "):
            tags = tags[1:]

        html = f"""
            <table style='color: grey; min-width: 190px; line-height: 1.2;'>
                <tr><td>ID</td><td><b>{note.id}</b></td></tr>
                <tr><td>Created</td><td><b>{created}</b></td></tr>
                <tr><td>Schedule</td><td><b>{schedule}</b></td></tr>
                <tr>
                    <td style='padding-top: 10px;'>Tags</td>
                    <td style='padding-top: 10px;'>
                        <input type='text' style='width: 210px; background: #2f2f31; margin-left: 4px; padding-left: 4px; border: 1px solid grey; border-radius: 4px; color: lightgrey;' onfocusout='pycmd("siac-update-note-tags {note.id} " + this.value)' value='{tags}'></input>
                    </td>
                </tr>
            </table>
        """
        return html

    def iframe_dialog(self, urls: List[str]) -> str:
        """ HTML for the button on the top left of the center pane, which allows to search for text in an iframe. """

        search_sources  = "<table style='margin: 10px 0 10px 0; cursor: pointer; box-sizing: border-box; width: 100%;' onclick='event.stopPropagation();'>"
        ix              = 0
        direct_links    = ""

        for url in urls:
            name = os.path.dirname(url)
            if "[QUERY]" in url:
                search_sources += "<tr><td><label for='%s'>%s</label></td><td><input type='radio' name='url-radio' id='%s' data-url='%s' %s/></td></tr>" % ("url-rd-%d" % ix, name, "url-rd-%d" % ix, url, "checked" if ix == 0 else "")
                ix += 1
            else:
                direct_links += """<div class="siac-url-ch" onclick='event.stopPropagation(); $("#siac-iframe-btn").removeClass("expanded"); pycmd("siac-url-srch $$$dummy$$$%s");'>%s</div>""" % (url, name)

        search_sources += "</table>"
        if len(direct_links) > 0:
            search_sources += "<div style='margin-bottom: 5px;'>Direct Links:</div>"
            search_sources += direct_links

        return search_sources

    @js
    def display_schedule_dialog(self):
        """ Called when the currently opened note has a schedule and after it is finished reading. """

        delta = self.note.due_days_delta() if self.note.is_due_sometime() else 0

        if delta == 0:
            header = "This note was scheduled for <b>today</b>."
        elif delta == 1:
            header = "This note was scheduled for <b>yesterday</b>, but not marked as done."
        elif delta  == -1:
            header = "This note is due <b>tomorrow</b>."
        elif delta < -1:
            header = f"This note is due in <b>{abs(delta)}</b> days."
        else:
            header = f"This note was due <b>{delta}</b> days ago, but not marked as done."

        header +="<br>How do you want to proceed?"
        options = ""
      
        if delta < 0:
            options += """
                    <label class='blue-hover' for='siac-rb-1'>
                        <input id='siac-rb-1' type='radio' name='sched' data-pycmd="1" checked>
                        <span>Keep that Schedule</span>
                    </label><br>
            """
        else:
            if self.note.schedule_type() == "td":
                days_delta = int(self.note.reminder.split("|")[2][3:])
                s = "s" if days_delta > 1 else ""
                options += f"""
                    <label class='blue-hover' for='siac-rb-1'>
                        <input id='siac-rb-1' type='radio' name='sched' data-pycmd="1" checked>
                        <span>Show again in <b>{days_delta}</b> day{s}</span>
                    </label><br>
                """
            elif self.note.schedule_type() == "wd":
                weekdays_due    = [int(d) for d in self.note.reminder.split("|")[2][3:]]
                next_date_due   = utility.date.next_instance_of_weekdays(weekdays_due)
                weekday_name    = utility.date.weekday_name(next_date_due.weekday() + 1)
                options += f"""
                    <label class='blue-hover' for='siac-rb-1'>
                        <input id='siac-rb-1' type='radio' name='sched' data-pycmd="1" checked>
                        <span>Show again next <b>{weekday_name}</b></span>
                    </label><br>
                """
            elif self.note.schedule_type() == "id":
                days_delta = int(self.note.reminder.split("|")[2][3:])
                s = "s" if days_delta > 1 else ""
                options += f"""
                    <label class='blue-hover' for='siac-rb-1'>
                        <input id='siac-rb-1' type='radio' name='sched' data-pycmd="1" checked>
                        <span>Show again in <b>{days_delta}</b> day{s}</span>
                    </label><br>
                """

        options += """
                <label class='blue-hover' for='siac-rb-2'>
                    <input id='siac-rb-2' type='radio' name='sched' data-pycmd="2">
                    <span>Rem. Schedule, but keep in Queue</span>
                </label><br>
                <label class='blue-hover' for='siac-rb-3'>
                    <input id='siac-rb-3' type='radio' name='sched' data-pycmd="3">
                    <span>Remove from Queue</span>
                </label><br>
            """

        modal = f"""
            <div id='siac-schedule-dialog' class="siac-modal-small dark" style="text-align:center;">
                {header}

                <div class='siac-pdf-main-color-border-bottom siac-pdf-main-color-border-top' style='text-align: left; user-select: none; cursor: pointer; margin: 10px 0 10px 0; padding: 15px;'>
                  {options}

                </div>
                <div style='text-align: left;'>
                    <a class='siac-clickable-anchor' onclick='pycmd("siac-eval index.ui.reading_modal.show_schedule_change_modal()")'>Change Scheduling</a>
                    <div class='siac-btn siac-btn-dark' style='float: right;' onclick='scheduleDialogQuickAction()'>Ok</div>
                </div>

            </div>
        """
        return """modalShown=true;
            $('#siac-rm-greyout').show();
            if (document.getElementById('siac-schedule-dialog')) {
                $('#siac-schedule-dialog').replaceWith(`%s`);
            } else {
                $('#siac-reading-modal-center').append(`%s`);
            }
            """ % (modal, modal)


    @js
    def show_remove_dialog(self, nid: Optional[int] = None):
        """ Shows a dialog to either remove the current note from the queue or to delete it altogether. """

        if nid:
            note = get_note(nid)
        else:
            note = self.note

        title   = utility.text.trim_if_longer_than(note.get_title(), 40).replace("`", "")
        rem_cl  = "checked" if note.position is not None and note.position >= 0 else "disabled"
        del_cl  = "checked" if note.position is None or note.position < 0 else ""

        modal   = f"""
            <div id='siac-schedule-dialog' class="siac-modal-small dark" style="text-align:center;">
                Remove / delete this note?<br><br>
                {title}

                <div class='siac-pdf-main-color-border-bottom siac-pdf-main-color-border-top' style='text-align: left; user-select: none; cursor: pointer; margin: 10px 0 10px 0; padding: 15px;'>
                    <label class='blue-hover' for='siac-rb-1'>
                        <input id='siac-rb-1' type='radio' {rem_cl} name='del' data-pycmd="1">
                        <span>Remove from Queue</span>
                    </label><br>
                    <label class='blue-hover' for='siac-rb-2'>
                        <input id='siac-rb-2' type='radio' {del_cl} name='del' data-pycmd="2">
                        <span>Delete Note</span>
                    </label><br>

                </div>
                <div style='text-align: right;'>
                    <div class='siac-btn siac-btn-dark' style='margin-right: 10px;' onclick='$(this.parentNode.parentNode).remove(); modalShown = false; ungreyoutBottom(); $("#siac-rm-greyout").hide();'>Cancel</div>
                    <div class='siac-btn siac-btn-dark' onclick='removeDialogOk({note.id})'>Ok</div>
                </div>

            </div>
        """
        return """modalShown=true;
            $('#siac-timer-popup').hide();
            $('#siac-rm-greyout').show();
            $('#siac-reading-modal-center').append(`%s`);
            """ % (modal)

    @js
    def show_schedule_change_modal(self, unscheduled: bool = False):
        """ Show a modal that allows to change the schedule of the current note. """

        title = "Set a new Schedule" if not unscheduled else "This note had no schedule before."
        if not unscheduled:
            back_btn = """<a class='siac-clickable-anchor' onclick='pycmd("siac-eval index.ui.reading_modal.display_schedule_dialog()")'>Back</a>"""
        else:
            back_btn = """<a class='siac-clickable-anchor' onclick='pycmd("siac-eval index.ui.reading_modal.display_head_of_queue()")'>Proceed without scheduling</a>"""

        body = f"""
                {title}
                <div class='siac-pdf-main-color-border-bottom siac-pdf-main-color-border-top' style='text-align: left; user-select: none; cursor: pointer; margin: 10px 0 10px 0; padding: 15px;'>

                    <label class='blue-hover' for='siac-rb-4'>
                        <input id='siac-rb-4' type='radio' data-pycmd='4' checked name='sched'>
                        <span>Show again in [n] days:</span>
                    </label><br>
                    <div class='w-100' style='margin: 10px 0 10px 0;'>
                        <input id='siac-sched-td-inp' type='number' min='1' style='width: 70px; color: lightgrey; border: 2px outset #b2b2a0; background: transparent;'/>
                        <div class='siac-btn siac-btn-dark' style='margin-left: 15px;' onclick='document.getElementById("siac-sched-td-inp").value = 1;'>Tomorrow</div>
                        <div class='siac-btn siac-btn-dark' style='margin-left: 5px;' onclick='document.getElementById("siac-sched-td-inp").value = 7;'>In 7 Days</div>
                    </div>
                    <label class='blue-hover' for='siac-rb-5'>
                        <input id='siac-rb-5' type='radio'  data-pycmd='5' name='sched'>
                        <span>Show on Weekday(s):</span>
                    </label><br>
                    <div class='w-100' style='margin: 10px 0 10px 0;' id='siac-sched-wd'>
                        <label><input type='checkbox' style='vertical-align: middle;'/>M</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>T</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>W</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>T</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>F</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>S</label>
                        <label style='margin: 0 0 0 4px;'><input style='vertical-align: middle;' type='checkbox'/>S</label>
                    </div>

                    <label class='blue-hover' for='siac-rb-6'>
                        <input id='siac-rb-6' type='radio'  data-pycmd='6' name='sched'>
                        <span>Show every [n]th Day</span>
                    </label><br>
                    <div class='w-100' style='margin: 10px 0 10px 0;'>
                        <input id='siac-sched-id-inp' type='number' min='1' style='width: 70px; color: lightgrey; border: 2px outset #b2b2a0; background: transparent;'/>
                    </div>

                </div>
                <div style='text-align: left;'>
                    {back_btn}
                    <div class='siac-btn siac-btn-dark' style='float: right;' onclick='updateSchedule()'>Set Schedule</div>
                </div>
        """
        return f"""
            if (document.getElementById('siac-schedule-dialog')) {{
                document.getElementById("siac-schedule-dialog").innerHTML = `{body}`;
            }} else {{
                $('#siac-reading-modal-center').append(`<div id='siac-schedule-dialog' class="siac-modal-small dark" style="text-align:center;">{body}</div>`);
            }}
        """

    def schedule_note(self, option: int):
        """ Will update the schedule of the note according to the chosen option. 
            This function is called after an option in the dialog of display_schedule_dialog() has been selected. """

        delta       = self.note.due_days_delta()
        now         = utility.date.date_now_stamp()
        new_prio    = get_priority(self.note_id)

        if option == 1:
            if delta < 0:
                # keep schedule & requeue
                new_reminder = self.note.reminder
            else:
                if self.note.schedule_type() == "td":
                    # show again in n days
                    days_delta      = int(self.note.reminder.split("|")[2][3:])
                    next_date_due   = dt.now() + timedelta(days=days_delta)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|td:{days_delta}"

                elif self.note.schedule_type() == "wd":
                    # show again on next weekday instance
                    wd_part         = self.note.reminder.split("|")[2]
                    weekdays_due    = [int(d) for d in wd_part[3:]]
                    next_date_due   = utility.date.next_instance_of_weekdays(weekdays_due)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|{wd_part}"
                elif self.note.schedule_type() == "id":
                    # show again according to interval
                    days_delta      = int(self.note.reminder.split("|")[2][3:])
                    next_date_due   = dt.now() + timedelta(days=days_delta)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|id:{days_delta}"
        elif option == 2:
            #remove schedule & requeue
            new_reminder    = ""
        elif option == 3:
            # remove entirely from queue
            new_reminder    = ""
            new_prio        = 0

        update_reminder(self.note_id, new_reminder)
        update_priority_list(self.note_id, new_prio)
        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            self.display(nid)
        else:
            self._editor.web.eval("""
                onReadingModalClose();
            """)

    @js
    def show_theme_dialog(self):
        """ Display a modal to change the main color of the reader. """

        modal = f"""
            <div id='siac-schedule-dialog' class="siac-modal-small dark" style="text-align:center;">
                Change the main color of the reader.<br><br>
                <div style='user-select: none;'>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader.css")'>Orange</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_lightblue.css")'>Lightblue</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_khaki.css")'>Khaki</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_darkseagreen.css")'>Darkseagreen</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_tan.css")'>Tan</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_lightgreen.css")'>Lightgreen</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_lightsalmon.css")'>Lightsalmon</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_yellow.css")'>Yellow</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_crimson.css")'>Crimson</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_coral.css")'>Coral</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_steelblue.css")'>Steelblue</a><br>
                    <a class='siac-clickable-anchor' onclick='setPdfTheme("pdf_reader_lightsteelblue.css")'>Light Steelblue</a><br>
                </div>
                <br>
                <div style='text-align: right;'>
                    <div class='siac-btn siac-btn-dark' style='margin-right: 10px;' onclick='$(this.parentNode.parentNode).remove(); modalShown = false; ungreyoutBottom(); $("#siac-rm-greyout").hide();'>Ok</div>
                </div>

            </div>
        """
        return """modalShown=true;
            $('#siac-timer-popup').hide();
            $('#siac-rm-greyout').show();
            $('#siac-reading-modal-center').append(`%s`);
            """ % (modal)

    @js
    def show_img_field_picker_modal(self, img_src: str):
        """
            Called after an image has been selected from a PDF, should display all fields that are currently in the editor,
            let the user pick one, and on picking, insert the img into the field.
        """

        # if Image Occlusion add-on is there and enabled, add a button to directly open the IO dialog
        io      = ""
        if hasattr(self._editor, 'onImgOccButton') and mw.addonManager.isEnabled("1374772155"):
            io  = f"<div class='siac-btn siac-btn-dark' style='margin-right: 9px;' onclick='pycmd(`siac-cutout-io {img_src}`); $(this.parentNode).remove();'>Image Occlusion</div>"
        modal   = """ <div class="siac-modal-small dark" style="text-align:center;"><b>Append to:</b><br><br><div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br>%s<div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); pycmd('siac-remove-snap-image %s')">Cancel</div></div> """
        flds    = ""
        for i, f in enumerate(self._editor.note.model()['flds']):
            # trigger note update
            fld_update_js = "pycmd(`blur:%s:${currentNoteId}:${$(`.field:eq(%s)`).html()}`);" % (i,i)
            flds += """<span class="siac-field-picker-opt" onclick="$(`.field`).get(%s).innerHTML += `<img src='%s'/>`; $(this.parentNode.parentNode).remove(); %s">%s</span><br>""" % (i, img_src, fld_update_js, f["name"])
        modal = modal % (flds, io, img_src)
        return "$('#siac-reading-modal-center').append('%s');" % modal.replace("'", "\\'")

    @js
    def show_cloze_field_picker_modal(self, cloze_text: str):
        """
        Shows a modal that lists all fields of the current note.
        When a field is selected, the cloze text is appended to that field.
        """

        cloze_text  = cloze_text.replace("`", "").replace("\n", "")
        modal       = """ <div class="siac-modal-small dark" style="text-align:center;">
                        <b>Append to:</b><br><br>
                        <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                    </div> """
        flds        = ""

        for i, f in enumerate(self._editor.note.model()['flds']):
            flds += """<span class="siac-field-picker-opt" onclick="appendToField({0}, `{1}`);  $(this.parentNode.parentNode).remove();">{2}</span><br>""".format(i, cloze_text, f["name"])
        modal       = modal % (flds)

        return "$('#siac-pdf-tooltip').hide(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

    @js
    def show_iframe_overlay(self, url: Optional[str] = None):
        js = """
            if (pdfDisplayed) {
                document.getElementById('siac-pdf-top').style.display = "none";
            } else {
                document.getElementById('siac-text-top-wr').style.display = "none";
            }
            document.getElementById('siac-iframe').style.display = "block";
            document.getElementById('siac-close-iframe-btn').style.display = "block";
            iframeIsDisplayed = true;
        """
        if url is not None:
            js += """
                document.getElementById('siac-iframe').src = `%s`;
            """ % url
        return js

    @js
    def hide_iframe_overlay(self):
        js = """
            document.getElementById('siac-iframe').src = "";
            document.getElementById('siac-iframe').style.display = "none";
            document.getElementById('siac-close-iframe-btn').style.display = "none";
            if (pdfDisplayed) {
                document.getElementById('siac-pdf-top').style.display = "block";
            } else {
                document.getElementById('siac-text-top-wr').style.display = "block";
            }
            iframeIsDisplayed = false;
        """
        return js

    @js
    def show_web_search_tooltip(self, inp: str):
        """ Context: Text was selected in a pdf, magnifying glass was clicked in the tooltip. """

        inp             = utility.text.remove_special_chars(inp)
        inp             = inp.strip()
        if len(inp) == 0:
            return
        search_sources  = ""
        config          = mw.addonManager.getConfig(__name__)
        urls            = config["searchUrls"]

        if urls is not None and len(urls) > 0:
            for url in urls:
                if "[QUERY]" in url:
                    name = os.path.dirname(url)
                    search_sources += """<div class="siac-url-ch" onclick='pycmd("siac-url-srch $$$" + document.getElementById("siac-tt-ws-inp").value + "$$$%s"); $(this.parentNode.parentNode).remove();'>%s</div>""" % (url, name)

        modal = """ <div class="siac-modal-small dark" style="text-align:center;">
                        <input style="width: 100%%; border-radius: 3px; padding-left: 4px; box-sizing: border-box; background: #2f2f31; color: white; border-color: white;" id="siac-tt-ws-inp" value="%s"></input>
                        <br/>
                        <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden; cursor: pointer; margin-top: 15px;">%s</div><br><br>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                    </div> """  % (inp, search_sources)

        js = """
        $('#siac-iframe-btn').removeClass('expanded');
        $('#siac-pdf-tooltip').hide();
        $('#siac-reading-modal-center').append('%s');
        """ % modal.replace("\n", "").replace("'", "\\'")
        return js

    @js
    def update_reading_bottom_bar(self, nid: int):
        """ Refresh the bottom bar. """

        queue   = _get_priority_list()
        pos_lbl = ""
        if queue is not None and len(queue) > 0:
            try:
                pos = next(i for i,v in enumerate(queue) if v.id == nid)
            except:
                pos = -1
            pos_lbl     = "Priority: " + get_priority_as_str(nid)
            pos_lbl_btn = f"Priority" if pos >= 0 else "Unqueued"
        else:
            pos_lbl     = "Unqueued"
            pos_lbl_btn = "<b>Unqueued</b>"

        qd = self.get_queue_head_display(queue)
        return """
            document.getElementById('siac-queue-lbl').innerHTML = '%s';
            $('#siac-queue-lbl').fadeIn('slow');
            $('.siac-queue-sched-btn:first').html('%s');
            $('#siac-queue-readings-list').replaceWith(`%s`);
            """ % (pos_lbl, pos_lbl_btn, qd)

    @js
    def show_pdf_bottom_tab(self, note_id: int, tab: str):
        """ Context: Clicked on a tab (Marks / Related / Info) in the bottom bar. """

        tab_js = "$('.siac-clickable-anchor.tab').removeClass('active');"
        if tab == "marks":
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(0).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`<div id='siac-marks-display' onclick='markClicked(event);'></div>`;
            updatePdfDisplayedMarks()"""
        if tab == "info":
            html = self.get_note_info_html()
            html = html.replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(2).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""
        if tab == "related":
            html = self.get_related_notes_html()
            html = html.replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(1).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""

    def get_related_notes_html(self) -> str:
        """ Context: Clicked on 'Related' tab in the bottom bar. """

        note_id = self.note_id
        r       = get_related_notes(note_id)
        note    = get_note(note_id)
        html    = "" 
        ids     = set()
        res     = []

        if r.related_by_tags:
            for r1 in r.related_by_tags:
                res.append(r1) 
                ids.add(r1.id)
                if len(r.related_by_title) > 0:
                    i = r.related_by_title.pop(0)
                    if not i.id in ids:
                        res.append(i)
                if len(res) > 20:
                    break
        if len(res) < 20 and len(r.related_by_title) > 0:
            for r2 in r.related_by_title:
                if not r2.id in ids:
                    res.append(r2)
                    if len(res) >= 20:
                        break
        
        if len(res) < 20 and len(r.related_by_folder) > 0:
            for r3 in r.related_by_folder:
                if not r3.id in ids:
                    res.append(r3)
                    if len(res) >= 20:
                        break

        for rel in res[:20]:
            if rel.id == note_id:
                continue
            title               = utility.text.trim_if_longer_than(rel.get_title(), 70)
            pdf_or_feed         = rel.is_pdf() or rel.is_feed()
            should_show_loader  = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showLoader(\"siac-reading-modal-center\", \"Loading Note...\");' if pdf_or_feed else ""
            html                = f"{html}<div class='siac-related-notes-item' onclick='if (!pdfLoading) {{ {should_show_loader}  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note {rel.id}\"); }}'>{title}</div>"
        return html


    def get_queue_infobox(self, note: SiacNote, read_stats: Tuple[Any, ...]) -> str:
        """ Returns the html that is displayed in the tooltip which appears when hovering over an item in the queue head. """

        diff        = datetime.datetime.now() - datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
        time_str    = "Created %s ago." % utility.misc.date_diff_to_string(diff)

        # pagestotal might be None (it is only available if at least one page has been read)
        if read_stats[2] is not None:
            prog_bar    = self.pdf_prog_bar(read_stats[0], read_stats[2])
            pages_read  = "<div style='width: 100%%; margin-top: 3px; font-weight: bold; text-align: center; font-size: 20px;'>%s / %s</div>" % (read_stats[0], read_stats[2])
        else:
            text_len    = f"{len(note.text.split())} Words" if note.text is not None else "Empty"
            prog_bar    = ""
            pages_read  = f"<div style='width: 100%; margin-top: 7px; font-weight: bold; text-align: center; font-size: 16px;'>Text Note, {text_len}</div>"

        html = """
            <div style='box-sizing: border-box; width: 100%; height: 100%; padding: 10px; display: inline-block; position: relative; vertical-align: top;'>
                <div style='width: 100%; text-align:center; white-space: nowrap; overflow: hidden; font-weight: bold; vertical-align: top; text-overflow: ellipsis;'>{title}</div>
                <div style='width: 100%; text-align:center; white-space: nowrap; overflow: hidden; color: lightgrey;vertical-align: top;'>{time_str}</div>
                {pages_read}
                <div style='width: calc(100%); padding: 5px 0 10px 0; text-align: center;'>
                    <div style='display: inline-block; vertical-align: bottom;'>
                        {prog_bar}
                    </div>
                </div>
            </div>
        
        """.format_map(dict(title = note.get_title(), pages_read=pages_read, time_str= time_str, prog_bar= prog_bar, nid = note.id))
        return html
    
    
    def pdf_prog_bar(self, read: Optional[int], read_total: Optional[int]) -> str:
        """ HTML for the progress bar in the top bar of the reader. """

        if read is not None and read_total is not None:
            perc        = int(read * 10.0 / read_total)
            perc_100    = int(read * 100.0 / read_total)
            prog_bar    = str(perc_100) + " % &nbsp;"

            for x in range(0, 10):
                if x < perc:
                    prog_bar = f"{prog_bar}<div class='siac-prog-sq-filled'></div>"
                else:
                    prog_bar = f"{prog_bar}<div class='siac-prog-sq'></div>"
            return prog_bar
        else:
            return ""

    @js
    def mark_range(self, start: int, end: int, pages_total: int, current_page: int):
        if start <= 0:
            start = 1
        if self.note.extract_start is not None and start < self.note.extract_start:
            start = self.note.extract_start
        if self.note.extract_start is None and end > pages_total:
            end = pages_total
        if self.note.extract_start is not None and end > self.note.extract_end:
            end = self.note.extract_end
        if end <= start or (self.note.extract_start is None and start >= pages_total) or (self.note.extract_start is not None and start >= pages_total + self.note.extract_start):
            return

        mark_range_as_read(self.note_id, start, end, pages_total)

        pages_read  = get_read_pages(self.note_id)
        js          = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])
        js          = f"pagesRead = [{js}];"

        if current_page >= start and current_page <= end:
            js += "pdfShowPageReadMark();"

        return f"{js}updatePdfProgressBar();"

    @js
    def display_cloze_modal(self, editor: Editor, selection: str, extracted: List[str]):
        s_html = "<table style='margin-top: 5px; font-size: 15px;'>"
        sentences = [s for s in extracted if len(s) < 300 and len(s.strip()) > 0]
        if len(sentences) == 0:
            for s in extracted:
                if len(s) >= 300:
                    f = utility.text.try_find_sentence(s, selection)
                    if f is not None and len(f) < 300:
                        sentences.append(f)

        if len(sentences) > 0 and sentences != [""]:
            selection = re.sub("  +", " ", selection).strip()
            for sentence in sentences:
                sentence = re.sub("  +", " ", sentence).strip()
                sentence = sentence.replace(selection, " <span style='color: lightblue;'>{{c1::%s}}</span> " % selection)

                # needs cleaning
                sentence = sentence.replace("  ", " ").replace("</span> ,", "</span>,")
                sentence = re.sub(" ([\"“”\\[(]) <span", " \\1<span", sentence)
                sentence = re.sub("</span> ([\"”\\]):])", "</span>\\1", sentence)
                sentence = re.sub("</span> -([^ \\d])", "</span>-\\1", sentence)
                sentence = re.sub("(\\S)- <span ", "\\1-<span ", sentence)
                sentence = re.sub(r"([^\\d ])- ([^\d])", r"\1\2", sentence)
                sentence = re.sub(" [\"“”], [\"“”] ?", "\", \"", sentence)
                sentence = re.sub(" [\"“”], ", "\", ", sentence)
                sentence = re.sub(": [\"“”] ", ": \"", sentence)
                sentence = sentence.replace("[ ", "[")
                sentence = sentence.replace(" ]", "]")
                sentence = re.sub(" ([,;:.]) ", r"\1 ", sentence)
                sentence = re.sub(r"\( (.) \)", r"(\1)", sentence)
                sentence = re.sub(" ([?!.])$", r"\1", sentence)
                sentence = re.sub("^[:.?!,;)] ", "", sentence)
                sentence = re.sub("^\\d+ ?[:\\-.,;] ([A-ZÖÄÜ])", r"\1", sentence)

                sentence = re.sub(" ([\"“”])([?!.])$", r"\1\2", sentence)

                s_html += "<tr class='siac-cl-row'><td><div contenteditable class='siac-pdf-main-color'>%s</div></td><td><input type='checkbox' checked/></td></tr>" % (sentence.replace("`", "&#96;"))
            s_html += "</table>"
            btn_html = """document.getElementById('siac-pdf-tooltip-bottom').innerHTML = `
                                <div style='margin-top: 8px;'>
                                <div class='siac-btn siac-btn-dark' onclick='pycmd("siac-fld-cloze " +$(".siac-cl-row div").first().text());' style='margin-right: 15px;'>Send to Field</div>
                                <div class='siac-btn siac-btn-dark' onclick='generateClozes();'>Generate</div>
                                </div>
                    `;"""

        else:
            s_html = "<br><center>Sorry, could not extract any sentences.</center>"
            btn_html = ""

        return """
                document.getElementById('siac-pdf-tooltip-results-area').innerHTML = `%s`;
                document.getElementById('siac-pdf-tooltip-top').innerHTML = `Found <b>%s</b> sentence(s) around selection: <br/><span style='color: lightgrey;'>(Click inside to edit, <i>Ctrl+Shift+C</i> to add new Clozes)</span>`;
                document.getElementById('siac-pdf-tooltip-searchbar').style.display = "none";
                %s
                """ % (s_html, len(sentences), btn_html)

    @js
    def notification(self, html: str, on_ok: Optional[str] = None):
        if on_ok is None:
            on_ok = ""
        modal = f""" <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                        {html}
                        <br/> <br/>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); $('#siac-rm-greyout').hide(); {on_ok}">&nbsp; Ok &nbsp;</div>
                    </div> """
        return """$('#siac-pdf-tooltip').hide();
                $('.siac-modal-small').remove();
                $('#siac-rm-greyout').show();
                $('#siac-reading-modal-center').append('%s');""" % modal.replace("\n", "").replace("'", "\\'")

    @js
    def update_bottom_bar_positions(self, nid: int, new_index: int, queue_len: int):
        queue_readings_list = self.get_queue_head_display(nid).replace("`", "\\`")
        priority_str = get_priority_as_str(nid)
        return f"""
            document.getElementById('siac-queue-lbl').innerHTML = 'Priority: {priority_str}';
            $('#siac-queue-lbl').fadeIn('slow');
            $('.siac-queue-sched-btn:first').html('Priority');
            $('#siac-queue-readings-list').replaceWith(`{queue_readings_list}`);
        """

    @js
    def show_timer_elapsed_popup(self, nid: int):
        """
            Shows the little popup that is displayed when the timer in the reading modal finished.
        """
        read_today_count    = get_read_today_count()
        added_today_count   = utility.misc.count_cards_added_today()
        html = """
        <div style='margin: 0 0 10px 0;'>
            <div style='text-align: center; vertical-align: middle; line-height: 50px; font-weight: bold; font-size: 40px; color: #2496dc;'>
                &#10711;
            </div>
            <div style='text-align: center; vertical-align: middle; line-height: 50px; font-weight: bold; font-size: 20px;'>
                Time is up!
            </div>
        </div>
        <div style='margin: 10px 0 25px 0; text-align: center; color: lightgrey;'>
            Read <b>%s</b> %s today.<br>
            Added <b>%s</b> %s today.
        </div>
        <div style='text-align: center; margin-bottom: 8px;'>
            Start:
        </div>
        <div style='text-align: center;'>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(5);'>&nbsp;5m&nbsp;</div>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(15);'>&nbsp;15m&nbsp;</div>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(30);'>&nbsp;30m&nbsp;</div>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(60);'>&nbsp;60m&nbsp;</div>
        </div>
        <div style='text-align: center; margin-top: 20px;'>
            <div class='siac-btn siac-btn-dark' onclick='this.parentNode.parentNode.style.display="none";'>Don't Start</div>
        </div>
        """ % (read_today_count, "page" if read_today_count == 1 else "pages", added_today_count, "card" if added_today_count == 1 else "cards")
        return "$('#siac-timer-popup').html(`%s`); $('#siac-timer-popup').show();" % html


    @js
    def jump_to_last_read_page(self):
        return """
            if (pagesRead && pagesRead.length) {
                pdfDisplayedCurrentPage = Math.max(...pagesRead);
                rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
            }
        """
    @js
    def jump_to_first_unread_page(self):
        return """
            if (pdfDisplayed) {
                let start = pdfExtract ? pdfExtract[0] : 1;
                for (var i = start; i < start + numPagesExtract(); i++) {
                    if (!pagesRead || pagesRead.indexOf(i) === -1) {
                        pdfDisplayedCurrentPage = i;
                        rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
                        break;
                    }
                }
            }
        """
    

    #
    # highlights
    #

    def show_highlights_for_page(self, page: int):
        highlights = get_highlights(self.note_id, page)
        if highlights is not None and len(highlights) > 0:
            js = ""
            for rowid, nid, page, type, grouping, x0, y0, x1, y1, text, data, created in highlights:
                text = text.replace("`", "")
                js = f"{js},[{x0},{y0},{x1},{y1},{type},{rowid}, `{text}`]"
            js = js[1:]
            self._editor.web.eval("Highlighting.current = [%s]; Highlighting.displayHighlights();" % js)



class ReadingModalSidebar():

    def __init__(self):

        self._editor                    : Editor                = None
        self.tab_displayed              : str                   = "fields"

        # cache last results to display when the tab is reopened
        self.browse_tab_last_results    : Optional[Tuple[Any, ...]]  = None
        self.pdfs_tab_last_results      : Optional[Tuple[Any, ...]]  = None

        #
        # Pagination
        #
        self.page                       : int                   = 1
        self.last_results               : Optional[Tuple[Any, ...]]  = None
        self.page_size                  :int                    = 100

    def set_editor(self, editor: Editor):
        self._editor = editor


    def print(self, results: List[IndexNote], stamp: str = "", query_set: List[str] = []):
        self.last_results   = results
        self.last_stamp     = stamp
        self.last_query_set = query_set
        self.show_page(1)

    def show_page(self, page: int):
        self.page = page
        if self.last_results is not None:
            to_print = self.last_results[(page- 1) * self.page_size: page * self.page_size]
            if self.tab_displayed == "browse":
                self.browse_tab_last_results = (self.last_results, self.last_stamp, self.last_query_set)
                self._print_sidebar_search_results(to_print, self.last_stamp, self.last_query_set)
            elif self.tab_displayed == "pdfs":
                self.pdfs_tab_last_results = self.last_results
                self._print_sidebar_results_title_only(to_print)


    def show_fields_tab(self):
        if self.tab_displayed == "fields":
            return
        self.tab_displayed = "fields"
        self._editor.web.eval("""
            $('#siac-left-tab-browse,#siac-left-tab-pdfs').remove();
            document.getElementById("fields").style.display = 'block';
        """)


    def show_browse_tab(self):
        if self.tab_displayed == "browse":
            return
        self.tab_displayed = "browse"
        self._editor.web.eval(f"""
            document.getElementById("fields").style.display = 'none';
            $('#siac-left-tab-browse,#siac-left-tab-pdfs').remove();
            $(`
                <div id='siac-left-tab-browse' style='display: flex; flex-direction: column;'>
                    <div class='siac-pdf-main-color-border-bottom' style='flex: 0 auto; padding: 5px 0 5px 0; user-select: none;'>
                        <strong style='color: grey;'>Last: </strong>
                        <strong class='blue-hover' style='color: grey; margin-left: 10px;' onclick='pycmd("siac-pdf-sidebar-last-addon")'>Add-on</strong>
                        <strong class='blue-hover' style='color: grey; margin-left: 10px;' onclick='pycmd("siac-pdf-sidebar-last-anki")'>Anki</strong>
                    </div>
                    <div id='siac-left-tab-browse-results' style='flex: 1 1 auto; overflow-y: auto; padding: 0 5px 0 0; margin: 10px 0 5px 0;'>
                    </div>
                    <div style='flex: 0 auto; padding: 5px 0 5px 0;'>
                        <input type='text' style='width: 100%; box-sizing: border-box;' onkeyup='pdfLeftTabAnkiSearchKeyup(this.value, event);'/>
                    </div>
                </div>
            `).insertBefore('#siac-reading-modal-tabs-left');
        """)
        if self.browse_tab_last_results is not None:
            self.print(self.browse_tab_last_results[0], self.browse_tab_last_results[1], self.browse_tab_last_results[2])
        else:
            self._editor.web.eval("pycmd('siac-pdf-sidebar-last-anki')")

    def show_pdfs_tab(self):
        if self.tab_displayed == "pdfs":
            return
        self.tab_displayed = "pdfs"
        self._editor.web.eval(f"""
            document.getElementById("fields").style.display = 'none';
            $('#siac-left-tab-browse,#siac-left-tab-pdfs').remove();
            $(`
                <div id='siac-left-tab-pdfs' style='display: flex; flex-direction: column;'>
                    <div class='siac-pdf-main-color-border-bottom' style='flex: 0 auto; padding: 5px 0 5px 0; user-select: none;'>
                        <strong class='blue-hover' style='color: grey; margin-left: 10px;' onclick='pycmd("siac-pdf-sidebar-pdfs-in-progress")'>In Progress</strong>
                        <strong class='blue-hover' style='color: grey; margin-left: 10px;' onclick='pycmd("siac-pdf-sidebar-pdfs-unread")'>Unread</strong>
                    </div>
                    <div id='siac-left-tab-browse-results' style='flex: 1 1 auto; overflow-y: auto; padding: 0 5px 0 0; margin: 10px 0 5px 0;'>
                    </div>
                    <div style='flex: 0 auto; padding: 5px 0 5px 0;'>
                        <input type='text' style='width: 100%; box-sizing: border-box;' onkeyup='pdfLeftTabPdfSearchKeyup(this.value, event);'/>
                    </div>
                </div>
            `).insertBefore('#siac-reading-modal-tabs-left');
        """)
        if self.pdfs_tab_last_results is not None:
            self.print(self.pdfs_tab_last_results)
        else:
            self._editor.web.eval("pycmd('siac-pdf-sidebar-pdfs-in-progress')")


    def _print_sidebar_search_results(self, results: List[Printable], stamp: str, query_set: List[str]):
        """
            Print the results of the browse tab.
        """
        if results:
            limit   = get_config_value_or_default("pdfTooltipResultLimit", 50)
            html    = self._sidebar_search_results(results[:limit], query_set)
            self._editor.web.eval("""
                document.getElementById('siac-left-tab-browse-results').innerHTML = `%s`;
                document.getElementById('siac-left-tab-browse-results').scrollTop = 0;
            """ % html)
        else:
            if not query_set:
                message = "Query was empty after cleaning."
            else:
                message = "Nothing found for query: <br/><br/><i>%s</i>" % (utility.text.trim_if_longer_than(" ".join(query_set), 200))

            self._editor.web.eval("""
                document.getElementById('siac-left-tab-browse-results').innerHTML = `%s`;
            """ % message)

    def _print_sidebar_results_title_only(self, results: List[SiacNote]):
        """ Print the results of the pdfs tab. """

        if not results:
            return
        html    = ""
        limit   = get_config_value_or_default("pdfTooltipResultLimit", 50)

        for note in results[:limit]:
            should_show_loader = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showLoader(\"siac-reading-modal-center\", \"Loading Note...\");' if note.is_pdf() else ""
            html = f"{html}<div class='siac-note-title-only' onclick='if (!pdfLoading) {{{should_show_loader}  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note {note.id}\"); hideQueueInfobox();}}'>{note.get_title()}</div>"

        html    = html.replace("`", "\\`")

        self._editor.web.eval(f"document.getElementById('siac-left-tab-browse-results').innerHTML = `{html}`;")



    def _sidebar_search_results(self, db_list: List[IndexNote], query_set: List[str]) -> str:
        html                        = ""
        epochTime                   = int(time.time() * 1000)
        timeDiffString              = ""
        newNote                     = ""
        lastNote                    = ""
        nids                        = [r.id for r in db_list]
        show_ret                    = get_config_value_or_default("showRetentionScores", True)
        fields_to_hide_in_results   = get_config_value_or_default("fieldsToHideInResults", {})
        remove_divs                 = get_config_value_or_default("removeDivsFromOutput", False)
        if show_ret:
            retsByNid               = getRetentions(nids)
        ret                         = 0
        highlighting                = get_config_value_or_default("highlighting", True)

        for counter, res in enumerate(db_list):
            ret = retsByNid[int(res.id)] if show_ret and int(res.id) in retsByNid else None
            if ret is not None:
                retMark = "background: %s; color: black;" % (utility.misc._retToColor(ret))
                retInfo = """<div class='retMark' style='%s'>%s</div>
                                """ % (retMark, int(ret))
            else:
                retInfo = ""

            lastNote    = newNote
            text        = res.get_content()

            # hide fields that should not be shown
            if str(res.mid) in fields_to_hide_in_results:
                text = "\u001f".join([spl for i, spl in enumerate(text.split("\u001f")) if i not in fields_to_hide_in_results[str(res.mid)]])

            #remove <div> tags if set in config
            if remove_divs and res.note_type != "user":
                text = utility.text.remove_divs(text)

            if highlighting and query_set is not None:
                text = utility.text.mark_highlights(text, query_set)

            text        = utility.text.cleanFieldSeparators(text).replace("\\", "\\\\").replace("`", "\\`").replace("$", "&#36;")
            text        = utility.text.try_hide_image_occlusion(text)
            #try to put fields that consist of a single image in their own line
            text        = utility.text.newline_before_images(text)
            template    = noteTemplateSimple if res.note_type == "index" else noteTemplateUserNoteSimple
            newNote     = template.format(
                counter=counter+1,
                nid=res.id,
                edited="",
                mouseup="",
                text=text,
                ret=retInfo,
                tags=utility.tags.build_tag_string(res.tags, False, False, maxLength = 25, maxCount = 2),
                creation="")
            html += newNote
        return html
