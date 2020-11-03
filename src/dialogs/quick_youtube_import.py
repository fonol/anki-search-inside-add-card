from aqt.qt import *
import aqt.editor
import aqt
from aqt.utils import showInfo
import utility.text

import requests
import json

class QuickYoutubeImport(QDialog):
    """Quickly prepare notes from YouTube videos"""
    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowSystemMenuHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.parent = parent

        self.setup_ui()
        self.setWindowTitle("Quick Youtube Import")

    def setup_ui(self):
        vbox = QVBoxLayout()

        # Cancel and Okay Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept_clicked)
        self.button_box.rejected.connect(self.reject)

        self.url_line = QLineEdit()
        self.url_line.textChanged.connect(self.on_input)
        self.url_line.setFocus()

        self.label_image = QLabel()
        self.label_title = QLabel()
        self.label_author = QLabel()

        vbox.addWidget(self.label_title)
        vbox.addWidget(self.url_line)
        vbox.addWidget(self.label_author)
        vbox.addWidget(self.label_image)
        vbox.addWidget(self.button_box)

        self.on_input(self.url_line.text())

        self.setLayout(vbox)

    def accept_clicked(self):
        self.accept()

    def on_input(self,text):
        # reset everything
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        self.label_title.setText("<b>Title</b>")
        self.label_author.setText("Youtube Channel")

        self.youtube_title = ""
        self.youtube_channel = ""
        self.youtube_url = ""

        image = QPixmap(320, 180)
        image.fill(QColorConstants.Black)
        self.label_image.setPixmap(image)

        # youtube ids are currently 11 characters long
        yt_id = utility.text.get_yt_video_id(text)

        if len(yt_id) == 11:
            oembed_url = f"""http://www.youtube.com/oembed?url=https://youtube.com/watch?v={yt_id}&format=json"""

            yt_videodata = requests.get(oembed_url)

            if yt_videodata.text is None or yt_videodata.text == "Not Found":
                return

            data = json.loads(yt_videodata.text)

            if "title" not in data:
                return

            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

            thumbnail_url = data["thumbnail_url"]
            self.youtube_title = data["title"]
            self.youtube_channel = data["author_name"]
            time = utility.text.get_yt_time(text)

            self.youtube_url = f"""https://www.youtube.com/watch?v={yt_id}&t={time}s"""

            self.label_title.setText(self.youtube_title)
            self.label_author.setText(self.youtube_channel)

            image.loadFromData(requests.get(f"""http://img.youtube.com/vi/{yt_id}/mqdefault.jpg""").content)
            self.label_image.setPixmap(image)
