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
from aqt.qt import *
import aqt
import functools
import typing
from typing import Optional
from enum import Enum, unique
from ..notes import dynamic_sched_to_str, find_notes_with_similar_prio, get_avg_priority, get_note, find_notes, find_unqueued_notes, find_suggested_unqueued_notes
from .calendar_dialog import CalendarDialog
from ..config import get_config_value_or_default, update_config
from ..models import SiacNote
from ..hooks import run_hooks

from datetime import datetime, timedelta
import utility.date
import utility.misc
import utility.text

class QtPrioritySlider(QWidget):


    def __init__(self, prio_default, nid, show_spec_sched=True, schedule=None, show_similar=True):
        QWidget.__init__(self)

        self.prio_default       = prio_default
        self.released_fn        = None
        self.has_schedule       = schedule is not None and len(schedule.strip()) > 0
        self.show_spec_sched    = show_spec_sched
        self.nid                = nid
        self.note               = None
        self.show_similar       = show_similar
        if nid and nid > 0:
            self.note           = get_note(self.nid)
            self.note_title     = self.note.get_title()
        self.avg_prio           = round(get_avg_priority(), 1)

        box                     = QGroupBox("Priority and Scheduling" if self.show_spec_sched else "Priority")
        vbox                    = QVBoxLayout()
        vbox.setContentsMargins(7,7,7,7)

        self.slider             = QSlider(Qt.Orientation.Horizontal)

        if prio_default is not None and prio_default >= 0:
            self.slider.setValue(prio_default)
        else:
            self.slider.setValue(0)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        vbox.addWidget(self.slider)

        self.value_lbl          = QLabel(str(prio_default))
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        hvalue                  = QHBoxLayout()
        hvalue.addSpacing(40)
        hvalue.addStretch()
        hvalue.addWidget(self.value_lbl)
        hvalue.addStretch()

        avg_lbl                 = QLabel(f"Ø: {self.avg_prio}")
        avg_lbl.setStyleSheet(f"padding-left: 4px; padding-right: 4px; color: white; background-color: {utility.misc.prio_color(self.avg_prio)};")
        avg_lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        hvalue.addWidget(avg_lbl)
        vbox.addLayout(hvalue)

        if not self.show_spec_sched and self.nid and self.show_similar:
            self.similar = QLabel("")
            vbox.addWidget(self.similar)

        if show_spec_sched:
            self.scheduler = QtScheduleComponent(schedule)
            vbox.addWidget(self.scheduler)

        box.setLayout(vbox)

        vbox_outer              = QVBoxLayout()
        vbox_outer.setContentsMargins(0,0,0,0)
        vbox_outer.addWidget(box)
        self.setLayout(vbox_outer)

        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.update_lbl()
        self.slider.valueChanged.connect(self.update_lbl)
        self.slider.sliderReleased.connect(self.slider_released)

        if not show_spec_sched:
            self.slider_released()

    def value(self):
        return self.slider.value()

    def has_changed_value(self):
        return self.value() != self.prio_default

    def schedule(self):
        return self.scheduler.schedule() 

    def reset(self):
        self.slider.setValue(0)
        self.update_lbl()

    def set_released_fn(self, fn):
        self.released_fn = fn

    def slider_released(self):
        if self.released_fn:
            self.released_fn(self.slider.value())


    def update_lbl(self):
        """
        Called when slider is moved.
        """
        if self.slider.value() == 0:
            self.value_lbl.setText("No Priority")
            # If 0 priority, disable setting specific schedule
            if self.show_spec_sched:
                self.scheduler.priority_set_to_zero()
            elif self.nid and self.show_similar:
                self.similar.setText(f"<br>Info: A note without a priority won't appear in <br>the queue, unless it has a schedule<br>which is due on that day.")
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #f0506e; border-radius: 3px; }")

        else:
            self.value_lbl.setText(dynamic_sched_to_str(self.slider.value()).replace("(", "(<b>").replace(")", "</b>)"))
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #2496dc; border-radius: 3px;}")
            if self.show_spec_sched:
                self.scheduler.priority_set_to_non_zero()
            elif self.nid and self.show_similar:
                val = self.slider.value()
                if self.nid is not None:
                    similar = find_notes_with_similar_prio(self.nid, val)
                    if similar and len(similar) > 0:
                        if self.note:
                            similar.append((val, self.nid, self.note_title))
                        txt = ""
                        for (p, nid, title) in sorted(similar, key=lambda x: x[0], reverse=True):
                            title   = utility.text.trim_if_longer_than(title, 50)
                            if nid == self.nid:
                                title = f"<font color='#2496dc'><b>{title}</b></font>"
                            txt     = f"{txt}<b>{int(p)}</b>:  {title}<br>"
                        self.similar.setText(f"Similar Priority: <br><br>" + txt)
                    else:
                        self.similar.setText(f"Similar Priority: <br><br>No results." )


