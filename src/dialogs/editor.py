from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
import functools
import re
import random
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from anki.lang import _
from ..notes import *
from ..notes import _get_priority_list
from ..hooks import run_hooks
import utility.text
import utility.misc
from ..web.web import update_reading_bottom_bar

def openEditor(mw, nid):
    note = mw.col.getNote(nid)
    dialog = EditDialog(mw, note)


class EditDialog(QDialog):

    def __init__(self, mw, note):
        QDialog.__init__(self, None, Qt.Window)
        mw.setupDialogGC(self)
        self.mw = mw
        self.form = aqt.forms.editcurrent.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(_("Edit Note"))
        self.setMinimumHeight(400)
        self.setMinimumWidth(500)
        self.resize(500, 700)
        self.form.buttonBox.button(QDialogButtonBox.Close).setShortcut(QKeySequence("Ctrl+Return"))
        self.editor = aqt.editor.Editor(self.mw, self.form.fieldsArea, self)
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
    """
    The editor window for non-anki notes.
    Has a text field and a tag field.
    """
    def __init__(self, parent, note_id = None, add_only = False, read_note_id = None, tag_prefill = None, source_prefill = None):
        self.note_id = note_id
        self.add_only = add_only
        self.read_note_id = read_note_id
        self.tag_prefill = tag_prefill
        self.source_prefill = source_prefill
        try:
            self.dark_mode_used = utility.misc.dark_mode_is_used(mw.addonManager.getConfig(__name__))
        except Exception as err:
            self.dark_mode_used = False

        if self.note_id is not None:
            self.note = get_note(note_id)
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        #self.mw.setupDialogGC(self)
        #self.setWindowModality(Qt.WindowModal)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setup_ui()



    def setup_ui(self):

        if self.note_id is not None:
            self.save = QPushButton("\u2714 Save")
            self.setWindowTitle('Edit Note')
            self.save.clicked.connect(self.on_update_clicked)
        else:
            self.save = QPushButton("\u2714 Create")
            self.setWindowTitle('New Note (Ctrl/Cmd + Shift + N)')
            self.save.clicked.connect(self.on_create_clicked)
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
        # tabs.addTab(self.browse_tab, "Browse")
        layout_main = QVBoxLayout()
        layout_main.addWidget(self.tabs)
        self.setLayout(layout_main)

        styles = ""
        if self.dark_mode_used:
            styles += """
                QTabBar {
                background: #222;
                color: #666;
                border-radius: 0;
                border: 2px solid #222;
                }
                 QTabWidget::pane {
                border-color: black;
                color: #666;
                border-radius: 0;
                border: 2px solid #222;
                }
                QTabBar::tab:top {
                margin: 1px 1px 0 0;
                padding: 4px 8px;
                border-bottom: 3px solid transparent;
                }

                QTabBar::tab:selected {
                color: white;
                border: 0;
                }

                QTabBar::tab:top:hover {
                border-bottom: 3px solid #444;
                }
                QTabBar::tab:top:selected {
                border-bottom: 3px solid #1086e2;
                }

                QTabBar::tab:hover,
                QTabBar::tab:focus {

                }
            """
        self.setStyleSheet(styles)
        self.create_tab.title.setFocus()
        self.exec_()



    def on_create_clicked(self):
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

        source = self.create_tab.source.text()
        tags = self.create_tab.tag.text()
        queue_schedule = self.create_tab.queue_schedule

        # don't allow for completely empty fields
        if len(title.strip()) + len(text.strip()) == 0:
            return

        create_note(title, text, source, tags, None, "", queue_schedule)
        #aqt.dialogs.close("UserNoteEditor")
        run_hooks("user-note-created")
        self.reject()

        # if reading modal is open, we might have to update the bottom bar
        if self.read_note_id is not None:
            update_reading_bottom_bar(self.read_note_id)

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
        source = self.create_tab.source.text()
        tags = self.create_tab.tag.text()
        queue_schedule = self.create_tab.queue_schedule
        update_note(self.note_id, title, text, source, tags, "", queue_schedule)
        run_hooks("user-note-created")
        self.reject()


    def reject(self):
        if not self.add_only:
            self.priority_tab.t_view.setModel(None)
        QDialog.reject(self)

    def accept(self):
        self.reject()


