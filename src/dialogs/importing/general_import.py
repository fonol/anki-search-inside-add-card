from typing import Optional, List, Generator

from aqt.qt import *
from aqt.main import AnkiQt
from aqt.utils import showWarning

#
# WIP:
# todo:
# needs file filters (.pdf, .md, ...)
# needs (checkable?) listing of found files
# needs import settings (tags, priorities, how to fill out source field)
# needs way of excluding individual files
# https://github.com/fonol/anki-search-inside-add-card/issues/191
#


class NoteImporterDialog(QDialog):
    def __init__(self, mw: AnkiQt):
        # noinspection PyTypeChecker
        QDialog.__init__(self, parent=mw)
        self.mw = mw
        self.ui = Ui_OrganiserDialog()
        self.ui.setupUi(self)

        self.ui.syncButton.clicked.connect(self.add_notes)

        # self.ui.dirPathLineEdit.textEdited.connect(self.refresh_dirs_to_ignore_list)
        self.ui.dirPathLineEdit.returnPressed.connect(self.refresh_dirs_to_ignore_list)

        self.ui.showTopSubdirsCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.ignoreAllHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.dontShowHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)

    # Slots
    ##########################################################################

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

    def refresh_dirs_to_ignore_list(self) -> None:
        path = self.ui.dirPathLineEdit.text()
        self.ui.dirIgnoreLw.clear()
        # if the path input exists, update the list widget with all of the subdirectories
        # otherwise, tell th user that the path does not exist
        if os.path.exists(path):
            if self.ui.showTopSubdirsCheckbox.isChecked():
                subdir_list = [d for d in return_top_level_subdirs(path) if d]
            else:
                subdir_list = [d for d in return_all_subdirs(path) if d]
            # don't show any of the directories that start with '.'
            if self.ui.dontShowHiddenCheckbox.isChecked() or self.ui.ignoreAllHiddenCheckbox.isChecked():
                subdir_list = [d for d in subdir_list if not d.startswith(r".")]

            for d in subdir_list:
                self.add_checkable_item_to_dir_ignore_list_view(d)
        else:
            self.add_item_to_list_view("Path entered above does not exist, please enter a real path", self.ui.dirIgnoreLw)

    # Gui functions
    ##########################################################################

    def add_checkable_item_to_dir_ignore_list_view(self, text: str) -> None:
        self.ui.lwi = QListWidgetItem()
        self.ui.lwi.setText(text)
        self.ui.lwi.setFlags(self.ui.lwi.flags() | Qt.ItemIsUserCheckable)
        self.ui.lwi.setCheckState(Qt.Unchecked)
        self.ui.dirIgnoreLw.addItem(self.ui.lwi)

    def add_item_to_list_view(self, text: str, list_widget: QListWidget):
        self.ui.lwi = QListWidgetItem()
        self.ui.lwi.setText(text)
        list_widget.addItem(self.ui.lwi)

    # Utility functions
    ##########################################################################

    def create_ignore_list_from_selection(self, path) -> list:
        """Creates a list containing the directories to ignore in the scan"""

        # returns a generator of all the directories to ignore from those selected in the list view
        def return_gen_of_dirs_to_ignore():
            for i in range(self.ui.dirIgnoreLw.count()):
                list_item = self.ui.dirIgnoreLw.item(i)
                if list_item.checkState() == Qt.Checked:
                    yield list_item.text()

        gen = return_gen_of_dirs_to_ignore()
        ignore_list = [os.path.join(path, p) for p in gen]

        # if ignore all hidden is checked, add all the directories that start with '.' to the ignore list
        if self.ui.ignoreAllHiddenCheckbox.isChecked():
            for p in os.listdir(path):
                if p.startswith("."):
                    ignore_list.append(os.path.join(path, p))

        return ignore_list


def return_filepath_generator(path: str, list_of_dirs_to_ignore: Optional[list] = None, ign_recursively: bool = True):
    """Returns generator of files in all dirs and subdirs of the dir path given"""
    if list_of_dirs_to_ignore is None:
        list_of_dirs_to_ignore = []

    for subdir, dirs, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(subdir, filename)
            # if it is not a recursive ignore, then check if the subdirectory is in the list of dirs to ignore
            if not ign_recursively and (subdir not in list_of_dirs_to_ignore):
                yield filepath

            # checks if the subdirectory path starts with any of the values in list of directories to ignore
            # so all of the subdirectories are included in the check of dirs to ignore
            elif ign_recursively and not any(map(subdir.startswith, list_of_dirs_to_ignore)):
                yield filepath


