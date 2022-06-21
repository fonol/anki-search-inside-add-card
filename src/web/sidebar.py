import typing
from typing import List, Optional, Tuple, Any
from aqt.editor import Editor
from anki.utils import isMac, isLin
from aqt import mw

from ..notes import get_note, get_all_tags_with_counts, get_notes_scheduled_for_today
from ..config import get_config_value_or_default as conf_or_def
from ..internals import HTML
from .templating import filled_template
import utility.misc
import utility.tags
import utility.text

class Sidebar:
    """ The toggle-able sidebar that is displayed left of the results. """

    def __init__(self):

        self.ADDON_NOTES_TAB        : int       = 1
        self.PDF_IMPORT_TAB         : int       = 2
        self.SPECIAL_SEARCHES_TAB   : int       = 3

        self.tab                    : int       = self.ADDON_NOTES_TAB
        self._editor                : Editor    = None

    def set_editor(self, editor: Editor):
        self._editor = editor

    def _html(self) -> HTML:

        tab_displayed_name = self._tab_displayed_name()

        if self.tab == self.ADDON_NOTES_TAB:
            (tmap, tcounts) = get_all_tags_with_counts()

            def iterateMap(tmap, prefix, start=False):
                if start:
                    html = "<ul class='deck-sub-list outer'>"
                else:
                    html = "<ul class='deck-sub-list'>"
                for key, value in tmap.items():
                    full = prefix + "::" + key if prefix else key
                    html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); searchUserNoteTag(event, '%s');\"><b class='exp' data-t='%s'>%s</b> %s <span class='siac-tag-cnt'>%s</span><i class='siac-tl-plus fa fa-plus mr-5 ml-5' onclick='event.stopPropagation(); pycmd(\"siac-create-note-tag-prefill %s\") '></i>%s</li>" % (full, full.replace("'", ""), "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), tcounts.get(full.lower(), "?"), full, iterateMap(value, full, False))
                html += "</ul>"
                return html

            tag_html            = iterateMap(tmap, "", True)
            tag_len             = len(tmap) if tmap is not None else 0

            # check if there are any notes scheduled for today
            scheduled_for_today = get_notes_scheduled_for_today()
            if scheduled_for_today is not None and len(scheduled_for_today) > 0:
                sched_today_menu_item = f"""<div class='siac-notes-sidebar-item' onclick='pycmd("siac-r-show-due-today")'>&nbsp; Due today ({len(scheduled_for_today)})</div>"""
            else:
                sched_today_menu_item = ""

            tab_html = filled_template("sidebar_main/sidebar_addon_tab", dict(sched_today_menu_item = sched_today_menu_item, tag_len = tag_len, tag_html = tag_html))

        elif self.tab == self.PDF_IMPORT_TAB:

            folders_to_search = conf_or_def("pdf.import.folders_to_search", [])
            exp = ""
            if len(folders_to_search) == 0:
                folders = """
                    <div style='padding: 15px; box-sizing: border-box; word-break: break-word;' class='siac-sidebar-bg h-100'>
                        <center>
                            <strong>
                                To browse local folders for pdfs, add some entries to the config option
                                "pdf.import.folders_to_search", e.g. <br><br>
                                "pdf.import.folders_to_search" : ["Some/Path/Documents/Uni", "Some/Path/Documents/Unsorted"] <br><br>
                                
                                The given folders (including their subfolders!) will be scanned for *.pdf files.
                                Don't use too large folders here, because they are searched everytime the tab is opened so you might see a delay then. 
                            </strong>
                        </center>
                    </div>
                """
            else:
                cleaned = []
                for f in folders_to_search:
                    if len(f.strip()) == 0:
                        continue
                    cleaned.append(f.replace("\\", "/"))
                if len(cleaned) == 0:
                    folders = """
                    <div style='padding: 15px;' class='siac-sidebar-bg'>
                        <center style='margin-top: 100px;'>
                            <strong>
                                Could not find any pdf files in the specified folders.
                            </strong>
                        </center>
                    </div>
                    """
                else:
                    files = []
                    for f in cleaned:
                        files += utility.misc.find_pdf_files_in_dir_recursive(f, cut_path=False)
                    
                    map = utility.tags.to_tag_hierarchy(files, sep="/")
                    map = utility.tags.flatten_map(map, "/")
                    def iterateMap(tmap, prefix, start=False):
                        if start:
                            html = "<ul class='deck-sub-list outer'>"
                        else:
                            html = "<ul class='deck-sub-list'>"
                        for key, value in tmap.items():
                            full        = prefix + "/" + key if prefix else key
                            if isMac or isLin and not full.startswith("/"):
                                full = f"/{full}"
                            click       = f"pycmd(\"siac-create-note-source-prefill {full}\")" if full.endswith(".pdf") else ""
                            exp         = "[+]" if value else ""
                            should_bold = "style='font-weight: bold;'" if value else ""
                            html        = f"{html}<li class='deck-list-item' onclick='event.stopPropagation(); {click}' {should_bold}><b class='exp'>{exp}</b> {utility.text.trim_if_longer_than(key, 35)}{iterateMap(value, full, False)}</li>"
                        html += "</ul>"
                        return html
                    folders = iterateMap(map, "", True)
                    folders = f"""<div style='margin-top: 15px;'>
                        {folders} 
                    </div>"""
                    exp = f"""
                        <div class='' style='flex: 1 0 auto;'>
                            <div class='w-100' style='margin-top: 20px;'><b>PDFs in Folders</b>
                                <b class='siac-tags-exp-icon' style='margin-right: 15px; padding: 0 2px 0 2px;' onclick='noteSidebarCollapseAll();'>&#x25B2;</b>
                                <b class='siac-tags-exp-icon mr-5' style='padding: 0 2px 0 2px;' onclick='noteSidebarExpandAll();'>&#x25BC;</b>
                            </div>
                        </div>
                    """

            tab_html = f"""
                {exp}
                <div class='' style='flex: 1 0 auto; overflow-y: auto;'>
                    {folders}
                </div>
            """

        elif self.tab == self.SPECIAL_SEARCHES_TAB:
            anki_tags   = mw.col.tags.all()
            tmap        = utility.tags.to_tag_hierarchy(anki_tags)

            def iterateMap(tmap, prefix, start=False):
                if start:
                    html = "<ul class='deck-sub-list outer'>"
                else:
                    html = "<ul class='deck-sub-list'>"
                for key, value in tmap.items():
                    full = prefix + "::" + key if prefix else key
                    html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); pycmd('siac-r-search-tag %s');\"><b class='exp' data-t='%s'>%s</b> %s %s</li>" % (full, full.replace("'", ""), "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), iterateMap(value, full, False))
                html += "</ul>"
                return html

            tag_html            = iterateMap(tmap, "", True)

            tab_html = filled_template("sidebar_main/sidebar_anki_tab", { "tags" : tag_html})

        return filled_template("sidebar_main/sidebar", dict(tab_html = tab_html, tab_displayed_name = tab_displayed_name))

    def display(self):
        html = self._html()
        self._editor.web.eval("""var sbFn = () => {
        if (!document.getElementById('resultsWrapper')) {
            setTimeout(sbFn, 50);
            return;
        }
        if (document.getElementById('siac-notes-sidebar')) {
            $('#siac-notes-sidebar').remove();
        }
        document.getElementById('resultsWrapper').insertAdjacentHTML("afterbegin", `%s`); 
        if (typeof(window._siacSidebar) === 'undefined') {
            window._siacSidebar = {
                addonTagsExpanded : [],
                ankiTagsExpanded : [],
                tab: '',
            };
        }
        window._siacSidebar.tab = %s;
        
        $('#siac-notes-sidebar .exp').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            let icn = $(this);
            if (icn.text()) {
                if (icn.text() === '[+]') {
                    icn.text('[-]');
                    if (_siacSidebar.tab === 1 || _siacSidebar.tab === 3) {
                        let exp_list = window._siacSidebar.tab === 1 ? _siacSidebar.addonTagsExpanded : _siacSidebar.ankiTagsExpanded;
                        if (exp_list.indexOf(this.dataset.t) === -1) {
                            exp_list.push(this.dataset.t);
                        }
                    }
                } else {
                    icn.text('[+]');
                    if (_siacSidebar.tab === 1 || _siacSidebar.tab === 3) {
                        let exp_list = window._siacSidebar.tab === 1 ? _siacSidebar.addonTagsExpanded : _siacSidebar.ankiTagsExpanded;
                        if (exp_list.indexOf(this.dataset.t) !== -1) {
                            exp_list.splice(exp_list.indexOf(this.dataset.t), 1);
                        }
                    }
                }
            }
            $(this).parent().children('ul').toggle();
        });
        let exp = [];
        let scrollTop = 0;
        if (window._siacSidebar.tab === 1) {
            exp = window._siacSidebar.addonTagsExpanded;
            scrollTop = window._siacSidebar.addonTagsScrollTop;
        } else if (window._siacSidebar.tab === 3) {
            exp = window._siacSidebar.ankiTagsExpanded;
            scrollTop = window._siacSidebar.ankiTagsScrollTop;
        }
        for (var t of exp) {
            $('#siac-notes-sidebar .exp[data-t="'+t+'"]').trigger('click');
        }
        if (scrollTop && scrollTop > 0) {
            $('.tag_scroll').first().get(0).scrollTop = scrollTop;
        }
        };
        sbFn();
        """ % (html, self.tab))

    def hide(self):
        self._editor.web.eval("$('#siac-notes-sidebar').remove(); $('#resultsWrapper').css('padding-left', 0);")

    def refresh_tab(self, tab: int):
        if conf_or_def("notes.sidebar.visible", False):
            if self.tab == tab:
                self.refresh()

    def refresh(self):
        if self._editor is None:
            return
        self.display()
    

    def show_tab(self, tab: int):
        self.tab = tab
        self.refresh()


    def _tab_displayed_name(self) -> str:
        if self.tab == self.PDF_IMPORT_TAB:
            return "PDF Import"
        elif self.tab == self.ADDON_NOTES_TAB:
            return "Add-on Notes"
        elif self.tab == self.SPECIAL_SEARCHES_TAB:
            return "Anki Notes"