from typing import Optional, List

from aqt.qt import *
from aqt.main import AnkiQt
from aqt.utils import showWarning

from ..components import ClickableQLabel

#
# WIP:
# todo:
# needs file filters (.pdf, .md, ...)
# needs (checkable?) listing of found files
# needs import settings (tags, priorities, review settings, how to fill out source field)
# needs way of excluding individual files
# window manager?
# https://github.com/fonol/anki-search-inside-add-card/issues/191
#


class NoteImporterDialog(QDialog):
    def __init__(self, mw: AnkiQt):
        # noinspection PyTypeChecker
        QDialog.__init__(self, parent=mw)
        self.mw             = mw
        self.ui             = Ui_OrganiserDialog()
        self.ui.setupUi(self)

        self.ui.syncButton.clicked.connect(self.add_notes)
        self.ui.selectFilesPushButton.clicked.connect(self.choose_file_and_add_to_ignore_list)
        self.ui.selectDirsPushButton.clicked.connect(self.choose_dir_and_add_to_ignore_list)

    # Slots
    ##########################################################################

    def choose_file_and_add_to_ignore_list(self):
        self.choose_and_add_to_ignore_list(mode=QFileDialog.AnyFile)

    def choose_dir_and_add_to_ignore_list(self):
        self.choose_and_add_to_ignore_list(mode=QFileDialog.Directory)

    def choose_and_add_to_ignore_list(self, mode):
        # todo: add ignored directories to settings and then load for future multiple use
        path = self.ui.dirPathLineEdit.text()

        if not os.path.exists(path):
            showWarning(f"{path} is not a valid directory path.\nPlease try again")
            return

        self.file_dialog = QFileDialog(parent=self, directory=path)
        self.file_dialog.setFileMode(mode)
        if self.file_dialog.exec_():
            fileNames = QFileDialog.selectedFiles(self.file_dialog)
            if fileNames:
                for file in fileNames:
                    if file not in [str(self.ui.dirIgnoreLw.item(i).text()) for i in range(self.ui.dirIgnoreLw.count())]:
                        self.add_item_to_list_view(file, self.ui.dirIgnoreLw)

    def add_notes(self):
        path = self.ui.dirPathLineEdit.text()
        if os.path.exists(path):
            ignore_list        = self.create_ignore_list_from_selection(path)
            generator_of_files = return_filepath_generator(path, ignore_list, self.ui.ignoreDirsRecursivelyCheckbox.isChecked())
            self.ui.filesFoundLw.clear()
            for file in generator_of_files:  # here you can do what you want with the files
                self.add_item_to_list_view(file, self.ui.filesFoundLw)
        else:
            showWarning(f"{path} is not a valid directory path.\nPlease try again")

    # Gui functions
    ##########################################################################

    # todo: make this clickable so that you can remove an item on click
    def add_item_to_list_view(self, text: str, list_widget: QListWidget):
        self.ui.lwi = QListWidgetItem()
        self.ui.lwi.setText(text)
        list_widget.addItem(self.ui.lwi)

    # Utility functions
    ##########################################################################

    def create_ignore_list_from_selection(self, path) -> list:
        """Creates a list containing the directories to ignore in the scan"""

        ignore_list = [str(self.ui.dirIgnoreLw.item(i).text()) for i in range(self.ui.dirIgnoreLw.count())]

        # if ignore all hidden is checked, add all the directories that start with '.' to the ignore list
        if self.ui.ignoreAllHiddenCheckbox.isChecked():
            for p in os.listdir(path):
                if p.startswith("."):
                    ignore_list.append(os.path.join(path, p))

        return ignore_list


def return_filepath_generator(path: str, list_of_dirs_and_files_to_ignore: Optional[list] = None,
                              ign_recursively: bool = True):
    """Returns generator of files in all dirs and subdirs of the dir path given"""
    if list_of_dirs_and_files_to_ignore is None:
        list_of_dirs_and_files_to_ignore = []

    for subdir, dirs, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(subdir, filename)
            # if it is not a recursive ignore, then check if the subdirectory is in the list of dirs to ignore
            # todo: little nested if here, remember to remove
            if filepath not in list_of_dirs_and_files_to_ignore:
                if not ign_recursively and (subdir not in list_of_dirs_and_files_to_ignore):
                    yield filepath

                # checks if the subdirectory path starts with any of the values in list of directories to ignore
                # so all of the subdirectories are included in the check of dirs to ignore
                elif ign_recursively and not any(map(os.path.abspath(subdir).startswith,
                                                     [os.path.abspath(i) for i in list_of_dirs_and_files_to_ignore])):
                    yield filepath


# Form implementation generated from reading ui file 'maindialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


