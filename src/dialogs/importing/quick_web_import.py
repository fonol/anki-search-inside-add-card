# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#TODO: tidy up, make config accessible from either settings or describe in config.md
from aqt.qt import *
import sip
import time
import re
import urllib
from aqt.qt import *
from aqt import mw
import aqt
from anki.utils import isMac

from ...config import get_config_value, get_config_value_or_default
from ...web_import import import_webpage
from ..editor import NoteEditor

import utility.misc
import utility.text


class QuickWebImport(QWidget):
    def __init__(self):

        QWidget.__init__(self)
        self.config             = mw.addonManager.getConfig(__name__)
        #self.auto_focus_field   = self.config["auto_focus_first_field_after_toggle_fields"]
        self.auto_focus_field   = True

        self.nightmode          = True
        self.setWindowTitle("Quick Web Import")

        # note settings
        self.web_title          = None
        self.source             = None
        self.web_url            = None
        self.text               = None

        self.layout             = QVBoxLayout()
        self.toplayout          = QHBoxLayout()

        self.menu = QWidget()
        menu_vbox = QVBoxLayout()

        # build bookmarks list
        btree = QTreeWidget()
        btree.itemClicked.connect(self.bookmark_clicked)
        bookmarks = self.config["import.quickweb.bookmarks"]
        #expand = config["expand_bookmark_folders_by_default"]
        expand = True
        for k, blist in bookmarks.items():
            folder = QTreeWidgetItem(btree, [k])
            folder.setExpanded(expand)
            for b in blist:
                b = re.sub("(https?://)?(www2?\\.)?", "", b)
                if b.endswith("/"):
                    b = b[:-1]
                item = QTreeWidgetItem([b])
                folder.addChild(item)
        btree.setHeaderLabels(["Bookmarks"])
        btree.setIconSize(QSize(0,0))
        menu_vbox.addWidget(btree, 2)

        seq = get_config_value("shortcuts.quickweb.search_on_page")
        menu_vbox.addWidget(QLabel(f"""
            Search on site shortcut: {seq}
        """))
        self.menu.setLayout(menu_vbox)

        self.menu.setVisible(False)

        self.setMinimumHeight(600)
        self.setMinimumWidth(900)

        line                    = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        back_btn = QPushButton(" < ")
        back_btn.clicked.connect(self.back)
        forward_btn = QPushButton(" > ")
        forward_btn.clicked.connect(self.forward)
        reload_btn = QPushButton(u"\u21BB")
        reload_btn.clicked.connect(self.page_refresh)
        self.toplayout.addWidget(line, 0)
        self.toplayout.addWidget(back_btn, 0)
        self.toplayout.addWidget(forward_btn, 0)
        self.toplayout.addWidget(reload_btn, 0)

        self.url = UrlInput(self.load_url)
        self.url.returnPressed.connect(self.load_url)
        self.toplayout.addWidget(self.url, 2)

        zoom_out = QPushButton(" - ")
        zoom_out.clicked.connect(self.zoom_out)
        zoom_out.setShortcut("Ctrl+-")
        zoom_in = QPushButton(" + ")
        zoom_in.clicked.connect(self.zoom_in)
        zoom_in.setShortcut("Ctrl++")
        self.toplayout.addWidget(zoom_out)
        self.toplayout.addWidget(zoom_in)


        if not isMac:
            back_btn.setMaximumWidth(back_btn.fontMetrics().boundingRect(" < ").width() + 15)
            reload_btn.setMaximumWidth(reload_btn.fontMetrics().boundingRect(u"\u21BB").width() + 15)
            forward_btn.setMaximumWidth(forward_btn.fontMetrics().boundingRect(" > ").width() + 15)
            zoom_out.setMaximumWidth(zoom_out.fontMetrics().boundingRect(" - ").width() + 15)
            zoom_in.setMaximumWidth(zoom_in.fontMetrics().boundingRect(" + ").width() + 15)

        menu = QPushButton("...")
        menu.setShortcut(get_config_value("shortcuts.quickweb.toggle_bookmarks"))
        menu.clicked.connect(self.toggle_menu)
        self.toplayout.addWidget(menu)

        self.tabs = QuickImportBrowserTabs(self)

        self._search_panel = SearchBar()
        self.search_toolbar = QToolBar()
        self.search_toolbar.addWidget(self._search_panel)
        self.search_toolbar.hide()
        self._search_panel.search_sig.connect(self.on_searched)
        self._search_panel.close_sig.connect(self.search_toolbar.hide)

        self.layout.addLayout(self.toplayout)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.search_toolbar)

        hb_bottom = QHBoxLayout()
        import_external    = QPushButton("Import as External")
        import_as_markdown = QPushButton("Import as Markdown")
        import_as_pdf      = QPushButton("Import as PDF")
        cancel             = QPushButton("Close")

        import_external.clicked.connect(self.external)
        import_as_markdown.clicked.connect(self.markdown)
        import_as_pdf.clicked.connect(self.pdf)
        cancel.clicked.connect(self.close)
        cancel.setShortcut("Escape")

        hb_bottom.addWidget(import_external)
        hb_bottom.addWidget(import_as_markdown)
        hb_bottom.addWidget(import_as_pdf)
        hb_bottom.addStretch()

        hb_bottom.addWidget(cancel)
        self.layout.addLayout(hb_bottom)

        menu_width = self.config["import.quickweb.bookmarks_width_percent"]
        self.layout.setContentsMargins(0,4,4,4)
        parentbox = QHBoxLayout()
        parentbox.addLayout(self.layout, 100 - menu_width)
        parentbox.addWidget(self.menu, menu_width)

        self.setLayout(parentbox)

        seq = get_config_value("shortcuts.quickweb.search_on_page")
        self.sc = QShortcut(QKeySequence(seq), self)
        self.sc.activated.connect(self.search_toolbar.show)
        self.sc.setEnabled(True)

        self.url_re = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def bookmark_clicked(self, item):
        if item.parent() is None:
            return
        self.load(item.text(0))

    def toggle_menu(self):
        """
            Toggle bookmarks visibility.
        """
        if self.menu.isHidden():
            self.menu.setVisible(True)
        else:
            self.menu.setVisible(False)

    def external(self):
        self.source = self.web_url

        self.open_note_window()

    def markdown(self):
        mdtext      = QTextEdit()
        self.source = ""
        mdtext.setHtml(import_webpage(self.web_url, inline_images=False))
        mdtext.setPlainText(mdtext.toMarkdown())
        self.text   = mdtext.toPlainText()
        self.open_note_window()

    def pdf(self):
        #TODO: tidy up functions to be not written 3x throughout add-on code
        name = self.web_title

        if name is None or len(name) == 0:
            name = utility.text.strip_url(self.web_url)
            name = utility.text.clean_file_name(name)
            return name
        name = utility.text.clean_file_name(name)

        path = get_config_value_or_default("pdfUrlImportSavePath", "")
        if path is None or len(path) == 0:
            tooltip("""You have to set a save path for imported URLs first.
                <center>Config value: <i>pdfUrlImportSavePath</i></center>
            """, period=4000)
            return
        path = utility.misc.get_pdf_save_full_path(path, name)
        utility.misc.url_to_pdf(self.web_url, path)

        self.source = path
        self.open_note_window()


    def open_note_window(self):
        self.web_url = self.url.text()

        dialog = NoteEditor(mw.app.activeWindow(),
                            title_prefill = self.web_title,
                            source_prefill = self.source,
                            url_prefill = self.web_url,
                            text_prefill = self.text)



    @pyqtSlot(str, QWebEnginePage.FindFlag)
    def on_searched(self, text, flag):
        def after(found):
            if text and not found:
                self._search_panel.signal_not_found()
            else:
                self._search_panel.signal_found()
        self.tabs.active_view().findText(text, flag, after)

    def load_url(self):
        url = self.url.text()
        if url is not None and len(url) > 0:
            if self.url_re.match(url):
                qurl = QUrl(url)
                qurl.setScheme("http")
                self.tabs.load(qurl)
            else:
                url = self.config["import.quickweb.search_engine"].replace("{query}", urllib.parse.quote_plus(url))
                self.tabs.load(QUrl(url))

    def update_url(self, url, title):
        self.url.setText(url)
        self.web_title = title
        self.web_url = url

    def page_refresh(self):
        self.tabs.page_refresh()

    def back(self):
        self.tabs.back()

    def forward(self):
        self.tabs.forward()

    def zoom_in(self):
        self.tabs.zoom_in()

    def zoom_out(self):
        self.tabs.zoom_out()

    def load(self, url):
        if url is not None and len(url) > 0:
            url = QUrl(url)
            url.setScheme("http")
            self.tabs.load(url)

