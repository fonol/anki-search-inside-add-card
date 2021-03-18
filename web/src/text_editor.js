// anki-search-inside-add-card
// Copyright (C) 2019 - 2020 Tom Z.

// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

//
// Functions for the text editor (currently SimpleMDE) in the reading modal.
//

SIAC.MD = new function () {

    var _mdSidebarEditors = {};

    this.tryExtractTextFromTextNote = function () {
        saveTextNote($('#siac-reading-modal-top-bar').data('nid'));
        pycmd("siac-try-copy-text-note");
    };

    this.saveTextNote = function (nid) {
        let html = "";
        try {
            html = textEditor.value();
        } catch (e) {
            pycmd("siac-notification Could not save text note for some reason.");
            return;
        }
        readerNotification("&nbsp;<i class='fa fa-save'></i>&nbsp; Note saved.&nbsp;");
        pycmd("siac-update-note-text " + nid + " " + html);
    };

    this.editorMDInit = function (elem) {
        textEditor = new SimpleMDE({
            element: elem,
            indentWithTabs: true,
            autoDownloadFontAwesome: false,
            autosave: { enabled: false },
            placeholder: "",
            status: false,
            tagSize: 4,
            toolbar: ["bold", "italic", "heading", "|", "code", "quote", "unordered-list", "ordered-list", "horizontal-rule", "|", "image", "link", "|", "preview"]
        });
    };
    this.mdSidebarEdit = function (mdFilePath, elem) {
    
        _mdSidebarEditors[mdFilePath] = new SimpleMDE({
            element: elem,
            indentWithTabs: true,
            autoDownloadFontAwesome: false,
            autosave: { enabled: false },
            placeholder: "",
            status: false,
            tagSize: 4,
            toolbar: ["bold", "italic", "heading", "|", "code", "quote", "unordered-list", "ordered-list", "horizontal-rule", "|", "image", "link", "|", "preview"]
        });
        _mdSidebarEditors[mdFilePath].codemirror.on("blur", function(){

            let fpathB64 =  window.SIAC.Helpers.b64EncodeUnicode(mdFilePath);
            let content = _mdSidebarEditors[mdFilePath].value();
            let fcontentB64 =  window.SIAC.Helpers.b64EncodeUnicode(content);
            window.pycmd("siac-update-md-file " + fpathB64 + " " + fcontentB64);
        });
    };
    this.mdSidebarDestroy = function(mdFilePath) {
        if (!(mdFilePath in _mdSidebarEditors)) {
            return;
        }
        let lMDEdit = _mdSidebarEditors[mdFilePath];
        lMDEdit.toTextArea();
        lMDEdit = null;
        delete _mdSidebarEditors[mdFilePath];

    };

   
}

/**
 *  WIP
 *  executed after keyup in the text editor pane
 */
window.textEditorKeyup = function () {
    if (pdf.tooltip.enabled && windowHasSelection()) {
        let s = window.getSelection();
        let r = s.getRangeAt(0);
        let text = s.toString();
        if (text.trim().length === 0 || text.length > 500) { return; }
        let nodesInSel = nodesInSelection(r);
        let sentences = getSentencesAroundSelection(r, nodesInSel, text);
        if (nodesInSel.length > 1) {
            text = joinTextLayerNodeTexts(nodesInSel, text);
        }
        let rect = r.getBoundingClientRect();
        let prect = byId("siac-reading-modal").getBoundingClientRect();
        byId('siac-pdf-tooltip-results-area').innerHTML = '<center>Searching...</center>';
        let left = rect.left - prect.left;
        if (prect.width - left < 250) {
            left -= 200;
        }
        let top = rect.top - prect.top + rect.height;
        if (top < 0) { return; }
        $('#siac-pdf-tooltip').css({ 'top': top + "px", 'left': left + "px" }).show();
        pycmd("siac-pdf-selection " + text);
        $('#siac-pdf-tooltip').data({ "sentences": sentences, "selection": text, "top": top });
    }

}
