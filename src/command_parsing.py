from aqt import mw, dialogs
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import runHook, addHook, wrap
import aqt
import aqt.webview
from aqt.addcards import AddCards
import aqt.editor
from aqt.editor import Editor, EditorWebView
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.editcurrent import EditCurrent
import aqt.stats
from aqt.main import AnkiQt
from aqt.webview import AnkiWebPage
from datetime import datetime
import os
import random
import sqlite3
import re
import time as t
import math
import webbrowser
import platform
import functools
import sys
import html

from .state import checkIndex, get_index, set_index, corpus_is_loaded, set_corpus, set_edit, get_edit, get_old_on_bridge_cmd
from .indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import *
from .web.html import *
from .special_searches import *
from .notes import *
from .output import Output
from .textutils import clean, trimIfLongerThan, replaceAccentsWithVowels, expandBySynonyms, remove_fields
from .editor import openEditor, EditDialog, NoteEditor
from .tag_find import findBySameTag, display_tag_info
from .stats import calculateStats, findNotesWithLowestPerformance, findNotesWithHighestPerformance, getSortedByInterval, getTrueRetentionOverTime
from .utils import get_user_files_folder_path

config = mw.addonManager.getConfig(__name__)
   
original_on_bridge_cmd = None

def expanded_on_bridge_cmd(self, cmd):
    """
    Process the various commands coming from the ui - 
    this includes users clicks on option checkboxes, on rendered results, on special searches, etc.
    """
    searchIndex = get_index()
    if searchIndex is not None and searchIndex.output.editor is None:
        searchIndex.output.editor = self


    if not config["disableNonNativeSearching"] and cmd.startswith("fldChgd "):
        rerenderInfo(self, cmd[8:])
    elif cmd.startswith("siac-page "):
        if checkIndex():
            searchIndex.output.show_page(self, int(cmd.split()[1]))
    elif cmd.startswith("srchDB "):
        rerenderInfo(self, cmd[7:], searchDB = True)
    elif cmd.startswith("fldSlctd ") and not config["disableNonNativeSearching"] and searchIndex is not None:
        if searchIndex.logging:
            log("Selected in field: " + cmd[9:])
        rerenderInfo(self, cmd[9:])
    elif (cmd.startswith("nStats ")):
        setStats(cmd[7:], calculateStats(cmd[7:], searchIndex.output.gridView))
    elif (cmd.startswith("tagClicked ")):
        if config["tagClickShouldSearch"]:
            if checkIndex():
                rerenderInfo(self, cmd[11:].strip(), searchByTags=True)
        else:    
            addTag(cmd[11:])
    elif (cmd.startswith("editN ")):
        openEditor(mw, int(cmd[6:]))
    elif (cmd.startswith("pinCrd")):
        setPinned(cmd[6:])
    elif (cmd.startswith("renderTags")):
        searchIndex.output.printTagHierarchy(cmd[11:].split(" "))
    elif (cmd.startswith("randomNotes ") and checkIndex()):
        res = getRandomNotes(searchIndex, [s for s in cmd[11:].split(" ") if s != ""])
        searchIndex.output.printSearchResults(res["result"], res["stamp"])
    elif cmd == "toggleTagSelect":
        if checkIndex():
            searchIndex.tagSelect = not searchIndex.tagSelect
            if searchIndex.tagSelect:
                fillTagSelect()
            else:
                fillDeckSelect(self)
    elif cmd.startswith("searchTag "):
        if checkIndex():
            rerenderInfo(self, cmd[10:].strip(), searchByTags=True)

    elif cmd.startswith("tagInfo "):
        if checkIndex():
            #this renders the popup
            display_tag_info(self, cmd.split()[1], " ".join(cmd.split()[2:]), searchIndex)
    
    elif cmd.startswith("pSort "):
        if checkIndex():
            parseSortCommand(cmd[6:])
    
    elif cmd == "siac-model-dialog":
        display_model_dialog()
        
    elif cmd.startswith("addedSameDay "):
        if checkIndex():
            getCreatedSameDay(searchIndex, self, int(cmd[13:]))
    
    elif cmd == "lastTiming":
        if searchIndex is not None and searchIndex.lastResDict is not None:
            showTimingModal()


    elif cmd.startswith("calInfo "):
        if checkIndex():
            context_html = get_cal_info_context(int(cmd[8:]))
            res = get_notes_added_on_day_of_year(int(cmd[8:]), min(searchIndex.limit, 100))
            searchIndex.output.print_timeline_info(context_html, res)

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

    #
    # Notes 
    #
    
    elif cmd == "siac-create-note":
        NoteEditor(self.parentWindow)
        #editor.user_note_edit = aqt.dialogs.open("UserNoteEditor", mw, None)

    elif cmd.startswith("siac-edit-user-note "):
        id = int(cmd.split()[1])
        NoteEditor(self.parentWindow, id)
        #editor.user_note_edit = aqt.dialogs.open("UserNoteEditor", mw, id)
    
    elif cmd.startswith("siac-delete-user-note-modal "):
        nid = int(cmd.split()[1])
        display_note_del_confirm_modal(self, nid)
    
    elif cmd.startswith("siac-delete-user-note "):
        id = int(cmd.split()[1])
        delete_note(id)
        if searchIndex is not None and searchIndex.type != "Whoosh":
            searchIndex.deleteNote(id)

    elif cmd.startswith("siac-read-user-note "):
        id = int(cmd.split()[1])
        display_note_reading_modal(id)

    elif cmd == "siac-user-note-queue":
        stamp = setStamp()
        notes = get_priority_list()
        if checkIndex():
            searchIndex.output.printSearchResults(notes, stamp)

    elif cmd == "siac-user-note-queue-random":
        stamp = setStamp()
        notes = get_queue_in_random_order()
        if checkIndex():
            searchIndex.output.printSearchResults(notes, stamp)

    elif cmd == "siac-user-note-newest":
        stamp = setStamp()
        if checkIndex():
            notes = get_newest(searchIndex.limit, searchIndex.pinned)
            searchIndex.output.printSearchResults(notes, stamp)

    elif cmd == "siac-user-note-random":
        stamp = setStamp()
        if checkIndex():
            notes = get_random(searchIndex.limit, searchIndex.pinned)
            searchIndex.output.printSearchResults(notes, stamp)

    elif cmd == "siac-user-note-update-btns":
        queue_count = get_queue_count()
        self.web.eval("document.getElementById('siac-queue-btn').innerHTML = '&nbsp;<b>Queue [%s]</b>';" % queue_count)

    elif cmd == "siac-user-note-search":
        if checkIndex():
            searchIndex.output.show_search_modal("searchForUserNote(event, this);", "Search For User Notes")
    
    elif cmd.startswith("siac-user-note-search-inp "):
        if checkIndex():
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
        searchIndex.output.editor.web.eval("""
        document.getElementById('siac-queue-lbl').innerHTML = 'Position in Queue: %s / %s'; 
        $('#siac-queue-lbl').fadeIn('slow'); 
        $('.siac-queue-sched-btn:first').html('%s / %s');
        $('#siac-queue-readings-list').replaceWith(`%s`);
        """ % (inserted_index[0] + 1, inserted_index[1], inserted_index[0] + 1, inserted_index[1], queue_readings_list))

    elif cmd.startswith("siac-remove-from-queue "):
        nid = cmd.split()[1]
        update_position(nid, QueueSchedule.NOT_ADD)
        searchIndex.output.editor.web.eval("afterRemovedFromQueue();")
        searchIndex.output.editor.web.eval("$('#siac-queue-lbl').hide(); document.getElementById('siac-queue-lbl').innerHTML = 'Not in Queue'; $('#siac-queue-lbl').fadeIn();")

    elif cmd == "siac-user-note-queue-read-random":
        rand_id = get_random_id_from_queue()
        if rand_id >= 0:
            display_note_reading_modal(rand_id)
    elif cmd == "siac-user-note-queue-read-head":
        nid = get_head_of_queue()
        if nid >= 0:
            display_note_reading_modal(nid)


    elif cmd.startswith("siac-scale "):
        factor = float(cmd.split()[1])
        config["noteScale"] = factor
        writeConfig()
        if checkIndex():
            searchIndex.output.scale = factor
            if factor != 1.0:
                searchIndex.output.editor.web.eval("showTagInfoOnHover = false;")
            else:
                searchIndex.output.editor.web.eval("showTagInfoOnHover = true;")


    #
    #   Synonyms
    #

    elif cmd == "synonyms":
        if checkIndex():
            searchIndex.output.showInModal(getSynonymEditor())
    elif cmd.startswith("saveSynonyms "):
        newSynonyms(cmd[13:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()
    elif cmd.startswith("editSynonyms "):
        editSynonymSet(cmd[13:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()
    elif cmd.startswith("deleteSynonyms "):
        deleteSynonymSet(cmd[15:])
        searchIndex.output.showInModal(getSynonymEditor())
        searchIndex.synonyms = loadSynonyms()
    elif cmd.startswith("siac-synset-search "):
        if checkIndex():
            searchIndex.output.hideModal()
            defaultSearchWithDecks(editor, cmd.split()[1], ["-1"])
            

    elif cmd == "styling":
        showStylingModal(self)

    elif cmd.startswith("styling "):
        updateStyling(cmd[8:])

    elif cmd == "writeConfig":
        writeConfig()

    #
    #  Index info modal
    #
    
    elif cmd == "indexInfo":
        if checkIndex():
            searchIndex.output.showInModal(getIndexInfo())
    
    #
    #   Special searches
    #
    elif cmd.startswith("predefSearch "):
        parsePredefSearchCmd(cmd, self)
   
    elif cmd.startswith("similarForCard "):
        if checkIndex():
            cid = int(cmd.split()[1])
            min_sim = int(cmd.split()[2])
            res_and_html = find_similar_cards(cid, min_sim, 20)
            searchIndex.output.show_in_modal_subpage(res_and_html[1])


    #
    #   Checkboxes
    #

    elif (cmd.startswith("highlight ")):
        if checkIndex():
            searchIndex.highlighting = cmd[10:] == "on"
    elif (cmd.startswith("searchWhileTyping ")):
        if checkIndex():
            searchIndex.searchWhileTyping = cmd[18:] == "on"
    elif (cmd.startswith("searchOnSelection ")):
        if checkIndex():
            searchIndex.searchOnSelection = cmd[18:] == "on"
    elif (cmd.startswith("deckSelection")):
        if not checkIndex():
            return
        if searchIndex.logging:
            if len(cmd) > 13:
                log("Updating selected decks: " + str( [d for d in cmd[14:].split(" ") if d != ""]))
            else:
                log("Updating selected decks: []")
        if len(cmd) > 13:
            searchIndex.selectedDecks = [d for d in cmd[14:].split(" ") if d != ""]
        else:
            searchIndex.selectedDecks = []
        #repeat last search if default 
        tryRepeatLastSearch(self)

    elif cmd == "toggleTop on":
        if checkIndex():
            searchIndex.topToggled = True
    
    elif cmd == "toggleTop off":
        if checkIndex():
            searchIndex.topToggled = False

    elif cmd == "toggleGrid on":
        if not checkIndex():
            return
        config["gridView"] = True
        searchIndex.output.gridView = True
        tryRepeatLastSearch(self)
        mw.addonManager.writeConfig(__name__, config)

    elif cmd == "toggleGrid off":
        if not checkIndex():
            return
        config["gridView"] = False
        searchIndex.output.gridView = False
        tryRepeatLastSearch(self)
        mw.addonManager.writeConfig(__name__, config)
    
    elif cmd == "toggleAll on":
        if checkIndex():
            searchIndex.output.uiVisible = True
    elif cmd == "toggleAll off":
        if checkIndex():
            searchIndex.output.uiVisible = False

    elif cmd == "selectCurrent":
        deckChooser = aqt.mw.app.activeWindow().deckChooser if hasattr(aqt.mw.app.activeWindow(), "deckChooser") else None
        if deckChooser is not None and searchIndex is not None:
            searchIndex.output.editor.web.eval("selectDeckWithId(%s);" % deckChooser.selectedId())
    
    elif cmd.startswith("siac-update-field-to-hide-in-results "):
        if not checkIndex():
            return
        update_field_to_hide_in_results(cmd.split()[1], int(cmd.split()[2]), cmd.split()[3] == "true")

    elif cmd.startswith("siac-update-field-to-exclude "):
        if not checkIndex():
            return
        update_field_to_exclude(cmd.split()[1], int(cmd.split()[2]), cmd.split()[3] == "true")


    else:
        return get_old_on_bridge_cmd()(self, cmd)


def parseSortCommand(cmd):
    """
    Helper function to parse the various sort commands (newest/remove tagged/...)
    """
    searchIndex = get_index()
    if cmd == "newest":
        searchIndex.output.sortByDate("desc")
    elif cmd == "oldest":
        searchIndex.output.sortByDate("asc")
    elif cmd == "remUntagged":
        searchIndex.output.removeUntagged()
    elif cmd == "remTagged":
        searchIndex.output.removeTagged()
    elif cmd == "remUnreviewed":
        searchIndex.output.removeUnreviewed()
    elif cmd == "remReviewed":
        searchIndex.output.removeReviewed()    

def parsePredefSearchCmd(cmd, editor):
    """
    Helper function to parse the various predefined searches (last added/longest text/...)
    """
    if not checkIndex():
        return 
    searchIndex = get_index()
    cmd = cmd[13:]
    searchtype = cmd.split(" ")[0]
    limit = int(cmd.split(" ")[1])
    decks = cmd.split(" ")[2:]
    if searchtype == "lowestPerf":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestPerf")
        res = findNotesWithLowestPerformance(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestPerf":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestPerf")
        res = findNotesWithHighestPerformance(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastAdded":
        getCreatedNotesOrderedByDate(searchIndex, editor, decks, limit, "desc")
    elif searchtype == "firstAdded":
        getCreatedNotesOrderedByDate(searchIndex, editor, decks, limit, "asc")
    elif searchtype == "lastModified":
        getLastModifiedNotes(searchIndex, editor, decks, limit)
    elif searchtype == "lowestRet":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestRet")
        res = findNotesWithLowestPerformance(decks, limit, searchIndex.pinned,  retOnly = True)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestRet":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestRet")
        res = findNotesWithHighestPerformance(decks, limit, searchIndex.pinned,  retOnly = True)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "longestText":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestRet")
        res = findNotesWithLongestText(decks, limit, searchIndex.pinned)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "randomUntagged":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "randomUntagged")
        res = getRandomUntagged(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "highestInterval":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "highestInterval", limit)
        res = getSortedByInterval(decks, limit, searchIndex.pinned, "desc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lowestInterval":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lowestInterval", limit)
        res = getSortedByInterval(decks, limit, searchIndex.pinned, "asc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastReviewed":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lastReviewed", limit)
        res = getLastReviewed(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "lastLapses":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "lastLapses", limit)
        res = getLastLapses(decks, limit)
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "longestTime":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "longestTime", limit)
        res = getByTimeTaken(decks, limit, "desc")
        searchIndex.output.printSearchResults(res, stamp)
    elif searchtype == "shortestTime":
        stamp = setStamp()
        searchIndex.lastSearch = (None, decks, "shortestTime", limit)
        res = getByTimeTaken(decks, limit, "asc")
        searchIndex.output.printSearchResults(res, stamp)


def setStamp():
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    if checkIndex():
        searchIndex = get_index()
        stamp = searchIndex.output.getMiliSecStamp()
        searchIndex.output.latest = stamp
        return stamp
    return None


              


def setStats(nid, stats):
    """
    Insert the statistics into the given card.
    """
    if checkIndex():
        get_index().output.showStats(stats[0], stats[1], stats[2], stats[3])



def rerenderInfo(editor, content="", searchDB = False, searchByTags = False):
    """
    Main function that is executed when a user has typed or manually entered a search.
    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    if (len(content) < 1):
        editor.web.eval("setSearchResults(``, 'No results found for empty string')")
    decks = list()
    if "~" in content:
        for s in content[:content.index('~')].split(','):
            decks.append(s.strip())
    searchIndex = get_index()
    if searchIndex is not None:
        
        if searchDB:
            content = content[content.index('~ ') + 2:].strip()
            if len(content) == 0:
                editor.web.eval("setSearchResults(``, 'No results found for empty string')")
                return
            searchIndex.lastSearch = (content, decks, "db")
            searchRes = searchIndex.searchDB(content, decks)  

        elif searchByTags:
            stamp = searchIndex.output.getMiliSecStamp()
            searchIndex.output.latest = stamp
            searchIndex.lastSearch = (content, ["-1"], "tags")
            searchRes = findBySameTag(content, searchIndex.limit, [], searchIndex.pinned)

        else:
            if len(content[content.index('~ ') + 2:]) > 2000:
                editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
                return
            content = content[content.index('~ ') + 2:]
            searchRes = searchIndex.search(content, decks)
      
      
        if (searchDB or searchByTags) and editor is not None and editor.web is not None:
            if searchRes is not None and len(searchRes["result"]) > 0:
                    searchIndex.output.printSearchResults(searchRes["result"], stamp if searchByTags else searchRes["stamp"], editor, searchIndex.logging)
            else:
                editor.web.eval("setSearchResults(``, 'No results found.')")
       

def rerenderNote(nid):
    res = mw.col.db.execute("select distinct notes.id, flds, tags, did, mid from notes left join cards on notes.id = cards.nid where notes.id = %s" % nid).fetchone()
    if res is not None and len(res) > 0:
        searchIndex = get_index()
        if searchIndex is not None and searchIndex.output is not None:
            searchIndex.output.updateSingle(res)


def defaultSearchWithDecks(editor, textRaw, decks):
    """
    Uses the searchIndex to clean the input and find notes.
    
    Args:
        decks: list of deck ids (string), if "-1" is contained, all decks are searched
    """
    if len(textRaw) > 2000:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
        return
    searchIndex = get_index()
    cleaned = searchIndex.clean(textRaw)
    if len(cleaned) == 0:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>')" % trimIfLongerThan(textRaw, 100))
        return
    searchIndex.lastSearch = (cleaned, decks, "default")
    searchRes = searchIndex.search(cleaned, decks)

def search_for_user_notes_only(editor, text):
    """
    Uses the searchIndex to clean the input and find user notes.
    """
    if len(text) > 2000:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was <b>too long</b>')")
        return
    searchIndex = get_index()
    cleaned = searchIndex.clean(text)
    if len(cleaned) == 0:
        if editor is not None and editor.web is not None:
            editor.web.eval("setSearchResults(``, 'Query was empty after cleaning.<br/><br/><b>Query:</b> <i>%s</i>')" % trimIfLongerThan(text, 100))
        return
    searchIndex.lastSearch = (cleaned, ["-1"], "user notes")
    searchRes = searchIndex.search(cleaned, ["-1"], only_user_notes = True)

def addHideShowShortcut(shortcuts, editor):
    if not "toggleShortcut" in config:
        return
    QShortcut(QKeySequence(config["toggleShortcut"]), editor.widget, activated=toggleAddon)


def getCurrentContent(editor):
    text = ""
    for f in editor.note.fields:
        text += f
    return text

def addNoteAndUpdateIndex(dialog, note):
    res = origAddNote(dialog, note)
    addNoteToIndex(note)
        
    return res

def addNoteToIndex(note):
    searchIndex = get_index()
    if searchIndex is not None:
        searchIndex.addNote(note)




def addTag(tag):
    """
    Insert the given tag in the tag field at bottom if not already there.
    """
    searchIndex = get_index()
    if tag == "" or searchIndex is None or searchIndex.output.editor is None:
        return
    tagsExisting = searchIndex.output.editor.tags.text()
    if (tag == tagsExisting or  " " +  tag + " " in tagsExisting or tagsExisting.startswith(tag + " ") or tagsExisting.endswith(" " + tag)):
        return
    
    searchIndex.output.editor.tags.setText(tagsExisting + " " + tag)
    searchIndex.output.editor.saveTags()


def setPinned(cmd):
    """
    Update the pinned search results.
    This is important because they should not be contained in the search results.
    """
    pinned = []
    searchIndex = get_index()
    for id in cmd.split(" "):
        if len(id) > 0:
            pinned.append(id)
    if searchIndex is not None:
        searchIndex.pinned = pinned
        if searchIndex.logging:
            log("Updated pinned: " + str(searchIndex.pinned))



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
    if checkIndex():
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

def tryRepeatLastSearch(editor = None):
    """
    Sometimes it is useful if we can simply repeat the last search,
    e.g. the user has clicked another deck in the deck select.
    """
    searchIndex = get_index()

    if searchIndex is not None and searchIndex.lastSearch is not None:
        if editor is None and searchIndex.output.editor is not None:
            editor = searchIndex.output.editor
        
        if searchIndex.lastSearch[2] == "default":
            defaultSearchWithDecks(editor, searchIndex.lastSearch[0], searchIndex.selectedDecks)
        elif searchIndex.lastSearch[2] == "lastCreated":
            getCreatedNotesOrderedByDate(searchIndex, editor, searchIndex.selectedDecks, searchIndex.lastSearch[3], "desc")
        elif searchIndex.lastSearch[2] == "firstCreated":
            getCreatedNotesOrderedByDate(searchIndex, editor, searchIndex.selectedDecks, searchIndex.lastSearch[3], "asc")



def getIndexInfo():
    """
    Returns the html that is rendered in the popup that appears on clicking the "info" button
    """
    searchIndex = get_index()

    if searchIndex is None:
        return ""
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
             </table>
             
            """ % (searchIndex.type, str(searchIndex.initializationTime), searchIndex.get_number_of_notes(), config["alwaysRebuildIndexIfSmallerThan"], len(searchIndex.stopWords), 
            "<span style='background: green; color: white;'>&nbsp;On&nbsp;</span>" if searchIndex.logging else "<span style='background: red; color: black;'>&nbsp;Off&nbsp;</span>", 
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
            ("%ssiac-notes.db" % config["addonNoteDBFolderPath"]) if config["addonNoteDBFolderPath"] is not None and len(config["addonNoteDBFolderPath"]) > 0 else get_user_files_folder_path() + "siac-notes.db"
            )

    
    return html

def showTimingModal():
    """
    Builds the html and shows the modal which gives some info about the last executed search (timing, query after stopwords etc.)
    """
    searchIndex = get_index()

    html = "<h4>Query (stopwords removed, checked SynSets):</h4><div style='width: 100%%; max-height: 200px; overflow-y: auto; margin-bottom: 10px;'><i>%s</i></div>" % searchIndex.lastResDict["query"]
    if "decks" in searchIndex.lastResDict:
        html += "<h4>Decks:</h4><div style='width: 100%%; max-height: 200px; overflow-y: auto; margin-bottom: 10px;'><i>%s</i></div>" % ", ".join([str(d) for d in searchIndex.lastResDict["decks"]])
    html += "<h4>Execution time:</h4><table style='width: 100%'>"
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Removing Stopwords", searchIndex.lastResDict["time-stopwords"] if searchIndex.lastResDict["time-stopwords"] > 0 else "< 1") 
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Checking SynSets", searchIndex.lastResDict["time-synonyms"] if searchIndex.lastResDict["time-synonyms"] > 0 else "< 1") 
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Executing Query", searchIndex.lastResDict["time-query"] if searchIndex.lastResDict["time-query"] > 0 else "< 1")
    if searchIndex.type != "SQLite FTS5":
        html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Ranking", searchIndex.lastResDict["time-ranking"] if searchIndex.lastResDict["time-ranking"] > 0 else "< 1")
       
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML", searchIndex.lastResDict["time-html"] if searchIndex.lastResDict["time-html"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Highlighting", searchIndex.lastResDict["time-html-highlighting"] if searchIndex.lastResDict["time-html-highlighting"] > 0 else "< 1")
    html += "<tr><td>%s</td><td><b>%s</b> ms</td></tr>" % ("Building HTML - Formatting SIAC Notes", searchIndex.lastResDict["time-html-build-user-note"] if searchIndex.lastResDict["time-html-build-user-note"] > 0 else "< 1")
   
    html += "</table>"
    searchIndex.output.showInModal(html)


def updateStyling(cmd):
    searchIndex = get_index()

    name = cmd.split()[0]
    if len(cmd.split()) < 2:
        return
    value = " ".join(cmd.split()[1:])

    if name == "addToResultAreaHeight":
        if int(value) < 501 and int(value) > -501:
            config[name] = int(value)
            searchIndex.output.editor.web.eval("addToResultAreaHeight = %s; onResize();" % value)
    
    elif name == "renderImmediately":
        m = value == "true" or value == "on"
        config["renderImmediately"] = m
        searchIndex.output.editor.web.eval("renderImmediately = %s;" % ("true" if m else "false"))

    elif name == "hideSidebar":
        m = value == "true" or value == "on"
        config["hideSidebar"] = m
        searchIndex.output.hideSidebar = m
        searchIndex.output.editor.web.eval("document.getElementById('searchInfo').classList.%s('hidden');"  % ("add" if m else "remove"))
    
    elif name == "removeDivsFromOutput":
        m = value == "true" or value == "on"
        config["removeDivsFromOutput"] = m
        searchIndex.output.remove_divs = m

    elif name == "addonNoteDBFolderPath":
        if value is not None and len(value.strip()) > 0:
            value = value.replace("\\", "/")
            if not value.endswith("/"):
                value += "/"
        config["addonNoteDBFolderPath"] = value

    elif name == "leftSideWidthInPercent":
        config[name] = int(value)
        right = 100 - int(value)
        if checkIndex():
            searchIndex.output.editor.web.eval("document.getElementById('leftSide').style.width = '%s%%'; document.getElementById('infoBox').style.width = '%s%%';" % (value, right) )

    elif name == "showTimeline":
        config[name] = value == "true" or value == "on"
        if not config[name] and checkIndex():
            searchIndex.output.editor.web.eval("document.getElementById('cal-row').style.display = 'none'; onResize();")
        elif config[name] and checkIndex():
            searchIndex.output.editor.web.eval("""
            if (document.getElementById('cal-row')) {
                document.getElementById('cal-row').style.display = 'block';
            } else {
                document.getElementById('bottomContainer').children[0].innerHTML = `%s`;
                $('.cal-block-outer').mouseenter(function(event) { calBlockMouseEnter(event, this);});
                $('.cal-block-outer').click(function(event) { displayCalInfo(this);});
            }
            onResize();
            """ % getCalendarHtml())

    elif name == "showTagInfoOnHover":
        config[name] = value == "true" or value == "on"
        if not config[name] and checkIndex():
            searchIndex.output.editor.web.eval("showTagInfoOnHover = false;")
        elif config[name] and checkIndex():
            searchIndex.output.editor.web.eval("showTagInfoOnHover = true;")

    elif name == "tagHoverDelayInMiliSec":
        config[name] = int(value)
        if checkIndex():
            searchIndex.output.editor.web.eval("tagHoverTimeout = %s;" % value) 
    
    elif name == "alwaysRebuildIndexIfSmallerThan":
        config[name] = int(value)
    

def writeConfig():
    searchIndex = get_index()

    mw.addonManager.writeConfig(__name__, config)
    searchIndex.output.editor.web.eval("$('.modal-close').unbind('click')")





def after_index_rebuilt():
    search_index = get_index()
    if search_index is not None and search_index.output is not None and search_index.output.editor is not None:
        editor = search_index.output.editor
        editor.web.eval("""
        disableGridView();
        $('.freeze-icon').removeClass('frozen');
        isFrozen = false;
        $('#selectionCb,#typingCb,#tagCb,#highlightCb').prop("checked", true);
        searchOnSelection = true; 
        searchOnTyping = true;
        $('#toggleTop').click(function() { toggleTop(this); });
        """)
        fillDeckSelect(editor)