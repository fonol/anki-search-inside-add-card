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


import platform
import os
import json
import re
import datetime
import time
import sys
from aqt import mw
from aqt.utils import showInfo

import utility.tags
import utility.text
import utility.misc

from ..tag_find import get_most_active_tags
from ..state import get_index, check_index, set_deck_map
from ..notes import get_note, _get_priority_list, get_all_tags, get_read_pages, get_pdf_marks, insert_pages_total, get_read_today_count
from .html import *
from ..internals import js, requires_index_loaded, perf_time
from ..config import get_config_value_or_default

@js
def toggleAddon():
    return "toggleAddon();"


def getScriptPlatformSpecific():
    """
        Returns the css and js used by the add-on in <style>/<script> tags. 
        Some placeholders in the scripts.js file and in the styles.css file are replaced 
        by config values.

        They could be exposed on the internal web server, but as they contain placeholders for config-defined styles, 
        it is easier for now that way.
    """
    #get path
    dir = utility.misc.get_web_folder_path()
    #css + js
    all = """
    <style>
    %s
    </style>

    <script type='text/javascript'>
    %s
    </script>
    """
    with open(dir + "scripts.js") as f:
        script = f.read()
    with open(dir + "styles.css") as f:
        css = f.read().replace("%", "%%")
    with open(dir + "pdf_reader.css") as f:
        css += f.read().replace("%", "%%")

    deckSelectFontSize = get_config_value_or_default(["styling", "topBar", "deckSelectFontSize"], 11)
    noteFontSize = get_config_value_or_default(["styling", "general", "noteFontSize"], 12)
    noteForegroundColor = get_config_value_or_default(["styling", "general", "noteForegroundColor"], "black")
    noteBackgroundColor = get_config_value_or_default(["styling", "general", "noteBackgroundColor"], "white")
    noteBorderColor = get_config_value_or_default(["styling", "general", "noteBorderColor"], "grey")
    noteHoverBorderColor = get_config_value_or_default(["styling", "general", "noteHoverBorderColor"], "#2496dc")
    tagBackgroundColor = get_config_value_or_default(["styling", "general", "tagBackgroundColor"], "#f0506e")
    tagForegroundColor = get_config_value_or_default(["styling", "general", "tagForegroundColor"], "white")
    tagFontSize = get_config_value_or_default(["styling", "general", "tagFontSize"], 12)
    deckSelectForegroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectForegroundColor"], "black")
    deckSelectBackgroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectBackgroundColor"], "white")
    deckSelectHoverForegroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectHoverForegroundColor"], "white")
    deckSelectHoverBackgroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectHoverBackgroundColor"], "#5f6468")
    deckSelectButtonForegroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectButtonForegroundColor"], "grey")
    deckSelectButtonBackgroundColor = get_config_value_or_default(["styling", "topBar", "deckSelectButtonBackgroundColor"], "white")
    deckSelectButtonBorderColor = get_config_value_or_default(["styling", "topBar", "deckSelectButtonBorderColor"], "grey")
    deckSelectCheckmarkColor = get_config_value_or_default(["styling", "topBar", "deckSelectCheckmarkColor"], "grey")
    modalBackgroundColor = get_config_value_or_default(["styling", "modal", "modalBackgroundColor"], "white")
    modalForegroundColor = get_config_value_or_default(["styling", "modal", "modalForegroundColor"], "black")
    browserSearchButtonBorderColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchButtonBorderColor"], "#2496dc")
    browserSearchButtonBackgroundColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchButtonBackgroundColor"], "white")
    browserSearchButtonForegroundColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchButtonForegroundColor"], "#2496dc")
    browserSearchInputBorderColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchInputBorderColor"], "#2496dc")
    browserSearchInputBackgroundColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchInputBackgroundColor"], "white")
    browserSearchInputForegroundColor = get_config_value_or_default(["styling", "bottomBar", "browserSearchInputForegroundColor"], "#2496dc")
    infoButtonBorderColor = get_config_value_or_default(["styling", "general", "buttonBorderColor"], "#2496dc")
    infoButtonBackgroundColor = get_config_value_or_default(["styling", "general", "buttonBackgroundColor"], "white")
    infoButtonForegroundColor = get_config_value_or_default(["styling", "general", "buttonForegroundColor"], "#2496dc")
    highlightBackgroundColor = get_config_value_or_default(["styling", "general", "highlightBackgroundColor"], "yellow")
    highlightForegroundColor = get_config_value_or_default(["styling", "general", "highlightForegroundColor"], "black")
    rankingLabelBackgroundColor = get_config_value_or_default(["styling", "general", "rankingLabelBackgroundColor"], "#2496dc")
    rankingLabelForegroundColor = get_config_value_or_default(["styling", "general", "rankingLabelForegroundColor"], "white")
    selectBackgroundColor = get_config_value_or_default(["styling", "bottomBar", "selectBackgroundColor"], "white")
    selectForegroundColor = get_config_value_or_default(["styling", "bottomBar", "selectForegroundColor"], "black")
    stripedTableBackgroundColor = get_config_value_or_default(["styling", "modal", "stripedTableBackgroundColor"], "#f2f2f2")
    modalBorderColor = get_config_value_or_default(["styling", "modal", "modalBorderColor"], "#2496dc")
    keywordColor = get_config_value_or_default(["styling", "general", "keywordColor"], "#2496dc")
    fieldSeparatorColor = get_config_value_or_default(["styling", "general", "fieldSeparatorColor"], "#2496dc")
    windowColumnSeparatorColor = get_config_value_or_default(["styling", "general", "windowColumnSeparatorColor"], "#2496dc")
    timelineBoxBackgroundColor = get_config_value_or_default(["styling", "bottomBar", "timelineBoxBackgroundColor"], "#595959")
    timelineBoxBorderColor = get_config_value_or_default(["styling", "bottomBar", "timelineBoxBorderColor"], "#595959")
    imgMaxHeight = str(get_config_value_or_default("imageMaxHeight", 300)) + "px"
    pdfTooltipMaxHeight = str(get_config_value_or_default("pdfTooltipMaxHeight", 300))
    pdfTooltipMaxWidth = str(get_config_value_or_default("pdfTooltipMaxWidth", 250))

    css = css.replace("$deckSelectFontSize$", str(deckSelectFontSize) + "px")
    css = css.replace("$deckSelectForegroundColor$", deckSelectForegroundColor)
    css = css.replace("$deckSelectBackgroundColor$", deckSelectBackgroundColor)
    css = css.replace("$deckSelectHoverForegroundColor$", deckSelectHoverForegroundColor)
    css = css.replace("$deckSelectHoverBackgroundColor$", deckSelectHoverBackgroundColor)
    css = css.replace("$deckSelectButtonForegroundColor$", deckSelectButtonForegroundColor)
    css = css.replace("$deckSelectButtonBackgroundColor$", deckSelectButtonBackgroundColor)
    css = css.replace("$deckSelectButtonBorderColor$", deckSelectButtonBorderColor)
    css = css.replace("$deckSelectCheckmarkColor$", deckSelectCheckmarkColor)

    css = css.replace("$noteFontSize$", str(noteFontSize) + "px")
    css = css.replace("$noteForegroundColor$", noteForegroundColor)
    css = css.replace("$noteBackgroundColor$", noteBackgroundColor)
    css = css.replace("$noteBorderColor$", noteBorderColor)
    css = css.replace("$noteHoverBorderColor$", noteHoverBorderColor)
    css = css.replace("$tagBackgroundColor$", tagBackgroundColor)
    css = css.replace("$tagForegroundColor$", tagForegroundColor)
    css = css.replace("$tagFontSize$", str(tagFontSize) + "px")

    css = css.replace("$modalBackgroundColor$", modalBackgroundColor)
    css = css.replace("$modalForegroundColor$", modalForegroundColor)

    css = css.replace("$buttonBackgroundColor$", infoButtonBackgroundColor)
    css = css.replace("$buttonBorderColor$", infoButtonBorderColor)
    css = css.replace("$buttonForegroundColor$", infoButtonForegroundColor)

    css = css.replace("$fieldSeparatorColor$", fieldSeparatorColor)
    css = css.replace("$windowColumnSeparatorColor$", windowColumnSeparatorColor)

    css = css.replace("$browserSearchButtonBackgroundColor$", browserSearchButtonBackgroundColor)
    css = css.replace("$browserSearchButtonBorderColor$", browserSearchButtonBorderColor)
    css = css.replace("$browserSearchButtonForegroundColor$", browserSearchButtonForegroundColor)

    css = css.replace("$browserSearchInputBackgroundColor$", browserSearchInputBackgroundColor)
    css = css.replace("$browserSearchInputBorderColor$", browserSearchInputBorderColor)
    css = css.replace("$browserSearchInputForegroundColor$", browserSearchInputForegroundColor)

    css = css.replace("$highlightBackgroundColor$", highlightBackgroundColor)
    css = css.replace("$highlightForegroundColor$", highlightForegroundColor)

    css = css.replace("$rankingLabelBackgroundColor$", rankingLabelBackgroundColor)
    css = css.replace("$rankingLabelForegroundColor$", rankingLabelForegroundColor)

    css = css.replace("$selectBackgroundColor$", selectBackgroundColor)
    css = css.replace("$selectForegroundColor$", selectForegroundColor)

    css = css.replace("$timelineBoxBackgroundColor$", timelineBoxBackgroundColor)
    css = css.replace("$timelineBoxBorderColor$", timelineBoxBorderColor)


    css = css.replace("$keywordColor$", keywordColor)
    css = css.replace("$stripedTableBackgroundColor$", stripedTableBackgroundColor)
    css = css.replace("$modalBorderColor$", modalBorderColor)

    css = css.replace("$imgMaxHeight$", imgMaxHeight)
    css = css.replace("$pdfTooltipMaxHeight$", pdfTooltipMaxHeight)
    css = css.replace("$pdfTooltipMaxWidth$", pdfTooltipMaxWidth)

    css = css.replace("$zoom$", str(get_config_value_or_default("searchpane.zoom", 1.0)))
    renderImmediately = str(get_config_value_or_default("renderImmediately", False)).lower()
    script = script.replace("$renderImmediately$", renderImmediately)

    #replace command key with meta key for mac
    cplatform = platform.system().lower()
    if cplatform == "darwin":
        script = script.replace("event.ctrlKey", "event.metaKey")

    return all % (css, script)

