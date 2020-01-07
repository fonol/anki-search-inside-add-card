import platform
import os
import json
import re
import datetime
import time
import sys
from aqt import mw

import utility.tags
import utility.text
import utility.misc

from ..tag_find import get_most_active_tags
from ..state import get_index, check_index, set_deck_map
from ..notes import get_note, _get_priority_list, get_all_tags, get_read_pages, get_pdf_marks, insert_pages_total, get_read_today_count
from .html import get_model_dialog_html, get_reading_modal_html, stylingModal, get_note_delete_confirm_modal_html, get_loader_html, get_queue_head_display, get_reading_modal_bottom_bar, get_notes_sidebar_html
from ..internals import js, requires_index_loaded

@js
def toggleAddon():
    return "toggleAddon();"


def getScriptPlatformSpecific(addToHeight, delayWhileTyping):
    """
        Returns the css and js used by the add-on in <style>/<script> tags. 
        Some placeholders in the scripts.js file and in the styles.css file are replaced 
        by config values.
    """
    #get path
    dir = utility.misc.get_web_folder_path()
    config = mw.addonManager.getConfig(__name__)
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
    script = script.replace("$del$", str(delayWhileTyping))

    try:
        deckSelectFontSize = config["styling"]["topBar"]["deckSelectFontSize"]
    except KeyError:
        deckSelectFontSize = 12
    try:
        noteFontSize = config["styling"]["general"]["noteFontSize"]
    except KeyError:
        noteFontSize = 12

    try:
        noteForegroundColor = config["styling"]["general"]["noteForegroundColor"]
    except KeyError:
        noteForegroundColor = "black"

    try:
        noteBackgroundColor = config["styling"]["general"]["noteBackgroundColor"]
    except KeyError:
        noteBackgroundColor = "white"

    try:
        noteBorderColor = config["styling"]["general"]["noteBorderColor"]
    except KeyError:
        noteBorderColor = "grey"
    try:
        noteHoverBorderColor = config["styling"]["general"]["noteHoverBorderColor"]
    except KeyError:
        noteHoverBorderColor = "#2496dc"
    try:
        tagBackgroundColor = config["styling"]["general"]["tagBackgroundColor"]
    except KeyError:
        tagBackgroundColor = "#f0506e"

    try:
        tagForegroundColor = config["styling"]["general"]["tagForegroundColor"]
    except KeyError:
        tagForegroundColor = "white"
    try:
        tagFontSize = config["styling"]["general"]["tagFontSize"]
    except KeyError:
        tagFontSize = 12
    try:
        deckSelectForegroundColor = config["styling"]["topBar"]["deckSelectForegroundColor"]
    except KeyError:
        deckSelectForegroundColor = "black"

    try:
        deckSelectBackgroundColor = config["styling"]["topBar"]["deckSelectBackgroundColor"]
    except KeyError:
        deckSelectBackgroundColor = "white"
    try:
        deckSelectHoverForegroundColor = config["styling"]["topBar"]["deckSelectHoverForegroundColor"]
    except KeyError:
        deckSelectHoverForegroundColor = "white"

    try:
        deckSelectHoverBackgroundColor = config["styling"]["topBar"]["deckSelectHoverBackgroundColor"]
    except KeyError:
        deckSelectHoverBackgroundColor = "#5f6468"

    try:
        deckSelectButtonForegroundColor = config["styling"]["topBar"]["deckSelectButtonForegroundColor"]
    except KeyError:
        deckSelectButtonForegroundColor = "grey"

    try:
        deckSelectButtonBackgroundColor = config["styling"]["topBar"]["deckSelectButtonBackgroundColor"]
    except KeyError:
        deckSelectButtonBackgroundColor = "white"

    try:
        deckSelectButtonBorderColor = config["styling"]["topBar"]["deckSelectButtonBorderColor"]
    except KeyError:
        deckSelectButtonBorderColor = "grey"
    try:
        deckSelectCheckmarkColor = config["styling"]["topBar"]["deckSelectCheckmarkColor"]
    except KeyError:
        deckSelectCheckmarkColor = "grey"

    try:
        modalBackgroundColor = config["styling"]["modal"]["modalBackgroundColor"]
    except KeyError:
        modalBackgroundColor = "white"

    try:
        modalForegroundColor = config["styling"]["modal"]["modalForegroundColor"]
    except KeyError:
        modalForegroundColor = "black"

    try:
        browserSearchButtonBorderColor = config["styling"]["bottomBar"]["browserSearchButtonBorderColor"]
    except KeyError:
        browserSearchButtonBorderColor = "#2496dc"

    try:
        browserSearchButtonBackgroundColor = config["styling"]["bottomBar"]["browserSearchButtonBackgroundColor"]
    except KeyError:
        browserSearchButtonBackgroundColor = "white"

    try:
        browserSearchButtonForegroundColor = config["styling"]["bottomBar"]["browserSearchButtonForegroundColor"]
    except KeyError:
        browserSearchButtonForegroundColor = "#2496dc"

    try:
        browserSearchInputBorderColor = config["styling"]["bottomBar"]["browserSearchInputBorderColor"]
    except KeyError:
        browserSearchInputBorderColor = "#2496dc"

    try:
        browserSearchInputBackgroundColor = config["styling"]["bottomBar"]["browserSearchInputBackgroundColor"]
    except KeyError:
        browserSearchInputBackgroundColor = "white"

    try:
        browserSearchInputForegroundColor = config["styling"]["bottomBar"]["browserSearchInputForegroundColor"]
    except KeyError:
        browserSearchInputForegroundColor = "#2496dc"

    try:
        infoButtonBorderColor = config["styling"]["general"]["buttonBorderColor"]
    except KeyError:
        infoButtonBorderColor = "#2496dc"

    try:
        infoButtonBackgroundColor = config["styling"]["general"]["buttonBackgroundColor"]
    except KeyError:
        infoButtonBackgroundColor = "white"

    try:
        infoButtonForegroundColor = config["styling"]["general"]["buttonForegroundColor"]
    except KeyError:
        infoButtonForegroundColor = "#2496dc"
    try:
        highlightBackgroundColor = config["styling"]["general"]["highlightBackgroundColor"]
    except KeyError:
        highlightBackgroundColor = "yellow"
    try:
        highlightForegroundColor = config["styling"]["general"]["highlightForegroundColor"]
    except KeyError:
        highlightForegroundColor = "black"
    try:
        rankingLabelBackgroundColor = config["styling"]["general"]["rankingLabelBackgroundColor"]
    except KeyError:
        rankingLabelBackgroundColor = "#2496dc"
    try:
        rankingLabelForegroundColor = config["styling"]["general"]["rankingLabelForegroundColor"]
    except KeyError:
        rankingLabelForegroundColor = "white"
    try:
        selectBackgroundColor = config["styling"]["bottomBar"]["selectBackgroundColor"]
    except KeyError:
        selectBackgroundColor = "white"
    try:
        selectForegroundColor = config["styling"]["bottomBar"]["selectForegroundColor"]
    except KeyError:
        selectForegroundColor = "black"


    try:
        stripedTableBackgroundColor = config["styling"]["modal"]["stripedTableBackgroundColor"]
    except KeyError:
        stripedTableBackgroundColor = "#f2f2f2"
    try:
        modalBorderColor = config["styling"]["modal"]["modalBorderColor"]
    except KeyError:
        modalBorderColor = "#2496dc"
    try:
        keywordColor = config["styling"]["general"]["keywordColor"]
    except KeyError:
        keywordColor = "#2496dc"
    try:
        fieldSeparatorColor = config["styling"]["general"]["fieldSeparatorColor"]
    except KeyError:
        fieldSeparatorColor = "#2496dc"
    try:
        windowColumnSeparatorColor = config["styling"]["general"]["windowColumnSeparatorColor"]
    except KeyError:
        windowColumnSeparatorColor = "#2496dc"


    try:
        timelineBoxBackgroundColor = config["styling"]["bottomBar"]["timelineBoxBackgroundColor"]
    except KeyError:
        timelineBoxBackgroundColor = "#595959"
    try:
        timelineBoxBorderColor = config["styling"]["bottomBar"]["timelineBoxBorderColor"]
    except KeyError:
        timelineBoxBorderColor = "#595959"
    try:
        imgMaxHeight = str(config["imageMaxHeight"]) + "px"
    except KeyError:
        imgMaxHeight = "300px"


    try:
        pdfTooltipMaxHeight = str(config["pdfTooltipMaxHeight"])
        pdfTooltipMaxWidth = str(config["pdfTooltipMaxWidth"])
    except KeyError:
        pdfTooltipMaxHeight = "300"
        pdfTooltipMaxWidth = "250"

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

    try:
        renderImmediately = str(config["renderImmediately"]).lower()
    except KeyError:
        renderImmediately = "false"
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
    if not index.highlighting:
        editor.web.eval("$('#highlightCb').prop('checked', false);")
    if not index.searchWhileTyping:
        editor.web.eval("$('#typingCb').prop('checked', false); setSearchOnTyping(false);")
    if not index.searchOnSelection:
        editor.web.eval("$('#selectionCb').prop('checked', false);")
    if not index.tagSearch:
        editor.web.eval("$('#tagCb').prop('checked', false);")
    if index.tagSelect:
        fillTagSelect(editor)
    if not index.topToggled:
        editor.web.eval("hideTop();")
    if index.output is not None and not index.output.uiVisible:
        editor.web.eval("$('#infoBox').addClass('addon-hidden')")
    if config["gridView"]:
        editor.web.eval('activateGridView();') 
    if index.searchbar_mode == "Browser":
        editor.web.eval("toggleSearchbarMode(document.getElementById('siac-search-inp-mode-lbl'));")
    if index.output is not None:
        #plot.js is already loaded if a note was just added, so this is a lazy solution for now
        index.output.plotjsLoaded = False
    if config["notes.sidebar.visible"]:
        display_notes_sidebar(editor)
        

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
        get_index().output.js(js)
    elif editor is not None and editor.web is not None:
        editor.web.eval(js)



