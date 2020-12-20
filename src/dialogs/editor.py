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

from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
import functools
import time
import math
import re
import random
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from anki.lang import _
from anki.utils import isMac
from ..notes import *
from ..notes import _get_priority_list
from ..hooks import run_hooks
from ..state import get_index
from ..markdown import markdown
from ..config import get_config_value_or_default, update_config
from ..web_import import import_webpage
from .importing.url_import import UrlImporter
from .external_file import ExternalFile
from .components import QtPrioritySlider, MDTextEdit
from .url_input_dialog import URLInputDialog
from ..markdown.extensions.fenced_code import FencedCodeExtension
from ..markdown.extensions.def_list import DefListExtension
from ..utility.tag_tree import TagTree

import utility.text
import utility.misc
import state

def open_editor(mw, nid):
    note = mw.col.getNote(nid)
    dialog = EditDialog(mw, note)

class EditDialog(QDialog):
    """ Edit dialog for Anki notes. """

    last_geom = None

    def __init__(self, mw, note):

        QDialog.__init__(self, None, Qt.Window)
        mw.setupDialogGC(self)

        self.mw         = mw
        self.form       = aqt.forms.editcurrent.Ui_Dialog()

        self.form.setupUi(self)
        self.form.buttonBox.button(QDialogButtonBox.Close).setShortcut(QKeySequence("Ctrl+Return"))
        self.editor     = aqt.editor.Editor(self.mw, self.form.fieldsArea, self)

        self.setWindowTitle(_("Edit Note"))
        self.setMinimumHeight(400)
        self.setMinimumWidth(500)
        if EditDialog.last_geom and get_config_value_or_default("anki.editor.remember_location", True):
            self.setGeometry(EditDialog.last_geom)
        else:
            self.resize(500, 850)
        self.editor.setNote(note, focusTo=0)
        addHook("reset", self.onReset)
        self.mw.requireReset()
        self.show()
        self.mw.progress.timer(100, lambda: self.editor.web.setFocus(), False)

    def onReset(self):
        try:
            n = self.editor.note
            n.load()
        except:
            remHook("reset", self.onReset)
            self.editor.setNote(None)
            self.mw.reset()
            self.close()
            return
        self.editor.setNote(n)

    def reopen(self, mw):
        tooltip("Please finish editing the existing card first.")
        self.onReset()

    def reject(self):
        self.saveAndClose()

    def saveAndClose(self):
        self.editor.saveNow(self._saveAndClose)

    def _saveAndClose(self):
        remHook("reset", self.onReset)
        self.editor.cleanup()
        EditDialog.last_geom = self.geometry()
        QDialog.reject(self)

    def closeWithCallback(self, onsuccess):
        def callback():
            self._saveAndClose()
            onsuccess()
        self.editor.saveNow(callback)

