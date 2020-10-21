from aqt.qt import *
from aqt import mw

from .setting_tabs.shortcut import setting_tab_shortcut


class SettingsDialog(QDialog):
    def __init__(self, parent):
        if not parent:
            parent = mw.app.activeWindow()

        QDialog.__init__(self, parent)

        self.setWindowTitle("SIAC Add-On Settings")
        self.setup_ui()
        self.exec_()

    def setup_ui(self):
        self.vbox = QVBoxLayout()

        self.tabs           = QTabWidget()

        #define tabs
        self.tab_appearance = setting_tab_shortcut()
        self.tab_shortcut = setting_tab_shortcut()

        self.tabs.addTab(self.tab_appearance, "Appearance")
        self.tabs.addTab(self.tab_shortcut   , "Shortcuts")

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept_clicked)
        self.buttonBox.rejected.connect(self.reject)

        self.vbox.addWidget(QLabel("Some settings may or may not need a restart!"))
        self.vbox.addWidget(self.tabs)
        self.vbox.addWidget(self.buttonBox)

        self.setLayout(self.vbox)

    def accept_clicked(self):
        self.appearance_tab.saveChanges()

        self.accept()
