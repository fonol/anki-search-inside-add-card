#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from aqt import mw, gui_hooks
from aqt.qt import *
from anki.hooks import wrap, addHook
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

from .state import check_index, get_index, corpus_is_loaded, set_corpus, set_edit, get_edit
from .index.indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import *
from .web.html import right_side_html
from .notes import *
from .hooks import add_hook
from .dialogs.editor import EditDialog
from .dialogs.quick_open_pdf import QuickOpenPDF
from .internals import requires_index_loaded
from .config import get_config_value_or_default
from .command_parsing import expanded_on_bridge_cmd, toggleAddon, rerenderNote, rerender_info, add_note_to_index




config = mw.addonManager.getConfig(__name__)

def init_addon():
    global origEditorContextMenuEvt

    # wrap js -> py bridge to include the add-ons commands, see command_parsing.py
    Editor.onBridgeCmd = wrap(Editor.onBridgeCmd, expanded_on_bridge_cmd, "around")
    #todo: Find out if there is a better moment to start index creation
    
    create_db_file_if_not_exists()

    gui_hooks.profile_did_open.append(build_index)
    gui_hooks.profile_did_open.append(insert_scripts)
    gui_hooks.profile_did_open.append(recalculate_priority_queue)
    #disabled for now, to be able to use Occlude Image in the context menu
    #origEditorContextMenuEvt = EditorWebView.contextMenuEvent
    #EditorWebView.contextMenuEvent = editorContextMenuEventWrapper

    if get_config_value_or_default("searchOnTagEntry", True):
        TagEdit.keyPressEvent = wrap(TagEdit.keyPressEvent, tag_edit_keypress, "around")

    setup_tagedit_timer()

    # add new notes to search index when adding
    AddCards.addNote = wrap(AddCards.addNote, add_note_and_update_index, "around")
    # update notes in index when changed through the "Edit" button
    EditDialog.saveAndClose = wrap(EditDialog.saveAndClose, editor_save_with_index_update, "around")

    # shortcut to toggle add-on pane 
    gui_hooks.editor_did_init_shortcuts.append(add_hide_show_shortcut) 

    # add-on internal hooks
    setup_hooks()

    # add shortcuts
    aqt.editor._html += """
    <script>
            document.addEventListener("keydown", function (e) {globalKeydown(e); }, false);
    </script>"""
    
    typing_delay = max(500, config['delayWhileTyping'])
    #this inserts all the javascript functions in scripts.js into the editor webview
    aqt.editor._html += getScriptPlatformSpecific(typing_delay)
    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    gui_hooks.editor_did_load_note.append(on_load_note)




def add_note_and_update_index(dialog, note, _old):
    """
        Wrapper around the note adding method, to update the index with the new created note.
    """
    res = _old(dialog, note)
    add_note_to_index(note)
    return res

def editor_save_with_index_update(dialog, _old):
    _old(dialog)
    # update index
    index = get_index()
    if index is not None and dialog.editor is not None and dialog.editor.note is not None:
        index.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        index.ui.edited[str(dialog.editor.note.id)] = t.time()


