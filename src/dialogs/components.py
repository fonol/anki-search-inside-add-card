from aqt.qt import *
import aqt
from ..notes import dynamic_sched_to_str

class QtPrioritySlider(QWidget):


    def __init__(self, prio_default):
        QWidget.__init__(self)

        self.prio_default = prio_default
        self.released_fn = None

        box = QGroupBox("Priority")
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

        box.setLayout(vbox)

        vbox_outer = QVBoxLayout()
        vbox_outer.addWidget(box)
        self.setLayout(vbox_outer)
    
        self.update_lbl()
        self.slider.valueChanged.connect(self.update_lbl)
        self.slider.sliderReleased.connect(self.slider_released)

    def value(self):
        return self.slider.value()

    def reset(self):
        self.slider.setValue(0)
        self.update_lbl()
    
    def set_released_fn(self, fn):
        self.released_fn = fn
    
    def slider_released(self):
        if self.released_fn:
            self.released_fn(self.slider.value())

    def update_lbl(self):
        if self.slider.value() == 0:
            self.value_lbl.setText("No Priority")
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #c62828; border-radius: 3px; }")
        else:
            self.value_lbl.setText(dynamic_sched_to_str(self.slider.value()).replace("(", "(<b>").replace(")", "</b>)"))
            self.slider.setStyleSheet("QSlider::handle:horizontal {background-color: #2496dc; border-radius: 3px;}")