def setup_ui_after_index_built(editor, index, init_time=None):
    #editor is None if index building finishes while add dialog is not open
    if editor is None:
        return
    config = mw.addonManager.getConfig(__name__)
    showSearchResultArea(editor, init_time)
    #restore previous settings
    cmd = ""
    if not index.highlighting:
       cmd += "$('#highlightCb').prop('checked', false);"
    if not get_config_value_or_default("searchOnTyping", True):
        cmd += "$('#typingCb').prop('checked', false); setSearchOnTyping(false);"
    if not get_config_value_or_default("searchOnSelection", True):
        cmd += "$('#selectionCb').prop('checked', false); siacState.searchOnSelection = false;"
    if not index.topToggled:
        cmd += "hideTop();"
    if index.ui is not None and not index.ui.uiVisible:
        cmd += "$('#siac-right-side').addClass('addon-hidden');"
    if config["gridView"]:
        cmd += "activateGridView();" 
    editor.web.eval(cmd)
    if index.ui is not None:
        #plot.js is already loaded if a note was just added, so this is a lazy solution for now
        index.ui.plotjsLoaded = False
    if config["notes.sidebar.visible"]:
        index.ui.sidebar.display()
        

def showSearchResultArea(editor=None, initializationTime=0):
    """
    Toggle between the loader and search result area when the index has finished building.
    """
    js = """
        if (document.getElementById('searchResults')) {
            document.getElementById('searchResults').style.display = 'block';
        }
        if (document.getElementById('loader')) {
            document.getElementById('loader').style.display = 'none';
        }"""
    if check_index():
        get_index().ui.js(js)
    elif editor is not None and editor.web is not None:
        editor.web.eval(js)



