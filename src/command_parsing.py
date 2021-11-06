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
from anki.utils import isMac, isLin
import os
import time
import urllib.parse
import json
from datetime import datetime
import typing
from typing import List, Dict, Any, Optional, Tuple


from .state import check_index, get_index, set_index
from .index.indexing import build_index
from .web.web import *
from .web.html import *
from .config import get_config_value_or_default, get_config_value
from .web.reading_modal import Reader
from .special_searches import *
from .internals import requires_index_loaded, js, perf_time
from .notes import *
from .hooks import run_hooks
from .output import UI
from .cmds.cmds_md import handle as handle_md
from .cmds.cmds_config import handle as handle_config
from .cmds.cmds_notes import handle as handle_notes
from .cmds.cmds_search import handle as handle_search
from .cmds.reader.cmds_highlighting import handle as handle_highlighting
from .cmds.reader.cmds_reader import handle as handle_reader
from .md import get_folder_structure
from .dialogs.editor import open_editor, NoteEditor
from .dialogs.queue_picker import QueuePicker
from .dialogs.importing.url_import import UrlImporter
from .dialogs.pdf_extract import PDFExtractDialog
from .dialogs.importing.zotero_import import ZoteroImporter
from .dialogs.schedule_dialog import ScheduleDialog
from .dialogs.timer_elapsed import TimerElapsedDialog
from .dialogs.done_dialog import DoneDialog
from .api import open_siac_with_id
from .tag_find import display_tag_info
from .stats import calculate_note_stats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval
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

    # special case: only cmd to be valid outside the editor
    if cmd.startswith("siac-open-linked-note "):
        siac_nid        = int(cmd.split()[1])
        page            = int(cmd.split()[2])
        open_siac_with_id(siac_nid, page=page)
        return (True, None)


    if not isinstance(self, aqt.editor.Editor):
        return handled

    state.last_cmd    = cmd
    if cmd.startswith("siac-r-"):
        state.last_search_cmd       = cmd
        state.last_page_requested   = None

    index       = get_index()
    # just to make sure
    if index is not None and UI._editor is None:
        UI.set_editor(self)
        Reader.set_editor(self)

    # there has to be a more elegant way of processing the cmds than a giant if else...

    # In general, cmds should start with "siac-" to avoid collisions with other add-ons and for easier debugging.
    # Commands that render some kind of result should start with "siac-r-",
    # so that they can be stored and repeated if the UI needs to be refreshed.

    

    elif cmd.startswith("siac-page "):
        # Page button in results clicked.
        # This is a special command, it triggers a rendering, but should not be stored
        # as last command in state.last_search_cmd like other cmds that start with "siac-r-".
        # That is because the UI caches the last result, and uses that cached result to display
        # a requested page (but to refresh the UI, we don't want the result to be cached).
        # So if we want to refresh the UI, state.last_search_cmd should point to the cmd that produces the search results,
        # and state.last_page_requested indicates that we are on a page other than the first at the time of refresh.
        state.last_page_requested = int(cmd.split()[1])
        UI.show_page(self, int(cmd.split()[1]))

   

 
    elif cmd.startswith("siac-note-stats "):
        # note "Info" button clicked
        set_stats(cmd[16:], calculate_note_stats(cmd[16:]))

    elif cmd.startswith("siac-tag-clicked ") and not config["tagClickShouldSearch"]:
        add_tag(cmd[17:])

    elif cmd.startswith("siac-edit-note "):
        # "Edit" clicked on a normal (Anki) note
        open_editor(mw, int(cmd[15:]))

    elif cmd.startswith("siac-eval "):
        # direct eval
        eval(cmd[10:])
    elif cmd.startswith("siac-exec "):
        # direct exec
        exec(cmd[10:])

    elif cmd.startswith("siac-open-folder "):
        # try to open a folder path with the default explorer
        folder = " ".join(cmd.split()[1:]).replace("\\", "/")
        if not folder.endswith("/"):
            folder += "/"
        if os.path.isdir(folder):
            try:
                if isLin:
                        import subprocess
                        subprocess.check_call(['xdg-open', '--', folder])
                else:
                    QDesktopServices.openUrl(QUrl("file:///" + folder))
            except:
                tooltip("Failed to open folder.")

    elif cmd.startswith("siac-pin"):
        # pin note symbol clicked
        set_pinned(cmd[9:])

    elif cmd.startswith("siac-freeze "):
        UI.frozen = cmd.split()[1].lower() == "true"

    elif cmd.startswith("siac-window-mode "):
        state.set_window_mode(cmd.split()[1], self)

    elif cmd.startswith("siac-render-tags"):
        # clicked on a tag with (+n)
        UI.print_tag_hierarchy(cmd[16:].split(" "))

    elif cmd.startswith("siac-fetch-json "):
        key         = cmd.split()[1]
        resource    = " ".join(cmd.split()[2:])
        args        = resource.split("$&&$")[1:] if len(resource.split("$&&$")) > 1 else []
        handle_json_fetch(self.web, key, resource.split("$&&$")[0], args)

    elif cmd == "siac-fill-deck-select":
        UI.fillDeckSelect(self, expanded=True, update=False)

    elif cmd == "siac-fill-tag-select":
        fillTagSelect(expanded=True)

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
        if check_index() and ix < len(UI.previous_calls):
            UI.print_search_results(*UI.previous_calls[ix] + [True])

    elif cmd == "siac-rerender":
        UI.try_rerender_last()

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

    elif cmd.startswith("siac-queue-info "):
        nid         = int(cmd.split()[1])
        note        = get_note(nid)
        read_stats  = get_read_stats(nid)
        UI.js("""
            if (pdfLoading || noteLoading || modalShown) {
                hideQueueInfobox();
            } else {
                // document.getElementById('siac-pdf-bottom-tabs').style.visibility = "hidden";
                document.getElementById('siac-queue-infobox').style.display = "block";
                document.getElementById('siac-queue-infobox').innerHTML =`%s`;
            }
        """ % Reader.get_queue_infobox(note, read_stats))

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


    elif cmd.startswith("siac-insert-pages-total "):
        insert_pages_total(int(cmd.split()[1]), int(cmd.split()[2]))
    
    elif cmd == "siac-url-dialog":
        dialog = UrlImporter(self.parentWindow)
        if dialog.exec_():
            if dialog.chosen_url:
                prio    = dialog.queue_schedule
                name    = dialog.get_name()
                path    = get_config_value("pdfUrlImportSavePath")
                path    = utility.misc.get_pdf_save_full_path(path, name)
                utility.misc.url_to_pdf(dialog.chosen_url, path, lambda *args: tooltip("Generated PDF Note.", period=4000))
                title = dialog._chosen_name
                if title is None or len(title) == 0:
                    title = name
                create_note(title, "", path, "", "", "", prio, "", url = dialog.chosen_url)
            else:
                pass

    elif cmd == "siac-zotero-import":
        dialog = ZoteroImporter(self.parentWindow)
        if dialog.exec_():
            tooltip(f"Created {dialog.total_count} notes.")

    elif cmd == "siac-schedule-dialog":
        # show the dialog that allows to change the schedule of a note
        show_schedule_dialog(self.parentWindow)


   

    elif cmd == "siac-reading-modal-tabs-left-browse":
        # clicked on "Browse" in the tabs on the fields' side.
        Reader.show_browse_tab()

    elif cmd == "siac-reading-modal-tabs-left-flds":
        # clicked on "Fields" in the tabs on the fields' side.
        Reader.show_fields_tab()

    elif cmd == "siac-reading-modal-tabs-left-pdfs":
        # clicked on "Fields" in the tabs on the fields' side.
        Reader.show_pdfs_tab()
    
    elif cmd == "siac-reading-modal-tabs-left-md":
        Reader.show_md_tab()

    elif cmd.startswith("siac-pdf-left-tab-anki-search "):
        # search input coming from the "Browse" tab in the pdf viewer
        inp = " ".join(cmd.split(" ")[1:])
        index.search(inp, ["-1"], only_user_notes = False, print_mode = "pdf.left")

    elif cmd.startswith("siac-pdf-left-tab-pdf-search "):
        # search input coming from the "PDFs" tab in the pdf viewer
        inp = " ".join(cmd.split(" ")[1:])
        if inp:
            notes = find_pdf_notes_by_title(inp)
            Reader.sidebar.print(notes)

    #
    # Search 
    #
    elif handle_search(self, cmd): 
        return (True, None)

    #
    # Markdown
    #
    elif handle_md(self, cmd): 
        return (True, None)
    
    #
    # Config
    #
    elif handle_config(self, cmd):
        return (True, None)

    #
    # Notes
    #
    elif handle_notes(self, cmd):
        return (True, None)
    
    #
    # Reader - Highlighting
    #
    elif handle_highlighting(self, cmd):
        return (True, None)

    #
    # Reader - Unsorted
    #
    elif handle_reader(self, cmd):
        return (True, None)
    

    elif cmd.startswith("siac-p-sort "):
        if check_index():
            parse_sort_cmd(cmd[12:])

    elif cmd == "siac-model-dialog":
        display_model_dialog()

    elif cmd.startswith("siac-r-added-same-day "):
        stamp               = set_stamp()
        index.lastSearch    = (None, None, "createdSameDay", index.limit)
        UI.print_search_results(["Anki", "Added same day"],  get_created_same_day(int(cmd.split()[1]), index.pinned, index.limit), stamp)

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
            UI.print_timeline_info(context_html, res)

    elif cmd == "siac_rebuild_index":
        # we have to reset the ui because if the index is recreated, its values won't be in sync with the ui anymore
        self.web.eval("""
            $('#searchResults').html('').hide();
            $('#siac-pagination-wrapper,#siac-pagination-status,#searchInfo').html("");
            $('#toggleTop').removeAttr('onclick').unbind("click");
            $('#greyout').show();
            $('#loader').show();""")
        set_index(None)
        build_index(force_rebuild=True, execute_after_end=after_index_rebuilt)

    elif cmd.startswith("siac-searchbar-mode"):
        index.searchbar_mode = cmd.split()[1]

    elif cmd == "siac-initialised-editor":
        run_hooks("editor-with-siac-initialised")



    elif cmd.startswith("siac-read-user-note "):
        id = int(cmd.split()[1])
        if id >= 0:
            pg  = None
            if len(cmd.split()) > 2:
                pg = int(cmd.split()[2])
            Reader.display(id, page=pg)

    elif cmd == "siac-r-user-note-queue":
        stamp = set_stamp()
        notes = get_priority_list()
        if check_index():
            UI.print_search_results(["Queue"],  notes, stamp)

    elif cmd == "siac-r-user-note-queue-random":
        stamp = set_stamp()
        notes = get_queue_in_random_order()
        if check_index():
            UI.print_search_results(["Queue", "Random order"],  notes, stamp)

    elif cmd == "siac-r-user-note-untagged":
        stamp = set_stamp()
        notes = get_untagged_notes()
        if check_index():
            UI.print_search_results(["SIAC notes", "Untagged"],  notes, stamp)

    elif cmd == "siac-r-user-note-newest":
        stamp = set_stamp()
        if check_index():
            notes = get_newest(index.limit, index.pinned)
            UI.print_search_results(["SIAC notes", "Newest"],  notes, stamp)

    elif cmd == "siac-r-user-note-last-opened":
        stamp = set_stamp()
        notes = get_last_opened_notes()
        UI.print_search_results(["SIAC notes", "Last opened"],  notes, stamp)

    elif cmd == "siac-r-user-note-random":
        stamp = set_stamp()
        notes = get_random(index.limit, index.pinned)
        UI.print_search_results(["SIAC notes", "Random"],  notes, stamp)

    elif cmd == "siac-r-user-note-random-pdf":
        stamp = set_stamp()
        notes = get_random_pdf_notes(index.limit, index.pinned)
        UI.print_search_results(["PDFs", "Random"],  notes, stamp)

    elif cmd == "siac-r-user-note-random-text":
        stamp = set_stamp()
        notes = get_random_text_notes(index.limit, index.pinned)
        UI.print_search_results(["Text notes", "Random"],  notes, stamp)

    elif cmd == "siac-r-user-note-random-video":
        stamp = set_stamp()
        notes = get_random_video_notes(index.limit, index.pinned)
        UI.print_search_results(["Video notes", "Random"],  notes, stamp)

    elif cmd.startswith("siac-r-user-note-search-tag "):
        stamp       = set_stamp()
        tag         = " ".join(cmd.split()[1:])
        notes       = find_by_tag(tag)
        # add meta note
        prios       = [n.priority for n in notes if n.priority is not None and n.priority > 0]
        avg_prio    = round(sum(prios) / len(prios), 1) if len(prios) > 0 else "-"
        avg_prio    = "100" if avg_prio == 100.0 else avg_prio
        notes.insert(0, SiacNote.mock(f"Tag: {tag}", filled_template("notes/tag_meta", dict(tag = tag, avg_prio = avg_prio)), "Meta"))
        UI.print_search_results(["SIAC notes", "Tag", tag],  notes, stamp)

    elif cmd.startswith("siac-r-last-opened-with-tag "):
        stamp       = set_stamp()
        tag         = " ".join(cmd.split()[1:])
        notes       = find_by_tag_ordered_by_opened_last(tag)
        # add meta note
        prios       = [n.priority for n in notes if n.priority is not None and n.priority > 0]
        avg_prio    = round(sum(prios) / len(prios), 1) if len(prios) > 0 else "-"
        avg_prio    = "100" if avg_prio == 100.0 else avg_prio
        notes.insert(0, SiacNote.mock(f"Last opened for tag: {tag}", filled_template("notes/tag_meta", dict(tag = tag, avg_prio = avg_prio)), "Meta"))
        UI.print_search_results(["SIAC notes", "Tag", tag, "Last opened"],  notes, stamp)

    elif cmd == "siac-user-note-queue-picker":
        # show the queue manager dialog
        dialog  = QueuePicker(self.parentWindow)
        if dialog.exec_():
            if dialog.chosen_id() is not None and dialog.chosen_id() > 0:
                Reader.display(dialog.chosen_id())
            else:
                Reader.reload_bottom_bar()
        else:
            Reader.reload_bottom_bar()

    elif cmd == "siac-user-note-update-btns":
        queue_count = get_queue_count()
        self.web.eval("document.getElementById('siac-queue-btn').innerHTML = '&nbsp;<b>Queue [%s]</b>';" % queue_count)

    elif cmd == "siac-user-note-search":
        if check_index():
            UI.show_search_modal("searchForUserNote(event, this);", "Search for SIAC notes")

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
        if to_remove == Reader.note_id:
            nid = get_head_of_queue()
            if nid is None or nid < 0:
                UI.js("onReadingModalClose();")
            else:
                Reader.display(nid)
        else:
            Reader.reload_bottom_bar()
        tooltip(f"<center>Removed from Queue.</center>")

        # DEBUG
        if state.dev_mode:
            note = get_note(to_remove)
            assert(not get_priority(to_remove))
            assert(note.position is None or note.is_or_was_due())
            assert(not note.is_in_queue() or note.is_or_was_due())

    
    #
    #   Synonyms
    #

    elif cmd == "siac-synonyms":
        if check_index():
            UI.show_in_modal("Synonyms", get_synonym_dialog())
    elif cmd.startswith("siac-save-synonyms "):
        new_synonyms(cmd[19:])
        UI.show_in_modal("Synonyms", get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-edit-synonyms "):
        edit_synonym_set(cmd[19:])
        UI.show_in_modal("Synonyms", get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-delete-synonyms "):
        delete_synonym_set(int(cmd[21:].strip()))
        UI.show_in_modal("Synonyms", get_synonym_dialog())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-r-synset-search "):
        if check_index():
            UI.hide_modal()
            default_search_with_decks(self, cmd.split()[1], ["-1"])

    #
    # Settings Dialog
    #

    elif cmd == "siac-styling":
        show_settings_modal(self)

    elif cmd.startswith("siac-styling "):
        handle_settings_update(cmd[13:])

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
                Reader.show_img_field_picker_modal(name)
                os.remove(image)
    
    elif cmd.startswith("siac-add-image-to-fld "):
        # append the given base 64 encoded image to the field with the given index
        fld_ix  = int(cmd.split()[1])
        b64     = cmd.split()[2][13:]
        image   = utility.misc.base64_to_file(b64)
        if image is None or len(image) == 0:
            tooltip("Failed to temporarily save file.", period=5000)
        else:
            name = mw.col.media.addFile(image)
            if name is None or len(name) == 0:
                tooltip("Failed to add file to media col.", period=5000)
            else:
                UI.js(f"SIAC.Fields.appendToFieldHtml({fld_ix}, `<img src='{name}'></img>`);")
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

        fld_ix  = int(cmd.split()[1])
        t       = int(cmd.split()[2])
        l       = int(cmd.split()[3])
        w       = int(cmd.split()[4])
        h       = int(cmd.split()[5])
        capture_web(fld_ix, t, l, w, h)


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
        Reader.show_cloze_field_picker_modal(cloze_text)

    elif cmd.startswith("siac-last-cloze "):
        # after a field has been selected in "Send to Field", store that field in Reader
        fld = " ".join(cmd.split()[1:])
        Reader.last_cloze = (self.note.model()['id'], fld)

    elif cmd.startswith("siac-url-srch "):
        search_term = cmd.split("$$$")[1]
        url = cmd.split("$$$")[2]
        if search_term == "":
            return (True, None)
        if url is None or len(url) == 0:
            return (True, None)
        url_enc = urllib.parse.quote_plus(search_term)

        Reader.show_iframe_overlay(url=url.replace("[QUERY]", url_enc))

    elif cmd == "siac-close-iframe":
        Reader.hide_iframe_overlay()

    elif cmd.startswith("siac-show-web-search-tooltip "):
        inp = " ".join(cmd.split()[1:])
        if inp == "":
            return (True, None)
        Reader.show_web_search_tooltip(inp)

    elif cmd == "siac-timer-elapsed":
        # timer has elapsed, show a modal
        d = TimerElapsedDialog(aqt.mw.app.activeWindow())
        if d.exec_():
            if d.restart is not None:
                UI.js(f"startTimer({d.restart});")

    #
    #  Index info modal
    #

    elif cmd == "siac-index-info":
        if check_index():
            UI.show_in_modal("Info", get_index_info())

    elif cmd == "siac-r-show-tips":
        tips = get_tips_html()
        UI.print_in_meta_cards(tips)

    #
    #   Special searches
    #
    elif cmd.startswith("siac-predef-search "):
        state.last_search_cmd = cmd
        parse_predef_search_cmd(cmd, self)

    elif cmd == "siac-pdf-sidebar-last-addon":
        # last add-on notes button clicked in the pdf sidebar
        notes = get_newest(get_config_value_or_default("pdfTooltipResultLimit", 50), [])
        Reader.sidebar.print(notes, "", [])

    elif cmd == "siac-pdf-sidebar-last-anki":
        # last anki notes button clicked in the pdf sidebar
        notes = get_last_added_anki_notes(get_config_value_or_default("pdfTooltipResultLimit", 50))
        Reader.sidebar.print(notes, "", [])

    elif cmd == "siac-pdf-sidebar-pdfs-in-progress":
        # pdfs in progress button clicked in the pdf sidebar
        notes = get_in_progress_pdf_notes()
        Reader.sidebar.print(notes)

    elif cmd == "siac-pdf-sidebar-pdfs-unread":
        # pdfs unread button clicked in the pdf sidebar
        notes = get_all_unread_pdf_notes()
        Reader.sidebar.print(notes)

    elif cmd == "siac-pdf-sidebar-pdfs-last-added":
        # pdfs last added button clicked in the pdf sidebar
        notes = get_pdf_notes_last_added_first(limit=100)
        Reader.sidebar.print(notes)

    #
    #   Checkboxes
    #

    elif cmd.startswith("siac-toggle-highlight "):
        UI.highlighting         = cmd.split()[1] == "on"
        index.highlighting      = cmd.split()[1] == "on"
        config["highlighting"]  = cmd.split()[1] == "on"
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

    elif cmd == "toggleGrid on":
        if not check_index():
            return (True, None)
        config["gridView"] = True
        UI.gridView = True
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleGrid off":
        if not check_index():
            return (True, None)
        config["gridView"] = False
        UI.gridView = False
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "siac-decks-select-current":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            UI.js("selectDeckWithId(%s);" % deckChooser.selectedId())

    elif cmd == "siac-decks-select-current-and-subdecks":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            UI.js("selectDeckAndSubdecksWithId(%s);" % deckChooser.selectedId())

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
        UI.sidebar.display()
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "siac-hide-note-sidebar":
        config["notes.sidebar.visible"] = False
        UI.sidebar.hide()
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "siac-sidebar-show-notes-tab":
        UI.sidebar.show_tab(UI.sidebar.ADDON_NOTES_TAB)
    elif cmd == "siac-sidebar-show-import-tab":
        UI.sidebar.show_tab(UI.sidebar.PDF_IMPORT_TAB)
    elif cmd == "siac-sidebar-show-special-tab":
        UI.sidebar.show_tab(UI.sidebar.SPECIAL_SEARCHES_TAB)

    elif cmd.startswith("siac-preview "):
        # clicked on preview icon -> open preview modal
        nid     = int(cmd.split(" ")[1])
        cards   = [mw.col.getCard(c) for c in mw.col.find_cards(f"nid:{nid}")]
        if len(cards) > 0:
            d = AddPreviewer(self.parentWindow, mw, cards)
            d.open()

    elif cmd == "siac-rev-last-linked":
        # clicked "Review" on modal that asks if the user wants to review the last notes before reading
        last_linked     = get_last_linked_notes(Reader.note_id, limit=500)
        if len(last_linked) > 0:
            if hasattr(mw.col, "find_cards"):
                due_today   = mw.col.find_cards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked]))
            else:
                due_today   = mw.col.findCards("(is:due or is:new or (prop:due=1 and is:review)) and (%s)" % " or ".join([f"nid:{nid}" for nid in last_linked]))
            (success, message)     = create_filtered_deck(due_today)
            if success:
                mw.col.startTimebox()
                mw.moveToState("review")
                mw.activateWindow()
                # workaround, as activateWindow doesn't seem to bring the main window on top on OSX
                if isMac:
                    mw.raise_()
            else:
                tooltip("Failed to create filtered deck.\n"+message)

    elif cmd == "siac-reopen-file":
        # opening a siac note in the reader which has a protocol in the source
        # e.g. file:///abc.txt
        source = Reader.note.source
        tooltip("Opening external file:<br>" + source)
        try:
            QDesktopServices.openUrl(QUrl(source, QUrl.TolerantMode))
        except:
            tooltip("Failed to open external file:<br>" + source)



    else:
        return handled

    # If we are here, else didn't return. So an (el)if did suceed, the
    # action was done, so we can return message to state that the
    # command is handled.
    return (True, None)


