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
// Functions access fields.
//

window.SIAC.Fields = {

    _fields: [],

    enableSearchOnTypingEventListener: function() {
        if (!this._fields || this._fields.length === 0) {
            this.cacheFields();
        }
        for (let f of this._fields) {
            f.removeEventListener('keydown', fieldKeypress, false);
            f.addEventListener('keydown', fieldKeypress, false);
        }
    },
    disableSearchOnTypingEventListener: function() {
        if (!this._fields || this._fields.length === 0) {
            this.cacheFields();
        }
        for (let f of this._fields) {
            f.removeEventListener('keydown', fieldKeypress, false);
        }
    },
    setSelectionMouseUpEventListener: function() {
        $('.field').attr('onmouseup', 'getSelectionText()');
    },
    getFocusedFieldText: function() {
        if (window.getCurrentField) {
            return window.getCurrentField().shadowRoot.querySelector('anki-editable').innerText;
        }
        let f = $('.field:focus').first();
        if (!f.length) {
            return null;
        }
        return f.text();
    },
    saveField: function(ix) {
        // $(this._fields[ix]).trigger('blur');
        pycmd(`blur:${ix}:${this._noteId()}:${this.getFieldHtml(ix)}`);
    },
    getFieldHtml: function(ix) {
        if (ix < this._fields.length) {
            return this._fields[ix].innerHTML;
        }
        return null;
    },
    setFieldHtml: function(ix, html) {
        if (ix < this._fields.length) {
            this._fields[ix].innerHTML = html;
        }
        this.saveField(ix);
    },
    appendSelectionToFieldHtml: function(ix) {
        let sel = selectionCleaned();
        if (sel && sel.length > 0) {
            this.appendToFieldHtml(ix, sel);
        }

    },
    appendToFieldHtml: function(ix, html) {
        if (ix < this._fields.length) {
            if (!this._fields[ix].innerHTML || this._fields[ix].innerHTML.trim() === '' || /^(?:<div><\/div>|<br\/?>)$/.test(this._fields[ix].innerHTML)) {
                this._fields[ix].innerHTML = html;
                if (this._fields[ix].innerHTML.startsWith('<br>')) {
                    this._fields[ix].innerHTML = this._fields[ix].innerHTML.substring(4);
                }
            } else {
                this._fields[ix].innerHTML += '<br>' + html;
            }
        }
        this.saveField(ix);
    },
    getAllFieldsText: function() {
        let html = '';
        for (var i = 0; i < this._fields.length; i++) {
            html += this._fields[i].innerText+"\u001f";
        }
        return html;
    },
    cacheFields: function() {
        this._fields = [];
        if (!$('#fields [contenteditable]').length) {
            // 2.1.41+
            let fields = document.querySelectorAll('.field');
            for (let f of fields) {
                this._fields.push(f.shadowRoot.querySelector('anki-editable'));
            }
        } else {
            // - 2.1.40
            this._fields = document.querySelectorAll('.field');
        }
    },
    count: function() {
        if (!this._fields || this._fields.length === 0) {
            this.cacheFields();
        }
        return this._fields.length;
    },
    empty: function() {
        for (var i = 0; i < this._fields.length; i++) {
            if (this._fields[i].innerText && this._fields[i].innerText.length > 0) {
                return false;
            }
        }
        return true;
    },
    _noteId: function() {
        // 2.1.41+
        if (typeof(window.getNoteId) !== 'undefined') {
            return getNoteId();
        }
        // - 2.1.40
        return currentNoteId;
    },

    displaySelectionMenu: function() {
        this.hideSelectionMenu();
        let fnames = document.querySelectorAll('.fname');
        for (var i = 0; i < fnames.length; i++) {
            let div = document.createElement("div");
            div.classList.add('siac-fld-sel-menu');
            let sc_icon = i < 9 ? `<b title="CTRL/CMD + ${i+1}: Send to this field">${i+1}</b>` : '';
            div.innerHTML = `
                <i class='fa fa-reply-all' onmousedown='SIAC.Fields.appendSelectionToFieldHtml(${i})'></i>
                <i class='fa fa-picture-o ml-5' onmousedown='event.preventDefault(); selectionSnapshot(${i}); return false;'></i>
                ${sc_icon} 
                `;
            if (typeof getEditorField !== "undefined") {
                getEditorField(i).labelContainer.appendChild(div);
            } else {
                fnames[i].appendChild(div);
            }

        }


    },
    hideSelectionMenu: function() {
        let fmenus = document.querySelectorAll('.siac-fld-sel-menu');
        for (var i = 0; i < fmenus.length; i++) {
            fmenus[i].parentNode.removeChild(fmenus[i]);
        }
    }
}


SIAC.Fields.cacheFields();