class QuickImportBrowserTabs(QTabWidget):

    def __init__(self, parent = None):
        self.parent = parent
        QTabWidget.__init__(self, parent)

        self.setTabsClosable(True)
        config = mw.addonManager.getConfig(__name__)

        self.start = QUrl(config["import.quickweb.default_page"])
        self.views = []

        self._add_tab()
        self.addTab(QWidget(), "+")
        if self.tabBar().tabButton(1, QTabBar.RightSide) is not None:
            self.tabBar().tabButton(1, QTabBar.RightSide).resize(0,0)

        self.currentChanged.connect(self._tab_clicked)
        self.tabCloseRequested.connect(self._tab_close)

        # maybe that fixes tabs being centered on mac
        if isMac:
            self.setStyleSheet("""
                QTabWidget::tab-bar {
                    left: 0;
                }
            """)

    def _add_tab(self, page=""):
        v = self._new_view(page)
        self.insertTab(max(0, self.count() -1), v, "Loading...")

        return v

    def _new_view(self, page=""):
        view = QuickImportWebView(self)
        # view.urlChanged.connect(self._view_url_changed)
        id = str(int(time.time() * 1000))
        view.setWindowTitle(id)

        self.views.append(view)
        if page is not None and len(page) > 0:
            view.load(self._to_qurl(page))
        else:
            view.load(self.start)

        return view

    def _to_qurl(self, str):
        qurl = QUrl(str)
        qurl.setScheme("http")
        return qurl

    def _tab_clicked(self, ix):
        if ix == self.count() - 1:
            self._add_tab()
            self.setCurrentIndex(ix)
        else:
            self.parent.update_url(self.active_view().url().toDisplayString(), self.active_view().title())

    def _tab_close(self, ix):
        if self.count() == 2:
            return
        self.blockSignals(True)

        self.removeTab(ix)
        sip.delete(self.views[ix])
        del self.views[ix]
        self.blockSignals(False)
        if self.count() == 2:
            self.setCurrentIndex(0)
        elif self.currentIndex() == self.count()- 1:
            self.setCurrentIndex(self.count() -2)

    def update_view_title(self, id, title):
        for ix in range(0, self.count()):
            if self.widget(ix).windowTitle() == id:
                self.setTabText(ix, title)
                self.parent.update_url(self.active_view().url().toDisplayString(), self.active_view().title())

    def _view_title_changed(self, title):
        self.setTabText(self.currentIndex(), title)

    def _view_url_changed(self, id, url):
        if self.active_view().windowTitle() == id:
            self.parent.update_url(url.toDisplayString(), self.active_view().title())

    def load(self, qurl):
        # self.setTabText(self.currentIndex(), "Loading...")
        self.active_view().load(qurl)

    def page_refresh(self):
        self.load(self.active_view().url())

    def back(self):
        self.active_view().back()

    def forward(self):
        self.active_view().forward()

    def zoom_out(self):
        z = self.active_view().zoomFactor()
        if z > 0.1:
            z = z - 0.1
        self.active_view().setZoomFactor(z)

    def zoom_in(self):
        z = self.active_view().zoomFactor()
        z = z + 0.1
        self.active_view().setZoomFactor(z)

    def active_view(self):
        return self.views[self.currentIndex()]

