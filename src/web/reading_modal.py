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
from typing import List, Optional, Tuple, Any, Callable
import aqt
import uuid
import base64
import html as ihtml
from aqt import mw, gui_hooks
from aqt.editor import Editor
from aqt.utils import showInfo, tooltip
from aqt.qt import QDesktopServices, QUrl

import utility.tags
import utility.text
import utility.misc
import utility.date
import state

from ..state import get_index, check_index
from ..notes import *
from ..notes import _get_priority_list
from ..special_searches import get_last_added_anki_notes
from ..models import SiacNote, IndexNote, Printable
from .html import *
from ..dialogs.done_dialog import DoneDialog
from ..dialogs.priority_dialog import PriorityDialog
from ..dialogs.postpone_dialog import PostponeDialog
from .templating import filled_template
from .note_templates import *
from ..internals import js, HTML, JS
from ..config import get_config_value_or_default, get_config_value
from ..web_import import import_webpage
from ..stats import getRetentions
from ..markdown import markdown
from ..output import UI



try:
    utility.misc.load_rust_lib()
    from siacrs import *
    state.rust_lib = True

except:
    state.rust_lib = False


class ReaderSidebar():

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
        self.page_size                  : int                    = 100

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
                <div id='siac-left-tab-browse' class='flex-col'>
                    <div class='siac-pdf-main-color-border-bottom user_sel_none' style='flex: 0 auto; padding: 5px 0 5px 0;'>
                        <strong class='fg_grey'>Last: </strong>
                        <strong class='blue-hover fg_grey ml-10' onclick='pycmd("siac-pdf-sidebar-last-addon")'>Add-on</strong>
                        <strong class='blue-hover fg_grey ml-10' onclick='pycmd("siac-pdf-sidebar-last-anki")'>Anki</strong>
                    </div>
                    <div id='siac-left-tab-browse-results' class='oflow_y_auto mt-10 mb-5' style='flex: 1 1 auto; padding: 0 7px 0 7px;'>
                    </div>
                    <div style='flex: 0 auto; padding: 5px 0 5px 0;'>
                        <input type='text' class='w-100' style='box-sizing: border-box;' onkeyup='pdfLeftTabAnkiSearchKeyup(this.value, event);'/>
                    </div>
                </div>
            `).insertBefore('#siac-reading-modal-tabs-left');
        """)
        if self.browse_tab_last_results is not None:
            self.print(self.browse_tab_last_results[0], self.browse_tab_last_results[1], self.browse_tab_last_results[2])
        else:
            notes = get_last_added_anki_notes(get_config_value_or_default("pdfTooltipResultLimit", 50))
            self.print(notes, "", [])

    def show_pdfs_tab(self):
        if self.tab_displayed == "pdfs":
            return
        self.tab_displayed = "pdfs"
        self._editor.web.eval(f"""
            document.getElementById("fields").style.display = 'none';
            $('#siac-left-tab-browse,#siac-left-tab-pdfs').remove();
            $(`
                <div id='siac-left-tab-pdfs' class='flex-col'>
                    <div class='siac-pdf-main-color-border-bottom' style='flex: 0 auto; padding: 5px 0 5px 0; user-select: none;'>
                        <strong class='blue-hover fg_grey ml-10' onclick='pycmd("siac-pdf-sidebar-pdfs-in-progress")'>In Progress</strong>
                        <strong class='blue-hover fg_grey ml-10' onclick='pycmd("siac-pdf-sidebar-pdfs-unread")'>Unread</strong>
                        <strong class='blue-hover fg_grey ml-10' onclick='pycmd("siac-pdf-sidebar-pdfs-last-added")'>Last Added</strong>
                    </div>
                    <div id='siac-left-tab-browse-results' class='oflow_y_auto mt-10 mb-5' style='flex: 1 1 auto; padding: 0 5px 0 0;'></div>
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
            html    = UI.get_result_html_simple(results[:limit], tag_hover=False, search_on_selection=False, query_set=query_set)
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
            html = "<center style='margin-top: 50px;'><b>Nothing found.</b></center>"
        else:
            html    = ""
            limit   = get_config_value_or_default("pdfTooltipResultLimit", 50)

            for note in results[:limit]:
                should_show_loader = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showPDFLoader();' if note.is_pdf() else ""
                html = f"{html}<div class='siac-note-title-only' onclick='if (!pdfLoading) {{{should_show_loader}  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note {note.id}\"); hideQueueInfobox();}}'>{note.get_title()}</div>"

            html    = html.replace("`", "\\`")

        self._editor.web.eval(f"document.getElementById('siac-left-tab-browse-results').innerHTML = `{html}`; document.getElementById('siac-left-tab-browse-results').scrollTop = 0;")



