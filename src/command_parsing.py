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


from aqt import mw
from aqt.qt import *
import aqt
import aqt.webview
import aqt.editor
import aqt.stats
from anki.notes import Note
from aqt.utils import tooltip, showInfo, isMac
import os
import time
import urllib.parse
import json
from datetime import datetime
import typing
from typing import List, Dict, Any, Optional, Tuple


from .state import check_index, get_index, set_index, set_corpus
from .index.indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import *
from .web.html import *
from .web.reading_modal import ReadingModal
from .special_searches import *
from .internals import requires_index_loaded, js, perf_time
from .notes import *
from .notes import _get_priority_list
from .hooks import run_hooks
from .output import Output
from .dialogs.editor import openEditor, NoteEditor
from .dialogs.queue_picker import QueuePicker
from .dialogs.quick_schedule import QuickScheduler
from .dialogs.url_import import UrlImporter
from .dialogs.pdf_extract import PDFExtractDialog
from .dialogs.zotero_import import ZoteroImporter
from .dialogs.schedule_dialog import ScheduleDialog
from .tag_find import findBySameTag, display_tag_info
from .stats import calculateStats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval
from .models import SiacNote
try:
    from .previewer import AddPreviewer
except: 
    pass
import utility.misc
import utility.text
import state

""" command_parsing.py - Mainly used to catch pycmds from the web view, and trigger the appropriate actions for them. """

config                  = mw.addonManager.getConfig(__name__)
REV_FILTERED_DECK_NAME  = "PDF Review"