def parse_sort_cmd(cmd):
    """ Helper function to parse the various sort commands (newest/remove tagged/...) """

    if cmd == "newest":
        UI.sort_by_date("desc")
    elif cmd == "oldest":
        UI.sort_by_date("asc")
    elif cmd == "remUntagged":
        UI.remove_untagged()
    elif cmd == "remTagged":
        UI.remove_tagged()
    elif cmd == "remUnreviewed":
        UI.remove_unreviewed()
    elif cmd == "remReviewed":
        UI.remove_reviewed()
    elif cmd == "remSuspended":
        UI.remove_suspended()
    elif cmd == "remUnsuspended":
        UI.remove_unsuspended()

def parse_predef_search_cmd(cmd: str, editor: aqt.editor.Editor):
    """ Helper function to parse the various predefined searches (last added/longest text/...) """

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
    elif stype == "highestPerf":
        res = findNotesWithHighestPerformance(decks, limit, index.pinned)
    elif stype == "lastAdded":
        res = get_notes_by_created_date(index, editor, decks, limit, "desc")
    elif stype == "firstAdded":
        res = get_notes_by_created_date(index, editor, decks, limit, "asc")
    elif stype == "lastModified":
        res = get_last_modified_notes(index, decks, limit)
    elif stype == "lowestRet":
        res = findNotesWithLowestPerformance(decks, limit, index.pinned, retOnly = True)
    elif stype == "highestRet":
        res = findNotesWithHighestPerformance(decks, limit, index.pinned, retOnly = True)
    elif stype == "longestText":
        res = findNotesWithLongestText(decks, limit, index.pinned)
    elif stype == "randomUntagged":
        res = getRandomUntagged(decks, limit)
    elif stype == "lastUntagged":
        res = get_last_untagged(decks, limit)
    elif stype == "highestInterval":
        res = getSortedByInterval(decks, limit, index.pinned, "desc")
    elif stype == "lowestInterval":
        res = getSortedByInterval(decks, limit, index.pinned, "asc")
    elif stype == "lastReviewed":
        res = getLastReviewed(decks, limit)
    elif stype == "lastLapses":
        res = getLastLapses(decks, limit)
    elif stype == "longestTime":
        res = getByTimeTaken(decks, limit, "desc")
    elif stype == "shortestTime":
        res = getByTimeTaken(decks, limit, "asc")
    UI.print_search_results(["Anki", "Predef. search", stype],  res, stamp)


