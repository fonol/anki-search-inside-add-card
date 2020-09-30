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
// Functions for the cloze / text extraction from PDFs.
//


window.joinTextLayerNodeTexts = function (nodes, text) {
    let total = "";
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].innerHTML === text) {
            return text;
        }
        total += nodes[i].innerHTML += " ";
    }
    total = total.replace("  ", " ");
    let spl = total.split(" ");
    total = "";
    for (var i = 0; i < spl.length; i++) {
        if (spl[i].length > 0 && text.indexOf(spl[i]) >= 0) {
            total += spl[i] + " ";
        }
    }
    return total.trim();
}

window.nodesInSelection = function (range) {
    var lAllChildren = byId("text-layer").children;
    let nodes = [];
    let inside = false;
    let start = range.startContainer.nodeName === "#text" ? range.startContainer.parentNode : range.startContainer;
    let end = range.endContainer.nodeName === "#text" ? range.endContainer.parentNode : range.endContainer;
    for (var i = 0; i < lAllChildren.length; i++) {
        if (lAllChildren[i] == start) {
            inside = true;
        }
        if (inside) {
            nodes.push(lAllChildren[i]);
        }
        if (lAllChildren[i] == end) {
            break;
        }
    }
    return nodes;
}
window.getSentencesAroundSelection = function (range, nodesInSel, selection) {
    if (!range.startContainer) {
        return;
    }
    selection = selection.replace(/  +/g, " ").trim();
    let currentNode = range.startContainer.parentElement.previousSibling;
    let text = "";
    let height = 0;
    let lastOffsetTop = 0;
    if (nodesInSel.length === 1) {
        text = nodesInSel[0].innerHTML;
        height = nodesInSel[0].clientHeight;
    } else {
        for (var i = 0; i < nodesInSel.length; i++) {
            text += nodesInSel[i].innerHTML + " ";
            height = nodesInSel[i].clientHeight;
        }
    }
    lastOffsetTop = nodesInSel[0].offsetTop;
    text = text.replace(/  +/g, " ").trim();
    let extracted = [];
    if (!currentNode) {
        extracted.push(text);
    }
    while (currentNode) {
        if (Math.abs(currentNode.clientHeight - height) > 5 || lastOffsetTop - currentNode.offsetTop > height * 1.5) {
            extracted.push(text);
            break;
        }
        lastOffsetTop = currentNode.offsetTop;
        text = (currentNode.innerHTML + " " + text).replace(/  +/g, " ").trim();
        let ext = extractPrev(text, extracted, selection);
        extracted = ext[1];
        if (ext[0]) {
            break;
        }
        currentNode = currentNode.previousSibling;
        if (!currentNode) {
            extracted.push(text);
            break;
        }
    }
    let extractedFinal = [];
    for (var i = 0; i < extracted.length; i++) {
        text = extracted[i];
        currentNode = range.endContainer.parentElement.nextSibling;
        if (!currentNode) {
            extractedFinal.push(text);
        }
        while (currentNode) {
            text = (text + " " + currentNode.innerHTML).replace(/  +/g, " ").trim();
            let ext = extractNext(text, extractedFinal, selection);
            extractedFinal = ext[1];
            if (ext[0]) {
                break;
            }
            currentNode = currentNode.nextSibling;
            if (!currentNode) {
                extractedFinal.push(text);
                break;
            }
        }
    }
    return extractedFinal;
}

window.sendClozes = function () {
    let sentences = $('#siac-pdf-tooltip').data("sentences");
    let selection = $('#siac-pdf-tooltip').data("selection");
    pycmd("siac-show-cloze-modal " + selection + "$$$" + sentences.join("$$$"));
}
window.generateClozes = function () {
    let cmd = "";
    $('.siac-cl-row').each(function (i, elem) {
        cmd += "$$$" + $(elem.children[0].children[0]).text();
    });
    let pdfPath = $('#siac-pdf-top').data("pdfpath");
    let pdfTitle = $('#siac-pdf-top').data("pdftitle");
    pycmd('siac-generate-clozes $$$' + pdfTitle + "$$$" + pdfPath + "$$$" + pdfDisplayedCurrentPage + cmd);
    $('#siac-pdf-tooltip').hide();
}

window.extractPrev = function (text, extracted, selection) {
    text = text.substring(0, text.lastIndexOf(selection) + selection.length) + text.substring(text.lastIndexOf(selection) + selection.length).replace(/\./g, "$DOT$");
    let matches = text.match(/.*[^.\d][.!?]"? (.+)/);
    if (!matches || matches[1].indexOf(selection) === -1) {
        return [false, extracted];
    }
    let ext = matches[1].replace(/\$DOT\$/g, ".");
    if (extracted.indexOf(ext) === -1) {
        extracted.push(ext);
    }
    return [true, extracted];

}
window.extractNext = function (text, extracted, selection) {
    text = text.substring(0, text.indexOf(selection)).replace(/\./g, "$DOT$") + text.substring(text.indexOf(selection));

    let matches = text.match(/(.+?(\.\.\.(?!,| [a-z])|[^.]\.(?!(\.|[0-9]|[A-Z]{2,20}))|[!?]|[^0-9]\. [A-Z])).*/);
    if (!matches || matches[1].indexOf(selection) === -1) {
        return [false, extracted];
    }
    let ext = matches[1].replace(/\$DOT\$/g, ".");
    if (extracted.indexOf(ext) === -1) {
        extracted.push(ext);
    }
    return [true, extracted];
}