def printStartingInfo(editor):
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

    if index is None or index.output is None:
        html += "<br/><b>Seems like something went wrong while building the index. Try to close the dialog and reopen it. If the problem persists, contact the addon author.</b>"
    editor.web.eval("document.getElementById('searchResults').innerHTML = `<div id='startInfo'>%s</div>`;" % html)


def display_model_dialog():
    if check_index():
        html = get_model_dialog_html()
        get_index().output.show_in_modal_subpage(html)

@js
def show_width_picker():
    html = """
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 25")'><b>25 - 75</b></div>
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 33")'><b>33 - 67</b></div>
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 40")'><b>40 - 60</b></div>
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 50")'><b>50 - 50</b></div>
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 60")'><b>60 - 40</b></div>
        <div class='w-100 siac-orange-hover' onclick='pycmd("siac-left-side-width 67")'><b>67 - 33</b></div>
    """

    modal = """
        <div class="siac-modal-small dark" contenteditable="false" style="text-align:center;">
            <b>Left Side - Right Side</b>
                <br><br>
            <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div>
                <br><br>
            <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Close</div>
        </div> 
    """ % html
    return "$('#siac-reading-modal-text').append(`%s`)" % modal

@requires_index_loaded
def display_note_reading_modal(note_id):
    index = get_index()
    note = get_note(note_id)

    html = get_reading_modal_html(note)
    index.output.show_in_large_modal(html)
    # if source is a pdf file path, try to display it
    if note[3] is not None and note[3].strip().lower().endswith(".pdf"):
        if utility.misc.file_exists(note[3]):
            _display_pdf(note[3].strip(), note_id)
        else:
            message = "Could not load the given PDF.<br>Are you sure the path is correct?"
            reading_modal_notification(message)