def set_stamp() -> Optional[str]:
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    stamp     = utility.misc.get_milisec_stamp()
    UI.latest = stamp
    return stamp

def set_stats(nid: int, stats: Tuple[Any, ...]):
    """ Insert the statistics into the given card. """
    if check_index():
        UI.show_stats(stats[0], stats[1], stats[2], stats[3])

def rerenderNote(nid: int):
    res = mw.col.db.all("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid)
    if res is not None and len(res) > 0:
        res = res[0]
        UI.update_single(res)

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
    if len(textRaw) > 3000:
        if editor is not None and editor.web is not None:
            UI.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(textRaw)
    if len(cleaned) == 0:
        UI.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(textRaw, 100).replace("\u001f", "").replace("`", "&#96;"))
        return
    index.lastSearch = (cleaned, decks, "default")
    searchRes = index.search(cleaned, decks)

@requires_index_loaded
def search_for_user_notes_only(editor: aqt.editor.Editor, text: str):
    """ Uses the index to clean the input and find user notes. """

    if text is None:
        return
    index = get_index()
    if len(text) > 3000:
        UI.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(text)
    if len(cleaned) == 0:
        UI.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(text, 100).replace("\u001f", "").replace("`", "&#96;"))
        return
    index.lastSearch    = (cleaned, ["-1"], "user notes")
    searchRes           = index.search(cleaned, ["-1"], only_user_notes = True)

