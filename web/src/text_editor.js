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

window.tryExtractTextFromTextNote = function () {
    saveTextNote($('#siac-reading-modal-top-bar').data('nid'));
    pycmd("siac-try-copy-text-note");
}

window.saveTextNote = function (nid) {
    let html = "";
    try {
        html = textEditor.value();
    } catch (e) {
        pycmd("siac-notification Could not save text note for some reason.");
        return;
    }
    readerNotification("&nbsp;<i class='fa fa-save'></i>&nbsp; Note saved.&nbsp;");
    pycmd("siac-update-note-text " + nid + " " + html);
}

window.editorMDInit = function () {
    textEditor = new SimpleMDE({
        element: byId("siac-text-top").children[0],
        indentWithTabs: true,
        autoDownloadFontAwesome: false,
        autosave: { enabled: false },
        placeholder: "",
        status: false,
        tagSize: 4,
        toolbar: ["bold", "italic", "heading", "code", "quote", "unordered-list", "ordered-list", "horizontal-rule", "link"]
    });
}