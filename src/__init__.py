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
from anki.utils import isMac, isLin
import aqt.webview
from aqt.addcards import AddCards
from anki.notes import Note
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
import typing
from typing import Dict, Any, List, Tuple, Optional, Callable
import sys
sys.path.insert(0, os.path.dirname(__file__))

import utility.tags
import utility.misc
import state

from .state import check_index, get_index, corpus_is_loaded, set_corpus, set_edit, get_edit
from .index.indexing import build_index, get_notes_in_collection
from .debug_logging import log
from .web.web import *
from .web.html import right_side_html
from .notes import *
from .hooks import add_hook
from .dialogs.editor import EditDialog, NoteEditor
from .dialogs.quick_open_pdf import QuickOpenPDF
from .internals import requires_index_loaded
from .config import get_config_value_or_default as conf_or_def
from .command_parsing import expanded_on_bridge_cmd, toggleAddon, rerenderNote, rerender_info, add_note_to_index, try_repeat_last_search, search_by_tags

config = mw.addonManager.getConfig(__name__)

def init_addon():
    """ Executed once on Anki startup. """
    global origEditorContextMenuEvt

    gui_hooks.webview_did_receive_js_message.append(expanded_on_bridge_cmd)
    
    #todo: Find out if there is a better moment to start index creation
    state.db_file_existed = create_db_file_if_not_exists()

    gui_hooks.profile_did_open.append(build_index)
    gui_hooks.profile_did_open.append(insert_scripts)
    gui_hooks.profile_did_open.append(lambda : recalculate_priority_queue(True))

    if conf_or_def("searchOnTagEntry", True):
        TagEdit.keyPressEvent = wrap(TagEdit.keyPressEvent, tag_edit_keypress, "around")

    setup_tagedit_timer()

    # add new notes to search index when adding
    gui_hooks.add_cards_did_add_note.append(add_note_to_index)
    gui_hooks.add_cards_did_add_note.append(save_pdf_page)

    # update notes in index when changed through the "Edit" button
    EditDialog.saveAndClose = wrap(EditDialog.saveAndClose, editor_save_with_index_update, "around")

    # register add-on's shortcuts 
    gui_hooks.editor_did_init_shortcuts.append(register_shortcuts) 
    # reset state after the add/edit dialog is opened
    gui_hooks.editor_did_init_shortcuts.append(reset_state) 

    # activate nighmode if Anki's nightmode is active
    gui_hooks.editor_did_init_shortcuts.append(activate_nightmode) 

    # set zoom factor according to config
    gui_hooks.editor_did_init_shortcuts.append(set_zoom) 

    # add-on internal hooks
    setup_hooks()

    # add shortcuts
    aqt.editor._html += """
    <script>
            document.addEventListener("keydown", function (e) {globalKeydown(e); }, false);
    </script>"""
    
    #this inserts all the javascript functions in scripts.js into the editor webview
    aqt.editor._html += getScriptPlatformSpecific()

    # patch webview dropevent to catch pdf file drop
    aqt.editor.EditorWebView.dropEvent =  wrap(aqt.editor.EditorWebView.dropEvent, webview_on_drop, "around")

    #when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    gui_hooks.editor_did_load_note.append(on_load_note)

def webview_on_drop(web: aqt.editor.EditorWebView, evt: QDropEvent, _old: Callable):
    """ If a pdf file is dropped, intercept and open Create Note dialog. """

    if evt:
        mime = evt.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                url = url.toLocalFile()
                if re.match("^.+\.pdf$", url, re.IGNORECASE):
                    editor = get_index().ui._editor
                    # editor.web.eval("dropTarget = document.getElementById('f0');")
                    # _old(web, evt)
                    expanded_on_bridge_cmd(None, f"siac-create-note-source-prefill {url}", editor)
                    return
    _old(web, evt)

def editor_save_with_index_update(dialog: EditDialog, _old: Callable):
    _old(dialog)
    # update index
    index = get_index()
    if index is not None and dialog.editor is not None and dialog.editor.note is not None:
        index.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        index.ui.edited[str(dialog.editor.note.id)] = t.time()

        if index.ui.reading_modal.note_id is not None:
            index.ui.js("updatePageSidebarIfShown()")