@js
def reload_note_reading_modal_bottom_bar(note_id):
    """
        Called after queue picker dialog has been closed without opening a new note.
    """
    note = get_note(note_id)
    html = get_reading_modal_bottom_bar(note)
    html = html.replace("`", "\\`")
    return "$('#siac-reading-modal-bottom-bar').replaceWith(`%s`); updatePdfDisplayedMarks();" % html

def _display_pdf(full_path, note_id):
    index = get_index()
    base64pdf = utility.misc.pdf_to_base64(full_path)
    blen = len(base64pdf)
    pages_read = get_read_pages(note_id)        
    pages_read_js = "" if len(pages_read) == 0 else ",".join([str(p) for p in pages_read])
    marks = get_pdf_marks(note_id)
    js_maps = utility.misc.marks_to_js_map(marks)
    marks_js = "pdfDisplayedMarks = %s; pdfDisplayedMarksTable = %s;" % (js_maps[0], js_maps[1]) 
    # pages read are ordered by date, so take last
    last_page_read = pages_read[-1] if len(pages_read) > 0 else 1

    init_code = """
        pdfLoading = true;
        var bstr = atob(b64);
        var n = bstr.length;
        var arr = new Uint8Array(n);
        while(n--){ 
            arr[n] = bstr.charCodeAt(n);
        }
        var file = new File([arr], "placeholder.pdf", {type : "application/pdf" });
        var fileReader = new FileReader();
        pagesRead = [%s];
        %s
        var loadFn = function(retry) {
            if (retry > 4) {
                $('#siac-loader-modal').remove();
                $('#siac-timer-popup').html(`<br><center>PDF.js could not be loaded from CDN.</center><br>`).show();
                pdfDisplayed = null;
                ungreyoutBottom();
                fileReader = null;
                pdfLoading = false;
                noteLoading = false;
                return;
            }
            if (typeof(pdfjsLib) === 'undefined') {
                window.setTimeout(() => { loadFn(retry + 1);}, 800);
                document.getElementById('siac-loader-text').innerHTML = `PDF.js was not loaded. Retrying (${retry+1} / 5)`;
                return;
            }
            if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.3.200/pdf.worker.min.js';
            }
            var canvas = document.getElementById("siac-pdf-canvas");
            var typedarray = new Uint8Array(fileReader.result);
            var loadingTask = pdfjsLib.getDocument(typedarray, {nativeImageDecoderSupport: 'display'});
            loadingTask.promise.catch(function(error) {
                    $('#siac-loader-modal').remove();
                    $('#siac-timer-popup').html(`<br><center>Could not load PDF - seems to be invalid.</center><br>`).show();
                    pdfDisplayed = null;
                    ungreyoutBottom();
                    fileReader = null;
                    pdfLoading = false;
                    noteLoading = false;
            });
            loadingTask.promise.then(function(pdf) {
                    pdfDisplayed = pdf;
                    pdfDisplayedCurrentPage = %s;
                    $('#siac-loader-modal').remove();
                    queueRenderPage(pdfDisplayedCurrentPage, true, true, true);
                    updatePdfProgressBar();
                    if (pagesRead.length === 0) { pycmd('siac-insert-pages-total %s ' + pdf.numPages); }
                    fileReader = null;
            });
        };
        fileReader.onload = (e) => { loadFn(0); };

        fileReader.readAsArrayBuffer(file);
        b64 = ""; arr = null; bstr = null; file = null;
    """ % (pages_read_js, marks_js, last_page_read, note_id)
    #send large files in multiple packets
    if blen > 10000000:
        index.output.editor.web.page().runJavaScript("var b64 = `%s`;" % base64pdf[0: 10000000])
        sent = 10000000
        while sent < blen:
            index.output.editor.web.page().runJavaScript("b64 += `%s`;" % base64pdf[sent: min(blen,sent + 10000000)])
            sent += min(blen - sent, 10000000)
        index.output.editor.web.page().runJavaScript(init_code)
    else:
        index.output.editor.web.page().runJavaScript("""
            var b64 = `%s`;
                %s
        """ % (base64pdf, init_code))


