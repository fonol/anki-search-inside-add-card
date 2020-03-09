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
import datetime
import time
import sys
from aqt import mw
from aqt.utils import showInfo

import utility.tags
import utility.text
import utility.misc

try:
    from .tag_find import get_most_active_tags
    from .state import get_index, check_index, set_deck_map
    from .notes import get_note, _get_priority_list, get_all_tags, get_read_pages, get_pdf_marks, insert_pages_total, get_read_today_count, mark_range_as_read
    from .web.html import *
    from .internals import js, requires_index_loaded, perf_time
    from .config import get_config_value_or_default
except:
    from tag_find import get_most_active_tags
    from state import get_index, check_index, set_deck_map
    from notes import get_note, _get_priority_list, get_all_tags, get_read_pages, get_pdf_marks, insert_pages_total, get_read_today_count
    from web.html import *
    from internals import js, requires_index_loaded, perf_time
    from config import get_config_value_or_default

class ReadingModal:

    def __init__(self):
        self.note_id = None
        self.note = None
        self.editor = None

    def reset(self):
        self.note_id = None
        self.note = None

    @requires_index_loaded
    def display(self, note_id):

        index = get_index()
        note = get_note(note_id)

        self.note_id = note_id
        self.note = note

        html = get_reading_modal_html(note)
        index.ui.show_in_large_modal(html)
        # if source is a pdf file path, try to display it
        if note.is_pdf():
            if utility.misc.file_exists(note.source):
                self._display_pdf(note.source.strip(), note_id)
            else:
                message = "Could not load the given PDF.<br>Are you sure the path is correct?"
                self.notification(message)

    @js
    def show_width_picker(self):
        html = """
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 10")'><b>10 - 90</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 15")'><b>15 - 85</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 25")'><b>25 - 75</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 33")'><b>33 - 67</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 40")'><b>40 - 60</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 50")'><b>50 - 50</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 60")'><b>60 - 40</b></div>
            <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 67")'><b>67 - 33</b></div>
        """

        modal = """
            <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                <b>Left Side - Right Side</b>
                    <br><br>
                <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div>
                    <br><br>
                <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Close</div>
            </div> 
        """ % html
        return "$('#siac-reading-modal-center').append(`%s`)" % modal

    @js
    def display_read_range_input(self, note_id, num_pages):
        on_confirm= """ if (document.getElementById('siac-range-input-min').value && document.getElementById('siac-range-input-max').value) {
        pycmd('siac-user-note-mark-range %s ' + document.getElementById('siac-range-input-min').value 
                + ' ' + document.getElementById('siac-range-input-max').value 
                + ' ' + pdfDisplayed.numPages
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
    def reload_bottom_bar(self, note_id=None):
        """
            Called after queue picker dialog has been closed without opening a new note.
        """
        if note_id is not None:

            note = get_note(note_id)
            html = get_reading_modal_bottom_bar(note)
            html = html.replace("`", "\\`")
            return "$('#siac-reading-modal-bottom-bar').replaceWith(`%s`); updatePdfDisplayedMarks();" % html
        
        else:
            return """if (document.getElementById('siac-reading-modal').style.display !== 'none' && document.getElementById('siac-reading-modal-top-bar')) { 
                        pycmd('siac-reload-reading-modal-bottom '+ $('#siac-reading-modal-top-bar').data('nid')); 
                    }"""
    

    def _display_pdf(self, full_path, note_id):
        base64pdf = utility.misc.pdf_to_base64(full_path)
        blen = len(base64pdf)

        #pages read are stored in js array [int]
        pages_read = get_read_pages(note_id)        
        pages_read_js = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])
        
        #marks are stored in two js maps, one with pages as keys, one with mark types (ints) as keys
        marks = get_pdf_marks(note_id)
        js_maps = utility.misc.marks_to_js_map(marks)
        marks_js = "pdfDisplayedMarks = %s; pdfDisplayedMarksTable = %s;" % (js_maps[0], js_maps[1]) 
        
        # pages read are ordered by date, so take last
        last_page_read = pages_read[-1] if len(pages_read) > 0 else 1

        addon_id = utility.misc.get_addon_id()
        port = mw.mediaServer.getPort()

        init_code = """
            pdfLoading = true;
            var bstr = atob(b64);
            var n = bstr.length;
            var arr = new Uint8Array(n);
            while(n--){ 
                arr[n] = bstr.charCodeAt(n);
            }
            var file = new File([arr], "placeholder.pdf", {type : "application/pdf" });
            var fileReader = new FileReader();
            pagesRead = [%s];
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
                var typedarray = new Uint8Array(fileReader.result);
                var loadingTask = pdfjsLib.getDocument(typedarray, {nativeImageDecoderSupport: 'display'});
                loadingTask.promise.catch(function(error) {
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
                        $('#siac-pdf-loader-wrapper').remove();
                        document.getElementById('siac-pdf-top').style.overflowY = 'auto';

                        if (pagesRead.length === pdf.numPages) {
                            pdfDisplayedCurrentPage = 1;
                            queueRenderPage(1, true, true, true);
                        } else {
                            queueRenderPage(pdfDisplayedCurrentPage, true, true, true);
                        }
                        updatePdfProgressBar();
                        if (pagesRead.length === 0) { pycmd('siac-insert-pages-total %s ' + pdf.numPages); }
                        fileReader = null;
                });
            };
            fileReader.onload = (e) => { loadFn(0); };

            fileReader.readAsArrayBuffer(file);
            b64 = ""; arr = null; bstr = null; file = null;
        """ % (pages_read_js, marks_js, port, addon_id, last_page_read, note_id)
        #send large files in multiple packets
        page = self.editor.web.page()
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



    @js
    def show_img_field_picker_modal(self, img_src):
        """
            Called after an image has been selected from a PDF, should display all fields that are currently in the editor,
            let the user pick one, and on picking, insert the img into the field.
        """
        # if Image Occlusion add-on is there and enabled, add a button to directly open the IO dialog
        io = ""
        if hasattr(self.editor, 'onImgOccButton') and mw.addonManager.isEnabled("1374772155"):
            io = f"<div class='siac-btn siac-btn-dark' style='margin-right: 9px;' onclick='pycmd(`siac-cutout-io {img_src}`); $(this.parentNode).remove();'>Image Occlusion</div>" 
        modal = """ <div class="siac-modal-small dark" style="text-align:center;"><b>Append to:</b><br><br><div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br>%s<div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); pycmd('siac-remove-snap-image %s')">Cancel</div></div> """
        flds = ""
        for i, f in enumerate(self.editor.note.model()['flds']):
            # trigger note update
            fld_update_js = "pycmd(`blur:%s:${currentNoteId}:${$(`.field:eq(%s)`).html()}`);" % (i,i)
            flds += """<span class="siac-field-picker-opt" onclick="$(`.field`).get(%s).innerHTML += `<img src='%s'/>`; $(this.parentNode.parentNode).remove(); %s">%s</span><br>""" % (i, img_src, fld_update_js, f["name"])
        modal = modal % (flds, io, img_src)
        return "$('#siac-reading-modal-center').append('%s');" % modal.replace("'", "\\'")

    @js
    def show_cloze_field_picker_modal(self, cloze_text):
        """
        Shows a modal that lists all fields of the current note.
        When a field is selected, the cloze text is appended to that field.
        """
        cloze_text = cloze_text.replace("`", "").replace("\n", "")
        modal = """ <div class="siac-modal-small dark" style="text-align:center;">
                        <b>Append to:</b><br><br>
                        <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                    </div> """
        flds = ""
        for i, f in enumerate(self.editor.note.model()['flds']):
            flds += """<span class="siac-field-picker-opt" onclick="appendToField({0}, `{1}`);  $(this.parentNode.parentNode).remove();">{2}</span><br>""".format(i, cloze_text, f["name"])
        modal = modal % (flds)
        return "$('#siac-pdf-tooltip').hide(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

    @js
    def show_iframe_overlay(self, url=None):
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
    def show_web_search_tooltip(self, inp):
        inp = utility.text.remove_special_chars(inp)
        inp = inp.strip()
        if len(inp) == 0:
            return
        search_sources = ""
        config = mw.addonManager.getConfig(__name__)
        urls = config["searchUrls"]
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
                    </div> """% (inp, search_sources)
        
        js = """
        $('#siac-iframe-btn').removeClass('expanded'); 
        $('#siac-pdf-tooltip').hide(); 
        $('#siac-reading-modal-center').append('%s');
        """ % modal.replace("\n", "").replace("'", "\\'")
        return js

    @js
    def update_reading_bottom_bar(self, nid):
        queue = _get_priority_list()
        pos_lbl = ""
        if queue is not None and len(queue) > 0:
            try:
                pos = next(i for i,v in enumerate(queue) if v.id == nid)
            except:
                pos = -1
            pos_lbl = "Priority: " + get_priority_as_str(nid)
            pos_lbl_btn = "In Queue" if pos >= 0 else "Unqueued"
        else:
            pos_lbl = "Unqueued"
            pos_lbl_btn = "<b>Unqueued</b>"

        qd = get_queue_head_display(nid, queue)
        return """
            document.getElementById('siac-queue-lbl').innerHTML = '%s';
            $('#siac-queue-lbl').fadeIn('slow');
            $('.siac-queue-sched-btn:first').html('%s');
            $('#siac-queue-readings-list').replaceWith(`%s`);
            """ % (pos_lbl, pos_lbl_btn, qd)

    @js
    def show_pdf_bottom_tab(self, note_id, tab):
        tab_js = "$('.siac-clickable-anchor.tab').removeClass('active');"
        if tab == "marks":
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(0).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`<div id='siac-marks-display' onclick='markClicked(event);'></div>`;
            updatePdfDisplayedMarks()"""
        if tab == "info":
            html = get_note_info_html(note_id)
            html = html.replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(2).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""
        if tab == "related":
            html = get_related_notes_html(note_id)
            html = html.replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-clickable-anchor.tab').eq(1).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""


    @js
    def mark_range(self, start, end, pages_total, current_page):
        if start <= 0:
            start = 1
        if end > pages_total:
            end = pages_total
        if end <= start or start >= pages_total:
            return
        mark_range_as_read(self.note_id, start, end, pages_total)
        pages_read = get_read_pages(self.note_id)
        js = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])
        js = f"pagesRead = [{js}];"
        if current_page >= start and current_page <= end:
            js += "pdfShowPageReadMark();"
        return f"{js}updatePdfProgressBar();"

    @js
    def display_cloze_modal(self, editor, selection, extracted):
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
                
                s_html += "<tr class='siac-cl-row'><td><div contenteditable style='color: darkorange;'>%s</div></td><td><input type='checkbox' checked/></td></tr>" % (sentence.replace("`", "&#96;"))
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
    def notification(self, html, on_ok=None):
        if on_ok is None:
            on_ok = ""
        modal = f""" <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                            {html}
                            <br/> <br/>
                            <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); {on_ok}">Ok</div>
                        </div> """
        return "$('#siac-pdf-tooltip').hide();$('.siac-modal-small').remove(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

    @js
    def update_bottom_bar_positions(self, nid, new_index, queue_len):
        queue_readings_list = get_queue_head_display(nid).replace("`", "\\`")
        priority_str = get_priority_as_str(nid)
        return f"""
            document.getElementById('siac-queue-lbl').innerHTML = 'Priority: {priority_str}';
            $('#siac-queue-lbl').fadeIn('slow');
            $('.siac-queue-sched-btn:first').html('In Queue');
            $('#siac-queue-readings-list').replaceWith(`{queue_readings_list}`);
        """

    @js
    def show_timer_elapsed_popup(self, nid):
        """
            Shows the little popup that is displayed when the timer in the reading modal finished.
        """
        read_today_count = get_read_today_count()
        added_today_count = utility.misc.count_cards_added_today()
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
        <div style='text-align: center;'>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(5);'>&nbsp;Start 5m&nbsp;</div>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px; width: 50px;' onclick='this.parentNode.parentNode.style.display="none";'>Ok</div>
            <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(15);'>&nbsp;Start 15m&nbsp;</div>
        </div>
        """ % (read_today_count, "page" if read_today_count == 1 else "pages", added_today_count, "card" if added_today_count == 1 else "cards")
        return "$('#siac-timer-popup').html(`%s`); $('#siac-timer-popup').show();" % html


    @js
    def jump_to_last_read_page(self, nid):
        return """
            if (pagesRead && pagesRead.length) {
                pdfDisplayedCurrentPage = Math.max(...pagesRead);
                rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
            }
        """
    @js
    def jump_to_first_unread_page(self, nid):
        return """
            if (pdfDisplayed) {
                for (var i = 1; i < pdfDisplayed.numPages + 1; i++) {
                if (!pagesRead || pagesRead.indexOf(i) === -1) {
                    pdfDisplayedCurrentPage = i;
                    rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
                    break;
                } 
                }
            }
        """