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


/** Experimental function to improve copy+paste from the text layer. */
window.onPDFCopy = function (e) {
    let sel = getSelection();
    let r = sel.getRangeAt(0);
    let nodes = nodesInSelection(r);
    if (!nodes) { return; }
    let text = "";
    let offsetLeftLast = 0;
    let offsetTopLast = 0;
    let widthLast = 0;
    let insertedCount = 0;
    let lastYDiffs = [];
    let lastFontSize = null;
    for (let i = 0; i < nodes.length; i++) {


        // check for new line
        if ((nodes[i].offsetLeft < offsetLeftLast || nodes[i].offsetTop > offsetTopLast + 5) && !nodes[i].innerText.startsWith(" ")) {
            // check for last font size, if difference is large, insert newlines
            if (lastFontSize && Math.abs(Number(nodes[i].style.fontSize.substring(0, nodes[i].style.fontSize.indexOf("px"))) - lastFontSize) > 4) {
                text += "\n\n" + nodes[i].innerText;
                insertedCount += 2;
            }

            // check for line with larger vertical distance to the previous lines 
            else if (lastYDiffs.length > 0 && (nodes[i].offsetTop - offsetTopLast) > lastYDiffs.slice(-1)[0] + 2) {
                text += "\n\n" + nodes[i].innerText;
                insertedCount += 2;
            }
            // if last word in previous line was hyphenated, join them
            else if (text.endsWith("-")) {
                text = text.substring(0, text.length - 1) + nodes[i].innerText;
                insertedCount--;
                // else insert a whitespace
            } else {
                text += " " + nodes[i].innerText;
                insertedCount++;
            }
            if (offsetTopLast !== 0) {
                lastYDiffs.push(nodes[i].offsetTop - offsetTopLast);
            }
            lastFontSize = Number(nodes[i].style.fontSize.substring(0, nodes[i].style.fontSize.indexOf("px")));

            // check for space between text divs, if there is enough space, we should probably insert a whitespace
        } else if (offsetLeftLast + widthLast < nodes[i].offsetLeft - 2 && !nodes[i].innerText.startsWith(" ")) {
            text += " " + nodes[i].innerText;
            insertedCount++;
        }
        else {
            text += nodes[i].innerText;
        }

        offsetLeftLast = nodes[i].offsetLeft;
        offsetTopLast = nodes[i].offsetTop;
        widthLast = nodes[i].offsetWidth;
    }
    let original = sel.toString();
    if (!text.length && original.length) {
        text = original;
    }
    text = text.replace("  ", " ");
    if (!original.startsWith(text.substring(0, Math.min(10, text.length)))) {
        for (var y = 10; y > 0; y--) {
            if (text.indexOf(original.substring(0, Math.min(y, original.length))) > 0) {
                text = text.substring(text.indexOf(original.substring(0, Math.min(y, original.length))));
                break;
            }
        }
    }
    if (text.length > original.length + insertedCount) {
        for (var ce = 10; ce > 0; ce--) {
            let lastOrig = original.substring(original.length - (Math.min(original.length, ce)));
            if (text.lastIndexOf(lastOrig) >= 0) {
                text = text.substring(0, text.lastIndexOf(lastOrig) + lastOrig.length);
                break;
            }
        }
    }

    text = text.replace(/( |&nbsp;){2,}/g, " ");
    text = text.replace(/ ([,.;:]) /g, "$1 ");
    text = text.replace(/ ([)\].!?:])/g, "$1");
    text = text.replace(/([(\[]) /g, "$1");
    e.clipboardData.setData('text/plain', text);
    e.preventDefault();
}

window.pdfLeftTabPdfSearchKeyup = function (value, event) {
    if (event.keyCode !== 13) {
        return;
    }
    if (value && value.trim().length > 0) {
        pycmd("siac-pdf-left-tab-pdf-search " + value);
    }
}

window.pdfLeftTabAnkiSearchKeyup = function (value, event) {
    if (event.keyCode !== 13) {
        return;
    }
    if (value && value.trim().length > 0) {
        pycmd("siac-pdf-left-tab-anki-search " + value);
    }
}

window.initAreaHighlightShortcutPressed = function() {
    if (pdf.instance && !iframeIsDisplayed && Highlighting.colorSelected.id > 0) {
        readerNotification("&nbsp;Area Highlight&nbsp;");
        initAreaHighlight();
        pdfTextLayerMetaKey = false;
    }
}


window.pdfTooltipClozeKeyup = function (event) {
    try {
        if (event.ctrlKey && event.shiftKey && event.keyCode === 67) {
            let text = window.getSelection().toString();
            if (!text || text.length === 0) {
                return;
            }
            let c_text = byId("siac-pdf-tooltip-results-area").innerHTML;
            for (var i = 1; i < 20; i++) {
                if (c_text.indexOf("{{c" + i + "::") === -1) {
                    c_text = c_text.split(text).join("<span style='color: lightblue;'>{{c" + i + "::" + text + "}}</span>");
                    byId("siac-pdf-tooltip-results-area").innerHTML = c_text;
                    break;
                }
            }
        }
    } catch (ex) {
        pycmd("siac-notification Something went wrong during clozing:<br> " + ex.message);
    }
}

window.markClicked = function (event) {
    if (event.target.className === "siac-page-mark-link") {
        pdf.page = Number(event.target.innerHTML);
        queueRenderPage(pdf.page, true);
    }
}

window.iframeBtnClicked = function(event) {
    event.preventDefault();
    $(event.target).toggleClass("expanded");
    event.stopPropagation();
    if ($(event.target).hasClass("expanded")) {
        $(event.target).find("input").first().focus();
    }
}

// clicked on the text layer, should
// 1. hide the tooltip if present
// 2. trigger the click on a highlight if it is below the textlayer at the given coords
window.textlayerClicked = function (event, el) {
    if (!event.ctrlKey && !windowHasSelection()) {
        $("#siac-pdf-tooltip").hide();
        if (el.style.pointerEvents !== "none") {
            el.style.pointerEvents = "none";
            let e = $.Event("click");
            e.ctrlKey = true;
            $(document.elementFromPoint(event.clientX, event.clientY)).trigger(e);
            el.style.pointerEvents = "auto";
        }
    }
}


/**
 *  executed after keyup in the pdf pane
 */
window.pdfKeyup = function (e) {
    if (!e) {
        return;
    }
    // selected text, no ctrl key -> show tooltip if enabled 
    if (!e.ctrlKey && !e.metaKey && pdfTooltipEnabled && windowHasSelection()) {
        pdfTooltip(e);
    } else if ((e.ctrlKey || e.metaKey) && Highlighting.colorSelected.id > 0 && windowHasSelection()) {
        // selected text, ctrl key pressed -> highlight 
        Highlighting.highlight();
        pdfTextLayerMetaKey = false;
    } else if ((e.ctrlKey || e.metaKey) && Highlighting.colorSelected.id === 0 && !windowHasSelection()) {
        // clicked with ctrl, text insert btn is active -> insert text area at coordinates
        Highlighting.insertText(e);
    } 
    
}

window.pdfTooltip = function(e) {
    $('#text-layer .tl-highlight').remove();
    let s = window.getSelection();
    let r = s.getRangeAt(0);
    let text = s.toString();
    if (text.trim().length === 0 || text.length > 500) { return; }
    // spans in textlayer have a max height to prevent selection jumping, but here we have to temporarily 
    // disable it, to get the actual bounding client rect
    $('#text-layer > span').css("height", "auto");
    let nodesInSel = nodesInSelection(r);
    let sentences = getSentencesAroundSelection(r, nodesInSel, text);
    if (nodesInSel.length > 1) {
        text = joinTextLayerNodeTexts(nodesInSel, text);
    }
    let rect = r.getBoundingClientRect();
    let prect = byId("siac-reading-modal").getBoundingClientRect();
    let left = rect.left - prect.left;
    if (prect.width - left < 250) {
        left -= 200;
    }
    let top = rect.top - prect.top + rect.height;
    if (top < 0) { return; }
    // save render to be able to go back
    pdf.tooltip = {
        sentences: sentences,
        selection: text,
        top: top,
        left: left,
    };
    renderTooltip(sentences, text, top, left);
    // limit height again to prevent selection jumping
    $('#text-layer > span').css("height", "200px");
}
window.renderTooltip = function(sentences, selection, top, left) {
    byId('siac-pdf-tooltip').innerHTML = '<center>Searching...</center>';
    $('#siac-pdf-tooltip').css({ 'top': top + "px", 'left': left + "px", 'display': 'flex' });
    pycmd("siac-pdf-selection " + selection);
    $('#siac-pdf-tooltip').data({"sentences":  sentences, "selection": selection, "top": top});
}

window.pdfMouseWheel = function (event) {
    if (!event.ctrlKey && !event.metaKey) { return; }
    if (event.deltaY < 0) {
        pdfScaleChange("up");
    }
    else if (event.deltaY > 0) {
        pdfScaleChange("down");
    }
    event.preventDefault();
}