@requires_index_loaded
def add_note_to_index(note: Note):
    get_index().addNote(note)

@requires_index_loaded
def add_tag(tag: str):
    """ Insert the given tag in the tag field at bottom if not already there. """

    # index = get_index()
    # if tag == "" or index is None or UI._editor is None:
    #     return
    # tagsExisting = UI._editor.tags.text()
    # if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
    #     return

    # UI._editor.tags.setText(tagsExisting + " " + tag)
    # UI._editor.saveTags()

    UI.js("setTags("+tag.replace('"', '\\"')+")")

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
        UI.fields_to_hide_in_results = config["fieldsToHideInResults"]
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
    if ix is None or Reader.note_id is not None:
        return

    if editor is None:
        editor = UI._editor

    # executing the last cmd again will reset state.last_page_requested, so store it before
    page = state.last_page_requested

    # execute the last command again
    expanded_on_bridge_cmd(None, state.last_search_cmd, editor)

    # If state.last_page_requested was not None, we were on a page > 1.
    # So now that we have executed the last search cmd again, which refreshed the results,
    # go to that page again.
    if page is not None:
        UI.show_page(editor, page)

def show_schedule_dialog(parent_window):
    """ Show the dialog that allows to change the schedule of a note """

    index           = get_index()
    original_sched  = Reader.note.reminder
    nid             = Reader.note_id
    dialog          = ScheduleDialog(Reader.note, parent_window)
    if dialog.exec_():
        schedule = dialog.schedule()
        if schedule != original_sched:
            update_reminder(nid, schedule)
            # set position to null before recalculating queue
            prio = get_priority(nid)
            if not prio or prio == 0:
                null_position(nid)
            # null_position(Reader.note_id)
            Reader.note = get_note(nid)
            # Reader.note.reminder = schedule
            if original_sched is not None and original_sched != "" and (schedule == "" or schedule is None):
                tooltip(f"Removed schedule.")
            else:
                tooltip(f"Updated schedule.")
            run_hooks("updated-schedule")


