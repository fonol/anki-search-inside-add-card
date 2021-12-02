#!/usr/bin/env python
# -*- coding: utf-8 -*-

# anki-search-inside-add-card
# Copyright (C) 2019 - 2021 Tom Z.

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
import json
import re
import time as t
import functools
import typing
from typing import Dict, Any, List, Tuple, Optional, Callable
import sys

sys.path.insert(0, os.path.dirname(__file__))

import utility.tags
import utility.misc
import state

from .state import get_index, set_edit, get_edit
from .index.indexing import build_index
from .web.web import *
from .web.html import right_side_html
from .notes import *
from .hooks import add_hook
from .review_interrupt import review_interruptor
from .dialogs.editor import EditDialog, NoteEditor
from .config import get_config_value_or_default as conf_or_def, get_config_value
from .command_parsing import expanded_on_bridge_cmd, toggleAddon, rerenderNote, add_note_to_index, try_repeat_last_search
from .cmds.cmds_search import search_by_tags
from .menubar import Menu
from .web.reading_modal import Reader
from .output import UI



config = mw.addonManager.getConfig(__name__)

def init_addon():
    """ Executed once on Anki startup. """
    global origEditorContextMenuEvt

    if config["dev_mode"]:
        state.dev_mode = True

    if hasattr(mw.pm, "night_mode"):
        state.set_nightmode(mw.pm.night_mode())

    gui_hooks.reviewer_did_answer_card.append(on_reviewer_did_answer)

    gui_hooks.webview_did_receive_js_message.append(expanded_on_bridge_cmd)

    #todo: Find out if there is a better moment to start index creation
    if not create_db_file_if_not_exists():
        print("[SIAC] Notes DB file did not exist, created a new one.")

    # state.window_mode = state.WindowMode[config["window_mode"]]

    gui_hooks.profile_did_open.append(build_index)
    # gui_hooks.profile_did_open.append(insert_scripts)
    gui_hooks.profile_did_open.append(lambda : recalculate_priority_queue(True))

    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)

    if conf_or_def("searchOnTagEntry", True):
        TagEdit.keyPressEvent = wrap(TagEdit.keyPressEvent, tag_edit_keypress, "around")

    setup_tagedit_timer()

    # add new notes to search index when adding
    gui_hooks.add_cards_did_add_note.append(add_note_to_index)
    # save that a note has been created while on a certain pdf page
    gui_hooks.add_cards_did_add_note.append(save_pdf_page)

    # update notes in index when changed through the "Edit" button
    EditDialog.saveAndClose = wrap(EditDialog.saveAndClose, editor_save_with_index_update, "around")

    # register add-on's shortcuts
    gui_hooks.editor_did_init_shortcuts.append(register_shortcuts)
    # reset state after the add/edit dialog is opened
    gui_hooks.editor_did_init_shortcuts.append(reset_state)

    gui_hooks.editor_did_load_note.append(setup_switch_btn)

    # activate nighmode if Anki's nightmode is active
    gui_hooks.editor_did_init_shortcuts.append(activate_nightmode)

    # set zoom factor according to config
    gui_hooks.editor_did_init_shortcuts.append(set_zoom)

    # add-on internal hooks
    setup_hooks()

    # patch webview dropevent to catch pdf file drop
    aqt.editor.EditorWebView.dropEvent =  wrap(aqt.editor.EditorWebView.dropEvent, webview_on_drop, "around")

    # when a note is loaded (i.e. the add cards dialog is opened), we have to insert our html for the search ui
    gui_hooks.editor_did_load_note.append(on_load_note)

    # IO add note wrapping
    if mw.addonManager.isEnabled("1374772155"):
        try:
            register_io_add_hook()
        except:
            pass
    
    # reviewer hook to show linked SIAC notes 
    gui_hooks.reviewer_did_show_answer.append(on_reviewer_did_show_answer)
    gui_hooks.reviewer_did_show_question.append(on_reviewer_did_show_question)


def webview_on_drop(web: aqt.editor.EditorWebView, evt: QDropEvent, _old: Callable):
    """ If a pdf file is dropped, intercept and open Create Note dialog. """

    if evt:
        mime = evt.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                url = url.toLocalFile()
                if re.match("^.+\.pdf$", url, re.IGNORECASE):
                    editor = UI._editor
                    # editor.web.eval("dropTarget = document.getElementById('f0');")
                    # _old(web, evt)
                    expanded_on_bridge_cmd(None, f"siac-create-note-source-prefill {url}", editor)
                    return
    _old(web, evt)


