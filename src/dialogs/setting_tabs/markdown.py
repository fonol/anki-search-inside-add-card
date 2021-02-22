from aqt.qt import *

from ...config import get_config_value, update_config


class MarkdownSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setup_values()
        self.setup_ui()

    def setup_values(self):
        self.previous_md_folder_path   = get_config_value("md.folder_path")

    def setup_ui(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("""Info: This is an experimental feature that allows to choose a folder and 'mirror' the markdown files in it.<br>
            This can be used to view .md files from an Obsidian vault for instance, and have them in the queue <br>or simply search for them while creating cards.<br>
            The given folder will be scanned for new or changed files on add-on startup (or on 'Rebuild Index'), and for each file,<br>
            an add-on note will be created/updated:
            <ul>
                <li>Its <i>Title</i> field will contain the filename
                <li>Its <i>Text</i> field contains the content of the .md file.</li>
                <li>Its <i>Source</i> field contains the path to the .md file with <i>md:///</i> prepended.</li>
                <li>Its <i>Tags</i> are filled with the path to the file, e.g. if the file is located like &lt;Root folder&gt;/uni/archived/stuff.md,<br>the tag will be
                <i>uni::archived</i></li>
            </ul>
            <br>
            <br>If you update the add-on note's text, the change will be written to the .md file.
        """))

        vbox.addSpacing(20)
        self.md_source_input = QLineEdit()
        if self.previous_md_folder_path is not None and len(self.previous_md_folder_path.strip()) > 0:
            self.md_source_input.setText(self.previous_md_folder_path)

        hbox = QHBoxLayout()

        dir_btn = QPushButton("Choose ...")
        dir_btn.clicked.connect(self.on_dir_btn)

        hbox.addWidget(QLabel("Markdown folder"))
        hbox.addStretch()
        hbox.addWidget(self.md_source_input)
        hbox.addWidget(dir_btn)
        vbox.addLayout(hbox)

        vbox.setAlignment(Qt.AlignTop)
        self.setLayout(vbox)

    def on_dir_btn(self):

        fname = str(QFileDialog.getExistingDirectory(self, "Select your markdown folder"))

        if fname is not None and len(fname) > 0:
            fname = fname.replace("\\", "/")
            self.md_source_input.setText(fname)

    def save_changes(self):

        md_folder_path = self.md_source_input.text()

        if md_folder_path != self.previous_md_folder_path:
            update_config("md.folder_path", md_folder_path)
            return "Changed Markdown folder."

        return ""