@js
def showStylingModal(editor):
    config = mw.addonManager.getConfig(__name__)
    html = stylingModal(config)
    index = get_index()
    index.output.showInModal(html)
    return "$('.modal-close').on('click', function() {pycmd(`writeConfig`) })"

@js
def show_img_field_picker_modal(img_src):
    """
        Called after an image has been selected from a PDF, should display all fields that are currently in the editor,
        let the user pick one, and on picking, insert the img into the field.
    """
    index = get_index()
    modal = """ <div class="siac-modal-small dark" style="text-align:center;"><b>Append to:</b><br><br><div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br><div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove(); pycmd('siac-remove-snap-image %s')">Cancel</div></div> """
    flds = ""
    for i, f in enumerate(index.output.editor.note.model()['flds']):
        fld_update_js = "pycmd(`blur:%s:${currentNoteId}:${$(`.field:eq(%s)`).html()}`);" % (i,i)
        flds += """<span class="siac-field-picker-opt" onclick="$(`.field`).get(%s).innerHTML += `<img src='%s'/>`; $(this.parentNode.parentNode).remove(); %s">%s</span><br>""" % (i, img_src, fld_update_js, f["name"])
    modal = modal % (flds, img_src)
    return "$('#siac-reading-modal-text').append('%s');" % modal.replace("'", "\\'")