def on_reviewer_did_answer(reviewer, card, ease):

    # hide link modal if existent
    reviewer.web.eval("if (document.getElementById('siac-link-modal')) { $('#siac-link-modal').remove(); }")

    # check if we want to do review interruption
    if not get_config_value_or_default("mix_reviews_and_reading", False) or state.rr_mix_disabled:
        return

    review_interruptor()

def on_webview_will_set_content(web_content: Any, context):
                
    if not isinstance(context, aqt.editor.Editor):
        return

    if not can_run_in_editor_context(context):
        return
    
    print("[SIAC] on_webview_will_set_content()")

    web_content.head += get_styles()
    web_content.body += insert_scripts()
 
def on_reviewer_did_show_question(card):
    win = aqt.mw.app.activeWindow()
    if win is not None and hasattr(win, "web"):
        win.web.eval("if (document.getElementById('siac-link-modal')) { $('#siac-link-modal').remove(); }")

def on_reviewer_did_show_answer(card):
    note = get_linked_addon_note(card.nid)
    if note is not None:
        win = aqt.mw.app.activeWindow()
        if hasattr(win, "web"):
            display_note_linking(win.web, note)

def editor_save_with_index_update(dialog: EditDialog, _old: Callable):
    """ Used in the edit dialog for Anki notes to update the index on saving an edited note. """

    _old(dialog)
    # update index
    index = get_index()
    if index is not None and dialog.editor is not None and dialog.editor.note is not None:
        index.updateNote(dialog.editor.note)
        # note should be rerendered
        rerenderNote(dialog.editor.note.id)
         # keep track of edited notes (to display a little remark in the results)
        UI.edited[str(dialog.editor.note.id)] = t.time()

        if Reader.note_id is not None:
            UI.js("updatePageSidebarIfShown()")


def on_load_note(editor: Editor):
    """
    Executed everytime a note is created/loaded in the add cards dialog.
    Wraps the normal editor html in a flex layout to render a second column for the searching ui.
    There are better hooks (i.e. ones that do not get executed on every note loading, but only once on the webview init instead),
    but for backwards compatibility, this hook is still used instead.
    """
    #only display in add cards dialog or in the review edit dialog (if enabled)
    if can_run_in_editor_context(editor):

        index                   = get_index()
        zoom                    = conf_or_def("searchpane.zoom", 1.0)
        typing_delay            = max(500, conf_or_def('delayWhileTyping', 1000))
        show_tag_info_on_hover  = "true" if conf_or_def("showTagInfoOnHover", True) and conf_or_def("noteScale", 1.0) == 1.0 and zoom == 1.0 else "false"
        pdf_color_mode          = conf_or_def("pdf.color_mode", "Day")
        pdf_highlights_render   = "siac-pdf-hl-alt-render" if conf_or_def("pdf.highlights.use_alt_render", False) else ""
        window_mode             = state.WindowMode[conf_or_def("window_mode", "Both")]

        editor.web.eval(f"""
            var onloadNoteInit = () => {{
                if (typeof(SIAC) === 'undefined') {{
                    setTimeout(onloadNoteInit, 50);
                    return;
                }}

                SIAC.State.showTagInfoOnHover   = {show_tag_info_on_hover};
                SIAC.State.tagHoverTimeout      = {conf_or_def("tagHoverDelayInMiliSec", 1000)};
                SIAC.State.typingDelay          = {typing_delay};
                SIAC.Colors.pdfColorMode        = "{pdf_color_mode}";
                SIAC.State.noteId               = {editor.note.id};

                SIAC.Fields.cacheFields();
                document.addEventListener('mouseup', onTextSelectionChange);
                onTextSelectionChange();

                setWindowMode('{window_mode.name}');
            }};
            onloadNoteInit();


            if ('{pdf_highlights_render}') {{
                document.body.classList.add("{pdf_highlights_render}");
            }}
        """)

        def cb(was_already_rendered):
            if was_already_rendered:
                return

            UI.set_editor(editor)
            Reader.reset()
            Reader.set_editor(editor)

            # https://github.com/fonol/anki-search-inside-add-card/issues/268
            editor.web.eval(f"setFonts({json.dumps(editor.fonts())})")

            if index is not None:
                UI.setup_ui_after_index_built(editor, index)

            # editor.web.eval("onWindowResize()")

            UI.fillDeckSelect(editor)
            if index is not None and index.lastSearch is None:
                UI.print_starting_info()

        # render the right side (search area) of the editor
        # (the script checks if it has been rendered already)
        editor.web.evalWithCallback(right_side_html(index is not None), cb)
        print("on_load_note > right_side_html()")


    if get_edit() is None and editor is not None:
        set_edit(editor)