class NoteEditor(QDialog):
    """ The editor window for non-anki notes. """

    last_tags = ""
    last_geom = None

    def __init__(self, parent, note_id = None, add_only = False,
                 read_note_id = None, tag_prefill = None, source_prefill = None,
                 text_prefill = None, title_prefill = None, prio_prefill = None,
                 author_prefill = None, url_prefill = None):

        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        self.mw             = aqt.mw
        self.parent         = parent

        self.note_id        = note_id
        self.note           = None
        self.add_only       = add_only
        self.read_note_id   = read_note_id
        self.tag_prefill    = tag_prefill
        self.source_prefill = source_prefill
        self.text_prefill   = text_prefill
        self.title_prefill  = title_prefill
        self.prio_prefill   = prio_prefill
        self.dark_mode_used = state.night_mode

        self.screen_h       = QApplication.desktop().screenGeometry().height()

        if self.note_id is not None:
            self.note = get_note(note_id)
            if not self.note:
                return

        # fill meta data
        if self.note:
            self.author = self.note.author
            self.url    = self.note.url
        else:
            self.author = author_prefill
            self.url    = url_prefill


        #self.mw.setupDialogGC(self)
        #self.setWindowModality(Qt.WindowModal)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setup_ui()

    def setup_ui(self):

        # editing an existing note
        if self.note_id is not None:
            self.save = QPushButton("\u2714 Save ")
            self.setWindowTitle('Edit Note')
            self.save.clicked.connect(self.on_update_clicked)
            self.priority = get_priority(self.note_id)
        # creating a new note
        else:
            self.save = QPushButton("\u2714 Create ")
            self.setWindowTitle('New Note')
            self.save.clicked.connect(self.on_create_clicked)
            self.priority = 0

            self.save_and_stay = QPushButton(" \u2714 Create && Keep Open ")
            self.save_and_stay.setFocusPolicy(Qt.NoFocus)
            self.save_and_stay.clicked.connect(self.on_create_and_keep_open_clicked)
            self.save_and_stay.setShortcut("Ctrl+Shift+Return")
            self.save_and_stay.setToolTip("Ctrl+Shift+Return")

        self.save.setShortcut("Ctrl+Return")
        self.save.setToolTip("Ctrl+Return")
        self.save.setFocus(True)
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)
        priority_list = _get_priority_list()
        self.priority_list = priority_list

        self.tabs = QTabWidget()

        self.create_tab = CreateTab(self)

        #self.browse_tab = BrowseTab()
        self.tabs.addTab(self.create_tab, "Create" if self.note_id is None else "Edit")

        self.metadata_tab = MetadataTab(self)
        self.tabs.addTab(self.metadata_tab, "Metadata")

        if not self.add_only:
            self.priority_tab = PriorityTab(priority_list, self)
            self.tabs.addTab(self.priority_tab, "Queue")

        self.settings_tab = SettingsTab(self)
        self.tabs.addTab(self.settings_tab, "Settings")

        # tabs.addTab(self.browse_tab, "Browse")
        layout_main = QVBoxLayout()
        layout_main.addWidget(self.tabs)
        self.setLayout(layout_main)

        self.create_tab.title.setFocus()

        # self.exec_()
        state.note_editor_shown = True

        if NoteEditor.last_geom is not None:
            self.setGeometry(NoteEditor.last_geom)
        self.show()

    def save_geom(self):
        NoteEditor.last_geom = self.geometry()

    def on_create_clicked(self):

        success = self._create_note()
        if not success:
            return

        # maybe more elegant solution to avoid renewing search please?
        ix = get_index()
        if ix is not None and ix.ui is not None and ix.ui._editor is not None and ix.ui._editor.web is not None:
            run_hooks("user-note-created")

        self.reject()

        # if reading modal is open, we might have to update the bottom bar
        if self.read_note_id is not None:
            get_index().ui.reading_modal.reload_bottom_bar()

    def on_create_and_keep_open_clicked(self):
        success = self._create_note()
        if not success:
            return

        # maybe more elegant solution to skip updating search/sidebar refresh?
        ix = get_index()
        if ix is not None and ix.ui is not None and ix.ui._editor is not None and ix.ui._editor.web is not None:
            run_hooks("user-note-created")


        if self.read_note_id is not None:
            get_index().ui.reading_modal.reload_bottom_bar()

        self._reset()

    def _create_note(self):
        title = self.create_tab.title.text()
        title = utility.text.clean_user_note_title(title)

        # if this check is missing, text is sometimes saved as an empty paragraph
        if self.create_tab.text.document().isEmpty():
            text = ""   
        else:
            # text = self.create_tab.text.toHtml()
            if self.create_tab.text.text_was_pasted:
                text = self.create_tab.text.toMarkdown()
            else:
                text = self.create_tab.text.toPlainText()
                # text = re.sub("(\r\n|\n|\r)^", "  \n", text, flags=re.M)
            # text = markdown(text)


        source              = self.create_tab.source.text()
        tags                = self.create_tab.tag.text()
        priority            = self.create_tab.slider.value()
        specific_schedule   = self.create_tab.slider.schedule()
        author              = self.metadata_tab.author.text()
        url                 = self.metadata_tab.url.text()

        # if source is a pdf, title must be given
        if len(title.strip()) == 0 and source.lower().strip().endswith(".pdf"):
            tooltip("Title must be set if source is PDF.")
            return False

        if len(title.strip()) + len(text.strip()) == 0:
            tooltip("Either Text or Title have to be filled out.")
            return False

        if len(tags.strip()) == 0:
            default_tags = get_config_value_or_default("notes.editor.defaultTagsIfEmpty", "")
            if len(default_tags) > 0:
                tags = default_tags

        NoteEditor.last_tags = tags
        create_note(title, text, source, tags, None, specific_schedule, priority, author, url = url)
        return True

    def _reset(self):
        """
            Called after a note is created with the save_and_stay button.
            Clear the fields for the next note.
        """
        self.create_tab.title.setText("")
        self.create_tab.text.setMarkdown("")
        if self.create_tab.source.text().endswith(".pdf"):
            self.create_tab.source.setText("")
        self.create_tab.title.setFocus()

        self.create_tab.tree.include_anki_tags = self.create_tab.all_tags_cb.isChecked()
        self.create_tab.tree.rebuild_tree()


    def on_update_clicked(self):
        title = self.create_tab.title.text()
        title = utility.text.clean_user_note_title(title)

        # if this check is missing, text is sometimes saved as an empty paragraph
        if self.create_tab.text.document().isEmpty():
            text = ""
        else:
            if self.create_tab.text.text_was_pasted:
                text = self.create_tab.text.toMarkdown()
            else:
                text = self.create_tab.text.toPlainText()
                # text = re.sub("([^ ][^ ])(\r\n|\n|\r)^", r"\1  \n", text, flags=re.M)
        source                  = self.create_tab.source.text()
        # TODO
        author                  = self.metadata_tab.author.text()
        url                     = self.metadata_tab.url.text()
        tags                    = self.create_tab.tag.text()
        priority                = self.create_tab.slider.value()
        if not self.create_tab.slider.has_changed_value():
            # -1 = unchanged
            priority = -1
        specific_schedule       = self.create_tab.slider.schedule()

        NoteEditor.last_tags    = tags
        update_note(self.note_id, title, text, source, tags, specific_schedule, priority, author, url)
        run_hooks("user-note-edited", self.note_id)

        if self.create_tab.slider.has_changed_value():
            run_hooks("updated-schedule")

        self.reject()

    def reject(self):
        """ Called in any case (Save, Cancel, Close Button on top right) """

        run_hooks("user-note-closed")
        self.save_geom()
        if not self.add_only:
            self.priority_tab.t_view.setModel(None)
        state.note_editor_shown = False
        QDialog.reject(self)

    def accept(self):
        state.note_editor_shown = False
        self.reject()