@js
def show_cloze_field_picker_modal(cloze_text):
    """
       Shows a modal that lists all fields of the current note.
       When a field is selected, the cloze text is appended to that field.
    """
    index = get_index()
    cloze_text = cloze_text.replace("`", "").replace("\n", "")
    modal = """ <div class="siac-modal-small dark" style="text-align:center;">
                    <b>Append to:</b><br><br>
                    <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden;">%s</div><br><br>
                    <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                </div> """
    flds = ""
    for i, f in enumerate(index.output.editor.note.model()['flds']):
        flds += """<span class="siac-field-picker-opt" onclick="appendToField({0}, `{1}`);  $(this.parentNode.parentNode).remove();">{2}</span><br>""".format(i, cloze_text, f["name"])
    modal = modal % (flds)
    return "$('#siac-pdf-tooltip').hide(); $('#siac-reading-modal-text').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

@js
def show_iframe_overlay(url=None):
    js = """
        if (pdfDisplayed) {
            document.getElementById('siac-pdf-top').style.display = "none";
        } else {
            document.getElementById('siac-text-top').style.display = "none";
        }
        document.getElementById('siac-iframe').style.display = "block";
        document.getElementById('siac-close-iframe-btn').style.display = "block";
        iframeIsDisplayed = true;
    """
    if url is not None:
        js += """
            document.getElementById('siac-iframe').src = `%s`;
        """ % url
    return js

@js
def hide_iframe_overlay():
    js = """
        document.getElementById('siac-iframe').src = "";
        document.getElementById('siac-iframe').style.display = "none";
        document.getElementById('siac-close-iframe-btn').style.display = "none";
        if (pdfDisplayed) {
            document.getElementById('siac-pdf-top').style.display = "block";
        } else {
            document.getElementById('siac-text-top').style.display = "block";
        }
        iframeIsDisplayed = false;
    """
    return js

@js
def show_web_search_tooltip(inp):
    inp = utility.text.remove_special_chars(inp)
    inp = inp.strip()
    if len(inp) == 0:
        return
    search_sources = ""
    config = mw.addonManager.getConfig(__name__)
    urls = config["searchUrls"]
    if urls is not None and len(urls) > 0:
        for url in urls:
            if "[QUERY]" in url:
                name = os.path.dirname(url)
                search_sources += """<div class="siac-url-ch" onclick='pycmd("siac-url-srch $$$" + document.getElementById("siac-tt-ws-inp").value + "$$$%s"); $(this.parentNode.parentNode).remove();'>%s</div>""" % (url, name)

    modal = """ <div class="siac-modal-small dark" style="text-align:center;">
                    <input style="width: 100%%; border-radius: 3px; padding-left: 4px; box-sizing: border-box; background: #272828; color: white; border-color: white;" id="siac-tt-ws-inp" value="%s"></input> 
                    <br/>
                    <div style="max-height: 200px; overflow-y: auto; overflow-x: hidden; cursor: pointer; margin-top: 15px;">%s</div><br><br>
                    <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Cancel</div>
                </div> """% (inp, search_sources)
    
    js = """
    $('#siac-iframe-btn').removeClass('expanded'); 
    $('#siac-pdf-tooltip').hide(); 
    $('#siac-reading-modal-text').append('%s');
    """ % modal.replace("\n", "").replace("'", "\\'")
    return js

@js
def update_reading_bottom_bar(nid):
    queue = _get_priority_list()
    pos_lbl = ""
    if queue is not None and len(queue) > 0:
        try:
            pos = next(i for i,v in enumerate(queue) if v[0] == nid)
            pos_lbl = "Position: %s / %s" % (pos + 1, len(queue))
            pos_lbl_btn = "<b>%s</b> / <b>%s</b>" % (pos + 1, len(queue))
        except:
            pos_lbl = "Not in Queue"
            pos_lbl_btn = "<b>Not in Queue</b>"

    else:
        pos_lbl = "Not in Queue"
        pos_lbl_btn = "<b>Not in Queue</b>"

    qd = get_queue_head_display(nid, queue)
    return """
        document.getElementById('siac-queue-lbl').innerHTML = '%s';
        $('#siac-queue-lbl').fadeIn('slow');
        $('.siac-queue-sched-btn:first').html('%s');
        $('#siac-queue-readings-list').replaceWith(`%s`);
        """ % (pos_lbl, pos_lbl_btn, qd)