def save_pdf_page(note: Note):

    if Reader.note_id is None:
        return

    nid = Reader.note_id
    def cb(page: int):
        link_note_and_page(nid, note.id, page)
        # update sidebar if shown
        UI.js("updatePageSidebarIfShown()")

    Reader.page_displayed(cb)


def insert_scripts():
    """
        Expose the scripts on the internal web server.
        'styles.css' not included that way, because it
        is processed ($<config value>$ placeholders are replaced) and inserted via <style> tags.
    """

    addon_id    = utility.misc.get_addon_id()
    port        = mw.mediaServer.getPort()

    # compatibility with newest pdf.js version needs more testing, until then, use old one
    chromium_v  = utility.misc.chromium_version()
    # pdfjs_v     = "2.6.347" if chromium_v  > "76" else "2.4.456"
    pdfjs_v     = "2.4.456"

    mw.addonManager.setWebExports(addon_id, ".*\\.(js|css|map|png|svg|ttf|woff2?|bcmap)$")

    def css(path: str) -> str:
        return f"""
            (() => {{
                let script = document.createElement('link');
                script.type = 'text/css';
                script.rel = 'stylesheet';
                script.href = 'http://127.0.0.1:{port}/{path}';
                document.body.appendChild(script);
            }})();"""

    def js(path: str, timeout: int = 0) -> str:
        if timeout > 0:
            return f"""
                setTimeout(function () {{
                    let script = document.createElement('script');
                    script.type = 'text/javascript';
                    script.src = 'http://127.0.0.1:{port}/{path}';
                    document.body.appendChild(script);
                }}, {timeout});

            """
        return f"""
            (() => {{
                let script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = 'http://127.0.0.1:{port}/{path}';
                document.body.appendChild(script);
            }})();"""
    
    js_css = css(f"_addons/{addon_id}/web/dist/styles.min.css")
    js_css += js(f"_addons/{addon_id}/web/dist/siac.min.js")
    js_css += js(f"_addons/{addon_id}/web/jquery.min.js")
    js_css += css(f"_addons/{addon_id}/web/fa/css/font-awesome.min.css")
    js_css += js(f"_addons/{addon_id}/web/simple_mde/simplemde.min.js")
    js_css += css(f"_addons/{addon_id}/web/simple_mde/simplemde.min.css")
    js_css += js(f"_addons/{addon_id}/web/pdfjs/{pdfjs_v}/pdf.js")
    js_css += js(f"_addons/{addon_id}/web/plot.js")
    js_css += js(f"_addons/{addon_id}/web/d3.min.js")
    js_css += css(f"_addons/{addon_id}/web/cal-heatmap.css")
    js_css += css(f"_addons/{addon_id}/web/pdfjs/textlayer.css")
    js_css += css(f"_addons/{addon_id}/web/pdf_reader.css")
    js_css += js(f"_anki/js/vendor/mathjax/tex-chtml.js", timeout=400)
    # js_css += js(f"_addons/{addon_id}/web/dist/vuejs/js/main.js")
    # js_css += css(f"_addons/{addon_id}/web/dist/vuejs/css/main.css")
    js_css += js(f"_addons/{addon_id}/web/cal-heatmap.min.js", timeout=200)

    js_css = f"""<script>
        {js_css}
        (() => {{
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = 'https://www.youtube.com/iframe_api';
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

        document.addEventListener("keydown", function (e) {{ if (typeof (globalKeydown) !== 'undefined') globalKeydown(e); }}, false);
        }})();
    </script>"""

    print("insert_scripts()")

    # aqt.editor._html += js_css
    return js_css

def set_editor_ready():
    state.set_bool(state.editor_is_ready, True)