class QtScheduleComponent(QWidget):

    def __init__(self, schedule):
        QWidget.__init__(self)

        self.initial_schedule   = schedule
        self.initial_stype      = schedule.split("|")[2][0:2] if self.initial_schedule and len(self.initial_schedule.strip()) > 0 else None

        self.has_schedule       = self.initial_schedule is not None and len(self.initial_schedule.strip()) > 0
        self.setup_ui()


    def setup_ui(self):

        self.edit_tab       = ScheduleEditTab(self)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.edit_tab)

    def schedule(self):
        new = self._get_schedule()
        # None means no specific schedule given
        if new is None:
            return self.initial_schedule
        return new

    def _get_schedule(self):
        return self.edit_tab._get_schedule()

    def schedule_has_changed(self) -> bool:
        new = self._get_schedule()
        if (self.initial_schedule is None or self.initial_schedule == "") and (new is None or new == ""):
            return False
        return new != self.initial_schedule

    def priority_set_to_zero(self):
        self.edit_tab.sched_radio_clicked()

    def priority_set_to_non_zero(self):
        self.edit_tab.td_rb.setEnabled(True)
        self.edit_tab.tpd_rb.setEnabled(True)
        self.edit_tab.tpwd_rb.setEnabled(True)
        self.edit_tab.no_sched_rb.setEnabled(True)

        if self.has_schedule:
            self.edit_tab.remove_sched_rb.setEnabled(True)



# Unused atm (10.10.20)
class ScheduleSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())

        header          = QLabel("General scheduling settings")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(header)

        line            = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout().addWidget(line)

        self.layout().addStretch()

        self.show_sched_cb = QCheckBox("Show schedule dialog after done with unsched. note")
        self.layout().addWidget(self.show_sched_cb)
        self.show_sched_cb.setChecked(get_config_value_or_default("notes.queue.scheduleDialogOnDoneUnscheduledNotes", False))
        self.show_sched_cb.clicked.connect(self.show_sched_cb_clicked)

        self.ivl_includes_today_cb = QCheckBox("Periodic schedules start on the current day")
        self.layout().addWidget(self.ivl_includes_today_cb)
        self.ivl_includes_today_cb.setChecked(get_config_value_or_default("notes.queue.intervalSchedulesStartToday", True))
        self.ivl_includes_today_cb.clicked.connect(self.ivl_includes_today_cb_checked)




    def show_sched_cb_clicked(self):
        update_config("notes.queue.scheduleDialogOnDoneUnscheduledNotes", self.show_sched_cb.isChecked())

    def ivl_includes_today_cb_checked(self):
        update_config("notes.queue.intervalSchedulesStartToday", self.ivl_includes_today_cb.isChecked())
        run_hooks("updated-schedule")

    def missed_rb_clicked(self):
        if self.missed_rb_1.isChecked():
            new_val = "place-front"
        elif self.missed_rb_2.isChecked():
            new_val = "remove-schedule"
        else:
            new_val = "new-schedule"
        update_config("notes.queue.missedNotesHandling", new_val)
        SiacNote.MISSED_NOTES = new_val


