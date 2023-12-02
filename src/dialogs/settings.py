from aqt.qt import *
from aqt import mw
from aqt.utils import tooltip

from .setting_tabs.shortcut import ShortcutSettingsTab
from .setting_tabs.appearance import AppearanceSettingsTab
from .setting_tabs.interleaving import InterleavingSettingsTab
from .setting_tabs.general import GeneralSettingsTab
from .setting_tabs.markdown import MarkdownSettingsTab


class SettingsDialog(QDialog):
    def __init__(self, parent):
        if not parent:
            parent = mw.app.activeWindow()

        QDialog.__init__(self, parent)
        self.parent = parent

        self.setWindowTitle("SIAC Settings")
        self.setup_ui()
        self.exec()

    def setup_ui(self):
        self.vbox             = QVBoxLayout()

        self.tabs             = QTabWidget()

        # Define tabs
        self.tab_appearance   = AppearanceSettingsTab()
        self.tab_shortcut     = ShortcutSettingsTab()
        self.tab_general      = GeneralSettingsTab()
        self.tab_interleaving = InterleavingSettingsTab()
        self.tab_markdown     = MarkdownSettingsTab()

        self.tabs.addTab(self.tab_appearance,   "Appearance")
        self.tabs.addTab(self.tab_shortcut,     "Shortcuts")
        self.tabs.addTab(self.tab_general,      "General")
        self.tabs.addTab(self.tab_interleaving, "Interleaving")
        self.tabs.addTab(self.tab_markdown,     "Markdown")

        # Cancel and Okay Buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Close)
        self.buttonBox.accepted.connect(self.accept_clicked)
        self.buttonBox.rejected.connect(self.reject)

        self.vbox.addWidget(self.tabs)
        self.vbox.addWidget(self.buttonBox)

        self.setLayout(self.vbox)

    def accept_clicked(self):
        tooltip_changes = self.tab_appearance.save_changes() + \
                          self.tab_shortcut.save_changes() + \
                          self.tab_general.save_changes() + \
                          self.tab_interleaving.save_changes() + \
                          self.tab_markdown.save_changes()

        if tooltip_changes:
            tooltip_text = "<b>Settings changed</b><br>" + \
                           tooltip_changes + \
                           "<br><i>Please restart Anki to make sure all settings are applied!</i>"
        else:
            tooltip_text = "<b>No settings changed!</b>"

        tooltip(tooltip_text, parent = self.parent)

        self.accept()