def setup_hooks():
    """ Todo: move more add-on code to hooks. """
    add_hook("editor-with-siac-initialised", lambda: set_editor_ready())

    add_hook("user-note-created", lambda: UI.sidebar.refresh_tab(1))
    add_hook("user-note-created", lambda: try_repeat_last_search())

    add_hook("user-note-deleted", lambda: UI.sidebar.refresh_tab(1))
    add_hook("user-note-deleted", lambda: recalculate_priority_queue())
    add_hook("user-note-deleted", lambda: try_repeat_last_search())

    add_hook("user-note-edited", lambda: UI.sidebar.refresh_tab(1))
    add_hook("user-note-edited", lambda: Reader.reload_bottom_bar())
    add_hook("user-note-edited", lambda: try_repeat_last_search())

    add_hook("updated-schedule", lambda: recalculate_priority_queue())
    add_hook("updated-schedule", lambda: Reader.reload_bottom_bar())

    add_hook("reading-modal-closed", lambda: UI.sidebar.refresh_tab(1))
    add_hook("reading-modal-closed", lambda: try_repeat_last_search())

def setup_switch_btn(editor: Editor):
    """ Add a button to switch the layout to the bottom of the AddCards dialog. """

    if hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, AddCards):
        win = aqt.dialogs._dialogs["AddCards"][1]
    elif hasattr(editor, "parentWindow") and isinstance(editor.parentWindow, EditCurrent):
        if not conf_or_def("useInEdit", False):
            return
        win = aqt.dialogs._dialogs["EditCurrent"][1]
    else:
        win = aqt.dialogs._dialogs["AddCards"][1]

    if win is None:
        return

    box     = win.form.buttonBox

    # check if button has been already added
    if hasattr(box, "switch_btn") and box.switch_btn is not None:
        return

    button  = QPushButton(conf_or_def("window_mode", "Both"))
    menu    = QMenu(button)
    a1      = menu.addAction("Show Both")
    a1.triggered.connect(functools.partial(state.set_window_mode, "Both", editor))

    a2      = menu.addAction("Show Both, Auto-hide Fields")
    a2.triggered.connect(functools.partial(state.set_window_mode, "Autohide", editor))

    a3      = menu.addAction("Show Only Fields")
    a3.triggered.connect(functools.partial(state.set_window_mode, "Fields", editor))

    a4      = menu.addAction("Show Only Add-on")
    a4.triggered.connect(functools.partial(state.set_window_mode, "Addon", editor))

    button.setMenu(menu)
    box.layout().insertWidget(0, button)
    box.switch_btn = button
    win.update()


def reset_state(shortcuts: List[Tuple], editor: Editor):
    """ After the Add Card / Edit Current dialog is opened, some state variables need to be reset. """

    # might still be true if Create Note dialog was closed by closing its parent window, so reset it
    state.note_editor_shown = False
    state.set_bool(state.editor_is_ready, False)

    index                   = get_index()
    if index:
        UI.frozen     = False

    def cb(night_mode: bool):
        state.set_nightmode(night_mode)
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

def can_run_in_editor_context(editor: Editor):
    """ Determine if the add-on can run in the given context. E.g. in Add Cards window or in the Edit Current dialog, but not in the Card Browser. """
    return editor.addMode or (conf_or_def("useInEdit", False) and isinstance(editor.parentWindow, EditCurrent))