def printStartingInfo(editor):
    """
        Displays the information that is visible after the first start of the add-on.
    """
    if editor is None or editor.web is None:
        return
    config = mw.addonManager.getConfig(__name__)
    index = get_index()
    html = "<h3>Search is <span style='color: green'>ready</span>. (%s)</h3>" %  index.type if index is not None else "?"
    if index is not None:
        html += "Initalized in <b>%s</b> s." % index.initializationTime
        if not index.creation_info["index_was_rebuilt"]:
            html += " (No changes detected, index was <b>not</b> rebuilt)"
        html += "<br/>Index contains <b>%s</b> notes." % index.get_number_of_notes()
        html += "<br/>Index is always rebuilt if smaller than <b>%s</b> notes." % config["alwaysRebuildIndexIfSmallerThan"]
        html += "<br/><i>Search on typing</i> delay is set to <b>%s</b> ms." % config["delayWhileTyping"]
        html += "<br/>Logging is turned <b>%s</b>. %s" % ("on" if index.logging else "off", "You should probably disable it if you don't have any problems." if index.logging else "")
        html += "<br/>Results are rendered <b>%s</b>." % ("immediately" if config["renderImmediately"] else "with fade-in")
        html += "<br/>Tag Info on hover is <b>%s</b>.%s" % ("shown" if config["showTagInfoOnHover"] else "not shown", (" Delay: [<b>%s</b> ms]" % config["tagHoverDelayInMiliSec"]) if config["showTagInfoOnHover"] else "")
        html += "<br/>Image max height is <b>%s</b> px." % config["imageMaxHeight"]
        html += "<br/>Retention is <b>%s</b> in the results." % ("shown" if config["showRetentionScores"] else "not shown")
        html += "<br/>Window split is <b>%s / %s</b>." % (config["leftSideWidthInPercent"], 100 - int(config["leftSideWidthInPercent"]))
        html += "<br/>Shortcut is <b>%s</b>." % (config["toggleShortcut"])

    if index is None or index.ui is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"


    editor.web.eval("document.getElementById('searchResults').innerHTML = `<div id='startInfo'>%s</div>`;" % html)

