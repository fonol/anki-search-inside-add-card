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
// Functions to change the colors of the rendered PDF.
//


window.setPDFColorMode = function (mode) {
    $('#siac-pdf-color-mode-btn > span').first().text(mode);
    pdfColorMode = mode;
    rerenderPDFPage(pdfDisplayedCurrentPage, false);
    pycmd('siac-update-config-str pdf.color_mode ' + mode);
    $('#siac-pdf-top').removeClass("siac-pdf-sand siac-pdf-night siac-pdf-peach siac-pdf-day siac-pdf-rose siac-pdf-moss siac-pdf-coral siac-pdf-x1 siac-pdf-x2 siac-pdf-mud").addClass("siac-pdf-" + pdfColorMode.toLowerCase());
}

/** Change the canvas colors according to the current pdfColorMode. */
window.invertCanvas = function (ctx) {
    if (pdfColorMode === "Night") {
        applyFilter(ctx, "#121212", "overlay");
        colorize(ctx, '#2496dc', 0.4);
        // invert(ctx);
        // applyFilter(ctx, "#121212", "lighten");
        // overlay(ctx, "#f5f0bc");
    } else if (pdfColorMode === 'X1') {
        invert(ctx);
        colorize(ctx, 'teal', 0.4);
        darken(ctx, 'lightsalmon');
    } else if (pdfColorMode === 'X2') {
        invert(ctx);
        colorize(ctx, 'darkslategrey', 0.4);
        darken(ctx, 'coral');
    } else if (pdfColorMode === 'Mud') {
        invert(ctx);
        colorize(ctx, 'coral', 0.3);
        darken(ctx, 'coral');
    } else if (pdfColorMode === 'Coral') {
        darken(ctx, '#ffb89e');
    } else if (pdfColorMode === 'Sand') {
        darken(ctx, '#ffebb3');
    } else if (pdfColorMode === 'Peach') {
        darken(ctx, '#ffcba4');
    } else if (pdfColorMode === 'Moss') {
        colorize(ctx, 'green', 0.4);
    }
    ctx.canvas.style.display = "inline-block";
}

/** Not used anymore currently. */
window.pxToSandScheme = function (red, green, blue) {
    if (red > 240 && green > 240 && blue > 240) { return { r: 241, g: 206, b: 147 }; }
    if (Math.abs(red - green) < 15 && Math.abs(red - blue) < 15) {
        red = Math.max(0, red - 40);
        green = Math.max(0, green - 40);
        blue = Math.max(0, blue - 40);
        return { r: red, g: green, b: blue };
    }
    if (red < 100 && green < 100 && blue < 100) { return { r: 0, g: 0, b: 0 }; }
    return { r: red, g: green, b: blue };
}
/** Not used anymore currently. */
window.pxToPeachScheme = function (red, green, blue) {
    if (red > 240 && green > 240 && blue > 240) { return { r: 237, g: 209, b: 176 }; }
    if (Math.abs(red - green) < 15 && Math.abs(red - blue) < 15) {
        red = Math.max(0, red - 40);
        green = Math.max(0, green - 40);
        blue = Math.max(0, blue - 40);
        return { r: red, g: green, b: blue };
    }
    if (red < 100 && green < 100 && blue < 100) { return { r: 0, g: 0, b: 0 }; }
    return { r: red, g: green, b: blue };
}
window.colorize = function (context, color, alpha) {
    context.globalCompositeOperation = "source-atop";
    context.globalAlpha = alpha;
    context.fillStyle = color;
    context.fillRect(0, 0, context.canvas.width, context.canvas.height);
    context.globalCompositeOperation = "source-over";
    context.globalAlpha = 1.0;
}
window.invert = function (ctx) {
    ctx.globalCompositeOperation = 'difference';
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.darken = function (ctx, color) {
    ctx.globalCompositeOperation = 'darken';
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.lighten = function (ctx, color) {
    ctx.globalCompositeOperation = 'lighten';
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.overlay = function (ctx, color) {
    ctx.globalCompositeOperation = 'overlay';
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.applyFilter = function (ctx, color, filter) {
    ctx.globalCompositeOperation = filter;
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}
window.refreshCanvas = function () {
    try {
        const ctx = activeCanvas().getContext("2d");
        ctx.putImageData(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height), 0, 0);
    } catch (e) { }
}
