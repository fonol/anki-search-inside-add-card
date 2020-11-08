from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *
from aqt.utils import showInfo

class KnowledgeTree(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Knowledge Tree")
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Knowledge Tree"))
        vbox.addWidget(QLabel("Knowledge Tree"))
        vbox.addWidget(QLabel("Knowledge Tree"))
        vbox.addWidget(QLabel("Knowledge Tree"))
        vbox.addWidget(QLabel("Knowledge Tree"))
        self.setLayout(vbox)
        self.setMinimumHeight(300)