class ScheduleEditTab(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self)
        self.parent = parent
        self.vbox   = QVBoxLayout()
        self.vbox.setSpacing(0)

        self.group  = QButtonGroup()
        if self.parent.has_schedule:

            s_rep_label         = QLabel(utility.date.schedule_verbose(self.parent.initial_schedule))
            s_rep_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vbox.addWidget(s_rep_label)

            line                = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            self.vbox.addSpacing(5)
            self.vbox.addWidget(line)
            self.vbox.addSpacing(5)

            self.no_sched_rb    = QRadioButton("Keep schedule")
        else:
            self.no_sched_rb = QRadioButton("No specific schedule")

        self.no_sched_rb.setChecked(True)
        self.td_rb      = QRadioButton("Show in ")
        self.tpwd_rb    = QRadioButton("Show on weekday(s):")
        self.tpd_rb     = QRadioButton("Show every ")
        self.tgd_rb     = QRadioButton("Growing Ivl.")
        self.group.addButton(self.no_sched_rb, 0)
        self.group.addButton(self.td_rb, 1)
        self.group.addButton(self.tpwd_rb, 2)
        self.group.addButton(self.tpd_rb, 3)
        self.group.addButton(self.tgd_rb, 4)

        for rb in [self.no_sched_rb, self.td_rb, self.tpwd_rb, self.tpd_rb, self.tgd_rb]:
            rb.clicked.connect(self.sched_radio_clicked)

        self.vbox.addWidget(self.no_sched_rb)
        if self.parent.has_schedule:
            self.remove_sched_rb = QRadioButton("Remove schedule")
            self.group.addButton(self.remove_sched_rb, 4)
            self.vbox.addWidget(self.remove_sched_rb)

        # time delta
        hbox1 = QHBoxLayout()
        self.td_inp = QDoubleSpinBox()
        self.td_inp.setMinimum(1)
        self.td_inp.setMaximum(10000)
        self.td_inp.setDecimals(0)
        self.td_inp.setSuffix(" day(s)")

        hbox1.addWidget(self.td_rb)
        hbox11 = QHBoxLayout()
        hbox11.addWidget(self.td_inp)
        cal_btn = QToolButton()
        cal_btn.setText("Date")
        cal_btn.clicked.connect(self.cal_btn_clicked)
        hbox11.addWidget(cal_btn)

        self.container1 = QWidget()
        self.container1.setLayout(hbox11)
        hbox1.addWidget(self.container1)
        # self.vbox.addWidget(self.td_rb)
        self.vbox.addLayout(hbox1)

        # weekdays
        hbox2 = QHBoxLayout()
        self.container2 = QWidget()
        self.container2.setLayout(hbox2)
        self.mon_cb = QCheckBox("M")
        self.tue_cb = QCheckBox("T")
        self.wed_cb = QCheckBox("W")
        self.thu_cb = QCheckBox("T")
        self.fri_cb = QCheckBox("F")
        self.sat_cb = QCheckBox("S")
        self.sun_cb = QCheckBox("S")
        hbox2.addWidget(self.mon_cb)
        hbox2.addWidget(self.tue_cb)
        hbox2.addWidget(self.wed_cb)
        hbox2.addWidget(self.thu_cb)
        hbox2.addWidget(self.fri_cb)
        hbox2.addWidget(self.sat_cb)
        hbox2.addWidget(self.sun_cb)
        self.vbox.addWidget(self.tpwd_rb)
        self.vbox.addWidget(self.container2)

        # intervals in days
        hbox3 = QHBoxLayout()
        self.tpd_inp = QDoubleSpinBox()
        self.tpd_inp.setMinimum(1)
        self.tpd_inp.setDecimals(0)
        self.tpd_inp.setSuffix(" day(s)")

        hbox3.addWidget(self.tpd_rb)
        hbox33 = QHBoxLayout()
        hbox33.addWidget(self.tpd_inp)
        self.container3 = QWidget()
        self.container3.setLayout(hbox33)
        hbox3.addWidget(self.container3)
        self.vbox.addLayout(hbox3)

        # intervals with growth factor
        hbox4 = QHBoxLayout()
        self.tgd_inp = QDoubleSpinBox()
        self.tgd_inp.setMinimum(1)
        self.tgd_inp.setDecimals(0)
        self.tgd_inp.setSuffix(" day(s) start ivl")

        self.fac_inp = QDoubleSpinBox()
        self.fac_inp.setMinimum(1)
        self.fac_inp.setDecimals(1)
        self.fac_inp.setValue(1.2)
        self.fac_inp.setSingleStep(0.1)
        self.fac_inp.setPrefix("Factor ")

        hbox4.addWidget(self.tgd_rb)
        hbox44 = QHBoxLayout()
        hbox44.addWidget(self.tgd_inp)
        hbox44.addWidget(self.fac_inp)
        self.container4 = QWidget()
        self.container4.setLayout(hbox44)
        hbox4.addWidget(self.container4)
        self.vbox.addLayout(hbox4)

        self.vbox.setContentsMargins(0,0,0,0)
        self.vbox.addStretch(1)
        self.setLayout(self.vbox)

        self.sched_radio_clicked()

        if self.parent.has_schedule:
            self.parse_schedule(self.parent.initial_schedule)
            self._schedule = self.parent.initial_schedule

    def sched_radio_clicked(self):
        if self.no_sched_rb.isChecked() or (self.parent.has_schedule and self.remove_sched_rb.isChecked()):
            self.container1.setEnabled(False)
            self.container2.setEnabled(False)
            self.container3.setEnabled(False)
            self.container4.setEnabled(False)
        elif self.td_rb.isChecked():
            self.container1.setEnabled(True)
            self.container2.setEnabled(False)
            self.container3.setEnabled(False)
            self.container4.setEnabled(False)

        elif self.tpd_rb.isChecked():
            self.container1.setEnabled(False)
            self.container2.setEnabled(False)
            self.container3.setEnabled(True)
            self.container4.setEnabled(False)

        elif self.tpwd_rb.isChecked():
            self.container1.setEnabled(False)
            self.container2.setEnabled(True)
            self.container3.setEnabled(False)
            self.container4.setEnabled(False)

        elif self.tgd_rb.isChecked():
            self.container1.setEnabled(False)
            self.container2.setEnabled(False)
            self.container3.setEnabled(False)
            self.container4.setEnabled(True)

    def cal_btn_clicked(self):
        dialog = CalendarDialog(self)
        if dialog.exec():
           date = dialog.date
           if date:
               diff = (date - datetime.today().date()).days
               if diff > 0:
                   self.td_inp.setValue(diff)

    def parse_schedule(self, schedule):
        stype   = schedule.split("|")[2]

        if stype.startswith("td:"):
            self.td_inp.setValue(float(stype[3:]))
        elif stype.startswith("wd:"):
            for d in stype[3:]:
                if d == "1": self.mon_cb.setChecked(True)
                elif d == "2": self.tue_cb.setChecked(True)
                elif d == "3": self.wed_cb.setChecked(True)
                elif d == "4": self.thu_cb.setChecked(True)
                elif d == "5": self.fri_cb.setChecked(True)
                elif d == "6": self.sat_cb.setChecked(True)
                elif d == "7": self.sun_cb.setChecked(True)
        elif stype.startswith("id:"):
            self.tpd_inp.setValue(float(stype[3:]))
        elif stype.startswith("gd:"):
            sval    = stype[3:]
            factor  = float(sval.split(";")[0])
            ivl     = float(sval.split(";")[1])
            self.tgd_inp.setValue(int(ivl))
            self.fac_inp.setValue(factor)


    def _get_schedule(self):
        if self.no_sched_rb.isChecked():
            return self.parent.initial_schedule
        if self.parent.has_schedule and self.remove_sched_rb.isChecked():
            return ""
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

        # in x days
        if self.td_rb.isChecked():
            val = self.td_inp.value()
            if val is None or int(val) <= 0:
                return None
            val = int(val)
            due = (datetime.now() + timedelta(days=int(val))).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|td:{val}"

        # every x days
        if self.tpd_rb.isChecked():
            val = self.tpd_inp.value()
            if val is None or int(val) <= 0:
                return None
            val = int(val)

            if get_config_value_or_default("notes.queue.intervalSchedulesStartToday", True):
                due = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            else:
                due = (datetime.now() + timedelta(days=int(val))).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|id:{val}"

        # weekday checkboxes
        if self.tpwd_rb.isChecked():
            wds = ""
            if self.mon_cb.isChecked(): wds += "1"
            if self.tue_cb.isChecked(): wds += "2"
            if self.wed_cb.isChecked(): wds += "3"
            if self.thu_cb.isChecked(): wds += "4"
            if self.fri_cb.isChecked(): wds += "5"
            if self.sat_cb.isChecked(): wds += "6"
            if self.sun_cb.isChecked(): wds += "7"
            if len(wds) == 0:
                return None

            today = datetime.now().weekday()
            if get_config_value_or_default("notes.queue.intervalSchedulesStartToday", True):
                next = [int(d) for d in wds if int(d) >= today + 1]
            else:
                next = [int(d) for d in wds if int(d) > today + 1]
            if len(next) > 0:
                next_date = next[0]
            else:
                next_date = int(wds[0:1])
            n = (next_date - 1 - today) % 7
            due = (datetime.now() + timedelta(days=n)).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|wd:{wds}"

        if self.tgd_rb.isChecked():
            # edge case: check if schedule is equal to initial schedule is not straightforward here:
            # initial schedule might have ivl with decimals, but the slider only knows whole numbers for the start interval

            factor = self.fac_inp.value()
            start  = self.tgd_inp.value()
            if self.parent.has_schedule and self.parent.initial_stype == "gd":
                orig_stype      = self.parent.initial_schedule.split("|")[2]
                orig_sval       = orig_stype[3:]
                orig_fac        = float(orig_sval.split(";")[0])
                orig_ivl        = float(orig_sval.split(";")[1])
                if orig_fac == factor and int(orig_ivl) == start:
                    return self.parent.initial_schedule

            due = (datetime.now() + timedelta(days=int(start))).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|gd:{factor};{start}"


class MDTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(QTextEdit, self).__init__(parent)
        self.text_was_pasted = False

    def setMarkdown(self, markdown):
        if "setMarkdown" in QTextEdit.__dict__:
            super(MDTextEdit, self).setMarkdown(markdown)
        else:
            self.setPlainText(markdown)

    def toMarkdown(self):
        if 'toMarkdown' in QTextEdit.__dict__:
            return super(MDTextEdit, self).toMarkdown()
        else:
            return self.toPlainText()

    def insertFromMimeData(self, source):

        super(MDTextEdit, self).insertFromMimeData(source)
        if source.hasText():
            self.text_was_pasted = True


class ClickableQLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None, hover_effect=False):
        QLabel.__init__(self, parent)
        self.hover_effect = hover_effect


    def enterEvent(self, event):
        if self.hover_effect:
            self.setStyleSheet("color: #2496dc")

    def leaveEvent(self, event):
        if self.hover_effect:
            self.setStyleSheet("color: none")

    def mousePressEvent(self, evt):
        self.clicked.emit()

class ClickableQWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

    def mousePressEvent(self, evt):
        self.clicked.emit()

# WIP
class DueCalendar(QCalendarWidget):

  def __init__(self,  parent=None):
    QCalendarWidget.__init__(self,parent)

  def paintCell(self, painter, rect, date):
    QCalendarWidget.paintCell(self, painter, rect, date)

    painter.drawText(rect.bottomLeft(), "test")




