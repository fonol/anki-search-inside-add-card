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

        self.thread_pool = QThreadPool()
        self.thread_running = False
        self.thread         = None

        self.ui.syncButton.clicked.connect(self.add_notes)

        self.ui.dirPathLineEdit.returnPressed.connect(self.refresh_dirs_to_ignore_list)
        self.ui.ignoreAllHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.dontShowHiddenCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limitSearchesCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limitSearchesCombobox.currentTextChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limLevelsCheckbox.stateChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.limLevelsCombobox.currentTextChanged.connect(self.refresh_dirs_to_ignore_list)
        self.ui.scan_status_abort.clicked.connect(self.abort_scan)

    # Slots
    ##########################################################################

    # todo
    def add_notes(self):
        pass

    def refresh_dirs_to_ignore_list(self):

        path = self.ui.dirPathLineEdit.text()

        if path is None or len(path.strip()) == 0:
            return

        self.ui.dirIgnoreLw.clear()

        if not os.path.exists(path):
            self.add_item_to_list_view("Path entered above does not exist, please enter a real path", self.ui.dirIgnoreLw)
            return

        if self.thread_running:
            if self.worker:
                self.worker.finished.connect(self.refresh_dirs_to_ignore_list)
                self.worker.stop()
            return

        if self.thread and self.thread.isRunning():
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
        
        self.thread_running = True

        # if the path input exists, update the list widget with all of the subdirectories
        # otherwise, tell th user that the path does not exist
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

        self.worker = ScanWorker(path, filter_hidden, lim_search_num, lim_levels_num)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.start.emit()
        self.worker.found_subdir.connect(self.bulk_add_to_dir_ignore)
        self.worker.finished.connect(self.thread_complete)
        self.worker.aborted.connect(self.worker_aborted)
        self.thread.start()
        self.ui.scan_status_lbl.setText("Scanning...")
        self.ui.scan_status_abort.setDisabled(False)

    def abort_scan(self):
        if self.worker:
            self.ui.scan_status_abort.setDisabled(True)
            self.worker.stop()



    # Functions to thread
    ##########################################################################

    def thread_complete(self):
        self.ui.scan_status_lbl.setText("Finished Scan.")
        self.ui.scan_status_abort.setDisabled(True)
        self.thread_running = False

    def worker_aborted(self):
        self.ui.scan_status_lbl.setText("Aborted Scan.")
        self.ui.scan_status_abort.setDisabled(True)
        self.thread_running = False


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

    def bulk_add_to_dir_ignore(self, items: List[str]) -> None:
        for i in items:
            lwi = QListWidgetItem()
            lwi.setText(i)
            lwi.setFlags(lwi.flags() | Qt.ItemIsUserCheckable)
            lwi.setCheckState(Qt.Unchecked)
            self.ui.dirIgnoreLw.addItem(lwi)

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



class ScanWorker(QObject):
    """ Perform subdir/file scan in a chosen folder. """

    found_subdir = pyqtSignal(list)
    finished     = pyqtSignal()
    start        = pyqtSignal()
    aborted      = pyqtSignal()

    def __init__(self, path, filter_hidden, lim_search_num, lim_levels_num):
        super(ScanWorker, self).__init__()

        self.path           = path
        self.filter_hidden  = filter_hidden
        self.lim_search_num = lim_search_num
        self.lim_levels_num = lim_levels_num

        self.abort          = False
        
        self.start.connect(self.run)

    @pyqtSlot()
    def run(self):
        self.abort  = False
        subdir_list = self.return_all_subdirs()
        batch       = []
        batch_size  = 50
        for d in subdir_list:
            batch.append(d)
            if len(batch) >= batch_size:
                self.found_subdir.emit(batch)
                batch = []
                
        if len(batch) > 0:
            self.found_subdir.emit(batch)

        if self.abort:
            self.aborted.emit()
        else:
            self.finished.emit()

    def return_all_subdirs(self):

        levels              = self.lim_levels_num
        limit_searches_to   = self.lim_search_num
        filter_hidden       = self.filter_hidden
        path                = self.path
        count               = 0
        
        if levels == 1:
            for d in os.listdir(path):
                if self.abort or limit_searches_to and count > limit_searches_to:
                    return
                if os.path.isdir(os.path.join(path, d)) and (not filter_hidden):
                    count += 1
                    yield d
                elif not d.startswith('.'):
                    count += 1
                    yield d
        else:
            for subdir, dirs, files in os.walk(path):
                if self.abort or (limit_searches_to and count > limit_searches_to):
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

    def stop(self):
        self.abort = True

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
        exclude_vb.addLayout(self.gridLayout)
        self.dirIgnoreLw = QListWidget(OrganiserDialog)
        self.dirIgnoreLw.setObjectName("dirIgnoreLw")
        exclude_vb.addWidget(self.dirIgnoreLw)
        exclude_gb.setLayout(exclude_vb)
        self.verticalLayout.addWidget(exclude_gb)
        self.scan_status_hb = QHBoxLayout()
        self.scan_status_abort = QPushButton("Abort Scan")
        self.scan_status_abort.setDisabled(True)
        self.scan_status_abort.setFocusPolicy(Qt.NoFocus)
        self.scan_status_hb.addWidget(self.scan_status_abort)
        self.scan_status_lbl = QLabel("")
        self.scan_status_hb.addStretch()
        self.scan_status_hb.addWidget(self.scan_status_lbl)
        exclude_vb.addLayout(self.scan_status_hb)


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