def capture_web(fld_ix: int, t: int, l: int, w: int, h: int):
    """ Save the given rectangle part of the webview as image. """

    web     = UI._editor.web
    image   = QImage(w, h, QImage.Format.Format_ARGB32)
    region  = QRegion(l, t, w, h)
    painter = QPainter(image)

    page    = web.page()
    QWebEngineView.forPage(page).render(painter, QPoint(), region)
    painter.end()
    ba      = QByteArray()
    buf     = QBuffer(ba)
    # buf.open(QImage.OpenMode.ReadWrite)
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
            if fld_ix < 0:
                Reader.show_img_field_picker_modal(name)
            else:
                UI.js(f"SIAC.Fields.appendToFieldHtml({fld_ix}, `<img src='{name}'/>`)")
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
        if model is None:
            tooltip("""Could not resolve note model.<br>
            If you don't have a note type called 'Cloze', try filling 'pdf.clozegen.notetype' in the config. """, period=8000)
            return
        deck_chooser    = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deck_chooser is None:
            tooltip("Could not determine chosen deck.", period=5000)
            return
        did = deck_chooser.selectedId()
        if check_index():
            tags        = UI._editor.tags.text()
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
                if Reader.note_id is not None:
                    nid = Reader.note_id

                    def cb(page: int):
                        if page >= 0:
                            link_note_and_page(nid, note.id, page)
                            # update sidebar if shown
                            UI.js("updatePageSidebarIfShown()")
                    Reader.page_displayed(cb)
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
               <tr><td>PDF: Toggle PDF Links</td><td>  <b>%s</b></td></tr>
               <tr><td>PDF: Toggle Scissor Tool</td><td>  <b>%s</b></td></tr>
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
            str(index.initializationTime),
            index.get_number_of_notes(),
            config["alwaysRebuildIndexIfSmallerThan"],
            len(config["stopwords"]),
            sp_on if index.logging else sp_off,
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
            config["shortcuts.menubar.import.create_new"],
            config["pdf.shortcuts.toggle_search_on_select"],
            config["pdf.shortcuts.toggle_pdf_links"],
            config["pdf.shortcuts.scissor_tool"],
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

    # collect all currently used Qt shortcuts
    try:
        all_shortcuts = UI._editor.widget.findChildren(QShortcut)
        all_shortcuts = sorted([f"\"{x.key().toString()}\"" for x in all_shortcuts])
    except:
        all_shortcuts = []

    if all_shortcuts != []:
        html += f"""
            <b>Currently used shortcuts in the editor (this add-on + other add-ons + Anki):</b><br>
            <span>This might help when changing shortcuts in the config.</span><br>
            <span>Note that this list is not exhaustive, as these are only shortcuts managed by Qt, not Javascript.</span>
            <br>
            {", ".join(all_shortcuts)}
        """

    changes = UI.changelog()

    if changes:
        html += "<br/><br/><b>Changelog:</b><hr>"
        for ix, c in enumerate(changes):
            html += f"<br>{ix + 1}. {c}"

    issues = UI.known_issues()

    if issues:
        html += "<br/><br/><b>Known Issues:</b><hr>"
        for ix, i in enumerate(issues):
            html += f"<br>{ix + 1}. {i}"

    html += """
        <br><br>
        <b>Contact:</b>
        <hr class='mb-10'/>
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

    UI.show_in_modal("Timing", html)

def handle_settings_update(cmd: str):

    name    = cmd.split()[0]
    value   = " ".join(cmd.split()[1:])

    if name == "searchpane.zoom":
        config[name] = float(value)
        UI._editor.web.setZoomFactor(float(value))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"]   = m
        UI.hideSidebar    = m
        UI.js("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))

    elif name == "removeDivsFromOutput":
        m = value == "true" or value == "on"
        config[name] = m
        UI.remove_divs = m

    elif name == "results.hide_cloze_brackets":
        m = value == "true" or value == "on"
        config[name] = m
        UI.show_clozes = not m

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
            UI.js("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('siac-right-side').style.width = '%s%%';" % (value, right) )

    elif name == "showTimeline":
        config[name] = value == "true" or value == "on"
        if not config[name]:
            UI.js("""document.getElementById('cal-row').style.display = 'none'; 
            onWindowResize();""")
        else:
            UI.js("""
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
            UI.js("SIAC.State.showTagInfoOnHover = false;")
        elif config[name] and check_index():
            UI.js("SIAC.State.showTagInfoOnHover = true;")

    elif name == "tagHoverDelayInMiliSec":
        config[name] = int(value)
        if check_index():
            UI.js("SIAC.State.tagHoverTimeout = %s;" % value)

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
    write_config()


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
    except Exception as e:
        print("[SIAC] Error on emptying filtered deck:")
        print(e)
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
        cids.sort()
        dyn = mw.col.decks.get(did)
        if not "terms" in dyn:
            dyn["terms"] = []
        dyn["terms"][0] = [" or ".join([f"cid:{cid}" for cid in cids]), 9999, 0]
        dyn["resched"] = True
        mw.col.decks.save(dyn)
        if hasattr(mw.col.sched, "rebuild_filtered_deck"):
            mw.col.sched.rebuild_filtered_deck(did)
        else:
            mw.col.sched.rebuildDyn(did)
        mw.col.decks.select(did)
        return (True, "")
    except Exception as e:
        print("[SIAC] Error on creating filtered deck:")
        print(e)
        return (False, str(e))


