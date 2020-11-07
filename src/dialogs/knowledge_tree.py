from aqt import mw
#from aqt.qt import QDialog, QLabel, QVBoxLayout
from aqt.qt import *

class KnowledgeTree(QDialog):
    def __init__(self):
        QDialog.__init__(self, parent = mw)
        self.setWindowTitle("Knowledge Tree")
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Knowledge Tree"))
        self.setLayout(vbox)
        self.setMinimumHeight(300)
        #self.show()