class CreateTab(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)

        self.queue_schedule     = 0
        self.parent             = parent
        self.tree               = QTreeWidget()
        self.original_bg        = None
        self.original_fg        = None

        web_path                = utility.misc.get_web_folder_path()
        icons_path              = web_path + "icons/"
        config                  = mw.addonManager.getConfig(__name__)

        self.tag_icon           = QIcon(icons_path + "icon-tag-24.png")

        if self.parent.dark_mode_used:
            tag_bg                  = config["styles.night.tagBackgroundColor"]
            tag_fg                  = config["styles.night.tagForegroundColor"]
            hover_bg                = "palette(light)"
        else:
            tag_bg                  = config["styles.tagBackgroundColor"]
            tag_fg                  = config["styles.tagForegroundColor"]
            hover_bg                = "palette(dark)"

        include_anki_tags   = get_config_value_or_default("notes.editor.include_anki_tags", False)
        tag_sort            = get_config_value_or_default("notes.editor.tag_sort", "a-z")

        self.tree   = TagTree(include_anki_tags = include_anki_tags, only_tags = True, knowledge_tree = False, sort=tag_sort)
        self.tree.itemClicked.connect(self.tree_item_clicked)

        queue_len   = len(parent.priority_list)
        schedule    = None if self.parent.note is None else self.parent.note.reminder
        self.slider = QtPrioritySlider(self.parent.priority, self.parent.note_id, schedule=schedule)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(10,10,10,10)

        vbox_taglist = QVBoxLayout()
        vbox_taglist.setContentsMargins(0,0,0,0)
        tag_lbl = QLabel()
        tag_icn = QPixmap(utility.misc.get_web_folder_path() + "icons/icon-tag-24.png").scaled(14,14)
        tag_lbl.setPixmap(tag_icn)

        tag_hb = QHBoxLayout()
        tag_hb.setAlignment(Qt.AlignLeft)
        tag_hb.addWidget(tag_lbl)
        tag_hb.addWidget(QLabel("Tags (Click to Add)"))

        vbox_taglist.addLayout(tag_hb)

        vbox_taglist.addWidget(self.tree)
        self.all_tags_cb = QCheckBox("Include Anki Tags")
        self.all_tags_cb.setChecked(include_anki_tags)
        self.all_tags_cb.stateChanged.connect(self.tag_cb_changed)
        hbox_tag_b = QHBoxLayout()
        hbox_tag_b.addWidget(self.all_tags_cb)

        self.tag_sort = QComboBox()
        self.tag_sort.addItem("A-Z")
        self.tag_sort.addItem("Recency")
        self.tag_sort.currentTextChanged.connect(self.on_tag_sort_change)
        self.tag_sort.setCurrentText(tag_sort)
        hbox_tag_b.addStretch(10)
        hbox_tag_b.addWidget(QLabel("Sort: "))
        hbox_tag_b.addWidget(self.tag_sort)

       
        hbox_tag_b.addStretch(1)
        vbox_taglist.addLayout(hbox_tag_b)


        vbox_priority = QVBoxLayout()
        vbox_priority.setContentsMargins(0,0,0,0)
        vbox_priority.addWidget(self.slider)

        widget_taglist = QWidget()
        widget_priority = QWidget()
        widget_priority.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        widget_taglist.setLayout(vbox_taglist)
        widget_priority.setLayout(vbox_priority)

        tmp_layout = QVBoxLayout()
        tmp_layout.setContentsMargins(0,0,0,0)

        self.left_pane = QWidget()
        self.left_pane.setLayout(tmp_layout)
        self.left_pane.layout().addWidget(widget_taglist, 1)
        self.left_pane.layout().addWidget(widget_priority, 0)
        self.layout.addWidget(self.left_pane, 7)

        hbox = QHBoxLayout()

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("<")
        self.toggle_btn.setFocusPolicy(Qt.NoFocus)
        self.toggle_btn.clicked.connect(self.toggle_left_pane)
        hbox.addWidget(self.toggle_btn)

        hbox.addStretch(1)
        if parent.note_id is None:
            hbox.addWidget(parent.save_and_stay)
        hbox.addWidget(parent.save)
        hbox.addWidget(parent.cancel)

        vbox = QVBoxLayout()
        # vbox.addStretch(1)

        title_lbl = QLabel("Title")
        self.title = QLineEdit()
        if self.parent.title_prefill is not None:
            self.title.setText(self.parent.title_prefill)
        f = self.title.font()
        f.setPointSize(14)
        self.title.setFont(f)
        vbox.addWidget(title_lbl)
        vbox.addWidget(self.title)

        text_lbl = QLabel("Text [Markdown]")
        self.text = MDTextEdit()
        f = self.text.font()
        f.setPointSize(12)
        self.text.setFont(f)


        if self.parent.screen_h < 1400:
            self.text.setMinimumHeight(180)
            self.text.setMinimumWidth(370)
        else:
            self.text.setMinimumHeight(380)
            self.text.setMinimumWidth(470)

        self.text.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding)
        self.text.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.text.setLineWidth(2)
        # self.text.cursorPositionChanged.connect(self.on_text_cursor_change)
        if hasattr(self.text, "setTabStopDistance"):
            self.text.setTabStopDistance(QFontMetricsF(f).horizontalAdvance(' ') * 4)
        t_h = QHBoxLayout()
        t_h.addWidget(text_lbl)

        self.tb = QToolBar("Format")
        # self.tb.setStyleSheet("background-color: transparent; border: 0px;")

        self.tb.setHidden(False)
        self.tb.setOrientation(Qt.Horizontal)
        self.tb.setIconSize(QSize(12, 12))

        clean_btn = QPushButton()
        clean_btn.setText("Clean...  ")
        clean_btn.setFocusPolicy(Qt.NoFocus)
        clean_menu = QMenu(clean_btn)
        if self.parent.dark_mode_used:
            clean_menu.setStyleSheet("""
                QMenu { background: #3a3a3a; color: lightgrey; font-size: 10px; }
                QMenu:item:selected { background: steelblue; color: white; }
            """)
        else:
            clean_menu.setStyleSheet("""
                QMenu { background: white; color: black; font-size: 10px;}
                QMenu:item:selected { background: #2496dc; color: white; }
            """)


        clean_menu.addAction("Remove all Formatting").triggered.connect(self.on_remove_formatting)
        clean_menu.addAction("Remove HTML").triggered.connect(self.on_remove_html)
        # clean_menu.addAction("Remove all Headers (#)").triggered.connect(self.on_remove_headers_clicked)
        clean_btn.setMenu(clean_menu)
        self.tb.addWidget(clean_btn)

        t_h.addStretch(1)
        t_h.addWidget(self.tb)

        url_btn = QPushButton(u"Fetch from URL ... ")
        url_btn.setFocusPolicy(Qt.NoFocus)
        url_btn.clicked.connect(self.on_url_clicked)
        t_h.addWidget(url_btn)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setFocusPolicy(Qt.NoFocus)
        self.preview_btn.clicked.connect(self.on_preview_clicked)
        t_h.addWidget(self.preview_btn)

        vbox.addLayout(t_h)
        vbox.addWidget(self.text)

        self.preview = QWebEngineView()

        if self.parent.screen_h < 1400:
            self.preview.setMinimumHeight(180)
            self.preview.setMinimumWidth(370)
        else:
            self.preview.setMinimumHeight(380)
            self.preview.setMinimumWidth(470)

        self.preview.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setVisible(False)
        vbox.addWidget(self.preview)

        self.source         = QLineEdit()
        # if note is an extract, prevent source editing
        if self.parent.note is not None and self.parent.note.extract_end is not None:
            source_lbl          = QLabel("Source - Note is an extract")
            # self.source.setReadOnly(True)
        else:
            source_lbl          = QLabel("Source")
        source_hb           = QHBoxLayout()
        #source_hb.addWidget(self.source)
        if self.parent.source_prefill is not None:
            self.source.setText(self.parent.source_prefill.replace("\\", "/"))

        file_btn            = QPushButton("External file")
        file_btn.setFocusPolicy(Qt.NoFocus)
        file_btn.clicked.connect(self.on_file_clicked)
        source_hb.addWidget(file_btn)
        pdf_btn             = QPushButton("PDF")
        pdf_btn.setFocusPolicy(Qt.NoFocus)
        pdf_btn.clicked.connect(self.on_pdf_clicked)
        source_hb.addWidget(pdf_btn)
        pdf_from_url_btn    = QPushButton("PDF from Webpage")
        pdf_from_url_btn.clicked.connect(self.on_pdf_from_url_clicked)
        pdf_from_url_btn.setFocusPolicy(Qt.NoFocus)
        source_hb.addWidget(pdf_from_url_btn)

        # if note is an extract, prevent source editing
        # if self.parent.note is not None and self.parent.note.extract_end is not None:
        #     pdf_btn.setDisabled(True)
        #     pdf_from_url_btn.setDisabled(True)

        vbox.addWidget(source_lbl)
        vbox.addWidget(self.source)
        vbox.addLayout(source_hb)

        if self.parent.text_prefill is not None:
            self.text.setPlainText(self.parent.text_prefill)

        # btn_styles = """
        # QPushButton#q_1 { padding-left: 20px; padding-right: 20px; }
        # QPushButton#q_2 { padding-left: 17px; padding-right: 17px; }
        # QPushButton#q_3 { padding-left: 13px; padding-right: 13px; }
        # QPushButton#q_4 { padding-left: 8px; padding-right: 8px; }
        # QPushButton#q_5 { padding-left: 2px; padding-right: 2px; }
        # QPushButton#q_6 { padding-left: 0px; padding-right: 0px; }
        # QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_3,QPushButton:hover#q_4,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: lightblue; }
        # """

        self.setObjectName("create_tab")

        styles = """
            QPushButton#q_1,QPushButton#q_2,QPushButton#q_3,QPushButton#q_4,QPushButton#q_5,QPushButton#q_6 { border-radius: 5px; }

            QTextEdit { border-radius: 5px; border: 1px solid #717378;  padding: 3px; }
            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}
            #recentDisp { margin: 5px; }

        """ #% btn_styles

        if parent.dark_mode_used:
            styles += """
                QToolTip { background: #3a3a3a; color: lightgrey; }
            """
        else:
            styles += """
                QToolTip { color: black; background-color: white; }
            """

        self.setStyleSheet(styles)

        # vbox.addStretch(1)
        tag_lbl2 = QLabel()
        tag_lbl2.setPixmap(tag_icn)

        tag_hb2 = QHBoxLayout()
        tag_hb2.setAlignment(Qt.AlignLeft)
        tag_hb2.addWidget(tag_lbl2)
        tag_hb2.addWidget(QLabel("Tags"))

        vbox.addLayout(tag_hb2)
        self.tag = QLineEdit()
        tags = get_all_tags()
        if tags:
            completer = QCompleter(tags)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.tag.setCompleter(completer)
        vbox.addWidget(self.tag)
        if self.parent.tag_prefill is not None:
            self.tag.setText(self.parent.tag_prefill)

        vbox.setAlignment(Qt.AlignTop)
        vbox.addSpacing(10)
        vbox.addLayout(hbox)
        vbox.setSpacing(5)
        self.layout.addSpacing(5)
        self.layout.addLayout(vbox, 73)
        self.setLayout(self.layout)

        # if we are in update mode, fill fields
        if parent.note is not None:
            self.tag.setText(parent.note.tags.lstrip())
            self.title.setText(parent.note.title)
            if utility.text.is_html(parent.note.text):
                self.text.setHtml(parent.note.text)
                self.text.setPlainText(self.text.toMarkdown())
            else:
                self.text.setPlainText(parent.note.text)
            self.source.setText(parent.note.source)


        # toggle left pane by default if enabled in settings
        if get_config_value_or_default("notes.editor.autoHideLeftPaneOnOpen", False):
            self.left_pane.setVisible(False)
            self.toggle_btn.setText(">")

        # fill tags with last tags if enabled in settings
        if (parent.note is None
            and self.parent.tag_prefill is None
            and len(NoteEditor.last_tags.strip()) > 0
            and get_config_value_or_default("notes.editor.autoFillWithLastTagsOnOpen", False)):
            self.tag.setText(NoteEditor.last_tags.lstrip())



    def _add_to_tree(self, map, prefix):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setData(1, 1, QVariant(prefix + t))
            ti.setIcon(0, self.tag_icon)
            prefix_c = prefix + t + "::"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def tree_item_clicked(self, item, col):
        tag = item.data(1, 1)
        self.add_tag(tag)

    def recent_item_clicked(self, item):
        tag = item.data(Qt.UserRole)
        self.add_tag(tag)

    def add_tag(self, tag):
        if tag is None or len(tag.strip()) == 0:
            return
        existing = self.tag.text().split()
        if tag in existing:
            return
        existing.append(tag)
        existing = sorted(existing)
        self.tag.setText(" ".join(existing))

    def tag_cb_changed(self, state):
        self.tree.include_anki_tags = (state == Qt.Checked)
        self.tree.rebuild_tree()
        update_config("notes.editor.include_anki_tags", state == Qt.Checked)

    def on_tag_sort_change(self, new_sort: str):
        self.tree.sort = new_sort.lower()
        self.tree.rebuild_tree()
        update_config("notes.editor.tag_sort", new_sort)


