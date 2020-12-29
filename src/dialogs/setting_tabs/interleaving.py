from aqt.qt import *
from aqt import mw

import state
from aqt.utils import showInfo
from ...config import get_config_value, update_config


class InterleavingSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setup_values()
        self.setup_ui()

    def setup_values(self):
        self.previous_enable_interruptor = get_config_value("mix_reviews_and_reading")
        self.previous_every_n_cards = get_config_value("mix_reviews_and_reading.interrupt_every_nth_card")
        self.previous_show_interrupt_dialog = get_config_value("mix_reviews_and_reading.show_dialog")
        self.previous_session_enabled = not state.rr_mix_disabled
        self.previous_mixingmode = get_config_value("mix_reviews_and_reading.mode")
        self.previous_fuzz = get_config_value("mix_reviews_and_reading.fuzz")

        self.previous_review_after_done = get_config_value("mix_reviews_and_reading.review_after_done")

        self.previous_cards_are_due_overlay = get_config_value("notes.show_linked_cards_are_due_overlay")

    def enable_interruption_settings(self, boolean):
        self.cb_session.setEnabled(boolean)
        self.sb_every_n_card.setEnabled(boolean)
        self.sb_fuzz.setEnabled(boolean)
        self.rb_every_n.setEnabled(boolean)
        self.rb_random_due.setEnabled(boolean)


    def setup_ui(self):
        vbox = QVBoxLayout()

        # Review Interruption
        vbox.addWidget(QLabel("<b>Review Interruption</b>"))
        explanation = "Review interruption will interleave your Anki reviews " +\
                      "with SIAC notes from the reading queue. This enables " + \
                      "an alternate and engaging workflow of both memorization " + \
                      "and learning.<br>"
        label_explanation = QLabel("<i>" + explanation + "</i>")
        label_explanation.setWordWrap(True)
        vbox.addWidget(label_explanation)

        self.cb_review_after_done = QCheckBox("Return to reviewing after Done!")
        self.cb_review_after_done.setChecked(self.previous_review_after_done)
        vbox.addWidget(self.cb_review_after_done)

        self.cb_enable_interruptor = QCheckBox("Enable review interruption")
        self.cb_enable_interruptor.setChecked(self.previous_enable_interruptor)
        self.cb_enable_interruptor.stateChanged.connect(self.enable_interruption_settings)
        vbox.addWidget(self.cb_enable_interruptor)

        # combobox for enabling in current session
        self.cb_session = QComboBox()
        self.cb_session.addItems([
            "Enabled in this session",
            "Disabled in this session"
        ])
        if self.previous_session_enabled:
            self.cb_session.setCurrentIndex(0)
        else:
            self.cb_session.setCurrentIndex(1)
        vbox.addWidget(self.cb_session)

        # Interrupt mixing mode
        vbox.addWidget(QLabel("<br><u>Interruption Modes</u>"))
        group_modes  = QButtonGroup()

        # every_n
        hbox_every_n = QHBoxLayout()
        self.rb_every_n = QRadioButton("Interrupt every ")
        self.sb_every_n_card = QDoubleSpinBox()
        self.sb_every_n_card.setValue(self.previous_every_n_cards)
        self.sb_every_n_card.setMinimum(1)
        self.sb_every_n_card.setMaximum(9999)
        self.sb_every_n_card.setDecimals(0)
        self.sb_every_n_card.setSuffix(" card(s)")
        hbox_every_n.addWidget(self.rb_every_n)
        hbox_every_n.addWidget(self.sb_every_n_card)
        hbox_every_n.setAlignment(Qt.AlignLeft)
        vbox.addLayout(hbox_every_n)

        # due_random
        hbox_random_due = QHBoxLayout()
        self.rb_random_due = QRadioButton("Try to interrupt all due add-on notes - Fuzz-factor: ")
        self.sb_fuzz = QDoubleSpinBox()
        self.sb_fuzz.setValue(int(self.previous_fuzz*100))
        self.sb_fuzz.setMinimum(0)
        self.sb_fuzz.setMaximum(100)
        self.sb_fuzz.setDecimals(0)
        self.sb_fuzz.setSuffix("%")
        hbox_random_due.addWidget(self.rb_random_due)
        hbox_random_due.addWidget(self.sb_fuzz)
        hbox_random_due.setAlignment(Qt.AlignLeft)
        vbox.addLayout(hbox_random_due)

        # group radiobuttons, preset
        group_modes.addButton(self.rb_every_n)
        group_modes.addButton(self.rb_random_due)
        self.rb_every_n.setChecked((self.previous_mixingmode == "every_n"))
        self.rb_random_due.setChecked((self.previous_mixingmode == "due_random"))

        vbox.addWidget(QLabel("<br><u>Interrupt Dialog</u>"))
        self.cb_show_interrupt_dialog = QCheckBox("Show interrupt dialog when interrupting")
        self.cb_show_interrupt_dialog.setChecked(self.previous_show_interrupt_dialog)
        vbox.addWidget(self.cb_show_interrupt_dialog)

        # enable/disable all settings according to interruptor settings
        self.enable_interruption_settings(self.previous_enable_interruptor)


        # Interleaving cards from SIAC note
        vbox.addWidget(QLabel("<br><b>Interleaving cards before reading</b>"))
        self.cb_cards_are_due_overlay = QCheckBox("Show overlay if cards which are linked to a note are due before reading/watching/writing the note")
        self.cb_cards_are_due_overlay.setChecked(self.previous_cards_are_due_overlay)
        vbox.addWidget(self.cb_cards_are_due_overlay)

        vbox.setAlignment(Qt.AlignTop)
        self.setLayout(vbox)

    def save_changes(self):
        return_string = ""

        # get current settings from checkboxes etc
        review_after_done = self.cb_review_after_done.isChecked()

        enable_interruptor = self.cb_enable_interruptor.isChecked()
        interrupt_dialog = self.cb_show_interrupt_dialog.isChecked()
        if self.cb_session.currentIndex()== 0:
            session_enabled = True
        else:
            session_enabled = False
        interrupt_n_cards = self.sb_every_n_card.value()
        cards_are_due_overlay = self.cb_cards_are_due_overlay.isChecked()
        fuzz = self.sb_fuzz.value()/100.0

        if self.rb_every_n.isChecked() == True:
            mixingmode = "every_n"
        else:
            mixingmode = "due_random"

        # check for changes
        if review_after_done != self.previous_review_after_done:
            update_config("mix_reviews_and_reading.review_after_done", review_after_done)
            if review_after_done:
                return_string += "Review after done: enabled. "
            else:
                return_string += "Review after done: disabled. "

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

        if interrupt_dialog != self.previous_show_interrupt_dialog:
            update_config("mix_reviews_and_reading.show_dialog", interrupt_dialog)
            if interrupt_dialog:
                return_string += "Show interrupt dialog. "
            else:
                return_string += "Do not show interrupt dialog. "

        if mixingmode != self.previous_mixingmode:
            update_config("mix_reviews_and_reading.mode", mixingmode)
            if mixingmode == "every_n":
                return_string += "Mode: Interrupt every n. "
            if mixingmode == "due_random":
                return_string += "Mode: Randomly all due notes. "

        if fuzz != self.previous_fuzz:
            update_config("mix_reviews_and_reading.fuzz", fuzz)
            fuzz100 = int(fuzz * 100)
            return_string += f"Mixing fuzz set to {fuzz100}. "


        if cards_are_due_overlay != self.previous_cards_are_due_overlay:
            update_config("notes.show_linked_cards_are_due_overlay", cards_are_due_overlay)
            if cards_are_due_overlay:
                return_string += "Show overlay if cards are due enabled. "
            else:
                return_string += "Show overlay if cards are due disabled. "

        if return_string != "":
            return_string += "<br>"


        return return_string
