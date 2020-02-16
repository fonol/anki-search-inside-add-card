from aqt.qt import *
import aqt
import random
import os
from .editor import NoteEditor
from ..notes import *
from ..notes import _get_priority_list
from ..internals import perf_time
import utility.text
import utility.misc
import utility.tags

class QueuePicker(QDialog):
    """
    Can be used to select a single note from the queue or to move pdf notes in/out of the queue.
    """
    def __init__(self, parent, note_list, note_list_right):
        self.chosen_id = None 
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        try:
            self.dark_mode_used = utility.misc.dark_mode_is_used(aqt.mw.addonManager.getConfig(__name__))
        except:
            self.dark_mode_used = False
        self.setup_ui(note_list, note_list_right)
        self.setWindowTitle("Queue Manager")
        
        # self.refresh_queue_list()
        queue = _get_priority_list()
        self.fill_list(self.t_view_left, queue, with_nums = True, with_icons = True)
        self.tabs_changed(0) 
       
    def setup_ui(self, note_list, note_list_right):

        self.vbox_left = QVBoxLayout()
        l_lbl = QLabel("Queue (Drag & Drop to Reorder)") 
        l_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_left.addWidget(l_lbl)
        self.t_view_left = QListWidget()
        self.t_view_left.setDragDropMode(QAbstractItemView.InternalMove)
        self.t_view_left.model().rowsMoved.connect(self.on_list_reorder)
        self.tabs = QTabWidget()
        self.tags_tab = TagsTab(self)
        self.pdfs_tab = PDFsTab(self)
        self.notes_tab = TextNotesTab(self)
        self.folders_tab = FoldersTab(self)
        self.tabs.currentChanged.connect(self.tabs_changed)
        self.tabs.addTab(self.tags_tab, "PDFs + Text Notes, By Tag")
        self.tabs.addTab(self.pdfs_tab, "PDFs, Unqueued")
        self.tabs.addTab(self.notes_tab, "Text Notes, Unqueued")
        self.tabs.addTab(self.folders_tab, "Folders - Import")

        self.t_view_left.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_view_left.setMaximumWidth(370)
        self.t_view_left.setUniformItemSizes(True)
        self.t_view_left.itemClicked.connect(self.item_clicked)
        self.vbox_left.addWidget(self.t_view_left)
        self.unqueue_btn = QPushButton("Dequeue Selected")
        self.unqueue_btn.clicked.connect(self.remove_from_queue)
        self.vbox_left.addWidget(self.unqueue_btn)

        self.unqueue_all_btn = QPushButton("Empty Queue")
        self.unqueue_all_btn.clicked.connect(self.remove_all_from_queue)

        self.shuffle_queue_btn = QPushButton("Shuffle")
        self.shuffle_queue_btn.clicked.connect(self.shuffle_queue)

        btn_hbox_l = QHBoxLayout()
        btn_hbox_l.addWidget(self.unqueue_all_btn)
        btn_hbox_l.addWidget(self.shuffle_queue_btn)
        self.vbox_left.addLayout(btn_hbox_l)

        self.reorder_select = QComboBox()
        self.reorder_select.addItem("Reorder by Date Created (Asc.)")
        self.reorder_select.addItem("Reorder by Date Created (Desc.)")
        self.reorder_select.addItem("Reorder by Name (Asc.)")
        self.reorder_btn = QPushButton("Apply")
        self.reorder_btn.clicked.connect(self.on_reorder_clicked)
        h_r = QHBoxLayout()
        h_r.addWidget(self.reorder_select)
        h_r.addWidget(self.reorder_btn)
        self.vbox_left.addLayout(h_r)
        self.vbox = QVBoxLayout()

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.vbox_left)
        self.hbox.addWidget(self.tabs)

        self.vbox.addLayout(self.hbox)
        
        bottom_box = QHBoxLayout()
        self.accept_btn = QPushButton("Read")
        self.accept_btn.clicked.connect(self.accept)
        self.accept_btn.setEnabled(False)
        self.chosen_lbl = QLabel("")
        boldf = QFont()
        boldf.setBold(True)
        self.chosen_lbl.setFont(boldf)
        bottom_box.addWidget(self.chosen_lbl)
        bottom_box.addStretch(1)
        bottom_box.addWidget(self.accept_btn)
        bottom_box.addSpacing(8)
        self.reject_btn = QPushButton("Close")
        self.reject_btn.clicked.connect(self.reject)
        bottom_box.addWidget(self.reject_btn)
        self.vbox.addSpacing(10)
        self.vbox.addLayout(bottom_box)

        self.setLayout(self.vbox)
        # self.resize(770, 480)

        if self.dark_mode_used:
            styles = """
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
            self.tags_tab.fill_tree(get_all_tags())
        elif ix == 1:
            self.pdfs_tab.fill_list(get_pdf_notes_not_in_queue())
        elif ix == 2:
            self.notes_tab.fill_list(get_non_pdf_notes_not_in_queue())
        elif ix == 3:
            self.folders_tab.fill_tree(get_most_used_pdf_folders())
        

    def fill_list(self, t_view, db_res, with_nums = False, with_icons = True):
        t_view.clear()
        icon_provider = QFileIconProvider()
        pdf_icon = None
        icon = QApplication.style().standardIcon(QStyle.SP_FileIcon)
        for ix, n in enumerate(db_res):
            title = n.title if n.title is not None and len(n.title) > 0 else "Untitled"
            if with_nums:
                title = f"{ix+1}.  {title}"
            if pdf_icon is None and n.is_pdf():
                #pdf_icon = icon_provider.icon(QFileInfo(n.source))
                pdf_icon = QIcon(utility.misc.get_web_folder_path() + "pdf-icon.png")
            i = pdf_icon if n.is_pdf() else icon
            if with_icons:
                title_i = QListWidgetItem(i, title)
            else:
                title_i = QListWidgetItem(title)
            title_i.setData(Qt.UserRole, QVariant(n.id))
            t_view.insertItem(ix, title_i)
        
    def item_clicked(self, item):
        self.clear_selection("right")
        self.set_chosen(item.data(Qt.UserRole), item.text()[item.text().index(".") + 2:])
    
    def on_list_reorder(self):
        nids = []
        for i in range(self.t_view_left.count()):
            item = self.t_view_left.item(i)
            nids.append(item.data(Qt.UserRole))
            item.setText(str(i+1) + ". " + item.text()[item.text().index(".")+2:])
        set_priority_list(nids)
            

    def set_chosen(self, id, name):
        self.chosen_id = id
        if len(name) > 0:
            self.chosen_lbl.setText("Chosen:  " + name)
            self.accept_btn.setEnabled(True)
            self.accept_btn.setText(f" Read \"{utility.text.trim_if_longer_than(name.strip(), 30)}\" ")
        else: 
            self.chosen_lbl.setText("")
            self.accept_btn.setText("Read")
            self.accept_btn.setEnabled(False)

    def clear_selection(self, list):
        if list == "left":
            lw = self.t_view_left
        else:
            lw = self.pdfs_tab.t_view_right
        for i in range(lw.count()):
            lw.item(i).setSelected(False)

    def refresh_queue_list(self):
        self.fill_list(self.t_view_left, _get_priority_list(), with_nums = True)

    def refill_list_views(self, left_list, right_list):
        self.t_view_left.clear()
        for ix, n in enumerate(left_list):
            title = n.title if n.title is not None and len(n.title) > 0 else "Untitled"
            title_i = QListWidgetItem(str(ix + 1) + ".  " + title)
            title_i.setData(Qt.UserRole, QVariant(n.id))
            self.t_view_left.insertItem(ix, title_i)

        self.pdfs_tab.fill_list(right_list)

    def shuffle_queue(self):
        priority_list = _get_priority_list()
        if priority_list is None or len(priority_list) == 0:
            return
        random.shuffle(priority_list)
        self.fill_list(self.t_view_left, priority_list, with_nums = True)
        ids = [p.id for p in priority_list]
        #persist reordering to db
        set_priority_list(ids)

    def remove_all_from_queue(self):
        empty_priority_list()
        self.fill_list(self.t_view_left, [], with_nums = True)
        self.tabs.currentWidget().refresh()

    def remove_from_queue(self):
        sels = self.t_view_left.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        if self.chosen_id == nid:
            self.set_chosen(-1, "")
        update_position(nid, QueueSchedule.NOT_ADD)
        self.refresh_queue_list()
        self.tabs.currentWidget().refresh()
    
    def on_reorder_clicked(self):
        sel = self.reorder_select.currentIndex()
        priority_list = _get_priority_list()
        if sel == 0:
            priority_list = sorted(priority_list, key=lambda x: x.created)
        elif sel == 1:
            priority_list = sorted(priority_list, key=lambda x: x.created, reverse=True)
        elif sel == 2:
            priority_list = sorted(priority_list, key=lambda x: x.title if x.title is not None else "")
        self.fill_list(self.t_view_left, priority_list, with_nums = True)
        set_priority_list([x.id for x in priority_list])



       

class PDFsTab(QWidget):
    
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.vbox_right = QVBoxLayout()
        r_lbl = QLabel("PDF notes, not in Queue") 
        r_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_right.addWidget(r_lbl)
        self.search_bar_right = QLineEdit()
        self.search_bar_right.textChanged.connect(self.search_enter)
        self.vbox_right.addWidget(self.search_bar_right)
        self.t_view_right = QListWidget()
        self.vbox_right.addWidget(self.t_view_right)
        self.vbox_right.setAlignment(Qt.AlignHCenter)
        self.move_to_queue_start_btn = QPushButton("Enqueue [Start]")
        self.move_to_queue_start_btn.clicked.connect(self.move_to_queue_beginning)
        self.move_to_queue_rnd_btn = QPushButton("Enqueue [Rnd]")
        self.move_to_queue_rnd_btn.clicked.connect(self.move_to_queue_random)
        self.move_to_queue_end_btn = QPushButton("Enqueue [End]")
        self.move_to_queue_end_btn.clicked.connect(self.move_to_queue_end)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.move_to_queue_start_btn)
        btn_hbox.addWidget(self.move_to_queue_rnd_btn)
        btn_hbox.addWidget(self.move_to_queue_end_btn)
        self.vbox_right.addLayout(btn_hbox)
        self.setLayout(self.vbox_right)
        self.t_view_right.itemClicked.connect(self.item_clicked_right_side)
    
    def refresh(self):
        self.search_bar_right.clear()
        self.fill_list(get_pdf_notes_not_in_queue())

    def fill_list(self, db_list):
        self.t_view_right.clear()
        # icon_provider = QFileIconProvider()
        icon = None
        for ix, n in enumerate(db_list):
            if icon is None:
                icon = QIcon(utility.misc.get_web_folder_path() + "pdf-icon.png")
                # icon = icon_provider.icon(QFileInfo(n.source))
            title = n.get_title()
            title_i = QListWidgetItem(icon, title)
            title_i.setData(Qt.UserRole, QVariant(n.id))
            self.t_view_right.insertItem(ix, title_i)

    def search_enter(self):
        inp = self.search_bar_right.text()
        if inp is None or len(inp.strip()) == 0:
            self.fill_list(get_pdf_notes_not_in_queue())
            return
        res = find_unqueued_pdf_notes(inp)
        self.t_view_right.clear()
        self.fill_list(res)

    def move_to_queue_beginning(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.HEAD)
        self.parent.refresh_queue_list()
        self.refresh()

    def move_to_queue_end(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.END)
        self.parent.refresh_queue_list()
        self.refresh()

    def move_to_queue_random(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.RANDOM)
        self.parent.refresh_queue_list()
        self.refresh()

    def item_clicked_right_side(self, item):
        self.parent.clear_selection("left")
        self.parent.set_chosen(item.data(Qt.UserRole), item.text())


class TextNotesTab(QWidget):
    
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()

    def setup_ui(self):
        self.vbox_right = QVBoxLayout()
        r_lbl = QLabel("Text notes, not in Queue") 
        r_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_right.addWidget(r_lbl)
        self.search_bar_right = QLineEdit()
        self.search_bar_right.textChanged.connect(self.search_enter)
        self.vbox_right.addWidget(self.search_bar_right)
        self.t_view_right = QListWidget()
        self.vbox_right.addWidget(self.t_view_right)
        self.vbox_right.setAlignment(Qt.AlignHCenter)
        self.move_to_queue_start_btn = QPushButton("Enqueue [Start]")
        self.move_to_queue_start_btn.clicked.connect(self.move_to_queue_beginning)
        self.move_to_queue_rnd_btn = QPushButton("Enqueue [Rnd]")
        self.move_to_queue_rnd_btn.clicked.connect(self.move_to_queue_random)
        self.move_to_queue_end_btn = QPushButton("Enqueue [End]")
        self.move_to_queue_end_btn.clicked.connect(self.move_to_queue_end)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.move_to_queue_start_btn)
        btn_hbox.addWidget(self.move_to_queue_rnd_btn)
        btn_hbox.addWidget(self.move_to_queue_end_btn)
        self.vbox_right.addLayout(btn_hbox)
        self.setLayout(self.vbox_right)
        self.t_view_right.itemClicked.connect(self.item_clicked_right_side)

    def refresh(self):
        self.search_bar_right.clear()
        self.fill_list(get_non_pdf_notes_not_in_queue())

    def fill_list(self, db_list):
        self.t_view_right.clear()
        style = QApplication.style()
        icon = style.standardIcon(QStyle.SP_FileIcon)
        for ix, n in enumerate(db_list):
            title = n.get_title()
            title_i = QListWidgetItem(icon, title)
            title_i.setData(Qt.UserRole, QVariant(n.id))
            self.t_view_right.insertItem(ix, title_i)

    def search_enter(self):
        inp = self.search_bar_right.text()
        if inp is None or len(inp.strip()) == 0:
            self.fill_list(get_non_pdf_notes_not_in_queue())
            return
        res = find_unqueued_non_pdf_notes(inp)
        self.t_view_right.clear()
        self.fill_list(res)

    def move_to_queue_beginning(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.HEAD)
        self.parent.refresh_queue_list()
        self.refresh()
       

    def move_to_queue_end(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.END)
        self.parent.refresh_queue_list()
        self.refresh()

    def move_to_queue_random(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.RANDOM)
        self.parent.refresh_queue_list()
        self.refresh()


    def item_clicked_right_side(self, item):
        self.parent.clear_selection("left")
        self.parent.set_chosen(item.data(Qt.UserRole), item.text())


class FoldersTab(QWidget):
    
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()


    def setup_ui(self):
        self.vbox_left = QVBoxLayout()
        r_lbl = QLabel("Most Used Folders:") 
        r_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_left.addWidget(r_lbl)
        self.vbox_left.setAlignment(r_lbl, Qt.AlignTop)
 
        self.folders_tree = QTreeWidget()
        self.folders_tree.setColumnCount(1)
        # self.folders_tree.setSizePolicy(QSizePolicy.M, QSizePolicy.Minimum)
        self.folders_tree.setHeaderHidden(True)
        self.folders_tree.setRootIsDecorated(False)
        self.folders_tree.setMaximumWidth(370)
        self.folders_tree.itemExpanded.connect(self.tree_exp)
        self.folders_tree.itemCollapsed.connect(self.tree_coll)
        style = QApplication.style()
        self.dir_open = style.standardIcon(QStyle.SP_DirOpenIcon)
        self.dir_closed = style.standardIcon(QStyle.SP_DirClosedIcon)
        self.pdf_icon = QIcon(utility.misc.get_web_folder_path()+ "pdf-icon.png")
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
            title_i.setData(Qt.UserRole, QVariant(os.path.join(path, n)))
            self.list.insertItem(ix, title_i)

    def fill_tree(self, folders):
        self.folders_tree.clear()
        fmap = utility.tags.to_tag_hierarchy(folders, sep="/")
        for t, children in fmap.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignLeft)
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
            ti.setTextAlignment(0, Qt.AlignLeft)
            ti.setData(1, 1, QVariant(prefix + t))
            ti.setIcon(0, self.dir_open)
            prefix_c = prefix + t + "/"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def add_pdf_note(self, item_clicked):
        full_path = item_clicked.data(Qt.UserRole)
        e = NoteEditor(self.parent, add_only=True, source_prefill=full_path)
        if self.path_displayed is not None:
            self.load_folders_unused_pdfs(self.path_displayed) 
            self.parent.refresh_queue_list()
            self.parent.pdfs_tab.refresh()

class TagsTab(QWidget):
    
    def __init__(self, parent):
        self.parent = parent
        QWidget.__init__(self)
        self.setup_ui()


    def setup_ui(self):
        self.vbox_left = QVBoxLayout()
        r_lbl = QLabel("Tags") 
        r_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_left.addWidget(r_lbl)
        self.vbox_left.setAlignment(r_lbl, Qt.AlignTop)
 
        self.tag_tree = QTreeWidget()
        self.tag_tree.setColumnCount(1)
        self.tag_tree.setHeaderHidden(True)
        self.tag_tree.setMaximumWidth(370)
        self.tag_icon = QIcon(utility.misc.get_web_folder_path()+ "icon-tag-24.png")
        self.pdf_icon = QIcon(utility.misc.get_web_folder_path()+ "pdf-icon.png")
        style = QApplication.style()
        self.text_note_icon = style.standardIcon(QStyle.SP_FileIcon)
        self.vbox_left.addWidget(self.tag_tree)
        self.tag_displayed = None

        self.vbox_right = QVBoxLayout()
        self.lbl = QLabel("Notes, unqueued.")
        self.list = QListWidget()
        self.list.itemClicked.connect(self.list_item_clicked)
        self.vbox_right.addWidget(self.lbl)
        self.vbox_right.addWidget(self.list)
        self.enqueue_all_btn = QPushButton("Enqueue All")
        self.enqueue_all_btn.clicked.connect(self.enqueue_all)
        self.empty_and_enqueue_all_btn = QPushButton("Empty Queue and Enqueue All")
        self.empty_and_enqueue_all_btn.clicked.connect(self.empty_queue_and_enqueue_all)
        self.vbox_right.addWidget(self.enqueue_all_btn)
        self.vbox_right.addWidget(self.empty_and_enqueue_all_btn)
        self.move_to_queue_start_btn = QPushButton("Enqueue [Start]")
        self.move_to_queue_start_btn.clicked.connect(self.move_to_queue_beginning)
        self.move_to_queue_rnd_btn = QPushButton("Enqueue [Rnd]")
        self.move_to_queue_rnd_btn.clicked.connect(self.move_to_queue_random)
        self.move_to_queue_end_btn = QPushButton("Enqueue [End]")
        self.move_to_queue_end_btn.clicked.connect(self.move_to_queue_end)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(self.move_to_queue_start_btn)
        btn_hbox.addWidget(self.move_to_queue_rnd_btn)
        btn_hbox.addWidget(self.move_to_queue_end_btn)
        self.vbox_right.addLayout(btn_hbox)
        # self.list.itemDoubleClicked.connect(self.add_pdf_note)
        self.tag_tree.itemClicked.connect(self.tree_item_clicked)
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
        tag = item.data(1,1)
        self.load_tags_unused_notes(tag)

    def list_item_clicked(self, item):
        self.parent.set_chosen(item.data(Qt.UserRole), item.text())

    def load_tags_unused_notes(self, tag):
        notes = get_unqueued_notes_for_tag(tag)
        self.fill_list(notes)
        self.tag_displayed = tag
        self.lbl.setText(f"Unqueued Notes for \"{utility.text.trim_if_longer_than(tag, 50)}\"")

    def fill_list(self, notes):
        self.list.clear()
        for ix, n in enumerate(notes):
            icon = self.text_note_icon if not n.is_pdf() else self.pdf_icon
            title_i = QListWidgetItem(icon, n.get_title())
            title_i.setData(Qt.UserRole, QVariant(n.id))
            self.list.insertItem(ix, title_i)

    def fill_tree(self, tags):
        self.tag_tree.clear()
        fmap = utility.tags.to_tag_hierarchy(tags)
        for t, children in fmap.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignLeft)
            ti.setData(1, 1, QVariant(t))
            ti.setIcon(0, self.tag_icon)
            ti.addChildren(self._add_to_tree(children, t + "::"))
            self.tag_tree.addTopLevelItem(ti)
        self.tag_tree.setExpandsOnDoubleClick(True)
        self.tag_tree.expandAll()
        if self.tag_tree.topLevelItemCount() > 0:
            self.load_tags_unused_notes(self.tag_tree.topLevelItem(0).data(1,1))

    def _add_to_tree(self, map, prefix):
        res = []
        for t, children in map.items():
            ti = QTreeWidgetItem([t])
            ti.setTextAlignment(0, Qt.AlignLeft)
            ti.setData(1, 1, QVariant(prefix + t))
            ti.setIcon(0, self.tag_icon)
            prefix_c = prefix + t + "::"
            for c,m in children.items():
                ti.addChildren(self._add_to_tree({c: m}, prefix_c))
            res.append(ti)
        return res

    def refresh(self):
        if self.tag_displayed is not None:
            self.load_tags_unused_notes(self.tag_displayed)

    def move_to_queue_beginning(self):
        sels = self.list.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.HEAD)
        self.parent.refresh_queue_list()
        self.refresh()
       

    def move_to_queue_end(self):
        sels = self.list.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.END)
        self.parent.refresh_queue_list()
        self.refresh()

    def move_to_queue_random(self):
        sels = self.list.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.parent.set_chosen(-1, "")
        update_position(nid, QueueSchedule.RANDOM)
        self.parent.refresh_queue_list()
        self.refresh()
    
    def empty_queue_and_enqueue_all(self):
        if self.tag_displayed is None:
            return
        empty_priority_list()
        notes = get_unqueued_notes_for_tag(self.tag_displayed)
        set_priority_list([n.id for n in notes])
        self.parent.refresh_queue_list()
        self.refresh()

    def enqueue_all(self):
        if self.tag_displayed is None:
            return
        notes = get_unqueued_notes_for_tag(self.tag_displayed)
        queue = _get_priority_list()
        set_priority_list([e.id for e in queue] + [n.id for n in notes])
        self.parent.refresh_queue_list()
        self.refresh()