#    def build_tree(self, tmap):
#        for t, children in tmap.items():
#            ti = QTreeWidgetItem([t])
#            ti.setData(1, 1, QVariant(t))
#            ti.setIcon(0, self.tag_icon)
#            ti.addChildren(self._add_to_tree(children, t + "::"))
#            self.tree.addTopLevelItem(ti)

    def toggle_left_pane(self):
        self.left_pane.setVisible(not self.left_pane.isVisible())
        if self.left_pane.isVisible():
            self.toggle_btn.setText("<")
        else:
            self.toggle_btn.setText(">")

    # def on_text_history_exp(self):

    def on_preview_clicked(self):
        if self.preview.isHidden():
            fg = self.text.palette().color(QPalette.Foreground).name()
            bg = self.text.palette().color(QPalette.Background).name()
            addon_id    = utility.misc.get_addon_id()
            port        = aqt.mw.mediaServer.getPort()
            nightmode   = "nightMode" if self.parent.dark_mode_used else ""
            self.preview.setHtml(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        background: {bg};
                        color: {fg};
                    }}
                    @font-face {{
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
                    }}
                    body {{
                        font-family: "Open Sans";
                    }}
                    dt {{
                        font-weight: bold;
                    }}
                    dd {{
                        font-style: italic;
                    }}
                    dl {{
                        border-left: 10px solid {fg};
                        padding-left: 10px;
                        margin: 1.5em 10px;

                    }}
                    blockquote,  pre {{
                        background: #f9f9f9;
                        border-left: 10px solid #2496dc;
                        margin: 1.5em 10px;
                        padding: 0.5em 10px;
                    }}
                    body.nightMode blockquote, body.nightMode pre {{
                        background: #474749;
                        border-left: 10px solid #2496dc;
                    }}

                </style>
            </head>
            <body class='{nightmode}'>
                {markdown(self.text.toMarkdown(), extensions=[FencedCodeExtension(), DefListExtension()])}
            </body>
            </html>""")
            self.preview_btn.setText("Back")
        else:
            self.preview_btn.setText("Preview")
        self.text.setVisible(self.text.isHidden())
        self.preview.setVisible(self.preview.isHidden())

    def on_file_clicked(self):
        dialog = ExternalFile(self)

        if dialog.exec_():
            path = dialog.chosen_file
            if path is not None and len(path.strip())> 0:
                self.source.setText(path)

    def on_pdf_clicked(self):
        fname = QFileDialog.getOpenFileName(self, 'Pick a PDF', '',"PDF (*.pdf)")
        if fname is not None:
            self.source.setText(fname[0])

    def on_pdf_from_url_clicked(self):
        dialog = UrlImporter(self, show_schedule=False)
        if dialog.exec_():
            if dialog.chosen_url is not None and len(dialog.chosen_url.strip()) > 0:
                name = dialog.get_name()
                path = get_config_value_or_default("pdfUrlImportSavePath", "")
                if path is None or len(path) == 0:
                    tooltip("""You have to set a save path for imported URLs first.
                        <center>Config value: <i>pdfUrlImportSavePath</i></center>
                    """, period=4000)
                    return
                path = utility.misc.get_pdf_save_full_path(path, name)
                utility.misc.url_to_pdf(dialog.chosen_url, path)
                self.source.setText(path)
            else:
                tooltip("Invalid URL")


    def on_url_clicked(self):
        dialog = URLInputDialog(self)
        if dialog.exec_():
            if dialog.chosen_url is not None and len(dialog.chosen_url.strip()) > 0:
                text = import_webpage(dialog.chosen_url, inline_images=False)
                if text is None:
                    tooltip("Failed to fetch text from page.")
                else:
                    self.text.setHtml(text)

    def on_remove_formatting(self):

        html = markdown(self.text.toMarkdown())
        text = utility.text.html_to_text(html)
        self.text.setPlainText(text)

    def on_remove_html(self):
        html = self.text.toPlainText()
        cleaned = utility.text.remove_html(html)
        self.text.setPlainText(cleaned)

    def on_text_cursor_change(self):
        cursor = self.text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()
        self.line_status.setText("Ln: {}, Col: {}".format(line,col))


class PriorityTab(QWidget):

    def __init__(self, priority_list, parent):

        QWidget.__init__(self)

        self.parent     = parent
        self.t_view     = QTableView()

        html_delegate   = HTMLDelegate()
        model           = self.get_model(priority_list)

        self.t_view.setItemDelegateForColumn(0, html_delegate)
        self.t_view.setItemDelegateForColumn(1, html_delegate)
        self.t_view.setModel(model)

        self.set_remove_btns(priority_list)

        self.t_view.resizeColumnsToContents()
        self.t_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.t_view.setDragEnabled(True)
        # self.t_view.setDropIndicatorShown(True)
        # self.t_view.setAcceptDrops(True)
        # self.t_view.viewport().setAcceptDrops(True)
        # self.t_view.setDragDropOverwriteMode(False)

        # self.t_view.setDragDropMode(QAbstractItemView.InternalMove)
        # self.t_view.setDefaultDropAction(Qt.MoveAction)
        if priority_list is not None and len(priority_list) > 0:
            self.t_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.t_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.t_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.t_view.resizeRowsToContents()

        self.t_view.verticalHeader().setSectionsMovable(False)
        self.t_view.setSelectionMode(QAbstractItemView.SingleSelection)

        self.vbox = QVBoxLayout()
        lbl = QLabel("'Remove' will only remove the item from the queue, not delete it.")
        self.vbox.addWidget(lbl)
        self.vbox.addWidget(self.t_view)

        # bottom_box = QHBoxLayout()
        # # self.shuffle_btn = QPushButton("Shuffle")
        # # # self.shuffle_btn.clicked.connect(self.on_shuffle_btn_clicked)
        # # bottom_box.addWidget(self.shuffle_btn)
        # # bottom_box.addStretch(1)
        # self.vbox.addLayout(bottom_box)

        self.setLayout(self.vbox)
        if parent.dark_mode_used:
            self.setStyleSheet("""
            QHeaderView::section { background-color: #313233; color: white; }
            QTableCornerButton::section {
                background-color: #313233;
            }
            """)


    def on_remove_clicked(self, id):
        """
            Remove an item from the queue.
        """
        row_len = self.t_view.model().rowCount()
        for r in range(row_len):
            n_id = self.t_view.model().item(r, 0).data()
            if n_id == id:
                self.t_view.model().removeRow(r)
                remove_from_priority_list(n_id)
                break

    def get_model(self, priority_list):
        model = PriorityListModel(self)

        config = mw.addonManager.getConfig(__name__)
        if self.parent.dark_mode_used:
            tag_bg                  = config["styles.night.tagBackgroundColor"]
            tag_fg                  = config["styles.night.tagForegroundColor"]
        else:
            tag_bg                  = config["styles.tagBackgroundColor"]
            tag_fg                  = config["styles.tagForegroundColor"]

        for c, pitem in enumerate(priority_list):

            # build display text
            text = pitem.title if pitem.title is not None and len(pitem.title.strip()) > 0 else "Untitled"
            text = "<b>%s</b>" % text

            tags = pitem.tags
            if tags is not None and len(tags.strip()) > 0:
                tag_sep = "&nbsp;</span> <span style='color: %s; background-color: %s; margin-right: 5px; border: none; border-radius: 5px;'>&nbsp;" % (tag_fg, tag_bg)
                tags = "<span style='color: %s; background-color: %s; margin-right: 5px; border: none; border-radius: 5px;'>&nbsp;%s&nbsp;</span>" % (tag_fg, tag_bg, tag_sep.join([t for t in tags.split(" ") if len(t) > 0]))

            item = QStandardItem(text)
            item.setData(QVariant(pitem.id))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 0, item)
            titem = QStandardItem(tags)
            titem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 1, titem)
            oitem = QStandardItem()
            oitem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 2, oitem)

        model.setHeaderData(0, Qt.Horizontal, "Title")
        model.setHeaderData(1, Qt.Horizontal, "Tags")
        model.setHeaderData(2, Qt.Horizontal, "Actions")
        return model

    def set_remove_btns(self, priority_list):
        for r in range(len(priority_list)):
            rem_btn = QToolButton()
            rem_btn.setText(" - ")
            rem_btn.clicked.connect(functools.partial(self.on_remove_clicked, priority_list[r].id))
            self.t_view.setIndexWidget(self.t_view.model().index(r,2), rem_btn)


class MetadataTab(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Author(s)"))
        self.author = QLineEdit()
        self.layout.addWidget(self.author)
        self.layout.addWidget(QLabel("Url"))
        self.url = QLineEdit()
        self.layout.addWidget(self.url)
        self.layout.addStretch()
        self.setLayout(self.layout)

        self.author.setText(self.parent.author)
        self.url.setText(self.parent.url)

class SettingsTab(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("If note is created untagged, give it the following tag(s)"))
        self.auto_tag_le = QLineEdit()
        self.auto_tag_le.setText(get_config_value_or_default("notes.editor.defaultTagsIfEmpty", ""))
        self.auto_tag_le.editingFinished.connect(self.update_default_tags)
        self.layout.addWidget(self.auto_tag_le)

        self.auto_fill_with_last_tag_cb = QCheckBox("Auto-fill with last tag(s) on open")
        self.auto_fill_with_last_tag_cb.setChecked(get_config_value_or_default("notes.editor.autoFillWithLastTagsOnOpen", False))
        self.auto_fill_with_last_tag_cb.clicked.connect(self.auto_fill_with_last_tag_cb_clicked)
        self.layout.addWidget(self.auto_fill_with_last_tag_cb)

        self.auto_hide_left_pane_cb = QCheckBox("Hide left side by default on open")
        self.auto_hide_left_pane_cb.setChecked(get_config_value_or_default("notes.editor.autoHideLeftPaneOnOpen", False))
        self.auto_hide_left_pane_cb.clicked.connect(self.auto_hide_left_pane_cb_clicked)
        self.layout.addWidget(self.auto_hide_left_pane_cb)

        self.layout.addWidget(QLabel("Shortcut for this modal (default \"Ctrl+Shift+n\", requires Anki restart):"))
        self.shortcut_le = QLineEdit()
        self.shortcut_le.setText(get_config_value_or_default("notes.editor.shortcut", "Ctrl+Shift+n"))
        self.layout.addWidget(self.shortcut_le)
        self.shortcut_le.editingFinished.connect(self.update_shortcut)

        self.layout.addSpacing(15)

        lbl = QLabel("Queue Settings")
        lbl.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        self.priority_mod_le = QDoubleSpinBox()
        self.priority_mod_le.setMinimum(0.1)
        self.priority_mod_le.setDecimals(1)
        self.priority_mod_le.setSingleStep(0.1)
        self.priority_mod_le.setValue(get_config_value_or_default("notes.queue.priorityMod", 1.0))
        self.priority_mod_le.valueChanged.connect(self.priority_mod_changed)
        hb = QHBoxLayout()
        hb.addWidget(QLabel("Priority Weight (default: 1.0, requires Anki restart):"))
        hb.addStretch(1)
        hb.addWidget(self.priority_mod_le)
        self.layout.addLayout(hb)

        self.layout.addSpacing(15)
        self.layout.addWidget(QLabel("Example queue calculation with current settings:"))


        container = QWidget()
        container.setLayout(QVBoxLayout())
        container.layout().setContentsMargins(0,0,0,0)

        self.qu_examples = [QLineEdit() for ix in range(0, 13)]
        for le in self.qu_examples:
            container.layout().addWidget(le)

        qs = QScrollArea()
        qs.setStyleSheet(""" QScrollArea { background-color: transparent; } """)
        qs.setFrameShape(QFrame.NoFrame)
        qs.setWidgetResizable(True)
        qs.setWidget(container)
        qs.setMaximumHeight(300)

        self.layout.addWidget(qs)
        self.layout.addStretch(1)
        self.setLayout(self.layout)
        self.update_queue_example()

    def auto_hide_left_pane_cb_clicked(self):
        update_config("notes.editor.autoHideLeftPaneOnOpen", self.auto_hide_left_pane_cb.isChecked())

    def auto_fill_with_last_tag_cb_clicked(self):
        update_config("notes.editor.autoFillWithLastTagsOnOpen", self.auto_fill_with_last_tag_cb.isChecked())

    def priority_mod_changed(self, new_val):
        update_config("notes.queue.priorityMod", new_val)
        self.update_queue_example()

    def update_default_tags(self):
        tags = self.auto_tag_le.text()
        update_config("notes.editor.defaultTagsIfEmpty", tags)
        self.update_queue_example

    def update_shortcut(self):
        text = self.shortcut_le.text()
        if text is None or len(text.strip()) == 0:
            return
        update_config("notes.editor.shortcut", text)

    def update_queue_example(self):
        """ Example queue calculation with the current parameters. """

        def _calc_score(priority, days_delta, prio_scale, prio_mod):
            prio_score = 1 + ((priority - 1) / 99) * (prio_scale - 1)
            if days_delta < 1:
                return days_delta + prio_score / 50000
            return days_delta + prio_mod * prio_score

        prio_scale  = get_config_value_or_default("notes.queue.priorityScaleFactor", 5)
        prio_mod    = get_config_value_or_default("notes.queue.priorityMod", 1.0)

        items       = [(0.1, 50), (1, 20), (1, 80), (3, 40), (0.5, 90), (0.2, 30), (10, 30), (10, 60), (6.4, 10), (1.4, 20), (0.1, 100), (0.2, 90), (0.01, 90)]

        scores      = []
        for item in items:
            score = _calc_score(item[1], item[0], prio_scale, prio_mod)
            scores.append((score, item))
        scores = sorted(scores, key=lambda x: x[0], reverse=True)
        for ix, s in enumerate(scores):
            self.qu_examples[ix].setText(f"{ix+1}. Score: {round(s[0], 2)}, Days since last seen: {s[1][0]}, Priority: {s[1][1]}")
            self.qu_examples[ix].setReadOnly(True)







class PriorityListModel(QStandardItemModel):

    def __init__(self, parent):
        super(PriorityListModel, self).__init__()
        self.parent = parent

    def dropMimeData(self, data, action, row, col, parent):
        if row == -1 and (parent is None or parent.row() == -1):
            return False
        success =  super(PriorityListModel, self).dropMimeData(data, action, row, 0, parent)
        if success:
            if row == -1 and parent is not None:
                row = parent.row()
            max_row = self.rowCount()
            ids = list()
            for i in range(0, max_row):
                item = self.item(i)
                data = item.data()
                ids.append(data)
            id = ids[row]
            ids = [i for ix ,i in enumerate(ids) if i != id or ix == row]

            rem_btn = QPushButton("Remove")
            if self.parent.parent.dark_mode_used:
                rem_btn.setStyleSheet("border: 1px solid darkgrey; border-style: outset; font-size: 10px; background: #313233; color: white; margin: 0px; padding: 3px;")
            else:
                rem_btn.setStyleSheet("border: 1px solid black; border-style: outset; font-size: 10px; background: white; margin: 0px; padding: 3px;")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setMinimumHeight(18)
            rem_btn.clicked.connect(functools.partial(self.parent.on_remove_clicked, self.item(row).data()))

            h_l = QHBoxLayout()
            h_l.addWidget(rem_btn)
            cell_widget = QWidget()
            cell_widget.setLayout(h_l)
            self.parent.t_view.setIndexWidget(self.index(row,2), cell_widget)
        return success

class BrowseTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

    def _add_to_tree(self, map):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            for c,m in children.items():
                ti.addChildren(self._add_to_tree(children))
            res.append(ti)
        return res

    def tree_item_clicked(self, item, col):
        tag = item.text(0)
        pass

class HTMLDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__()
        self.doc = QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()

        options = QStyleOptionViewItem(option)

        self.initStyleOption(options, index)
        self.doc.setHtml(options.text)
        options.text = ""

        style = QApplication.style() if options.widget is None \
            else options.widget.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(
                QPalette.Active, QPalette.HighlightedText))
        else:
            ctx.palette.setColor(QPalette.Text, option.palette.color(
                QPalette.Active, QPalette.Text))

        textRect = style.subElementRect(
            QStyle.SE_ItemViewItemText, options)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(self.doc.idealWidth(), self.doc.size().height())

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()