@js
def display_cloze_modal(editor, selection, extracted):
    s_html = "<table style='margin-top: 5px; font-size: 15px;'>"
    sentences = [s for s in extracted if len(s) < 300 and len(s.strip()) > 0]
    if len(sentences) == 0:
        for s in extracted:
            if len(s) >= 300:
                f = utility.text.try_find_sentence(s, selection)
                if f is not None and len(f) < 300:
                    sentences.append(f)

    if len(sentences) > 0 and sentences != [""]:
        selection = re.sub("  +", " ", selection).strip()
        for sentence in sentences:
            sentence = re.sub("  +", " ", sentence).strip()
            sentence = sentence.replace(selection, " <span style='color: lightblue;'>{{c1::%s}}</span> " % selection)

            # needs cleaning

            sentence = sentence.replace("  ", " ").replace("</span> ,", "</span>,")
            sentence = re.sub(" ([\"“”\\[(]) <span", " \\1<span", sentence)
            sentence = re.sub("</span> ([\"”\\]):])", "</span>\\1", sentence)
            sentence = re.sub("</span> -([^ \\d])", "</span>-\\1", sentence)
            sentence = re.sub("(\\S)- <span ", "\\1-<span ", sentence)
            sentence = re.sub(r"([^\\d ])- ([^\d])", r"\1\2", sentence)
            sentence = re.sub(" [\"“”], [\"“”] ?", "\", \"", sentence)
            sentence = re.sub(" [\"“”], ", "\", ", sentence)
            sentence = re.sub(": [\"“”] ", ": \"", sentence)
            sentence = sentence.replace("[ ", "[")
            sentence = sentence.replace(" ]", "]")
            sentence = re.sub(" ([,;:.]) ", r"\1 ", sentence)
            sentence = re.sub(r"\( (.) \)", r"(\1)", sentence)
            sentence = re.sub(" ([?!.])$", r"\1", sentence)
            sentence = re.sub("^[:.?!,;)] ", "", sentence)
            sentence = re.sub("^\\d+ ?[:\\-.,;] ([A-ZÖÄÜ])", r"\1", sentence)

            sentence = re.sub(" ([\"“”])([?!.])$", r"\1\2", sentence)
            
           
            
            s_html += "<tr class='siac-cl-row'><td><div contenteditable style='color: darkorange;'>%s</div></td><td><input type='checkbox' checked/></td></tr>" % (sentence.replace("`", "&#96;"))
        s_html += "</table>"
        btn_html = """document.getElementById('siac-pdf-tooltip-bottom').innerHTML = `
                            <div style='margin-top: 8px;'>
                              <div class='siac-btn siac-btn-dark' onclick='pycmd("siac-fld-cloze " +$(".siac-cl-row div").first().text());' style='margin-right: 15px;'>Send to Field</div>
                              <div class='siac-btn siac-btn-dark' onclick='generateClozes();'>Generate</div>
                            </div>
                   `;"""

    else:
        s_html = "<br><center>Sorry, could not extract any sentences.</center>" 
        btn_html = ""
    
    return """
            document.getElementById('siac-pdf-tooltip-results-area').innerHTML = `%s`;
            document.getElementById('siac-pdf-tooltip-top').innerHTML = `Found <b>%s</b> sentence(s) around selection: <br/><span style='color: lightgrey;'>(Click inside to edit, <i>Ctrl+Shift+C</i> to add new Clozes)</span>`;
            document.getElementById('siac-pdf-tooltip-searchbar').style.display = "none";
            %s
            """ % (s_html, len(sentences), btn_html)

@js
def reading_modal_notification(html):
    modal = """ <div class="siac-modal-small dark" contenteditable="false" style="text-align:center; color: lightgrey;">
                        %s
                        <br/> <br/>
                        <div class="siac-btn siac-btn-dark" onclick="$(this.parentNode).remove();">Ok</div>
                    </div> """ % html
    return "$('#siac-pdf-tooltip').hide();$('.siac-modal-small').remove(); $('#siac-reading-modal-text').append('%s');" % modal.replace("\n", "").replace("'", "\\'")

