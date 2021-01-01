from typing import Optional

from aqt.qt import *
from aqt.main import AnkiQt
from aqt.utils import showWarning

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
        self.mw = mw
        self.ui = Ui_OrganiserDialog()
        self.ui.setupUi(self)

        self.threadpool = QThreadPool()
        self.thread_running = False

        self.ui.syncButton.clicked.connect(self.add_notes)

        # self.ui.dirPathLineEdit.textEdited.connect(self.refresh_dirs_to_ignore_list)
        self.ui.dirPathLineEdit.returnPressed.connect(self.refresh_dirs_to_ignore_list)

        self.ui.ignoreAllHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.dontShowHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limitSearchesCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limitSearchesCombobox.currentTextChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limLevelsCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limLevelsCombobox.currentTextChanged.connect(self.refresh_dirs_to_ignore_list)

    # Slots
    ##########################################################################

    # todo
    def add_notes(self):
        pass

    def refresh_dirs_to_ignore_list(self):#
        # todo: maybe kill the thread and start a new one if it is running rather than wait for it to finish
        # maybe associate the state 'is_running' with the worker in some way
        if not self.thread_running:
            self.thread_running = True
            worker = Worker(self._refresh_dirs_to_ignore_list)
            self.threadpool.start(worker)
            worker.signals.finished.connect(self.thread_complete)

    # Functions to thread
    ##########################################################################

    def thread_complete(self):
        self.thread_running = False

    def _refresh_dirs_to_ignore_list(self) -> None:
        path = self.ui.dirPathLineEdit.text()
        self.ui.dirIgnoreLw.clear()
        # if the path input exists, update the list widget with all of the subdirectories
        # otherwise, tell th user that the path does not exist
        if os.path.exists(path):
            # don't show any of the directories that start with '.'
            if self.ui.dontShowHiddenCheckbox.isChecked() or self.ui.ignoreAllHiddenCheckbox.isChecked():
                filter_hidden = True
            else:
                filter_hidden = False

            if self.ui.limitSearchesCheckbox.isChecked():
                lim_search_num = int(self.ui.limitSearchesCombobox.currentText())
            else:
                lim_search_num = 0

            if self.ui.limLevelsCheckbox.isChecked():
                lim_levels_num = int(self.ui.limLevelsCombobox.currentText())
            else:
                lim_levels_num = 0

            subdir_list = return_all_subdirs(path, filter_hidden, lim_search_num, lim_levels_num)
            for d in subdir_list:
                self.add_checkable_item_to_dir_ignore_list_view(d)
        else:
            self.add_item_to_list_view("Path entered above does not exist, please enter a real path", self.ui.dirIgnoreLw)

    def _add_notes(self):
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


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


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


