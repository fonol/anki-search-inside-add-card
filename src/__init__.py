#!/usr/bin/env python
# -*- coding: utf-8 -*-
from aqt import mw
from aqt.qt import *
from anki.hooks import addHook
import aqt
from aqt.utils import showInfo
import aqt.webview
from aqt.addcards import AddCards
import aqt.editor
from aqt.editor import Editor, EditorWebView
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.editcurrent import EditCurrent
import aqt.stats
import os
import re
import time as t
import webbrowser
import functools
import sys
sys.path.insert(0, os.path.dirname(__file__))

import utility.tags
import utility.misc

from .state import check_index, get_index, corpus_is_loaded, set_corpus, set_edit, get_edit, set_old_on_bridge_cmd
from .index.indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import printStartingInfo, getScriptPlatformSpecific, showSearchResultArea, fillDeckSelect, fillTagSelect, reload_note_sidebar, display_notes_sidebar, setup_ui_after_index_built, reload_note_reading_modal_bottom_bar
from .web.html import right_side_html
from .notes import *
from .hooks import add_hook
from .dialogs.editor import EditDialog
from .internals import requires_index_loaded
from .config import get_config_value_or_default
from .command_parsing import expanded_on_bridge_cmd, addHideShowShortcut, rerenderNote, rerender_info, add_note_to_index


config = mw.addonManager.getConfig(__name__)

def init_addon():
    global oldOnBridge, orig_add_note, orig_tag_keypress, orig_save_and_close, origEditorContextMenuEvt
    set_old_on_bridge_cmd(Editor.onBridgeCmd)
    Editor.onBridgeCmd = expanded_on_bridge_cmd
    #todo: Find out if there is a better moment to start index creation
    create_db_file_if_not_exists()
    addHook("profileLoaded", build_index)
    addHook("profileLoaded", insert_scripts)
    orig_add_note = AddCards.addNote
    origEditorContextMenuEvt = EditorWebView.contextMenuEvent

    AddCards.addNote = add_note_and_update_index
    if get_config_value_or_default("searchOnTagEntry", True):
        orig_tag_keypress = TagEdit.keyPressEvent
        TagEdit.keyPressEvent = tag_edit_keypress

    setup_tagedit_timer()
    EditorWebView.contextMenuEvent = editorContextMenuEventWrapper

    orig_save_and_close = EditDialog.saveAndClose
    EditDialog.saveAndClose = editorSaveWithIndexUpdate
    addHook("setupEditorShortcuts", addHideShowShortcut) 

    setup_hooks()

    #main functions to search
    if not config["disableNonNativeSearching"]:
        aqt.editor._html += """
            <script>
            function sendContent(event) {
                if ((event && event.repeat) || pdfDisplayed != null || siacState.isFrozen)
                    return;
                let html = "";
                showLoading("Typing");
                $fields.each(function(index, elem) {
                    html += $(elem).html() + "\u001f";
                });
                pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
            }
            function sendSearchFieldContent() {
                showLoading("Searchbar");
                html = document.getElementById('siac-browser-search-inp').value + "\u001f";
                pycmd('siac-srch-db ' + siacState.selectedDecks.toString() + ' ~ ' + html);
            }

            function searchFor(text) {
                showLoading("Note Search");
                text += "\u001f";
                pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + text);
            }
    
            </script>
        """
    else:
        aqt.editor._html += """
            <script>
            function sendContent(event) {
                return;
            }
            function sendSearchFieldContent() {
                showLoading("Note Search");
                html = document.getElementById('siac-browser-search-inp').value + "\u001f";
                pycmd('siac-srch-db ' + siacState.selectedDecks.toString() + ' ~ ' + html);
            }
            function searchFor(text) {
                return;
            }
            </script>
        """
    # add shortcuts
    aqt.editor._html += """
    <script>
            document.addEventListener("keydown", function (e) {globalKeydown(e); }, false);
    </script>"""

    
    typing_delay = max(500, config['delayWhileTyping'])
    #this inserts all the javascript functions in scripts.js into the editor webview
    aqt.editor._html += getScriptPlatformSpecific(config["addToResultAreaHeight"], typing_delay)
    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    addHook("loadNote", on_load_note)



def add_note_and_update_index(dialog, note):
    res = orig_add_note(dialog, note)
    add_note_to_index(note)
    return res

def editorSaveWithIndexUpdate(dialog):
    orig_save_and_close(dialog)
    # update index
    index = get_index()
    if index is not None and dialog.editor is not None and dialog.editor.note is not None:
        index.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        index.output.edited[str(dialog.editor.note.id)] = t.time()


