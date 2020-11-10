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


export const Highlighting = {

    /**
     * state
     */
    colorSelected: { id: 1, color: "red" },
    current: [],



    /**
     * Main entry point, called after keyup in text layer with ctrl pressed.
     */
    highlight: function () {
        let s = window.getSelection();
        let r = s.getRangeAt(0);
        $('#text-layer > span').css("height", "auto");
        let clientRects = r.getClientRects();
        if (clientRects.length > 100) {
            readerNotification("Selection too long to highlight.");
            return;
        }
        let rects = this._fuseOverlappingClientRects(clientRects);
        let rectCanvas = byId("text-layer").getBoundingClientRect();
        let offset = byId('text-layer').offsetLeft;
        //page group type [x,y,w,h]+ # text
        let cmd = pdf.page + " -1 " + this.colorSelected.id + " ";

        rects.forEach((r) => {
            let x = r.x - rectCanvas.x;
            let y = r.y - rectCanvas.y;
            let conv = pdf.displayedViewPort.convertToPdfPoint(x, y);

            cmd += conv[0] + " " + conv[1] + " ";
            conv = pdf.displayedViewPort.convertToPdfPoint(x + r.w, y + r.h);
            cmd += conv[0] + " " + conv[1] + " ";
            // text layer spans seem to be shifted to the top by some pixels, so add a small offset to the highlight div
            // this._createHighlightDiv(x + offset, y, r.w, r.h, this.colorSelected.id);

        });
        cmd += "# " + s.toString();
        s.removeAllRanges();
        pycmd("siac-hl-new " + cmd);
        $('#text-layer > span').css("height", "100px");
    },
    createAreaHighlight: function(x, y, w, h) {
        let t = this.colorSelected.id;
        if (t < 1 || (w < 2 && h < 2)) {return;}
        if (x + w > activeCanvas().offsetWidth) {
            return;
        }
        if (y + h > activeCanvas().offsetHeight) {
            return;
        }
        if (t >= 6) {
            t += 3;
            x -= 3;
            y -= 3;
        }
        let conv_xy = pdf.displayedViewPort.convertToPdfPoint(x, y);
        let conv_wh = pdf.displayedViewPort.convertToPdfPoint(x + w, y + h);
        let cmd = `siac-hl-new ${pdf.page} -1 ${t} ${conv_xy[0]} ${conv_xy[1]} ${conv_wh[0]} ${conv_wh[1]} # `;
        pycmd(cmd);
    },
    insertText: function (event) {
        let rectCanvas = byId("text-layer").getBoundingClientRect();
        let offset = byId('text-layer').offsetLeft;

        let x = event.clientX - rectCanvas.x;
        let y = event.clientY - rectCanvas.y;
        this._createHighlightDiv(x + offset, y, 100, 20, this.colorSelected.id, "");
        let cmd = pdf.page + " -1 0 ";
        let conv = pdf.displayedViewPort.convertToPdfPoint(x, y);
        cmd += conv[0] + " " + conv[1] + " ";
        conv = pdf.displayedViewPort.convertToPdfPoint(x + 100, y + 20);
        cmd += conv[0] + " " + conv[1] + " #";
        pycmd("siac-hl-new " + cmd);
    },

    displayFakeHighlight: function() {
        this._createHighlightDiv(0,0,50,50,1, -1);
    },

    displayHighlights: function () {
        this._removeAllHighlights();
        let canvas = activeCanvas();
        if (!canvas) { return; }
        let st = byId("siac-pdf-overflow").scrollTop;

        this.current.forEach((r) => {
            let x0 = r[0];
            let y0 = r[1];
            let x1 = r[2];
            let y1 = r[3];
            let t = r[4];
            let id = r[5];
            let text = r[6];
            let bounds = pdf.displayedViewPort.convertToViewportRectangle([x0, y0, x1, y1]);
            let x = Math.min(bounds[0], bounds[2]);
            x += canvas.offsetLeft;
            let y = Math.min(bounds[1], bounds[3]);
            let w = Math.abs(bounds[0] - bounds[2]);
            let h = Math.abs(bounds[1] - bounds[3]);
            this._createHighlightDiv(x, y, w, h, t, id, text);

        });
        byId("siac-pdf-overflow").scrollTop = st;
    },

    _removeAllHighlights: function () {
        let all = document.getElementsByClassName('siac-hl');
        while (all[0]) {
            all[0].parentNode.removeChild(all[0]);
        }
    },

    _colorById: function (t) {
        switch (t) {
            case 0: return "white";
            case 1: return "#e65100";
            case 2: return "#558b2f";
            case 3: return "#2196f3";
            case 4: return "#ffee58";
            case 5: return "#ab47bc";
            case 6: case 9: return "#e65100";
            case 7: case 10: return "#558b2f";
            case 8: case 11: return "#2196f3";
        }
    },


    /**
     *  getClientRects returns many overlapping rects for the text layer, so we try to fuse them together 
     */
    _fuseOverlappingClientRects: function (domRectList) {
        let fused = true;
        let x, y, w, h = 0;
        let clientRects = [];
        for (var n = 0; n < domRectList.length; n++) {
            clientRects.push({ x: domRectList[n].x, y: domRectList[n].y, w: domRectList[n].width, h: domRectList[n].height })
        }
        if (clientRects.length === 1) {
            return clientRects;
        }
        while (fused) {
            fused = false;
            let out = [];
            let i1 = 0;
            for (var i0 = 0; i0 < clientRects.length; i0++) {
                if (fused && i1 === i0) {
                    continue;
                }
                x = clientRects[i0].x;
                y = clientRects[i0].y;
                w = clientRects[i0].w;
                h = clientRects[i0].h;

                if (!fused) {
                    for (i1 = 0; i1 < clientRects.length; i1++) {
                        if (i1 === i0) { continue; }

                        // lots of room for improvement, some cases can probably get unified
                        if (clientRects[i1].x === x && clientRects[i1].y === y && clientRects[i1].w === w && clientRects[i1].h !== h) {
                            h = Math.max(clientRects[i1].h, h);
                            fused = true;
                        } else if (clientRects[i1].x === x && clientRects[i1].y === y && clientRects[i1].w !== w && clientRects[i1].h === h) {
                            w = Math.max(clientRects[i1].w, w);
                            fused = true;
                        } else if (clientRects[i1].x === x && clientRects[i1].y !== y && clientRects[i1].w === w && clientRects[i1].h === h) {
                            y = Math.min(y, clientRects[i1].y);
                            fused = true;
                        } else if (clientRects[i1].x !== x && clientRects[i1].y === y && clientRects[i1].w === w && clientRects[i1].h === h) {
                            x = Math.min(x, clientRects[i1].x);
                            fused = true;
                        }

                        else if (clientRects[i1].x !== x && clientRects[i1].y === y && clientRects[i1].w === w && clientRects[i1].h !== h && Math.abs(clientRects[i1].h - h) < 100) {
                            x = Math.min(x, clientRects[i1].x);
                            h = Math.max(clientRects[i1].h, h);
                            fused = true;
                        } else if (clientRects[i1].x !== x && clientRects[i1].y === y && clientRects[i1].h === h) {
                            if (clientRects[i1].x < x) {
                                w = x + w - clientRects[i1].x;
                                x = clientRects[i1].x;
                            } else {
                                w = (clientRects[i1].x + clientRects[i1].w) - x;
                            }
                            fused = true;
                        } else if (clientRects[i1].x === x && clientRects[i1].w === w) {
                            h = Math.max(clientRects[i1].h, h, Math.max(y + h, clientRects[i1].y + clientRects[i1].h) - Math.min(clientRects[i1].y, y));
                            y = Math.min(clientRects[i1].y, y);
                            fused = true;
                        } else if (clientRects[i1].y > y && clientRects[i1].y + clientRects[i1].h < y + h) {
                            w = Math.max(clientRects[i1].w, w, clientRects[i1].x + clientRects[i1].w - Math.min(clientRects[i1].x, x), x + w - Math.min(clientRects[i1].x, x));
                            x = Math.min(clientRects[i1].x, x);
                            fused = true;
                        }  else if (Math.abs(clientRects[i1].y - y) < h) {
                            w = Math.max(clientRects[i1].w, w, clientRects[i1].x + clientRects[i1].w - Math.min(clientRects[i1].x, x), x + w - Math.min(clientRects[i1].x, x));
                            y = Math.min(clientRects[i1].y, y);
                            h = clientRects[i1].h + Math.abs(clientRects[i1].y - y);
                            fused = true;
                        }
                        if (fused) {
                            if (i1 < i0) {
                                out.splice(i1, 1);
                            }
                            break;
                        }
                    }
                }
                // console.assert(x >= 0 && y >= 0 && w >= 0 && h >= 0, "neg value");
                if (out.indexOf({ x, y, w, h }) === -1) {
                    out.push({ x, y, w, h });
                }
            }
            if (fused && clientRects.length === out.length) {
                console.log("something went terribly wrong");
                return clientRects;
            }
            clientRects = Array.from(out);
        }
        return clientRects;
    },
    /**
     * Button at the side of the pdf pane clicked.
     * Switches selected highlighting tool.
     */
    onColorBtn: function (elem) {
        this.colorSelected = { id: Number($(elem).data("id")), color: $(elem).data("color") };
        $('.siac-pdf-color-btn,.siac-pdf-ul-btn').removeClass("active");
        $(elem).addClass("active");
        pycmd("siac-hl-clicked " + this.colorSelected.id + " " + this.colorSelected.color);
        if (this.colorSelected.id > 0) {
            readerNotification("CTRL + select to Highlight<br>CTRL + Shift + A to Area Highlight");
        } else {
            readerNotification("CTRL + click to insert text<br>CTRL + click again to remove");
        }
    },

    /**
     * Mouse up in text comment, should check if width has changed (element was resized by dragging), if yes,
     * update db entry. 
     */
    onTextMouseUp: function(event, el) {
        if (!el.dataset.id) {
            return;
        }
        if (el.offsetWidth != el.dataset.ow || el.clientHeight != el.dataset.oh) {
            el.dataset.ow = el.offsetWidth;
            el.dataset.oh = el.clientHeight;

            let rectCanvas = byId("text-layer").getBoundingClientRect();
            let x0 = el.offsetLeft - activeCanvas().offsetLeft;
            let y0 = el.offsetTop ;
            let x1 = x0 + el.offsetWidth - 6; 
            let y1 = y0 + el.clientHeight; 

            let conv = pdf.displayedViewPort.convertToPdfPoint(x0, y0);
            x0 = conv[0];
            y0 = conv[1];
            conv = pdf.displayedViewPort.convertToPdfPoint(x1, y1);
            x1 = conv[0];
            y1 = conv[1];

            pycmd(`siac-hl-text-update-coords ${el.dataset.id} ${x0} ${y0} ${x1-2} ${y1+2}`);
        }
    },

    /**
     * Text comment loses focus, so save changed content to db. 
     */
    onTextBlur: function(el) {
        if (!el.dataset.id) {
            return;
        }
        pycmd(`siac-hl-text-update-text ${el.dataset.id} ${pdf.page} ${$(el).val()}`);
    },

    onTextKeyup: function(el) {
        $(el).height(1); 
        $(el).height($(el).prop('scrollHeight') + 1);
        this.onTextMouseUp(null, el);
    },

    /**
     * Clicked on a highlight marker 
     */
    hlClick: function (event, el) {
        if (!el.dataset.id) {
            return;
        }
        if (event.ctrlKey || event.metaKey) {
            this.current = this.current.filter(c => c[5] != el.dataset.id);
            pycmd("siac-hl-del " + el.dataset.id);
            $(el).remove();
        }
    },
    /**
     *  create the actual div that will be the highlight and append it to the dom
     */
    _createHighlightDiv: function (x, y, w, h, t, id = -1, text = "") {

        let el;
        //regular highlight
        if (t > 0) {
            el = document.createElement("div");
            el.className = "siac-hl siac-hl-c";
            el.style.height = h + "px";
            el.style.width = w + "px";
            el.style.top = y + "px";
            el.style.left = x + "px";
            if (id !== -1) {
                el.dataset.id = id;
            }
            el.setAttribute("onclick", "Highlighting.hlClick(event, this);");
            if (t >= 6 && t < 9)
                el.style.borderBottom = "3px solid " + this._colorById(t);
            else if (t >= 9)
                el.style.border = "3px solid " + this._colorById(t);
            else
                el.style.background = this._colorById(t);
        }
        // text highlight 
        else {
            el = document.createElement("textarea");
            el.className = "siac-hl siac-text-hl";
            el.style.height = h + "px";
            el.style.width = w + "px";
            el.style.top = y + "px";
            el.style.left = x + "px";
            if (id !== -1) {
                el.dataset.id = id;
            }
            el.value = text;
            el.setAttribute("onclick", "Highlighting.hlClick(event, this);");
            el.style.background = this._colorById(t);
            el.setAttribute("onmouseup", "Highlighting.onTextMouseUp(event, this);");
            el.setAttribute("onblur", "Highlighting.onTextBlur(this);");
            el.setAttribute("onkeyup", "Highlighting.onTextKeyup(this);");
        }

        byId("siac-pdf-overflow").append(el);
        return el;
    }
};