def return_all_subdirs(path, filter_hidden: bool, limit_searches_to: int = 0, levels: int = 0):
    count = 0
    if levels == 1:
        for d in os.listdir(path):
            if limit_searches_to and count > limit_searches_to:
                return
            if os.path.isdir(os.path.join(path, d)) and (not filter_hidden):
                count += 1
                yield d
            elif not d.startswith('.'):
                count += 1
                yield d
    else:
        for subdir, dirs, files in os.walk(path):
            if limit_searches_to and count > limit_searches_to:
                return
            rel_path = os.path.relpath(subdir, start=path)
            # stops it from adding the current directory as '.'
            if rel_path != '.' and (not filter_hidden):
                if not levels:
                    count += 1
                    yield rel_path
                elif len(rel_path.split(os.path.sep)) <= levels:
                    count += 1
                    yield rel_path
            elif not os.path.basename(rel_path).startswith('.') and not rel_path.startswith('.'):
                if not levels:
                    count += 1
                    yield rel_path
                elif len(os.path.split(rel_path)) <= levels:
                    count += 1
                    yield rel_path


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
        self.gridLayout.addWidget(self.ignoreAllHiddenCheckbox, 0, 0, 1, 1)
        self.dontShowHiddenCheckbox = QCheckBox(OrganiserDialog)
        self.dontShowHiddenCheckbox.setObjectName("dontShowHiddenCheckbox")
        self.gridLayout.addWidget(self.dontShowHiddenCheckbox, 0, 1, 1, 1)
        self.ignoreDirsRecursivelyCheckbox = QCheckBox(OrganiserDialog)
        self.ignoreDirsRecursivelyCheckbox.setEnabled(True)
        self.ignoreDirsRecursivelyCheckbox.setCheckable(True)
        self.ignoreDirsRecursivelyCheckbox.setChecked(True)
        self.ignoreDirsRecursivelyCheckbox.setObjectName("ignoreDirsRecursivelyCheckbox")
        self.gridLayout.addWidget(self.ignoreDirsRecursivelyCheckbox, 1, 0, 1, 1)
        self.limitSearchesCheckbox = QCheckBox(OrganiserDialog)
        self.limitSearchesCheckbox.setEnabled(True)
        self.limitSearchesCheckbox.setCheckable(True)
        self.limitSearchesCheckbox.setChecked(True)
        self.limitSearchesCheckbox.setObjectName("limitSearchesCheckbox")
        self.gridLayout.addWidget(self.limitSearchesCheckbox, 2, 0, 1, 1)
        self.limitSearchesCombobox = QComboBox(OrganiserDialog)
        self.limitSearchesCombobox.setObjectName("limitSearchesCombobox")
        self.limitSearchesCombobox.addItem("")
        self.limitSearchesCombobox.addItem("")
        self.limitSearchesCombobox.addItem("")
        self.limitSearchesCombobox.addItem("")
        self.gridLayout.addWidget(self.limitSearchesCombobox, 2, 1, 1, 1)
        self.limLevelsCombobox = QComboBox(OrganiserDialog)
        self.limLevelsCombobox.setObjectName("limLevelsCombobox")
        self.limLevelsCombobox.addItem("")
        self.limLevelsCombobox.addItem("")
        self.limLevelsCombobox.addItem("")
        self.limLevelsCombobox.addItem("")
        self.gridLayout.addWidget(self.limLevelsCombobox, 3, 1, 1, 1)
        self.limLevelsCheckbox = QCheckBox(OrganiserDialog)
        self.limLevelsCheckbox.setEnabled(True)
        self.limLevelsCheckbox.setCheckable(True)
        self.limLevelsCheckbox.setChecked(True)
        self.limLevelsCheckbox.setObjectName("limLevelsCheckbox")
        self.gridLayout.addWidget(self.limLevelsCheckbox, 3, 0, 1, 1)
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
        self.ignoreAllHiddenCheckbox.setText(_translate("OrganiserDialog", "Ignore all directories (and subdirectories) starting with \'.\' in the scan"))
        self.dontShowHiddenCheckbox.setText(_translate("OrganiserDialog", "Don\'t show directories starting with \'.\'"))
        self.ignoreDirsRecursivelyCheckbox.setText(_translate("OrganiserDialog", "Ignore selected directories recursively"))
        self.limitSearchesCheckbox.setText(_translate("OrganiserDialog", "Limit searches to:"))
        self.limitSearchesCombobox.setItemText(0, _translate("OrganiserDialog", "50"))
        self.limitSearchesCombobox.setItemText(1, _translate("OrganiserDialog", "100"))
        self.limitSearchesCombobox.setItemText(2, _translate("OrganiserDialog", "150"))
        self.limitSearchesCombobox.setItemText(3, _translate("OrganiserDialog", "200"))
        self.limLevelsCombobox.setItemText(0, _translate("OrganiserDialog", "1"))
        self.limLevelsCombobox.setItemText(1, _translate("OrganiserDialog", "2"))
        self.limLevelsCombobox.setItemText(2, _translate("OrganiserDialog", "3"))
        self.limLevelsCombobox.setItemText(3, _translate("OrganiserDialog", "4"))
        self.limLevelsCheckbox.setText(_translate("OrganiserDialog", "Limit the number of levels shown to:"))
        self.syncButton.setText(_translate("OrganiserDialog", "Import File Notes"))
        self.filesFoundLabel.setText(_translate("OrganiserDialog", "Files found:"))