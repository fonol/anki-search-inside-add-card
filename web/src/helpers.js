

window.SIAC.Helpers = {

    /**
    * Uses canvas.measureText to compute and return the width of the given text of given font in pixels.
    * 
    * @param {String} text The text to be rendered.
    * @param {String} font The css font descriptor that text is to be rendered with (e.g. "bold 14px verdana").
    * 
    * @see https://stackoverflow.com/questions/118241/calculate-text-width-with-javascript/21015393#21015393
    */
    calculateTextWidth: function (text, font) {
        var canvas = this.calculateTextWidth.canvas || (this.calculateTextWidth.canvas = document.createElement("canvas"));
        var context = canvas.getContext("2d");
        context.font = font;
        var metrics = context.measureText(text);
        return metrics.width;
    },

    isAncestor: function (node, container) {
        while (node) {
            if (node === container) {
                return true;
            }
            node = node.parentNode;
        }
        return false;
    },

    /**
     * Returns true if the given element or any of its ancestors contains the current selected range. 
     */
    selectionIsInside: function (el) {

        let sel = window.getSelection();
        if (sel.rangeCount > 0) {
            for (var i = 0; i < sel.rangeCount; ++i) {
                if (!this.isAncestor(sel.getRangeAt(i).commonAncestorContainer, el)) {
                    return false;
                }
            }
            return true;
        }
        return false;
    },
    getSelectionCoords: function () {
        let sel = window.getSelection();
        if (sel.rangeCount) {
            $('#text-layer > span').css("height", "auto");
            let range = sel.getRangeAt(0);
            let rects = range.getClientRects();
            let res = { top: -1, bottom: -1, left: -1, right: -1 };

            for (var i = 0; i < rects.length; i++) {
                if (rects[i].left < res.left || res.left === -1) res.left = rects[i].left;
                if (rects[i].top < res.top || res.top === -1) res.top = rects[i].top;
                if (rects[i].bottom > res.bottom || res.bottom === -1) res.bottom = rects[i].bottom;
                if (rects[i].right > res.right || res.right === -1) res.right = rects[i].right;
            }
           
            $('#text-layer > span').css("height", "200px");
            if (res.top > -1 && res.bottom > -1 && res.left > -1 && res.right > -1) {
                return { top: res.top, left: res.left, width: res.right - res.left, height: res.bottom - res.top };
            }
            return null;
        }
        return null;
    }

};