@requires_index_loaded
def display_model_dialog():
    """
        Called after clicking on "Set Fields" in the settings modal.
    """
    if check_index():
        html = get_model_dialog_html()
        get_index().ui.show_in_modal_subpage(html)



@js
def showStylingModal(editor):
    config = mw.addonManager.getConfig(__name__)
    html = stylingModal(config)
    index = get_index()
    index.ui.showInModal(html)
    return "$('.modal-close').on('click', function() {pycmd(`writeConfig`) })"

@js
def show_unsuspend_modal(nid):
    html = get_unsuspend_modal(nid)
    index = get_index()
    index.ui.showInModal(html)
    return "$('.modal-close').on('click', function() {pycmd(`siac-rerender`);$('.modal-close').off('click'); })"


@js
def display_note_del_confirm_modal(editor, nid):
    html = get_note_delete_confirm_modal_html(nid)
    return "$('#greyout').show();$('#searchResults').append(`%s`);" % html




   

def fillTagSelect(editor = None, expanded = False) :
    """
    Builds the html for the "browse tags" mode in the deck select.
    Also renders the html.
    """
    tags = mw.col.tags.all()
    user_note_tags = get_all_tags()
    tags.extend(user_note_tags)
    tags = set(tags)
    tmap = utility.tags.to_tag_hierarchy(tags)

    most_active = get_most_active_tags(5)
    most_active_map = dict()
    for t in most_active:
        if t in tmap:
            most_active_map[t] = tmap[t]
        else:
            most_active_map[t] = {}


    def iterateMap(tmap, prefix, start=False):
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in tmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item' onclick=\"event.stopPropagation(); pycmd('searchTag %s')\"><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % (full, "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), iterateMap(value, full, False))
        html += "</ul>"
        return html

    most_active_html = iterateMap(most_active_map, "", True)
    html = iterateMap(tmap, "", True)

    # the dropdown should only be expanded on user click, not on initial render
    expanded_js = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""

    cmd = """
    document.getElementById('deck-sel-info-lbl').style.display = 'none';
    document.getElementById('deckSelQuickWrapper').style.display = '%s';
    document.getElementById('deckSelQuick').innerHTML = `%s`;
    document.getElementById('deckSel').innerHTML = `%s`;
    $('#deckSelWrapper .exp').click(function(e) {
		e.stopPropagation();
        let icn = $(this);
        if (icn.text()) {
            if (icn.text() === '[+]')
                icn.text('[-]');
            else
                icn.text('[+]');
        }
        $(this).parent().parent().children('ul').toggle();
    });
    $("#siac-deck-sel-btn-wrapper").hide();
    %s
    """ % ("block" if len(most_active_map) > 0 else "none", most_active_html, html, expanded_js)
    if editor is not None:
        editor.web.eval(cmd)
    else:
        get_index().ui.js(cmd)

