/**
 * ###########################################
 *  PDF image cut-out / Page Snapshot
 * ###########################################
 */

// const { Highlighting } = require("./pdf_highlighting");

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
        var pdfC = document.getElementById("siac-pdf-canvas");
        cropSelection(pdfC, pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX, pdfImgSel.endY - pdfImgSel.startY, insertImage);
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
    }
}
/** Save whole page to image */
window.pageSnapshot = function() {
    var pdfC = document.getElementById("siac-pdf-canvas");
    cropSelection(pdfC, 0, 0, pdfC.offsetWidth, pdfC.offsetHeight, insertImage);
}
window.cropSelection = function(canvasSrc, offsetX, offsetY, width, height, callback) {
    let temp = document.createElement('canvas');
    let tctx = temp.getContext('2d');
    temp.width = width;
    temp.height = height;
    tctx.drawImage(canvasSrc, offsetX * window.devicePixelRatio, offsetY * window.devicePixelRatio, width * window.devicePixelRatio, height * window.devicePixelRatio, 0, 0, temp.width, temp.height);
    callback(temp.toDataURL());
}
window.insertImage = function(data) {
    pycmd("siac-add-image 1 " + data.replace("image/png", ""));
}
window.pdfImgMouseDown = function(event) {
    pdfImgSel.canvasDispl = document.getElementById("siac-pdf-canvas").offsetLeft;
    pdfImgSel.mouseIsDown = true;
    pdfImgSel.cvsOffLeft = $(pdfImgSel.canvas).offset().left;
    pdfImgSel.cvsOffTop = $(pdfImgSel.canvas).offset().top;
    pdfImgSel.startX = pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
    pdfImgSel.startY = pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
    drawSquare();
}
window.initImageSelection = function() {
    if ($('#text-layer').is(":hidden")) {
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
        return;
    }
    disableAreaHighlight();
    $('#text-layer').hide();
    pdfImgSel.canvas = document.getElementById("siac-pdf-canvas");
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
    pdfImgSel.canvas = document.getElementById("siac-pdf-canvas");
    var lCanvasOverlay = document.createElement("canvas");
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
    }
    return false;
}
window.pdfAreaHighlightMouseUp = function (event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.mouseIsDown = false;
        drawSquare();
        Highlighting.createAreaHighlight(pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX, pdfImgSel.endY - pdfImgSel.startY);
        clearImgSelectionCanvas();
    }
}