class QuickImportWebView(QWebEngineView):
    def __init__(self, parent=None):
        QWebEngineView.__init__(self, parent)
        if parent is not None:
            # self.titleChanged.connect(self.view_title_changed)
            self.loadStarted.connect(self.load_started)
            self.loadFinished.connect(self.load_finished)
            self.titleChanged.connect(self.view_title_changed)
            self.urlChanged.connect(self.url_changed)
        self.settings().setAttribute(QWebEngineSettings.PluginsEnabled,True)
        self.page().profile().setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        self.parent = parent

    def view_title_changed(self, title):
        self.parent.update_view_title(self.windowTitle(), title)

    def load_finished(self, ok):
        self.parent.update_view_title(self.windowTitle(), self.title())

    def load_started(self):
        return
        self.parent.update_view_title(self.windowTitle(), "Loading...")

    def url_changed(self, url):
        self.parent._view_url_changed(self.windowTitle(), url)

    def createWindow(self, windowType):
        if windowType == QWebEnginePage.WebBrowserTab:
            v = self.parent._add_tab(self.page().requestedUrl().toDisplayString())
            return v
        return super(QuickImportWebView, self).createWindow(windowType)

class UrlInput(QLineEdit):
    def __init__(self, cb, parent=None):
        QLineEdit.__init__(self, parent)
        self.cb = cb
        self.suggestions = []
        self.completer = QCompleter(self.suggestions, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Enter or e.key() == Qt.Key_Return:
            self.cb()
            self._refresh_completer()
            e.accept()
        else:
            QLineEdit.keyPressEvent(self, e)

    def _refresh_completer(self):
        t = QUrl(self.text()).toDisplayString()
        if len(t) > 0 and not t in self.suggestions:
            self.suggestions.append(t)
            self.completer = QCompleter(self.suggestions, self)
            self.completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.setCompleter(self.completer)

    def mousePressEvent(self, e):
        self.selectAll()


class SuppressLineEdit(QLineEdit):
    """
        Don't propagate enter/return to accept the add dialog.
    """
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Enter or e.key() == Qt.Key_Return:
            e.accept()
        else:
            QLineEdit.keyPressEvent(self, e)


class SearchBar(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        close_btn = QPushButton('Close')
        next_btn = QPushButton('Next')
        prev_btn = QPushButton('Previous')
        self.case_btn = QPushButton('Aa', checkable=True)
        self.input = SuppressLineEdit()
        self.setFocusProxy(self.input)
        close_btn.clicked.connect(self.close_sig)
        next_btn.clicked.connect(self.on_search_forward)
        prev_btn.clicked.connect(self.on_search_prev)
        self.case_btn.clicked.connect(self.on_search_forward)
        for btn in [self.case_btn, self.input, next_btn, prev_btn, close_btn]:
            self.layout.addWidget(btn)
            if isinstance(btn, QPushButton):
                btn.clicked.connect(self.setFocus)
        self.close_sig.connect(self.input.clear)
        self.input.textChanged.connect(self.on_search_forward)
        self.input.returnPressed.connect(self.on_search_forward)

        QShortcut(QKeySequence.FindNext, self, activated=next_btn.animateClick)
        QShortcut(QKeySequence.FindPrevious, self, activated=prev_btn.animateClick)
        #QShortcut(QKeySequence(get_config_value(shortcuts.quickweb.search_on_page)), self.input, activated=self.close_sig)

    def signal_not_found(self):
        self.input.setStyleSheet("color: red;")

    def signal_found(self):
        self.input.setStyleSheet("color: green;")

    @pyqtSlot()
    def on_search_prev(self):
        self.on_search_forward(QWebEnginePage.FindBackward)

    @pyqtSlot()
    def on_search_forward(self, direction= QWebEnginePage.FindFlag()):
        flag = direction
        if self.case_btn.isChecked():
            flag |= QWebEnginePage.FindCaseSensitively
        self.search_sig.emit(self.input.text(), flag)

    def showEvent(self, event):
        super(SearchBar, self).showEvent(event)
        self.setFocus(True)

    search_sig = pyqtSignal(str, QWebEnginePage.FindFlag)
    close_sig = pyqtSignal()
