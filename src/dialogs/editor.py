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
from ..notes import *
from ..notes import _get_priority_list
from ..hooks import run_hooks
from ..state import get_index
from ..config import get_config_value_or_default, update_config
from ..web_import import import_webpage
from .url_import import UrlImporter
from .components import QtPrioritySlider
from .url_input_dialog import URLInputDialog

import utility.text
import utility.misc
import state

def openEditor(mw, nid):
    note = mw.col.getNote(nid)
    dialog = EditDialog(mw, note)

class EditDialog(QDialog):
    """ Edit dialog for Anki notes. """

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
        QDialog.reject(self)

    def closeWithCallback(self, onsuccess):
        def callback():
            self._saveAndClose()
            onsuccess()
        self.editor.saveNow(callback)

class NoteEditor(QDialog):
    """ The editor window for non-anki notes. """

    last_tags = ""

    def __init__(self, parent, note_id = None, add_only = False, read_note_id = None, tag_prefill = None, source_prefill = None, text_prefill = None, title_prefill = None, prio_prefill = None):

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

        if self.note_id is not None:
            self.note = get_note(note_id)
        #self.mw.setupDialogGC(self)
        #self.setWindowModality(Qt.WindowModal)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setup_ui()

    def setup_ui(self):
        
        # editing an existing note
        if self.note_id is not None:
            self.save = QPushButton("\u2714 Save")
            self.setWindowTitle('Edit Note')
            self.save.clicked.connect(self.on_update_clicked)
            self.priority = get_priority(self.note_id)
        # creating a new note
        else:
            self.save = QPushButton("\u2714 Create")
            self.setWindowTitle('New Note')
            self.save.clicked.connect(self.on_create_clicked)
            self.priority = 0
        
            self.save_and_stay = QPushButton(" \u2714 Create && Keep Open ")
            self.save_and_stay.clicked.connect(self.on_create_and_keep_open_clicked)
            self.save_and_stay.setShortcut("Ctrl+Shift+Return")

        self.save.setShortcut("Ctrl+Return")
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)
        priority_list = _get_priority_list()
        self.priority_list = priority_list

        self.tabs = QTabWidget()
         
        self.create_tab = CreateTab(self)
        
        #self.browse_tab = BrowseTab()
        self.tabs.addTab(self.create_tab, "Create")
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
        self.show()


    def on_create_clicked(self):
        
        success = self._create_note()
        if not success:
            return
        #aqt.dialogs.close("UserNoteEditor")
        run_hooks("user-note-created")
        self.reject()

        # if reading modal is open, we might have to update the bottom bar
        if self.read_note_id is not None:
            get_index().ui.reading_modal.update_reading_bottom_bar(self.read_note_id)

    def on_create_and_keep_open_clicked(self):
        success = self._create_note()
        if not success:
            return
        run_hooks("user-note-created")
        if self.read_note_id is not None:
            get_index().ui.reading_modal.update_reading_bottom_bar(self.read_note_id)

        self._reset()

    def _create_note(self):
        title = self.create_tab.title.text()
        title = utility.text.clean_user_note_title(title) 
        if self.create_tab.plain_text_cb.checkState() == Qt.Checked:
            text = self.create_tab.text.toPlainText()
        else:
            # if this check is missing, text is sometimes saved as an empty paragraph
            if self.create_tab.text.document().isEmpty():
                text = ""
            else:
                text = self.create_tab.text.toHtml()

        source              = self.create_tab.source.text()
        tags                = self.create_tab.tag.text()
        queue_schedule      = self.create_tab.slider.value()
        specific_schedule   = self.create_tab.slider.schedule()

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
        create_note(title, text, source, tags, None, specific_schedule, queue_schedule)
        return True

    def _reset(self):
        """
            Called after a note is created with the save_and_stay button.
            Clear the fields for the next note.
        """
        self.create_tab.title.setText("")
        self.create_tab.text.setText("")
        if self.create_tab.source.text().endswith(".pdf"):
            self.create_tab.source.setText("")
        self.create_tab.title.setFocus()
        

    def on_update_clicked(self):
        title = self.create_tab.title.text()
        title = utility.text.clean_user_note_title(title) 
        if self.create_tab.plain_text_cb.checkState() == Qt.Checked:
            text = self.create_tab.text.toPlainText()
        else:
            # if this check is missing, text is sometimes saved as an empty paragraph
            if self.create_tab.text.document().isEmpty():
                text = ""
            else:
                text = self.create_tab.text.toHtml()
        source                  = self.create_tab.source.text()
        tags                    = self.create_tab.tag.text()
        priority                = self.create_tab.slider.value()
        if not self.create_tab.slider.has_changed_value():
            priority = -1
        specific_schedule       = self.create_tab.slider.schedule()

        NoteEditor.last_tags    = tags
        update_note(self.note_id, title, text, source, tags, specific_schedule, priority)
        run_hooks("user-note-edited")

        self.reject()

    def reject(self):
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

        self.tree.setColumnCount(1)
        self.tree.setIconSize(QSize(0,0))
        self.build_tree(get_all_tags_as_hierarchy(False))
        self.tree.itemClicked.connect(self.tree_item_clicked)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setMinimumHeight(150)
        self.tree.setMinimumWidth(220)
        self.tree.setHeaderHidden(True)

        self.highlight_map      = {
            "ob": [0,0,0,232,151,0],
            "rw": [255, 255, 255, 209, 46, 50],
            "yb": [0,0,0,235, 239, 69],
            "bw": [255,255,255,2, 119,189],
            "gb": [255,255,255,34,177,76]
        }
         
        recently_used_tags      = get_recently_used_tags()
        
        config                  = mw.addonManager.getConfig(__name__)
        tag_bg                  = config["styling"]["general"]["tagBackgroundColor"]
        tag_fg                  = config["styling"]["general"]["tagForegroundColor"]

        self.recent_tbl         = QWidget()
        self.recent_tbl.setObjectName("recentDisp")
        self.recent_tbl.setStyleSheet("background-color: transparent;")
        bs = f"""
            background-color: {tag_bg};
            color: {tag_fg};
            padding: 2px 3px 2px 3px;
            border-radius: 5px;
        """
        lo = FlowLayout()
        self.recent_tbl.setLayout(lo)
        for ix, t in enumerate(recently_used_tags):
            btn = QPushButton(t)
            btn.setStyleSheet(bs)
            btn.clicked.connect(functools.partial(self.add_tag, t))
            lo.addWidget(btn)
        self.recent_tbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.recent_tbl.setMaximumHeight(100)

        queue_len = len(parent.priority_list)
        schedule = None if self.parent.note is None else self.parent.note.reminder
        self.slider = QtPrioritySlider(self.parent.priority, schedule=schedule)

        self.layout = QHBoxLayout()
        vbox_left = QVBoxLayout()

        tag_lbl = QLabel()
        tag_icn = QPixmap(utility.misc.get_web_folder_path() + "icons/icon-tag-24.png").scaled(14,14)
        tag_lbl.setPixmap(tag_icn)

        tag_hb = QHBoxLayout()
        tag_hb.setAlignment(Qt.AlignLeft)
        tag_hb.addWidget(tag_lbl)
        tag_hb.addWidget(QLabel("Tags (Click to Add)"))

        vbox_left.addLayout(tag_hb)

        vbox_left.addWidget(self.tree)
        self.all_tags_cb = QCheckBox("Show All Tags")
        self.all_tags_cb.stateChanged.connect(self.tag_cb_changed)
        vbox_left.addWidget(self.all_tags_cb)
        if len(recently_used_tags) > 0:
            tag_lbl1 = QLabel()
            tag_lbl1.setPixmap(tag_icn)

            tag_hb1 = QHBoxLayout()
            tag_hb1.setAlignment(Qt.AlignLeft)
            tag_hb1.addWidget(tag_lbl1)
            tag_hb1.addWidget(QLabel("Recent (Click to Add)"))
            vbox_left.addLayout(tag_hb1)
            qs = QScrollArea()
            qs.setStyleSheet("""
                QScrollArea { background-color: transparent; } 
            """)
            qs.setFrameShape(QFrame.NoFrame)
            qs.setWidgetResizable(True)
           
            qs.setWidget(self.recent_tbl)
            vbox_left.addWidget(qs)


        vbox_left.addWidget(self.slider)
        vbox_left.setContentsMargins(0,0,0,0)
        self.left_pane = QWidget()
        self.left_pane.setLayout(vbox_left)
        self.layout.addWidget(self.left_pane, 7)

        hbox = QHBoxLayout()

        self.toggle_btn = QPushButton("<")
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

        text_lbl = QLabel("Text")
        text_lbl.setToolTip("Text may contain HTML (some tags and inline styles may be removed).")
        self.text = QTextEdit()
        f = self.text.font()
        f.setPointSize(12)
        self.text.setFont(f)
        self.text.setMinimumHeight(380)
        self.text.setMinimumWidth(470)
        self.text.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding)
        self.text.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.text.setLineWidth(2)
        self.text.cursorPositionChanged.connect(self.on_text_cursor_change)
        if hasattr(self.text, "setTabStopDistance"):
            self.text.setTabStopDistance(QFontMetricsF(f).horizontalAdvance(' ') * 4) 
        t_h = QHBoxLayout()
        t_h.addWidget(text_lbl)

        self.tb = QToolBar("Format")
        self.tb.setStyleSheet("background-color: transparent; border: 0px;")

        self.tb.setHidden(False)
        self.tb.setOrientation(Qt.Horizontal)
        self.tb.setIconSize(QSize(12, 12))

        self.vtb = QToolBar("Highlight")
        self.vtb.setStyleSheet("background-color: transparent; border: 0px;")
        self.vtb.setOrientation(Qt.Vertical)
        self.vtb.setIconSize(QSize(16, 16))

         
        self.orange_black = self.vtb.addAction(QIcon(web_path + "icons/icon-orange-black.png"), "Highlight 1")
        self.orange_black.triggered.connect(self.on_highlight_ob_clicked)

        self.red_white = self.vtb.addAction(QIcon(web_path + "icons/icon-red-white.png"), "Highlight 2")
        self.red_white.triggered.connect(self.on_highlight_rw_clicked)

        self.yellow_black = self.vtb.addAction(QIcon(web_path + "icons/icon-yellow-black.png"), "Highlight 3")
        self.yellow_black.triggered.connect(self.on_highlight_yb_clicked)

        self.blue_white = self.vtb.addAction(QIcon(web_path + "icons/icon-blue-white.png"), "Highlight 4")
        self.blue_white.triggered.connect(self.on_highlight_bw_clicked)

        self.green_black = self.vtb.addAction(QIcon(web_path + "icons/icon-green-black.png"), "Highlight 5")
        self.green_black.triggered.connect(self.on_highlight_gb_clicked)

        bold =  self.tb.addAction("b")
        f = bold.font()
        f.setBold(True)
        bold.setFont(f)
        bold.setCheckable(True)
        bold.triggered.connect(self.on_bold_clicked)
        bold.setShortcut(QKeySequence("Ctrl+b"))

        italic = self.tb.addAction("i")
        italic.setCheckable(True)
        italic.triggered.connect(self.on_italic_clicked)
        f = italic.font()
        f.setItalic(True)
        italic.setFont(f)
        italic.setShortcut(QKeySequence("Ctrl+i"))

        underline = self.tb.addAction("u")
        underline.setCheckable(True)
        underline.triggered.connect(self.on_underline_clicked)
        f = underline.font()
        f.setUnderline(True)
        underline.setFont(f)
        underline.setShortcut(QKeySequence("Ctrl+u"))

        strike = self.tb.addAction("s")
        strike.setCheckable(True)
        strike.triggered.connect(self.on_strike_clicked)
        f = strike.font()
        f.setStrikeOut(True)
        strike.setFont(f)

        color = self.tb.addAction(QIcon(web_path + "icons/icon-color-change.png"), "Foreground Color")
        color.triggered.connect(self.on_color_clicked)

        bullet_list = self.tb.addAction("BL")
        bullet_list.setToolTip("Bullet List")
        bullet_list.triggered.connect(self.on_bullet_list_clicked)

        numbered_list = self.tb.addAction("NL")
        numbered_list.setToolTip("Numbered List")
        numbered_list.triggered.connect(self.on_numbered_list_clicked)

        clean_btn = QToolButton()
        clean_btn.setText("Clean Text  ")
        clean_btn.setPopupMode(QToolButton.InstantPopup)
        clean_btn.setFocusPolicy(Qt.NoFocus)
        clean_menu = QMenu(clean_btn)
        if self.parent.dark_mode_used:
            clean_menu.setStyleSheet("""
                QMenu { background: #3a3a3a; color: lightgrey; }
                QMenu:item:selected { background: #aaa; color: white; }
            """)
        else:
            clean_menu.setStyleSheet("""
                QMenu { background: white; color: black; }
                QMenu:item:selected { background: #2496dc; color: white; }
            """)
        
        header_a = clean_menu.addAction("Remove Headers")
        header_a.triggered.connect(self.on_remove_headers_clicked)
        header_a1 = clean_menu.addAction("Remove All Bold Formatting")
        header_a1.triggered.connect(self.on_remove_bold_clicked)
        header_a2 = clean_menu.addAction("Convert Images to Base64")
        header_a2.triggered.connect(self.on_convert_images_clicked)
        header_a3 = clean_menu.addAction("Remove All Colors")
        header_a3.triggered.connect(self.on_remove_colors_clicked)
        clean_btn.setMenu(clean_menu)
        self.tb.addWidget(clean_btn)

        t_h.addWidget(self.tb)

        vbox.addLayout(t_h)
        text_h = QHBoxLayout()
        text_h.addWidget(self.text)
        text_h.addWidget(self.vtb)
        vbox.addLayout(text_h)

        self.plain_text_cb = QCheckBox("Save as Plain Text")
        self.line_status = QLabel("Ln: 0, Col: 0")
        p_hb = QHBoxLayout()
        p_hb.addSpacing(5)
        p_hb.addWidget(self.line_status)
        p_hb.addStretch(1)
        p_hb.addWidget(self.plain_text_cb)
        
        url_btn = QPushButton(u" Fetch from URL ... ")
        url_btn.clicked.connect(self.on_url_clicked)
        p_hb.addWidget(url_btn)
        p_hb.addSpacing(35)
        vbox.addLayout(p_hb)

        source_lbl          = QLabel("Source")
        self.source         = QLineEdit()
        source_hb           = QHBoxLayout()
        source_hb.addWidget(self.source)
        if self.parent.source_prefill is not None:
            self.source.setText(self.parent.source_prefill.replace("\\", "/"))
        pdf_btn             = QPushButton("PDF")
        pdf_btn.clicked.connect(self.on_pdf_clicked)
        source_hb.addWidget(pdf_btn)
        pdf_from_url_btn    = QPushButton("PDF from Webpage")
        pdf_from_url_btn.clicked.connect(self.on_pdf_from_url_clicked)
        source_hb.addWidget(pdf_from_url_btn)

        vbox.addWidget(source_lbl)
        vbox.addLayout(source_hb)

        if self.parent.text_prefill is not None:
            self.text.setText(self.parent.text_prefill)

        btn_styles = """
        QPushButton#q_1 { padding-left: 20px; padding-right: 20px; }
        QPushButton#q_2 { padding-left: 17px; padding-right: 17px; }
        QPushButton#q_3 { padding-left: 13px; padding-right: 13px; }
        QPushButton#q_4 { padding-left: 8px; padding-right: 8px; }
        QPushButton#q_5 { padding-left: 2px; padding-right: 2px; }
        QPushButton#q_6 { padding-left: 0px; padding-right: 0px; }
        QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_3,QPushButton:hover#q_4,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: lightblue; }
        """
     
        styles = """
            QPushButton#q_1,QPushButton#q_2,QPushButton#q_3,QPushButton#q_4,QPushButton#q_5,QPushButton#q_6 { border-radius: 5px; }
            %s 
    
            QTextEdit { border-radius: 5px; border: 1px solid #717378;  padding: 3px; }
            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}
            #recentDisp { margin: 5px; }

        """ % btn_styles

        if parent.dark_mode_used:
            styles += """
                QToolTip { background: #3a3a3a; color: lightgrey; }
            """
        else:
            styles += """
                QToolTip { color: black; background-color: white; }
            """

        #     styles += """
        #         QPushButton#q_1,QPushButton#q_2,QPushButton#q_22,QPushButton#q_3,QPushButton#q_33,QPushButton#q_4,QPushButton#q_44,QPushButton#q_5,QPushButton#q_6 { color: beige; }
        #         QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_22,QPushButton:hover#q_3,QPushButton:hover#q_33,QPushButton:hover#q_4,QPushButton:hover#q_44,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: grey; border-color: blue; color: white; }
        #     """

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
        vbox.addWidget(self.tag)
        if self.parent.tag_prefill is not None:
            self.tag.setText(self.parent.tag_prefill)

        vbox.setAlignment(Qt.AlignTop)
        vbox.addSpacing(10)
        vbox.addLayout(hbox)
        self.layout.addSpacing(5)
        self.layout.addLayout(vbox, 73)
        self.setLayout(self.layout)
        if parent.note is not None:
            self.tag.setText(parent.note.tags.lstrip())
            self.title.setText(parent.note.title)
            self.text.setHtml(parent.note.text)
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
            ti.setData(0, 1, QVariant(prefix + t))
            prefix_c = prefix + t + "::"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def tree_item_clicked(self, item, col):
        tag = item.data(0, 1)
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
        self.tree.clear()
        tmap = None
        if state == Qt.Checked:
            tmap = get_all_tags_as_hierarchy(include_anki_tags = True)
        else:
            tmap = get_all_tags_as_hierarchy(include_anki_tags = False)
        self.build_tree(tmap)

    def build_tree(self, tmap):
        for t, children in tmap.items():
            ti = QTreeWidgetItem([t])
            ti.setData(0, 1, QVariant(t))
            ti.addChildren(self._add_to_tree(children, t + "::"))
            self.tree.addTopLevelItem(ti)

    def toggle_left_pane(self):
        self.left_pane.setVisible(not self.left_pane.isVisible())
        if self.left_pane.isVisible():
            self.toggle_btn.setText("<")
        else:
            self.toggle_btn.setText(">")

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
                text = import_webpage(dialog.chosen_url)
                if text is None:
                    tooltip("Failed to fetch text from page.")
                else:
                    self.text.setHtml(text)

    def on_italic_clicked(self):
        self.text.setFontItalic(not self.text.fontItalic())

    def on_bold_clicked(self):
        self.text.setFontWeight(QFont.Normal if self.text.fontWeight() > QFont.Normal else QFont.Bold)

    def on_remove_headers_clicked(self):
        html = self.text.toHtml()
        html = utility.text.remove_headers(html)
        self.text.setHtml(html)

    def on_remove_bold_clicked(self):
        html = self.text.toHtml()
        html = utility.text.remove_all_bold_formatting(html)
        self.text.setHtml(html)

    def on_bullet_list_clicked(self):
        cursor = self.text.textCursor()
        cursor.createList(QTextListFormat.ListDisc)

    def on_numbered_list_clicked(self):
        cursor = self.text.textCursor()
        cursor.createList(QTextListFormat.ListDecimal)

    def on_underline_clicked(self):
        state = self.text.fontUnderline()
        self.text.setFontUnderline(not state)

    def on_strike_clicked(self):
        format = self.text.currentCharFormat()
        format.setFontStrikeOut(not format.fontStrikeOut())
        self.text.setCurrentCharFormat(format)

    def on_color_clicked(self):
        color = QColorDialog.getColor()
        self.text.setTextColor(color)

    def highlight(self, type):
        self.save_original_bg_and_fg()
        if self.text.textCursor().selectedText() is not None and len(self.text.textCursor().selectedText()) > 0:
            c = self.get_color_at_selection()
            cursor = self.text.textCursor()
            fmt = QTextCharFormat()
            colors = self.highlight_map[type]
            if (c[0] == self.original_fg or (c[0] == QColor(0,0,0) and self.original_fg ==  QColor(255,255,255))) and (c[1] == self.original_bg or c[1] == QColor(0, 0, 0) or c[1] == QColor(255,255,255)):
                fmt.setBackground(QBrush(QColor(colors[3], colors[4], colors[5])))
                fmt.setForeground(QBrush(QColor(colors[0], colors[1], colors[2])))
            else:
                fmt.setBackground(QBrush(self.original_bg))
                fmt.setForeground(QBrush(self.original_fg))
            cursor.mergeCharFormat(fmt)
            cursor.clearSelection()
            self.text.setTextCursor(cursor)
            self.restore_original_bg_and_fg()

    def on_highlight_ob_clicked(self):
        self.highlight("ob")

    def on_highlight_rw_clicked(self):
        self.highlight("rw")

    def on_highlight_yb_clicked(self):
        self.highlight("yb")

    def on_highlight_bw_clicked(self):
        self.highlight("bw")

    def on_highlight_gb_clicked(self):
        self.highlight("gb")

    def get_color_at_selection(self):
        fg = self.text.textCursor().charFormat().foreground().color()
        #fg = self.text.textColor()
        # bg = self.text.textCursor().charFormat().background().color()
        bg = self.text.textBackgroundColor()
        return (fg, bg)

    def save_original_bg_and_fg(self):
        if self.original_bg is None:
            self.original_bg = self.text.palette().color(QPalette.Base)

            self.original_fg = self.text.palette().color(QPalette.Foreground)
            #self.original_fg = self.text.textColor()

    def restore_original_bg_and_fg(self):
        self.text.setTextBackgroundColor(self.original_bg)
        self.text.setTextColor(self.original_fg)

    def on_text_cursor_change(self):
        cursor = self.text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()
        self.line_status.setText("Ln: {}, Col: {}".format(line,col))

    def on_remove_colors_clicked(self):
        html = self.text.toHtml()
        html = utility.text.remove_colors(html)
        self.text.setHtml(html)

    def on_convert_images_clicked(self):
        html = self.text.toHtml()
        images_contained = utility.text.find_all_images(html)
        if images_contained is None:
            return
        for image_tag in images_contained:
            #ignore images already in base64
            if re.findall("src=['\"] *data:image/(png|jpe?g);[^;]{0,50};base64,", image_tag, flags=re.IGNORECASE):
                continue
            url = re.search("src=(\"[^\"]+\"|'[^']+')", image_tag, flags=re.IGNORECASE).group(1)[1:-1]
            try:
                base64 = utility.misc.url_to_base64(url)
                if base64 is None or len(base64) == 0:
                    return
                ending = ""
                if url.lower().endswith("jpg") or url.lower().endswith("jpeg"):
                    ending = "jpeg"
                elif url.lower().endswith("png"):
                    ending = "png"
                elif "jpg" in url.lower() or "jpeg" in url.lower():
                    ending = "jpeg"
                elif "png" in url.lower():
                    ending = "png"
                else:
                    ending = "jpeg"
                html = html.replace(image_tag, "<img src=\"data:image/%s;base64,%s\">" % (ending,base64))
            except:
                continue
        self.text.setHtml(html)


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
        tag_bg = config["styling"]["general"]["tagBackgroundColor"]
        tag_fg = config["styling"]["general"]["tagForegroundColor"]

        for c, pitem in enumerate(priority_list):

            # build display text
            text = pitem.title if pitem.title is not None and len(pitem.title.strip()) > 0 else "Untitled"
            text = "<b>%s</b>" % text

            tags = pitem.tags
            if tags is not None and len(tags.strip()) > 0:
                tag_sep = "&nbsp;</span> <span style='color: %s; background-color: %s; margin-right: 5px; border-radius: 5px;'>&nbsp;" % (tag_fg, tag_bg)
                tags = "<span style='color: %s; background-color: %s; margin-right: 5px; border-radius: 5px;'>&nbsp;%s&nbsp;</span>" % (tag_fg, tag_bg, tag_sep.join([t for t in tags.split(" ") if len(t) > 0]))

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
            rem_btn = QPushButton("Remove")
            if self.parent.dark_mode_used:
                rem_btn.setStyleSheet("border: 1px solid darkgrey; border-style: outset; font-size: 10px; background: #313233; color: white; margin: 0px; padding: 3px;")
            else:
                rem_btn.setStyleSheet("border: 1px solid black; border-style: outset; font-size: 10px; background: white; color: black; margin: 0px; padding: 3px;")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setMinimumHeight(18)
            rem_btn.clicked.connect(functools.partial(self.on_remove_clicked, priority_list[r].id))

            h_l = QHBoxLayout()
            h_l.addWidget(rem_btn)
            cell_widget = QWidget()
            cell_widget.setLayout(h_l)
            self.t_view.setIndexWidget(self.t_view.model().index(r,2), cell_widget)

    def on_shuffle_btn_clicked(self):
        priority_list = _get_priority_list()
        if priority_list is None or len(priority_list) == 0:
            return
        random.shuffle(priority_list)
        model = self.get_model(priority_list)
        ids = [p.id for p in priority_list]
        #persist reordering to db
        set_priority_list(ids)
        self.t_view.setModel(model)
        self.set_remove_btns(priority_list)

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
        
        self.qu_examples = [QLineEdit() for ix in range(0, 13)]
        for le in self.qu_examples:
            self.layout.addWidget(le)

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
            set_priority_list(ids)

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
