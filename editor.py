from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from aqt.utils import showInfo
from anki.utils import isMac
from anki.lang import _
from .notes import *
from .notes import _get_priority_list
from .textutils import trimIfLongerThan

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
        self.form.buttonBox.button(QDialogButtonBox.Close).setShortcut( QKeySequence("Ctrl+Return"))
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

    def reopen(self,mw):
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
    def __init__(self, parent, note_id = None):
        self.note_id = note_id
        QDialog.__init__(self, parent)
        self.mw = aqt.mw
        self.parent = parent
        #self.mw.setupDialogGC(self)
        #self.setWindowModality(Qt.WindowModal)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        self.setup_ui()


    def setup_ui(self):

        if self.note_id is not None:
            self.save = QPushButton("Save")
            self.setWindowTitle('Edit Note')
            self.save.clicked.connect(self.on_update_clicked)
        else:
            self.save = QPushButton("Create")
            self.setWindowTitle('Create a new note')    
            self.save.clicked.connect(self.on_create_clicked)

        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)
        priority_list = _get_priority_list()
        self.priority_list = priority_list

        self.tabs = QTabWidget()
        self.create_tab = CreateTab(self)
        self.priority_tab = PriorityTab(priority_list)
        #self.browse_tab = BrowseTab()
        self.tabs.addTab(self.create_tab, "Create")
        self.tabs.addTab(self.priority_tab, "Queue")
        # tabs.addTab(self.browse_tab, "Browse")
        layout_main = QVBoxLayout()
        layout_main.addWidget(self.tabs)
        self.setLayout(layout_main)
        self.resize(640, 700)
        
        self.exec_()

    def on_create_clicked(self):
        title = self.create_tab.title.text()
        text = self.create_tab.text.toHtml()
        source = self.create_tab.source.text()
        tags = self.create_tab.tag.text()
        queue_schedule = self.create_tab.queue_schedule

        # don't allow for completely empty fields
        if len(title.strip()) + len(text.strip()) == 0:
            return

        create_note(title, text, source, tags, None, "", queue_schedule)
        #aqt.dialogs.close("UserNoteEditor")
        self.reject()


    def on_update_clicked(self):
        title = self.create_tab.title.text()
        text = self.create_tab.text.toHtml()
        source = self.create_tab.source.text()
        tags = self.create_tab.tag.text()
        update_note(self.note_id, title, text, source, tags, "")
        #aqt.dialogs.close("UserNoteEditor")
        self.reject()

    
    def reject(self):
        self.priority_tab.t_view.setModel(None)
        QDialog.reject(self)

    def accept(self):
        self.reject()


class CreateTab(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self) 
        self.queue_schedule = 1
        tmap = get_all_tags_as_hierarchy(False)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["Tags (Click to Add)"])
        self.build_tree(tmap)
        self.tree.itemClicked.connect(self.tree_item_clicked)

        self.note_tree = QTreeWidget()
        self.note_tree.setColumnCount(1)
        self.note_tree.setHeaderLabels(["Recent"])


        note_tree_data = get_note_tree_data()
        for date_str, o_note_list in note_tree_data.items():
            ti = QTreeWidgetItem([date_str])
            for note in o_note_list:
                title = note[1] if note[1] is not None and len(note[1].strip()) > 0 else "Untitled"
                tc = QTreeWidgetItem([title])
                tc.setData(0, 1, QVariant(note[0]))
                ti.addChild(tc)
            self.note_tree.addTopLevelItem(ti)


        self.layout = QHBoxLayout()
        vbox_left = QVBoxLayout()
        vbox_left.addWidget(self.tree)
        self.all_tags_cb = QCheckBox("Show All Tags")
        self.all_tags_cb.stateChanged.connect(self.tag_cb_changed)
        vbox_left.addWidget(self.all_tags_cb)
        vbox_left.addWidget(self.note_tree)

       
        self.layout.addLayout(vbox_left, 33)

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
        f.setPointSize(13)
        self.text.setFont(f)
        self.text.setMinimumHeight(250)
        self.text.setSizePolicy(
            QSizePolicy.Expanding, 
            QSizePolicy.Expanding)
        vbox.addWidget(text_lbl)
        vbox.addWidget(self.text, 2)

        source_lbl = QLabel("Source")
        self.source = QLineEdit()
        vbox.addWidget(source_lbl)
        vbox.addWidget(self.source)
        vbox.addSpacing(18)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        vbox.addWidget(line)

        self.setStyleSheet("""
        QPushButton:hover#q_1 { background-color: lightblue; }
        QPushButton:hover#q_2 { background-color: lightblue; }
        QPushButton:hover#q_3 { background-color: lightblue; }
        QPushButton:hover#q_4 { background-color: lightblue; }
        QPushButton:hover#q_5 { background-color: lightblue; }
        """)


        queue_len = len(parent.priority_list)
        queue_lbl = QLabel("Currently, your reading queue contains <b>%s</b> items" % queue_len)
        vbox.addWidget(queue_lbl)

        self.q_lbl_1 = QPushButton("Don't Add to Queue")
        self.q_lbl_1.setObjectName("q_1")
        self.q_lbl_1.setFlat(True)
        self.q_lbl_1.setStyleSheet("border: 2px solid green; padding: 3px; font-weight: bold;")
        self.q_lbl_1.clicked.connect(lambda: self.queue_selected(1))
        vbox.addWidget(self.q_lbl_1)

        vbox.addSpacing(5)
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.HLine)
        line_sep.setFrameShadow(QFrame.Sunken)
        vbox.addWidget(line_sep)
        vbox.addSpacing(5)

        self.q_lbl_2 = QPushButton("Head")
        self.q_lbl_2.setObjectName("q_2")
        self.q_lbl_2.setFlat(True)
        self.q_lbl_2.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey;")
        self.q_lbl_2.clicked.connect(lambda: self.queue_selected(2))
        vbox.addWidget(self.q_lbl_2)

        self.q_lbl_3 = QPushButton("End of first 3rd")
        self.q_lbl_3.setObjectName("q_3")
        self.q_lbl_3.setFlat(True)
        self.q_lbl_3.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey;")
        self.q_lbl_3.clicked.connect(lambda: self.queue_selected(3))
        vbox.addWidget(self.q_lbl_3)

        self.q_lbl_4 = QPushButton("End of second 3rd")
        self.q_lbl_4.setObjectName("q_4")
        self.q_lbl_4.setFlat(True)
        self.q_lbl_4.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey;")
        self.q_lbl_4.clicked.connect(lambda: self.queue_selected(4))
        vbox.addWidget(self.q_lbl_4)

        self.q_lbl_5 = QPushButton("End")
        self.q_lbl_5.setObjectName("q_5")
        self.q_lbl_5.setFlat(True)
        self.q_lbl_5.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey;")
        self.q_lbl_5.clicked.connect(lambda: self.queue_selected(5))
        vbox.addWidget(self.q_lbl_5)

        vbox.addStretch(1)

        tag_lbl = QLabel("Tags")
        self.tag = QLineEdit()
        vbox.addWidget(tag_lbl)
        vbox.addWidget(self.tag)

        vbox.setAlignment(Qt.AlignTop)
        vbox.addLayout(hbox)
        self.layout.addLayout(vbox, 66)
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
                ti.addChildren(self._add_to_tree(children, prefix_c))
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
        for lbl in [self.q_lbl_1, self.q_lbl_2, self.q_lbl_3, self.q_lbl_4, self.q_lbl_5]:
            lbl.setStyleSheet("border: 2px solid lightgrey; padding: 3px; color: grey; font-weight: normal;")
        [self.q_lbl_1, self.q_lbl_2, self.q_lbl_3, self.q_lbl_4, self.q_lbl_5][queue_schedule-1].setStyleSheet("border: 2px solid green; padding: 3px; font-weight: bold;")
        self.queue_schedule = queue_schedule