@js
def write_config():
    mw.addonManager.writeConfig(__name__, config)
    return "$('.modal-close').unbind('click')"

def update_config(key, value):
    config[key] = value
    mw.addonManager.writeConfig(__name__, config)



def handle_json_fetch(web, key, resource_name, resource_args):

    r = {}
    if resource_name == "md-file-content":
        fpath           = resource_args[0]
        md_folder       = get_config_value("md.folder_path").replace("\\", "/")
        if not md_folder.endswith("/"):
            md_folder += "/"
        fpath_full      = md_folder + fpath
        r["content"]    = utility.misc.file_content(fpath_full)
    elif resource_name == "md-file-tree":
        r["tree"] = get_folder_structure(get_config_value("md.folder_path").replace("\\", "/"))

    web.eval(f"SIAC.fetch.callback('{key}', {json.dumps(r)})")



@requires_index_loaded
def after_index_rebuilt():

    search_index            = get_index()
    editor                  = UI._editor
    UI.frozen               = False

    editor.web.eval("""
        $('.freeze-icon').removeClass('frozen');
        SIAC.State.isFrozen = false;
        $('#selectionCb,#typingCb,#highlightCb').prop("checked", true);
        SIAC.State.searchOnSelection = true;
        SIAC.State.searchOnTyping = true;
        $('#toggleTop').click(function() { toggleTop(this); });
        $('#greyout').hide();
    """)
    UI.fillDeckSelect(editor)
    UI.setup_ui_after_index_built(editor, search_index)