def fillDeckSelect(editor = None, expanded= False):
    """
    Fill the selection with user's decks
    """

    deckMap = dict()
    config = mw.addonManager.getConfig(__name__)
    deckList = config['decks']
    index = get_index()
    if editor is None:
        if index is not None and index.ui is not None and index.ui._editor is not None:
            editor = index.ui._editor
        else:
            return

    for d in list(mw.col.decks.decks.values()):
       if d['name'] == 'Standard':
          continue
       if deckList is not None and len(deckList) > 0 and d['name'] not in deckList:
           continue
       deckMap[d['name']] = d['id']
    set_deck_map(deckMap)
    dmap = {}
    for name, id in deckMap.items():
        dmap = addToDecklist(dmap, id, name)

    dmap = dict(sorted(dmap.items(), key=lambda item: item[0].lower()))
    def iterateMap(dmap, prefix, start=False):
        decks = index.selectedDecks if index is not None else []
        if start:
            html = "<ul class='deck-sub-list outer'>"
        else:
            html = "<ul class='deck-sub-list'>"
        for key, value in dmap.items():
            full = prefix + "::" + key if prefix else key
            html += "<li class='deck-list-item %s' data-id='%s' onclick='event.stopPropagation(); updateSelectedDecks(this);'><div class='list-item-inner'><b class='exp'>%s</b> %s <span class='check'>&#10004;</span></div>%s</li>" % ( "selected" if str(deckMap[full]) in decks or decks == ["-1"] else "", deckMap[full],  "[+]" if value else "", utility.text.trim_if_longer_than(key, 35), iterateMap(value, full, False))
        html += "</ul>"
        return html

    html = iterateMap(dmap, "", True)
    expanded_js = """$('#siac-switch-deck-btn').addClass("expanded");""" if expanded else ""

    cmd = """
    document.getElementById('deck-sel-info-lbl').style.display = 'block';
    document.getElementById('deckSelQuickWrapper').style.display = 'none';
    document.getElementById('deckSel').innerHTML = `%s`;
    $('#deckSelWrapper .exp').click(function(e) {
		e.stopPropagation();
        let icn = $(this);
        if (icn.text()) {
            if (icn.text() === '[+]')
                icn.text('[-]');
            else
                icn.text('[+]');
        }
        $(this).parent().parent().children('ul').toggle();
    });
    %s
    $("#siac-deck-sel-btn-wrapper").show();
    updateSelectedDecks();

    """ % (html, expanded_js)
    editor.web.eval(cmd)

def addToDecklist(dmap, id, name):
    names = [s for s in name.split("::") if s != ""]
    for c, d in enumerate(names):
        found = dmap
        for i in range(c):
            found = found.setdefault(names[i], {})
        if not d in found:
            found.update({d : {}})
    return dmap

@js
def show_notification(html):

    return """
        $('.siac-notification').remove();
        let target = $('#siac-reading-modal').is(':visible') ? "#reading-modal" : "#siac-right-side";
        $(target).append(`
            <div class='siac-notification'>
                %s
            </div> 
         `);

        window.setTimeout(function() {
            $('.siac-notification').fadeOut(5000);
            $('.siac-notification').remove();
         }, 5000);
    
    
    """ % html