import json
from typing import Optional
from ..output import UI
from aqt.utils import tooltip
from ..dialogs.editor import  NoteEditor
from ..web.reading_modal import Reader
from ..notes import *
from ..web.web import display_note_del_confirm_modal
from ..state import get_index
from ..hooks import run_hooks
from ..models import SiacNote
from ..web.html import get_pdf_list_first_card, marks_card_body, read_counts_card_body, read_counts_by_date_card_body, topic_card_body

import state
import utility.misc
import utility.date

def handle(editor, cmd: str) -> bool:

    if cmd == "siac-create-note":
        if not state.note_editor_shown:
            NoteEditor(editor.parentWindow)
        return True

    elif cmd.startswith("siac-create-note-add-only "):
        if not state.note_editor_shown:
            nid         = int(cmd.split()[1])
            tag_prefill = ""
            if Reader.note_id:
                tag_prefill = get_note(Reader.note_id).tags

            NoteEditor(editor.parentWindow, add_only=True, read_note_id=nid, tag_prefill=tag_prefill)
        return True

    elif cmd.startswith("siac-create-note-tag-prefill "):
        if not state.note_editor_shown:
            tag = cmd.split()[1]
            NoteEditor(editor.parentWindow, add_only=False, read_note_id=None, tag_prefill = tag)
        return True

    elif cmd.startswith("siac-create-note-source-prefill "):
        source      = " ".join(cmd.split()[1:])
        existing    = get_pdf_id_for_source(source)
        if existing > 0:
            Reader.display(existing)
        else:
            if not state.note_editor_shown:
                NoteEditor(editor.parentWindow, add_only=False, read_note_id=None, tag_prefill = None, source_prefill=source)
            else:
                tooltip("Close the opened note dialog first!")
        return True

    elif cmd.startswith("siac-edit-user-note "):
        if not state.note_editor_shown:
            id = int(cmd.split()[1])
            if id > -1:
                NoteEditor(editor.parentWindow, id)
        return True

    elif cmd.startswith("siac-edit-user-note-from-modal "):
        if not state.note_editor_shown:
            id = int(cmd.split()[1])
            read_note_id = int(cmd.split()[2])
            if id > -1:
                NoteEditor(editor.parentWindow, note_id=id, add_only=False, read_note_id=read_note_id)
        return True

    elif cmd.startswith("siac-delete-user-note-modal "):
        nid = int(cmd.split()[1])
        if nid > -1:
            display_note_del_confirm_modal(editor, nid)
        return True

    elif cmd.startswith("siac-delete-user-note "):
        id = int(cmd.split()[1])
        delete_note(id)
        index = get_index()
        if index is not None:
            index.deleteNote(id)
        run_hooks("user-note-deleted")
        UI.js(""" $('#siac-del-modal').remove(); """)
        return True

    elif cmd == "siac-r-show-pdfs":
        stamp = set_stamp()
        notes = get_all_pdf_notes()
        # add special note at front
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        UI.print_search_results(["PDFs", "Newest"],  notes, stamp)
        return True

    elif cmd == "siac-r-show-text-notes":
        stamp = set_stamp()
        notes = get_all_text_notes()
        UI.print_search_results(["Text notes", "Newest"],  notes, stamp)
        return True

    elif cmd == "siac-r-show-video-notes":
        stamp = set_stamp()
        notes = get_all_video_notes()
        UI.print_search_results(["Video notes", "Newest"],  notes, stamp)
        return True

    elif cmd == "siac-r-show-pdfs-unread":
        stamp   = set_stamp()
        notes   = get_all_unread_pdf_notes()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        UI.print_search_results(["PDFs", "Unread"],  notes, stamp)
        return True

    elif cmd == "siac-r-show-pdfs-in-progress":
        stamp   = set_stamp()
        notes   = get_in_progress_pdf_notes()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        UI.print_search_results(["PDFs", "In progress"], notes, stamp)
        return True

    elif cmd == "siac-r-show-pdfs-last-opened":
        stamp   = set_stamp()
        notes   = get_last_opened_pdf_notes()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        UI.print_search_results(["PDFs", "Last opened"], notes, stamp)
        return True

    elif cmd == "siac-r-show-pdfs-marks":
        stamp   = set_stamp()
        marks   = get_recently_created_marks(limit=100)
        sp_body = marks_card_body(marks)
        UI.print_search_results(["PDFs", "Marks"], [SiacNote.mock("Most recent marked pages", sp_body, "Meta")], stamp)
        return True

    elif cmd == "siac-r-show-due-today":
        stamp = set_stamp()
        notes = get_notes_scheduled_for_today()
        UI.print_search_results(["Due today"],  notes, stamp)
        return True

    elif cmd == "siac-r-show-stats":
        # Read Stats clicked in sidebar
        show_read_stats()
        return True

    elif cmd == "siac-r-show-last-done":
        stamp = set_stamp()
        notes = get_last_done_notes()
        UI.print_search_results(["Last done"],  notes, stamp)
        return True

    elif cmd == "siac-r-pdf-last-read":
        stamp = set_stamp()
        notes = get_pdf_notes_last_read_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        UI.print_search_results(["PDFs", "Last read"],  notes, stamp)
        return True

    elif cmd == "siac-r-pdf-last-added":
        stamp = set_stamp()
        notes = get_pdf_notes_last_added_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        UI.print_search_results(["PDFs", "Newest"],  notes, stamp)
        return True

    elif cmd.startswith("siac-r-pdf-size "):
        stamp   = set_stamp()
        notes   = get_pdf_notes_ordered_by_size(cmd.split()[1])
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body, "Meta"))
        title   = "Highest page count" if cmd.split()[1] == "desc" else "Lowest page count"
        UI.print_search_results(["PDFs", title],  notes, stamp)
        return True

    elif cmd == "siac-r-pdf-find-invalid":
        stamp   = set_stamp()
        notes   = get_invalid_pdfs()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote.mock("PDF Meta", sp_body,"Meta"))
        UI.print_search_results(["PDFs", "Invalid paths"],  notes, stamp)
        return True

    return False


def set_stamp() -> Optional[str]:
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    stamp     = utility.misc.get_milisec_stamp()
    UI.latest = stamp
    return stamp


def show_read_stats():
    """ Displays some cards with pages read graphs. """

    stamp       = set_stamp()
    res         = []

    # first card: Read pages heatmap
    t_counts    = get_read_last_n_days_by_day(utility.date.day_of_year())
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

    UI.print_search_results(None,  res, stamp)

    # fill plots
    UI.js(f"""drawHeatmap("#siac-read-time-ch", {json.dumps(t_counts)});""")
    if len(topics) > 0 or len(rec_topics) > 0:
        UI.js(f"drawTopics({json.dumps(topics)}, {json.dumps(rec_topics)});")