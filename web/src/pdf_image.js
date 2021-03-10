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


/**
 * ###########################################
 *  PDF image cut-out / Page Snapshot
 * ###########################################
 */


window.pdfImgSel = {
    canvas: null,
    context: null,
    startX: null,
    endX: null,
    startY: null,
    endY: null,
    cvsOffLeft: null,
    cvsOffTop: null,
    mouseIsDown: false,
    canvasDispl: null
};

window.pdfImgMouseUp = function (event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.mouseIsDown = false;
        drawSquare();
        cropSelection(activeCanvas(), pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX, pdfImgSel.endY - pdfImgSel.startY, insertImage);
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
    }
}
/** Save whole page to image */
window.pageSnapshot = function(fld_ix) {
    // Function can be called from Qt-controlled shortcut,
    // so it might be that there is no PDF opened when called.
    if (!pdf.instance) {
        return;
    }
    let pdfC = activeCanvas();
    cropSelection(pdfC, 0, 0, pdfC.offsetWidth, pdfC.offsetHeight, function(data) { insertImage(data, fld_ix); });
}


window.extractPages = function() {
    // Function can be called from Qt-controlled shortcut,
    // so it might be that there is no PDF opened when called.
    if (!pdf.instance) {
        return;
    }
    pycmd("siac-create-pdf-extract " + pdf.page + " " + pdf.instance.numPages); event.stopPropagation();
}

/**
 * Make a picture of the area around the current selection and send it to the given field. 
 */