class Reader:
    """ Used to display text and PDF notes. """

    last_opened         : Optional[int]             = None
    last_cloze          : Optional[Tuple[int, str]] = None

    current_note        : Optional[SiacNote]        = None
    _original_win_title : Optional[str]             = None

    note_id            : Optional[int]         = None
    note               : Optional[SiacNote]    = None
    _editor            : Optional[Editor]      = None

    highlight_color    : str                   = "#e65100"
    highlight_type     : int                   = 1

    sidebar            : ReaderSidebar   = ReaderSidebar()

    # self.pdfjs_v            : str                   = "2.6.347" if utility.misc.chromium_version()  > "76" else "2.4.456"
    pdfjs_v            : str                   = "2.4.456"


     
    @classmethod
    def set_editor(cls, editor):
        cls._editor            = editor
        cls.sidebar.set_editor(editor)

        #TODO: ugly fix
        gui_hooks.editor_did_load_note.remove(cls.fill_sources)
        gui_hooks.editor_did_load_note.append(cls.fill_sources)

    @classmethod
    def reset(cls):
        cls.note_id                = None
        cls.note                   = None
        Reader.current_note   = None
        cls.sidebar.tab_displayed  = None
        if Reader._original_win_title is not None:
            win = mw.app.activeWindow()
            if isinstance(win, aqt.addcards.AddCards):
                win.setWindowTitle(Reader._original_win_title)


    @classmethod
    def page_displayed(cls, cb: Callable):
        """ Evaluates the currently read page from the webview, and calls the given callback function with the page number. """

        if not cls.note_id:
            return

        if not cls.note.is_pdf():
            cb(1)

        cls._editor.web.evalWithCallback("(() => { return pdf.page; })()", cb)


    @classmethod
    def display(cls, note_id: int):

        if not note_id or note_id <= 0:
            return

        note                    = get_note(note_id)

        if not note:
            return

        # persist note as opened in db
        mark_note_as_opened(note_id)

        if Reader.last_opened is None or (cls.note_id is not None and int(note_id) != cls.note_id):
            Reader.last_opened = cls.note_id if Reader.last_opened else note_id

        cls.note_id              = int(note_id)
        cls.note                 = note
        Reader.current_note      = note
        html                     = cls.html()

        UI.show_in_large_modal(html)

        # wrap fields in tabs
        UI.js("""
            $(document.body).addClass('siac-reading-modal-displayed');
            //remove modal animation to prevent it from being triggered when switching left/right or CTRL+F-ing
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
                cls._display_pdf(note.source.strip(), note_id)
                # try to select deck which was mostly used when adding notes while this pdf was open
                deck_name = get_deck_mostly_linked_to_note(note_id)
                if deck_name:
                    selected = UI.try_select_deck(deck_name)

            else:
                message = "<i class='fa fa-exclamation-triangle mb-10' style='font-size: 20px;'></i><br>Could not load the given PDF.<br>Are you sure the path is correct?"
                cls.notification(message)

        # auto fill tag entry if pdf has tags and config option is set
        if note.tags is not None and len(note.tags.strip()) > 0 and get_config_value_or_default("pdf.onOpen.autoFillTagsWithPDFsTags", True):
            cls._editor.tags.setText(" ".join(mw.col.tags.canonify(mw.col.tags.split(note.tags))))


        # auto fill user defined fields
        cls.fill_sources(cls._editor)


        # try to change the window title to include the title of the currently read note
        win = mw.app.activeWindow()
        if hasattr(win, "setWindowTitle") and isinstance(win, aqt.addcards.AddCards):
            if Reader._original_win_title is None:
                Reader._original_win_title = win.windowTitle()
            win.setWindowTitle(f"{Reader._original_win_title} [{cls.note.get_title()}]")


    @classmethod
    def _display_pdf(cls, full_path: str, note_id: int):

        # use rust based lib for better performance if possible
        if state.rust_lib:
            try:
                base64pdf       = encode_file(full_path)
            except:
                state.rust_lib = False
        if not state.rust_lib:
            base64pdf       = utility.misc.pdf_to_base64(full_path)
        blen            = len(base64pdf)

        #pages read are stored in js array [int]
        pages_read      = get_read_pages(note_id)
        pages_read_js   = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])

        #marks are stored in two js maps, one with pages as keys, one with mark types (ints) as keys
        marks           = get_pdf_marks(note_id)
        js_maps         = utility.misc.marks_to_js_map(marks)
        marks_js        = "pdf.displayedMarks = %s; pdf.displayedMarksTable = %s;" % (js_maps[0], js_maps[1])

        # pdf might be an extract (should only show a range of pages)
        extract_js      = f"pdf.extract = [{cls.note.extract_start}, {cls.note.extract_end}];" if cls.note.extract_start is not None else "pdf.extract = null;"

        # get possible other extracts created from the current pdf
        extracts        = get_extracts(note_id, cls.note.source)
        extract_js      += f"pdf.extractExclude = {json.dumps(extracts)};"

        # pages read are ordered by date, so take last
        last_page_read  = pages_read[-1] if len(pages_read) > 0 else 1


        if cls.note.extract_start is not None:
            if len(pages_read) > 0:
                read_in_extract = [p for p in pages_read if p >= cls.note.extract_start and p <= cls.note.extract_end]
                last_page_read = read_in_extract[-1] if len(read_in_extract) > 0 else cls.note.extract_start
            else:
                last_page_read  = cls.note.extract_start

        title           = utility.text.trim_if_longer_than(cls.note.get_title(), 50).replace('"', "")
        addon_id        = utility.misc.get_addon_id()
        port            = mw.mediaServer.getPort()

        init_code = """
            (() => {
            pdfLoading = true;
            var bstr = atob(b64);
            pdf.pagesRead = [%s];
            %s
            %s
            var loadFn = function(retry) {
                if (retry > 4) {
                    $('#siac-pdf-loader-wrapper').remove();
                    $('#siac-timer-popup').html(`<br><center>PDF.js could not be loaded from CDN.</center><br>`).show();
                    pdf.instance = null;
                    ungreyoutBottom();
                    fileReader = null;
                    pdfLoading = false;
                    noteLoading = false;
                    return;
                }
                if (typeof(pdfjsLib) === 'undefined') {
                    window.setTimeout(() => { loadFn(retry + 1);}, 800);
                    pdfLoaderText(`PDF.js was not loaded. Retrying (${retry+1} / 5)`);
                    return;
                }
                if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
                    pdfjsLib.GlobalWorkerOptions.workerSrc = 'http://127.0.0.1:%s/_addons/%s/web/pdfjs/%s/pdf.worker.min.js';
                }
                var canvas = document.getElementById("siac-pdf-canvas");
                window.pdf_canvas_0 = canvas;
                window.pdf_canvas_1 = document.getElementById("siac-pdf-canvas_1");
                var loadingTask = pdfjsLib.getDocument({data: bstr, nativeImageDecoderSupport: 'none'});
                loadingTask.promise.catch(function(error) {
                        $('#siac-pdf-loader-wrapper').remove();
                        $('#siac-timer-popup').html(`<br><center>Could not load PDF - seems to be invalid.</center><br>`).show();
                        pdf.instance = null;
                        ungreyoutBottom();
                        fileReader = null;
                        pdfLoading = false;
                        noteLoading = false;
                });
                loadingTask.promise.then(function(pdfDoc) {
                        pdf.instance = pdfDoc;
                        displayedNoteId = %s;
                        pdf.page = getLastReadPage() || %s;
                        pdf.highDPIWasUsed = false;
                        if (!document.getElementById('siac-pdf-top')) {
                            return;
                        }
                        document.getElementById('text-layer').style.display = 'inline-block';
                        if (pdf.pagesRead.length === pdfDoc.numPages) {
                            pdf.page = getLastReadPage() || 1;
                            queueRenderPage(pdf.page, true, true, true);
                        } else {
                            queueRenderPage(pdf.page, true, true, true);
                        }
                        updatePdfProgressBar();
                        if (topBarIsHidden()) {
                            readerNotification("%s");
                        }
                        if (pdf.pagesRead.length === 0) { pycmd('siac-insert-pages-total %s ' + numPagesExtract()); }
                        fileReader = null;
                        pdf.TOC = null;
                        setTimeout(checkTOC, 300);
                }).catch(function(err) { setTimeout(function() { console.log(err); }); });
            };
            loadFn();
            b64 = "";
            bstr = null; file = null;
            })();
        """ % (pages_read_js, marks_js, extract_js, port, addon_id, cls.pdfjs_v, note_id, last_page_read, title, note_id)

        #send large files in multiple packets
        page        = cls._editor.web.page()
        chunk_size  = 50000000
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

    @classmethod
    def fill_sources(cls, editor):
        """ Check if any of the fields in pdf.onOpen.autoFillFieldsWithPDFName"""
        """" are present, if yes, fill them with the note's title. """

        siacnote = cls.note

        if siacnote is not None and get_config_value_or_default("pdf.onOpen.autoFillSourceFieldsBool", True):
            note                = cls._editor.note

            fields_to_prefill   = get_config_value_or_default("pdf.onOpen.autoFillFieldsWithPDFName", [])
            title               = siacnote.get_title().replace("`", "&#96;")

            if siacnote.url is not None:
                title += '<br><a class="siac-source-link" href="' + siacnote.url + '">' + siacnote.url + '</a>'

            if len(fields_to_prefill) > 0:
                for f in fields_to_prefill:
                    if f in list(note.keys()):
                        i = note._fieldOrd(f)
                        cls._editor.web.eval(f"$('.field').eq({i}).html(`{title}`);")


    @classmethod
    def read_head_of_queue(cls):
        """ Will open the first item in the queue if existing, if not, show a tooltip. """

        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            cls.display(nid)
        else:
            cls.close()
            tooltip("Queue is Empty! Add some items first.", period=4000)

    @classmethod
    def close(cls):
        """ Resets the state on the python and UI/javascript side. Will close the dialog in the UI. """

        cls._editor.web.eval("ungreyoutBottom();noteLoading=false;pdfLoading=false;modalShown=false;onReadingModalClose();")
        cls.reset()

    @classmethod
    def display_head_of_queue_after_sched_modal(cls):

        recalculate_priority_queue()

        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            cls.display(nid)
        else:
            cls.close()
            tooltip("Queue is empty.")

    @classmethod
    def done(cls):
        """ Hit "Done" / "Add to Queue" button. """

        note        = cls.note
        done_dialog = DoneDialog(cls._editor.parentWindow, cls.note_id)

        if done_dialog.exec_():
            new_priority        = done_dialog.priority
            new_schedule        = done_dialog.schedule
            sched_has_changed   = done_dialog.schedule_has_changed

            if sched_has_changed:
                update_reminder(cls.note_id, new_schedule)
            else:
                # if the note has a schedule and was due today, either:
                # - update the schedule (set a new due date based on its scheduling type)
                # - or delete the schedule (schedule type was 'td', i.e. one-shot schedule)

                if note.has_schedule() and note.is_or_was_due():
                    if note.schedule_type() != "td":
                        new_schedule = utility.date.get_new_reminder(note.schedule_type(), note.schedule_value())
                        update_reminder(cls.note_id, new_schedule)
                    else:
                        update_reminder(cls.note_id, "")

            remove_delay(cls.note_id)
            update_priority_list(cls.note_id, new_priority)

            # 1. check if any notes have been selected to enqueue, if yes, update priority list
            if done_dialog.enqueue_next_ids and len(done_dialog.enqueue_next_ids) > 0:
                for nid in done_dialog.enqueue_next_ids:
                    update_priority_list(nid, done_dialog.enqueue_next_prio)

            if get_config_value("mix_reviews_and_reading.review_after_done") and state.interrupted_review:
                win = mw.app.activeWindow()
                if isinstance(win, aqt.addcards.AddCards):
                    win.close()

            # 2. check if a tag filter is set, if yes, the next opened note should not be the first in the queue, but rather
            # the next enqueued note with at least one overlapping tag
            if done_dialog.tag_filter is not None and len(done_dialog.tag_filter.strip()) > 0:
                nid = find_next_enqueued_with_tag(done_dialog.tag_filter.split(" "))
                if nid is not None and nid > 0:
                    cls.display(nid)
                else:
                    cls.read_head_of_queue()
            else:
                cls.read_head_of_queue()


                mw.raise_()
                state.interrupted_review = False
        else:
            cls._editor.web.eval("ungreyoutBottom();noteLoading=false;pdfLoading=false;modalShown=false;")


    @classmethod
    def show_prio_dialog(cls):
        dialog          = PriorityDialog(cls._editor.parentWindow, cls.note_id)
        if dialog.exec_():
            initial = get_priority(cls.note_id)
            prio    = dialog.value

            if initial and initial > 0:
                update_priority_without_timestamp(cls.note_id, prio)
                tooltip(f"Updated priority.")
            else:
                update_priority_list(cls.note_id, prio)
                tooltip(f"Updated priority and added to queue.")
            cls.reload_bottom_bar()

    @classmethod
    def show_postpone_dialog(cls):
        """ Show a dialog to move the note either back in the queue or schedule for a future day. """

        cls.note = get_note(cls.note_id)
        if cls.note.position is None:
            tooltip("Cannot postpone a note that is not in the queue.", period=5000)
            return

        dialog          = PostponeDialog(cls._editor.parentWindow, cls.note_id)
        if dialog.exec_():
            # 1. option: later today (move back in queue)
            if dialog.value == 0:
                qlen = len(_get_priority_list())
                if qlen > 2:
                    delay = int(qlen/3)
                    if cls.note.position < 3:
                        delay += (3 - cls.note.position)
                    set_delay(cls.note_id, delay)
                    recalculate_priority_queue()
                    tooltip("Moved note back in queue")
                    cls.read_head_of_queue()
                else:
                    tooltip("Later only works if 3+ items are in the queue.")
            else:
                # 2. option: schedule note to appear in x days
                days_delta = dialog.value
                if cls.note.has_schedule():
                    new_reminder = utility.date.postpone_reminder(cls.note.reminder, days_delta)
                else:
                    new_reminder = utility.date.get_new_reminder("td", str(days_delta))
                update_reminder(cls.note_id, new_reminder)
                # delete any delays if existent
                remove_delay(cls.note_id)

                # remove note from queue
                prio = get_priority(cls.note_id)
                update_priority_list(cls.note_id, 0)

                # DEBUG
                if state.dev_mode:
                    note = get_note(cls.note_id)
                    assert(get_priority(cls.note_id) is None)
                    assert(not note.is_in_queue())
                    assert(note.position is None)

                cls.read_head_of_queue()

    @classmethod
    @js
    def show_width_picker(cls) -> JS:
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
            <div class="siac-modal-small dark ta_center fg_lightgrey" contenteditable="false">
                <b>Width (%%)</b><br>
                <b>Fields - Add-on</b>
                    <br><br>
                <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div>
                    <br><br>
                <div class='w-100 ta_right'>
                    <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode.parentNode).remove();">Close</div>
                </div>
            </div>
        """ % html
        return "$('#siac-reading-modal-center').append(`%s`)" % modal

    @classmethod
    @js
    def display_read_range_input(cls, note_id: int, num_pages: int) -> JS:
        on_confirm= """ if (document.getElementById('siac-range-input-min').value && document.getElementById('siac-range-input-max').value) {
        pycmd('siac-user-note-mark-range %s ' + document.getElementById('siac-range-input-min').value
                + ' ' + document.getElementById('siac-range-input-max').value
                + ' ' + numPagesExtract()
                + ' ' + pdf.page);
        }
        """ % note_id
        modal = f""" <div class="siac-modal-small dark ta_center fg_lightgrey" contenteditable="false">
                            Input a range of pages to mark as read (end incl.)<br><br>
                            <input id='siac-range-input-min' class='fg_lightgrey' style='width: 60px; background: #222; border-radius: 4px;' type='number' min='1' max='{num_pages}'/> &nbsp;-&nbsp; <input id='siac-range-input-max' style='width: 60px;background: #222; color: lightgrey; border-radius: 4px;' type='number' min='1' max='{num_pages}'/>
                            <br/> <br/>
                            <div class="siac-btn siac-btn-dark" onclick="{on_confirm} $(this.parentNode).remove();">&nbsp; Ok &nbsp;</div>
                            &nbsp;
                            <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                        </div> """
        return "$('#siac-pdf-tooltip').hide();$('.siac-modal-small').remove(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")


    @classmethod
    @js
    def reload_bottom_bar(cls) -> JS:
        """
            Called after queue picker dialog has been closed without opening a new note.
        """
        if cls.note_id is None:
            return
        note = get_note(cls.note_id)
        html = cls.bottom_bar(note)
        html = html.replace("`", "\\`")
        return "$('#siac-reading-modal-bottom-bar').replaceWith(`%s`); updatePdfDisplayedMarks(true);" % html




    @classmethod
    def show_fields_tab(cls):
        cls.sidebar.show_fields_tab()

    @classmethod
    def show_browse_tab(cls):
        cls.sidebar.show_browse_tab()

    @classmethod
    def show_pdfs_tab(cls):
        cls.sidebar.show_pdfs_tab()

    @classmethod
    def html(cls) -> HTML:
        """ Builds the html which has to be inserted into the webview to display the reading modal. """

        note        = cls.note
        note_id     = cls.note_id
        text        = note.text
        created_dt  = datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
        diff        = datetime.datetime.now() - created_dt
        time_str    = "Added %s ago." % utility.date.date_diff_to_string(diff)

        if check_index():

            title           = note.get_title()
            title           = utility.text.trim_if_longer_than(title, 70)
            title           = ihtml.escape(title)
            source          = note.source.strip() if note.source is not None and len(note.source.strip()) > 0 else "Empty"
            priority        = note.priority
            img_folder      = utility.misc.img_src_base_path()
            page_sidebar    = str(conf_or_def("pdf.page_sidebar_shown", True)).lower()

            rev_overlay     = ""
            if get_config_value("notes.show_linked_cards_are_due_overlay"):
                # check for last linked pages
                last_linked     = get_last_linked_notes(note_id, limit = 500)
                if len(last_linked) > 0:
                    if hasattr(mw.col, "find_cards"):
                        due_today   = mw.col.find_cards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked]))
                    else:
                        due_today   = mw.col.findCards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked]))
                    if due_today and len(due_today) > 0:
                        act         = "Reading"
                        if note.is_pdf():
                            ntype = "PDF"
                        elif note.is_yt():
                            ntype = "video"
                            act   = "Watching"
                        else:
                            ntype = "note"

                        rev_overlay = f"""
                            <div class='siac-rev-overlay'>
                                <div class='ta_center bold fg_lightgrey' style='font-size: 22px;'>
                                <span>Some of the last cards you made in this {ntype} are due today.<br>Review them before {act.lower()}?</span>
                                </div>
                                <div class='ta_center bold' style='opacity: 1; margin: 50px 0 30px 0;'>
                                    <div class='siac-btn siac-btn-dark' style='margin-right: 15px;' onclick='pycmd("siac-rev-last-linked");document.getElementsByClassName("siac-rev-overlay")[0].style.display = "none";'><i class="fa fa-graduation-cap"></i>&nbsp;Review</div>
                                    <div class='siac-btn siac-btn-dark' style='filter: brightness(.65);' onclick='document.getElementsByClassName("siac-rev-overlay")[0].style.display = "none";'><i class="fa fa-book"></i>&nbsp;Continue {act}</div>
                                </div>
                            </div>
                        """

            overflow        = "auto"
            notification    = ""
            editable        = False
            #check note type
            if note.is_file() and not note.is_md():
                editable = len(text) < 100000
                overflow = "hidden"
                text = cls.file_note_html(editable, priority, source)
            elif note.is_pdf() and utility.misc.file_exists(source):
                overflow        = "hidden"
                text            = cls.pdf_viewer_html(source, note.get_title(), priority)

                if "/" in source:
                    source  = source[source.rindex("/") +1:]
            elif note.is_feed():
                text        = cls.get_feed_html(note_id, source)
            elif note.is_yt():
                text        = cls.yt_html()
            else:
                editable    = len(text) < 100000
                overflow    = "hidden"
                text        = cls.text_note_html(editable, priority)
            bottom_bar      = cls.bottom_bar(note)

            top_hidden      = "top-hidden" if conf_or_def("notes.queue.hide_top_bar", False) else ""

            if not note.is_in_queue() and utility.date.schedule_is_due_in_the_future(note.reminder):
                notification    = f"readerNotification('Scheduled for {note.due_date_str()}');"

            params              = dict(note_id = note_id, title = title, source = source, time_str = time_str, img_folder = img_folder, text = text,
            overflow=overflow, top_hidden=top_hidden,
            notification=notification, page_sidebar=page_sidebar, rev_overlay = rev_overlay, bottom_bar=bottom_bar)

            html = filled_template("rm/reading_modal", params)

            return html
        return ""

    @classmethod
    def file_note_html(cls, editable: bool, priority: int, source: str) -> HTML:
        """
            Returns a slightly altered editor for the text, with an indication towards the file
        """
        nid                     = cls.note_id
        text                    = cls.note.text if not utility.text.is_html(cls.note.text) else utility.text.html_to_text(cls.note.text)
        search_sources          = ""
        config                  = mw.addonManager.getConfig(__name__)
        urls                    = config["searchUrls"]

        if urls is not None and len(urls) > 0:
            search_sources = cls.iframe_dialog(urls)

        title                   = utility.text.trim_if_longer_than(cls.note.get_title(), 50).replace('"', "")
        params                  = dict(text = text, nid = nid, search_sources=search_sources, title=title, source = source)

        html                    = filled_template("rm/file_viewer", params)
        return html


    @classmethod
    def text_note_html(cls, editable: bool, priority: int) -> HTML:
        """
            Returns the html which is wrapped around the text of user notes inside the reading modal.
            This function is used if the note is a regular, text-only note, if the note is a pdf note,
            pdf_viewer_html is used instead.
        """

        nid                     = cls.note_id
        text                    = cls.note.text if not utility.text.is_html(cls.note.text) else utility.text.html_to_text(cls.note.text)
        search_sources          = ""
        config                  = mw.addonManager.getConfig(__name__)
        urls                    = config["searchUrls"]

        if urls is not None and len(urls) > 0:
            search_sources = cls.iframe_dialog(urls)

        title                   = utility.text.trim_if_longer_than(cls.note.get_title(), 50).replace('"', "")
        params                  = dict(text = text, nid = nid, search_sources=search_sources, title=title)

        html                    = filled_template("rm/text_viewer", params)
        return html

    @classmethod
    def yt_html(cls) -> HTML:
        """ Returns the HTML for the embedded youtube video player. """

        title   = utility.text.trim_if_longer_than(cls.note.get_title(), 50).replace('"', "")
        url     = cls.note.source.strip()
        match   = re.match(r".+/watch\?v=([^&]+)(?:&t=(.+)s)?", url)
        time    = 0

        if match:
            video = match.group(1)
            if len(match.groups()) > 1:
                if match.group(2) is not None and len(match.group(2)) > 0:
                    time = int(match.group(2))

        params = dict(
            note_id = cls.note_id,
            title   = title,
            video   = video,
            time    = time
        )
        return filled_template("rm/yt_viewer", params)


    @classmethod
    def get_feed_html(cls, nid, source) -> HTML:
        """ Not used currently. """

        #extract feed url
        try:
            feed_url    = source[source.index(":") +1:].strip()
        except:
            return "<center>Could not load feed. Please check the URL.</center>"
        res             = read(feed_url)
        search_sources  = ""
        config          = mw.addonManager.getConfig(__name__)
        urls            = config["searchUrls"]
        if urls is not None and len(urls) > 0:
            search_sources = cls.iframe_dialog(urls)
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
            <div id='siac-iframe-btn' style='top: 5px; left: 0px;' class='siac-btn siac-btn-dark' onclick='iframeBtnClicked(event)'><i class="fa fa-globe" aria-hidden="true"></i>
                <div style='margin-left: 5px; margin-top: 4px; color: lightgrey; width: calc(100% - 35px); text-align: right; color: grey; font-size: 10px;'>Note: Not all sites allow embedding!</div>
                <div style='padding: 0 15px 10px 15px; margin-top: 10px; max-height: 500px; overflow-y: auto; box-sizing: border-box; width: 100%;'>
                    <input onclick="event.stopPropagation();" onkeyup="if (event.keyCode === 13) {{ pdfUrlSearch(this.value); this.value = ''; }}"></input>
                    <br/>
                {search_sources}
                </div>
            </div>
            <div id='siac-close-iframe-btn' class='siac-btn siac-btn-dark fg_lightgrey' onclick='pycmd("siac-close-iframe")'><b>&times; &nbsp;CLOSE</b></div>
            <div id='siac-text-top' contenteditable='false' onmouseup='nonPDFKeyup();' onclick='if (!window.getSelection().toString().length) {{$("#siac-pdf-tooltip").hide();}}'>
                {text}
            </div>
            <iframe id='siac-iframe' sandbox='allow-scripts' style='height: calc(100% - 47px);'></iframe>
            <div class="siac-reading-modal-button-bar-wrapper">
                <div style='position: absolute; left: 0; z-index: 1; user-select: none;'>
                    <div class='siac-btn siac-btn-dark' style="margin-left: -20px;" onclick='toggleBottomBar();'>&#x2195;</div>
                    <div class='siac-btn siac-btn-dark ml-5' id='siac-rd-note-btn' onclick='pycmd("siac-create-note-add-only {nid}")'><b>&#9998; Note</b></div>
                </div>
            </div>
            <script>
                if (pdfTooltipEnabled) {{
                    $('#siac-pdf-tooltip-toggle').addClass('active');
                }} else {{
                    $('#siac-pdf-tooltip-toggle').removeClass('active');
                }}
                if (pdfLinksEnabled) {{
                    $('#siac-pdf-links-toggle').addClass('active');
                }} else {{
                    $('#siac-pdf-links-toggle').removeClass('active');
                }}
                ungreyoutBottom();
            </script>
        """.format_map(dict(text = text, nid = nid, search_sources=search_sources))
        return html


    @classmethod
    def bottom_bar(cls, note) -> HTML:
        """ Returns only the html for the bottom bar, useful if the currently displayed pdf should not be reloaded, but the queue display has to be refreshed. """

        text            = note.text
        note_id         = note.id
        queue           = _get_priority_list()
        priority        = note.priority
        has_schedule    = "active" if note.is_due_sometime() else ""

        if note.is_in_queue():
            queue_btn_text      = "Done!"
        else:
            queue_btn_text      = "Add to Queue"

        editable            = not note.is_feed() and not note.is_pdf() and len(text) < 50000

        # decide what to show in the top button
        # 1. note is in queue and has a priority -> show the priority
        if note.is_in_queue() and priority:
            queue_info      = "Priority: %s" % (dynamic_sched_to_str(priority))
        # 2. note is in queue but has no priority (it is scheduled for today/ was due in the last 7 days)
        elif note.is_in_queue():
            if note.is_due_today():
                queue_info      = "Scheduled for today"
            else:
                # note must have been due before but hasn't beeen done
                if note.due_days_delta() == 1:
                    queue_info      = "Scheduled for yesterday"
                else:
                    queue_info      = f"Scheduled for {note.due_days_delta()} days ago"
        else:
            queue_info      = "Unqueued"

        hide_page_map       = "hidden" if not note.is_pdf() else ""
        if not note.is_in_queue() and utility.date.schedule_is_due_in_the_future(note.reminder):
            queue_info      = "Scheduled for future date"
        queue_readings_list = cls.get_queue_head_display(queue, editable)

        bar_hidden          = "bottom-hidden" if get_config_value_or_default("notes.queue.hide_bottom_bar", False) else ""

        params              = dict(note_id = note_id, queue_btn_text = queue_btn_text, queue_info = queue_info,
        queue_readings_list = queue_readings_list, has_schedule=has_schedule, hide_page_map = hide_page_map, bar_hidden = bar_hidden)

        html                = filled_template("rm/reading_modal_bottom", params)

        return html

    @classmethod
    def get_queue_head_display(cls, queue: Optional[List[SiacNote]] = None, should_save: bool = False) -> HTML:
        """ This builds the html for the little list at the bottom of the reading modal which shows the first 5 items in the queue. """

        if queue is None:
            queue = _get_priority_list()

        note_id             = cls.note_id
        note                = cls.note

        if not note.is_pdf() and not note.is_feed():
            should_save     = True

        config              = mw.addonManager.getConfig(__name__)
        hide                = config["pdf.queue.hide"]
        position            = str(note.position+1) if note.position is not None else "-"
        avg_prio            = round(get_avg_priority(), 1)
        show_prios          = config["notes.queue.show_priorities"]
        if show_prios:
            priorities      = get_priorities([n.id for n in queue[:5]])
        queue_head_readings = ""

        for ix, queue_item in enumerate(queue):

            should_greyout = "greyedout" if queue_item.id == int(note_id) else ""
            if not hide or queue_item.id == int(note_id):
                qi_title = utility.text.trim_if_longer_than(queue_item.get_title(), 40)
                qi_title = ihtml.escape(qi_title)
            else:
                qi_title = utility.text.trim_if_longer_than(re.sub("[^ ]", "?",queue_item.get_title()), 40)

            hover_actions       = "onmouseenter='showQueueInfobox(this, %s);' onmouseleave='leaveQueueItem(this);'" % (queue_item.id) if not hide else ""
            #if the note is a pdf or feed, show a loader on click
            pdf_or_feed         = queue_item.is_feed() or queue_item.is_pdf()
            clock               = "&nbsp; <i class='fa fa-calendar'/>&nbsp;" if queue_item.is_scheduled() else ""
            should_show_loader  = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showPDFLoader();' if pdf_or_feed else ""
            if show_prios:
                if queue_item.id in priorities:
                    prio_lbl        = int(priorities[queue_item.id])
                    prio_lbl        = f"<span class='mr-5 ml-5 siac-prio-lbl' style='background: {utility.misc.prio_color(prio_lbl)};'>{prio_lbl}</span>"
                else:
                    prio_lbl        = f"<span class='mr-5 ml-5 siac-prio-lbl fg_lightgrey' style='background: #5a5a5a;'>-</span>"
            else:
                prio_lbl = ""
            queue_head_readings +=  "<a onclick='if (!pdfLoading && !modalShown) {%s destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note %s\"); hideQueueInfobox();}' class='siac-link-btn bold %s' style='font-size: 12px;' %s >%s.%s%s %s</a><br>" % (should_show_loader, queue_item.id, should_greyout, hover_actions, queue_item.position + 1, prio_lbl, clock, qi_title)
            if ix > 3:
                break

        if hide:
            hide_btn = """<div class='fg_grey bright-hover siac-queue-btn ml-5' onclick='unhideQueue(%s)'>Show Items</div>""" % note_id
        else:
            hide_btn = """<div class='fg_grey bright-hover siac-queue-btn ml-5' onclick='hideQueue(%s)'>Hide Items</div>""" % note_id

        show_prio_action    = "off" if show_prios else "on"
        show_prio_lbl       = "Hide" if show_prios else "Show"
        show_prio_btn       = f"""<div class='fg_grey bright-hover siac-queue-btn ml-5' onclick='pycmd("siac-toggle-show-prios {show_prio_action}")'>{show_prio_lbl} Prios</div>"""

        html = f"""
        <div id='siac-queue-readings-list'>
            <div class='fg_lightgrey cursor-pointer white-hover siac-queue-btn' onclick='pycmd("siac-user-note-queue-picker")'><i class="fa fa-inbox mr-10"></i>{position} / {len(queue)}</div>
            <div class='fg_lightgrey siac-queue-btn ml-5'>&#216;&nbsp;{avg_prio}</div>
            {hide_btn}
            {show_prio_btn}
            <br>
            {queue_head_readings}
        </div>
        """

        return html


    @classmethod
    def pdf_viewer_html(cls, source: str, title: str, priority: int) -> HTML:
        """ Returns the center area of the reading modal. Use this if the displayed note is a pdf. """

        nid                 = cls.note_id
        config              = mw.addonManager.getConfig(__name__)
        urls                = config["searchUrls"]
        search_sources      = cls.iframe_dialog(urls) if urls else ""
        marks_img_src       = utility.misc.img_src("mark-star-24px.png")
        marks_grey_img_src  = utility.misc.img_src("mark-star-lightgrey-24px.png")
        pdf_search_img_src  = utility.misc.img_src("magnify-24px.png")
        extract             = ""

        if cls.note.extract_start:
            if cls.note.extract_start == cls.note.extract_end:
                extract = f"<div class='siac-extract-marker'>&nbsp;<i class='fa fa-book' aria-hidden='true'></i> &nbsp;Extract: P. {cls.note.extract_start}&nbsp;</div>"
            else:
                extract = f"<div class='siac-extract-marker'>&nbsp;<i class='fa fa-book' aria-hidden='true'></i> &nbsp;Extract: P. {cls.note.extract_start} - {cls.note.extract_end}&nbsp;</div>"

        params = dict(nid = nid, pdf_title = title, pdf_path = source, search_sources=search_sources, marks_img_src=marks_img_src,
        marks_grey_img_src=marks_grey_img_src, pdf_search_img_src=pdf_search_img_src, extract=extract)

        html   = filled_template("rm/pdf_viewer", params)
        return html

    @classmethod
    def get_note_info_html(cls) -> HTML:
        """ Returns the html that is displayed in the "Info" tab in the bottom bar of the reading modal. """

        note    = cls.note
        created = note.created
        tags    = note.tags

        if note.reminder is None or len(note.reminder.strip()) == 0:
            schedule = "No Schedule"
        else:
            schedule = utility.date.schedule_verbose(note.reminder)

        if tags.startswith(" "):
            tags = tags[1:]

        html = f"""
            <table class='fg_grey' style='min-width: 190px; line-height: 1.2;'>
                <tr><td>ID</td><td><b>{note.id}</b> &nbsp;<b style='color: #ababab; cursor: pointer;' onclick='pycmd("siac-copy-to-cb {note.id}")'>[Copy]</b></td></tr>
                <tr><td>Created</td><td><b>{created}</b></td></tr>
                <tr><td>Schedule</td><td><b>{schedule}</b></td></tr>
                <tr>
                    <td style='padding-top: 10px;'><i class='fa fa-tags'></i>&nbsp; Tags</td>
                    <td style='padding-top: 10px;'>
                        <input type='text' class='siac-rm-bg fg_lightgrey' style='width: 210px; margin-left: 4px; padding-left: 4px; border: 1px solid grey; border-radius: 4px;' onfocusout='pycmd("siac-update-note-tags {note.id} " + this.value)' value='{tags}'></input>
                    </td>
                </tr>
            </table>
        """
        return html

    @classmethod
    def iframe_dialog(cls, urls: List[str]) -> HTML:
        """ HTML for the button on the top left of the center pane, which allows to search for text in an iframe. """

        search_sources  = "<table class='cursor-pointer w-100' style='margin: 10px 0 10px 0; box-sizing: border-box;' onclick='event.stopPropagation();'>"
        ix              = 0
        direct_links    = ""

        for url in urls:
            name = os.path.dirname(url)
            name = re.sub("^https?://(www2?.)?", "", name)
            if "[QUERY]" in url:
                search_sources += "<tr><td><label for='%s'>%s</label></td><td><input type='radio' name='url-radio' id='%s' data-url='%s' %s/></td></tr>" % ("url-rd-%d" % ix, name, "url-rd-%d" % ix, url, "checked" if ix == 0 else "")
                ix += 1
            else:
                direct_links += """<div class="siac-url-ch" onclick='event.stopPropagation(); $("#siac-iframe-btn").removeClass("expanded"); pycmd("siac-url-srch $$$dummy$$$%s");'>%s</div>""" % (url, name)

        search_sources += "</table>"
        if len(direct_links) > 0:
            search_sources += "<div class='mb-5'>Direct Links:</div>"
            search_sources += direct_links

        return search_sources

    @classmethod
    @js
    def show_remove_dialog(cls, nid: Optional[int] = None) -> JS:
        """ Shows a dialog to either remove the current note from the queue or to delete it altogether. """

        if nid:
            note = get_note(nid)
        else:
            note = cls.note

        prio    = get_priority(note.id)

        title   = utility.text.trim_if_longer_than(note.get_title(), 40).replace("`", "")
        rem_cl  = "checked" if note.position is not None and note.position >= 0 and prio and prio > 0 else "disabled"
        del_cl  = "checked" if rem_cl == "disabled" else ""
        note_id = note.id

        modal   = filled_template("remove_modal", dict(title = title, rem_cl = rem_cl, del_cl = del_cl, note_id = note_id))
        return """modalShown=true;
            $('#siac-timer-popup').hide();
            $('#siac-rm-greyout').show();
            $('#siac-reading-modal-center').append(`%s`);
            """ % modal


    @classmethod
    def schedule_note(cls, option: int):
        """ Will update the schedule of the note according to the chosen option.
            This function is called after an option in the dialog of display_schedule_dialog() has been selected. """

        delta       = cls.note.due_days_delta()
        now         = utility.date.date_now_stamp()
        new_prio    = get_priority(cls.note_id)

        if option == 1:
            if delta < 0:
                # keep schedule & requeue
                new_reminder = cls.note.reminder
            else:
                if cls.note.schedule_type() == "td":
                    # show again in n days
                    days_delta      = int(cls.note.reminder.split("|")[2][3:])
                    next_date_due   = dt.now() + timedelta(days=days_delta)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|td:{days_delta}"

                elif cls.note.schedule_type() == "wd":
                    # show again on next weekday instance
                    wd_part         = cls.note.reminder.split("|")[2]
                    weekdays_due    = [int(d) for d in wd_part[3:]]
                    next_date_due   = utility.date.next_instance_of_weekdays(weekdays_due)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|{wd_part}"
                elif cls.note.schedule_type() == "id":
                    # show again according to interval
                    days_delta      = int(cls.note.reminder.split("|")[2][3:])
                    next_date_due   = dt.now() + timedelta(days=days_delta)
                    new_reminder    = f"{now}|{utility.date.dt_to_stamp(next_date_due)}|id:{days_delta}"
        elif option == 2:
            #remove schedule & requeue
            new_reminder    = ""
        elif option == 3:
            # remove entirely from queue
            new_reminder    = ""
            new_prio        = 0

        update_reminder(cls.note_id, new_reminder)
        update_priority_list(cls.note_id, new_prio)
        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            cls.display(nid)
        else:
            cls._editor.web.eval("""
                onReadingModalClose();
            """)

    @classmethod
    @js
    def show_theme_dialog(cls) -> JS:
        """ Display a modal to change the main color of the reader. """

        modal = filled_template("rm/theme", {}).replace('`', '\\`')

        return """modalShown=true;
            $('#siac-timer-popup').hide();
            $('#siac-rm-greyout').show();
            $('#siac-reading-modal-center').append(`%s`);
            """ % modal

    @classmethod
    @js
    def show_img_field_picker_modal(cls, img_src: str) -> JS:
        """
            Called after an image has been selected from a PDF, should display all fields that are currently in the editor,
            let the user pick one, and on picking, insert the img into the field.
        """

        # if Image Occlusion add-on is there and enabled, add a button to directly open the IO dialog
        io      = ""
        if hasattr(cls._editor, 'onImgOccButton') and mw.addonManager.isEnabled("1374772155"):
            io  = f"<div class='siac-btn siac-btn-dark' style='margin-right: 9px;' onclick='pycmd(\"siac-cutout-io {img_src}\"); $(this.parentNode).remove();'><i class='fa fa-eraser'></i>&nbsp; Image Occlusion</div>"
        modal   = """<div class="siac-modal-small dark ta_center">
                        <img src="%s" style="height: 90px;"/><br>
                        <b>Append to field:</b><br><br>
                        <div class='oflow_y_auto ta_left' style="max-height: 200px; margin: 0 40px; padding-left:4px; overflow-x: hidden;">%s</div>
                        <br><br>
                        %s
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); pycmd('siac-remove-snap-image %s')">Cancel</div>
                    </div> """
        flds    = ""
        for i, f in enumerate(cls._editor.note.model()['flds']):
            # trigger note update
            fld_update_js = "pycmd(`blur:%s:${currentNoteId}:${$(`.field:eq(%s)`).html()}`);" % (i,i)
            flds += """<span class="siac-field-picker-opt" onclick="$('.field').get(%s).innerHTML += `<img src='%s'/>`; $(this.parentNode.parentNode).remove(); %s"><i class='fa fa-plus-square-o mr-10'></i>%s</span><br>""" % (i, img_src, fld_update_js, f["name"])
        modal = modal % (img_src, flds, io, img_src)
        return "$('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

    @classmethod
    @js
    def show_cloze_field_picker_modal(cls, cloze_text: str) -> JS:
        """
        Shows a modal that lists all fields of the current note.
        When a field is selected, the cloze text is appended to that field.
        """

        cloze_text  = cloze_text.replace("`", "").replace("\n", "")
        modal       = """ <div class="siac-modal-small dark ta_center">
                        <b>Append to field:</b><br><br>
                        <div class='oflow_y_auto ta_left' style="max-height: 200px; margin: 0 40px; padding-left:4px; overflow-x: hidden;">%s</div><br><br>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                    </div> """
        flds        = ""

        for i, f in enumerate(cls._editor.note.model()['flds']):
            flds += """<span class="siac-field-picker-opt" onclick="appendToField({0}, `{1}`); $(this.parentNode.parentNode).remove(); pycmd('siac-last-cloze {2}');"><i class='fa fa-plus-square-o mr-10'></i>{3}</span><br>""".format(i, cloze_text, f["name"], f["name"])
        modal       = modal % (flds)

        return "$('#siac-pdf-tooltip').hide(); $('#siac-reading-modal-center').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

    @classmethod
    @js
    def show_iframe_overlay(cls, url: Optional[str] = None) -> JS:
        js = """
            if (pdf.instance) {
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

    @classmethod
    @js
    def hide_iframe_overlay(cls) -> JS:
        js = """
            document.getElementById('siac-iframe').src = "";
            document.getElementById('siac-iframe').style.display = "none";
            document.getElementById('siac-close-iframe-btn').style.display = "none";
            if (pdf.instance) {
                document.getElementById('siac-pdf-top').style.display = "flex";
            } else {
                document.getElementById('siac-text-top-wr').style.display = "flex";
            }
            iframeIsDisplayed = false;
        """
        return js

    @classmethod
    @js
    def show_web_search_tooltip(cls, inp: str) -> JS:
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
                    name = re.sub("^https?://(www2?.)?", "", name)
                    search_sources += """<div class="siac-url-ch" onclick='pycmd("siac-url-srch $$$" + document.getElementById("siac-tt-ws-inp").value + "$$$%s"); $(this.parentNode.parentNode).remove();'>
                                            <i class="fa fa-search"></i>&nbsp; %s
                                        </div>""" % (url, name)

        modal = """ <div class="siac-modal-small dark ta_center">
                        <label class='siac-caps'>Search Text</label>
                        <input class='siac-rm-bg w-100' id="siac-tt-ws-inp" value="%s"></input>
                        <br/>
                        <div class='cursor-pointer oflow_y_auto' style="max-height: 200px; overflow-x: hidden; margin-top: 15px; text-align: left;">%s</div><br><br>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                    </div> """  % (inp, search_sources)

        js = """
        $('#siac-iframe-btn').removeClass('expanded');
        $('#siac-pdf-tooltip').hide();
        $('#siac-reading-modal-center').append('%s');
        """ % modal.replace("\n", "").replace("'", "\\'")
        return js

    #region page sidebar

    @classmethod
    def page_sidebar_info(cls, page: int, pages_total: int):
        """ Fill the page sidebar with Anki notes made on that page / other pdf info. """

        if page == -1:
            linked              = get_linked_anki_notes(cls.note_id)
            around              = []
        else:
            linked              = get_linked_anki_notes_for_pdf_page(cls.note_id, page)
            around              = get_linked_anki_notes_around_pdf_page(cls.note_id, page)
        read_today          = get_read_today_count()
        added_today_count   = utility.misc.count_cards_added_today()

        around_s            = ""
        around_d            = {  p: 0  for p in set(around) }
        for p in around:
            around_d[p] += 1

        upper               = page + 4 + abs(min(0, page - 4))
        lower               = page - 3 - (3 - min(pages_total - page, 3))

        for p_ix in range(max(1, lower), min(upper, pages_total + 1)):
            if not p_ix in around_d:
                around_d[p_ix] = 0

        for p_ix in range(max(1, lower), min(upper, pages_total + 1)):
            c = around_d[p_ix]
            if c == 0:
                if page == p_ix:
                    around_s += f"<span onclick='pycmd(\"siac-linked-to-page {p_ix} \" + pdf.instance.numPages)' class='siac-pa-sq empty current'>-</span>"
                else:
                    around_s += f"<span onclick='pycmd(\"siac-linked-to-page {p_ix} \" + pdf.instance.numPages)' class='siac-pa-sq empty'>-</span>"
            else:
                if page == p_ix:
                    around_s += f"<span onclick='pycmd(\"siac-linked-to-page {p_ix} \" + pdf.instance.numPages)' class='siac-pa-sq current'>{c}</span>"
                else:
                    around_s += f"<span onclick='pycmd(\"siac-linked-to-page {p_ix} \" + pdf.instance.numPages)' class='siac-pa-sq'>{c}</span>"

        if page != -1:
            header = f"{page} / {pages_total}"
        else:
            header = f"Anki Notes ({len(linked)})"
        if around_s != "":
            around_s = f"<center class='siac-page-sidebar-around'>{around_s}</center>"


        stats_s = f"""<div class='fg_lightgrey ta_center' style='flex: 0 1 auto; margin-top: 15px; padding-top: 5px; border-top: 4px double grey;'>
                    <i class="fa fa-bar-chart"></i>:&nbsp; Read <b>{read_today}</b> page{"s" if read_today != 1 else ""},
                    added <b>{added_today_count}</b> card{"s" if added_today_count != 1 else ""}
                </div>"""
        if len(linked) > 0:
            html = UI.get_result_html_simple(linked, tag_hover=False, search_on_selection=False, query_set=None)
            html = html.replace("`", "\\`")
            html = f"""
                <div class='fg_lightgrey siac-page-sidebar-header'>
                    <center class='siac-note-header'><b>{header}</b></center>
                    {around_s}
                </div>
                <div style='overflow-y: auto; flex: 1 1 auto; padding: 7px 6px 7px 6px; text-align: left;'>
                    {html}
                </div>
                {stats_s}"""
        else:
            html = f"""
                <div class='fg_lightgrey siac-page-sidebar-header'>
                    <center class='siac-note-header'><b>{header}</b></center>
                    {around_s}
                </div>
                <div class='fg_lightgrey flex-col' style='flex: 1 1 auto; justify-content: center;'>
                    <div class='mb-10' style='font-size: 25px;'><i class="fa fa-graduation-cap"></i></div>
                    <center class='bold' style='padding: 20px; font-variant-caps: small-caps; font-size: medium;'>No notes added while on this page.</center>
                </div>
                {stats_s}"""

        cls._editor.web.eval(f"document.getElementById('siac-page-sidebar').innerHTML = `{html}`;")

    #endregion page sidebar

    @classmethod
    @js
    def show_pdf_bottom_tab(cls, note_id: int, tab: str) -> JS:
        """ Context: Clicked on a tab (Marks / Related / Info) in the bottom bar. """

        tab_js = f"$('.siac-link-btn.tab').removeClass('active'); bottomBarTabDisplayed = '{tab}';"
        if tab == "marks":
            return f"""{tab_js}
            $('.siac-link-btn.tab').eq(0).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`<div id='siac-marks-display' onclick='markClicked(event);'></div>`;
            updatePdfDisplayedMarks(false);"""
        if tab == "info":
            html = cls.get_note_info_html().replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-link-btn.tab').eq(2).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""
        if tab == "related":
            html = cls.get_related_notes_html().replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-link-btn.tab').eq(1).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""
        if tab == "pages":
            html = cls.get_page_map_html().replace("`", "&#96;")
            return f"""{tab_js}
            $('.siac-link-btn.tab').eq(3).addClass('active');
            document.getElementById('siac-pdf-bottom-tab').innerHTML =`{html}`;"""

    @classmethod
    def get_page_map_html(cls) -> HTML:
        """ Context: Clicked on 'Page' tab in the bottom bar. """

        pages = get_read_pages(cls.note_id)
        total = get_read_stats(cls.note_id)
        if total is None or total[2] <= 0:
            return ""
        total = total[2]
        html  = ""
        e_st  = 0 if not cls.note.extract_start else cls.note.extract_start
        c     = 0
        limit = 25
        for ix in range(max(1, e_st), max(1, e_st) + total):

            if c % limit == 0:
                if c > 0:
                    html = f"{html}<br>"
                html = f"{html}<span class='sq-lbl'>{c+1}-{c + min(limit, total - c)}</span>"
            c += 1
            if ix in pages:
                html = f"{html}<i class='sq-r sq-rg' onclick='pdfGotoPg({ix})'></i>"
            else:
                html = f"{html}<i class='sq-r' onclick='pdfGotoPg({ix})'></i>"

        if total < 50:
            html = f"<div class='mt-10' style='line-height: 1em;'>{html}</div>"
        else:
            html = f"<div style='line-height: 1em;'>{html}</div>"
        return html


    @classmethod
    def get_related_notes_html(cls) -> HTML:
        """ Context: Clicked on 'Related' tab in the bottom bar. """

        note_id = cls.note_id
        r       = get_related_notes(note_id)
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
                        ids.add(i.id)
                        res.append(i)
                if len(res) > 20:
                    break
        if len(res) < 20 and len(r.related_by_title) > 0:
            for r2 in r.related_by_title:
                if not r2.id in ids:
                    ids.add(r2.id)
                    res.append(r2)
                    if len(res) >= 20:
                        break

        if len(res) < 20 and len(r.related_by_folder) > 0:
            for r3 in r.related_by_folder:
                if not r3.id in ids:
                    res.append(r3)
                    if len(res) >= 20:
                        break

        res = list({x.id: x for x in res}.values())

        for rel in res[:20]:
            if rel.id == note_id:
                continue
            title               = utility.text.trim_if_longer_than(rel.get_title(), 70)
            pdf_or_feed         = rel.is_pdf() or rel.is_feed()
            should_show_loader  = 'document.getElementById("siac-reading-modal-center").innerHTML = ""; showPDFLoader();' if pdf_or_feed else ""
            html                = f"{html}<div class='siac-related-notes-item' onclick='if (!pdfLoading) {{ {should_show_loader}  destroyPDF(); noteLoading = true; greyoutBottom(); pycmd(\"siac-read-user-note {rel.id}\"); }}'>{title}</div>"
        return html


    @classmethod
    def get_queue_infobox(cls, note: SiacNote, read_stats: Tuple[Any, ...]) -> HTML:
        """ Returns the html that is displayed in the tooltip which appears when hovering over an item in the queue head. """

        diff        = datetime.datetime.now() - datetime.datetime.strptime(note.created, '%Y-%m-%d %H:%M:%S')
        time_str    = "Created %s ago." % utility.date.date_diff_to_string(diff)

        # pagestotal might be None (it is only available if at least one page has been read)
        if read_stats[2] is not None:
            prog_bar    = cls.pdf_prog_bar(read_stats[0], read_stats[2])
            pages_read  = "<div class='bold w-100 ta_center' style='margin-top: 3px; font-size: 20px;'>%s / %s</div>" % (read_stats[0], read_stats[2])
        elif not note.is_yt():
            text_len    = f"{len(note.text.split())} Words" if note.text is not None and len(note.text) > 0 else "Empty"
            prog_bar    = ""
            pages_read  = f"<div class='bold w-100 ta_center' style='margin-top: 7px; font-size: 16px;'>Text Note, {text_len}</div>"
        else:
            prog_bar    = ""
            time        = utility.text.get_yt_time(note.source.strip())
            if not time or time == 0:
                time    = "Beginning"
            else:
                secs    = time % 60
                if secs < 10:
                    secs = f"0{secs}"
                time    = f"{int(time / 60)}:{secs}"
            pages_read  = f"<div class='bold w-100 ta_center' style='margin-top: 7px; font-size: 16px;'>Video, {time}</div>"

        html = """
            <div class='w-100 h-100' style='box-sizing: border-box; padding: 10px; display: inline-block; position: relative; vertical-align: top;'>
                <div class='ta_center w-100 bold' style='white-space: nowrap; overflow: hidden; vertical-align: top; text-overflow: ellipsis;'>{title}</div>
                <div class='fg_lightgrey ta_center w-100 oflow_hidden' style='white-space: nowrap; vertical-align: top;'>{time_str}</div>
                {pages_read}
                <div class='w-100 ta_center' style='padding: 5px 0 10px 0;'>
                    <div style='display: inline-block; vertical-align: bottom;'>
                        {prog_bar}
                    </div>
                </div>
            </div>

        """.format_map(dict(title = note.get_title(), pages_read=pages_read, time_str= time_str, prog_bar= prog_bar, nid = note.id))
        return html


    @classmethod
    def pdf_prog_bar(cls, read: Optional[int], read_total: Optional[int]) -> HTML:
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

    @classmethod
    @js
    def mark_range(cls, start: int, end: int, pages_total: int, current_page: int) -> JS:
        if start <= 0:
            start = 1
        if cls.note.extract_start is not None and start < cls.note.extract_start:
            start = cls.note.extract_start
        if cls.note.extract_start is None and end > pages_total:
            end = pages_total
        if cls.note.extract_start is not None and end > cls.note.extract_end:
            end = cls.note.extract_end
        if end <= start or (cls.note.extract_start is None and start >= pages_total) or (cls.note.extract_start is not None and start >= pages_total + cls.note.extract_start):
            return

        mark_range_as_read(cls.note_id, start, end, pages_total)

        pages_read  = get_read_pages(cls.note_id)
        js          = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])
        js          = f"pdf.pagesRead = [{js}];"

        if current_page >= start and current_page <= end:
            js += "pdfShowPageReadMark();"

        return f"{js}updatePdfProgressBar();"

    @classmethod
    @js
    def display_cloze_modal(cls, editor: Editor, selection: str, extracted: List[str]) -> JS:
        """ Displays the modal to view and edit the generated cloze. """

        s_html      = "<table style='margin-top: 5px; font-size: 15px;'>"
        sentences   = [s for s in extracted if len(s) < 300 and len(s.strip()) > 0]

        if len(sentences) == 0:
            for s in extracted:
                if len(s) >= 300:
                    f = utility.text.try_find_sentence(s, selection)
                    if f is not None and len(f) < 300:
                        sentences.append(f)

        # we use a list here, but atm, there is only one sentence
        if len(sentences) > 0 and sentences != [""]:
            selection = re.sub("  +", " ", selection).strip()
            for sentence in sentences:
                sentence = re.sub("  +", " ", sentence).strip()
                sentence = sentence.replace(selection, " <span style='color: lightblue;'>{{c1::%s}}</span> " % selection)

                # try to get some sensible formatting (mostly trimming whitespaces where they not belong)
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
                sentence = re.sub(" \(([\"“”]) ", r" (\1", sentence)
                sentence = re.sub(" ([\"“”])\)", r"\1)", sentence)
                sentence = sentence.replace("[ ", "[")
                sentence = sentence.replace(" ]", "]")
                sentence = re.sub(" ([,;:.]) ", r"\1 ", sentence)
                sentence = re.sub(r"\( *(.+?) *\)", r"(\1)", sentence, re.DOTALL)
                sentence = re.sub(" ([?!.])$", r"\1", sentence)
                sentence = re.sub("^[:.?!,;)] ", "", sentence)
                sentence = re.sub("^\\d+ ?[:\\-.,;] ([A-ZÖÄÜ])", r"\1", sentence)
                sentence = re.sub(" ([\"“”])([?!.])$", r"\1\2", sentence)

                # remove enumeration dots from the beginning of the sentence
                sentence = re.sub("^[\u2022,\u2023,\u25E6,\u2043,\u2219]", "", sentence)

                s_html += "<tr class='siac-cl-row'><td><div contenteditable class='siac-pdf-main-color'>%s</div></td></tr>" % (sentence.replace("`", "&#96;"))
            s_html += "</table>"
            model_id = cls._editor.note.model()['id']

            # if another Send to Field has been executed before, and the note type is the same, add another button
            # to directly send the cloze to that last used field.
            last_btn = ""
            if Reader.last_cloze is not None and model_id == Reader.last_cloze[0]:
                ix          = [f["name"] for f in cls._editor.note.model()["flds"]].index(Reader.last_cloze[1])
                last_btn    = f"<div class='siac-btn siac-btn-dark mt-5' style='margin-right: 15px;' onclick=\"appendToField({ix}, $('.siac-cl-row div').first().text());  $('#siac-pdf-tooltip').hide();\">'{utility.text.trim_if_longer_than(Reader.last_cloze[1], 15)}'</div>"

            btn_html = """document.getElementById('siac-pdf-tooltip-bottom').innerHTML = `
                                <div style='margin-top: 8px;'>
                                    %s
                                    <div class='siac-btn siac-btn-dark' onclick='pycmd("siac-fld-cloze " +$(".siac-cl-row div").first().text());' style='margin-right: 15px; margin-top: 5px;'>Send to Field...</div>
                                    <div class='siac-btn siac-btn-dark' onclick='generateClozes();' style='margin-top: 5px;'>&nbsp;<i class='fa fa-bolt'></i>&nbsp; Generate</div>
                                </div>
                    `;""" % last_btn

        else:
            s_html = "<br><center>Sorry, could not extract any sentences.</center>"
            btn_html = ""

        return """
                document.getElementById('siac-pdf-tooltip-results-area').innerHTML = `%s`;
                document.getElementById('siac-pdf-tooltip-top').innerHTML = `<span class='fg_lightgrey;'>(Click inside to edit, <i>Ctrl+Shift+C</i> to add new Clozes)</span>`;
                document.getElementById('siac-pdf-tooltip-searchbar').style.display = "none";
                %s
                """ % (s_html, btn_html)

    @classmethod
    @js
    def notification(cls, html: HTML, on_ok: Optional[JS] = None) -> JS:
        if on_ok is None:
            on_ok = ""
        modal = f""" <div class="siac-modal-small dark ta_center fg_lightgrey" contenteditable="false">
                        {html}
                        <br/> <br/>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); $('#siac-rm-greyout').hide(); {on_ok}">&nbsp; Ok &nbsp;</div>
                    </div> """
        return """$('#siac-pdf-tooltip').hide();
                $('.siac-modal-small').remove();
                $('#siac-rm-greyout').show();
                $('#siac-reading-modal-center').append('%s');""" % modal.replace("\n", "").replace("'", "\\'")

    @classmethod
    @js
    def jump_to_last_read_page(cls) -> JS:
        return """
            if (pdf.pagesRead && pdf.pagesRead.length) {
                pdf.page = Math.max(...pdf.pagesRead);
                rerenderPDFPage(pdf.page, false, true);
            }
        """

    @classmethod
    @js
    def jump_to_random_unread_page(cls) -> JS:
        return """
            if (pdf.instance) {
                const start = pdf.extract ? pdf.extract[0] : 1;
                const options = [];
                for (var i = start; i < start + numPagesExtract(); i++) {
                    if (!pdf.pagesRead || pdf.pagesRead.indexOf(i) === -1) {
                        options.push(i);
                    }
                }
                if (options.length > 0) {
                    pdf.page = options[Math.floor(Math.random() * options.length)];
                    rerenderPDFPage(pdf.page, false, true);
                }
            }
        """
    @classmethod
    @js
    def jump_to_first_unread_page(cls) -> JS:
        return """
            if (pdf.instance) {
                let start = pdf.extract ? pdf.extract[0] : 1;
                for (var i = start; i < start + numPagesExtract(); i++) {
                    if (!pdf.pagesRead || pdf.pagesRead.indexOf(i) === -1) {
                        pdf.page = i;
                        rerenderPDFPage(pdf.page, false, true);
                        break;
                    }
                }
            }
        """



    #
    # highlights
    #

    @classmethod
    def show_highlights_for_page(cls, page: int):
        highlights = get_highlights(cls.note_id, page)
        if highlights is not None and len(highlights) > 0:
            js = ""
            for rowid, nid, page, type, grouping, x0, y0, x1, y1, text, data, created in highlights:
                text = text.replace("`", "")
                js = f"{js},[{x0},{y0},{x1},{y1},{type},{rowid}, `{text}`]"
            js = js[1:]
            UI.js("Highlighting.current = [%s]; Highlighting.displayHighlights();" % js)



