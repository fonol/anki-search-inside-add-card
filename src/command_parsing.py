from aqt import mw
from aqt.qt import *
import aqt
import aqt.webview
import aqt.editor
import aqt.stats
from anki.notes import Note
from aqt.utils import tooltip
import os
import urllib.parse


from .state import check_index, get_index, set_index, set_corpus, get_old_on_bridge_cmd
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
from .dialogs.url_import import UrlImporter
from .tag_find import findBySameTag, display_tag_info
from .stats import calculateStats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval
from .models import SiacNote
import utility.misc
import utility.text

config = mw.addonManager.getConfig(__name__)

original_on_bridge_cmd = None

def expanded_on_bridge_cmd(self, cmd):
    """
    Process the various commands coming from the ui -
    this includes users clicks on option checkboxes, on rendered results, on special searches, etc.
    """
    index = get_index()
    if index is not None and index.output.editor is None:
        index.output.editor = self

    if not config["disableNonNativeSearching"] and cmd.startswith("siac-fld "):
        rerender_info(self, cmd[8:])
    elif cmd.startswith("siac-page "):
        if check_index():
            index.output.show_page(self, int(cmd.split()[1]))
    elif cmd.startswith("siac-srch-db "):
        if check_index() and index.searchbar_mode == "Add-on":
            rerender_info(self, cmd[13:])
        else:
            rerender_info(self, cmd[13:], searchDB = True)
    elif cmd.startswith("fldSlctd ") and not config["disableNonNativeSearching"] and index is not None:
        if index.logging:
            log("Selected in field: " + cmd[9:])
        rerender_info(self, cmd[9:])
    elif (cmd.startswith("nStats ")):
        setStats(cmd[7:], calculateStats(cmd[7:], index.output.gridView))
    elif (cmd.startswith("tagClicked ")):
        if config["tagClickShouldSearch"]:
            if check_index():
                rerender_info(self, cmd[11:].strip(), searchByTags=True)
        else:
            add_tag(cmd[11:])
    elif cmd.startswith("siac-edit-note "):
        openEditor(mw, int(cmd[15:]))
    elif (cmd.startswith("siac-pin")):
        set_pinned(cmd[9:])
    elif (cmd.startswith("siac-render-tags")):
        index.output.printTagHierarchy(cmd[16:].split(" "))
    elif (cmd.startswith("siac-random-notes ") and check_index()):
        res = getRandomNotes(index, [s for s in cmd[17:].split(" ") if s != ""])
        index.output.print_search_results(res["result"], res["stamp"])
    elif cmd == "siac-fill-deck-select":
        fillDeckSelect(self, expanded=True)
    elif cmd == "siac-fill-tag-select":
        fillTagSelect(expanded=True)
    elif cmd.startswith("searchTag "):
        if check_index():
            rerender_info(self, cmd[10:].strip(), searchByTags=True)

    elif cmd.startswith("tagInfo "):
        if check_index():
            #this renders the popup
            display_tag_info(self, cmd.split()[1], " ".join(cmd.split()[2:]), index)

    elif cmd.startswith("siac-rerender "):
        ix = int(cmd.split()[1])
        if check_index() and ix < len(index.output.previous_calls):
            index.output.print_search_results(*index.output.previous_calls[ix] + [True])
            

    elif cmd.startswith("siac-show-loader "):
        target = cmd.split()[1]
        text = cmd.split()[2]
        show_loader(target, text)

    elif cmd == "siac-show-pdfs":
        if check_index():
            stamp = setStamp()
            notes = get_all_pdf_notes()
            # add special note at front
            sp_body = get_pdf_list_first_card()
            notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
            index.output.print_search_results(notes, stamp)

    elif cmd == "siac-pdf-last-read":
        stamp = setStamp()
        notes = get_pdf_notes_last_read_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.output.print_search_results(notes, stamp)

    elif cmd == "siac-pdf-last-added":
        stamp = setStamp()
        notes = get_pdf_notes_last_added_first()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.output.print_search_results(notes, stamp)
    
    elif cmd == "siac-pdf-find-invalid":
        stamp = setStamp()
        notes = get_invalid_pdfs()
        sp_body = get_pdf_list_first_card()
        notes.insert(0, SiacNote((-1, "PDF Meta", sp_body, "", "Meta", -1, "", "", "", "", -1)))
        index.output.print_search_results(notes, stamp)

    elif cmd.startswith("siac-queue-info "):
        nid = int(cmd.split()[1])
        note = get_note(nid)
        read_stats = get_read_stats(nid)
        index.output.js("""
            if (pdfLoading || noteLoading) {
                hideQueueInfobox();
            } else {
                document.getElementById('siac-pdf-bottom-tabs').style.display = "none";
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
        

    elif cmd.startswith("siac-jump-last-read"):
        jump_to_last_read_page(self, int(cmd.split()[1]))

    elif cmd.startswith("siac-jump-first-unread"):
        jump_to_first_unread_page(self, int(cmd.split()[1]))

    elif cmd.startswith("siac-mark-read-up-to "):
        mark_as_read_up_to(int(cmd.split()[1]), int(cmd.split()[2]), int(cmd.split()[3]))

    elif cmd.startswith("siac-mark-all-read "):
        mark_all_pages_as_read(int(cmd.split()[1]), int(cmd.split()[2]))

    elif cmd.startswith("siac-mark-all-unread "):
        mark_all_pages_as_unread(int(cmd.split()[1]))

    elif cmd.startswith("siac-insert-pages-total "):
        insert_pages_total(int(cmd.split()[1]), int(cmd.split()[2]))

    elif cmd.startswith("siac-show-cloze-modal "):
        selection = " ".join(cmd.split()[1:]).split("$$$")[0]
        sentences = cmd.split("$$$")[1:]
        display_cloze_modal(self, selection, sentences)

    elif cmd == "siac-url-dialog":
        dialog = UrlImporter(self.parentWindow)
        if dialog.exec_():
            if dialog.chosen_url is not None and len(dialog.chosen_url) >= 0:
                sched = dialog.queue_schedule
                name = dialog.get_name()
                path = config["pdfUrlImportSavePath"]
                if path is None or len(path) == 0:
                    return
                c = 0
                while os.path.isfile(os.path.join(path, name + ".pdf")):
                    name += "-" + str(c) 
                    c += 1 
                path = os.path.join(path, name + ".pdf")
                utility.misc.url_to_pdf(dialog.chosen_url, path)
                title = dialog._chosen_name
                if title is None or len(title) == 0:
                    title = name
                create_note(title, "", path, "", "", "", sched)
            else:
                pass
        else:
            pass

    
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
            index.output.print_timeline_info(context_html, res)

    elif cmd == "siac_rebuild_index":
        # we have to reset the ui because if the index is recreated, its values won't be in sync with the ui anymore
        self.web.eval("""
        $('#searchResults').html('').hide();
        $('#siac-pagination-wrapper,#siac-pagination-status,#searchInfo').html("");
        $('#toggleTop').removeAttr('onclick').unbind("click");
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

    elif cmd.startswith("siac-edit-user-note "):
        id = int(cmd.split()[1])
        if id > -1:
            NoteEditor(self.parentWindow, id)

    elif cmd.startswith("siac-delete-user-note-modal "):
        nid = int(cmd.split()[1])
        if nid > -1:
            display_note_del_confirm_modal(self, nid)

    elif cmd.startswith("siac-delete-user-note "):
        id = int(cmd.split()[1])
        delete_note(id)
        if index is not None and index.type != "Whoosh":
            index.deleteNote(id)
        run_hooks("user-note-deleted")

    elif cmd.startswith("siac-read-user-note "):
        id = int(cmd.split()[1])
        if id >= 0:
            display_note_reading_modal(id)

    elif cmd == "siac-user-note-queue":
        stamp = setStamp()
        notes = get_priority_list()
        if check_index():
            index.output.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-queue-random":
        stamp = setStamp()
        notes = get_queue_in_random_order()
        if check_index():
            index.output.print_search_results(notes, stamp)
    
    elif cmd == "siac-user-note-untagged":
        stamp = setStamp()
        notes = get_untagged_notes()
        if check_index():
            index.output.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-newest":
        stamp = setStamp()
        if check_index():
            notes = get_newest(index.limit, index.pinned)
            index.output.print_search_results(notes, stamp)

    elif cmd == "siac-user-note-random":
        stamp = setStamp()
        if check_index():
            notes = get_random(index.limit, index.pinned)
            index.output.print_search_results(notes, stamp)
    
    elif cmd.startswith("siac-user-note-search-tag "):
        stamp = setStamp()
        if check_index():
            notes = find_by_tag(" ".join(cmd.split()[1:]))
            index.output.print_search_results(notes, stamp)

    elif cmd.startswith("siac-user-note-queue-picker "):
        nid = int(cmd.split()[1])
        #picker = QueuePicker(self.parentWindow, _get_priority_list(), get_pdf_notes_not_in_queue())
        picker = QueuePicker(self.parentWindow, [], [])
        if picker.exec_():
            if picker.chosen_id is not None and picker.chosen_id >= 0:
                display_note_reading_modal(picker.chosen_id)
            else:
                reload_note_reading_modal_bottom_bar(nid)
        else:
            reload_note_reading_modal_bottom_bar(nid)


    elif cmd == "siac-user-note-update-btns":
        queue_count = get_queue_count()
        self.web.eval("document.getElementById('siac-queue-btn').innerHTML = '&nbsp;<b>Queue [%s]</b>';" % queue_count)

    elif cmd == "siac-user-note-search":
        if check_index():
            index.output.show_search_modal("searchForUserNote(event, this);", "Search For User Notes")

    elif cmd.startswith("siac-user-note-search-inp "):
        if check_index():
            search_for_user_notes_only(self, " ".join(cmd.split()[1:]))

    elif cmd.startswith("siac-update-note-text "):
        id = cmd.split()[1]
        text = " ".join(cmd.split(" ")[2:])
        update_note_text(id, text)

    elif cmd.startswith("siac-requeue "):
        nid = cmd.split()[1]
        queue_sched = int(cmd.split()[2])
        inserted_index = update_position(nid, QueueSchedule(queue_sched))
        queue_readings_list = get_queue_head_display(nid)
        index.output.js("""
        document.getElementById('siac-queue-lbl').innerHTML = 'Position: %s / %s';
        $('#siac-queue-lbl').fadeIn('slow');
        $('.siac-queue-sched-btn:first').html('%s / %s');
        $('#siac-queue-readings-list').replaceWith(`%s`);
        """ % (inserted_index[0] + 1, inserted_index[1], inserted_index[0] + 1, inserted_index[1], queue_readings_list))

    elif cmd.startswith("siac-requeue-tt "):
        nid = cmd.split()[1]
        nid_displayed = cmd.split()[3]
        queue_sched = int(cmd.split()[2])
        inserted_index = update_position(nid, QueueSchedule(queue_sched))
        queue_readings_list = get_queue_head_display(nid_displayed)
        p_s = "Position: "
        if nid_displayed != nid:
            pos_displayed = get_position(nid_displayed)
            if pos_displayed is None:
                pos_html = "Not in Queue"
                p_s = ""
            else: 
                pos_html = "%s / %s" % (pos_displayed + 1, inserted_index[1])
        else:
            pos_displayed = inserted_index[0]
            pos_html = "%s / %s" % (pos_displayed + 1, inserted_index[1])

        
        index.output.js("""
            document.getElementById('siac-queue-lbl').innerHTML = '%s%s';
            $('#siac-queue-lbl').fadeIn('slow');
            $('.siac-queue-sched-btn:first').html('%s');
            $('#siac-queue-readings-list').replaceWith(`%s`);
        """ % (p_s, pos_html, pos_html, queue_readings_list))


    elif cmd.startswith("siac-remove-from-queue "):
        # called from the buttons on the left
        nid = cmd.split()[1]
        update_position(nid, QueueSchedule.NOT_ADD)
        queue_readings_list = get_queue_head_display(nid)

        index.output.js("afterRemovedFromQueue();")
        index.output.js("$('#siac-queue-lbl').hide(); document.getElementById('siac-queue-lbl').innerHTML = 'Not in Queue'; $('#siac-queue-lbl').fadeIn();$('#siac-queue-readings-list').replaceWith(`%s`)" % queue_readings_list)
    
    elif cmd.startswith("siac-remove-from-queue-tt "):
        # called from the tooltip
        nid = cmd.split()[1]
        nid_displayed = cmd.split()[2]
        ix = update_position(nid, QueueSchedule.NOT_ADD)
        pos = get_position(nid_displayed)
        queue_len = ix[1]
        queue_readings_list = get_queue_head_display(nid)
        if pos is None:
            pos_js = """
                document.getElementById('siac-queue-lbl').innerHTML = 'Not in Queue';
                $('.siac-queue-sched-btn:first').html('Not in Queue');
                """
        else: 
            pos_js = """
                document.getElementById('siac-queue-lbl').innerHTML = 'Position: %s / %s';
                $('.siac-queue-sched-btn:first').html('%s / %s');
            """ % (pos + 1, queue_len, pos + 1, queue_len)
        js = """
        if ($('#siac-reading-modal-top-bar').data('nid') === '%s')  {
            document.getElementById('siac-queue-lbl').innerHTML = 'Not in Queue';
             $('.siac-queue-sched-btn:first').html('Not in Queue');
        } else {
            %s
        }
        $('#siac-queue-readings-list').replaceWith(`%s`)""" % (nid, pos_js, queue_readings_list)
        index.output.js(js)

    elif cmd == "siac-user-note-queue-read-random":
        rand_id = get_random_id_from_queue()
        if rand_id >= 0:
            display_note_reading_modal(rand_id)
        else:
            index.output.js("ungreyoutBottom();")
    elif cmd == "siac-user-note-queue-read-head":
        nid = get_head_of_queue()
        if nid >= 0:
            display_note_reading_modal(nid)
        else:
            index.output.js("ungreyoutBottom();")

    elif cmd.startswith("siac-scale "):
        factor = float(cmd.split()[1])
        config["noteScale"] = factor
        write_config()
        if check_index():
            index.output.scale = factor
            if factor != 1.0:
                index.output.js("showTagInfoOnHover = false;")
            else:
                index.output.js("showTagInfoOnHover = true;")

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
        update_reading_bottom_bar(nid)
    
    elif cmd.startswith("siac-hide-pdf-queue "):
        nid = int(cmd.split()[1])
        config["pdf.queue.hide"] = True
        write_config()
        update_reading_bottom_bar(nid)

    elif cmd == "siac-left-side-width":
        show_width_picker()

    elif cmd.startswith("siac-left-side-width "):
        value = int(cmd.split()[1])
        config["leftSideWidthInPercent"] = value
        right = 100 - value
        if check_index():
            index.output.js("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('infoBox').style.width = '%s%%';" % (value, right) )
        write_config()

    elif cmd.startswith("siac-pdf-show-bottom-tab "):
        nid = int(cmd.split()[1])
        tab = cmd.split()[2]
        show_pdf_bottom_tab(nid, tab)

    #
    #   Synonyms
    #

    elif cmd == "synonyms":
        if check_index():
            index.output.showInModal(getSynonymEditor())
    elif cmd.startswith("saveSynonyms "):
        newSynonyms(cmd[13:])
        index.output.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("editSynonyms "):
        editSynonymSet(cmd[13:])
        index.output.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("deleteSynonyms "):
        deleteSynonymSet(cmd[15:])
        index.output.showInModal(getSynonymEditor())
        index.synonyms = loadSynonyms()
    elif cmd.startswith("siac-synset-search "):
        if check_index():
            index.output.hideModal()
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
        name = mw.col.media.addFile(image)
        show_img_field_picker_modal(name)
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
        show_cloze_field_picker_modal(cloze_text)


    elif cmd.startswith("siac-url-srch "):
        search_term = cmd.split("$$$")[1]
        url = cmd.split("$$$")[2]
        if search_term == "":
            return
        if url is None or len(url) == 0:
            return 
        url_enc = urllib.parse.quote_plus(search_term)
        
        show_iframe_overlay(url=url.replace("[QUERY]", url_enc))

    elif cmd == "siac-close-iframe":
        hide_iframe_overlay()

    elif cmd.startswith("siac-show-web-search-tooltip "):
        inp = " ".join(cmd.split()[1:])
        if inp == "":
            return
        show_web_search_tooltip(inp)
    
    elif cmd.startswith("siac-timer-elapsed "):
        nid = int(cmd.split()[1])
        show_timer_elapsed_popup(nid)


    #
    #  Index info modal
    #

    elif cmd == "indexInfo":
        if check_index():
            index.output.showInModal(get_index_info())

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
            index.output.show_in_modal_subpage(res_and_html[1])


    #
    #   Checkboxes
    #

    elif (cmd.startswith("highlight ")):
        if check_index():
            index.highlighting = cmd[10:] == "on"
    elif (cmd.startswith("searchWhileTyping ")):
        if check_index():
            index.searchWhileTyping = cmd[18:] == "on"
    elif (cmd.startswith("searchOnSelection ")):
        if check_index():
            index.searchOnSelection = cmd[18:] == "on"
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
        index.output.gridView = True
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleGrid off":
        if not check_index():
            return
        config["gridView"] = False
        index.output.gridView = False
        try_repeat_last_search(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleAll on":
        if check_index():
            index.output.uiVisible = True
    elif cmd == "toggleAll off":
        if check_index():
            index.output.uiVisible = False

    elif cmd == "selectCurrent":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and index is not None:
            index.output.js("selectDeckWithId(%s);" % deckChooser.selectedId())

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
        display_notes_sidebar(self)
        mw.addonManager.writeConfig(__name__, config)
    elif cmd == "siac-hide-note-sidebar":
        config["notes.sidebar.visible"] = False
        self.web.eval("$('#siac-notes-sidebar').remove(); $('#resultsWrapper').css('padding-left', 0);")
        mw.addonManager.writeConfig(__name__, config)
    else:
        return get_old_on_bridge_cmd()(self, cmd)


def parseSortCommand(cmd):
    """
    Helper function to parse the various sort commands (newest/remove tagged/...)
    """
    index = get_index()
    if cmd == "newest":
        index.output.sortByDate("desc")
    elif cmd == "oldest":
        index.output.sortByDate("asc")
    elif cmd == "remUntagged":
        index.output.removeUntagged()
    elif cmd == "remTagged":
        index.output.removeTagged()
    elif cmd == "remUnreviewed":
        index.output.removeUnreviewed()
    elif cmd == "remReviewed":
        index.output.removeReviewed()

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
        index.output.print_search_results(res, stamp)
    elif searchtype == "highestPerf":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestPerf")
        res = findNotesWithHighestPerformance(decks, limit, index.pinned)
        index.output.print_search_results(res, stamp)
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
        index.output.print_search_results(res, stamp)
    elif searchtype == "highestRet":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestRet")
        res = findNotesWithHighestPerformance(decks, limit, index.pinned, retOnly = True)
        index.output.print_search_results(res, stamp)
    elif searchtype == "longestText":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestRet")
        res = findNotesWithLongestText(decks, limit, index.pinned)
        index.output.print_search_results(res, stamp)
    elif searchtype == "randomUntagged":
        stamp = setStamp()
        index.lastSearch = (None, decks, "randomUntagged")
        res = getRandomUntagged(decks, limit)
        index.output.print_search_results(res, stamp)
    elif searchtype == "highestInterval":
        stamp = setStamp()
        index.lastSearch = (None, decks, "highestInterval", limit)
        res = getSortedByInterval(decks, limit, index.pinned, "desc")
        index.output.print_search_results(res, stamp)
    elif searchtype == "lowestInterval":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lowestInterval", limit)
        res = getSortedByInterval(decks, limit, index.pinned, "asc")
        index.output.print_search_results(res, stamp)
    elif searchtype == "lastReviewed":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lastReviewed", limit)
        res = getLastReviewed(decks, limit)
        index.output.print_search_results(res, stamp)
    elif searchtype == "lastLapses":
        stamp = setStamp()
        index.lastSearch = (None, decks, "lastLapses", limit)
        res = getLastLapses(decks, limit)
        index.output.print_search_results(res, stamp)
    elif searchtype == "longestTime":
        stamp = setStamp()
        index.lastSearch = (None, decks, "longestTime", limit)
        res = getByTimeTaken(decks, limit, "desc")
        index.output.print_search_results(res, stamp)
    elif searchtype == "shortestTime":
        stamp = setStamp()
        index.lastSearch = (None, decks, "shortestTime", limit)
        res = getByTimeTaken(decks, limit, "asc")
        index.output.print_search_results(res, stamp)


def setStamp():
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    if check_index():
        index = get_index()
        stamp = utility.misc.get_milisec_stamp()
        index.output.latest = stamp
        return stamp
    return None

def setStats(nid, stats):
    """
    Insert the statistics into the given card.
    """
    if check_index():
        get_index().output.showStats(stats[0], stats[1], stats[2], stats[3])

def rerender_info(editor, content="", searchDB = False, searchByTags = False):
    """
    Main function that is executed when a user has typed or manually entered a search.
    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    index = get_index()
    if (len(content) < 1):
        index.output.empty_result("No results found for empty string")
    decks = list()
    if "~" in content:
        for s in content[:content.index('~')].split(','):
            decks.append(s.strip())
    if index is not None:

        if searchDB:
            content = content[content.index('~ ') + 2:].strip()
            if len(content) == 0:
                index.output.empty_result("No results found for empty string")
                return
            index.lastSearch = (content, decks, "db")
            searchRes = index.searchDB(content, decks)

        elif searchByTags:
            stamp = utility.misc.get_milisec_stamp()
            index.output.latest = stamp
            index.lastSearch = (content, ["-1"], "tags")
            searchRes = findBySameTag(content, index.limit, [], index.pinned)

        else:
            if len(content[content.index('~ ') + 2:]) > 2000:
                index.output.empty_result("Query was <b>too long</b>")
                return
            content = content[content.index('~ ') + 2:]
            searchRes = index.search(content, decks)


        if (searchDB or searchByTags) and editor is not None and editor.web is not None:
            if searchRes is not None and len(searchRes["result"]) > 0:
                index.output.print_search_results(searchRes["result"], stamp if searchByTags else searchRes["stamp"], editor, index.logging)
            else:
                index.output.empty_result("No results found")


def rerenderNote(nid):
    res = mw.col.db.execute("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid).fetchone()
    if res is not None and len(res) > 0:
        index = get_index()
        if index is not None and index.output is not None:
            index.output.updateSingle(res)

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
            index.output.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(textRaw)
    if len(cleaned) == 0:
        index.output.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(textRaw, 100).replace("\u001f", ""))
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
        index.output.empty_result("Query was <b>too long</b>")
        return
    cleaned = index.clean(text)
    if len(cleaned) == 0:
        index.output.empty_result("Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>" % utility.text.trim_if_longer_than(text, 100).replace("\u001f", ""))
        return
    index.lastSearch = (cleaned, ["-1"], "user notes")
    searchRes = index.search(cleaned, ["-1"], only_user_notes = True)

def addHideShowShortcut(shortcuts, editor):
    if not "toggleShortcut" in config:
        return
    QShortcut(QKeySequence(config["toggleShortcut"]), editor.widget, activated=toggleAddon)

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
    if tag == "" or index is None or index.output.editor is None:
        return
    tagsExisting = index.output.editor.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return

    index.output.editor.tags.setText(tagsExisting + " " + tag)
    index.output.editor.saveTags()

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
        get_index().output.fields_to_hide_in_results = config["fieldsToHideInResults"]
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
        if editor is None and index.output.editor is not None:
            editor = index.output.editor

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
            return
        deck_chooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deck_chooser is None: 
            return
        did = deck_chooser.selectedId()
        if check_index():
            tags = index.output.editor.tags.text()
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

        tooltip("Added %s Cloze(s)." % added, period=2000)
    except:
        tooltip("Something went wrong during Cloze generation.", period=2000)

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
               <tr><td>PDF: Page Right</td><td>  <b>Ctrl+Space / Ctrl+Right</b></td></tr>
               <tr><td>PDF: Page Right + Mark Page as Read</td><td>  <b>Ctrl+Shift+Space</b></td></tr>
               <tr><td>PDF: Page Left</td><td>  <b>Ctrl+Left</b></td></tr>
               <tr><td>New Note</td><td>  <b>Ctrl+Shift+N</b></td></tr>
               <tr><td>Confirm New Note</td><td>  <b>Ctrl+Enter</b></td></tr>

             </table>

            """ % (index.type, str(index.initializationTime), index.get_number_of_notes(), config["alwaysRebuildIndexIfSmallerThan"], len(index.stopWords),
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
    index.output.showInModal(html)

@requires_index_loaded
def update_styling(cmd):
    index = get_index()
    name = cmd.split()[0]
    if len(cmd.split()) < 2:
        return
    value = " ".join(cmd.split()[1:])

    if name == "addToResultAreaHeight":
        if int(value) < 501 and int(value) > -501:
            config[name] = int(value)
            index.output.js("addToResultAreaHeight = %s; onResize();" % value)
    elif name == "searchpane.zoom":
        config[name] = float(value)
        index.output.js("document.getElementById('infoBox').style.zoom = '%s'; showTagInfoOnHover = %s;" % (value, "false" if float(value) != 1.0 else "true"))
    elif name == "renderImmediately":
        m = value == "true" or value == "on"
        config["renderImmediately"] = m
        index.output.js("renderImmediately = %s;" % ("true" if m else "false"))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"] = m
        index.output.hideSidebar = m
        index.output.js("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))

    elif name == "removeDivsFromOutput":
        m = value == "true" or value == "on"
        config["removeDivsFromOutput"] = m
        index.output.remove_divs = m

    elif name == "addonNoteDBFolderPath":
        if value is not None and len(value.strip()) > 0:
            value = value.replace("\\", "/")
            if not value.endswith("/"):
                value += "/"
            config["addonNoteDBFolderPath"] = value

    elif name == "leftSideWidthInPercent":
        config[name] = int(value)
        right = 100 - int(value)
        if check_index():
            index.output.js("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('infoBox').style.width = '%s%%';" % (value, right) )

    elif name == "showTimeline":
        config[name] = value == "true" or value == "on"
        if not config[name] and check_index():
            index.output.js("document.getElementById('cal-row').style.display = 'none'; onResize();")
        elif config[name] and check_index():
            index.output.js("""
            if (document.getElementById('cal-row')) {
                document.getElementById('cal-row').style.display = 'block';
            } else {
                document.getElementById('bottomContainer').children[1].innerHTML = `%s`;
                $('.cal-block-outer').mouseenter(function(event) { calBlockMouseEnter(event, this);});
                $('.cal-block-outer').click(function(event) { displayCalInfo(this);});
            }
            onResize();
            """ % getCalendarHtml())

    elif name == "showTagInfoOnHover":
        config[name] = value == "true" or value == "on"
        if not config[name] and check_index():
            index.output.js("showTagInfoOnHover = false;")
        elif config[name] and check_index():
            index.output.js("showTagInfoOnHover = true;")

    elif name == "tagHoverDelayInMiliSec":
        config[name] = int(value)
        if check_index():
            index.output.js("tagHoverTimeout = %s;" % value)

    elif name == "alwaysRebuildIndexIfSmallerThan":
        config[name] = int(value)

    elif name == "pdfUrlImportSavePath":
        if value is not None and len(value.strip()) > 0:
            value = value.replace("\\", "/")
            if not value.endswith("/"):
                value += "/"
            config["pdfUrlImportSavePath"] = value


@js
def write_config():
    mw.addonManager.writeConfig(__name__, config)
    return "$('.modal-close').unbind('click')"


@requires_index_loaded
def after_index_rebuilt():
    search_index = get_index()
    editor = search_index.output.editor
    editor.web.eval("""
        $('.freeze-icon').removeClass('frozen');
        siacState.isFrozen = false;
        $('#selectionCb,#typingCb,#tagCb,#highlightCb').prop("checked", true);
        siacState.searchOnSelection = true;
        siacState.searchOnTyping = true;
        $('#toggleTop').click(function() { toggleTop(this); });
    """)
    fillDeckSelect(editor)