window.selectionSnapshot = function(fld_ix) {
    let r = SIAC.Helpers.getSelectionCoords();
    if (r) {
        let sel = getSelection();
        if (sel && sel.rangeCount > 0) {
            sel.getRangeAt(0).collapse();
        }
        if (byId('siac-pdf-tooltip')) {
            byId('siac-pdf-tooltip').style.display = 'none';
        }
        setTimeout(function() {
            pycmd(`siac-screen-capture ${fld_ix} ${Math.max(0, Math.trunc(r.top - 10))} ${Math.max(0, Math.trunc(r.left - 10))} ${Math.min(Math.trunc(r.width + 20), screen.width)} ${Math.min(screen.height, Math.trunc(r.height +20))}`); 
        }, 50);
    }
}
window.cropSelection = function(canvasSrc, offsetX, offsetY, width, height, callback) {
    if (width < 2 || height < 2) {
        return;
    }
    let temp = document.createElement('canvas');
    let tctx = temp.getContext('2d');
    temp.width = width;
    temp.height = height;
    tctx.drawImage(canvasSrc, offsetX * window.devicePixelRatio, offsetY * window.devicePixelRatio, width * window.devicePixelRatio, height * window.devicePixelRatio, 0, 0, temp.width, temp.height);
    callback(temp.toDataURL());
}
window.insertImage = function(data, fld_ix) {
    if (fld_ix == null) {
        pycmd("siac-add-image 1 " + data.replace("image/png", ""));
    } else {
        pycmd("siac-add-image-to-fld " + fld_ix + " " + data.replace("image/png", ""));
    }
}
window.pdfImgMouseDown = function(event) {
    pdfImgSel.canvasDispl = activeCanvas().offsetLeft;
    pdfImgSel.mouseIsDown = true;
    pdfImgSel.cvsOffLeft = $(pdfImgSel.canvas).offset().left;
    pdfImgSel.cvsOffTop = $(pdfImgSel.canvas).offset().top;
    pdfImgSel.startX = pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
    pdfImgSel.startY = pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
    drawSquare();
}
window.initImageSelection = function() {

    // Function can be called from Qt-controlled shortcut,
    // so it might be that there is no PDF opened when called.
    if (!pdf.instance) {
        return;
    }
    if ($('#text-layer').is(":hidden")) {
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
        return;
    }
    disableAreaHighlight();
    $('#text-layer').hide();
    pdfImgSel.canvas = activeCanvas();
    var lCanvasOverlay = document.createElement("canvas");
    pdfImgSel.canvas.parentNode.insertBefore(lCanvasOverlay, pdfImgSel.canvas.nextSibling);
    $(lCanvasOverlay).css({ "width": (pdfImgSel.canvas.width / window.devicePixelRatio) + "px", "height": (pdfImgSel.canvas.height / window.devicePixelRatio) + "px", "top": "0", "left": document.getElementById('text-layer').style.left, "position": "absolute", "z-index": 999999, "opacity": 0.3, "cursor": "crosshair" });
    lCanvasOverlay.setAttribute('width', pdfImgSel.canvas.width);
    lCanvasOverlay.setAttribute('height', pdfImgSel.canvas.height);
    pdfImgSel.context = lCanvasOverlay.getContext("2d");
    lCanvasOverlay.addEventListener("mousedown", function (e) { pdfImgMouseDown(e); }, false);
    lCanvasOverlay.addEventListener("mouseup", function (e) { pdfImgMouseUp(e); }, false);
    lCanvasOverlay.addEventListener("mousemove", function (e) { pdfImgMouseXY(e); }, false);
    pdfImgSel.canvas = lCanvasOverlay;
}
window.pdfImgMouseXY = function(event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
        pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
        drawSquare();
    }
}
window.drawSquare = function() {
    pdfImgSel.context.clearRect(0, 0, pdfImgSel.context.canvas.width, pdfImgSel.context.canvas.height);
    pdfImgSel.context.fillRect(pdfImgSel.startX * window.devicePixelRatio, pdfImgSel.startY * window.devicePixelRatio, Math.abs(pdfImgSel.startX - pdfImgSel.endX) * window.devicePixelRatio, Math.abs(pdfImgSel.startY - pdfImgSel.endY) * window.devicePixelRatio);
    pdfImgSel.context.fillStyle = "yellow";
    pdfImgSel.context.fill();
}
window.clearImgSelectionCanvas = function() {
    if (!pdfImgSel.canvas) {return;}
    let ctx = pdfImgSel.canvas.getContext("2d");
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.initAreaHighlight = function() {

    // remove any possibly already existing temporary canvases
    let existing = document.getElementsByClassName('area_highlight_cv');
    while(existing[0]) {
        existing[0].parentNode.removeChild(existing[0]);
    }

    pdfImgSel.canvas = activeCanvas();
    var lCanvasOverlay = document.createElement("canvas");
    lCanvasOverlay.classList.add("area_highlight_cv");
    lCanvasOverlay.oncontextmenu = disableAreaHighlight;
    pdfImgSel.canvas.parentNode.insertBefore(lCanvasOverlay, pdfImgSel.canvas.nextSibling);
    $(lCanvasOverlay).css({ "width": (pdfImgSel.canvas.width / window.devicePixelRatio) + "px", "height": (pdfImgSel.canvas.height / window.devicePixelRatio) + "px", "top": "0", "left": document.getElementById('text-layer').style.left, "position": "absolute", "z-index": 999999, "opacity": 0.3, "cursor": "crosshair" });
    lCanvasOverlay.setAttribute('width', pdfImgSel.canvas.width);
    lCanvasOverlay.setAttribute('height', pdfImgSel.canvas.height);
    pdfImgSel.context = lCanvasOverlay.getContext("2d");
    lCanvasOverlay.addEventListener("mousedown", function (e) { pdfImgMouseDown(e); }, false);
    lCanvasOverlay.addEventListener("mouseup", function (e) { pdfAreaHighlightMouseUp(e); }, false);
    lCanvasOverlay.addEventListener("mousemove", function (e) { pdfImgMouseXY(e); }, false);
    pdfImgSel.canvas = lCanvasOverlay;
}
window.disableAreaHighlight = function() {
    if (pdfImgSel.canvas) {
        $(pdfImgSel.canvas).remove();
        pdfImgSel.canvas = null;
    }
    return false;
}
window.pdfAreaHighlightMouseUp = function (event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.mouseIsDown = false;
        drawSquare();
        SIAC.Highlighting.createAreaHighlight(pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX, pdfImgSel.endY - pdfImgSel.startY);
        clearImgSelectionCanvas();
    }
}