class CreateTab(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.queue_schedule = 1
        self.parent = parent
        tmap = get_all_tags_as_hierarchy(False)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.build_tree(tmap)
        self.tree.itemClicked.connect(self.tree_item_clicked)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree.setMinimumHeight(150)
        self.tree.setHeaderHidden(True)
        self.original_bg = None
        self.original_fg = None

        self.highlight_map = {
            "ob": [0,0,0,232,151,0],
            "rw": [255, 255, 255, 209, 46, 50],
            "yb": [0,0,0,235, 239, 69],
            "bw": [255,255,255,2, 119,189],
            "gb": [255,255,255,34,177,76]
        }


        recently_used_tags = get_recently_used_tags()
        self.recent_tree = QTreeWidget()
        self.recent_tree.setColumnCount(1)
        self.recent_tree.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.recent_tree.setMaximumHeight(100)
        self.recent_tree.setHeaderHidden(True)

        for t in recently_used_tags:
            ti = QTreeWidgetItem([t])
            ti.setData(0, 1, QVariant(t))
            self.recent_tree.addTopLevelItem(ti)
        self.recent_tree.itemClicked.connect(self.tree_item_clicked)

        self.queue_section = QGroupBox("Queue")
        ex_v = QVBoxLayout()
        queue_len = len(parent.priority_list)
        if parent.note_id is None:
            queue_lbl = QLabel("Add to Queue? (<b>%s</b> items)" % queue_len)
        else:
            #check if note has position (is in queue)
            if parent.note[10] is None or parent.note[10] < 0:
                queue_lbl = QLabel("<b>Not</b> in Queue (<b>%s</b> items)" % queue_len)
            else:
                queue_lbl = QLabel("Position: <b>%s</b> / <b>%s</b>" % (parent.note[10] + 1, queue_len))

        queue_lbl.setAlignment(Qt.AlignCenter)
        ex_v.addWidget(queue_lbl, Qt.AlignCenter)
        ex_v.addSpacing(5)

        if parent.note_id is None:
            self.q_lbl_1 = QPushButton("Don't Add to Queue")
        else:
            if parent.note[10] is None or parent.note[10] < 0:
                self.q_lbl_1 = QPushButton("Don't Add to Queue")
            else:
                self.q_lbl_1 = QPushButton("Keep Position in Queue")

        if parent.dark_mode_used:
            btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
            btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: lightgrey; font-weight: bold; } QPushButton:hover { border: 2px solid #2496dc; color: black; }"
        else:
            btn_style = "QPushButton { border: 2px solid lightgrey; padding: 3px; color: grey; }"
            btn_style_active = "QPushButton { border: 2px solid #2496dc; padding: 3px; color: black; font-weight: bold;}"


        self.q_lbl_1.setObjectName("q_1")
        self.q_lbl_1.setFlat(True)
        self.q_lbl_1.setStyleSheet(btn_style_active)
        self.q_lbl_1.clicked.connect(lambda: self.queue_selected(1))
        ex_v.addWidget(self.q_lbl_1)

        ex_v.addSpacing(5)
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.HLine)
        line_sep.setFrameShadow(QFrame.Sunken)
        ex_v.addWidget(line_sep)
        ex_v.addSpacing(5)

        self.q_lbl_2 = QPushButton("Head")
        self.q_lbl_2.setObjectName("q_2")
        self.q_lbl_2.setFlat(True)
        self.q_lbl_2.setStyleSheet(btn_style)
        self.q_lbl_2.clicked.connect(lambda: self.queue_selected(2))
        ex_v.addWidget(self.q_lbl_2)

        self.q_lbl_22 = QPushButton("[Rnd]")
        self.q_lbl_22.setObjectName("q_22")
        self.q_lbl_22.setFlat(True)
        self.q_lbl_22.setStyleSheet(btn_style)
        self.q_lbl_22.clicked.connect(lambda: self.queue_selected(7))
        ex_v.addWidget(self.q_lbl_22)


        self.q_lbl_3 = QPushButton("End of first 3rd")
        self.q_lbl_3.setObjectName("q_3")
        self.q_lbl_3.setFlat(True)
        self.q_lbl_3.setStyleSheet(btn_style)
        self.q_lbl_3.clicked.connect(lambda: self.queue_selected(3))
        ex_v.addWidget(self.q_lbl_3)

        self.q_lbl_33 = QPushButton("[Rnd]")
        self.q_lbl_33.setObjectName("q_33")
        self.q_lbl_33.setFlat(True)
        self.q_lbl_33.setStyleSheet(btn_style)
        self.q_lbl_33.clicked.connect(lambda: self.queue_selected(8))
        ex_v.addWidget(self.q_lbl_33)



        self.q_lbl_4 = QPushButton("End of second 3rd")
        self.q_lbl_4.setObjectName("q_4")
        self.q_lbl_4.setFlat(True)
        self.q_lbl_4.setStyleSheet(btn_style)
        self.q_lbl_4.clicked.connect(lambda: self.queue_selected(4))
        ex_v.addWidget(self.q_lbl_4)

        self.q_lbl_44 = QPushButton("[Rnd]")
        self.q_lbl_44.setObjectName("q_44")
        self.q_lbl_44.setFlat(True)
        self.q_lbl_44.setStyleSheet(btn_style)
        self.q_lbl_44.clicked.connect(lambda: self.queue_selected(9))
        ex_v.addWidget(self.q_lbl_44)

        self.q_lbl_5 = QPushButton("End")
        self.q_lbl_5.setObjectName("q_5")
        self.q_lbl_5.setFlat(True)
        self.q_lbl_5.setStyleSheet(btn_style)
        self.q_lbl_5.clicked.connect(lambda: self.queue_selected(5))
        ex_v.addWidget(self.q_lbl_5)

        self.q_lbl_6 = QPushButton("\u2685 Random")
        self.q_lbl_6.setObjectName("q_6")
        self.q_lbl_6.setFlat(True)
        self.q_lbl_6.setStyleSheet(btn_style)
        self.q_lbl_6.clicked.connect(lambda: self.queue_selected(6))
        ex_v.addWidget(self.q_lbl_6)

        self.queue_section.setLayout(ex_v)

        self.layout = QHBoxLayout()
        vbox_left = QVBoxLayout()

        tag_lbl = QLabel()
        tag_icn = QPixmap(utility.misc.get_web_folder_path() + "tag-icon.png").scaled(14,14)
        tag_lbl.setPixmap(tag_icn);

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
            tag_lbl1.setPixmap(tag_icn);

            tag_hb1 = QHBoxLayout()
            tag_hb1.setAlignment(Qt.AlignLeft)
            tag_hb1.addWidget(tag_lbl1)
            tag_hb1.addWidget(QLabel("Recent (Click to Add)"))
            vbox_left.addLayout(tag_hb1)

            vbox_left.addWidget(self.recent_tree)

        vbox_left.addWidget(self.queue_section)


        self.layout.addLayout(vbox_left, 27)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(parent.save)
        hbox.addWidget(parent.cancel)

        vbox = QVBoxLayout()
        # vbox.addStretch(1)

        title_lbl = QLabel("Title")
        self.title = QLineEdit()
        f = self.title.font()
        f.setPointSize(14)
        self.title.setFont(f)
        vbox.addWidget(title_lbl)
        vbox.addWidget(self.title)

        text_lbl = QLabel("Text")
        text_lbl.setToolTip("Text may contain HTML (some tags and inline styles may be removed), \nimages in the HTML will only be visible when connected to the internet.")
        self.text = QTextEdit()
        f = self.text.font()
        f.setPointSize(12)
        self.text.setFont(f)
        self.text.setMinimumHeight(380)
        self.text.setMinimumWidth(450)
        self.text.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding)
        self.text.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.text.setLineWidth(2)
        self.text.cursorPositionChanged.connect(self.on_text_cursor_change)

        t_h = QHBoxLayout()
        t_h.addWidget(text_lbl)

        self.tb = QToolBar("Format")
        self.tb.setHidden(False)
        self.tb.setOrientation(Qt.Horizontal)
        self.tb.setIconSize(QSize(12, 12))

        self.vtb = QToolBar("Highlight")
        self.vtb.setOrientation(Qt.Vertical)
        self.vtb.setIconSize(QSize(16, 16))

        self.orange_black = self.vtb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-orange-black.png"), "Highlight 1")
        self.orange_black.triggered.connect(self.on_highlight_ob_clicked)

        self.red_white = self.vtb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-red-white.png"), "Highlight 2")
        self.red_white.triggered.connect(self.on_highlight_rw_clicked)

        self.yellow_black = self.vtb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-yellow-black.png"), "Highlight 3")
        self.yellow_black.triggered.connect(self.on_highlight_yb_clicked)

        self.blue_white = self.vtb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-blue-white.png"), "Highlight 4")
        self.blue_white.triggered.connect(self.on_highlight_bw_clicked)

        self.green_black = self.vtb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-green-black.png"), "Highlight 5")
        self.green_black.triggered.connect(self.on_highlight_gb_clicked)


        bold =  self.tb.addAction("b")
        f = bold.font()
        f.setBold(True)
        bold.setFont(f)
        bold.setCheckable(True)
        bold.triggered.connect(self.on_bold_clicked)

        italic = self.tb.addAction("i")
        italic.setCheckable(True)
        italic.triggered.connect(self.on_italic_clicked)
        f = italic.font()
        f.setItalic(True)
        italic.setFont(f)

        underline = self.tb.addAction("u")
        underline.setCheckable(True)
        underline.triggered.connect(self.on_underline_clicked)
        f = underline.font()
        f.setUnderline(True)
        underline.setFont(f)

        strike = self.tb.addAction("s")
        strike.setCheckable(True)
        strike.triggered.connect(self.on_strike_clicked)
        f = strike.font()
        f.setStrikeOut(True)
        strike.setFont(f)

        color = self.tb.addAction(QIcon(utility.misc.get_web_folder_path() + "icon-color-change.png"), "Foreground Color")
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
        p_hb.addSpacing(35)
        vbox.addLayout(p_hb)

        source_lbl = QLabel("Source")
        self.source = QLineEdit()
        source_hb = QHBoxLayout()
        source_hb.addWidget(self.source)
        if self.parent.source_prefill is not None:
            self.source.setText(self.parent.source_prefill.replace("\\", "/"))
        pdf_btn = QPushButton("PDF")
        pdf_btn.clicked.connect(self.on_pdf_clicked)
        source_hb.addWidget(pdf_btn)

        vbox.addWidget(source_lbl)
        vbox.addLayout(source_hb)

        styles = """
            QPushButton#q_1,QPushButton#q_2,QPushButton#q_22,QPushButton#q_3,QPushButton#q_33,QPushButton#q_4,QPushButton#q_44,QPushButton#q_5,QPushButton#q_6 { border-radius: 5px; }
            QPushButton#q_1 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_2 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_22 { margin-left: 70px; margin-right: 70px; }
            QPushButton#q_3 { margin-left: 30px; margin-right: 30px; }
            QPushButton#q_33 { margin-left: 70px; margin-right: 70px; }
            QPushButton#q_4 { margin-left: 30px; margin-right: 30px; }
            QPushButton#q_44 { margin-left: 70px; margin-right: 70px; }
            QPushButton#q_5 { margin-left: 10px; margin-right: 10px; }
            QPushButton#q_6 { margin-left: 10px; margin-right: 10px; }


            QPushButton:hover#q_1,QPushButton:hover#q_2,QPushButton:hover#q_5,QPushButton:hover#q_6 { background-color: lightblue; margin-left: 7px; margin-right: 7px; }
            QPushButton:hover#q_22,QPushButton:hover#q_33,QPushButton:hover#q_44 { background-color: lightblue; margin-left: 67px; margin-right: 67px; }
            QPushButton:hover#q_3,QPushButton:hover#q_4 { background-color: lightblue; margin-left: 27px; margin-right: 27px; }

            QTextEdit { border-radius: 5px; border: 1px solid #717378;  padding: 3px; }
            QLineEdit { border-radius: 5px; border: 1px solid #717378;  padding: 2px;}

        """

        # if parent.dark_mode_used:
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
        vbox.addLayout(hbox)
        self.layout.addSpacing(5)
        self.layout.addLayout(vbox, 73)
        self.setLayout(self.layout)
        if parent.note_id is not None:
            n = get_note(parent.note_id)
            if n is not None:
                self.tag.setText(n[4])
                self.title.setText(n[1])
                self.text.setHtml(n[2])
                self.source.setText(n[3])


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

    def queue_selected(self, queue_schedule):
        for lbl in [self.q_lbl_1, self.q_lbl_2,  self.q_lbl_22,  self.q_lbl_3,  self.q_lbl_33,  self.q_lbl_4, self.q_lbl_44, self.q_lbl_5, self.q_lbl_6]:
            if self.parent.dark_mode_used:
                lbl.setStyleSheet("QPushButton { border: 2px solid lightgrey; padding: 3px; color: lightgrey; } QPushButton:hover { border: 2px solid #2496dc; color: black; }")
            else:
                lbl.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey; font-weight: normal;")
        [self.q_lbl_1, self.q_lbl_2,  self.q_lbl_3, self.q_lbl_4, self.q_lbl_5, self.q_lbl_6, self.q_lbl_22, self.q_lbl_33, self.q_lbl_44][queue_schedule-1].setStyleSheet("border: 2px solid #2496dc; padding: 3px; font-weight: bold;")
        self.queue_schedule = queue_schedule


    def on_pdf_clicked(self):
        fname = QFileDialog.getOpenFileName(self, 'Pick a PDF', '',"PDF (*.pdf)")
        if fname is not None:
            self.source.setText(fname[0])

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
        html = remove_all_bold_formatting(html)
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
        self.parent = parent
        model = self.get_model(priority_list)
        self.t_view = QTableView()
        html_delegate = HTMLDelegate()
        self.t_view.setItemDelegateForColumn(0, html_delegate)
        self.t_view.setItemDelegateForColumn(1, html_delegate)
        self.t_view.setModel(model)

        self.set_remove_btns(priority_list)


        self.t_view.resizeColumnsToContents()
        self.t_view.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.t_view.setDragEnabled(True)
        self.t_view.setDropIndicatorShown(True)
        self.t_view.setAcceptDrops(True)
        self.t_view.viewport().setAcceptDrops(True)
        self.t_view.setDragDropOverwriteMode(False)

        self.t_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.t_view.setDefaultDropAction(Qt.MoveAction)
        if priority_list is not None and len(priority_list) > 0:
            self.t_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.t_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.t_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.t_view.verticalHeader().setSectionsMovable(False)
        self.t_view.setSelectionMode(QAbstractItemView.SingleSelection);

        self.vbox = QVBoxLayout()
        lbl = QLabel("Drag & Drop to reorder.\n'Remove' will only remove the item from the queue, not delete it.")
        self.vbox.addWidget(lbl)
        self.vbox.addWidget(self.t_view)

        bottom_box = QHBoxLayout()
        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.clicked.connect(self.on_shuffle_btn_clicked)
        bottom_box.addWidget(self.shuffle_btn)
        bottom_box.addStretch(1)
        self.vbox.addLayout(bottom_box)


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
                update_position(n_id, QueueSchedule.NOT_ADD)
                break

    def get_model(self, priority_list):
        model = PriorityListModel(self)

        config = mw.addonManager.getConfig(__name__)
        tag_bg = config["styling"]["general"]["tagBackgroundColor"]
        tag_fg = config["styling"]["general"]["tagForegroundColor"]

        for c, pitem in enumerate(priority_list):

            # build display text
            text = pitem[1] if pitem[1] is not None and len(pitem[1].strip()) > 0 else "Untitled"
            text = "<b>%s</b>" % text

            tags = pitem[4]
            if tags is not None and len(tags.strip()) > 0:
                tag_sep = "&nbsp;</span> <span style='color: %s; background-color: %s; margin-right: 5px; border-radius: 5px;'>&nbsp;" % (tag_fg, tag_bg)
                tags = "<span style='color: %s; background-color: %s; margin-right: 5px; border-radius: 5px;'>&nbsp;%s&nbsp;</span>" % (tag_fg, tag_bg, tag_sep.join([t for t in tags.split(" ") if len(t) > 0]))

            item = QStandardItem(text)
            item.setData(QVariant(pitem[0]))
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
                rem_btn.setStyleSheet("border: 1px solid black; border-style: outset; font-size: 10px; background: white; margin: 0px; padding: 3px;")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setMinimumHeight(18)
            rem_btn.clicked.connect(functools.partial(self.on_remove_clicked, priority_list[r][0]))

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
        ids = [p[0] for p in priority_list]
        #persist reordering to db
        set_priority_list(ids)
        self.t_view.setModel(model)
        self.set_remove_btns(priority_list)


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


class ExpandableSection(QWidget):
    def __init__(self, title="", parent=None):
        super(ExpandableSection, self).__init__(parent)

        self.toggle_button = QToolButton( text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QParallelAnimationGroup(self)

        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setFrameShape(QFrame.NoFrame)

        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation( QPropertyAnimation(self, b"minimumHeight"))
        self.toggle_animation.addAnimation( QPropertyAnimation(self, b"maximumHeight"))
        self.toggle_animation.addAnimation( QPropertyAnimation(self.content_area, b"maximumHeight"))

    @pyqtSlot()
    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(
            Qt.DownArrow if not checked else Qt.RightArrow
        )
        self.toggle_animation.setDirection(
            QAbstractAnimation.Forward
            if not checked
            else QAbstractAnimation.Backward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        collapsed_height = (
            self.sizeHint().height() - self.content_area.maximumHeight()
        )
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(500)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_animation.setDuration(500)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
