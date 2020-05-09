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
from datetime import datetime, timedelta
import utility.date

class QtPrioritySlider(QWidget):


    def __init__(self, prio_default, show_spec_sched=True, schedule=None):
        QWidget.__init__(self)

        self.prio_default = prio_default
        self.released_fn = None
        self._schedule = None
        self.has_schedule = schedule is not None and len(schedule.strip()) > 0
        self.show_spec_sched = show_spec_sched

        box = QGroupBox("Priority and Scheduling" if self.show_spec_sched else "Priority")
        vbox = QVBoxLayout()

        self.slider = QSlider(Qt.Horizontal)
        if prio_default is not None and prio_default >= 0:
            self.slider.setValue(prio_default)
        else:
            self.slider.setValue(0)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        vbox.addWidget(self.slider)

        self.value_lbl = QLabel(str(prio_default))
        self.value_lbl.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.value_lbl)

        if show_spec_sched:
            bg = QButtonGroup()
            if self.has_schedule:
                s_rep_label = QLabel(utility.date.schedule_verbose(schedule))
                s_rep_label.setAlignment(Qt.AlignCenter)
                vbox.addWidget(s_rep_label)
                self.no_sched_rb = QRadioButton("Keep schedule")
            else:
                self.no_sched_rb = QRadioButton("No specific schedule")
            self.no_sched_rb.setChecked(True)
            self.td_rb = QRadioButton("Show in [n] days:")
            self.tpwd_rb = QRadioButton("Show on weekday(s):")
            self.tpd_rb = QRadioButton("Show every [n]th day:")

            for rb in [self.no_sched_rb, self.td_rb, self.tpwd_rb, self.tpd_rb]:
                rb.clicked.connect(self.sched_radio_clicked)

            vbox.addWidget(self.no_sched_rb)
            if self.has_schedule:
                self.remove_sched_rb = QRadioButton("Remove schedule")
                vbox.addWidget(self.remove_sched_rb)

            # time delta
            hbox1 = QHBoxLayout()
            self.container1 = QWidget()
            self.container1.setLayout(hbox1)
            self.td_inp = QLineEdit()
            val = QIntValidator()
            self.td_inp.setValidator(val)
            tomorrow_btn = QPushButton("Tomorrow")
            tomorrow_btn.clicked.connect(lambda: self.td_inp.setText("1"))
            week_btn = QPushButton("In 7 days")
            week_btn.clicked.connect(lambda: self.td_inp.setText("7"))
            hbox1.addWidget(self.td_inp)
            hbox1.addWidget(tomorrow_btn)
            hbox1.addWidget(week_btn)
            vbox.addWidget(self.td_rb)
            vbox.addWidget(self.container1)

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
            vbox.addWidget(self.tpwd_rb)
            vbox.addWidget(self.container2)

            # intervals in days
            hbox3 = QHBoxLayout()
            self.container3 = QWidget()
            self.container3.setLayout(hbox3)
            self.tpd_inp = QLineEdit()
            self.tpd_inp.setValidator(val)
        
            hbox3.addWidget(self.tpd_inp)
            hbox3.addStretch(1) 
            vbox.addWidget(self.tpd_rb)
            vbox.addWidget(self.container3)

            if schedule is not None and len(schedule.strip()) > 0:
                self.parse_schedule(schedule)
                self._schedule = schedule

        box.setLayout(vbox)

        vbox_outer = QVBoxLayout()
        vbox_outer.addWidget(box)
        self.setLayout(vbox_outer)
    
        self.update_lbl()
        if show_spec_sched:
            self.sched_radio_clicked()
        self.slider.valueChanged.connect(self.update_lbl)
        self.slider.sliderReleased.connect(self.slider_released)

    def value(self):
        return self.slider.value()
    
    def has_changed_value(self):
        return self.value() != self.prio_default

    def schedule(self):
        new = self._get_schedule()
        # None means no specific schedule given
        if new is None:
            return self._schedule
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
                if self.has_schedule:
                    self.remove_sched_rb.setChecked(True)
                    self.no_sched_rb.setEnabled(False)
                else:
                    self.no_sched_rb.setChecked(True)

                self.td_rb.setEnabled(False)
                self.tpd_rb.setEnabled(False)
                self.tpwd_rb.setEnabled(False)
                self.sched_radio_clicked()
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #c62828; border-radius: 3px; }")
        else:
            self.value_lbl.setText(dynamic_sched_to_str(self.slider.value()).replace("(", "(<b>").replace(")", "</b>)"))
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #2496dc; border-radius: 3px;}")
            if self.show_spec_sched:
                self.td_rb.setEnabled(True)
                self.tpd_rb.setEnabled(True)
                self.tpwd_rb.setEnabled(True)
                self.no_sched_rb.setEnabled(True)

                if self.has_schedule:
                    self.remove_sched_rb.setEnabled(True)


    def sched_radio_clicked(self):
        if self.no_sched_rb.isChecked() or (self.has_schedule and self.remove_sched_rb.isChecked()):
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
        due = schedule.split("|")[1]
        stype = schedule.split("|")[2]

        if stype.startswith("td:"):
            self.td_inp.setText(stype[3:])
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
            self.tpd_inp.setText(stype[3:])

    def _get_schedule(self):
        if self.no_sched_rb.isChecked():
            return None
        if self.has_schedule and self.remove_sched_rb.isChecked():
            return ""
        now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        if self.td_rb.isChecked():
            val = self.td_inp.text()
            if val is None or len(val) == 0 or int(val) <= 0:
                return None
            due = (datetime.now() + timedelta(days=int(val))).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|td:{val}"
        if self.tpd_rb.isChecked():
            val = self.tpd_inp.text()
            if val is None or len(val) == 0 or int(val) <= 0:
                return None
            due = (datetime.now() + timedelta(days=int(val))).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|id:{val}"
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
            next = [int(d) for d in wds if int(d) > today + 1]
            if len(next) > 0:
                next_date = next[0]
            else:
                next_date = int(wds[0:1])
            n = (next_date - 1 - today) % 7 
            due = (datetime.now() + timedelta(days=n)).strftime('%Y-%m-%d-%H-%M-%S')
            return f"{now}|{due}|wd:{wds}"

                

            
            
