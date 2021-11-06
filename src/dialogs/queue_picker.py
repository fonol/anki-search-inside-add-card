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
from aqt.utils import tooltip, showInfo
import aqt
import random
import os
import copy
import functools
from .editor import NoteEditor
from .components import QtPrioritySlider, ClickableQWidget
from .priority_dialog import PriorityDialog
from .tag_assign_dialog import TagAssignDialog
from ..web.reading_modal import Reader
from ..notes import *
from ..notes import _get_priority_list
from ..internals import perf_time
from ..hooks import run_hooks, add_tmp_hook
from ..state import get_index
from ..config import get_config_value
from ..output import UI

import utility.text
import utility.misc
import utility.tags
import utility.date
import state



class QueuePicker(QDialog):
    """ Can be used to select a single note from the queue or to move pdf notes in/out of the queue. """

    icons_path          = None
    vline_icn           = None
    branch_more_icn     = None
    branch_end_icn      = None
    branch_closed_icn   = None
    branch_open_icn     = None

    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowCloseButtonHint)

        self.mw         = aqt.mw
        self.parent     = parent

        if QueuePicker.icons_path is None:
            QueuePicker.icons_path          = utility.misc.get_web_folder_path()+ "icons/"
            QueuePicker.vline_icn           = QueuePicker.icons_path + ('vline-night' if state.is_nightmode() else 'vline')
            QueuePicker.branch_more_icn     = QueuePicker.icons_path + ('branch-more-night' if state.is_nightmode() else 'branch-more')
            QueuePicker.branch_end_icn      = QueuePicker.icons_path + ('branch-end-night' if state.is_nightmode() else 'branch-end')
            QueuePicker.branch_closed_icn   = QueuePicker.icons_path + ('branch-closed-night' if state.is_nightmode() else 'branch-closed')
            QueuePicker.branch_open_icn     = QueuePicker.icons_path + ('branch-open-night' if state.is_nightmode() else 'branch-open')

        try:
            self.dark_mode_used = state.is_nightmode()
        except:
            self.dark_mode_used = False

        self.setup_ui()
        self.setWindowTitle("Queue Manager")
        self.showMaximized()
        # self.setWindowState(Qt.WindowFullScreen)

    def setup_ui(self):
        self.setLayout(QVBoxLayout())
        self.mode_sel = QComboBox()
        self.mode_sel.addItem("Queue", QVariant(1))
        self.mode_sel.addItem("Schedules", QVariant(2))
        self.mode_sel.currentIndexChanged.connect(self.mode_change)

        self.layout().addWidget(self.mode_sel)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignTop)

        self.queue_widget = QueueWidget(self)
        self.sched_widget = ScheduleMWidget(self)

        self.sched_widget.setVisible(False)

        self.layout().addWidget(self.queue_widget)
        self.layout().addWidget(self.sched_widget)

    def chosen_id(self):
        return self.queue_widget.chosen_id

    def mode_change(self, ix):
        if ix == 0:
            self.sched_widget.setVisible(False)
            self.queue_widget.setVisible(True)
        else:
            self.queue_widget.setVisible(False)
            self.sched_widget.setVisible(True)
            self.sched_widget.refresh()




class PDFsTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.vbox_right = QVBoxLayout()
        r_lbl = QLabel("PDF notes, not in Queue")
        r_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox_right.addWidget(r_lbl)
        self.search_bar_right = QLineEdit()
        self.search_bar_right.setPlaceholderText("Type to search")
        self.search_bar_right.textChanged.connect(self.search_enter)
        self.vbox_right.addWidget(self.search_bar_right)
        self.t_view_right = NoteList(self)
        self.vbox_right.addWidget(self.t_view_right)
        self.vbox_right.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.setLayout(self.vbox_right)

    def refresh(self):
        self.search_bar_right.clear()
        self.fill_list(get_pdf_notes_not_in_queue())

    def fill_list(self, db_list):
        self.t_view_right.fill(db_list)

    def search_enter(self):
        inp = self.search_bar_right.text()
        if inp is None or len(inp.strip()) == 0:
            self.fill_list(get_pdf_notes_not_in_queue())
            return
        res = find_unqueued_pdf_notes(inp)
        self.t_view_right.clear()
        self.fill_list(res)

class VideosTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.vbox_right = QVBoxLayout()
        r_lbl = QLabel("Video notes, not in Queue")
        r_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox_right.addWidget(r_lbl)
        self.search_bar_right = QLineEdit()
        self.search_bar_right.setPlaceholderText("Type to search")
        self.search_bar_right.textChanged.connect(self.search_enter)
        self.vbox_right.addWidget(self.search_bar_right)
        self.t_view_right = NoteList(self)
        self.vbox_right.addWidget(self.t_view_right)
        self.vbox_right.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(self.vbox_right)

    def refresh(self):
        self.search_bar_right.clear()
        self.fill_list(get_video_notes_not_in_queue())

    def fill_list(self, db_list):
        self.t_view_right.fill(db_list)

    def search_enter(self):
        inp = self.search_bar_right.text()
        if inp is None or len(inp.strip()) == 0:
            self.fill_list(get_video_notes_not_in_queue())
            return
        res = find_unqueued_video_notes(inp)
        self.fill_list(res)

class TextNotesTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.vbox_right         = QVBoxLayout()
        r_lbl                   = QLabel("Text notes, not in Queue")
        r_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox_right.addWidget(r_lbl)

        self.search_bar_right   = QLineEdit()
        self.search_bar_right.setPlaceholderText("Type to search")
        self.search_bar_right.textChanged.connect(self.search_enter)
        self.vbox_right.addWidget(self.search_bar_right)

        self.t_view_right       = NoteList(self)
        self.vbox_right.addWidget(self.t_view_right)

        self.vbox_right.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(self.vbox_right)

    def refresh(self):
        self.search_bar_right.clear()
        self.fill_list(get_text_notes_not_in_queue())

    def fill_list(self, db_list):
        self.t_view_right.fill(db_list)

    def search_enter(self):
        inp = self.search_bar_right.text()
        if inp is None or len(inp.strip()) == 0:
            self.fill_list(get_text_notes_not_in_queue())
            return
        res = find_unqueued_text_notes(inp)
        self.fill_list(res)

class FoldersTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()


    def setup_ui(self):
        self.vbox_left = QVBoxLayout()
        r_lbl = QLabel("Most Used Folders:")
        r_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vbox_left.addWidget(r_lbl)
        self.vbox_left.setAlignment(r_lbl, Qt.AlignmentFlag.AlignTop)

        self.folders_tree = QTreeWidget()
        self.folders_tree.setColumnCount(1)
        # self.folders_tree.setSizePolicy(QSizePolicy.M, QSizePolicy.Policy.Minimum)
        self.folders_tree.setHeaderHidden(True)
        self.folders_tree.setRootIsDecorated(False)
        self.folders_tree.setMaximumWidth(370)
        self.folders_tree.itemExpanded.connect(self.tree_exp)
        self.folders_tree.itemCollapsed.connect(self.tree_coll)

        self.folders_tree.setStyleSheet(f"""
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            border-image: url({QueuePicker.vline_icn}.png) 0;
        }}
        QTreeWidget::branch:has-siblings:adjoins-item {{
            border-image: url({QueuePicker.branch_more_icn}.png) 0;
        }}
        QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
            border-image: url({QueuePicker.branch_end_icn}.png) 0;
        }}
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url({QueuePicker.branch_closed_icn}.png);
        }}
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings  {{
                border-image: none;
                image: url({QueuePicker.branch_open_icn}.png);
        }}""")


        style = QApplication.style()
        self.dir_open = style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.dir_closed = style.standardIcon(QStyle.StandardPixmap.SP_DirClosedIcon)
        self.pdf_icon = QIcon(utility.misc.get_web_folder_path()+ "icons/pdf-icon.png")
        self.vbox_left.addWidget(self.folders_tree)
        self.path_displayed = None

        self.vbox_right = QVBoxLayout()
        lbl = QLabel("PDFs, unused. (Double Click to Add)")
        self.list = QListWidget()
        self.vbox_right.addWidget(lbl)
        self.vbox_right.addWidget(self.list)
        self.list.itemDoubleClicked.connect(self.add_pdf_note)
        self.folders_tree.itemClicked.connect(self.tree_item_clicked)
        hbox = QHBoxLayout()
        hbox.addLayout(self.vbox_left)
        hbox.addLayout(self.vbox_right)
        self.setLayout(hbox)
        self.setStyleSheet("""
            QTreeWidget::item {
                padding: 0;
                margin: 0;
            }
        """)

    def tree_item_clicked(self, item):
        path = item.data(1,1)
        self.load_folders_unused_pdfs(path)

    def tree_exp(self, item):
        item.setIcon(0, self.dir_open)

    def tree_coll(self, item):
        item.setIcon(0, self.dir_closed)

    def refresh(self):
        if self.path_displayed is None:
            return
        self.load_folders_unused_pdfs(self.path_displayed)

    def load_folders_unused_pdfs(self, path):
        path = path.replace("\\", "/")
        if not path.endswith("/"):
            path += "/"
        files = utility.misc.find_pdf_files_in_dir(path)
        files_full = [os.path.join(path, f).replace("\\", "/") for f in files]
        existing = get_pdfs_by_sources(files_full)
        res = set(files_full) - set(existing)
        res_f = [r[r.rindex("/")+1:] if "/" in r else r for r in res]
        self.fill_list(path, res_f)
        self.path_displayed = path

    def fill_list(self, path, names):
        self.list.clear()
        for ix, n in enumerate(names):
            title_i = QListWidgetItem(self.pdf_icon, n)
            title_i.setData(Qt.ItemDataRole.UserRole, QVariant(os.path.join(path, n)))
            self.list.insertItem(ix, title_i)

    def fill_tree(self, folders):
        self.folders_tree.clear()
        fmap = utility.tags.to_tag_hierarchy(folders, sep="/")
        for t, children in fmap.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)
            ti.setData(1, 1, QVariant(t))
            ti.setIcon(0, self.dir_open)
            ti.addChildren(self._add_to_tree(children, t + "/"))
            self.folders_tree.addTopLevelItem(ti)
        self.folders_tree.setExpandsOnDoubleClick(True)
        self.folders_tree.expandAll()

    def _add_to_tree(self, map, prefix):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)
            ti.setData(1, 1, QVariant(prefix + t))
            ti.setIcon(0, self.dir_open)
            prefix_c = prefix + t + "/"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def add_pdf_note(self, item_clicked):
        full_path = item_clicked.data(Qt.ItemDataRole.UserRole)

        if not state.note_editor_shown:
            if self.path_displayed is not None:
                tab = self
                def after():
                    tab.load_folders_unused_pdfs(tab.path_displayed)
                    tab.parent.refresh_queue_list()
                    tab.parent.pdfs_tab.refresh()
                add_tmp_hook("user-note-created", after)
            e = NoteEditor(self.parent, add_only=True, source_prefill=full_path)
        else:
            tooltip("Close the opened Note dialog first!")