def on_load_note(editor: Editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    There are better hooks (i.e. ones that do not get executed on every note loading, but only once on the webview init instead),
    but for backwards compatibility, this hook is still used instead.
    """
    #only display in add cards dialog or in the review edit dialog (if enabled)
    if editor.addMode or (conf_or_def("useInEdit", False) and isinstance(editor.parentWindow, EditCurrent)):

        index                   = get_index()
        zoom                    = conf_or_def("searchpane.zoom", 1.0)
        typing_delay            = max(500, conf_or_def('delayWhileTyping', 1000))
        show_tag_info_on_hover  = "true" if conf_or_def("showTagInfoOnHover", True) and conf_or_def("noteScale", 1.0) == 1.0 and zoom == 1.0 else "false"
        pdf_color_mode          = conf_or_def("pdf.color_mode", "Day")

        pdf_highlights_render   = "siac-pdf-hl-alt-render" if conf_or_def("pdf.highlights.use_alt_render", False) else ""

        editor.web.eval(f"""
            var showTagInfoOnHover  = {show_tag_info_on_hover}; 
            tagHoverTimeout         = {conf_or_def("tagHoverDelayInMiliSec", 1000)};
            var delayWhileTyping    = {typing_delay};
            pdfColorMode            = "{pdf_color_mode}";

            if ('{pdf_highlights_render}') {{
                document.body.classList.add("{pdf_highlights_render}");
            }}
        """)

        def cb(was_already_rendered):
            if was_already_rendered:
                return

            if index is not None and index.ui is not None:
                index.ui.set_editor(editor)

            if index is not None:
                setup_ui_after_index_built(editor, index)

            # editor.web.eval("onWindowResize()")

            fillDeckSelect(editor)
            if index is not None and index.lastSearch is None:
                print_starting_info(editor)
            if not corpus_is_loaded():
                corpus = get_notes_in_collection()
                set_corpus(corpus)

        # render the right side (search area) of the editor
        # (the script checks if it has been rendered already)
        editor.web.evalWithCallback(right_side_html(index is not None), cb)
      

    if get_edit() is None and editor is not None:
        set_edit(editor)

def on_add_cards_init(add_cards: AddCards):

    if get_index() is not None and add_cards.editor is not None:
        get_index().ui.set_editor(add_cards.editor)
        
def save_pdf_page(note: Note):

    ix = get_index()
    if ix.ui.reading_modal.note_id is None:
        return

    nid = ix.ui.reading_modal.note_id 
    def cb(page: int):
        if page >= 0:
            link_note_and_page(nid, note.id, page)
            # update sidebar if shown
            ix.ui.js("updatePageSidebarIfShown()")
    
    ix.ui.reading_modal.page_displayed(cb)


def insert_scripts():
    """
        Expose the scripts on the internal web server.
        'styles.css' not included that way, because it 
        is processed ($<config value>$ placeholders are replaced) and inserted via <style> tags.
    """

    addon_id    = utility.misc.get_addon_id()
    pdf_theme   = conf_or_def("pdf.theme", "pdf_reader.css")
    port        = mw.mediaServer.getPort()

    mw.addonManager.setWebExports(addon_id, ".*\\.(js|css|map|png|svg|ttf|woff2?)$")
    aqt.editor._html += f"""
    <script>

        var script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/dist/styles.min.css';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/dist/siac.min.js';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/fa/css/font-awesome.min.css';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/simple_mde/simplemde.min.js';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/simple_mde/simplemde.min.css';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdfjs/pdf.min.js';
        document.body.appendChild(script);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/plot.js';
        document.body.appendChild(script);

        setTimeout(function() {{
            script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/plot.resize.js';
            document.body.appendChild(script);

            script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/cal-heatmap.min.js';
            document.body.appendChild(script);
        }}, 200);

        script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/d3.min.js';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/cal-heatmap.css';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/pdfjs/textlayer.css';
        document.body.appendChild(script);

        script = document.createElement('link');
        script.type = 'text/css';
        script.id ='siac-pdf-css';
        script.rel = 'stylesheet';
        script.href = 'http://127.0.0.1:{port}/_addons/{addon_id}/web/{pdf_theme}';
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

def setup_hooks():
    """ Todo: move more add-on code to hooks. """

    add_hook("user-note-created", lambda: get_index().ui.sidebar.refresh_tab(1))
    add_hook("user-note-created", lambda: try_repeat_last_search())

    add_hook("user-note-deleted", lambda: get_index().ui.sidebar.refresh_tab(1))
    add_hook("user-note-deleted", lambda: recalculate_priority_queue())
    add_hook("user-note-deleted", lambda: try_repeat_last_search())

    add_hook("user-note-edited", lambda: get_index().ui.sidebar.refresh_tab(1))
    add_hook("user-note-edited", lambda: get_index().ui.reading_modal.reload_bottom_bar())
    add_hook("user-note-edited", lambda: try_repeat_last_search())

    add_hook("updated-schedule", lambda: recalculate_priority_queue())
    add_hook("updated-schedule", lambda: get_index().ui.reading_modal.reload_bottom_bar())

    add_hook("reading-modal-closed", lambda: get_index().ui.sidebar.refresh_tab(1))
    add_hook("reading-modal-closed", lambda: try_repeat_last_search())


def reset_state(shortcuts: List[Tuple], editor: Editor):
    """ After the Add Card / Edit Current dialog is opened, some state variables need to be reset. """
    
    # might still be true if Create Note dialog was closed by closing its parent window, so reset it
    state.note_editor_shown = False

    def cb(night_mode: bool):
        state.night_mode = night_mode

    editor.web.evalWithCallback("(() => {  return document.body.classList.contains('nightMode'); })();", cb)


def set_zoom(shortcuts: List[Tuple], editor: Editor):
    """ After the Add Card / Edit Current dialog is opened, set the zoom according to 'searchpane.zoom'. """
    
    win = editor.parentWindow
    if not win or isinstance(win, Browser): 
        return
    if not isinstance(win, AddCards) and not get_config_value_or_default("useInEdit", False):
        return
    zoom = get_config_value_or_default("searchpane.zoom", 1.0)
    if zoom != 1.0:
        editor.web.setZoomFactor(zoom)


def register_shortcuts(shortcuts: List[Tuple], editor: Editor):
    """ Register shortcuts used by the add-on. """

    def _try_register(shortcut: str, activated: Callable):
        try:
            QShortcut(QKeySequence(shortcut), editor.widget, activated=activated)
        except: 
            state.shortcuts_failed.append(shortcut)
            return
        existing = editor.widget.findChildren(QShortcut)
        existing = [e.key().toString().lower() for e in existing]
        if not shortcut.lower() in existing:
            state.shortcuts_failed.append(shortcut)


    # toggle add-on pane 
    _try_register(config["toggleShortcut"], toggleAddon)

    # quick open dialog
    _try_register("Ctrl+o", show_quick_open_pdf)

    # open Create/Update note modal
    _try_register(config["notes.editor.shortcut"], show_note_modal)

    # toggle search on select in pdf reader
    _try_register(config["pdf.shortcuts.toggle_search_on_select"], lambda: editor.web.eval("togglePDFSelect()"))

    # toggle page read in pdf reader
    _try_register(config["pdf.shortcuts.toggle_page_read"], lambda: editor.web.eval("togglePageRead()"))

    # 'Done' in reading modal
    _try_register(config["pdf.shortcuts.done"], lambda: editor.web.eval("doneShortcut()"))

    # 'Later' in reading modal
    _try_register(config["pdf.shortcuts.later"], lambda: editor.web.eval("laterShortcut()"))

    # Jump to first/last page in pdf reader 
    _try_register(config["pdf.shortcuts.jump_to_last_page"], lambda: editor.web.eval("jumpLastPageShortcut()"))
    _try_register(config["pdf.shortcuts.jump_to_first_page"], lambda: editor.web.eval("jumpFirstPageShortcut()"))

    _try_register(config["shortcuts.focus_search_bar"], lambda: editor.web.eval("focusSearchShortcut()"))
    _try_register(config["shortcuts.trigger_search"], lambda: editor.web.eval("triggerSearchShortcut()"))
    _try_register(config["shortcuts.trigger_predef_search"], lambda: editor.web.eval("predefSearch()"))
    _try_register(config["shortcuts.trigger_current_filter"], lambda: editor.web.eval("sort()"))
    _try_register(config["shortcuts.search_for_current_field"], lambda: editor.web.eval("searchCurrentField()"))

def show_note_modal():
    if not state.note_editor_shown:
        ix              = get_index()
        read_note_id    = ix.ui.reading_modal.note_id
        NoteEditor(ix.ui._editor.parentWindow, note_id=None, add_only=False, read_note_id=read_note_id)

def show_quick_open_pdf():
    """ Ctrl + O pressed -> show small dialog to quickly open a PDF. """

    ix      = get_index()
    dialog  = QuickOpenPDF(ix.ui._editor.parentWindow)

    if dialog.exec_():
        if dialog.chosen_id is not None and dialog.chosen_id > 0:
            def cb(can_load):
                if can_load:
                    ix.ui.reading_modal.display(dialog.chosen_id)
            ix.ui.js_with_cb("beforeNoteQuickOpen();", cb)

def setup_tagedit_timer():
    global tagEditTimer
    tagEditTimer = QTimer()
    tagEditTimer.setSingleShot(True) 

def tag_edit_keypress(self, evt, _old):
    """
    Used if "Search on Tag Entry" is enabled.
    Triggers a search if the user has stopped typing in the tag field.
    """
    _old(self, evt)
    win = aqt.mw.app.activeWindow()
    # dont trigger keypress in edit dialogs opened within the add dialog
    if isinstance(win, EditDialog) or isinstance(win, Browser):
        return
    modifiers = evt.modifiers()
    if modifiers == Qt.ControlModifier or modifiers == Qt.AltModifier or modifiers == Qt.MetaModifier:
        return
    index = get_index()

    if index is not None and len(self.text().strip()) > 0:
        text = self.text()
        try:
            tagEditTimer.timeout.disconnect()
        except Exception: pass
        tagEditTimer.timeout.connect(lambda: search_by_tags(text)) 
        tagEditTimer.start(1000)

init_addon()
