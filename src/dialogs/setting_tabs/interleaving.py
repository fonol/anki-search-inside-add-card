from aqt.qt import *
from aqt import mw

import state
from aqt.utils import showInfo
from ...config import get_config_value, update_config


class setting_tab_interleaving(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setup_values()
        self.setup_ui()

    def setup_values(self):
        self.previous_enable_interruptor = get_config_value("mix_reviews_and_reading")
        self.previous_every_n_cards = get_config_value("mix_reviews_and_reading.interrupt_every_nth_card")
        self.previous_session_enabled = not state.rr_mix_disabled

    def update_session_cb(self, boolean):
        self.cb_session.setEnabled(boolean)
        self.sb_every_n_card.setEnabled(boolean)


    def setup_ui(self):
        vbox = QVBoxLayout()

        # explanation
        vbox.addWidget(QLabel("<b>Review Interruption</b>"))
        explanation = "Review interruption will interleave your Anki reviews " +\
                      "with SIAC notes from the reading queue. This enables " + \
                      "an alternate and engaging workflow of both memorization " + \
                      "and learning.<br>"
        label_explanation = QLabel("<i>" + explanation + "</i>")
        label_explanation.setWordWrap(True)
        vbox.addWidget(label_explanation)

        self.cb_enable_interruptor = QCheckBox("Enable review interruption")
        self.cb_enable_interruptor.setChecked(self.previous_enable_interruptor)
        self.cb_enable_interruptor.stateChanged.connect(self.update_session_cb)
        vbox.addWidget(self.cb_enable_interruptor)

        # combobox for enabling in current session
        self.cb_session = QComboBox()
        self.cb_session.setEnabled(self.previous_enable_interruptor)
        self.cb_session.addItems([
            "Enabled in this session",
            "Disabled in this session"
        ])
        if self.previous_session_enabled:
            self.cb_session.setCurrentIndex(0)
        else:
            self.cb_session.setCurrentIndex(1)
        vbox.addWidget(self.cb_session)

        hbox = QHBoxLayout()
        text = QLabel("Interrupt every ")
        self.sb_every_n_card = QDoubleSpinBox()
        self.sb_every_n_card.setEnabled(self.previous_enable_interruptor)
        self.sb_every_n_card.setValue(self.previous_every_n_cards)
        self.sb_every_n_card.setMinimum(1)
        self.sb_every_n_card.setMaximum(9999)
        self.sb_every_n_card.setDecimals(0)
        self.sb_every_n_card.setSuffix(" card(s)")
        hbox.addWidget(text)
        hbox.addWidget(self.sb_every_n_card)
        hbox.setAlignment(Qt.AlignLeft)
        vbox.addLayout(hbox)

        vbox.setAlignment(Qt.AlignTop)
        self.setLayout(vbox)

    def save_changes(self):
        return_string = ""

        # get current settings from checkboxes etc
        enable_interruptor = self.cb_enable_interruptor.isChecked()
        if self.cb_session.currentIndex()== 0:
            session_enabled = True
        else:
            session_enabled = False
        interrupt_n_cards = self.sb_every_n_card.value()

        # check for changes
        if enable_interruptor != self.previous_enable_interruptor:
            update_config("mix_reviews_and_reading", enable_interruptor)
            if enable_interruptor:
                return_string += "Enabled review interruption. "
            else:
                return_string += "Disabled review interruption. "

        if session_enabled != self.previous_session_enabled:
            state.rr_mix_disabled = not session_enabled
            if session_enabled:
                return_string += "Enabled interruption for this session. "
            else:
                return_string += "Disabled interruption for this session. "

        if interrupt_n_cards != self.previous_every_n_cards:
            interrupt_n_cards = int(interrupt_n_cards)
            update_config("mix_reviews_and_reading.interrupt_every_nth_card", interrupt_n_cards)
            return_string += f"""Interrupt every {interrupt_n_cards} cards. """

        if return_string != "":
            return_string += "<br>"

        return return_string