@unique
class NoteSelectorMode(Enum):
    UNQUEUED    = 1
    QUEUED      = 2
    ALL         = 3


class NoteSelector(QWidget):

    def __init__(self, parent, mode : NoteSelectorMode, nid: Optional[int] = None):
        QWidget.__init__(self, parent)

        self.mode           = mode
        self.selected_ids   = []
        self.selected_notes = []
        self.nid            = nid

        self.setup_ui()
        self.refresh_search_results()

    def setup_ui(self):

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(3)

        lbl_sel = QLabel("Selection")
        lbl_sel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_sel)
        self.selected_list = QTableWidget()
        self.selected_list.setColumnCount(3)
        self.selected_list.setHorizontalHeaderLabels(["", "Title", "Type"])
        self.selected_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.selected_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.selected_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.selected_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.selected_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.selected_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.selected_list.setMaximumHeight(80)
        self.layout.addWidget(self.selected_list)

        self.layout.addSpacing(10)

        self.input  = QLineEdit()
        self.input.textChanged.connect(self.refresh_search_results)
        self.input.setPlaceholderText("Type to search")
        self.layout.addWidget(self.input)
        self.lbl_sr = QLabel("Search Results")
        self.lbl_sr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.lbl_sr)
        self.list = QTableWidget()
        self.list.setColumnCount(3)
        self.list.setHorizontalHeaderLabels(["", "Title", "Type"])
        self.list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.layout.addWidget(self.list)

        self.setLayout(self.layout)

    def refresh(self):
        self.refresh_selection()
        self.refresh_search_results()

    def refresh_selection(self):

        self.selected_list.clear()
        self._fill_list(self.selected_list, self.selected_notes)


    def refresh_search_results(self):
        notes = []
        query = self.input.text()
        if len(query.strip()) > 0:
            self.lbl_sr.setText("Search Results")
            if self.mode == NoteSelectorMode.UNQUEUED:
                notes = find_unqueued_notes(query)
            elif self.mode == NoteSelectorMode.ALL:
                notes = find_notes(query)
        else:
            if self.nid:
                self.lbl_sr.setText("Suggested")
                if self.mode == NoteSelectorMode.UNQUEUED:
                    notes = find_suggested_unqueued_notes(self.nid)



        notes = [n for n in notes if n.id != self.nid and n.id not in self.selected_ids][:50]
        self._current = notes
        self._fill_list(self.list, notes)

    def _fill_list(self, list, notes):


        list.clear()
        list.setRowCount(len(notes))

        list.setHorizontalHeaderLabels(["", "Title", "Type"])

        for ix, n in enumerate(notes):

            cb = QCheckBox()
            if n.id in self.selected_ids:
                cb.setChecked(True)
            cb.stateChanged.connect(functools.partial(self.cb_clicked, ix, n.id))
            cw = ClickableQWidget()
            cw.clicked.connect(functools.partial(self.cb_outer_clicked, cb))
            lcb = QHBoxLayout()
            cw.setLayout(lcb)
            lcb.addWidget(cb)
            lcb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lcb.setContentsMargins(0,0,0,0)

            title = QTableWidgetItem(n.get_title())
            title.setData(Qt.ItemDataRole.UserRole, QVariant(n.id))

            ntype = QTableWidgetItem(n.get_note_type())

            list.setCellWidget(ix, 0, cw)
            list.setItem(ix, 1, title)
            list.setItem(ix, 2, ntype)

        list.resizeRowsToContents()

    def cb_clicked(self, ix, nid, state):
        if state == Qt.CheckState.Checked:
            self.selected_ids.append(nid)
            self.selected_notes.append([n for n in self._current if n.id == nid][0])
        else:
            del self.selected_ids[self.selected_ids.index(nid)]
            self.selected_notes = [n for n in self.selected_notes if n.id != nid]

        self.refresh()

    def cb_outer_clicked(self, cb):
        cb.setChecked(not cb.checkState() == Qt.CheckState.Checked)
