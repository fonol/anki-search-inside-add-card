from aqt.qt import *
import aqt
import requests
import json
import typing

import utility.text


class QuickYoutubeImport(QDialog):
    """Quickly prepare notes from YouTube videos"""
    def __init__(self, parent):
        QDialog.__init__(self, parent, Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)

        self.parent             = parent
        self.last_yt_id         = None
        self.youtube_title      = ""
        self.youtube_channel    = ""
        self.youtube_url        = ""

        self.setup_ui()
        self.setWindowTitle("Quick Youtube Import")

    def setup_ui(self):

        vbox = QVBoxLayout()

        # Cancel and Okay Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_clicked)
        self.button_box.rejected.connect(self.reject)

        self.url_line = QLineEdit()
        self.url_line.textChanged.connect(self.on_input)
        self.url_line.setFocus()

        self.label_image    = QLabel()
        self.label_title    = QLabel()
        self.label_author   = QLabel()

        vbox.addWidget(self.label_title)
        vbox.addWidget(self.url_line)
        vbox.addWidget(self.label_author)
        vbox.addWidget(self.label_image)
        vbox.addWidget(self.button_box)

        self.on_input(self.url_line.text())

        self.setLayout(vbox)

        # get clipboard content
        clipboard_text = QApplication.clipboard().text()

        if utility.text.is_yt_video_url(clipboard_text):

            yt_id = utility.text.get_yt_video_id(clipboard_text)

            if yt_id is not None and len(yt_id) > 0:
                self.url_line.setText(clipboard_text)

    def accept_clicked(self):
        self.accept()

    def on_input(self, lineedit_text: str):
        # reset everything
        image = QPixmap(320, 180)

        def _reset_yt_properties():
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.last_yt_id = None
            self.label_title.setText("<b>Paste a Youtube video url</b>")
            self.label_author.setText("Youtube Channel")

            self.youtube_title = ""
            self.youtube_channel = ""
            self.youtube_url = ""

            image.fill(QColorConstants.Black)
            self.label_image.setPixmap(image)


        # get youtube_id from string
        yt_id = utility.text.get_yt_video_id(lineedit_text)

        # only adjust time if already loaded
        if yt_id == self.last_yt_id:
            pass
        # current yt_id's are 11 long
        elif len(yt_id) == 11:
            oembed_url = f"""https://www.youtube.com/oembed?url=https://youtube.com/watch?v={yt_id}&format=json"""
            yt_videodata = requests.get(oembed_url)

            # failure, cant get reasonable json
            if yt_videodata.text is None or yt_videodata.text == "Not Found":
                _reset_yt_properties()
                return

            data = json.loads(yt_videodata.text)

            if "title" not in data:
                _reset_yt_properties()
                return

            thumbnail_url           = data["thumbnail_url"]
            self.youtube_title      = data["title"]
            self.youtube_channel    = data["author_name"]
            self.last_yt_id         = yt_id

            self.label_title.setText("<b>" + self.youtube_title + "</b>")
            self.label_author.setText(self.youtube_channel)

            # TODO: will throw error if youtube video could be loaded, but not the image
            try:
                image.loadFromData(requests.get(f"""https://img.youtube.com/vi/{yt_id}/mqdefault.jpg""").content)
                self.label_image.setPixmap(image)
            except:
                pass

        # everything else is not youtube
        else:
            _reset_yt_properties()
            return

        self.set_youtube_url(lineedit_text, yt_id)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def set_youtube_url(self, urlstring: str, yt_id: str):
        time = utility.text.get_yt_time(urlstring)

        if time is not None:
            self.youtube_url = f"""https://www.youtube.com/watch?v={yt_id}&t={time}s"""
        else:
            self.youtube_url = f"""https://www.youtube.com/watch?v={yt_id}"""