@js
def show_timer_elapsed_popup(nid):
    """
        Shows the little popup that is displayed when the timer in the reading modal finished.
    """
    read_today_count = get_read_today_count()
    added_today_count = utility.misc.count_cards_added_today()
    html = """
    <div style='margin: 0 0 10px 0;'>
        <div style='text-align: center; vertical-align: middle; line-height: 50px; font-weight: bold; font-size: 40px; color: #2496dc;'>
            &#10711;
        </div>
        <div style='text-align: center; vertical-align: middle; line-height: 50px; font-weight: bold; font-size: 20px;'>
            Time is up!
        </div>
    </div>
    <div style='margin: 10px 0 25px 0; text-align: center; color: lightgrey;'>
        Read <b>%s</b> pages today.<br>
        Added <b>%s</b> cards today.
    </div>
    <div style='text-align: center;'>
        <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(5);'>&nbsp;Start 5m&nbsp;</div>
        <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none";'>&nbsp;&nbsp;Ok&nbsp;&nbsp;</div>
        <div class='siac-btn siac-btn-dark' style='margin: 0 5px 0 5px;' onclick='this.parentNode.parentNode.style.display="none"; startTimer(15);'>&nbsp;Start 15m&nbsp;</div>
    </div>
    """ % (read_today_count, added_today_count)
    return "$('#siac-timer-popup').html(`%s`); $('#siac-timer-popup').show();" % html

@js
def display_note_del_confirm_modal(editor, nid):
    html = get_note_delete_confirm_modal_html(nid)
    return "$('#greyout').show();$('#searchResults').append(`%s`);" % html

@js
def jump_to_last_read_page(editor, nid):
    return """
        if (pagesRead && pagesRead.length) {
            pdfDisplayedCurrentPage = Math.max(...pagesRead);
            rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
        }
    """
@js
def jump_to_first_unread_page(editor, nid):
    return """
        if (pdfDisplayed) {
            for (var i = 1; i < pdfDisplayed.numPages + 1; i++) {
               if (!pagesRead || pagesRead.indexOf(i) === -1) {
                   pdfDisplayedCurrentPage = i;
                   rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
                   break;
               } 
            }
        }
    """

@js
def display_notes_sidebar(editor):
    html = get_notes_sidebar_html()
    return """
    if (!document.getElementById('siac-notes-sidebar')) {
        document.getElementById('resultsWrapper').style.paddingLeft = "265px"; 
        document.getElementById('resultsWrapper').innerHTML += `%s`; 
        $('#siac-notes-sidebar .exp').click(function(e) {
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
    }
    """ % html

@js
def reload_note_sidebar():
    html = get_notes_sidebar_html()
    return """
        if (document.getElementById('siac-notes-sidebar')) {
            $('#siac-notes-sidebar').remove();
            document.getElementById('resultsWrapper').style.paddingLeft = "265px"; 
            document.getElementById('resultsWrapper').innerHTML += `%s`; 
            $('#siac-notes-sidebar .exp').click(function(e) {
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
        }
    """ % html
    
   

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
        get_index().output.js(cmd)

def fillDeckSelect(editor = None, expanded= False):
    """
    Fill the selection with user's decks
    """

    deckMap = dict()
    config = mw.addonManager.getConfig(__name__)
    deckList = config['decks']
    index = get_index()
    if editor is None:
        if index is not None and index.output is not None and index.output.editor is not None:
            editor = index.output.editor
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
def show_loader(target_div_id, text):
    """
    Renders a small loading modal (absolute positioned) inside the given div.
    Does not deal with hiding the modal.
    """

    html = get_loader_html(text)
    return "$('#%s').append(`%s`);" % (target_div_id, html)

@js
def show_notification(editor, html):

    return """
        $('.siac-notification').remove();
        $('#infoBox').append(`
        <div class='siac-notification'>
            %s
        </div> 
         `);

        window.setTimeout(function() {
            $('.siac-notification').fadeOut(5000);
            $('.siac-notification').remove();
         }, 5000);
    
    
    """ % html