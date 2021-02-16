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

window.SIAC.Colors = new function () {

    /**
     * Private members
     */

    /** Not used anymore currently. */
    var pxToSandScheme = function (red, green, blue) {
        if (red > 240 && green > 240 && blue > 240) { return { r: 241, g: 206, b: 147 }; }
        if (Math.abs(red - green) < 15 && Math.abs(red - blue) < 15) {
            red = Math.max(0, red - 40);
            green = Math.max(0, green - 40);
            blue = Math.max(0, blue - 40);
            return { r: red, g: green, b: blue };
        }
        if (red < 100 && green < 100 && blue < 100) { return { r: 0, g: 0, b: 0 }; }
        return { r: red, g: green, b: blue };
    };
    /** Not used anymore currently. */
    var pxToPeachScheme = function (red, green, blue) {
        if (red > 240 && green > 240 && blue > 240) { return { r: 237, g: 209, b: 176 }; }
        if (Math.abs(red - green) < 15 && Math.abs(red - blue) < 15) {
            red = Math.max(0, red - 40);
            green = Math.max(0, green - 40);
            blue = Math.max(0, blue - 40);
            return { r: red, g: green, b: blue };
        }
        if (red < 100 && green < 100 && blue < 100) { return { r: 0, g: 0, b: 0 }; }
        return { r: red, g: green, b: blue };
    };
    var colorize = function (context, color, alpha) {
        context.globalCompositeOperation = "source-atop";
        context.globalAlpha = alpha;
        context.fillStyle = color;
        context.fillRect(0, 0, context.canvas.width, context.canvas.height);
        context.globalCompositeOperation = "source-over";
        context.globalAlpha = 1.0;
    };
    var invert = function (ctx) {
        ctx.globalCompositeOperation = 'difference';
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    };
    var darken = function (ctx, color) {
        ctx.globalCompositeOperation = 'darken';
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    };
    var lighten = function (ctx, color) {
        ctx.globalCompositeOperation = 'lighten';
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    };
    var overlay = function (ctx, color) {
        ctx.globalCompositeOperation = 'overlay';
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    };
    var applyFilter = function (ctx, color, filter) {
        ctx.globalCompositeOperation = filter;
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    };

    /**
     * Public members
     */

    this.pdfColorMode = '';

    this.setPDFColorMode = function (mode) {
        $('#siac-pdf-color-mode-btn > span').first().text(mode);
        this.pdfColorMode = mode;
        pycmd('siac-update-config-str pdf.color_mode ' + mode);
        $('#siac-pdf-top').removeClass("siac-pdf-sand siac-pdf-night siac-pdf-peach siac-pdf-day siac-pdf-rose siac-pdf-moss siac-pdf-coral siac-pdf-x1 siac-pdf-x2 siac-pdf-mud siac-pdf-spooky").addClass("siac-pdf-" + this.pdfColorMode.toLowerCase());
    };

    /** Change the canvas colors according to the current this.pdfColorMode. */
    this.invertCanvas = function (ctx) {
        if (this.pdfColorMode === "Night") {
            colorize(ctx, 'blue', 0.3);
        } else if (this.pdfColorMode === 'X1') {
            invert(ctx);
            colorize(ctx, 'teal', 0.4);
            darken(ctx, 'lightsalmon');
        } else if (this.pdfColorMode === 'X2') {
            invert(ctx);
            colorize(ctx, 'darkslategrey', 0.4);
            darken(ctx, 'coral');
        } else if (this.pdfColorMode === 'Mud') {
            invert(ctx);
            colorize(ctx, 'coral', 0.3);
            darken(ctx, 'coral');
        } else if (this.pdfColorMode === 'Coral') {
            darken(ctx, '#ffb89e');
        } else if (this.pdfColorMode === 'Sand') {
            darken(ctx, '#ffebb3');
        } else if (this.pdfColorMode === 'Peach') {
            darken(ctx, '#ffcba4');
        } else if (this.pdfColorMode === 'Moss') {
            colorize(ctx, 'green', 0.4);
        } else if (this.pdfColorMode === 'Spooky') {
            invert(ctx);
            darken(ctx, '#e50045');
        }
        ctx.canvas.style.display = "inline-block";
    };

    this.shouldChangeColors = function() {
        return ["Sand", "Peach", "Night", "X1", "X2", "Mud", "Coral", "Moss", "Spooky"].indexOf(this.pdfColorMode) !== -1;
    },


    this.refreshCanvas = function () {
        try {
            const ctx = activeCanvas().getContext("2d");
            ctx.putImageData(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height), 0, 0);
        } catch (e) { }
    };
    //
    // Theme dialog
    //
    this.setTextureBg = function (bg, bg_size, type = 'svg') {
        pycmd("siac-update-config-str styles.readingModalBackgroundSize $1".replace('$1', bg_size));
        pycmd("siac-styling styles.readingModalTexture url('$1.$2')".replace('$1', bg).replace('$2', type));
    }
};


