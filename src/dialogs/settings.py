from aqt.qt import *
from aqt import mw
from aqt.utils import tooltip

from .setting_tabs.shortcut import setting_tab_shortcut
from .setting_tabs.appearance import setting_tab_appearance


class SettingsDialog(QDialog):
    def __init__(self, parent):
        if not parent:
            parent = mw.app.activeWindow()

        QDialog.__init__(self, parent)

        self.setWindowTitle("SIAC Settings")
        self.setup_ui()
        self.exec_()

    def setup_ui(self):
        self.vbox = QVBoxLayout()

        self.tabs           = QTabWidget()

        # Define tabs
        self.tab_appearance = setting_tab_appearance()
        self.tab_shortcut = setting_tab_shortcut()

        self.tabs.addTab(self.tab_appearance, "Appearance")
        self.tabs.addTab(self.tab_shortcut   , "Shortcuts")

        # Cancel and Okay Buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept_clicked)
        self.buttonBox.rejected.connect(self.reject)

        self.vbox.addWidget(self.tabs)
        self.vbox.addWidget(QLabel("<i>Some settings may or may not need a restart! Work in progress!</i>"))
        self.vbox.addWidget(self.buttonBox)

        self.setLayout(self.vbox)

    def accept_clicked(self):
        tooltip_text = "<b>Settings changed</b><br>" + \
                       self.tab_appearance.save_changes() + \
                       self.tab_shortcut.save_changes() + \
                       "<br><i>Please restart Anki to make sure all settings are applied!</i>"

        tooltip(tooltip_text, parent = mw)

        self.accept()
