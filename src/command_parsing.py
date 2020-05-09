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
from aqt.utils import tooltip, showInfo
import os
import urllib.parse
import json


from .state import check_index, get_index, set_index, set_corpus
from .index.indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import *
from .web.html import *
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
from .dialogs.zotero_import import ZoteroImporter
from .tag_find import findBySameTag, display_tag_info
from .stats import calculateStats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval
from .models import SiacNote
import utility.misc
import utility.text


config = mw.addonManager.getConfig(__name__)

def expanded_on_bridge_cmd(handled, cmd, self):
    """
    Process the various commands coming from the ui -
    this includes users clicks on option checkboxes, on rendered results, on special searches, etc.

    todo: needs some serious cleanup
    """
    if not isinstance(self, aqt.editor.Editor):
        return handled
    index = get_index()
    # just to make sure
    if index is not None and index.ui._editor is None:
        index.ui.set_editor(self)

    if cmd.startswith("siac-fld "):
        # keyup in fields -> search
        rerender_info(self, cmd[8:])
    
    elif cmd.startswith("siac-page "):
        # page in results clicked
        index.ui.show_page(self, int(cmd.split()[1]))
    
    elif cmd.startswith("siac-srch-db "):
        # bottom search input used
        if index.searchbar_mode == "Add-on":
            rerender_info(self, cmd[13:])
        else:
            rerender_info(self, cmd[13:], searchDB = True)
    
    elif cmd.startswith("fldSlctd ") and index is not None:
        # selection in field or note
        rerender_info(self, cmd[9:])
    
    elif (cmd.startswith("siac-note-stats ")):
        # note "Info" button clicked
        setStats(cmd[16:], calculateStats(cmd[16:], index.ui.gridView))

    elif (cmd.startswith("siac-tag-clicked ")):
        # clicked on a tag
        if config["tagClickShouldSearch"]:
            rerender_info(self, cmd[17:].strip(), searchByTags=True)
        else:
            add_tag(cmd[17:])

    elif cmd.startswith("siac-edit-note "):
        # "Edit" clicked on a normal note
        openEditor(mw, int(cmd[15:]))

    elif cmd.startswith("siac-eval "):
        # direct eval, saves code
        eval(cmd[10:])
    elif cmd.startswith("siac-exec "):
        # direct exec, saves code
        exec(cmd[10:])

    elif cmd.startswith("siac-pin"):
        set_pinned(cmd[9:])

    elif (cmd.startswith("siac-render-tags")):
        index.ui.printTagHierarchy(cmd[16:].split(" "))

    elif (cmd.startswith("siac-random-notes ") and check_index()):
        res = getRandomNotes(index, [s for s in cmd[17:].split(" ") if s != ""])
        index.ui.print_search_results(res["result"], res["stamp"])
    elif cmd == "siac-fill-deck-select":
        fillDeckSelect(self, expanded=True)
    elif cmd == "siac-fill-tag-select":
        fillTagSelect(expanded=True)
    elif cmd.startswith("searchTag "):
        rerender_info(self, cmd[10:].strip(), searchByTags=True)

    elif cmd.startswith("siac-tag-info "):
        #this renders the popup
        display_tag_info(self, cmd.split()[1], " ".join(cmd.split()[2:]), index)

    elif cmd.startswith("siac-rerender "):
        ix = int(cmd.split()[1])
        if check_index() and ix < len(index.ui.previous_calls):
            index.ui.print_search_results(*index.ui.previous_calls[ix] + [True])

    elif cmd == "siac-rerender":
        index.ui.try_rerender_last()      
    
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
        
    elif cmd == "siac-show-pdfs":
        if check_index():
            stamp = setStamp()
            notes = get_all_pdf_notes()
            # add special note at front
            sp_body = get_pdf_list_first_card()
            notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-show-pdfs-unread":
        if check_index():
            stamp = setStamp()
            notes = get_all_unread_pdf_notes()
            index.ui.print_search_results(notes, stamp)
    
    elif cmd == "siac-show-pdfs-in-progress":
        if check_index():
            stamp = setStamp()
            notes = get_in_progress_pdf_notes()
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-pdf-last-read":
        stamp = setStamp()
        notes = get_pdf_notes_last_read_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-pdf-last-added":
        stamp = setStamp()
        notes = get_pdf_notes_last_added_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.ui.print_search_results(notes, stamp)
    
    elif cmd == "siac-pdf-find-invalid":
        stamp = setStamp()
        notes = get_invalid_pdfs()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-queue-info "):
        nid = int(cmd.split()[1])
        note = get_note(nid)
        read_stats = get_read_stats(nid)
        index.ui.js("""
            if (pdfLoading || noteLoading || modalShown) {
                hideQueueInfobox();
            } else {
                document.getElementById('siac-pdf-bottom-tabs').style.visibility = "hidden";
                document.getElementById('siac-queue-infobox').style.display = "block";
                document.getElementById('siac-queue-infobox').innerHTML =`%s`;
            }
        """ % get_queue_infobox(note, read_stats))

    elif cmd.startswith("siac-pdf-selection "):
        stamp = setStamp()
        if check_index():
            index.search(cmd[19:], ["-1"], only_user_notes = False, print_mode = "pdf")

    elif cmd.startswith("siac-pdf-tooltip-search "):
        inp = cmd[len("siac-pdf-tooltip-search "):]
        if len(inp.strip()) > 0:
            if check_index():
                stamp = setStamp()
                index.search(inp, ["-1"], only_user_notes = False, print_mode = "pdf")

    elif cmd.startswith("siac-cutout-io "):
        img_src = " ".join(cmd.split()[1:])
        full_path = os.path.join(mw.col.media.dir(), img_src).replace("\\", "/")
        self.onImgOccButton(image_path=full_path)

    elif cmd.startswith("siac-jump-last-read"):
        index.ui.reading_modal.jump_to_last_read_page(int(cmd.split()[1]))

    elif cmd.startswith("siac-jump-first-unread"):
        index.ui.reading_modal.jump_to_first_unread_page(int(cmd.split()[1]))

    elif cmd.startswith("siac-mark-read-up-to "):
        mark_as_read_up_to(int(cmd.split()[1]), int(cmd.split()[2]), int(cmd.split()[3]))

    elif cmd.startswith("siac-display-range-input "):
        nid = int(cmd.split()[1])
        num_pages = int(cmd.split()[2])
        index.ui.reading_modal.display_read_range_input(nid, num_pages)

    elif cmd.startswith("siac-user-note-mark-range "):
        start = int(cmd.split()[2])
        end = int(cmd.split()[3])
        pages_total = int(cmd.split()[4])
        current_page = int(cmd.split()[5])
        index.ui.reading_modal.mark_range(start, end, pages_total, current_page)

    elif cmd.startswith("siac-mark-all-read "):
        mark_all_pages_as_read(int(cmd.split()[1]), int(cmd.split()[2]))

    elif cmd.startswith("siac-mark-all-unread "):
        mark_all_pages_as_unread(int(cmd.split()[1]))

    elif cmd.startswith("siac-insert-pages-total "):
        insert_pages_total(int(cmd.split()[1]), int(cmd.split()[2]))

    elif cmd.startswith("siac-show-cloze-modal "):
        selection = " ".join(cmd.split()[1:]).split("$$$")[0]
        sentences = cmd.split("$$$")[1:]
        index.ui.reading_modal.display_cloze_modal(self, selection, sentences)

    elif cmd == "siac-url-dialog":
        dialog = UrlImporter(self.parentWindow)
        if dialog.exec_():
            if dialog.chosen_url is not None and len(dialog.chosen_url) >= 0:
                sched = dialog.queue_schedule
                name = dialog.get_name()
                path = config["pdfUrlImportSavePath"]
                if path is None or len(path) == 0:
                    tooltip("""You have to set a save path for imported URLs first.
                        <center>Config value: <i>pdfUrlImportSavePath</i></center> 
                    """, period=4000)
                    return
                path = utility.misc.get_pdf_save_full_path(path, name)
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



    
    elif cmd.startswith("siac-pdf-mark "):
        mark_type = int(cmd.split()[1])
        nid = int(cmd.split()[2])
        page = int(cmd.split()[3])
        pages_total = int(cmd.split()[4])
        marks_updated = toggle_pdf_mark(nid, page, pages_total, mark_type)
        js_maps = utility.misc.marks_to_js_map(marks_updated)
        self.web.eval(""" pdfDisplayedMarks = %s; pdfDisplayedMarksTable = %s; updatePdfDisplayedMarks();""" % (js_maps[0], js_maps[1]))


    elif cmd.startswith("siac-generate-clozes "):
        pdf_title = cmd.split("$$$")[1]
        pdf_path = cmd.split("$$$")[2]
        page = cmd.split("$$$")[3]
        sentences = [s for s in cmd.split("$$$")[4:] if len(s) > 0]
        generate_clozes(sentences, pdf_path, pdf_title, page)

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
        if inp is not None and len(inp) > 0:
            notes = find_pdf_notes_by_title(inp) 
            index.ui.reading_modal.sidebar.print(notes)

    elif cmd.startswith("pSort "):
        if check_index():
            parseSortCommand(cmd[6:])

    elif cmd == "siac-model-dialog":
        display_model_dialog()

    elif cmd.startswith("addedSameDay "):
        if check_index():
            getCreatedSameDay(index, self, int(cmd[13:]))

    elif cmd == "lastTiming":
        if index is not None and index.lastResDict is not None:
            show_timing_modal()
    elif cmd.startswith("lastTiming "):
        render_time = int(cmd.split()[1])
        if index is not None and index.lastResDict is not None:
            show_timing_modal(render_time)
    elif cmd.startswith("calInfo "):
        if check_index():
            context_html = get_cal_info_context(int(cmd[8:]))
            res = get_notes_added_on_day_of_year(int(cmd[8:]), min(index.limit, 100))
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
        NoteEditor(self.parentWindow)

    elif cmd.startswith("siac-create-note-add-only "):
        nid = int(cmd.split()[1])
        NoteEditor(self.parentWindow, add_only=True, read_note_id=nid)

    elif cmd.startswith("siac-create-note-tag-prefill "):
        tag = cmd.split()[1]
        NoteEditor(self.parentWindow, add_only=False, read_note_id=None, tag_prefill = tag)
    
    elif cmd.startswith("siac-create-note-source-prefill "):
        source = " ".join(cmd.split()[1:])
        existing = get_pdf_id_for_source(source)
        if existing > 0:
            index.ui.reading_modal.display(existing)
        else:
            NoteEditor(self.parentWindow, add_only=False, read_note_id=None, tag_prefill = None, source_prefill=source)

    elif cmd.startswith("siac-edit-user-note "):
        id = int(cmd.split()[1])
        if id > -1:
            NoteEditor(self.parentWindow, id)
    
    elif cmd.startswith("siac-edit-user-note-from-modal "):
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
        index.ui.js("""
            $("#greyout").hide(); 
            $('#siac-del-modal').remove();
        """)

    elif cmd == "siac-delete-current-user-note":
        # delete the currently opened note in the reading modal
        id = index.ui.reading_modal.note_id
        delete_note(id)
        if index is not None:
            index.deleteNote(id)
        run_hooks("user-note-deleted")
        head = get_head_of_queue()
        tooltip("Deleted note.")
        if head is None or head < 0:
            index.ui.js("""
                onReadingModalClose(); 
            """)
        else:
            index.ui.reading_modal.display(head)


    elif cmd.startswith("siac-read-user-note "):
        id = int(cmd.split()[1])
        if id >= 0:
            index.ui.reading_modal.display(id)

    elif cmd == "siac-user-note-queue":
        stamp = setStamp()
        notes = get_priority_list()
        if check_index():
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-queue-random":
        stamp = setStamp()
        notes = get_queue_in_random_order()
        if check_index():
            index.ui.print_search_results(notes, stamp)
    
    elif cmd == "siac-user-note-untagged":
        stamp = setStamp()
        notes = get_untagged_notes()
        if check_index():
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-newest":
        stamp = setStamp()
        if check_index():
            notes = get_newest(index.limit, index.pinned)
            index.ui.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-random":
        stamp = setStamp()
        if check_index():
            notes = get_random(index.limit, index.pinned)
            index.ui.print_search_results(notes, stamp)
    
    elif cmd.startswith("siac-user-note-search-tag "):
        stamp = setStamp()
        if check_index():
            notes = find_by_tag(" ".join(cmd.split()[1:]))
            index.ui.print_search_results(notes, stamp)

    elif cmd.startswith("siac-user-note-queue-picker "):
        nid = int(cmd.split()[1])
        picker = QueuePicker(self.parentWindow, [], [])
        if picker.exec_() and picker.chosen_id is not None and picker.chosen_id >= 0:
            note = get_note(nid)
            index.ui.reading_modal.display(picker.chosen_id)
        else:
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

    elif cmd.startswith("siac-user-note-search-inp "):
        if check_index():
            search_for_user_notes_only(self, " ".join(cmd.split()[1:]))

    elif cmd.startswith("siac-update-note-text "):
        id = cmd.split()[1]
        text = " ".join(cmd.split(" ")[2:])
        update_note_text(id, text)

    elif cmd.startswith("siac-requeue "):
        # priority slider released
        nid = int(cmd.split()[1])
        new_prio = int(cmd.split()[2])
        note = get_note(nid)
        if note.is_due_sometime():
            add_to_prio_log(nid, new_prio)
            index.ui.reading_modal.display_schedule_dialog() 
        else:
            update_priority_list(nid, new_prio)
            nid = get_head_of_queue()
            index.ui.reading_modal.display(nid)
            if new_prio == 0:
                tooltip(f"<center>Removed from Queue.</center>")
            else:
                tooltip(f"<center>Set priority to: <b>{dynamic_sched_to_str(new_prio)}</b></center><center>Recalculated Priority Queue.</center>")


    elif cmd.startswith("siac-update-prio "):
        # prio slider in bottom bar released on value != 0
        # not used atm
        nid = int(cmd.split()[1])
        new_prio = int(cmd.split()[2])
        update_priority_without_timestamp(nid, new_prio)
        # todo: find a better solution
        recalculate_priority_queue()
        index.ui.reading_modal.update_reading_bottom_bar(nid)
        tooltip(f"<center>Set priority to: <b>{dynamic_sched_to_str(new_prio)}</b></center><center>Recalculated Priority Queue.</center>")

    elif cmd.startswith("siac-remove-from-queue"):
        # called from the buttons on the left of the reading modal bottom bar 
        # if not " " in cmd:
        #     nid = index.ui.reading_modal.note_id
        # else:
        #     nid = int(cmd.split()[1])
        # remove_from_priority_list(nid)
        # queue_readings_list = get_queue_head_display(nid)
        # index.ui.js("afterRemovedFromQueue();")
        # index.ui.js("$('#siac-queue-lbl').hide(); document.getElementById('siac-queue-lbl').innerHTML = 'Unqueued'; $('#siac-queue-lbl').fadeIn();$('#siac-queue-readings-list').replaceWith(`%s`)" % queue_readings_list)    
        update_priority_list(index.ui.reading_modal.note_id, 0)
        nid = get_head_of_queue()
        if nid is None or nid < 0:
            index.ui.eval("onReadingModalClose();")
        else:
            index.ui.reading_modal.display(nid)
        tooltip(f"<center>Removed from Queue.</center>")

    elif cmd == "siac-user-note-queue-read-random":
        rand_id = get_random_id_from_queue()
        if rand_id >= 0:
            index.ui.reading_modal.display(rand_id)
        else:
            index.ui.js("ungreyoutBottom();noteLoading=false;pdfLoading=false;modalShown=false;")
            tooltip("Queue is Empty! Add some items first.", period=4000)

    elif cmd == "siac-user-note-queue-read-head":
        nid = get_head_of_queue()
        if nid is not None and nid >= 0:
            index.ui.reading_modal.display(nid)
        else:
            tooltip("Queue is Empty! Add some items first.", period=4000)

    elif cmd == "siac-user-note-done":
        if index.ui.reading_modal.note.is_due_sometime():
            index.ui.reading_modal.display_schedule_dialog() 
        else:
            nid = index.ui.reading_modal.note_id
            prio = get_priority(nid)
            update_priority_list(nid, prio)
            nid = get_head_of_queue()
            index.ui.reading_modal.display(nid)
    
    elif cmd.startswith("siac-update-schedule "):
        stype = cmd.split()[1]
        svalue = cmd.split()[2]
        new_reminder = utility.date.get_new_reminder(stype, svalue)
        update_reminder(index.ui.reading_modal.note_id, new_reminder)
        nid = index.ui.reading_modal.note_id
        prio = get_priority(nid)
        update_priority_list(nid, prio)
        nid = get_head_of_queue()   
        if nid is not None and nid >= 0:
            index.ui.reading_modal.display(nid)
        else:
            tooltip("Queue is Empty! Add some items first.", period=4000)
        

    elif cmd.startswith("siac-update-note-tags "):
        nid = int(cmd.split()[1])
        tags = " ".join(cmd.split()[2:])
        tags = utility.text.clean_tags(tags)
        update_note_tags(nid, tags)
        index.ui.sidebar.refresh()

    elif cmd == "siac-try-copy-text-note":
        # copy to new note button clicked in reading modal
        nid = index.ui.reading_modal.note_id
        note = get_note(nid)
        html = note.text
        prio = get_priority(nid)
        if html is None or len(html) == 0:
            tooltip("Note text seems to be empty.")
        else:
            NoteEditor(self.parentWindow, add_only=True, read_note_id=None, tag_prefill =note.tags, source_prefill=note.source, text_prefill=html, title_prefill = note.title, prio_prefill = prio)

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

    elif cmd.startswith("siac-pdf-page-unread"):
        nid = cmd.split()[1]
        page = cmd.split()[2]
        mark_page_as_unread(nid, page)

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
            index.ui.js(f"""$('#siac-quick-sched-btn .siac-btn-dark-smaller').last().show().text('Current ({prio})');
                            $('#siac-prio-slider-small').val({prio});
                            $('#siac-slider-small-lbl').html('{prio}');
                            $('#siac-quick-sched-btn').toggleClass('expanded');""")
    #
    #   Synonyms
    #

    elif cmd == "synonyms":
        if check_index():
            index.ui.showInModal(getSynonymEditor())
    elif cmd.startswith("saveSynonyms "):
        newSynonyms(cmd[13:])
        index.ui.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("editSynonyms "):
        editSynonymSet(cmd[13:])
        index.ui.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("deleteSynonyms "):
        deleteSynonymSet(cmd[15:])
        index.ui.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-synset-search "):
        if check_index():
            index.ui.hideModal()
            default_search_with_decks(self, cmd.split()[1], ["-1"])

    elif cmd == "styling":
        showStylingModal(self)

    elif cmd.startswith("styling "):
        update_styling(cmd[8:])

    elif cmd == "writeConfig":
        write_config()

    elif cmd.startswith("siac-add-image "):
        b64 = cmd.split()[2][13:]
        image = utility.misc.base64_to_file(b64)
        if image is None or len(image) == 0:
            tooltip("Failed to temporarily save file.", period=5000)
            return
        name = mw.col.media.addFile(image)
        if name is None or len(name) == 0:
            tooltip("Failed to add file to media col.", period=5000)
            return
        index.ui.reading_modal.show_img_field_picker_modal(name)
        os.remove(image)

    # if the user clicked on cancel, the image is already added to the media folder, so we delete it
    elif cmd.startswith("siac-remove-snap-image "):
        name = " ".join(cmd.split()[1:])
        media_dir = mw.col.media.dir()
        try:
            os.remove(os.path.join(media_dir, name))
        except:
            pass

    elif cmd.startswith("siac-fld-cloze "):
        cloze_text = " ".join(cmd.split()[1:])
        index.ui.reading_modal.show_cloze_field_picker_modal(cloze_text)


    elif cmd.startswith("siac-url-srch "):
        search_term = cmd.split("$$$")[1]
        url = cmd.split("$$$")[2]
        if search_term == "":
            return
        if url is None or len(url) == 0:
            return 
        url_enc = urllib.parse.quote_plus(search_term)
        
        index.ui.reading_modal.show_iframe_overlay(url=url.replace("[QUERY]", url_enc))

    elif cmd == "siac-close-iframe":
        index.ui.reading_modal.hide_iframe_overlay()

    elif cmd.startswith("siac-show-web-search-tooltip "):
        inp = " ".join(cmd.split()[1:])
        if inp == "":
            return
        index.ui.reading_modal.show_web_search_tooltip(inp)
    
    elif cmd.startswith("siac-timer-elapsed "):
        nid = int(cmd.split()[1])
        index.ui.reading_modal.show_timer_elapsed_popup(nid)


    #
    #  Index info modal
    #

    elif cmd == "indexInfo":
        if check_index():
            index.ui.showInModal(get_index_info())

    #
    #   Special searches
    #
    elif cmd.startswith("predefSearch "):
        parse_predef_search_cmd(cmd, self)

    elif cmd.startswith("similarForCard "):
        if check_index():
            cid = int(cmd.split()[1])
            min_sim = int(cmd.split()[2])
            res_and_html = similar_cards(cid, min_sim, 20)
            index.ui.show_in_modal_subpage(res_and_html[1])

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
        page = int(cmd.split(" ")[1])
        group = int(cmd.split(" ")[2])
        type = int(cmd.split(" ")[3])
        nid = index.ui.reading_modal.note_id
        all = []
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
        id = int(cmd.split()[1])
        text = " ".join(cmd.split(" ")[2:])
        update_text_comment_text(id, text)

    #
    #   Checkboxes
    #

    elif (cmd.startswith("highlight ")):
        if check_index():
            index.highlighting = cmd[10:] == "on"
            config["highlighting"] = cmd[10:] == "on"
            mw.addonManager.writeConfig(__name__, config)
    elif cmd.startswith("searchWhileTyping "):
        config["searchOnTyping"] = cmd[18:] == "on"
        mw.addonManager.writeConfig(__name__, config)
    elif (cmd.startswith("searchOnSelection ")):
        config["searchOnSelection"] = cmd[18:] == "on"
        mw.addonManager.writeConfig(__name__, config)
    elif (cmd.startswith("deckSelection")):
        if not check_index():
            return
        if index.logging:
            if len(cmd) > 13:
                log("Updating selected decks: " + str( [d for d in cmd[14:].split(" ") if d != ""]))
            else:
                log("Updating selected decks: []")
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
            return
        config["gridView"] = True
        index.ui.gridView = True
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleGrid off":
        if not check_index():
            return
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

    elif cmd == "selectCurrent":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            index.ui.js("selectDeckWithId(%s);" % deckChooser.selectedId())

    elif cmd.startswith("siac-update-field-to-hide-in-results "):
        if not check_index():
            return
        update_field_to_hide_in_results(cmd.split()[1], int(cmd.split()[2]), cmd.split()[3] == "true")

    elif cmd.startswith("siac-update-field-to-exclude "):
        if not check_index():
            return
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



    else:
        return handled

    # If we are here, else didn't return. So an (el)if did suceed, the
    # action was done, so we can return message to state that the
    # command is handled.
    return (True, None)


