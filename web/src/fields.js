if (typeof(window.SIAC) === 'undefined') {
    window.SIAC = {};
}

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
    },
    appendToFieldHtml: function(ix, html) {
        if (ix < this._fields.length) {
            if (!this._fields[ix].innerText || this._fields[ix].innerText.trim() === '') {
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
    }
}


SIAC.Fields.cacheFields();