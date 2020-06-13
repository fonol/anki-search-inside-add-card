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
import aqt
from ..notes import dynamic_sched_to_str
from ..config import get_config_value_or_default, update_config
from ..models import SiacNote

from datetime import datetime, timedelta
import utility.date

class QtPrioritySlider(QWidget):


    def __init__(self, prio_default, show_spec_sched=True, schedule=None):
        QWidget.__init__(self)

        self.prio_default       = prio_default
        self.released_fn        = None
        self.has_schedule       = schedule is not None and len(schedule.strip()) > 0
        self.show_spec_sched    = show_spec_sched

        box                     = QGroupBox("Priority and Scheduling" if self.show_spec_sched else "Priority")
        vbox                    = QVBoxLayout()

        self.slider             = QSlider(Qt.Horizontal)

        if prio_default is not None and prio_default >= 0:
            self.slider.setValue(prio_default)
        else:
            self.slider.setValue(0)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        vbox.addWidget(self.slider)

        self.value_lbl          = QLabel(str(prio_default))
        self.value_lbl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.value_lbl)

        if show_spec_sched:
            self.scheduler = QtScheduleComponent(schedule) 
            vbox.addWidget(self.scheduler)

        box.setLayout(vbox)

        vbox_outer              = QVBoxLayout()
        vbox_outer.addWidget(box)
        self.setLayout(vbox_outer)
    
        self.update_lbl()
        if show_spec_sched:
            self.scheduler.edit_tab.sched_radio_clicked()
        self.slider.valueChanged.connect(self.update_lbl)
        self.slider.sliderReleased.connect(self.slider_released)

    def value(self):
        return self.slider.value()
    
    def has_changed_value(self):
        return self.value() != self.prio_default

    def schedule(self):
        new = self.scheduler._get_schedule()
        # None means no specific schedule given
        if new is None:
            return self.scheduler.initial_schedule
        return new

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
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #c62828; border-radius: 3px; }")
        else:
            self.value_lbl.setText(dynamic_sched_to_str(self.slider.value()).replace("(", "(<b>").replace(")", "</b>)"))
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #2496dc; border-radius: 3px;}")
            if self.show_spec_sched:
                self.scheduler.priority_set_to_non_zero()

            
class QtScheduleComponent(QWidget):

    def __init__(self, schedule):
        QWidget.__init__(self)

        self.initial_schedule   = schedule
        self.has_schedule       = self.initial_schedule is not None and len(self.initial_schedule.strip()) > 0
        self.setup_ui()
            
        
    def setup_ui(self):

        self.tabs           = QTabWidget()
        self.edit_tab       = ScheduleEditTab(self)
        self.settings_tab   = ScheduleSettingsTab()
        
        self.tabs.addTab(self.edit_tab, "Edit")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.tabs)

    def _get_schedule(self):
        return self.edit_tab._get_schedule()

    def priority_set_to_zero(self):
        if self.has_schedule:
            self.edit_tab.remove_sched_rb.setChecked(True)
            self.edit_tab.no_sched_rb.setEnabled(False)
        else:
            self.edit_tab.no_sched_rb.setChecked(True)

        self.edit_tab.td_rb.setEnabled(False)
        self.edit_tab.tpd_rb.setEnabled(False)
        self.edit_tab.tpwd_rb.setEnabled(False)
        self.edit_tab.sched_radio_clicked()

    def priority_set_to_non_zero(self):
        self.edit_tab.td_rb.setEnabled(True)
        self.edit_tab.tpd_rb.setEnabled(True)
        self.edit_tab.tpwd_rb.setEnabled(True)
        self.edit_tab.no_sched_rb.setEnabled(True)

        if self.has_schedule:
            self.edit_tab.remove_sched_rb.setEnabled(True)

class ScheduleSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        
        header          = QLabel("General scheduling settings")
        header.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(header)

        line            = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout().addWidget(line)

        self.layout().addWidget(QLabel("How to deal with <b>missed schedules</b>?"))
        self.missed_rb_1 = QRadioButton("Place in front of queue")
        self.missed_rb_2 = QRadioButton("Remove schedule, keep in queue")
        self.missed_rb_3 = QRadioButton("Reschedule based on previous schedule")
        
        self.layout().addWidget(self.missed_rb_1)
        self.layout().addWidget(self.missed_rb_2)
        self.layout().addWidget(self.missed_rb_3)

        self.missed_rb_1.clicked.connect(self.missed_rb_clicked)
        self.missed_rb_2.clicked.connect(self.missed_rb_clicked)
        self.missed_rb_3.clicked.connect(self.missed_rb_clicked)

        handling = get_config_value_or_default("notes.queue.missedNotesHandling", "remove-schedule")
        if handling == "remove-schedule":
            self.missed_rb_2.setChecked(True)
        elif handling == "place-front":
            self.missed_rb_1.setChecked(True)
        elif handling == "new-schedule":
            self.missed_rb_3.setChecked(True)
        
        self.layout().addWidget(QLabel("Changes for this setting will take effect after a restart."))
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
        self.group  = QButtonGroup()
        if self.parent.has_schedule:

            s_rep_label         = QLabel(utility.date.schedule_verbose(self.parent.initial_schedule))
            s_rep_label.setAlignment(Qt.AlignCenter)
            self.vbox.addWidget(s_rep_label)

            line                = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            self.vbox.addWidget(line)

            self.no_sched_rb    = QRadioButton("Keep schedule")
        else:
            self.no_sched_rb = QRadioButton("No specific schedule")

        self.no_sched_rb.setChecked(True)
        self.td_rb      = QRadioButton("Show in ")
        self.tpwd_rb    = QRadioButton("Show on weekday(s):")
        self.tpd_rb     = QRadioButton("Show every ")
        self.group.addButton(self.no_sched_rb, 0)
        self.group.addButton(self.td_rb, 1)
        self.group.addButton(self.tpwd_rb, 2)
        self.group.addButton(self.tpd_rb, 3)
        

        for rb in [self.no_sched_rb, self.td_rb, self.tpwd_rb, self.tpd_rb]:
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
        self.td_inp.setDecimals(0)
        self.td_inp.setSuffix(" day(s)")

        hbox1.addWidget(self.td_rb)
        hbox11 = QHBoxLayout()
        hbox11.addWidget(self.td_inp)

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
        # self.tpd_inp.setValidator(val)
    
        hbox3.addWidget(self.tpd_rb)
        hbox33 = QHBoxLayout()
        hbox33.addWidget(self.tpd_inp)
        self.container3 = QWidget()
        self.container3.setLayout(hbox33)
        hbox3.addWidget(self.container3)
        self.vbox.addLayout(hbox3)
        self.setLayout(self.vbox)

        if self.parent.has_schedule:
            self.parse_schedule(self.parent.initial_schedule)
            self._schedule = self.parent.initial_schedule

    def sched_radio_clicked(self):
        if self.no_sched_rb.isChecked() or (self.parent.has_schedule and self.remove_sched_rb.isChecked()):
            self.container1.setEnabled(False)
            self.container2.setEnabled(False)
            self.container3.setEnabled(False)
        elif self.td_rb.isChecked():
            self.container1.setEnabled(True)
            self.container2.setEnabled(False)
            self.container3.setEnabled(False)
        
        elif self.tpd_rb.isChecked():
            self.container1.setEnabled(False)
            self.container2.setEnabled(False)
            self.container3.setEnabled(True)

        elif self.tpwd_rb.isChecked():
            self.container1.setEnabled(False)
            self.container2.setEnabled(True)
            self.container3.setEnabled(False)

    def parse_schedule(self, schedule):
        created = schedule.split("|")[0]
        due     = schedule.split("|")[1]
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

    def _get_schedule(self):
        if self.no_sched_rb.isChecked():
            return None
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