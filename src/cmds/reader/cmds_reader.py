import typing
from aqt.utils import tooltip

from ...web.reading_modal import Reader
from ...notes import *
from ...state import get_index
from ...hooks import run_hooks
from ...dialogs.done_dialog import DoneDialog
from ...dialogs.pdf_extract import PDFExtractDialog
from ...dialogs.editor import NoteEditor
from ...output import UI
from ...config import update_config

import state
import utility.date
import utility.text
import utility.misc

def handle(editor, cmd: str) -> bool:


    if cmd.startswith("siac-delete-current-user-note "):
        # Delete a note, invoked from the reading modal
        id      = int(cmd.split()[1])
        delete_note(id)

        index   = get_index()
        if index is not None:
            index.deleteNote(id)

        run_hooks("user-note-deleted")
        tooltip("Deleted note.")

        if id == Reader.note_id:
            head = get_head_of_queue()
            if head is None or head < 0:
                UI.js("onReadingModalClose();")
            else:
                Reader.display(head)
        else:
            Reader.reload_bottom_bar()
        return True
    
    elif cmd.startswith("siac-read-next-with-tag "):
        nid                 = find_next_enqueued_with_tag(cmd.split(" ")[1:])
        if nid and nid > 0  :
            DoneDialog.last_tag_filter = cmd.split()[1]
            Reader.display(nid)
        else                :
            tooltip("No queued note found for the given tag.")
        return True
    
    elif cmd.startswith("siac-read-random-with-tag "):
        nid                 = get_random_with_tag(cmd.split(" ")[1])
        if nid and nid > 0  : 
            Reader.display(nid)
        else                : 
            tooltip("No note found for the given tag.")
        return True

    elif cmd == "siac-on-reading-modal-close":
        Reader.reset()
        run_hooks("reading-modal-closed")
        return True

    elif cmd == "siac-user-note-queue-read-random":
        rand_id = get_random_id_from_queue()
        if rand_id >= 0:
            Reader.display(rand_id)
        else:
            UI.js("ungreyoutBottom();noteLoading=false;pdfLoading=false;modalShown=false;")
            tooltip("Queue is Empty! Add some items first.", period=4000)
        return True

    elif cmd == "siac-user-note-queue-read-head":
        Reader.read_head_of_queue()
        return True

    elif cmd == "siac-user-note-done":
        # hit "Done" button in reading modal
        Reader.done()
        return True

    elif cmd.startswith("siac-update-schedule "):
        stype           = cmd.split()[1]
        svalue          = cmd.split()[2]
        new_reminder    = utility.date.get_new_reminder(stype, svalue)
        update_reminder(Reader.note_id, new_reminder)
        nid             = Reader.note_id
        prio            = get_priority(nid)
        update_priority_list(nid, prio)
        nid             = get_head_of_queue()
        if nid is not None and nid >= 0:
            Reader.display(nid)
        else:
            tooltip("Queue is Empty! Add some items first.", period=4000)
        return True

    elif cmd.startswith("siac-update-note-tags "):
        # entered tags in the tag line input in the reading modal bottom bar
        nid  = int(cmd.split()[1])
        tags = " ".join(cmd.split()[2:])
        tags = utility.text.clean_tags(tags)
        update_note_tags(nid, tags)
        UI.sidebar.refresh()
        return True

    elif cmd == "siac-try-copy-text-note":
        # copy to new note button clicked in reading modal
        nid  = Reader.note_id
        note = get_note(nid)
        html = note.text
        prio = get_priority(nid)
        if html is None or len(html) == 0:
            tooltip("Note text seems to be empty.")
        else:
            if not state.note_editor_shown:
                NoteEditor(editor.parentWindow, add_only=True, read_note_id=None, tag_prefill =note.tags, source_prefill=note.source, text_prefill=html, title_prefill = note.title, prio_prefill = prio)
            else:
                tooltip("Close the opened note dialog first!")

        return True

    elif cmd.startswith("siac-yt-save-time "):
        # save time clicked in yt player
        time    = int(cmd.split()[1])
        src     = Reader.note.source
        set_source(Reader.note_id, utility.text.set_yt_time(src, time))
        return True

    elif cmd.startswith("siac-pdf-page-read"):
        nid     = cmd.split()[1]
        page    = cmd.split()[2]
        total   = cmd.split()[3]
        mark_page_as_read(nid, page, total)
        UI.js("updatePageSidebarIfShown()")
        return True

    elif cmd.startswith("siac-pdf-page-unread"):
        nid     = cmd.split()[1]
        page    = cmd.split()[2]
        mark_page_as_unread(nid, page)
        UI.js("updatePageSidebarIfShown()")
        return True

    elif cmd.startswith("siac-unhide-pdf-queue "):
        update_config("pdf.queue.hide", False)
        Reader.reload_bottom_bar()
        return True

    elif cmd.startswith("siac-hide-pdf-queue "):
        update_config("pdf.queue.hide", True)
        Reader.reload_bottom_bar()
        return True

    elif cmd.startswith("siac-toggle-show-prios "):
        update_config("notes.queue.show_priorities", cmd.split(" ")[1] == "on")
        Reader.reload_bottom_bar()
        return True

    elif cmd == "siac-left-side-width":
        Reader.show_width_picker()
        return True
    
    elif cmd.startswith("siac-pdf-show-bottom-tab "):
        nid = int(cmd.split()[1])
        tab = cmd.split()[2]
        Reader.show_pdf_bottom_tab(nid, tab)
        return True
    
    elif cmd == "siac-show-text-extract-modal":
        Reader.show_text_extract_modal()
        return True
    
    elif cmd.startswith("siac-text-extract-send-to-field "):
        fld_ix = int(cmd.split()[1])
        Reader.send_text_extract_to_field(fld_ix)
        return True

    elif cmd.startswith("siac-show-cloze-modal "):
        selection = " ".join(cmd.split()[1:]).split("$$$")[0]
        sentences = cmd.split("$$$")[1:]
        Reader.display_cloze_modal(editor, selection, sentences)
        return True

    elif cmd.startswith("siac-linked-to-page "):
        page  = int(cmd.split()[1])
        total = int(cmd.split()[2])
        Reader.page_sidebar_info(page, total)
        return True
    
    elif cmd.startswith("siac-create-pdf-extract "):
        dialog = PDFExtractDialog(editor.parentWindow, int(cmd.split(" ")[1]), int(cmd.split(" ")[2]), Reader.note)
        return True

    elif cmd.startswith("siac-jump-last-read"):
        Reader.jump_to_last_read_page()
        return True

    elif cmd.startswith("siac-jump-first-unread"):
        Reader.jump_to_first_unread_page()
        return True

    elif cmd == "siac-jump-random-unread":
        Reader.jump_to_random_unread_page()
        return True

    elif cmd.startswith("siac-mark-read-up-to "):
        mark_as_read_up_to(Reader.note, int(cmd.split()[2]), int(cmd.split()[3]))
        UI.js("updatePageSidebarIfShown()")
        return True

    elif cmd.startswith("siac-display-range-input "):
        nid         = int(cmd.split()[1])
        num_pages   = int(cmd.split()[2])
        Reader.display_read_range_input(nid, num_pages)
        return True

    elif cmd.startswith("siac-user-note-mark-range "):
        start           = int(cmd.split()[2])
        end             = int(cmd.split()[3])
        pages_total     = int(cmd.split()[4])
        current_page    = int(cmd.split()[5])
        Reader.mark_range(start, end, pages_total, current_page)
        UI.js("updatePageSidebarIfShown()")
        return True

    elif cmd.startswith("siac-mark-all-read "):
        mark_all_pages_as_read(Reader.note, int(cmd.split()[2]))
        UI.js("updatePageSidebarIfShown()")
        return True

    elif cmd.startswith("siac-mark-all-unread "):
        mark_all_pages_as_unread(int(cmd.split()[1]))
        UI.js("updatePageSidebarIfShown()")
        return True
    
    elif cmd.startswith("siac-pdf-mark "):
        mark_type       = int(cmd.split()[1])
        nid             = int(cmd.split()[2])
        page            = int(cmd.split()[3])
        pages_total     = int(cmd.split()[4])
        marks_updated   = toggle_pdf_mark(nid, page, pages_total, mark_type)
        js_maps         = utility.misc.marks_to_js_map(marks_updated)
        editor.web.eval(""" pdf.displayedMarks = %s; pdf.displayedMarksTable = %s; updatePdfDisplayedMarks(true);""" % (js_maps[0], js_maps[1]))
        return True

    return False