def expanded_on_bridge_cmd(handled: Tuple[bool, Any], cmd: str, self: Any) -> Tuple[bool, Any]:
    """
    Process the various commands coming from the ui -
    this includes users clicks on option checkboxes, on rendered results, on special searches, etc.

    Todo: Needs some serious cleanup / splitting up.
    Todo: Maybe move cmd handling to components (reading_modal, sidebar, index)
    """
    if not isinstance(self, aqt.editor.Editor):
        return handled

    state.last_cmd    = cmd
    if cmd.startswith("siac-r-"):
        state.last_search_cmd       = cmd
        state.last_page_requested   = None

    index       = get_index()
    # just to make sure
    if index is not None and index.ui._editor is None:
        index.ui.set_editor(self)

    # there has to be a more elegant way of processing the cmds than a giant if else...

    # In general, cmds should start with "siac-" to avoid collisions with other add-ons and for easier debugging.
    # Commands that render some kind of result should start with "siac-r-",
    # so that they can be stored and repeated if the UI needs to be refreshed.

    if cmd.startswith("siac-r-fld "):
        # keyup in fields -> search
        rerender_info(self, cmd[10:])

    elif cmd.startswith("siac-page "):
        # Page button in results clicked.
        # This is a special command, it triggers a rendering, but should not be stored 
        # as last command in state.last_search_cmd like other cmds that start with "siac-r-".
        # That is because the index.ui instance caches the last result, and uses that cached result to display 
        # a requested page (but to refresh the UI, we don't want the result to be cached).
        # So if we want to refresh the UI, state.last_search_cmd should point to the cmd that produces the search results, 
        # and state.last_page_requested indicates that we are on a page other than the first at the time of refresh.
        state.last_page_requested = int(cmd.split()[1])
        index.ui.show_page(self, int(cmd.split()[1]))

    elif cmd.startswith("siac-r-srch-db "):
        # bottom search input used, so trigger either an add-on search or a browser search
        if index.searchbar_mode.lower() == "add-on":
            rerender_info(self, cmd[15:])
        else:
            rerender_info(self, cmd[15:], searchDB = True)

    elif cmd.startswith("siac-r-fld-selected ") and index is not None:
        # selection in field or note
        rerender_info(self, cmd[20:])

    elif cmd.startswith("siac-note-stats "):
        # note "Info" button clicked
        set_stats(cmd[16:], calculateStats(cmd[16:], index.ui.gridView))

    elif cmd.startswith("siac-tag-clicked "):
        # clicked on a tag -> either trigger a search or add the tag to the tag bar
        if config["tagClickShouldSearch"]:
            state.last_search_cmd = cmd
            search_by_tags(cmd[17:].strip())
        else:
            add_tag(cmd[17:])

    elif cmd.startswith("siac-edit-note "):
        # "Edit" clicked on a normal (Anki) note
        openEditor(mw, int(cmd[15:]))

    elif cmd.startswith("siac-eval "):
        # direct eval, saves code
        eval(cmd[10:])
    elif cmd.startswith("siac-exec "):
        # direct exec, saves code
        exec(cmd[10:])

    elif cmd.startswith("siac-open-folder "):
        # try to open a folder path with the default explorer
        folder = " ".join(cmd.split()[1:]).replace("\\", "/")
        if not folder.endswith("/"):
            folder += "/"
        if os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl("file:///" + folder))

    elif cmd.startswith("siac-pin"):
        # pin note symbol clicked
        set_pinned(cmd[9:])

    elif cmd == "siac-zoom-out":
        # zoom out webview
        z   = get_config_value_or_default("searchpane.zoom", 1.0)
        new = round(max(0.3, z - 0.05), 2)
        self.web.setZoomFactor(new)
        tooltip(f"Set Zoom to <b>{str(int(new * 100))}%</b>")
        update_config("searchpane.zoom", new)
    elif cmd == "siac-zoom-in":
        # zoom in webview
        z   = get_config_value_or_default("searchpane.zoom", 1.0)
        new = round(min(2.0, z + 0.05), 2)
        self.web.setZoomFactor(new)
        tooltip(f"Set Zoom to <b>{str(int(new * 100))}%</b>")
        update_config("searchpane.zoom", new)

 
    elif cmd.startswith("siac-render-tags"):
        # clicked on a tag with (+n) 
        index.ui.printTagHierarchy(cmd[16:].split(" "))

    elif cmd.startswith("siac-r-random-notes ") and check_index():
        # RANDOM clicked
        res = getRandomNotes(index, [s for s in cmd[19:].split(" ") if s != ""])
        index.ui.print_search_results(res["result"], res["stamp"])

    elif cmd == "siac-fill-deck-select":
        fillDeckSelect(self, expanded=True, update=False)

    elif cmd == "siac-fill-tag-select":
        fillTagSelect(expanded=True)

    elif cmd.startswith("siac-r-search-tag "):
        search_by_tags(cmd[18:].strip())

    elif cmd.startswith("siac-tag-info "):
        #this renders the popup
        display_tag_info(self, cmd.split()[1], " ".join(cmd.split()[2:]), index)

    elif cmd.startswith("siac-copy-to-cb "):
        # copy to clipboard
        try:
            QApplication.clipboard().setText(cmd[16:])
            tooltip("Copied to Clipboard!")
        except: 
            tooltip("Failed to copy to clipboard!")

    elif cmd.startswith("siac-copy-cid-to-cb "):
        # copy first cid for given nid to clipboard
        cards = mw.col.findCards(f"nid:{cmd.split()[1]}")
        if cards and len(cards) > 0:
            try:
                QApplication.clipboard().setText(str(cards[0]))
                tooltip("Copied to Clipboard!")
            except: 
                tooltip("Failed to copy to clipboard!")

    elif cmd.startswith("siac-rerender "):
        ix = int(cmd.split()[1])
        if check_index() and ix < len(index.ui.previous_calls):
            index.ui.print_search_results(*index.ui.previous_calls[ix] + [True])

    elif cmd == "siac-rerender":
        index.ui.try_rerender_last()

    elif cmd.startswith("siac-config-bool "):
        key = cmd.split()[1]
        b   = cmd.split()[2].lower() == "true" or cmd.split()[2].lower() == "on"
        update_config(key, b)

    elif cmd.startswith("siac-notification "):
        tooltip(cmd[18:])

    elif cmd.startswith("siac-unsuspend-modal "):
        nid = cmd.split()[1]
        show_unsuspend_modal(nid)

    elif cmd.startswith("siac-unsuspend "):
        nid = cmd.split()[1]
        cids = [int(cid) for cid in cmd.split()[2:]]
        mw.col.sched.unsuspendCards(cids)
        show_unsuspend_modal(nid)

    elif cmd == "siac-r-show-pdfs":
        stamp = set_stamp()
        notes = get_all_pdf_notes()
        # add special note at front
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-show-text-notes":
        stamp = set_stamp()
        notes = get_all_text_notes()
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-show-video-notes":
        stamp = set_stamp()
        notes = get_all_video_notes()
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-show-pdfs-unread":
        if check_index():
            stamp = set_stamp()
            notes = get_all_unread_pdf_notes()
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-show-pdfs-in-progress":
        if check_index():
            stamp = set_stamp()
            notes = get_in_progress_pdf_notes()
            index.ui.print_search_results(notes, stamp)
    
    elif cmd == "siac-r-show-due-today":
        stamp = set_stamp()
        notes = get_notes_scheduled_for_today()
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-show-stats":
        # Read Stats clicked in sidebar
        show_read_stats()

    elif cmd == "siac-r-show-last-done":
        stamp = set_stamp()
        notes = get_last_done_notes()
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-pdf-last-read":
        stamp = set_stamp()
        notes = get_pdf_notes_last_read_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-pdf-last-added":
        stamp = set_stamp()
        notes = get_pdf_notes_last_added_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-r-pdf-size "):
        stamp = set_stamp()
        notes = get_pdf_notes_ordered_by_size(cmd.split()[1])
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-pdf-find-invalid":
        stamp = set_stamp()
        notes = get_invalid_pdfs()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-queue-info "):
        nid         = int(cmd.split()[1])
        note        = get_note(nid)
        read_stats  = get_read_stats(nid)
        index.ui.js("""
            if (pdfLoading || noteLoading || modalShown) {
                hideQueueInfobox();
            } else {
                document.getElementById('siac-pdf-bottom-tabs').style.visibility = "hidden";
                document.getElementById('siac-queue-infobox').style.display = "block";
                document.getElementById('siac-queue-infobox').innerHTML =`%s`;
            }
        """ % index.ui.reading_modal.get_queue_infobox(note, read_stats))

    elif cmd.startswith("siac-pdf-selection "):
        stamp = set_stamp()
        if check_index():
            index.search(cmd[19:], ["-1"], only_user_notes = False, print_mode = "pdf")

    elif cmd.startswith("siac-pdf-tooltip-search "):
        inp = cmd[len("siac-pdf-tooltip-search "):]
        if len(inp.strip()) > 0:
            if check_index():
                stamp = set_stamp()
                index.search(inp, ["-1"], only_user_notes = False, print_mode = "pdf")

    elif cmd.startswith("siac-cutout-io "):
        img_src     = " ".join(cmd.split()[1:])
        full_path   = os.path.join(mw.col.media.dir(), img_src).replace("\\", "/")
        self.onImgOccButton(image_path=full_path)

    elif cmd.startswith("siac-create-pdf-extract "):
        dialog = PDFExtractDialog(self.parentWindow, int(cmd.split(" ")[1]), int(cmd.split(" ")[2]), index.ui.reading_modal.note)

    elif cmd.startswith("siac-jump-last-read"):
        index.ui.reading_modal.jump_to_last_read_page()

    elif cmd.startswith("siac-jump-first-unread"):
        index.ui.reading_modal.jump_to_first_unread_page()

    elif cmd.startswith("siac-mark-read-up-to "):
        mark_as_read_up_to(index.ui.reading_modal.note, int(cmd.split()[2]), int(cmd.split()[3]))
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-display-range-input "):
        nid         = int(cmd.split()[1])
        num_pages   = int(cmd.split()[2])
        index.ui.reading_modal.display_read_range_input(nid, num_pages)

    elif cmd.startswith("siac-user-note-mark-range "):
        start           = int(cmd.split()[2])
        end             = int(cmd.split()[3])
        pages_total     = int(cmd.split()[4])
        current_page    = int(cmd.split()[5])
        index.ui.reading_modal.mark_range(start, end, pages_total, current_page)
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-mark-all-read "):
        mark_all_pages_as_read(index.ui.reading_modal.note, int(cmd.split()[2]))
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-mark-all-unread "):
        mark_all_pages_as_unread(int(cmd.split()[1]))
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-insert-pages-total "):
        insert_pages_total(int(cmd.split()[1]), int(cmd.split()[2]))

    elif cmd.startswith("siac-show-cloze-modal "):
        selection = " ".join(cmd.split()[1:]).split("$$$")[0]
        sentences = cmd.split("$$$")[1:]
        index.ui.reading_modal.display_cloze_modal(self, selection, sentences)

    elif cmd.startswith("siac-linked-to-page "):
        page  = int(cmd.split()[1])
        total = int(cmd.split()[2])
        index.ui.reading_modal.page_sidebar_info(page, total)

    elif cmd == "siac-url-dialog":
        dialog = UrlImporter(self.parentWindow)
        if dialog.exec_():
            if dialog.chosen_url:
                sched   = dialog.queue_schedule
                name    = dialog.get_name()
                path    = get_config_value("pdfUrlImportSavePath")
                path    = utility.misc.get_pdf_save_full_path(path, name)
                utility.misc.url_to_pdf(dialog.chosen_url, path, lambda *args: tooltip("Generated PDF Note.", period=4000))
                title = dialog._chosen_name
                if title is None or len(title) == 0:
                    title = name
                create_note(title, "", path, "", "", "", sched)
            else:
                pass

    elif cmd == "siac-zotero-import":
        dialog = ZoteroImporter(self.parentWindow)
        if dialog.exec_():
            tooltip(f"Created {dialog.total_count} notes.")

    elif cmd == "siac-schedule-dialog":
        # show the dialog that allows to change the schedule of a note
        show_schedule_dialog(self.parentWindow)

    elif cmd == "siac-delay-note":
        # "Later" button pressed in the reading modal
        qlen = len(_get_priority_list())
        if qlen > 2:
            delay = int(qlen/3) 
            if index.ui.reading_modal.note.position < 3:
                delay += (3 - index.ui.reading_modal.note.position)
            set_delay(index.ui.reading_modal.note_id, delay)
            recalculate_priority_queue()
            nid = get_head_of_queue()
            index.ui.reading_modal.display(nid)
            tooltip("Moved note back in queue")
        else:
            tooltip("Later only works if 3+ items are in the queue.")

    elif cmd.startswith("siac-pdf-mark "):
        mark_type       = int(cmd.split()[1])
        nid             = int(cmd.split()[2])
        page            = int(cmd.split()[3])
        pages_total     = int(cmd.split()[4])
        marks_updated   = toggle_pdf_mark(nid, page, pages_total, mark_type)
        js_maps         = utility.misc.marks_to_js_map(marks_updated)
        self.web.eval(""" pdfDisplayedMarks = %s; pdfDisplayedMarksTable = %s; updatePdfDisplayedMarks(true);""" % (js_maps[0], js_maps[1]))

    elif cmd == "siac-reading-modal-tabs-left-browse":
        # clicked on "Browse" in the tabs on the fields' side.
        index.ui.reading_modal.show_browse_tab()

    elif cmd == "siac-reading-modal-tabs-left-flds":
        # clicked on "Fields" in the tabs on the fields' side.
        index.ui.reading_modal.show_fields_tab()

    elif cmd == "siac-reading-modal-tabs-left-pdfs":
        # clicked on "Fields" in the tabs on the fields' side.
        index.ui.reading_modal.show_pdfs_tab()

    elif cmd.startswith("siac-pdf-left-tab-anki-search "):
        # search input coming from the "Browse" tab in the pdf viewer
        inp = " ".join(cmd.split(" ")[1:])
        index.search(inp, ["-1"], only_user_notes = False, print_mode = "pdf.left")

    elif cmd.startswith("siac-pdf-left-tab-pdf-search "):
        # search input coming from the "PDFs" tab in the pdf viewer
        inp = " ".join(cmd.split(" ")[1:])
        if inp: 
            notes = find_pdf_notes_by_title(inp)
            index.ui.reading_modal.sidebar.print(notes)

    elif cmd.startswith("siac-p-sort "):
        if check_index():
            parse_sort_cmd(cmd[12:])

    elif cmd == "siac-model-dialog":
        display_model_dialog()

    elif cmd.startswith("siac-r-added-same-day "):
        if check_index():
            getCreatedSameDay(index, self, int(cmd.split()[1]))

    elif cmd == "siac-last-timing":
        if index is not None and index.lastResDict is not None:
            show_timing_modal()

    elif cmd.startswith("siac-last-timing "):
        render_time = int(cmd.split()[1])
        if index is not None and index.lastResDict is not None:
            show_timing_modal(render_time)

    elif cmd.startswith("siac-cal-info "):
        # clicked on a square of the timeline
        if check_index():
            context_html    = get_cal_info_context(int(cmd[14:]))
            res             = get_notes_added_on_day_of_year(int(cmd[14:]), min(index.limit, 100))
            index.ui.print_timeline_info(context_html, res)

    elif cmd == "siac_rebuild_index":
        # we have to reset the ui because if the index is recreated, its values won't be in sync with the ui anymore
        self.web.eval("""
            $('#searchResults').html('').hide();
            $('#siac-pagination-wrapper,#siac-pagination-status,#searchInfo').html("");
            $('#toggleTop').removeAttr('onclick').unbind("click");
            $('#greyout').show();
            $('#loader').show();""")
        set_index(None)
        set_corpus(None)
        build_index(force_rebuild=True, execute_after_end=after_index_rebuilt)

    elif cmd.startswith("siac-searchbar-mode"):
        index.searchbar_mode = cmd.split()[1]

    #
    # Notes
    #

    elif cmd == "siac-create-note":
        if not state.note_editor_shown:
            NoteEditor(self.parentWindow)

    elif cmd.startswith("siac-create-note-add-only "):
        if not state.note_editor_shown:
            nid = int(cmd.split()[1])
            NoteEditor(self.parentWindow, add_only=True, read_note_id=nid)

    elif cmd.startswith("siac-create-note-tag-prefill "):
        if not state.note_editor_shown:
            tag = cmd.split()[1]
            NoteEditor(self.parentWindow, add_only=False, read_note_id=None, tag_prefill = tag)

    elif cmd.startswith("siac-create-note-source-prefill "):
        source = " ".join(cmd.split()[1:])
        existing = get_pdf_id_for_source(source)
        if existing > 0:
            index.ui.reading_modal.display(existing)
        else:
            if not state.note_editor_shown:
                NoteEditor(self.parentWindow, add_only=False, read_note_id=None, tag_prefill = None, source_prefill=source)
            else:
                tooltip("Close the opened note dialog first!")

    elif cmd.startswith("siac-edit-user-note "):
        if not state.note_editor_shown:
            id = int(cmd.split()[1])
            if id > -1:
                NoteEditor(self.parentWindow, id)

    elif cmd.startswith("siac-edit-user-note-from-modal "):
        if not state.note_editor_shown:
            id = int(cmd.split()[1])
            read_note_id = int(cmd.split()[2])
            if id > -1:
                NoteEditor(self.parentWindow, note_id=id, add_only=False, read_note_id=read_note_id)

    elif cmd.startswith("siac-delete-user-note-modal "):
        nid = int(cmd.split()[1])
        if nid > -1:
            display_note_del_confirm_modal(self, nid)

    elif cmd.startswith("siac-delete-user-note "):
        id = int(cmd.split()[1])
        delete_note(id)
        if index is not None:
            index.deleteNote(id)
        run_hooks("user-note-deleted")
        index.ui.js(""" $('#siac-del-modal').remove(); """)

    elif cmd.startswith("siac-delete-current-user-note "):
        # Delete a note, invoked from the reading modal
        id = int(cmd.split()[1])
        delete_note(id)
        if index is not None:
            index.deleteNote(id)
        run_hooks("user-note-deleted")
        tooltip("Deleted note.")
        if id == index.ui.reading_modal.note_id:
            head = get_head_of_queue()
            if head is None or head < 0:
                index.ui.js(""" onReadingModalClose(); """)
            else:
                index.ui.reading_modal.display(head)
        else:
            index.ui.reading_modal.reload_bottom_bar()

    elif cmd.startswith("siac-read-user-note "):
        id = int(cmd.split()[1])
        if id >= 0:
            index.ui.reading_modal.display(id)

    elif cmd == "siac-r-user-note-queue":
        stamp = set_stamp()
        notes = get_priority_list()
        if check_index():
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-user-note-queue-random":
        stamp = set_stamp()
        notes = get_queue_in_random_order()
        if check_index():
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-user-note-untagged":
        stamp = set_stamp()
        notes = get_untagged_notes()
        if check_index():
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-user-note-newest":
        stamp = set_stamp()
        if check_index():
            notes = get_newest(index.limit, index.pinned)
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-r-user-note-random":
        stamp = set_stamp()
        if check_index():
            notes = get_random(index.limit, index.pinned)
            index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-r-user-note-search-tag "):
        stamp = set_stamp()
        if check_index():
            notes = find_by_tag(" ".join(cmd.split()[1:]))
            index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-user-note-queue-picker "):
        # show the queue manager dialog
        nid     = int(cmd.split()[1])
        picker  = QueuePicker(self.parentWindow)
        if picker.exec_() and picker.chosen_id() is not None and picker.chosen_id() >= 0:
            # note = get_note(nid)
            index.ui.reading_modal.display(picker.chosen_id())
        else:
            if nid >= 0:
                index.ui.reading_modal.reload_bottom_bar(nid)

    elif cmd.startswith("siac-reload-reading-modal-bottom "):
        nid = int(cmd.split()[1])
        index.ui.reading_modal.reload_bottom_bar(nid)

    elif cmd == "siac-user-note-update-btns":
        queue_count = get_queue_count()
        self.web.eval("document.getElementById('siac-queue-btn').innerHTML = '&nbsp;<b>Queue [%s]</b>';" % queue_count)

    elif cmd == "siac-user-note-search":
        if check_index():
            index.ui.show_search_modal("searchForUserNote(event, this);", "Search For User Notes")

    elif cmd.startswith("siac-r-user-note-search-inp "):
        if check_index():
            search_for_user_notes_only(self, " ".join(cmd.split()[1:]))

    elif cmd.startswith("siac-update-note-text "):
        id = cmd.split()[1]
        text = " ".join(cmd.split(" ")[2:])
        update_note_text(id, text)


    elif cmd.startswith("siac-remove-from-queue "):
        to_remove = int(cmd.split(" ")[1])
        update_priority_list(to_remove, 0)
        if to_remove == index.ui.reading_modal.note_id:
            nid = get_head_of_queue()
            if nid is None or nid < 0:
                index.ui.js("onReadingModalClose();")
            else:
                index.ui.reading_modal.display(nid)
        else:
            index.ui.reading_modal.reload_bottom_bar()
        tooltip(f"<center>Removed from Queue.</center>")

    elif cmd == "siac-on-reading-modal-close":
        index.ui.reading_modal.reset()
        run_hooks("reading-modal-closed")

    elif cmd == "siac-user-note-queue-read-random":
        rand_id = get_random_id_from_queue()
        if rand_id >= 0:
            index.ui.reading_modal.display(rand_id)
        else:
            index.ui.js("ungreyoutBottom();noteLoading=false;pdfLoading=false;modalShown=false;")
            tooltip("Queue is Empty! Add some items first.", period=4000)

    elif cmd == "siac-user-note-queue-read-head":
        index.ui.reading_modal.read_head_of_queue() 

    elif cmd == "siac-user-note-done":
        # hit "Done" button in reading modal
        index.ui.reading_modal.done()

    elif cmd.startswith("siac-update-schedule "):
        stype           = cmd.split()[1]
        svalue          = cmd.split()[2]
        new_reminder    = utility.date.get_new_reminder(stype, svalue)
        update_reminder(index.ui.reading_modal.note_id, new_reminder)
        nid             = index.ui.reading_modal.note_id
        prio            = get_priority(nid)
        update_priority_list(nid, prio)
        nid             = get_head_of_queue()
        if nid is not None and nid >= 0:
            index.ui.reading_modal.display(nid)
        else:
            tooltip("Queue is Empty! Add some items first.", period=4000)

    elif cmd.startswith("siac-update-note-tags "):
        # entered tags in the tag line input in the reading modal bottom bar
        nid  = int(cmd.split()[1])
        tags = " ".join(cmd.split()[2:])
        tags = utility.text.clean_tags(tags)
        update_note_tags(nid, tags)
        index.ui.sidebar.refresh()

    elif cmd == "siac-try-copy-text-note":
        # copy to new note button clicked in reading modal
        nid  = index.ui.reading_modal.note_id
        note = get_note(nid)
        html = note.text
        prio = get_priority(nid)
        if html is None or len(html) == 0:
            tooltip("Note text seems to be empty.")
        else:
            if not state.note_editor_shown:
                NoteEditor(self.parentWindow, add_only=True, read_note_id=None, tag_prefill =note.tags, source_prefill=note.source, text_prefill=html, title_prefill = note.title, prio_prefill = prio)
            else:
                tooltip("Close the opened note dialog first!")

    elif cmd.startswith("siac-yt-save-time "):
        # save time clicked in yt player
        time = int(cmd.split()[1])
        src = index.ui.reading_modal.note.source 
        set_source(index.ui.reading_modal.note_id, utility.text.set_yt_time(src, time))


    elif cmd.startswith("siac-scale "):
        factor = float(cmd.split()[1])
        config["noteScale"] = factor
        write_config()
        if check_index():
            index.ui.scale = factor
            if factor != 1.0:
                index.ui.js("showTagInfoOnHover = false;")
            else:
                index.ui.js("showTagInfoOnHover = true;")

    elif cmd.startswith("siac-pdf-page-read"):
        nid = cmd.split()[1]
        page = cmd.split()[2]
        total = cmd.split()[3]
        mark_page_as_read(nid, page, total)
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-pdf-page-unread"):
        nid = cmd.split()[1]
        page = cmd.split()[2]
        mark_page_as_unread(nid, page)
        index.ui.js("updatePageSidebarIfShown()")

    elif cmd.startswith("siac-unhide-pdf-queue "):
        nid = int(cmd.split()[1])
        config["pdf.queue.hide"] = False
        write_config()
        index.ui.reading_modal.update_reading_bottom_bar(nid)

    elif cmd.startswith("siac-hide-pdf-queue "):
        nid = int(cmd.split()[1])
        config["pdf.queue.hide"] = True
        write_config()
        index.ui.reading_modal.update_reading_bottom_bar(nid)

    elif cmd == "siac-left-side-width":
        index.ui.reading_modal.show_width_picker()

    elif cmd.startswith("siac-quick-schedule "):
        # not used, wip
        nid = int(cmd.split()[1])
        scheduler = QuickScheduler(self.parentWindow, nid)
        if scheduler.exec_() and scheduler.queue_schedule is not None:
            update_priority_list(nid, scheduler.queue_schedule)
            index.ui.reading_modal.reload_bottom_bar(nid)

    elif cmd.startswith("siac-left-side-width "):
        value = int(cmd.split()[1])
        if value > 70:
            tooltip("Value capped at 70%.")
            value = 70
        config["leftSideWidthInPercent"] = value
        right = 100 - value
        if check_index():
            index.ui.js("""document.getElementById('leftSide').style.width = '%s%%';
                        document.getElementById('siac-right-side').style.width = '%s%%';
                        document.getElementById('siac-partition-slider').value = '%s';
                        if (pdfDisplayed) {pdfFitToPage();}""" % (value, right, value) )
        write_config()

    elif cmd.startswith("siac-switch-left-right "):
        config["switchLeftRight"] = cmd.split()[1]  == "true"
        write_config()
        tooltip("Layout switched.")

    elif cmd.startswith("siac-pdf-show-bottom-tab "):
        nid = int(cmd.split()[1])
        tab = cmd.split()[2]
        index.ui.reading_modal.show_pdf_bottom_tab(nid, tab)

    elif cmd == "siac-quick-schedule-fill":
        # when the quick schedule button in the reading modal is clicked and expanded
        nid = index.ui.reading_modal.note_id
        prio = get_priority(nid)
        if prio is None:
            index.ui.js(f"""$('#siac-quick-sched-btn .siac-btn-dark-smaller').last().hide();
                        $('#siac-prio-slider-small').val(0);
                        $('#siac-slider-small-lbl').html('0');
                        $('#siac-quick-sched-btn').toggleClass('expanded');""")
        else:
            index.ui.js(f"""$('#siac-quick-sched-btn .siac-btn-dark-smaller').last().show().html('<b>Current ({prio})</b>');
                            $('#siac-prio-slider-small').val({prio});
                            $('#siac-slider-small-lbl').html('{prio}');
                            $('#siac-quick-sched-btn').toggleClass('expanded');""")
    #
    #   Synonyms
    #

    elif cmd == "siac-synonyms":
        if check_index():
            index.ui.showInModal(get_synonym_dialog())
    elif cmd.startswith("siac-save-synonyms "):
        newSynonyms(cmd[19:])
        index.ui.showInModal(get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-edit-synonyms "):
        editSynonymSet(cmd[19:])
        index.ui.showInModal(get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-delete-synonyms "):
        deleteSynonymSet(cmd[21:])
        index.ui.showInModal(get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-r-synset-search "):
        if check_index():
            index.ui.hideModal()
            default_search_with_decks(self, cmd.split()[1], ["-1"])

    #
    # Settings Dialog
    # 

    elif cmd == "siac-styling":
        show_settings_modal(self)

    elif cmd.startswith("siac-styling "):
        update_styling(cmd[13:])

    elif cmd.startswith("siac-update-config-str "):
        key = cmd.split()[1]
        val = cmd.split()[2]
        update_config(key, val)

    elif cmd == "siac-write-config":
        # after the settings modal has been closed
        write_config()
        try_repeat_last_search(self)

    #
    # Image cutout in PDF viewer
    # 

    elif cmd.startswith("siac-add-image "):
        b64     = cmd.split()[2][13:]
        image   = utility.misc.base64_to_file(b64)
        if image is None or len(image) == 0:
            tooltip("Failed to temporarily save file.", period=5000)
        else:
            name = mw.col.media.addFile(image)
            if name is None or len(name) == 0:
                tooltip("Failed to add file to media col.", period=5000)
            else:
                index.ui.reading_modal.show_img_field_picker_modal(name)
                os.remove(image)

    elif cmd.startswith("siac-remove-snap-image "):
        # user clicked on cancel, image is already added to the media folder, so we delete it
        name        = " ".join(cmd.split()[1:])
        media_dir   = mw.col.media.dir()
        try:
            os.remove(os.path.join(media_dir, name))
        except:
            pass
    
    elif cmd.startswith("siac-screen-capture "):
        # capture part of webview (e.g. 'Capture' btn in Yt viewer clicked)

        t = int(cmd.split()[1])
        r = int(cmd.split()[2])
        b = int(cmd.split()[3])
        l = int(cmd.split()[4])
        capture_web(t, r, b, l)


    elif cmd.startswith("siac-generate-clozes "):
        # 'Generate' clicked in the cloze modal
        pdf_title   = cmd.split("$$$")[1]
        pdf_path    = cmd.split("$$$")[2]
        page        = cmd.split("$$$")[3]
        sentences   = [s for s in cmd.split("$$$")[4:] if len(s) > 0]
        generate_clozes(sentences, pdf_path, pdf_title, page)

    elif cmd.startswith("siac-fld-cloze "):
        # "Send to Field" clicked -> show modal with field list 
        cloze_text = " ".join(cmd.split()[1:])
        index.ui.reading_modal.show_cloze_field_picker_modal(cloze_text)

    elif cmd.startswith("siac-last-cloze "):
        # after a field has been selected in "Send to Field", store that field in ReadingModal
        fld = " ".join(cmd.split()[1:])
        ReadingModal.last_cloze = (self.note.model()['id'], fld)

    elif cmd.startswith("siac-url-srch "):
        search_term = cmd.split("$$$")[1]
        url = cmd.split("$$$")[2]
        if search_term == "":
            return (True, None)
        if url is None or len(url) == 0:
            return (True, None)
        url_enc = urllib.parse.quote_plus(search_term)

        index.ui.reading_modal.show_iframe_overlay(url=url.replace("[QUERY]", url_enc))

    elif cmd == "siac-close-iframe":
        index.ui.reading_modal.hide_iframe_overlay()

    elif cmd.startswith("siac-show-web-search-tooltip "):
        inp = " ".join(cmd.split()[1:])
        if inp == "":
            return (True, None)
        index.ui.reading_modal.show_web_search_tooltip(inp)

    elif cmd.startswith("siac-timer-elapsed "):
        nid = int(cmd.split()[1])
        index.ui.reading_modal.show_timer_elapsed_popup(nid)

    #
    #  Index info modal
    #

    elif cmd == "siac-index-info":
        if check_index():
            index.ui.showInModal(get_index_info())

    elif cmd == "siac-r-show-tips":
        tips = get_tips_html()
        index.ui.print_in_meta_cards(tips)

    #
    #   Special searches
    #
    elif cmd.startswith("siac-predef-search "):
        state.last_search_cmd = cmd
        parse_predef_search_cmd(cmd, self)

    elif cmd == "siac-pdf-sidebar-last-addon":
        # last add-on notes button clicked in the pdf sidebar
        notes = get_newest(get_config_value_or_default("pdfTooltipResultLimit", 50), [])
        index.ui.reading_modal.sidebar.print(notes, "", [])

    elif cmd == "siac-pdf-sidebar-last-anki":
        # last anki notes button clicked in the pdf sidebar
        notes = get_last_added_anki_notes(get_config_value_or_default("pdfTooltipResultLimit", 50))
        index.ui.reading_modal.sidebar.print(notes, "", [])

    elif cmd == "siac-pdf-sidebar-pdfs-in-progress":
        # pdfs in progress button clicked in the pdf sidebar
        notes = get_in_progress_pdf_notes()
        index.ui.reading_modal.sidebar.print(notes)

    elif cmd == "siac-pdf-sidebar-pdfs-unread":
        # pdfs unread button clicked in the pdf sidebar
        notes = get_all_unread_pdf_notes()
        index.ui.reading_modal.sidebar.print(notes)

    elif cmd == "siac-pdf-sidebar-pdfs-last-added":
        # pdfs last added button clicked in the pdf sidebar
        notes = get_pdf_notes_last_added_first(limit=100)
        index.ui.reading_modal.sidebar.print(notes)


    #
    # highlights
    #

    elif cmd.startswith("siac-hl-clicked "):
        # highlight btn clicked -> store current highlight color in reading modal
        id = int(cmd.split()[1])
        color = " ".join(cmd.split()[2:])
        index.ui.reading_modal.highlight_color = color
        index.ui.reading_modal.highlight_type = id

    elif cmd.startswith("siac-pdf-page-loaded "):
        # page loaded, so load highlights from db
        page = int(cmd.split()[1])
        index.ui.reading_modal.show_highlights_for_page(page)

    elif cmd.startswith("siac-hl-new "):
        # highlights created, save to db
        # order is page group type [x0,y0,x1,y1]+ # text
        page    = int(cmd.split(" ")[1])
        group   = int(cmd.split(" ")[2])
        type    = int(cmd.split(" ")[3])
        nid     = index.ui.reading_modal.note_id
        all     = []
        # [(nid,page,group,type,text,x0,y0,x1,y1)]
        text = cmd[cmd.index("#") + 1:]
        for ix, i in enumerate(cmd.split(" ")[4:]):
            if i == "#":
                break
            if ix % 4 == 0:
                x0 = float(i[:10])
            elif ix % 4 == 1:
                y0 = float(i[:10])
            elif ix % 4 == 2:
                x1 = float(i[:10])
            else:
                y1 = float(i[:10])
                all.append((nid,page,group,type,text,x0,y0,x1,y1))
        insert_highlights(all)
        index.ui.reading_modal.show_highlights_for_page(page)

    elif cmd.startswith("siac-hl-del "):
        # delete highlight with given id
        id = int(cmd.split()[1])
        delete_highlight(id)

    elif cmd.startswith("siac-hl-text-update-coords "):
        # text comment was resized, so update coords in db
        id = int(cmd.split()[1])
        x0 = float(cmd.split()[2])
        y0 = float(cmd.split()[3])
        x1 = float(cmd.split()[4])
        y1 = float(cmd.split()[5])
        update_text_comment_coords(id, x0, y0, x1, y1)

    elif cmd.startswith("siac-hl-text-update-text "):
        # text comment content has changed, so update in db
        id      = int(cmd.split()[1])
        page    = int(cmd.split()[2])
        text    = " ".join(cmd.split(" ")[3:])

        update_text_comment_text(id, text)
        index.ui.reading_modal.show_highlights_for_page(page)

    #
    #   Checkboxes
    #

    elif (cmd.startswith("siac-toggle-highlight ")):
        if check_index():
            index.highlighting = cmd.split()[1] == "on"
            config["highlighting"] = cmd.split()[1] == "on"
            mw.addonManager.writeConfig(__name__, config)
    elif cmd.startswith("deckSelection"):
        if not check_index():
            return (True, None)
        if len(cmd) > 13:
            index.selectedDecks = [d for d in cmd[14:].split(" ") if d != ""]
        else:
            index.selectedDecks = []
        #repeat last search if default
        try_repeat_last_search(self)

    elif cmd == "toggleTop on":
        if check_index():
            index.topToggled = True

    elif cmd == "toggleTop off":
        if check_index():
            index.topToggled = False

    elif cmd == "toggleGrid on":
        if not check_index():
            return (True, None)
        config["gridView"] = True
        index.ui.gridView = True
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleGrid off":
        if not check_index():
            return (True, None)
        config["gridView"] = False
        index.ui.gridView = False
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleAll on":
        if check_index():
            index.ui.uiVisible = True
    elif cmd == "toggleAll off":
        if check_index():
            index.ui.uiVisible = False

    elif cmd == "siac-decks-select-current":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            index.ui.js("selectDeckWithId(%s);" % deckChooser.selectedId())

    elif cmd == "siac-decks-select-current-and-subdecks":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            index.ui.js("selectDeckAndSubdecksWithId(%s);" % deckChooser.selectedId())
    elif cmd.startswith("siac-update-field-to-hide-in-results "):
        if not check_index():
            return (True, None)
        update_field_to_hide_in_results(cmd.split()[1], int(cmd.split()[2]), cmd.split()[3] == "true")

    elif cmd.startswith("siac-update-field-to-exclude "):
        if not check_index():
            return (True, None)
        update_field_to_exclude(cmd.split()[1], int(cmd.split()[2]), cmd.split()[3] == "true")

    elif cmd == "siac-show-note-sidebar":
        config["notes.sidebar.visible"] = True
        index.ui.sidebar.display()
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "siac-hide-note-sidebar":
        config["notes.sidebar.visible"] = False
        index.ui.sidebar.hide()
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "siac-sidebar-show-notes-tab":
        index.ui.sidebar.show_tab(index.ui.sidebar.ADDON_NOTES_TAB)
    elif cmd == "siac-sidebar-show-import-tab":
        index.ui.sidebar.show_tab(index.ui.sidebar.PDF_IMPORT_TAB)
    elif cmd == "siac-sidebar-show-special-tab":
        index.ui.sidebar.show_tab(index.ui.sidebar.SPECIAL_SEARCHES_TAB)

    elif cmd.startswith("siac-preview "):
        # clicked on preview icon -> open preview modal
        nid     = int(cmd.split(" ")[1])
        cards   = [mw.col.getCard(c) for c in mw.col.find_cards(f"nid:{nid}")]
        if len(cards) > 0:
            d = AddPreviewer(self.parentWindow, mw, cards)
            d.open()
    
    elif cmd == "siac-rev-last-linked":
        # clicked "Review" on modal that asks if the user wants to review the last notes before reading
        last_linked     = get_last_linked_notes(index.ui.reading_modal.note_id, limit=500)
        if len(last_linked) > 0:
            if hasattr(mw.col, "find_cards"):
                due_today   = mw.col.find_cards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked])) 
            else:
                due_today   = mw.col.findCards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked])) 
            success     = create_filtered_deck(due_today)
            if success:
                mw.moveToState("review")
                mw.activateWindow()
                # workaround, as activateWindow doesn't seem to bring the main window on top on OSX
                if isMac:
                    mw.raise_()
            else:
                tooltip("Failed to create filtered deck.")


    else:
        return handled

    # If we are here, else didn't return. So an (el)if did suceed, the
    # action was done, so we can return message to state that the
    # command is handled.
    return (True, None)