class Ui_OrganiserDialog(object):
    def setupUi(self, OrganiserDialog):
        OrganiserDialog.setObjectName("OrganiserDialog")
        OrganiserDialog.resize(525, 536)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(OrganiserDialog.sizePolicy().hasHeightForWidth())
        OrganiserDialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(OrganiserDialog)
        self.verticalLayout.setObjectName("verticalLayout")

        # Path of directory to scan 
        ##########################################################################
        scan_path_gb = QGroupBox("1. Path of directory to scan")
        scan_path_vb = QVBoxLayout()
        self.scanPathLabel = QLabel(OrganiserDialog)
        self.scanPathLabel.setObjectName("scanPathLabel")
        self.dirPathLineEdit = QLineEdit(OrganiserDialog)
        self.dirPathLineEdit.setObjectName("dirPathLineEdit")
        scan_path_vb.addWidget(self.dirPathLineEdit)
        scan_path_gb.setLayout(scan_path_vb)
        self.verticalLayout.addWidget(scan_path_gb)

        # Files/Folder exclusions
        ##########################################################################
        exclude_gb = QGroupBox("2. [Optional] Exclude Files and/or Folders")
        exclude_vb = QVBoxLayout()
        self.dirIgnoreLabel = QLabel(OrganiserDialog)
        self.dirIgnoreLabel.setObjectName("dirIgnoreLabel")
        exclude_vb.addWidget(self.dirIgnoreLabel)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.ignoreAllHiddenCheckbox = QCheckBox(OrganiserDialog)
        self.ignoreAllHiddenCheckbox.setObjectName("ignoreAllHiddenCheckbox")
        self.gridLayout.addWidget(self.ignoreAllHiddenCheckbox, 0, 0, 1, 1)
        self.ignoreDirsRecursivelyCheckbox = QCheckBox(OrganiserDialog)
        self.ignoreDirsRecursivelyCheckbox.setEnabled(True)
        self.ignoreDirsRecursivelyCheckbox.setCheckable(True)
        self.ignoreDirsRecursivelyCheckbox.setChecked(True)
        self.ignoreDirsRecursivelyCheckbox.setObjectName("ignoreDirsRecursivelyCheckbox")
        self.gridLayout.addWidget(self.ignoreDirsRecursivelyCheckbox, 0, 1, 1, 1)
        exclude_vb.addLayout(self.gridLayout)
        self.selectGridLayout = QGridLayout()
        self.selectFilesPushButton = QPushButton('Select Files', parent=OrganiserDialog)
        self.selectGridLayout.addWidget(self.selectFilesPushButton, 0, 0, 1, 1)
        self.selectDirsPushButton = QPushButton('Select Directories', parent=OrganiserDialog)
        self.selectGridLayout.addWidget(self.selectDirsPushButton, 0, 1, 1, 1)
        exclude_vb.addLayout(self.selectGridLayout)
        self.dirIgnoreLw = QListWidget(OrganiserDialog)
        self.dirIgnoreLw.setObjectName("dirIgnoreLw")
        exclude_vb.addWidget(self.dirIgnoreLw)
        exclude_gb.setLayout(exclude_vb)
        self.verticalLayout.addWidget(exclude_gb)

        self.syncButton = QPushButton(OrganiserDialog)
        self.syncButton.setObjectName("syncButton")
        self.verticalLayout.addWidget(self.syncButton)
        self.filesFoundLabel = QLabel(OrganiserDialog)
        self.filesFoundLabel.setObjectName("dirIgnoreLabel")
        self.verticalLayout.addWidget(self.filesFoundLabel)
        self.filesFoundLw = QListWidget(OrganiserDialog)
        self.filesFoundLw.setObjectName("filesFoundLw")
        self.verticalLayout.addWidget(self.filesFoundLw)

        self.retranslateUi(OrganiserDialog)
        QMetaObject.connectSlotsByName(OrganiserDialog)

    def retranslateUi(self, OrganiserDialog):
        _translate = QCoreApplication.translate
        OrganiserDialog.setWindowTitle(_translate("OrganiserDialog", "External Files Anki Organiser"))
        self.dirIgnoreLabel.setText(_translate("OrganiserDialog", "Select subdirectories/files to ignore"))
        self.ignoreAllHiddenCheckbox.setText(_translate("OrganiserDialog", "Ignore all directories (and subdirectories) starting with \'.\' in the scan"))
        self.ignoreDirsRecursivelyCheckbox.setText(_translate("OrganiserDialog", "Ignore selected directories recursively"))
        self.syncButton.setText(_translate("OrganiserDialog", "Import File Notes"))
        self.filesFoundLabel.setText(_translate("OrganiserDialog", "Files found:"))