def parseSortCommand(cmd):
    """
    Helper function to parse the various sort commands (newest/remove tagged/...)
    """
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
        index.ui.removeUnreviewed()
    elif cmd == "remReviewed":
        index.ui.removeReviewed()

def parse_predef_search_cmd(cmd, editor):
    """
    Helper function to parse the various predefined searches (last added/longest text/...)
    """
    if not check_index():
        return
    index = get_index()
    cmd = cmd[13:]
    searchtype = cmd.split(" ")[0]
    limit = int(cmd.split(" ")[1])
    decks = cmd.split(" ")[2:]
    if searchtype == "lowestPerf":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lowestPerf")
        res = findNotesWithLowestPerformance(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "highestPerf":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestPerf")
        res = findNotesWithHighestPerformance(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "lastAdded":
        getCreatedNotesOrderedByDate(index, editor, decks, limit, "desc")
    elif searchtype == "firstAdded":
        getCreatedNotesOrderedByDate(index, editor, decks, limit, "asc")
    elif searchtype == "lastModified":
        getLastModifiedNotes(index, editor, decks, limit)
    elif searchtype == "lowestRet":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lowestRet")
        res = findNotesWithLowestPerformance(decks, limit, index.pinned, retOnly = True)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "highestRet":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestRet")
        res = findNotesWithHighestPerformance(decks, limit, index.pinned, retOnly = True)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "longestText":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestRet")
        res = findNotesWithLongestText(decks, limit, index.pinned)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "randomUntagged":
        stamp = setStamp()
        index.lastSearch = (None, decks, "randomUntagged")
        res = getRandomUntagged(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "highestInterval":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestInterval", limit)
        res = getSortedByInterval(decks, limit, index.pinned, "desc")
        index.ui.print_search_results(res, stamp)
    elif searchtype == "lowestInterval":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lowestInterval", limit)
        res = getSortedByInterval(decks, limit, index.pinned, "asc")
        index.ui.print_search_results(res, stamp)
    elif searchtype == "lastReviewed":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lastReviewed", limit)
        res = getLastReviewed(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "lastLapses":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lastLapses", limit)
        res = getLastLapses(decks, limit)
        index.ui.print_search_results(res, stamp)
    elif searchtype == "longestTime":
        stamp = setStamp()
        index.lastSearch = (None, decks, "longestTime", limit)
        res = getByTimeTaken(decks, limit, "desc")
        index.ui.print_search_results(res, stamp)
    elif searchtype == "shortestTime":
        stamp = setStamp()
        index.lastSearch = (None, decks, "shortestTime", limit)
        res = getByTimeTaken(decks, limit, "asc")
        index.ui.print_search_results(res, stamp)


def setStamp():
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    if check_index():
        index = get_index()
        stamp = utility.misc.get_milisec_stamp()
        index.ui.latest = stamp
        return stamp
    return None

def setStats(nid, stats):
    """
    Insert the statistics into the given card.
    """
    if check_index():
        get_index().ui.showStats(stats[0], stats[1], stats[2], stats[3])

def rerender_info(editor, content="", searchDB = False, searchByTags = False):
    """
    Main function that is executed when a user has typed or manually entered a search.
    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    index = get_index()
    if (len(content) < 1):
        index.ui.empty_result("No results found for empty string")
    decks = list()
    if "~" in content:
        for s in content[:content.index('~')].split(','):
            decks.append(s.strip())
    if index is not None:

        if searchDB:
            content = content[content.index('~ ') + 2:].strip()
            if len(content) == 0:
                index.ui.empty_result("No results found for empty string")
                return
            index.lastSearch = (content, decks, "db")
            searchRes = index.searchDB(content, decks)

        elif searchByTags:
            stamp = utility.misc.get_milisec_stamp()
            index.ui.latest = stamp
            index.lastSearch = (content, ["-1"], "tags")
            searchRes = findBySameTag(content, index.limit, [], index.pinned)

        else:
            if len(content[content.index('~ ') + 2:]) > 2000:
                index.ui.empty_result("Query was <b>too long</b>")
                return
            content = content[content.index('~ ') + 2:]
            searchRes = index.search(content, decks)


        if (searchDB or searchByTags) and editor is not None and editor.web is not None:
            if searchRes is not None and len(searchRes["result"]) > 0:
                index.ui.print_search_results(searchRes["result"], stamp if searchByTags else searchRes["stamp"], editor, index.logging)
            else:
                index.ui.empty_result("No results found")


def rerenderNote(nid):
    res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid)
    if res is not None and len(res) > 0:
        res = res[0]
        index = get_index()
        if index is not None and index.ui is not None:
            index.ui.updateSingle(res)

@requires_index_loaded
def default_search_with_decks(editor, textRaw, decks):
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
        index.ui.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(textRaw, 100).replace("\u001f", ""))
        return
    index.lastSearch = (cleaned, decks, "default")
    searchRes = index.search(cleaned, decks)

@requires_index_loaded
def search_for_user_notes_only(editor, text):
    """
    Uses the index to clean the input and find user notes.
    """
    if text is None:
        return
    index = get_index()
    if len(text) > 2000:
        index.ui.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(text)
    if len(cleaned) == 0:
        index.ui.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(text, 100).replace("\u001f", ""))
        return
    index.lastSearch = (cleaned, ["-1"], "user notes")
    searchRes = index.search(cleaned, ["-1"], only_user_notes = True)



def getCurrentContent(editor):
    text = ""
    for f in editor.note.fields:
        text += f
    return text

@requires_index_loaded
def add_note_to_index(note):
    get_index().addNote(note)

@requires_index_loaded
def add_tag(tag):
    """
    Insert the given tag in the tag field at bottom if not already there.
    """
    index = get_index()
    if tag == "" or index is None or index.ui._editor is None:
        return
    tagsExisting = index.ui._editor.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return

    index.ui._editor.tags.setText(tagsExisting + " " + tag)
    index.ui._editor.saveTags()

@requires_index_loaded
def set_pinned(cmd):
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



def update_field_to_hide_in_results(mid, fldOrd, value):
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


def update_field_to_exclude(mid, fldOrd, value):
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
def try_repeat_last_search(editor = None):
    """
    Sometimes it is useful if we can simply repeat the last search,
    e.g. the user has clicked another deck in the deck select.
    """
    index = get_index()

    if index.lastSearch is not None:
        if editor is None and index.ui._editor is not None:
            editor = index.ui._editor

        if index.lastSearch[2] == "default":
            default_search_with_decks(editor, index.lastSearch[0], index.selectedDecks)
        elif index.lastSearch[2] == "lastCreated":
            getCreatedNotesOrderedByDate(index, editor, index.selectedDecks, index.lastSearch[3], "desc")
        elif index.lastSearch[2] == "firstCreated":
            getCreatedNotesOrderedByDate(index, editor, index.selectedDecks, index.lastSearch[3], "asc")

def generate_clozes(sentences, pdf_path, pdf_title, page):
    try:
        # (optional) field that full path to pdf doc goes into
        path_fld = config["pdf.clozegen.field.pdfpath"]
        # (optional) field that title of pdf note goes into
        note_title_fld = config["pdf.clozegen.field.pdftitle"]
        # (optional) field that page of the pdf where the cloze was generated goes into
        page_fld = config["pdf.clozegen.field.page"]

        # name of cloze note type to use
        model_name = config["pdf.clozegen.notetype"]
        # name of field that clozed text has to go into
        fld_name = config["pdf.clozegen.field.clozedtext"]

        # default cloze note type and fld
        if model_name is None or len(model_name) == 0:
            model_name = "Cloze"
        if fld_name is None or len(fld_name) == 0:
            fld_name = "Text"
        
        model = mw.col.models.byName(model_name)
        index = get_index()
        if model is None:
            tooltip("Could not resolve note model.", period=3000)
            return
        deck_chooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deck_chooser is None: 
            tooltip("Could not determine chosen deck.", period=3000)
            return
        did = deck_chooser.selectedId()
        if check_index():
            tags = index.ui._editor.tags.text()
            tags = mw.col.tags.canonify(mw.col.tags.split(tags))
        else:
            tags = []
        added = 0 
        for sentence in sentences:
            if not "{{c1::" in sentence or not "}}" in sentence:
                continue
            note = Note(mw.col, model)
            note.model()['did'] = did
            note.tags = tags
            if not fld_name in note:
                return
            note[fld_name] = sentence
            if path_fld is not None and len(path_fld) > 0:
                note[path_fld] = pdf_path
            if note_title_fld is not None and len(note_title_fld) > 0:
                note[note_title_fld] = pdf_title
            if page_fld is not None and len(page_fld) > 0:
                note[page_fld] = page

            a = mw.col.addNote(note)
            if a > 0:
                add_note_to_index(note)
            added += a
        tags_str = " ".join(tags) if len(tags) > 0 else "<i>No tags</i>"
        deck_name = mw.col.decks.get(did)["name"]
        s = "" if added == 1 else "s"
        tooltip(f"""<center>Added {added} Cloze{s}.</center><br>
                  <center>Deck: <b>{deck_name}</b></center>
                  <center>Tags: <b>{tags_str}</b></center>""", period=3000)
    except:
        tooltip("Something went wrong during Cloze generation.", period=3000)

@requires_index_loaded
def get_index_info():
    """
    Returns the html that is rendered in the popup that appears on clicking the "info" button
    """
    index = get_index()
    excluded_fields = config["fieldsToExclude"]
    field_c = 0
    for k,v in excluded_fields.items():
        field_c += len(v)

    html = """
            <table class="striped" style='width: 100%%; margin-bottom: 18px;'>
               <tr><td>Index Used:</td><td> <b>%s</b></td></tr>
               <tr><td>SQLite Version</td><td> <b>%s</b></td></tr>
               <tr><td>Initialization:</td><td>  <b>%s s</b></td></tr>
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
               <tr><td>Path to Note DB</td><td>  %s</td></tr>

               <tr><td>&nbsp;</td><td>  <b></b></td></tr>
               <tr><td>PDF: Page Right</td><td>  <b>Ctrl+Space / Ctrl+Right / Ctrl+J</b></td></tr>
               <tr><td>PDF: Page Right + Mark Page as Read</td><td>  <b>Ctrl+Shift+Space</b></td></tr>
               <tr><td>PDF: Page Left</td><td>  <b>Ctrl+Left / Ctrl+K</b></td></tr>
               <tr><td>New Note</td><td>  <b>Ctrl+Shift+N</b></td></tr>
               <tr><td>Confirm New Note</td><td>  <b>Ctrl+Enter</b></td></tr>
               <tr><td>PDF: Quick Open</td><td>  <b>Ctrl+O</b></td></tr>
               <tr><td>PDF: Toggle Top & Bottom Bar</td><td>  <b>F11</b></td></tr>
             </table>

            """ % (index.type, sqlite3.sqlite_version,
            str(index.initializationTime), index.get_number_of_notes(), config["alwaysRebuildIndexIfSmallerThan"], len(index.stopWords),
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if index.logging else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>",
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if config["renderImmediately"] else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>",
            "Search" if config["tagClickShouldSearch"] else "Add",
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if config["showTimeline"] else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>",
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if config["showTagInfoOnHover"] else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>",
            config["tagHoverDelayInMiliSec"],
            config["imageMaxHeight"],
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if config["showRetentionScores"] else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>",
            str(config["leftSideWidthInPercent"]) + " / " + str(100 - config["leftSideWidthInPercent"]),
            config["toggleShortcut"],
            "None" if len(excluded_fields) == 0 else "<b>%s</b> field(s) among <b>%s</b> note type(s)" % (field_c, len(excluded_fields)),
            ("%ssiac-notes.db" % config["addonNoteDBFolderPath"]) if config["addonNoteDBFolderPath"] is not None and len(config["addonNoteDBFolderPath"]) > 0 else utility.misc.get_user_files_folder_path() + "siac-notes.db"
            )


    return html

@requires_index_loaded
def show_timing_modal(render_time = None):
    """
    Builds the html and shows the modal which gives some info about the last executed search (timing, query after stopwords etc.)
    """
    index = get_index()
    html = "<h4>Query (stopwords removed, checked SynSets):</h4><div style='width: 100%%; max-height: 200px; overflow-y: auto; margin-bottom: 10px;'><i>%s</i></div>" % index.lastResDict["query"]
    if "decks" in index.lastResDict:
        html += "<h4>Decks:</h4><div style='width: 100%%; max-height: 200px; overflow-y: auto; margin-bottom: 10px;'><i>%s</i></div>" % ", ".join([str(d) for d in index.lastResDict["decks"]])
    html += "<h4>Execution time:</h4><table style='width: 100%'>"
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Removing Stopwords", index.lastResDict["time-stopwords"] if index.lastResDict["time-stopwords"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Checking SynSets", index.lastResDict["time-synonyms"] if index.lastResDict["time-synonyms"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Executing Query", index.lastResDict["time-query"] if index.lastResDict["time-query"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML", index.lastResDict["time-html"] if index.lastResDict["time-html"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Highlighting", index.lastResDict["time-html-highlighting"] if index.lastResDict["time-html-highlighting"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Formatting SIAC Notes", index.lastResDict["time-html-build-user-note"] if index.lastResDict["time-html-build-user-note"] > 0 else "< 1")
    if render_time is not None:
        html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Rendering", render_time)
    html += "</table>"
    index.ui.showInModal(html)

@requires_index_loaded
def update_styling(cmd):
    index = get_index()
    name = cmd.split()[0]
    value = " ".join(cmd.split()[1:])
    if name == "default" and value == "day":
        config["styling"] = json.loads(default_styles())
        tooltip("Styling updated. Restart to apply changes.", period=4000)
    elif name == "default" and value == "night":
        config["styling"] = json.loads(default_night_mode_styles())
        tooltip("Styling updated. Restart to apply changes.", period=4000)
   
    elif name == "searchpane.zoom":
        config[name] = float(value)
        index.ui.js("document.getElementById('siac-right-side').style.zoom = '%s'; showTagInfoOnHover = %s;" % (value, "false" if float(value) != 1.0 else "true"))
    elif name == "renderImmediately":
        m = value == "true" or value == "on"
        config["renderImmediately"] = m
        index.ui.js("renderImmediately = %s;" % ("true" if m else "false"))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"] = m
        index.ui.hideSidebar = m
        index.ui.js("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))

    elif name == "removeDivsFromOutput":
        m = value == "true" or value == "on"
        config["removeDivsFromOutput"] = m
        index.ui.remove_divs = m

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
        config[name] = int(value)
        right = 100 - int(value)
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
            """ % getCalendarHtml())

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
    
    elif name == "notes.showSource":
        config[name] = value == "true"
    
        


@js
def write_config():
    mw.addonManager.writeConfig(__name__, config)
    return "$('.modal-close').unbind('click')"

def update_config(key, value):
    config[key] = value
    mw.addonManager.writeConfig(__name__, config)

@requires_index_loaded
def after_index_rebuilt():
    search_index = get_index()
    editor = search_index.ui._editor
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