class TagsTab(QWidget):

    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()


    def setup_ui(self):

        self.vbox_left                  = QVBoxLayout()
        r_lbl                           = QLabel("Tags")
        r_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vbox_left.addWidget(r_lbl)
        self.vbox_left.setAlignment(r_lbl, Qt.AlignmentFlag.AlignTop)

        if state.is_nightmode():
            self.tag_fg                 = get_config_value("styles.night.tagForegroundColor")
            self.tag_bg                 = get_config_value("styles.night.tagBackgroundColor")
        else:
            self.tag_fg                 = get_config_value("styles.tagForegroundColor")
            self.tag_bg                 = get_config_value("styles.tagBackgroundColor")


        self.tag_tree                   = QTreeWidget()
        self.tag_tree.setColumnCount(1)
        self.tag_tree.setHeaderHidden(True)
        self.tag_tree.setMaximumWidth(370)
        self.tag_icon                   = QIcon(QueuePicker.icons_path + "icon-tag-24.png")



        self.tag_tree.setStyleSheet(f"""
        QTreeWidget::item:hover,QTreeWidget::item:hover:selected {{
            border:none;
            border-radius:5px;
            font-weight: bold;
            background-color: {self.tag_bg};
            color: {self.tag_fg};
        }}
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            border-image: url({QueuePicker.vline_icn}.png) 0;
        }}
        QTreeWidget::branch:has-siblings:adjoins-item {{
            border-image: url({QueuePicker.branch_more_icn}.png) 0;
        }}
        QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
            border-image: url({QueuePicker.branch_end_icn}.png) 0;
        }}
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url({QueuePicker.branch_closed_icn}.png);
        }}
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings  {{
                border-image: none;
                image: url({QueuePicker.branch_open_icn}.png);
        }}
        """)
        self.vbox_left.addWidget(self.tag_tree)
        self.tag_displayed = None

        self.vbox_right                 = QVBoxLayout()
        self.lbl                        = QLabel("Notes, unqueued.")
        self.tag_lbl                    = QLabel("")
        hbox_top                        = QHBoxLayout()
        hbox_top.addWidget(self.lbl)
        hbox_top.addWidget(self.tag_lbl)
        hbox_top.addStretch()
        self.list                       = NoteList(self)
        self.vbox_right.addLayout(hbox_top)
        self.vbox_right.addWidget(self.list)
        self.enqueue_all_btn            = QPushButton("+ Enqueue All...")
        self.enqueue_all_btn.clicked.connect(self.enqueue_all)
        self.empty_and_enqueue_all_btn  = QPushButton("+ Empty Queue and Enqueue All...")
        self.empty_and_enqueue_all_btn.clicked.connect(self.empty_queue_and_enqueue_all)


        btn_hbox                        = QHBoxLayout()
        btn_hbox.addWidget(self.enqueue_all_btn)
        btn_hbox.addWidget(self.empty_and_enqueue_all_btn)
        btn_hbox.addStretch()
        self.vbox_right.addLayout(btn_hbox)

        self.tag_tree.itemClicked.connect(self.tree_item_clicked)
        hbox                            = QHBoxLayout()
        hbox.addLayout(self.vbox_left)
        hbox.addLayout(self.vbox_right)
        self.setLayout(hbox)
        self.setStyleSheet("""
            QTreeWidget::item {
                padding: 0;
                margin: 0;
            }
        """)
       
    def tree_item_clicked(self, item):
        tag = item.data(1,1)
        self.load_tags_unused_notes(tag)

    def list_item_clicked(self, item):
        self.parent.set_chosen(item.data(Qt.ItemDataRole.UserRole), item.text())

    def load_tags_unused_notes(self, tag):
        notes = get_unqueued_notes_for_tag(tag)
        self.fill_list(notes)
        self.tag_displayed = tag
        self.lbl.setText(f"Unqueued Notes for")
        self.tag_lbl.setText(utility.text.trim_if_longer_than(tag, 50))
        self.tag_lbl.setStyleSheet(f"background-color: {self.tag_bg}; color: {self.tag_fg}; border-radius: 3px; padding: 3px;")

    def fill_list(self, notes):
        self.list.fill(notes)

    def fill_tree(self, tags):
        self.tag_tree.clear()
        fmap = utility.tags.to_tag_hierarchy(tags)
        for t, children in fmap.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)
            ti.setData(1, 1, QVariant(t))
            ti.setIcon(0, self.tag_icon)
            ti.addChildren(self._add_to_tree(children, t + "::"))
            self.tag_tree.addTopLevelItem(ti)
        self.tag_tree.setExpandsOnDoubleClick(True)
        self.tag_tree.expandAll()
        if self.tag_displayed is None and self.tag_tree.topLevelItemCount() > 0:
            self.load_tags_unused_notes(self.tag_tree.topLevelItem(0).data(1,1))

    def _add_to_tree(self, map, prefix):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)
            ti.setData(1, 1, QVariant(prefix + t))
            ti.setIcon(0, self.tag_icon)
            prefix_c = prefix + t + "::"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def refresh(self):
        self.fill_tree(get_all_tags())
        if self.tag_displayed is not None:
            self.load_tags_unused_notes(self.tag_displayed)

    def enqueue(self, sched):
        if sched == 0:
            return
        sels = self.list.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.ItemDataRole.UserRole)
        self.parent.set_chosen(-1, "")
        update_priority_list(nid, sched)
        self.parent.refresh_queue_list()
        self.refresh()
        tooltip(f"Moved in Queue, with priority <b>{dynamic_sched_to_str(sched)}</b>")

    def empty_queue_and_enqueue_all(self):
        if self.tag_displayed is None:
            return
        notes = get_unqueued_notes_for_tag(self.tag_displayed)
        if len(notes) == 0:
            return
        dialog = PriorityDialog(self, None)

        if dialog.exec_():
            empty_priority_list()
            prio = dialog.value
            for n in notes:
                update_priority_list(n.id, prio)
            self.parent.refresh_queue_list()
            self.refresh()
            tooltip(f"Emptied Queue, inserted all with tag <b>{self.tag_displayed}</b>")

    def enqueue_all(self):
        if self.tag_displayed is None:
            return

        notes = get_unqueued_notes_for_tag(self.tag_displayed)
        if len(notes) == 0:
            return
        dialog = PriorityDialog(self, None)

        if dialog.exec_():
            prio = dialog.value
            for n in notes:
                update_priority_list(n.id, prio)
            self.parent.refresh_queue_list()
            self.refresh()
            tooltip(f"Added all with tag <b>{self.tag_displayed}</b>")


class ScheduleMWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.notes = {}
        self.prios = {}
        self.table_boundary = 14
        self.setup_ui()


    def refresh(self):
        self.notes = get_notes_by_future_due_date()
        self.prios = get_priorities([item.id for item in [item for sublist in self.notes.values() for item in sublist]])
        self.fill_table()
        self.frame_cb.setCurrentIndex([14,28,60,180].index(self.table_boundary))

    def setup_ui(self):
        self.setLayout(QHBoxLayout())
        self.table = QTableWidget()
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setRowCount(len(self.notes))
        self.table.setColumnCount(2)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        v_left = QVBoxLayout()

        h_frame = QHBoxLayout()
        self.frame_cb = QComboBox()
        self.frame_cb.addItem("14 days", QVariant(14))
        self.frame_cb.addItem("28 days", QVariant(28))
        self.frame_cb.addItem("60 days", QVariant(60))
        self.frame_cb.addItem("180 days", QVariant(180))
        self.frame_cb.currentTextChanged.connect(self.on_frame_changed)
        self.frame_cb.setCurrentIndex([14,28,60,180].index(self.table_boundary))
        h_frame.addWidget(QLabel("Frame: "))
        h_frame.addWidget(self.frame_cb)
        self.avg_lbl = QLabel("")
        self.avg_lbl.setStyleSheet("background: #2496dc; color: white; padding-left: 5px; padding-right: 5px;")
        h_frame.addStretch()
        h_frame.addWidget(self.avg_lbl)

        v_left.addLayout(h_frame)
        v_left.addWidget(self.table)
        # v_left.addStretch()
        self.layout().addLayout(v_left)

        v_right = QVBoxLayout()
        self.calendar = QCalendarWidget()
        v_right.addWidget(QLabel("WIP"))
        v_right.addWidget(self.calendar)
        v_right.addWidget(QLabel("WIP"))
        v_right.addStretch()
        self.layout().addLayout(v_right)

        # self.layout().addStretch()
        self.fill_table()

    def fill_table(self):
        self.table.clear()
        self.table.setRowCount(len(self.notes))

        due_dates   = sorted(self.notes.keys())
        c_total     = 0
        ix          = -1
        today_stmp  = datetime.today().strftime("%Y-%m-%d")

        while ix < len(due_dates) - 1:

            ix          += 1
            due_date    = due_dates[ix]
            dt          = utility.date.dt_from_date_only_stamp(due_date)

            # only regard next n days
            if (dt.date() - datetime.now().date()).days > self.table_boundary:
                break

            pretty      = utility.date.dt_from_date_only_stamp(due_date).strftime("%a, %d %b, %Y")

            sub         = QTableWidget()
            sub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            sub.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            sub.setRowCount(len(self.notes[due_date]))
            sub.setColumnCount(3)
            sub.horizontalHeader().setVisible(False)
            sub.verticalHeader().setVisible(False)
            sub.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            sub.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            sub.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

            item = QTableWidgetItem(pretty)
            item.setTextAlignment(Qt.AlignmentFlag.AlignTop)
            self.table.setItem(ix, 0, item)
            if ix == 0 and today_stmp == due_date:
                self.table.item(ix, 0).setForeground(Qt.blue if not state.is_nightmode() else Qt.cyan)
                self.table.item(ix, 0).setText("Today")
            elif (datetime.today().date() + timedelta(days=1)).strftime("%Y-%m-%d") == due_date:
                self.table.item(ix, 0).setText(f"{pretty}\n(Tomorrow)")
            due     = ""
            types   = ""
            c_total += len(self.notes[due_date])
            for ix_2, note in enumerate(self.notes[due_date]):
                if note.schedule_type() != "td" :
                    next_rem = note.reminder
                    while True:
                        next_rem    = utility.date.get_next_reminder(next_rem)
                        due         = utility.date.dt_from_stamp(next_rem.split("|")[1])

                        if (due.date() - datetime.now().date()).days <= self.table_boundary:
                            due_stamp       = due.strftime("%Y-%m-%d")
                            copied          = copy.copy(note)
                            copied.reminder = next_rem
                            if due_stamp in self.notes:
                                if not note.id in [n.id for n in self.notes[due_stamp]]:
                                    self.notes[due_stamp].append(copied)
                            else:
                                self.notes[due_stamp] = [copied]
                                self.table.setRowCount(len(self.notes))
                                due_dates = sorted(self.notes.keys())
                        else:
                            break


                if note.id in self.prios:
                    prio = self.prios[note.id]
                else:
                    prio = "-"

                prio_lbl = QLabel(str(prio))
                prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if prio != "-":
                    prio_lbl.setStyleSheet(f"background: {utility.misc.prio_color(prio)}; color: white;")

                title_lbl = QLabel(note.get_title())
                title_lbl.setStyleSheet("padding-left: 5px;")

                sched_lbl = QLabel(utility.date.schedule_verbose(note.reminder))
                sched_lbl.setStyleSheet("padding-left: 5px;")

                sub.setCellWidget(ix_2, 0, prio_lbl)
                sub.setCellWidget(ix_2, 1, title_lbl)
                sub.setCellWidget(ix_2, 2, sched_lbl)

            sub.setColumnWidth(2, 300)
            sub.resizeRowsToContents()
            sub.setMaximumHeight(sub.verticalHeader().length() + 5)

            self.table.setCellWidget(ix, 1, sub)
            # self.table.item(ix, 0).setFlags(Qt.ItemIsEnabled)
        self.table.resizeRowsToContents()
        if c_total > 0:
            self.avg_lbl.setText(f"Avg. {round(c_total/ self.table_boundary, 1)} notes / day")
        else:
            self.avg_lbl.setText("")

    def on_frame_changed(self, new_text):
        self.table_boundary = int(new_text.split()[0])
        self.refresh()


class QueueWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent     = parent
        self.chosen_id  = None
        self.setup_ui()

        queue           = _get_priority_list()

        self.fill_list(self.t_view_left, queue)
        self.tabs_changed(0)

    def setup_ui(self):

        self.vbox_left      = QVBoxLayout()
        self.title_hbox          = QHBoxLayout()
        l_lbl               = QLabel("Queue")
        self.title_hbox.addWidget(l_lbl)
        self.title_hbox.addStretch()
        self.vbox_left.addLayout(self.title_hbox)
        self.t_view_left    = QTableWidget()
        self.tabs           = QTabWidget()
        self.tags_tab       = TagsTab(self)
        self.pdfs_tab       = PDFsTab(self)
        self.notes_tab      = TextNotesTab(self)
        self.videos_tab     = VideosTab(self)
        self.folders_tab    = FoldersTab(self)

        self.tabs.currentChanged.connect(self.tabs_changed)
        self.tabs.addTab(self.tags_tab, "Unqueued Notes, By Tag")
        self.tabs.addTab(self.pdfs_tab, "PDFs")
        self.tabs.addTab(self.notes_tab, "Text Notes")
        self.tabs.addTab(self.videos_tab, "Videos")
        self.tabs.addTab(self.folders_tab, "Folders - Import")

        self.t_view_left.setColumnCount(6)
        self.t_view_left.setHorizontalHeaderLabels(["", "Title", "Sched.", "Prio", "", ""])
        self.t_view_left.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.t_view_left.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.t_view_left.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.t_view_left.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.t_view_left.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.t_view_left.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.t_view_left.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.t_view_left.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.t_view_left.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.t_view_left.cellDoubleClicked.connect(self.cell_clicked)

        self.t_view_left.setMinimumWidth(470)
        self.vbox_left.addWidget(self.t_view_left)

        # buttons under queue table

        uncheck_icn = "icons/unchecked" + ("_night.png" if state.is_nightmode() else ".png")
        check_icn   = "icons/checked" + ("_night.png" if state.is_nightmode() else ".png")

        self.check_all_btn = QPushButton("")
        self.check_all_btn.setIcon(QIcon(utility.misc.get_web_folder_path()+ check_icn))
        self.check_all_btn.clicked.connect(self.check_all_clicked)

        self.uncheck_all_btn = QPushButton("")
        self.uncheck_all_btn.setIcon(QIcon(utility.misc.get_web_folder_path()+ uncheck_icn))
        self.uncheck_all_btn.clicked.connect(self.uncheck_all_clicked)

        self.unqueue_btn = QPushButton(" Remove Sel.")
        self.unqueue_btn.setDisabled(True)
        self.unqueue_btn.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.unqueue_btn.clicked.connect(self.rem_selected_clicked)

        self.unqueue_all_btn = QPushButton(" Empty... ")
        self.unqueue_all_btn.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.unqueue_all_btn.clicked.connect(self.empty_clicked)

        self.shuffle_queue_btn = QPushButton(" Shuffle... ")
        self.shuffle_queue_btn.clicked.connect(self.shuffle_clicked)

        self.spread_prios_btn = QPushButton(" Spread Priorities... ")
        self.spread_prios_btn.clicked.connect(self.spread_clicked)

        self.random_prios_btn = QPushButton(" Randomize Priorities... ")
        self.random_prios_btn.clicked.connect(self.random_prios_clicked)

        self.tags_btn = QPushButton(" Tag... ")
        self.tags_btn.clicked.connect(self.tag_assign_clicked)

        btn_hbox_l = QHBoxLayout()
        btn_hbox_l.addWidget(self.check_all_btn)
        btn_hbox_l.addWidget(self.uncheck_all_btn)
        btn_hbox_l.addWidget(self.unqueue_btn)
        btn_hbox_l.addWidget(self.unqueue_all_btn)
        btn_hbox_l.addWidget(self.shuffle_queue_btn)
        btn_hbox_l.addWidget(self.spread_prios_btn)
        btn_hbox_l.addWidget(self.random_prios_btn)
        btn_hbox_l.addWidget(self.tags_btn)
        btn_hbox_l.addStretch()

        self.vbox_left.addLayout(btn_hbox_l)
        self.vbox = QVBoxLayout()

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.vbox_left)
        self.hbox.addWidget(self.tabs)

        self.vbox.addLayout(self.hbox)

        bottom_box = QHBoxLayout()
        bottom_box.addStretch(1)
        self.reject_btn = QPushButton("Close")
        self.reject_btn.clicked.connect(self.parent.reject)
        bottom_box.addWidget(self.reject_btn)
        self.vbox.addSpacing(10)
        self.vbox.addLayout(bottom_box)

        self.setLayout(self.vbox)
        # self.resize(770, 480)

        styles = """
            QTableWidget::item:hover {
                background-color: #2496dc;
                color: white;
            }
        """
        if self.parent.dark_mode_used:
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
                QTabBar::tab:focus { }

                QComboBox {
                    background-color: #222;
                    color: lightgrey;
                }
            """
        self.setStyleSheet(styles)

    def tabs_changed(self, ix):
        if ix == 0:
            self.tags_tab.refresh()
        elif ix == 1:
            self.pdfs_tab.refresh()
        elif ix == 2:
            self.notes_tab.refresh()
        elif ix == 3:
            self.videos_tab.refresh()
        elif ix == 4:
            self.folders_tab.fill_tree(get_most_used_pdf_folders())


    def fill_list(self, t_view, db_res):
        """ Fill the queue list. """

        t_view.clearContents()
        if db_res is None:
            t_view.setRowCount(0)
            return
        else:
            t_view.setRowCount(len(db_res))

        open_icon       = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        rem_icon        = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        prios           = get_priorities([n.id for n in db_res])
        self.priorities = prios
        note_types      = {}

        for ix, n in enumerate(db_res):
            t = n.get_note_type()
            if not t in note_types:
                note_types[t] = 1
            else:
                note_types[t] += 1
            title       = n.title if n.title is not None and len(n.title) > 0 else "Untitled"
            title_i     = QTableWidgetItem(title)
            title_i.setData(Qt.ItemDataRole.UserRole, QVariant(n.id))

            sched       = utility.date.next_instance_of_schedule_verbose(n.reminder) if n.has_schedule() else "-"
            sched_lbl   = QLabel(sched)
            sched_lbl.setStyleSheet("padding-left: 4px; padding-right: 4px;")
            sched_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)


            cb = QCheckBox()
            cb.stateChanged.connect(functools.partial(self.cb_clicked, ix))
            cw = ClickableQWidget()
            cw.clicked.connect(functools.partial(self.cb_outer_clicked, ix))
            lcb = QHBoxLayout()
            cw.setLayout(lcb)
            lcb.addWidget(cb)
            lcb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lcb.setContentsMargins(0,0,0,0)


            read_btn    = QToolButton()
            read_btn.setIcon(open_icon)
            read_btn.setToolTip("Open")
            read_btn.clicked.connect(functools.partial(self.read_btn_clicked, n.id))

            rem_btn     = QToolButton()
            rem_btn.setIcon(rem_icon)
            rem_btn.setToolTip("Remove from Queue")
            rem_btn.clicked.connect(functools.partial(self.rem_btn_clicked, n.id))

            if n.id in prios:
                prio_lbl    = QLabel(str(int(prios[n.id])))
                prio_lbl.setStyleSheet(f"background-color: {utility.misc.prio_color(prios[n.id])}; color: white; font-size: 14px; text-align: center;")
            else:
                prio_lbl    = QLabel("-")
                prio_lbl.setStyleSheet(f"font-size: 14px; text-align: center;")
            prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # t_view.setItem(ix, 0, cb)
            t_view.setCellWidget(ix, 0, cw)
            t_view.setItem(ix, 1, title_i)
            t_view.setCellWidget(ix, 2, sched_lbl)
            t_view.setCellWidget(ix, 3, prio_lbl)
            t_view.setCellWidget(ix, 4, read_btn)
            t_view.setCellWidget(ix, 5, rem_btn)

        # clear title layout
        for i in reversed(range(self.title_hbox.count())):
            if self.title_hbox.itemAt(i).widget():
                self.title_hbox.itemAt(i).widget().setParent(None)

        if len(db_res) == 0:
            self.unqueue_all_btn.setDisabled(True)
            self.title_hbox.insertWidget(max(0,self.title_hbox.count() - 2), QLabel(f"Queue, empty"))
        else:
            self.unqueue_all_btn.setDisabled(False)
            s = "s" if len(db_res) > 1 else ""
            self.title_hbox.insertWidget(max(0,self.title_hbox.count() - 2), QLabel(f"Queue, {len(db_res)} item{s}"))

        avg_prio        = round(sum(prios.values()) / len(prios), 1) if len(prios) > 0 else 0
        avg_prio_lbl    = QLabel()
        avg_prio_lbl.setText(f"Avg. Prio: {avg_prio}")
        avg_prio_lbl.setStyleSheet(f"background-color: {utility.misc.prio_color(avg_prio)}; padding: 4px; color: white; text-align: center;")
        self.title_hbox.insertWidget(self.title_hbox.count() - 1, avg_prio_lbl)

        if len(note_types) > 0:
            for k,v in note_types.items():
                lbl = QLabel(f"{k}: {v}")
                lbl.setStyleSheet("background-color: #2496dc; color: white; padding: 4px;")
                self.title_hbox.insertWidget(self.title_hbox.count() - 1, lbl)

        self.unqueue_btn.setText(f"Remove Selected")
        self.unqueue_btn.setDisabled(True)
        self.tags_btn.setDisabled(True)

        t_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        t_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        t_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        t_view.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        t_view.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        t_view.resizeRowsToContents()
        # t_view.resizeColumnsToContents()

    def selected(self):
        r = []
        for ix in range(self.t_view_left.rowCount()):
            if self.t_view_left.cellWidget(ix, 0).layout().itemAt(0).widget().checkState() == Qt.Checked:
                r.append(self.t_view_left.item(ix, 1).data(Qt.ItemDataRole.UserRole))
        return r

    def check_all_clicked(self):
        for ix in range(self.t_view_left.rowCount()):
            self.t_view_left.cellWidget(ix, 0).layout().itemAt(0).widget().setChecked(True)

    def uncheck_all_clicked(self):
        for ix in range(self.t_view_left.rowCount()):
            self.t_view_left.cellWidget(ix, 0).layout().itemAt(0).widget().setChecked(False)

    def rem_btn_clicked(self, id):

        remove_from_priority_list(id)
        self.refresh_queue_list()
        self.tabs.currentWidget().refresh()
        tooltip(f"Removed Note from Queue.")

    def rem_selected_clicked(self):
        selected = self.selected()
        if len(selected) > 0:
            for id in selected:
                remove_from_priority_list(id)
            self.refresh_queue_list()
            self.tabs.currentWidget().refresh()
            if len(selected) == 1:
                tooltip(f"Removed note from queue.")
            else:
                tooltip(f"Removed {len(selected)} notes from queue.")
            self.unqueue_btn.setText(f"Remove Selected")
            self.unqueue_btn.setDisabled(True)
        else:
            tooltip("Select some items first")

    def empty_clicked(self):
        reply = QMessageBox.question(self, 'Empty Queue', "This will remove all items from the queue.<br> Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            empty_priority_list()
            self.refresh_queue_list()
            self.tabs.currentWidget().refresh()

    def shuffle_clicked(self):
        reply = QMessageBox.question(self, 'Shuffle Queue', """This will change the current order of all items in the queue.
                                            <br>Priorities and schedules will stay the same.<br>
                                            Are you sure?<br>""".replace("\n", ""), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            shuffle_queue()
            self.refresh_queue_list()
            self.tabs.currentWidget().refresh()

    def spread_clicked(self):
        reply = QMessageBox.question(self, 'Spread Priorities', """
                                            This will spread the current priorities between 1 and 100.<br>
                                            Are you sure?<br>
                                            """.replace("\n", ""), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            spread_priorities()
            self.refresh_queue_list()
            self.tabs.currentWidget().refresh()

    def random_prios_clicked(self):
        reply = QMessageBox.question(self, 'Random Priorities', """
                                            This will change the priorities of all items to a random value between 1 and 100.<br>
                                            Are you sure?<br>
                                            """.replace("\n", ""), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            assign_random_priorities()
            self.refresh_queue_list()
            self.tabs.currentWidget().refresh()

    def tag_assign_clicked(self):
        selected    = [int(nid) for nid in self.selected()]
        dialog      = TagAssignDialog(self, selected)
        if dialog.exec_():
            chosen = dialog.tags
            if chosen is not None and len(chosen.strip()) > 0:
                tags = [t for t in chosen.split(" ") if len(t.strip()) > 0]
                if len(tags) > 0:
                    add_tags(selected, tags)
                    tooltip(f"Added tag(s) to {len(selected)} note(s).")
                    self.tabs.currentWidget().refresh()


    def read_btn_clicked(self, id):
        self.set_chosen(id, "")
        self.parent.accept()

    def cell_clicked(self, row, col):
        if col == 1:
            nid = int(self.t_view_left.item(row, col).data(Qt.ItemDataRole.UserRole))
            self.display_note_modal(nid)


    def cb_clicked(self, row, state):
        sel_len = len(self.selected())
        if sel_len == 0:
            self.unqueue_btn.setText(f" Remove Sel.")
            self.unqueue_btn.setDisabled(True)
            self.tags_btn.setDisabled(True)
        else:
            self.unqueue_btn.setDisabled(False)
            self.tags_btn.setDisabled(False)
            self.unqueue_btn.setText(f" Remove Sel. ({sel_len})")

    def cb_outer_clicked(self, row):
        widget = self.t_view_left.cellWidget(row, 0).layout().itemAt(0).widget()
        widget.setChecked(not widget.checkState() == Qt.Checked)


    def display_note_modal(self, id):
        """ Open the edit modal for the given ID. """

        if Reader.note_id == id:
            showInfo("Cannot edit that note: It is currently opened in the reader.")
            return
        if not state.note_editor_shown:
            add_tmp_hook("user-note-closed", self.refresh_all)
            dialog = NoteEditor(self, id, add_only=True, read_note_id=None)

    def set_chosen(self, id, name):
        self.chosen_id = id

    def refresh_all(self):
        self.refresh_queue_list()
        self.tabs.currentWidget().refresh()

    def refresh_queue_list(self):
        self.fill_list(self.t_view_left, _get_priority_list())




class NoteList(QTableWidget):
    """ Used for the note lists displayed on the right side of the dialog. """

    def __init__(self, parent):
        self.parent = parent
        super(NoteList, self).__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Title", "", "", ""])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cellDoubleClicked.connect(self.cell_clicked)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)


    def fill(self, notes):
        self.clearContents()
        if notes is None or len(notes) == 0:
            self.setRowCount(0)
            return
        self.setRowCount(len(notes))

        open_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        del_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        for ix, n in enumerate(notes):

            title = QTableWidgetItem(n.get_title())
            title.setData(Qt.ItemDataRole.UserRole, QVariant(n.id))

            open_btn = QToolButton()
            open_btn.setIcon(open_icon)
            open_btn.setToolTip("Open")
            open_btn.clicked.connect(functools.partial(self.open_btn_clicked, n.id))

            del_btn = QToolButton()
            del_btn.setIcon(del_icon)
            del_btn.setToolTip("Delete Note...")
            del_btn.clicked.connect(functools.partial(self.del_btn_clicked, n.id))

            add_btn = QToolButton()
            add_btn.setText("+")
            add_btn.setToolTip("Add to Queue...")
            add_btn.clicked.connect(functools.partial(self.add_btn_clicked, n.id))

            self.setItem(ix, 0, title)
            self.setCellWidget(ix, 1, open_btn)
            self.setCellWidget(ix, 2, del_btn)
            self.setCellWidget(ix, 3, add_btn)

        self.resizeRowsToContents()


    def open_btn_clicked(self, id):
        self.parent.parent.set_chosen(id, "")
        win = mw.app.activeWindow()
        win.accept()

    def del_btn_clicked(self, id):

        reply = QMessageBox.question(self, 'Delete Note?', "This will irreversibly delete the chosen note. \nAre you sure?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            delete_note(id)
            if get_index() is not None:
                get_index().deleteNote(id)
            run_hooks("user-note-deleted")
            self.parent.refresh()

    def cell_clicked(self, row, col):
        if col == 0:
            nid = int(self.item(row, col).data(Qt.ItemDataRole.UserRole))
            self.parent.parent.display_note_modal(nid)


    def add_btn_clicked(self, id):
        dialog = PriorityDialog(self, id)
        if dialog.exec_():
            prio = dialog.value
            update_priority_list(id, prio)
            self.parent.parent.refresh_queue_list()
            self.parent.refresh()
            tooltip(f"Moved in Queue, with priority <b>{dynamic_sched_to_str(prio)}</b>")