def on_load_note(editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    """

    #only display in add cards dialog or in the review edit dialog (if enabled)
    if editor.addMode or (get_config_value_or_default("useInEdit", False) and isinstance(editor.parentWindow, EditCurrent)):
        index = get_index()
        if index is not None and index.logging:
            log("Trying to insert html in editor")
            log("Editor.addMode: %s" % editor.addMode)
        zoom = get_config_value_or_default("searchpane.zoom", 1.0)
        show_tag_info_on_hover = "true" if get_config_value_or_default("showTagInfoOnHover", True) and get_config_value_or_default("noteScale", 1.0) == 1.0 and zoom == 1.0 else "false"
        editor.web.eval(f"""
        var addToResultAreaHeight = {get_config_value_or_default("addToResultAreaHeight", 0)}; 
        var showTagInfoOnHover = {show_tag_info_on_hover}; 
        tagHoverTimeout = {get_config_value_or_default("tagHoverDelayInMiliSec", 1000)};
        """)
        # render the right side (search area) of the editor
        # (the script checks if it has been rendered already)
        editor.web.eval(right_side_html(index is not None))

        if index is not None:
            setup_ui_after_index_built(editor, index)

        editor.web.eval("onResize()")

        if index is None or not index.tagSelect:
            fillDeckSelect(editor)
            if get_index() is None or (index is not None and index.lastSearch is None):
                printStartingInfo(editor)
        if not corpus_is_loaded():
            if index is not None and index.logging:
                log("loading notes from anki db...")
            corpus = get_notes_in_collection()
            set_corpus(corpus)
            if index is not None and index.logging:
                log("loaded notes: len(corpus): " + str(len(corpus)))

        if index is not None and index.output is not None:
            index.output.editor = editor
            index.output._loadPlotJsIfNotLoaded()
    if get_edit() is None and editor is not None:
        set_edit(editor)


def editorContextMenuEventWrapper(view, evt):
    global contextEvt
    win = aqt.mw.app.activeWindow()
    if isinstance(win, Browser):
        origEditorContextMenuEvt(view, evt)
        return
    contextEvt = evt
    pos = evt.pos()
    determineClickTarget(pos)
    #origEditorContextMenuEvt(view, evt)

def insert_scripts():
    addon_id = utility.misc.get_addon_id()
    mw.addonManager.setWebExports(addon_id, ".*\\.(js|css|map|png)$")
    port = mw.mediaServer.getPort()
    aqt.editor._html += f"""
    <script>
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/tinymce/tinymce.min.js';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdfjs/pdf.min.js';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdf-reader.js';
        document.body.appendChild(script);
    </script>
    """

@requires_index_loaded
def determineClickTarget(pos):
    get_index().output.editor.web.page().runJavaScript("sendClickedInformation(%s, %s)" % (pos.x(), pos.y()), addOptionsToContextMenu)


def addOptionsToContextMenu(clickInfo):
    index = get_index()

    if clickInfo is not None and clickInfo.startswith("img "):
        try:
            src = clickInfo[4:]
            m = QMenu(index.output.editor.web)
            a = m.addAction("Open Image in Browser")
            a.triggered.connect(lambda: openImgInBrowser(src))
            cpSubMenu = m.addMenu("Copy Image To Field...")
            for key in index.output.editor.note.keys():
                cpSubMenu.addAction("Append to %s" % key).triggered.connect(functools.partial(appendImgToField, src, key))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(index.output.editor.web, contextEvt)
    elif clickInfo is not None and clickInfo.startswith("note "):
        try:
            content = " ".join(clickInfo.split()[2:])
            nid = int(clickInfo.split()[1])
            m = QMenu(index.output.editor.web)
            a = m.addAction("Find Notes Added On The Same Day")
            a.triggered.connect(lambda: getCreatedSameDay(index, index.output.editor, nid))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(index.output.editor.web, contextEvt)

    # elif clickInfo is not None and clickInfo.startswith("span "):
    #     content = clickInfo.split()[1]

    else:
        origEditorContextMenuEvt(index.output.editor.web, contextEvt)


def setup_hooks():
    add_hook("user-note-created", reload_note_sidebar)
    add_hook("user-note-deleted", reload_note_sidebar)
    add_hook("user-note-edited", reload_note_sidebar)
    add_hook("user-note-edited", reload_note_reading_modal_bottom_bar)

def openImgInBrowser(url):
    if len(url) > 0:
        webbrowser.open(url)

def appendNoteToField(content, key):
    if not check_index():
        return
    index = get_index()
    note = index.output.editor.note
    note.fields[note._fieldOrd(key)] += content
    note.flush()
    index.output.editor.loadNote()

def appendImgToField(src, key):
    if src is None or len(src) == 0:
        return
    index = get_index()
    note = index.output.editor.note
    src = re.sub("https?://[0-9.]+:\\d+/", "", src)
    note.fields[note._fieldOrd(key)] += "<img src='%s'/>" % src
    note.flush()
    index.output.editor.loadNote()

def setup_tagedit_timer():
    global tagEditTimer
    tagEditTimer = QTimer()
    tagEditTimer.setSingleShot(True) 

def tag_edit_keypress(self, evt):
    """
    Used if "search on tag entry" is enabled.
    Triggers a search if the user has stopped typing in the tag field.
    """
    orig_tag_keypress(self, evt)
    win = aqt.mw.app.activeWindow()
    # dont trigger keypress in edit dialogs opened within the add dialog
    if isinstance(win, EditDialog) or isinstance(win, Browser):
        return
    index = get_index()

    if index is not None and len(self.text().strip()) > 0:
        text = self.text()
        try:
            tagEditTimer.timeout.disconnect()
        except Exception: pass
        tagEditTimer.timeout.connect(lambda: rerender_info(index.output.editor, text, searchByTags = True)) 
        tagEditTimer.start(1000)

init_addon()