def register_shortcuts(shortcuts: List[Tuple], editor: Editor):
    """ Register shortcuts used by the add-on. """

    # prevent shortcuts from 
    if not can_run_in_editor_context(editor):
        print("[SIAC] register_shortcuts() called, but invalid editor context")
        return

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
    #_try_register("Ctrl+o", show_quick_open_pdf)

    # open Create/Update note modal
    #_try_register(config["notes.editor.shortcut"], show_note_modal)
    # can be replaced by SIAC mainmenu hotkey

    # toggle search on select in pdf reader
    _try_register(config["pdf.shortcuts.toggle_search_on_select"], lambda: editor.web.eval("togglePDFSelect()"))

    # toggle pdf links in pdf reader
    _try_register(config["pdf.shortcuts.toggle_pdf_links"], lambda: editor.web.eval("togglePDFLinks()"))

    # image selection (scissor tool) in pdf reader
    _try_register(config["pdf.shortcuts.scissor_tool"], lambda: editor.web.eval("initImageSelection()"))

    # toggle page read in pdf reader
    _try_register(config["pdf.shortcuts.toggle_page_read"], lambda: editor.web.eval("togglePageRead()"))

    # 'Done' in reading modal
    _try_register(config["pdf.shortcuts.done"], lambda: editor.web.eval("doneShortcut()"))

    # 'Later' in reading modal
    _try_register(config["pdf.shortcuts.later"], lambda: editor.web.eval("laterShortcut()"))

    # 'Page Snapshot'
    _try_register(config['pdf.shortcuts.page_snapshot'], lambda: editor.web.eval("pageSnapshot()"))

    # 'Extract'
    _try_register(config['pdf.shortcuts.extract_pages'], lambda: editor.web.eval("extractPages()"))

    # Jump to first/last page in pdf reader
    _try_register(config["pdf.shortcuts.jump_to_last_page"], lambda: editor.web.eval("jumpLastPageShortcut()"))
    _try_register(config["pdf.shortcuts.jump_to_first_page"], lambda: editor.web.eval("jumpFirstPageShortcut()"))

    # pdf page left / right
    _try_register(config["pdf.shortcuts.page_left"], lambda: editor.web.eval("pdfPageLeft()"))
    _try_register(config["pdf.shortcuts.page_right"], lambda: editor.web.eval("pdfPageRight()"))
    _try_register(config["pdf.shortcuts.toggle_read_page_right"], lambda: editor.web.eval("pdfToggleReadAndPageRight()"))

    # area highlight
    _try_register(config["pdf.shortcuts.init_area_highlight"], lambda: editor.web.eval("initAreaHighlightShortcutPressed()"))

    _try_register(config["shortcuts.focus_search_bar"], lambda: editor.web.eval("focusSearchShortcut()"))
    _try_register(config["shortcuts.trigger_search"], lambda: editor.web.eval("triggerSearchShortcut()"))
    _try_register(config["shortcuts.trigger_predef_search"], lambda: editor.web.eval("predefSearch()"))
    _try_register(config["shortcuts.trigger_current_filter"], lambda: editor.web.eval("sort()"))
    _try_register(config["shortcuts.search_for_current_field"], lambda: editor.web.eval("searchCurrentField()"))

    _try_register(config["shortcuts.window_mode.show_right"], lambda: state.switch_window_mode("right", editor))
    _try_register(config["shortcuts.window_mode.show_left"], lambda: state.switch_window_mode("left", editor))
    _try_register(config["shortcuts.window_mode.show_both"], lambda: state.switch_window_mode("both", editor))

def show_note_modal():
    """ Displays the Create/Update dialog if not already shown. """
    if not state.note_editor_shown:
        read_note_id    = Reader.note_id
        NoteEditor(UI._editor.parentWindow, note_id=None, add_only=read_note_id is not None, read_note_id=read_note_id)


def register_io_add_hook():
    """ Monkey patch IO note generation to save links to PDF page. """

    io  = __import__("1374772155")
    old = io.ngen.ImgOccNoteGenerator._saveMaskAndReturnNote

    def snew(gen, omask_path, qmask, amask, img, note_id, nid=None):
        old(gen, omask_path, qmask, amask, img, note_id, nid)
        index = get_index()
        if index and Reader.note_id and Reader.note.is_pdf() and not nid:
            stamp = utility.misc.get_milisec_stamp() - 1000
            res = mw.col.db.list(f"select * from notes where id > {stamp}")
            if res and len(res) > 0:
                nid = Reader.note_id
                def cb(page: int):
                    if page is not None and page >= 0:
                        for anid in res:
                            link_note_and_page(nid, anid, page)
                        # update sidebar if shown
                        UI.js("updatePageSidebarIfShown()")
                Reader.page_displayed(cb)

    io.ngen.ImgOccNoteGenerator._saveMaskAndReturnNote = snew

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
    if not isinstance(win, AddCards):
        return
    modifiers = evt.modifiers()
    if modifiers == Qt.ControlModifier or modifiers == Qt.AltModifier or modifiers == Qt.MetaModifier:
        return
    index = get_index()
    if UI.frozen:
        return

    if index is not None and len(self.text().strip()) > 0:
        text = self.text()
        try:
            tagEditTimer.timeout.disconnect()
        except Exception: pass
        tagEditTimer.timeout.connect(lambda: search_by_tags(text))
        tagEditTimer.start(1000)

init_addon()
menu = Menu()
