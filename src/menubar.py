from aqt import QMenu, mw
from aqt.qt import QAction, QKeySequence, Qt, QIcon
from .config import get_config_value
from .api import show_queue_picker, show_quick_open_pdf, queue_has_items, try_open_first_in_queue
from aqt.utils import showInfo, tooltip
from .dialogs.editor import NoteEditor
from .dialogs.importing.zotero_import import ZoteroImporter
from .dialogs.importing.quick_youtube_import import QuickYoutubeImport
from .dialogs.importing.quick_web_import import QuickWebImport
from .dialogs.settings import SettingsDialog


import state
import utility.misc

class Menu():

    def __init__(self):
        self.quick_web = None

        # state.night_mode is not yet set here
        nightmode = False
        if hasattr(mw.pm, "night_mode"):
            nightmode = mw.pm.night_mode()

        # gc_icn = "graduation_cap_night.png" if nightmode else "graduation_cap.png"

        menu            = get_menu(mw, "&SIAC")
        submenu_import  = get_sub_menu(menu, "Import")

        menu.setStyleSheet("""
            QMenu::icon {
                padding-right: 30px;
            }
        """)

        import_options=( #SHORTCUT_CONF_KEY, TITLE, CALLBACK
            ("shortcuts.menubar.import.create_new", "Create New",           self.import_create_new),
            ("shortcuts.menubar.import.web",        "Web",    self.import_web),
            ("shortcuts.menubar.import.youtube",    "YouTube",       self.import_youtube),
            ("shortcuts.menubar.import.zotero_csv", "Zotero CSV",    self.import_zotero)
        )

        add_menu_actions(submenu_import, import_options)


        menu_options=( # CONF_KEY, TITLE, CALLBACK
            ("shortcuts.menubar.queue_manager",  "Queue Manager",       self.queue_picker),
            ("shortcuts.menubar.read_first",     "Read first in Queue", self.read_first),
            ("shortcuts.menubar.quick_open",     "Quick Open...",       self.quick_open),
            ("shortcuts.menubar.addon_settings", "Add-on Settings",     self.settings)
        )


        add_menu_actions(menu, menu_options)

    def import_zotero(self):
        dialog = ZoteroImporter(mw.app.activeWindow())

        if dialog.exec_():
            tooltip(f"Created {dialog.total_count} notes.")

    def import_web(self):
        if self.quick_web is None:
            self.quick_web = QuickWebImport()

        self.quick_web.show()
        self.quick_web.raise_()

        #if dialog.exec_():

    def import_youtube(self):
        active_win = mw.app.activeWindow()
        dialog = QuickYoutubeImport(active_win)

        if dialog.exec_():
            title   = dialog.youtube_title
            channel = dialog.youtube_channel
            url     = dialog.youtube_url

            text=f"""Title: {title}""" + "  \n" + f"""Channel: {channel}"""

            note_editor = NoteEditor(active_win, title_prefill = title, text_prefill = text, source_prefill = url, author_prefill = channel, url_prefill = url)

    def import_create_new(self):
        dialog = NoteEditor(mw.app.activeWindow())

    def quick_open(self):
        show_quick_open_pdf()

    def queue_picker(self):
        show_queue_picker()

    def settings(self):
        dialog = SettingsDialog(mw.app.activeWindow())

    def read_first(self):
        if not queue_has_items():
            tooltip("Queue is empty!")
            return

        try_open_first_in_queue()


def get_menu(parent, menuName, icon = None):
    menubar = parent.form.menubar
    for a in menubar.actions():
        if menuName == a.text():
            return a.menu()
    else:
        if icon:
            icon = QIcon(utility.misc.get_web_folder_path()+ "icons/" + icon)
            return menubar.addMenu(icon, menuName)
        return menubar.addMenu(menuName)


def get_sub_menu(menu, subMenuName):
    for a in menu.actions():
        if subMenuName == a.text():
            return a.menu()
    else:
        subMenu = QMenu(subMenuName, menu)
        menu.addMenu(subMenu)
        return subMenu

def add_menu_actions(menu, menu_options):
    for mp in menu_options:

        k   = mp[0]
        t   = mp[1]
        cb  = mp[2]

        hk = 0
        if k:
            hk = get_config_value(k)

        act = QAction(t,menu)
        if hk:
            act.setShortcut(QKeySequence(hk))
            act.setShortcutContext(Qt.ApplicationShortcut)

        if len(mp) > 3:
            icon = mp[3]
            icon = QIcon(utility.misc.get_web_folder_path()+ "icons/" + icon)
            act.setIcon(icon)


        act.triggered.connect(cb)
        menu.addAction(act)