def on_load_note(editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    """

    #only display in add cards dialog or in the review edit dialog (if enabled)
    if editor.addMode or (get_config_value_or_default("useInEdit", False) and isinstance(editor.parentWindow, EditCurrent)):
        index = get_index()

        zoom = get_config_value_or_default("searchpane.zoom", 1.0)
        show_tag_info_on_hover = "true" if get_config_value_or_default("showTagInfoOnHover", True) and get_config_value_or_default("noteScale", 1.0) == 1.0 and zoom == 1.0 else "false"
        editor.web.eval(f"""
            var showTagInfoOnHover = {show_tag_info_on_hover}; 
            tagHoverTimeout = {get_config_value_or_default("tagHoverDelayInMiliSec", 1000)};
        """)

        def cb(was_already_rendered):
            if was_already_rendered:
                return
            if index is not None:
                setup_ui_after_index_built(editor, index)

            # editor.web.eval("onWindowResize()")

            fillDeckSelect(editor)
            if index is not None and index.lastSearch is None:
                printStartingInfo(editor)
            if not corpus_is_loaded():
                corpus = get_notes_in_collection()
                set_corpus(corpus)

            if index is not None and index.ui is not None:
                index.ui.set_editor(editor)
                index.ui._loadPlotJsIfNotLoaded()


        # render the right side (search area) of the editor
        # (the script checks if it has been rendered already)
        editor.web.evalWithCallback(right_side_html(index is not None), cb)
        
      

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
    """
        Expose the scripts on the internal web server.
        styles.css and pdf_reader.css are not included that way, because they 
        are processed ($<config value>$ placeholders are replaced) and inserted via <style> tags.
    """
    addon_id = utility.misc.get_addon_id()
    mw.addonManager.setWebExports(addon_id, ".*\\.(js|css|map|png|ttf)$")
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
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdf_reader.js';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdfjs/textlayer.css';
        document.body.appendChild(script);

        var css = `@font-face {{
                        font-family: "Open Sans";
                        src: url("http://127.0.0.1:{port}/_addons/{addon_id}/web/font/OpenSans-Regular.ttf");
                        font-weight: normal;
                        font-style: normal;
                    }}
                    @font-face {{
                        font-family: "Open Sans";
                        src: url("http://127.0.0.1:{port}/_addons/{addon_id}/web/font/OpenSans-Bold.ttf");
                        font-weight: bold;
                        font-style: normal;
                    }}
                    @font-face {{
                        font-family: "Open Sans";
                        src: url("http://127.0.0.1:{port}/_addons/{addon_id}/web/font/OpenSans-Italic.ttf");
                        font-weight: normal;
                        font-style: italic;
                    }}`;
        var font_style = document.createElement('style');
        document.head.appendChild(font_style);
        font_style.type = 'text/css';
        font_style.appendChild(document.createTextNode(css));

    </script>
    """

@requires_index_loaded
def determineClickTarget(pos):
    get_index().ui._editor.web.page().runJavaScript("sendClickedInformation(%s, %s)" % (pos.x(), pos.y()), addOptionsToContextMenu)


def addOptionsToContextMenu(clickInfo):
    index = get_index()

    if clickInfo is not None and clickInfo.startswith("img "):
        try:
            src = clickInfo[4:]
            m = QMenu(index.ui._editor.web)
            a = m.addAction("Open Image in Browser")
            a.triggered.connect(lambda: openImgInBrowser(src))
            cpSubMenu = m.addMenu("Copy Image To Field...")
            for key in index.ui._editor.note.keys():
                cpSubMenu.addAction("Append to %s" % key).triggered.connect(functools.partial(appendImgToField, src, key))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(index.ui._editor.web, contextEvt)
    elif clickInfo is not None and clickInfo.startswith("note "):
        try:
            content = " ".join(clickInfo.split()[2:])
            nid = int(clickInfo.split()[1])
            m = QMenu(index.ui._editor.web)
            a = m.addAction("Find Notes Added On The Same Day")
            a.triggered.connect(lambda: getCreatedSameDay(index, index.ui._editor, nid))
            m.popup(QCursor.pos())
        except:
            origEditorContextMenuEvt(index.ui._editor.web, contextEvt)

    # elif clickInfo is not None and clickInfo.startswith("span "):
    #     content = clickInfo.split()[1]

    else:
        origEditorContextMenuEvt(index.ui._editor.web, contextEvt)


def setup_hooks():
    add_hook("user-note-created", reload_note_sidebar)
    add_hook("user-note-deleted", reload_note_sidebar)
    add_hook("user-note-edited", reload_note_sidebar)
    add_hook("user-note-edited", lambda: get_index().ui.reading_modal.reload_bottom_bar())


def add_hide_show_shortcut(shortcuts, editor):
    if not "toggleShortcut" in config:
        return
    QShortcut(QKeySequence(config["toggleShortcut"]), editor.widget, activated=toggleAddon)
    QShortcut(QKeySequence("Ctrl+o"), editor.widget, activated=show_quick_open_pdf)

def openImgInBrowser(url):
    if len(url) > 0:
        webbrowser.open(url)

def show_quick_open_pdf():
    ix = get_index()
    dialog = QuickOpenPDF(ix.ui._editor.parentWindow)
    if dialog.exec_():
        if dialog.chosen_id is not None and dialog.chosen_id > 0:
            def cb(can_load):
                if can_load:
                    ix.ui.reading_modal.display(dialog.chosen_id)
            ix.ui.js_with_cb("beforeNoteQuickOpen();", cb)

def appendNoteToField(content, key):
    if not check_index():
        return
    index = get_index()
    note = index.ui._editor.note
    note.fields[note._fieldOrd(key)] += content
    note.flush()
    index.ui._editor.loadNote()

def appendImgToField(src, key):
    if src is None or len(src) == 0:
        return
    index = get_index()
    note = index.ui._editor.note
    src = re.sub("https?://[0-9.]+:\\d+/", "", src)
    note.fields[note._fieldOrd(key)] += "<img src='%s'/>" % src
    note.flush()
    index.ui._editor.loadNote()

def setup_tagedit_timer():
    global tagEditTimer
    tagEditTimer = QTimer()
    tagEditTimer.setSingleShot(True) 

def tag_edit_keypress(self, evt, _old):
    """
    Used if "search on tag entry" is enabled.
    Triggers a search if the user has stopped typing in the tag field.
    """
    _old(self, evt)
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
        tagEditTimer.timeout.connect(lambda: rerender_info(index.ui._editor, text, searchByTags = True)) 
        tagEditTimer.start(1000)

init_addon()