def return_all_subdirs(path):
    for subdir, dirs, files in os.walk(path):
        rel_path = os.path.relpath(subdir, start=path)
        if rel_path != '.':  # stops it from adding the current directory as '.'
            yield rel_path


def return_top_level_subdirs(path):
    for d in os.listdir(path):
        if os.path.isdir(os.path.join(path, d)):
            yield d



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
        self.dirScanHL = QFormLayout()
        self.dirScanHL.setObjectName("dirScanHL")
        self.scanPathLabel = QLabel(OrganiserDialog)
        self.scanPathLabel.setObjectName("scanPathLabel")
        self.dirScanHL.setWidget(0, QFormLayout.LabelRole, self.scanPathLabel)
        self.dirPathLineEdit = QLineEdit(OrganiserDialog)
        self.dirPathLineEdit.setObjectName("dirPathLineEdit")
        self.dirScanHL.setWidget(0, QFormLayout.FieldRole, self.dirPathLineEdit)
        self.verticalLayout.addLayout(self.dirScanHL)
        self.dirIgnoreLabel = QLabel(OrganiserDialog)
        self.dirIgnoreLabel.setObjectName("dirIgnoreLabel")
        self.verticalLayout.addWidget(self.dirIgnoreLabel)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.ignoreAllHiddenCheckbox = QCheckBox(OrganiserDialog)
        self.ignoreAllHiddenCheckbox.setObjectName("ignoreAllHiddenCheckbox")
        self.gridLayout.addWidget(self.ignoreAllHiddenCheckbox, 1, 0, 1, 1)
        self.dontShowHiddenCheckbox = QCheckBox(OrganiserDialog)
        self.dontShowHiddenCheckbox.setObjectName("dontShowHiddenCheckbox")
        self.gridLayout.addWidget(self.dontShowHiddenCheckbox, 0, 1, 1, 1)
        self.showTopSubdirsCheckbox = QCheckBox(OrganiserDialog)
        self.showTopSubdirsCheckbox.setObjectName("showTopSubdirsCheckbox")
        self.gridLayout.addWidget(self.showTopSubdirsCheckbox, 0, 0, 1, 1)
        self.ignoreDirsRecursivelyCheckbox = QCheckBox(OrganiserDialog)
        self.ignoreDirsRecursivelyCheckbox.setEnabled(True)
        self.ignoreDirsRecursivelyCheckbox.setCheckable(True)
        self.ignoreDirsRecursivelyCheckbox.setChecked(True)
        self.ignoreDirsRecursivelyCheckbox.setObjectName("ignoreDirsRecursivelyCheckbox")
        self.gridLayout.addWidget(self.ignoreDirsRecursivelyCheckbox, 1, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.dirIgnoreLw = QListWidget(OrganiserDialog)
        self.dirIgnoreLw.setObjectName("dirIgnoreLw")
        self.verticalLayout.addWidget(self.dirIgnoreLw)
        self.syncButtonHL = QHBoxLayout()
        self.syncButtonHL.setObjectName("syncButtonHL")
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.syncButtonHL.addItem(spacerItem)
        self.syncButton = QPushButton(OrganiserDialog)
        self.syncButton.setObjectName("syncButton")
        self.syncButtonHL.addWidget(self.syncButton)
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.syncButtonHL.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.syncButtonHL)
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
        OrganiserDialog.setWindowTitle(_translate("OrganiserDialog", "External Files Anki Orgnaniser"))
        self.scanPathLabel.setText(_translate("OrganiserDialog", "Path of directory to scan"))
        self.dirIgnoreLabel.setText(_translate("OrganiserDialog", "Select subdirectories/files to ignore"))
        self.ignoreAllHiddenCheckbox.setText(_translate("OrganiserDialog", "Ignore all directories starting with \'.\' in the scan"))
        self.dontShowHiddenCheckbox.setText(_translate("OrganiserDialog", "Don\'t show directories starting with \'.\'"))
        self.showTopSubdirsCheckbox.setText(_translate("OrganiserDialog", "Show only top level directories"))
        self.ignoreDirsRecursivelyCheckbox.setText(_translate("OrganiserDialog", "Ignore selected directories recursively"))
        self.syncButton.setText(_translate("OrganiserDialog", "Import File Notes"))
        self.filesFoundLabel.setText(_translate("OrganiserDialog", "Files found:"))