class PriorityTab(QWidget):

    def __init__(self, priority_list):
        QWidget.__init__(self)

        model = PriorityListModel(self)
        for c, pitem in enumerate(priority_list):

            # build display text
            source = pitem[3]
            source = "Empty" if source is None or len(source.strip()) == 0 else trimIfLongerThan(source, 100)
            source = "<i>Source: %s</i>" % source
            text = pitem[1] if pitem[1] is not None and len(pitem[1].strip()) > 0 else "Untitled"
            text = "<b>%s</b>" % text
            text += "<br>" + source

            item = QStandardItem(text)
            item.setData(QVariant(pitem[0]))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 0, item)
            titem = QStandardItem(pitem[4])
            titem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 1, titem)
            oitem = QStandardItem()
            oitem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            model.setItem(c, 2, oitem)
       
        model.setHeaderData(0, Qt.Horizontal, "Title & Source")
        model.setHeaderData(1, Qt.Horizontal, "Tags")
        model.setHeaderData(2, Qt.Horizontal, "Actions")
        self.t_view = QTableView()
       
        self.t_view.setItemDelegateForColumn(0, HTMLDelegate())
        self.t_view.setModel(model)

        for r in range(len(priority_list)):
            rem_btn = QPushButton("Remove [Queue]")
            rem_btn.setStyleSheet("border: 1px solid black; border-style: outset; font-size: 10px; background: white; margin: 0px; padding: 3px;")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setMinimumHeight(18)
            rem_btn.clicked.connect(lambda r=r: self.on_remove_clicked(priority_list[r][0]))
         

            h_l = QHBoxLayout()
            h_l.addWidget(rem_btn)

            cell_widget = QWidget()
            cell_widget.setLayout(h_l)
            self.t_view.setIndexWidget(self.t_view.model().index(r,2), cell_widget)


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
        lbl = QLabel("Drag & Drop to reorder")
        self.vbox.addWidget(lbl)
        self.vbox.addWidget(self.t_view)
        self.setLayout(self.vbox)

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
            
            
            rem_btn = QPushButton("Remove [Queue]")
            rem_btn.setStyleSheet("border: 1px solid black; border-style: outset; font-size: 10px; background: white; margin: 0px; padding: 3px;")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setMinimumHeight(18)
            rem_btn.clicked.connect(lambda: self.parent.on_remove_clicked(self.item(row).data()))
         

            h_l = QHBoxLayout()
            h_l.addWidget(rem_btn)
            cell_widget = QWidget()
            cell_widget.setLayout(h_l)
            self.parent.t_view.setIndexWidget(self.index(row,2), cell_widget)
        return success
   

class BrowseTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        # tmap = get_all_tags_as_hierarchy()
        # self.tree = QTreeWidget()
        # self.tree.setColumnCount(1)
        # self.tree.setHeaderLabels(["Tags"])
        # for t, children in tmap.items():
        #     ti = QTreeWidgetItem([t])
        #     ti.addChildren(self._add_to_tree(children))
        #     self.tree.addTopLevelItem(ti)
        # self.tree.itemClicked.connect(self.tree_item_clicked)
        # self.layout = QHBoxLayout()
        # vbox_left = QVBoxLayout()
        # vbox_left.addWidget(self.tree)
        # vbox_right = QVBoxLayout()
        # vbox_right.setAlignment(Qt.AlignTop)
        # vbox_right.addWidget(QLabel("Notes with this tag:"))
        # self.layout.addLayout(vbox_left)
        # self.layout.addLayout(vbox_right)
        # self.setLayout(self.layout)
        
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