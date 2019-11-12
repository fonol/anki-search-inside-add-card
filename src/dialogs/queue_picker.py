from aqt.qt import *
from aqt.utils import tooltip
import aqt.editor
import aqt
import functools
import re
import random
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from aqt.utils import showInfo
from anki.utils import isMac
from anki.lang import _


from ..notes import *
from ..notes import _get_priority_list
import utility.text
import utility.misc

class QueuePicker(QDialog):
    """
    Can be used to select a single note from the queue.
    """
    def __init__(self, parent, note_list, note_list_right):
        self.chosen_id = None 
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mw = aqt.mw
        self.parent = parent
        self.setup_ui(note_list, note_list_right)
        self.setWindowTitle("Pick a note to open")

    def setup_ui(self, note_list, note_list_right):

        self.vbox_left = QVBoxLayout()
        l_lbl = QLabel("Queue") 
        l_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_left.addWidget(l_lbl)
        self.t_view_left = QListWidget()

        for ix, n in enumerate(note_list):
            title = n[1] if n[1] is not None and len(n[1]) > 0 else "Untitled"
            title_i = QListWidgetItem(str(ix + 1) + ".  " + title)
            title_i.setData(Qt.UserRole, QVariant(n[0]))
            self.t_view_left.insertItem(ix, title_i)
        
        self.t_view_right = QListWidget()

        for ix, n in enumerate(note_list_right):
            title = n[1] if n[1] is not None and len(n[1]) > 0 else "Untitled"
            title_i = QListWidgetItem(title)
            title_i.setData(Qt.UserRole, QVariant(n[0]))
            self.t_view_right.insertItem(ix, title_i)

        self.vbox_right = QVBoxLayout()
        r_lbl = QLabel("PDF notes, not in Queue") 
        r_lbl.setAlignment(Qt.AlignCenter)
        self.vbox_right.addWidget(r_lbl)
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

        self.t_view_left.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_view_left.itemClicked.connect(self.item_clicked)
        self.t_view_right.itemClicked.connect(self.item_clicked_right_side)
        self.vbox_left.addWidget(self.t_view_left)

        self.unqueue_btn = QPushButton("Dequeue")
        self.unqueue_btn.clicked.connect(self.remove_from_queue)
        btn_hbox_l = QHBoxLayout()
        btn_hbox_l.addWidget(self.unqueue_btn)
        self.vbox_left.addLayout(btn_hbox_l)

        self.vbox = QVBoxLayout()

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.vbox_left)
        self.hbox.addLayout(self.vbox_right)

        self.vbox.addLayout(self.hbox)
        
        bottom_box = QHBoxLayout()
        self.accept_btn = QPushButton("Read")
        self.accept_btn.clicked.connect(self.accept)
        self.chosen_lbl = QLabel("")
        bottom_box.addWidget(self.chosen_lbl)
        bottom_box.addStretch(1)
        bottom_box.addWidget(self.accept_btn)
        bottom_box.addSpacing(8)
        self.reject_btn = QPushButton("Cancel")
        self.reject_btn.clicked.connect(self.reject)
        bottom_box.addWidget(self.reject_btn)
        self.vbox.addSpacing(10)
        self.vbox.addLayout(bottom_box)

        self.setLayout(self.vbox)
        self.resize(600, 420)

    def item_clicked(self, item):
        self.clear_selection("right")
        self.set_chosen(item.data(Qt.UserRole), item.text()[item.text().index(".") + 2:])
    
    def item_clicked_right_side(self, item):
        self.clear_selection("left")
        self.set_chosen(item.data(Qt.UserRole), item.text())

    def set_chosen(self, id, name):
        self.chosen_id = id
        if len(name) > 0:
            self.chosen_lbl.setText("Chosen:  " + name)
        else: 
            self.chosen_lbl.setText("")


    def clear_selection(self, list):
        if list == "left":
            lw = self.t_view_left
        else:
            lw = self.t_view_right
        for i in range(lw.count()):
            lw.item(i).setSelected(False)

    def move_to_queue_beginning(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.set_chosen(-1, "")
        update_position(nid, QueueSchedule.HEAD)
        self.refill_list_views(_get_priority_list(), get_pdf_notes_not_in_queue()) 

    def move_to_queue_end(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.set_chosen(-1, "")
        update_position(nid, QueueSchedule.END)
        self.refill_list_views(_get_priority_list(), get_pdf_notes_not_in_queue()) 

    def move_to_queue_random(self):
        sels = self.t_view_right.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        self.set_chosen(-1, "")
        update_position(nid, QueueSchedule.RANDOM)
        self.refill_list_views(_get_priority_list(), get_pdf_notes_not_in_queue()) 

    def refill_list_views(self, left_list, right_list):
        self.t_view_left.clear()
        self.t_view_right.clear()
        for ix, n in enumerate(left_list):
            title = n[1] if n[1] is not None and len(n[1]) > 0 else "Untitled"
            title_i = QListWidgetItem(str(ix + 1) + ".  " + title)
            title_i.setData(Qt.UserRole, QVariant(n[0]))
            self.t_view_left.insertItem(ix, title_i)

        for ix, n in enumerate(right_list):
            title = n[1] if n[1] is not None and len(n[1]) > 0 else "Untitled"
            title_i = QListWidgetItem(title)
            title_i.setData(Qt.UserRole, QVariant(n[0]))
            self.t_view_right.insertItem(ix, title_i)

    def remove_from_queue(self):
        sels = self.t_view_left.selectedItems()
        if sels is None or len(sels) == 0:
            return
        nid = sels[0].data(Qt.UserRole)
        if self.chosen_id == nid:
            self.set_chosen(-1, "")
        update_position(nid, QueueSchedule.NOT_ADD)
        self.refill_list_views(_get_priority_list(), get_pdf_notes_not_in_queue()) 