def parse_sort_cmd(cmd):
    """ Helper function to parse the various sort commands (newest/remove tagged/...) """
    index = get_index()
    if cmd == "newest":
        index.ui.sortByDate("desc")
    elif cmd == "oldest":
        index.ui.sortByDate("asc")
    elif cmd == "remUntagged":
        index.ui.removeUntagged()
    elif cmd == "remTagged":
        index.ui.removeTagged()
    elif cmd == "remUnreviewed":
        index.ui.remove_unreviewed()
    elif cmd == "remReviewed":
        index.ui.remove_reviewed()
    elif cmd == "remSuspended":
        index.ui.remove_suspended()
    elif cmd == "remUnsuspended":
        index.ui.remove_unsuspended()

def parse_predef_search_cmd(cmd: str, editor: aqt.editor.Editor):
    """
    Helper function to parse the various predefined searches (last added/longest text/...)
    """
    if not check_index():
        return
    index               = get_index()
    cmd                 = " ".join(cmd.split()[1:])
    stype               = cmd.split(" ")[0]
    limit               = int(cmd.split(" ")[1])
    decks               = cmd.split(" ")[2:]
    stamp               = set_stamp()
    index.lastSearch    = (None, decks, stype, limit)

    if stype == "lowestPerf":
        res = findNotesWithLowestPerformance(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif stype == "highestPerf":
        res = findNotesWithHighestPerformance(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif stype == "lastAdded":
        getCreatedNotesOrderedByDate(index, editor, decks, limit, "desc")
    elif stype == "firstAdded":
        getCreatedNotesOrderedByDate(index, editor, decks, limit, "asc")
    elif stype == "lastModified":
        getLastModifiedNotes(index, editor, decks, limit)
    elif stype == "lowestRet":
        res = findNotesWithLowestPerformance(decks, limit, index.pinned, retOnly = True)
        index.ui.print_search_results(res, stamp)
    elif stype == "highestRet":
        res = findNotesWithHighestPerformance(decks, limit, index.pinned, retOnly = True)
        index.ui.print_search_results(res, stamp)
    elif stype == "longestText":
        res = findNotesWithLongestText(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif stype == "randomUntagged":
        res = getRandomUntagged(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif stype == "lastUntagged":
        res = get_last_untagged(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif stype == "highestInterval":
        res = getSortedByInterval(decks, limit, index.pinned, "desc")
        index.ui.print_search_results(res, stamp)
    elif stype == "lowestInterval":
        res = getSortedByInterval(decks, limit, index.pinned, "asc")
        index.ui.print_search_results(res, stamp)
    elif stype == "lastReviewed":
        res = getLastReviewed(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif stype == "lastLapses":
        res = getLastLapses(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif stype == "longestTime":
        res = getByTimeTaken(decks, limit, "desc")
        index.ui.print_search_results(res, stamp)
    elif stype == "shortestTime":
        res = getByTimeTaken(decks, limit, "asc")
        index.ui.print_search_results(res, stamp)


def set_stamp() -> Optional[str]:
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    if check_index():
        index           = get_index()
        stamp           = utility.misc.get_milisec_stamp()
        index.ui.latest = stamp
        return stamp
    return None

def set_stats(nid: int, stats: Tuple[Any, ...]):
    """ Insert the statistics into the given card. """
    if check_index():
        get_index().ui.show_stats(stats[0], stats[1], stats[2], stats[3])

def rerender_info(editor: aqt.editor.Editor, content: str = "", searchDB: bool = False):
    """
    Main function that is executed when a user has typed or manually entered a search.
    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    index = get_index()
    if not index:
        return

    if len(content) < 1:
        index.ui.empty_result("No results found for empty string")

    decks = []
    if "~" in content:
        decks = [s.strip() for s in content[:content.index('~')].split(',') if s.strip() != ""]

    if searchDB:
        content             = content[content.index('~ ') + 2:].strip()
        if len(content) == 0:
            index.ui.empty_result("No results found for empty string")
            return
        index.lastSearch    = (content, decks, "db")
        search_res          = index.searchDB(content, decks)
        if editor and editor.web:
            index.ui.print_search_results(search_res["result"], search_res["stamp"], editor, logging=index.logging)

    else:
        if len(content[content.index('~ ') + 2:]) > 2000:
            index.ui.empty_result("Query was <b>too long</b>")
            return
        content             = content[content.index('~ ') + 2:]
        search_res          = index.search(content, decks)


@requires_index_loaded
def search_by_tags(query: str):
    """ Searches for notes with at least one fitting tag. """

    index               = get_index()
    stamp               = utility.misc.get_milisec_stamp()
    index.ui.latest     = stamp
    index.lastSearch    = (query, ["-1"], "tags")
    res                 = findBySameTag(query, index.limit, [], index.pinned)

    index.ui.print_search_results(res["result"], stamp, index.ui._editor, logging=index.logging)


def rerenderNote(nid: int):
    res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid)
    if res is not None and len(res) > 0:
        res = res[0]
        index = get_index()
        if index is not None and index.ui is not None:
            index.ui.updateSingle(res)

@requires_index_loaded
def default_search_with_decks(editor: aqt.editor.Editor, textRaw: Optional[str], decks: List[int]):
    """
    Uses the index to clean the input and find notes.

    Args:
        decks: list of deck ids (string), if "-1" is contained, all decks are searched
    """
    if textRaw is None:
        return
    index = get_index()
    if len(textRaw) > 2000:
        if editor is not None and editor.web is not None:
            index.ui.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(textRaw)
    if len(cleaned) == 0:
        index.ui.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(textRaw, 100).replace("\u001f", "").replace("`", "&#96;"))
        return
    index.lastSearch = (cleaned, decks, "default")
    searchRes = index.search(cleaned, decks)

@requires_index_loaded
def search_for_user_notes_only(editor: aqt.editor.Editor, text: str):
    """ Uses the index to clean the input and find user notes. """

    if text is None:
        return
    index = get_index()
    if len(text) > 2000:
        index.ui.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(text)
    if len(cleaned) == 0:
        index.ui.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(text, 100).replace("\u001f", "").replace("`", "&#96;"))
        return
    index.lastSearch    = (cleaned, ["-1"], "user notes")
    searchRes           = index.search(cleaned, ["-1"], only_user_notes = True)

@requires_index_loaded
def add_note_to_index(note: Note):
    get_index().addNote(note)

@requires_index_loaded
def add_tag(tag: str):
    """ Insert the given tag in the tag field at bottom if not already there. """

    index = get_index()
    if tag == "" or index is None or index.ui._editor is None:
        return
    tagsExisting = index.ui._editor.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return

    index.ui._editor.tags.setText(tagsExisting + " " + tag)
    index.ui._editor.saveTags()

@requires_index_loaded
def set_pinned(cmd: str):
    """
    Update the pinned search results.
    This is important because they should not be contained in the search results.
    """
    pinned = []
    index = get_index()
    for id in cmd.split(" "):
        if len(id) > 0:
            pinned.append(id)
    index.pinned = pinned
    if index.logging:
        log("Updated pinned: " + str(index.pinned))

def update_field_to_hide_in_results(mid: int, fldOrd: int, value: bool):
    if not value:
        config["fieldsToHideInResults"][mid].remove(fldOrd)
        if len(config["fieldsToHideInResults"][mid]) == 0:
            del config["fieldsToHideInResults"][mid]
    else:
        if not mid in config["fieldsToHideInResults"]:
            config["fieldsToHideInResults"][mid] = [fldOrd]
        else:
            config["fieldsToHideInResults"][mid].append(fldOrd)
    if check_index():
        get_index().ui.fields_to_hide_in_results = config["fieldsToHideInResults"]
    mw.addonManager.writeConfig(__name__, config)


def update_field_to_exclude(mid: int, fldOrd: int, value: bool):
    if not value:
        config["fieldsToExclude"][mid].remove(fldOrd)
        if len(config["fieldsToExclude"][mid]) == 0:
            del config["fieldsToExclude"][mid]
    else:
        if not mid in config["fieldsToExclude"]:
            config["fieldsToExclude"][mid] = [fldOrd]
        else:
            config["fieldsToExclude"][mid].append(fldOrd)
    mw.addonManager.writeConfig(__name__, config)


@requires_index_loaded
def try_repeat_last_search(editor: Optional[aqt.editor.Editor] = None):
    """
    Sometimes it is useful if we can simply repeat the last search,
    e.g. the user has clicked another deck in the deck select / updated a note / deleted a note / closed the reading modal.
    This will attempt to repeat the last command that rendered some kind of result (i.e. the last cmd that started with "siac-r-").
    """

    if state.last_search_cmd is None:
        return
    
    ix = get_index()

    # if index is not initialized or reading modal is active, abort
    if ix is None or ix.ui.reading_modal.note_id is not None:
        return

    if editor is None:
        editor = ix.ui._editor

    # executing the last cmd again will reset state.last_page_requested, so store it before
    page = state.last_page_requested

    # execute the last command again
    expanded_on_bridge_cmd(None, state.last_search_cmd, editor)

    # If state.last_page_requested was not None, we were on a page > 1.
    # So now that we have executed the last search cmd again, which refreshed the results,
    # go to that page again.
    if page is not None:
        ix.ui.show_page(editor, page)
    
def show_schedule_dialog(parent_window):
    """ Show the dialog that allows to change the schedule of a note """
    
    index           = get_index()
    original_sched  = index.ui.reading_modal.note.reminder
    nid             = index.ui.reading_modal.note_id
    dialog          = ScheduleDialog(index.ui.reading_modal.note, parent_window)
    if dialog.exec_():
        schedule = dialog.schedule()
        if schedule != original_sched:
            update_reminder(nid, schedule)
            # set position to null before recalculating queue
            prio = get_priority(nid)
            print(f"prio: {prio}")
            if not prio or prio == 0:
                null_position(nid)
            # null_position(index.ui.reading_modal.note_id)
            index.ui.reading_modal.note = get_note(nid)
            print(f"ix.ui.rm.note.reminder: {index.ui.reading_modal.note.reminder}")
            # index.ui.reading_modal.note.reminder = schedule
            if original_sched is not None and original_sched != "" and (schedule == "" or schedule is None):
                tooltip(f"Removed schedule.")
                # removed schedule, and config was set to not show scheduled notes in the queue, so now we have to insert it again
                # TODO
                # update_priority_list(index.ui.reading_modal.note_id, get_priority(index.ui.reading_modal.note_id))
            else:
                tooltip(f"Updated schedule.")
            run_hooks("updated-schedule")


def show_read_stats():
    """ Displays some cards with pages read graphs. """

    index       = get_index()
    stamp       = set_stamp()
    res         = []

    # first card: Read pages heatmap
    t_counts    = get_read_last_n_days_by_day(365)
    body        = read_counts_by_date_card_body(t_counts)
    t_counts    = utility.date.counts_to_timestamps(t_counts)
    res.append(SiacNote.mock(f"Pages read per day ({datetime.now().year})", body, "Meta"))

    # second card: Pie charts with tags
    topics      = pdf_topic_distribution()
    rec_topics  = pdf_topic_distribution_recently_read(7)

    if len(topics) > 0:
        body    = topic_card_body(topics)
        res.append(SiacNote.mock(f"Topic/Tag Distribution", body, "Meta"))

    counts      = get_read(0)
    body        = read_counts_card_body(counts)
    res.append(SiacNote.mock(f"Pages read today ({sum([c[0] for c in counts.values()])})", body, "Meta"))
    counts      = get_read(1)
    body        = read_counts_card_body(counts)
    res.append(SiacNote.mock(f"Pages read yesterday ({sum([c[0] for c in counts.values()])})", body,"Meta"))
    counts      = get_read_last_n_days(7)
    body        = read_counts_card_body(counts)
    res.append(SiacNote.mock(f"Pages read last 7 days ({sum([c[0] for c in counts.values()])})", body, "Meta"))
    counts      = get_read_last_n_days(30)
    body        = read_counts_card_body(counts)
    res.append(SiacNote.mock(f"Pages read last 30 days ({sum([c[0] for c in counts.values()])})", body, "Meta"))
    index.ui.print_search_results(res, stamp)
    # fill plots
    index.ui.js(f"""drawHeatmap("#siac-read-time-ch", {json.dumps(t_counts)});""")
    if len(topics) > 0:
        index.ui.js(f"drawTopics('siac-read-stats-topics-pc_1', {json.dumps(topics)});")
    if len(rec_topics) > 0:
        index.ui.js(f"drawTopics('siac-read-stats-topics-pc_2', {json.dumps(rec_topics)});")


def capture_web(t: int, r: int, b: int, l: int):
    """ Save the given rectangle part of the webview as image. """

    w       = r - l
    h       = b - t
    index   = get_index()
    web     = index.ui._editor.web
    image   = QImage(w, h, QImage.Format_ARGB32)
    region  = QRegion(l, t, w, h)
    painter = QPainter(image)

    web.page().view().render(painter, QPoint(), region)
    painter.end()
    ba      = QByteArray()
    buf     = QBuffer(ba)
    buf.open(QBuffer.ReadWrite)
    image.save(buf, "JPG", 100)
    b64     = ba.toBase64()
    buf.close()
    image = utility.misc.base64_to_file(b64)
    if image is None or len(image) == 0:
        tooltip("Failed to temporarily save file.", period=5000)
    else:
        name = mw.col.media.addFile(image)
        if name is None or len(name) == 0:
            tooltip("Failed to add file to media col.", period=5000)
        else:
            index.ui.reading_modal.show_img_field_picker_modal(name)
            os.remove(image)


def generate_clozes(sentences: List[str], pdf_path: str, pdf_title: str, page: int):
    try:
        # (optional) field that full path to pdf doc goes into
        path_fld        = config["pdf.clozegen.field.pdfpath"]
        # (optional) field that title of pdf note goes into
        note_title_fld  = config["pdf.clozegen.field.pdftitle"]
        # (optional) field that page of the pdf where the cloze was generated goes into
        page_fld        = config["pdf.clozegen.field.page"]

        # name of cloze note type to use
        model_name      = config["pdf.clozegen.notetype"]
        # name of field that clozed text has to go into
        fld_name        = config["pdf.clozegen.field.clozedtext"]

        # default cloze note type and fld
        if model_name is None or len(model_name) == 0:
            model_name  = "Cloze"
        if fld_name is None or len(fld_name) == 0:
            fld_name    = "Text"

        model           = mw.col.models.byName(model_name)
        index           = get_index()
        if model is None:
            tooltip("Could not resolve note model.", period=3000)
            return
        deck_chooser    = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deck_chooser is None:
            tooltip("Could not determine chosen deck.", period=3000)
            return
        did = deck_chooser.selectedId()
        if check_index():
            tags        = index.ui._editor.tags.text()
            tags        = mw.col.tags.canonify(mw.col.tags.split(tags))
        else:
            tags        = []

        added           = 0

        for sentence in sentences:
            if not "{{c1::" in sentence or not "}}" in sentence:
                continue

            note                = Note(mw.col, model)
            note.model()['did'] = did
            note.tags           = tags

            if not fld_name in note:
                return

            note[fld_name] = sentence
            if path_fld is not None and len(path_fld) > 0:
                note[path_fld] = pdf_path
            if note_title_fld is not None and len(note_title_fld) > 0:
                note[note_title_fld] = pdf_title
            if page_fld is not None and len(page_fld) > 0:
                note[page_fld] = page

            a                   = mw.col.addNote(note)
            if a > 0:
                add_note_to_index(note)
                if index.ui.reading_modal.note_id is not None:
                    nid = index.ui.reading_modal.note_id 

                    def cb(page: int):
                        if page >= 0:
                            link_note_and_page(nid, note.id, page)
                            # update sidebar if shown
                            index.ui.js("updatePageSidebarIfShown()")
                    index.ui.reading_modal.page_displayed(cb)
            added               += a

        tags_str            = " ".join(tags) if len(tags) > 0 else "<i>No tags</i>"
        deck_name           = mw.col.decks.get(did)["name"]
        s                   = "" if added == 1 else "s"
        tooltip(f"""<center>Added {added} Cloze{s}.</center><br>
                  <center>Deck: <b>{deck_name}</b></center>
                  <center>Tags: <b>{tags_str}</b></center>""", period=3000)
    except:
        tooltip("Something went wrong during Cloze generation.", period=3000)

@requires_index_loaded
def get_index_info():
    """ Returns the html that is rendered in the popup that appears on clicking the "info" button """

    index           = get_index()
    config          = mw.addonManager.getConfig(__name__)
    excluded_fields = config["fieldsToExclude"]
    field_c         = 0

    for k,v in excluded_fields.items():
        field_c += len(v)

    # qt and chromium version
    chromium_v      = ""
    qt_v            = ""
    try:
        user_agent      = QWebEngineProfile.defaultProfile().httpUserAgent()

        for t in user_agent.split():
            if t.startswith("Chrome/"):
                chromium_v = t.split("/")[1]
            elif t.startswith("QtWebEngine/"):
                qt_v = t.split("/")[1]
    except:
        pass

    full_path       = utility.misc.get_addon_base_folder_path()
    dir_name        = utility.misc.get_addon_id()
    notes_db_path   = ("%ssiac-notes.db" % config["addonNoteDBFolderPath"]) if config["addonNoteDBFolderPath"] is not None and len(config["addonNoteDBFolderPath"]) > 0 else utility.misc.get_user_files_folder_path() + "siac-notes.db"
    notes_db_folder = config["addonNoteDBFolderPath"] if config["addonNoteDBFolderPath"] is not None and len(config["addonNoteDBFolderPath"]) > 0 else utility.misc.get_user_files_folder_path() 
    notes_db_bu     = notes_db_folder + ("siac_backups/" if notes_db_folder.endswith("/") else "/siac_backups/")
    data_folder     = config["addon.data_folder"]

    # last update
    last_mod        = ""
    try:
        id          = utility.misc.get_addon_id()
        meta        = mw.addonManager.addon_meta(id)
        last_mod    = time.strftime("%Y-%m-%dT%H:%M", time.localtime(meta.installed_at)) if meta.installed_at else "?"
    except:
        pass

    if state.shortcuts_failed == []:
        shortcuts = ""
    else:
        shortcuts = "<b>Following shortcuts failed to register (maybe a conflict with existing shortcuts):</b><br>"
        shortcuts += "<br>".join(state.shortcuts_failed)
        shortcuts += "<br>"

    sp_on   = "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>"
    sp_off  = "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>"
    html            = """
            <table class="striped" style='width: 100%%; margin-bottom: 18px;'>
                
               <tr><td>Add-on Folder:</td><td> <a class='keyword' onclick='pycmd("siac-open-folder %s")'><b>%s</b></a></td></tr>
               <tr><td>Last Update:</td><td> <b>%s</b></td></tr>
               <tr><td>Qt Version:</td><td> <b>%s</b></td></tr>
               <tr><td>Chromium Version:</td><td> <b>%s</b></td></tr>
               <tr><td>Rust Libs:</td><td> <b>%s</b></td></tr>
               <tr><td>Index Used:</td><td> <b>%s</b></td></tr>
               <tr><td>SQLite Version</td><td> <b>%s</b></td></tr>
               <tr><td>Index Initialization:</td><td>  <b>%s s</b></td></tr>
               <tr><td>Index Size:</td><td>  <b>%s</b> notes</td></tr>
               <tr><td>Index is always rebuilt if smaller than:</td><td>  <b>%s</b> notes</td></tr>
               <tr><td>Stopwords:</td><td>  <b>%s</b></td></tr>
               <tr><td>Logging:</td><td>  <b>%s</b></td></tr>
               <tr><td>Render Immediately:</td><td>  <b>%s</b></td></tr>
               <tr><td>Tag Click:</td><td>  <b>%s</b></td></tr>
               <tr><td>Timeline:</td><td>  <b>%s</b></td></tr>
               <tr><td>Tag Info on Hover:</td><td>  <b>%s</b></td></tr>
               <tr><td>Tag Hover Delay:</td><td>  <b>%s</b> ms</td></tr>
               <tr><td>Image Max Height:</td><td>  <b>%s px</b></td></tr>
               <tr><td>Show Pass Rate in Results:</td><td>  <b>%s</b></td></tr>
               <tr><td>Window split:</td><td>  <b>%s</b></td></tr>
               <tr><td>Toggle Shortcut:</td><td>  <b>%s</b></td></tr>
               <tr><td>&nbsp;</td><td>  <b></b></td></tr>
               <tr><td>Fields Excluded:</td><td>  %s</td></tr>
               <tr><td>Path to Note DB</td><td>  <b>%s &nbsp;<a class='keyword' onclick='pycmd("siac-open-folder %s")'>[Open Folder]</a></b></td></tr>
               <tr><td>Path to Note DB Backups</td><td>  <b>%s &nbsp;<a class='keyword' onclick='pycmd("siac-open-folder %s")'>[Open Folder]</a></b></td></tr>
               <tr><td>Path to Search Data DB</td><td>  <b>%s &nbsp;<a class='keyword' onclick='pycmd("siac-open-folder %s")'>[Open Folder]</a></b></td></tr>

               <tr><td>&nbsp;</td><td>  <b></b></td></tr>
               <tr><td>PDF: Page Right</td><td>  <b>Ctrl+Right / Ctrl+J</b></td></tr>
               <tr><td>PDF: Page Right + Mark Page as Read</td><td>  <b>Ctrl+Shift+Space</b></td></tr>
               <tr><td>PDF: Page Left</td><td>  <b>Ctrl+Left / Ctrl+K</b></td></tr>
               <tr><td>New Note</td><td>  <b>%s</b></td></tr>
               <tr><td>Confirm new note</td><td>  <b>Ctrl+Enter</b></td></tr>
               <tr><td>Confirm new note and keep open</td><td>  <b>Ctrl+Shift+Enter</b></td></tr>
               <tr><td>PDF: Quick Open</td><td>  <b>Ctrl+O</b></td></tr>
               <tr><td>PDF: Toggle Top & Bottom Bar</td><td>  <b>F11</b></td></tr>
               <tr><td>PDF: Toggle Search on Select</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Jump to first Page</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Jump to last Page</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Toggle Page Read</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Done</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Later</td><td>  <b>%s</b></td></tr>
               <tr><td>Focus Search Input</td><td><b>%s</b></td></tr>
               <tr><td>Trigger Search with current field contents</td><td>  <b>%s</b></td></tr>
               <tr><td>Trigger Search with current focused field's contents</td><td>  <b>%s</b></td></tr>
               <tr><td>Trigger Predefined Search</td><td>  <b>%s</b></td></tr>
               <tr><td>Trigger current filter</td><td>  <b>%s</b></td></tr>
             </table>

            %s

            """ % (
            full_path,
            dir_name,
            last_mod,
            qt_v,
            chromium_v,
            str(state.rust_lib),
            index.type, 
            sqlite3.sqlite_version,
            str(index.initializationTime), index.get_number_of_notes(), config["alwaysRebuildIndexIfSmallerThan"], len(index.stopWords),
            sp_on if index.logging else sp_off,
            sp_on if config["renderImmediately"] else sp_off,
            "Search" if config["tagClickShouldSearch"] else "Add",
            sp_on if config["showTimeline"] else sp_off,
            sp_on if config["showTagInfoOnHover"] else sp_off,
            config["tagHoverDelayInMiliSec"],
            config["imageMaxHeight"],
            sp_on if config["showRetentionScores"] else sp_off,
            str(config["leftSideWidthInPercent"]) + " / " + str(100 - config["leftSideWidthInPercent"]),
            config["toggleShortcut"],
            "None" if len(excluded_fields) == 0 else "<b>%s</b> field(s) among <b>%s</b> note type(s)" % (field_c, len(excluded_fields)),
            notes_db_path, notes_db_folder, notes_db_bu, notes_db_bu, 
            data_folder, data_folder,
            config["notes.editor.shortcut"],
            config["pdf.shortcuts.toggle_search_on_select"],
            config["pdf.shortcuts.jump_to_first_page"],
            config["pdf.shortcuts.jump_to_last_page"],
            config["pdf.shortcuts.toggle_page_read"],
            config["pdf.shortcuts.done"],
            config["pdf.shortcuts.later"],
            config["shortcuts.focus_search_bar"],
            config["shortcuts.trigger_search"],
            config["shortcuts.search_for_current_field"],
            config["shortcuts.trigger_predef_search"],
            config["shortcuts.trigger_current_filter"],
            shortcuts
            )

 

    changes = changelog()

    if changes:
        html += "<br/><br/><b>Changelog:</b><hr>"
        for ix, c in enumerate(changes):
            html += f"<br>{ix + 1}. {c}"

    issues = known_issues()

    if issues:
        html += "<br/><br/><b>Known Issues:</b><hr>"
        for ix, i in enumerate(issues):
            html += f"<br>{ix + 1}. {i}"

    html += """
        <br><br>
        <b>Contact:</b>
        <hr>
        <br>
        For bug reports, feedback or suggestions: <a href='https://github.com/fonol/anki-search-inside-add-card/issues'>Github Repository</a>
        <br>
        If you want to support this project: <a href='https://www.patreon.com/tomtomtom'>Patreon Site</a>

    """

    return html

@requires_index_loaded
def show_timing_modal(render_time = None):
    """ Builds the html and shows the modal which gives some info about the last executed search (timing, query after stopwords etc.) """

    index   = get_index()
    html    = "<h4>Query (stopwords removed, checked Synsets):</h4><div class='w-100 oflow_y_auto mb-10' style='max-height: 200px;'><i>%s</i></div>" % index.lastResDict["query"]

    if "decks" in index.lastResDict:
        html += "<h4>Decks:</h4><div class='w-100 oflow_y_auto mb-10' style='max-height: 200px;'><i>%s</i></div>" % ", ".join([str(d) for d in index.lastResDict["decks"]])

    html += "<h4>Execution time:</h4><table class='w-100'>"
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Removing Stopwords", index.lastResDict["time-stopwords"] if index.lastResDict["time-stopwords"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Checking Synsets", index.lastResDict["time-synonyms"] if index.lastResDict["time-synonyms"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("SQLite: Executing Query", index.lastResDict["time-query"] if index.lastResDict["time-query"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML", index.lastResDict["time-html"] if index.lastResDict["time-html"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Highlighting", index.lastResDict["time-html-highlighting"] if index.lastResDict["time-html-highlighting"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Formatting SIAC Notes", index.lastResDict["time-html-build-user-note"] if index.lastResDict["time-html-build-user-note"] > 0 else "< 1")

    if render_time is not None:
        html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Rendering", render_time)

    html += "</table>"

    index.ui.showInModal(html)

@requires_index_loaded
def update_styling(cmd):

    index   = get_index()
    name    = cmd.split()[0]
    value   = " ".join(cmd.split()[1:])


    if name == "searchpane.zoom":
        config[name] = float(value)
        index.ui._editor.web.setZoomFactor(float(value))
    elif name == "renderImmediately":
        m = value == "true" or value == "on"
        config["renderImmediately"] = m
        index.ui.js("renderImmediately = %s;" % ("true" if m else "false"))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"]   = m
        index.ui.hideSidebar    = m
        index.ui.js("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))

    elif name == "removeDivsFromOutput":
        m = value == "true" or value == "on"
        config[name] = m
        index.ui.remove_divs = m

    elif name == "results.hide_cloze_brackets":
        m = value == "true" or value == "on"
        config[name] = m
        index.ui.show_clozes = not m

    elif name == "addonNoteDBFolderPath":
        if value is not None and len(value.strip()) > 0:
            value = value.replace("\\", "/")
            if not value.endswith("/"):
                value += "/"
            old_val = config["addonNoteDBFolderPath"]
            config["addonNoteDBFolderPath"] = value
            if value != old_val:
                write_config()
                existed = create_db_file_if_not_exists()
                if existed:
                    ex = "Created no new file, because there was already a <i>siac-notes.db</i> in that location."
                else:
                    ex = "Created an empty file there."
                tooltip(f"Updated path to note .db file to <b>{value}</b>.<br>{ex}<br>If you have existing notes, replace that new file with your old file.", period=9000)


    elif name == "leftSideWidthInPercent":
        config[name]    = int(value)
        right           = 100 - int(value)
        if check_index():
            index.ui.js("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('siac-right-side').style.width = '%s%%';" % (value, right) )

    elif name == "showTimeline":
        config[name] = value == "true" or value == "on"
        if not config[name] and check_index():
            index.ui.js("document.getElementById('cal-row').style.display = 'none'; onWindowResize();")
        elif config[name] and check_index():
            index.ui.js("""
            if (document.getElementById('cal-row')) {
                document.getElementById('cal-row').style.display = 'block';
            } else {
                document.getElementById('bottomContainer').children[1].innerHTML = `%s`;
                $('.cal-block-outer').mouseenter(function(event) { calBlockMouseEnter(event, this);});
                $('.cal-block-outer').click(function(event) { displayCalInfo(this);});
            }
            onWindowResize();
            """ % get_calendar_html())

    elif name == "showTagInfoOnHover":
        config[name] = value == "true" or value == "on"
        if not config[name] and check_index():
            index.ui.js("showTagInfoOnHover = false;")
        elif config[name] and check_index():
            index.ui.js("showTagInfoOnHover = true;")

    elif name == "tagHoverDelayInMiliSec":
        config[name] = int(value)
        if check_index():
            index.ui.js("tagHoverTimeout = %s;" % value)

    elif name == "alwaysRebuildIndexIfSmallerThan":
        config[name] = int(value)

    elif name == "pdfUrlImportSavePath":
        if value is not None and len(value.strip()) > 0:
            value = value.replace("\\", "/")
            if not value.endswith("/"):
                value += "/"
            config["pdfUrlImportSavePath"] = value

    elif name.startswith("styles."):
        config[name] = value
        write_config()
        reload_styles()
        tooltip("Reloaded styles.")

    elif name in ["notes.showSource", "useInEdit", "results.showFloatButton", "results.showIDButton", "results.showCIDButton"]:
        config[name] = value == "true"


def empty_filtered_deck_by_name(name: str) -> bool:

    try:
        deck = mw.col.decks.byName(name)
        if deck:
            did = deck["id"]
            if hasattr(mw.col.sched, "empty_filtered_deck"):
                mw.col.sched.empty_filtered_deck(did)
            else:
                mw.col.sched.emptyDyn(did)
        return True
    except:
        return False

def create_filtered_deck(cids: List[int]) -> bool:

    try:
        cur = mw.col.decks.byName(REV_FILTERED_DECK_NAME)
        if cur:
            did = cur["id"]
            if hasattr(mw.col.sched, "empty_filtered_deck"):
                mw.col.sched.empty_filtered_deck(did)
            else:
                mw.col.sched.emptyDyn(did)
        else:    
            if hasattr(mw.col.decks, "new_filtered"):
                did = mw.col.decks.new_filtered(REV_FILTERED_DECK_NAME)
            else:
                did = mw.col.decks.newDyn(REV_FILTERED_DECK_NAME)
        dyn = mw.col.decks.get(did)
        dyn["terms"][0] = [" or ".join([f"cid:{cid}" for cid in cids]), 9999, 0]
        dyn["resched"] = True
        mw.col.decks.save(dyn)
        if hasattr(mw.col.sched, "rebuild_filtered_deck"):
            mw.col.sched.rebuild_filtered_deck(did)
        else:
            mw.col.sched.rebuildDyn(did)
        mw.col.decks.select(did)
        return True
    except:
        return False


@js
def write_config():
    mw.addonManager.writeConfig(__name__, config)
    return "$('.modal-close').unbind('click')"

def update_config(key, value):
    config[key] = value
    mw.addonManager.writeConfig(__name__, config)


@requires_index_loaded
def after_index_rebuilt():

    search_index    = get_index()
    editor          = search_index.ui._editor

    editor.web.eval("""
        $('.freeze-icon').removeClass('frozen');
        siacState.isFrozen = false;
        $('#selectionCb,#typingCb,#highlightCb').prop("checked", true);
        siacState.searchOnSelection = true;
        siacState.searchOnTyping = true;
        $('#toggleTop').click(function() { toggleTop(this); });
        $('#greyout').hide();
    """)
    fillDeckSelect(editor)
    setup_ui_after_index_built(editor, search_index)
