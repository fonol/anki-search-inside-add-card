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

import { Highlighting } from "./pdf_highlighting.js";


window.Highlighting = Highlighting;

/** Pomodoro timer */
window.remainingSeconds = 30 * 60;
window.readingTimer = null;

/** PDF rendering */
window.pdfDisplayed = null;
window.pdfDisplayedViewPort = null;
window.pdfPageRendering = false;
window.pdfDisplayedCurrentPage = null;
window.pdfDisplayedScale = 2.0;
window.pdfHighDPIWasUsed = false;
window.pdfColorMode = "Day";
window.pageNumPending = null;
window.latestRenderTimestamp = null;

/** PDF meta (pages read, marks, extract) */
window.pagesRead = [];
window.pdfExtract = null;
window.pdfDisplayedMarks = null;
window.pdfDisplayedMarksTable = null;
window.pdfLastReadPages = {};

/** State variables */
window.noteLoading = false;
window.pdfLoading = false;
window.modalShown = false;
window.pdfTooltipEnabled = true;
window.iframeIsDisplayed = false;
window.pageSidebarDisplayed = true;
window.pdfFullscreen = false;
window.pdfBarsHidden = false;
window.displayedNoteId = null;
window.pdfTextLayerMetaKey = false;
window.pdfNotification = {
    queue: [],
    current: ""
};
/** SimpleMDE */
window.textEditor = null;

/** Workaround for older chromium versions. */
if (typeof globalThis === "undefined") {
    var globalThis = window;
}


/**
 * ###########################################
 *  PDF rendering
 * ###########################################
 */

window.pdfFitToPage = function() {
    if (!iframeIsDisplayed) {
        rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
    }
}
window.queueRenderPage = function(num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (pdfPageRendering) {
        pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
    }
}
window.rerenderPDFPage = function(num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    document.getElementById("siac-pdf-tooltip").style.display = "none";
    document.getElementById("siac-pdf-page-lbl").innerHTML = `${pdfDisplayedCurrentPage} / ${pdfDisplayed.numPages}`;
    Highlighting._removeAllHighlights();
    pdfLoading = true;
    pdfDisplayed.getPage(num)
        .then(function (page) {
            updatePdfDisplayedMarks();
            pdfPageRendering = true;
            var lPage = page;
            var pageTimestamp = new Date().getTime();
            latestRenderTimestamp = pageTimestamp;
            var canvas = document.getElementById("siac-pdf-canvas");
            if (fitToPage) {
                var viewport = page.getViewport({ scale: 1.0 });
                pdfDisplayedScale = (canvas.parentNode.clientWidth - 23) / viewport.width;
            }
            var viewport = page.getViewport({ scale: pdfDisplayedScale });
            canvas.height = viewport.height * window.devicePixelRatio;
            canvas.width = viewport.width * window.devicePixelRatio;
            if (window.devicePixelRatio !== 1 || pdfHighDPIWasUsed) {
                pdfHighDPIWasUsed = true;
                canvas.style.height = viewport.height + "px";
                canvas.style.width = viewport.width + "px";
            }
            if (["Peach", "Sand", "Night", "X1", "X2", "Mud"].indexOf(pdfColorMode) !== -1)
                canvas.style.display = "none";
            var ctx = canvas.getContext('2d');
            var renderTask = page.render({
                canvasContext: ctx,
                viewport: viewport,
                transform: window.devicePixelRatio !== 1 ? [window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0] : null,
                continueCallback: function (cont) {
                    if (latestRenderTimestamp != pageTimestamp) {
                        return;
                    }
                    cont();
                }
            });
            if (pageNumPending !== null) {
                rerenderPDFPage(pageNumPending, shouldScrollUp);
                pageNumPending = null;
                return Promise.reject();
            }
            renderTask.promise.then(function () {
                pdfPageRendering = false;
                if (pageNumPending !== null) {
                    rerenderPDFPage(pageNumPending, shouldScrollUp);
                    pageNumPending = null;
                    return null;
                } else {
                    if (["Sand", "Peach", "Night", "X1", "X2", "Mud"].indexOf(pdfColorMode) !== -1) {
                        invertCanvas(ctx);
                    }
                }
                return lPage.getTextContent({ normalizeWhitespace: false, disableCombineTextItems: false });
            }).catch(function (err) { console.log(err); return Promise.reject(); }).then(function (textContent) {
                if (!textContent) {
                    return Promise.reject();
                }
                if (pageNumPending) {
                    return; 
                }
                $("#text-layer").css({ height: canvas.height / window.devicePixelRatio, width: canvas.width / window.devicePixelRatio + 1, left: canvas.offsetLeft }).html('');
                pdfjsLib.renderTextLayer({
                    textContent: textContent,
                    container: document.getElementById("text-layer"),
                    viewport: viewport,
                    textDivs: []
                });
                if (query) {
                    highlightPDFText(query);
                } else {
                    resetSearch();
                }
                pdfLoading = false;
                if (isInitial || query) {
                    ungreyoutBottom();
                }
                if (isInitial) {
                    setTimeout(function () { refreshCanvas(); }, 3000);
                }
                pdfDisplayedViewPort = viewport;
                if (fetchHighlights) {
                    Highlighting.current = [];
                    pycmd("siac-pdf-page-loaded " + pdfDisplayedCurrentPage);
                } else {
                    Highlighting.displayHighlights();
                }
                setLastReadPage();
            });
            if (!pageNumPending) {
                if (shouldScrollUp) {
                    canvas.parentElement.scrollTop = 0;
                }
                if (pagesRead.indexOf(num) !== -1) {
                    document.getElementById('siac-pdf-overlay').style.display = 'block';
                    document.getElementById('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Unread';
                } else {
                    document.getElementById('siac-pdf-overlay').style.display = 'none';
                    document.getElementById('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Read';
                }
                if (fetchHighlights && pdfExtract) {
                    if (pdfExtract[0] > pdfDisplayedCurrentPage || pdfExtract[1] < pdfDisplayedCurrentPage) {
                        $('#siac-pdf-top').addClass("extract");
                    } else {
                        $('#siac-pdf-top').removeClass("extract");
                    }
                }
                if (fetchHighlights && pageSidebarDisplayed) {
                    pycmd("siac-linked-to-page " + pdfDisplayedCurrentPage);
                }
            }
        }).catch(function (err) { setTimeout(function () { console.log(err); }); });
}

window.invertCanvas = function(ctx) {
    if (pdfColorMode === "Night") {
        colorize(ctx, '#2496dc', 0.4);
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
    } else {
        var imgData = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
        var data = imgData.data;
        var mapped;
        var fn;

        switch (pdfColorMode) {
            case "Sand": fn = pxToSandScheme; break;
            case "Peach": fn = pxToPeachScheme; break;
        }
        for (var i = 0; i < data.length; i += 4) {
            mapped = fn(data[i], data[i + 1], data[i + 2]);
            data[i] = mapped.r;
            data[i + 1] = mapped.g;
            data[i + 2] = mapped.b;
        }
        ctx.putImageData(imgData, 0, 0);
    }
    ctx.canvas.style.display = "inline-block";
}
window.refreshCanvas = function() {
    try {
        const ctx = document.getElementById("siac-pdf-canvas").getContext("2d");
        ctx.putImageData(ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height), 0, 0);
    } catch (e) { }
}


/**
 * ###########################################
 *  Buttons & related functions
 * ###########################################
 */

window.pdfPageRight = function() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage < pdfDisplayed.numPages) {
        pdfDisplayedCurrentPage++;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}
window.pdfPageLeft = function() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage > 1) {
        pdfDisplayedCurrentPage--;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}

window.togglePageRead = function(nid) {

    // function can be called from pyqt shortcut, so it might be that no PDF is displayed when shortcut is triggered
    if (!pdfDisplayed) {
        return;
    }

    // don't allow for blue'd out pages in pdf extracts to be marked as read
    if (pdfExtract && (pdfDisplayedCurrentPage < pdfExtract[0] || pdfDisplayedCurrentPage > pdfExtract[1])) {
        return;
    }

    if (!nid) {
        nid = displayedNoteId;
    }

    if (pagesRead.indexOf(pdfDisplayedCurrentPage) === -1) {
        document.getElementById('siac-pdf-overlay').style.display = 'block';
        document.getElementById('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Unread';
        pycmd("siac-pdf-page-read " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
    } else {
        document.getElementById('siac-pdf-overlay').style.display = 'none';
        document.getElementById('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Read';
        pycmd("siac-pdf-page-unread " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        pagesRead.splice(pagesRead.indexOf(pdfDisplayedCurrentPage), 1);
    }
    updatePdfProgressBar();
}
window.pdfHidePageReadMark = function() {
    document.getElementById("siac-pdf-overlay").style.display = "none"; document.getElementById("siac-pdf-read-btn").innerHTML = "\u2713&nbsp; Read";
}
window.pdfShowPageReadMark = function() {
    document.getElementById("siac-pdf-overlay").style.display = "block"; document.getElementById("siac-pdf-read-btn").innerHTML = "&times; Unread";
}
window.pdfJumpToPage = function(e, inp) {
    if (e.keyCode !== 13) {
        return;
    }
    let p = inp.value;
    p = Math.min(pdfDisplayed.numPages, p);
    pdfDisplayedCurrentPage = p;
    queueRenderPage(pdfDisplayedCurrentPage);
}
window.pdfScaleChange = function(mode) {
    if (mode === "up") {
        pdfDisplayedScale += 0.1;
    } else {
        pdfDisplayedScale -= 0.1;
        pdfDisplayedScale = Math.max(0.1, pdfDisplayedScale);
    }
    queueRenderPage(pdfDisplayedCurrentPage, false, false, false, '', false);
}
window.setAllPagesRead = function() {
    if (!pdfExtract) {
        pagesRead = Array.from(Array(pdfDisplayed.numPages).keys()).map(x => ++x)
    } else {
        pagesRead = [];
        for (var i = pdfExtract[0]; i <= pdfExtract[1]; i++) {
            pagesRead.push(i);
        }
    }
    if (pagesRead.indexOf(pdfDisplayedCurrentPage) !== -1) {
        pdfShowPageReadMark();
    }
}
window.saveTextNote = function(nid) {
    let html = "";
    try {
        html = textEditor.value();
    } catch (e) {
        pycmd("siac-notification Could not save text note for some reason.");
        return;
    } 
    readerNotification("&nbsp;<i class='fa fa-save'></i>&nbsp; Note saved.&nbsp;");
    pycmd("siac-update-note-text " + nid + " " + html);
}
window.toggleQueue = function() {
    if (noteLoading || pdfLoading || modalShown) {
        return;
    }
    let $wr = $("#siac-queue-sched-wrapper");
    if ($wr.hasClass('active')) {
        $wr.css({ "max-width": "0px", "overflow": "hidden" });
        $('.siac-queue-sched-btn:first').addClass("active");
    } else {
        $wr.css({ "max-width": "500px", "overflow": "visible" });
        $('.siac-queue-sched-btn:first').removeClass("active");
    }
    $wr.toggleClass('active');
}
window.queueSchedBtnClicked = function(btn_el) {
    $('#siac-queue-lbl').hide();
    $('.siac-queue-sched-btn').removeClass("active");
    toggleQueue();
    $(btn_el).addClass("active");
}
window.onQuickSchedBtnClicked = function(elem) {
    if (!$(elem).hasClass("expanded")) {
        pycmd("siac-quick-schedule-fill");
    } else {
        $(elem).toggleClass('expanded');
    }
}
window.setLastReadPage = function() {
    pdfLastReadPages[displayedNoteId] = pdfDisplayedCurrentPage;
}
window.getLastReadPage = function() {
    if (displayedNoteId && displayedNoteId in pdfLastReadPages) {
        return pdfLastReadPages[displayedNoteId];
    }
    return null;
}

window.updatePdfProgressBar = function() {
    let percs = Math.floor(pagesRead.length * 10 / numPagesExtract());
    let html = `<span style='margin-right: 10px; display: inline-block; min-width: 35px;'>${Math.trunc(pagesRead.length * 100 / numPagesExtract())} %</span>`;
    for (var c = 0; c < 10; c++) {
        if (c < percs) {
            html += `<div class='siac-prog-sq-filled'></div>`;
        } else {
            html += `<div class='siac-prog-sq'></div>`;
        }
    }
    document.getElementById("siac-prog-bar-wr").innerHTML = html;
}
window.numPagesExtract = function() {
    if (!pdfExtract) {
        return pdfDisplayed.numPages;
    }
    return pdfExtract[1] - pdfExtract[0] + 1;
}

window.markReadUpToCurrent = function() {
    for (var i = 0; i < pdfDisplayedCurrentPage; i++) {
        if (pagesRead.indexOf(i + 1) === -1) {
            if (!pdfExtract || ((i + 1) >= pdfExtract[0] && (i + 1) <= pdfExtract[1])) {
                pagesRead.push(i + 1);
            }
        }
    }
    if (pagesRead.indexOf(pdfDisplayedCurrentPage) !== -1) {
        pdfShowPageReadMark();
    }
}

window.afterRemovedFromQueue = function() {
    toggleQueue();
    $('.siac-queue-sched-btn').first().addClass("active").html('Unqueued');
}

/**
 * ###########################################
 *  Pomodoro timer
 * ###########################################
 */


window._startTimer = function(elementToUpdateId) {
    if (readingTimer) { clearInterval(readingTimer); }
    readingTimer = setInterval(function () {
        remainingSeconds--;
        document.getElementById(elementToUpdateId).innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
        if (remainingSeconds <= 0) {
            clearInterval(readingTimer);
            remainingSeconds = 1800;
            $('#siac-timer-play-btn').html("Start").addClass("inactive");
            $('.siac-timer-btn').removeClass('active');
            $('.siac-timer-btn').eq(4).addClass('active');
            document.getElementById(elementToUpdateId).innerHTML = "30 : 00";
            pycmd('siac-timer-elapsed ' + $('#siac-reading-modal-top-bar').data('nid'));
            readingTimer = null;
        }
    }, 999);
}
window.toggleTimer = function(timer) {
    if ($(timer).hasClass('inactive')) {
        $(timer).removeClass("inactive");
        timer.innerHTML = "Pause";
        _startTimer("siac-reading-modal-timer");
    } else {
        clearInterval(readingTimer);
        readingTimer = null;
        $(timer).addClass("inactive");
        timer.innerHTML = "Start";
    }
}
window.resetTimer = function(elem) {
    clearInterval(readingTimer);
    readingTimer = null;
    $('.siac-timer-btn').removeClass('active');
    $(elem).addClass('active');
    remainingSeconds = Number(elem.innerHTML) * 60;
    document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
    $('#siac-timer-play-btn').addClass("inactive").html("Start");
}
window.startTimer = function(mins) {
    $('.siac-timer-btn').each((i, e) => {
        if (e.innerHTML === mins.toString()) {
            resetTimer(e);
            $('#siac-timer-play-btn').trigger('click');
        }
    });
}
window.escapeRegExp = function(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


/**
 * Display a short message in bottom right area of the reader.
 */
window.readerNotification = function(html, immediate) {

    if (!html) { return; }
    if (!immediate && pdfNotification.current != "") {
        if (pdfNotification.queue.length > 0) {
            if (html === pdfNotification.queue[pdfNotification.queue.length - 1]) {
                return;
            }
        } else if (pdfNotification.current === html) {
            return;
        }
        pdfNotification.queue.push(html);
        return;
    }
    pdfNotification.current = html;
    document.getElementById('siac-pdf-br-notify').innerHTML = html;
    document.getElementById('siac-pdf-br-notify').style.display = "block";

    window.setTimeout(() => {
        pdfNotification.current = "";
        if (document.getElementById('siac-pdf-br-notify')) {
            document.getElementById('siac-pdf-br-notify').style.display = "none";
            if (pdfNotification.queue.length) {
                setTimeout(function () {
                    let next = pdfNotification.queue.shift();
                    readerNotification(next, true);
                }, 800);
            }
        } else {
            pdfNotification.queue = [];
        }

    }, 3500);
}
window.swapReadingModal = function() {
    let modal = document.getElementById("siac-reading-modal");
    if (modal.parentNode.id === "siac-right-side") {
        document.getElementById("leftSide").appendChild(modal);
    } else {
        document.getElementById("siac-right-side").appendChild(modal);
    }
}
window.setPDFColorMode = function(mode) {
    $('#siac-pdf-color-mode-btn > span').first().text(mode);
    pdfColorMode = mode;
    rerenderPDFPage(pdfDisplayedCurrentPage, false);
    pycmd('siac-update-config-str pdf.color_mode ' + mode);
    $('#siac-pdf-top').removeClass("siac-pdf-sand siac-pdf-night siac-pdf-peach siac-pdf-day siac-pdf-rose siac-pdf-moss siac-pdf-coral siac-pdf-x1 siac-pdf-x2 siac-pdf-mud").addClass("siac-pdf-" + pdfColorMode.toLowerCase());
}

window.joinTextLayerNodeTexts = function(nodes, text) {
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

window.nodesInSelection = function(range) {
    var lAllChildren = document.getElementById("text-layer").children;
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
window.getSentencesAroundSelection = function(range, nodesInSel, selection) {
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

window.sendClozes = function() {
    let sentences = $('#siac-pdf-tooltip').data("sentences");
    let selection = $('#siac-pdf-tooltip').data("selection");
    pycmd("siac-show-cloze-modal " + selection + "$$$" + sentences.join("$$$"));
}
window.generateClozes = function() {
    let cmd = "";
    $('.siac-cl-row').each(function (i, elem) {
        cmd += "$$$" + $(elem.children[0].children[0]).text();
    });
    let pdfPath = $('#siac-pdf-top').data("pdfpath");
    let pdfTitle = $('#siac-pdf-top').data("pdftitle");
    pycmd('siac-generate-clozes $$$' + pdfTitle + "$$$" + pdfPath + "$$$" + pdfDisplayedCurrentPage + cmd);
    $('#siac-pdf-tooltip').hide();
}

window.extractPrev = function(text, extracted, selection) {
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
window.extractNext = function(text, extracted, selection) {
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
window.pxToSandScheme = function(red, green, blue) {
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
window.pxToPeachScheme = function(red, green, blue) {
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
window.colorize = function(context, color, alpha) {
    context.globalCompositeOperation = "source-atop";
    context.globalAlpha = alpha;
    context.fillStyle = color;
    context.fillRect(0, 0, context.canvas.width, context.canvas.height);
    context.globalCompositeOperation = "source-over";
    context.globalAlpha = 1.0;
}
window.invert = function(ctx) {
    ctx.globalCompositeOperation='difference';
    ctx.fillStyle='white';
    ctx.fillRect(0,0,ctx.canvas.width,ctx.canvas.height);
}
window.darken = function(ctx, color) {
    ctx.globalCompositeOperation='darken';
    ctx.fillStyle=color;
    ctx.fillRect(0,0,ctx.canvas.width,ctx.canvas.height);
}
window.updatePdfDisplayedMarks = function() {
    if (pdfDisplayedMarks == null) {
        return;
    }
    let html = "";
    $('.siac-mark-btn-inner').removeClass('active');
    if (pdfDisplayedCurrentPage in pdfDisplayedMarks) {
        for (var i = 0; i < pdfDisplayedMarks[pdfDisplayedCurrentPage].length; i++) {
            switch (pdfDisplayedMarks[pdfDisplayedCurrentPage][i]) {
                case 1: html += "<div class='siac-pdf-mark-lbl'>Revisit &nbsp;<b onclick='$(\".siac-mark-btn-inner-1\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-1').first().addClass('active'); break;
                case 2: html += "<div class='siac-pdf-mark-lbl'>Hard &nbsp;<b onclick='$(\".siac-mark-btn-inner-2\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-2').first().addClass('active'); break;
                case 3: html += "<div class='siac-pdf-mark-lbl'>More Info &nbsp;<b onclick='$(\".siac-mark-btn-inner-3\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-3').first().addClass('active'); break;
                case 4: html += "<div class='siac-pdf-mark-lbl'>More Cards &nbsp;<b onclick='$(\".siac-mark-btn-inner-4\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-4').first().addClass('active'); break;
                case 5: html += "<div class='siac-pdf-mark-lbl'>Bookmark &nbsp;<b onclick='$(\".siac-mark-btn-inner-5\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-5').first().addClass('active'); break;
            }
        }
    }
    let w1 = document.getElementById("siac-queue-readings-list").offsetWidth;
    let w2 = document.getElementById("siac-queue-actions").offsetWidth;
    let w = document.getElementById("siac-reading-modal-bottom-bar").clientWidth - w1 - w2 - 100;
    var tableHtml = "";
    Object.keys(pdfDisplayedMarksTable).forEach(function (key) {
        let name = "";
        switch (key) {
            case "1": name = "Revisit"; break;
            case "2": name = "Hard"; break;
            case "3": name = "More Info"; break;
            case "4": name = "More Cards"; break;
            case "5": name = "Bookmark"; break;
        }
        let pages = "";

        for (var i = 0; i < pdfDisplayedMarksTable[key].length; i++) {
            pages += "<span class='siac-page-mark-link'>" + pdfDisplayedMarksTable[key][i] + "</span>, ";
        }
        pages = pages.length > 0 ? pages.substring(0, pages.length - 2) : pages;
        tableHtml += `<tr style='color: grey;'><td><b>${name}</b></td><td>${pages}</td></tr>`;
    });
    if (tableHtml.length) {
        tableHtml = `<table style='user-select: none; table-layout: fixed; max-width: ${w}px;'>` + tableHtml + "</table>";
    }
    if (document.getElementById("siac-pdf-overlay-top-lbl-wrap"))
        document.getElementById("siac-pdf-overlay-top-lbl-wrap").innerHTML = html;
    if (document.getElementById("siac-marks-display")) { document.getElementById("siac-marks-display").innerHTML = tableHtml; }
    onMarkBtnClicked(document.getElementById("siac-mark-jump-btn"));

}

/**
 * 'Done' Shortcut activated in qt.
 */
window.doneShortcut = function() {
    if (!pdfLoading && !noteLoading && !modalShown && document.body.classList.contains("siac-reading-modal-displayed")) {
        $('#siac-first-in-queue-btn').trigger("click");
    }
}
/**
 * 'Later' Shortcut activated in qt.
 */
window.laterShortcut = function() {
    if (!pdfLoading && !noteLoading && !modalShown && document.body.classList.contains("siac-reading-modal-displayed") && document.getElementById('siac-later-btn')) {
        $('#siac-later-btn').trigger("click");
    }
}
window.jumpLastPageShortcut = function() {
    if (pdfLoading || noteLoading || modalShown || !pdfDisplayed) {
        return;
    }
    pdfDisplayedCurrentPage = pdfDisplayed.numPages;
    queueRenderPage(pdfDisplayedCurrentPage, true);
}
window.jumpFirstPageShortcut = function() {
    if (pdfLoading || noteLoading || modalShown || !pdfDisplayed) {
        return;
    }
    pdfDisplayedCurrentPage = 1;
    queueRenderPage(1, true);
}


window.togglePDFSelect = function(elem) {
    if (!elem) {
        elem = document.getElementById('siac-pdf-tooltip-toggle');
    }
    if (!elem) {
        return;
    }
    pdfTooltipEnabled = !pdfTooltipEnabled;
    if (pdfTooltipEnabled) {
        $(elem).addClass('active');
        readerNotification("Search on select enabled.", true);
    } else {
        $(elem).removeClass('active');
        $('#siac-pdf-tooltip').hide();
        readerNotification("Search on select disabled.", true);
    }
}
window.onMarkBtnClicked = function(elem) {
    if ($(elem).hasClass("expanded")) {
        if (pdfDisplayedMarks && Object.keys(pdfDisplayedMarks).length > 0) {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b onclick='event.stopPropagation(); jumpToNextMark();' style='vertical-align: middle;'>Jump to Next Mark</b>";
        } else {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b style='vertical-align:middle; color: grey;'>No Marks in PDF</b>";
        }
    }
}
window.jumpToNextMark = function() {
    if (!pdfDisplayed) {
        return;
    }
    let pages = Object.keys(pdfDisplayedMarks);
    for (var i = 0; i < pages.length; i++) {
        if (Number(pages[i]) > pdfDisplayedCurrentPage) {
            pdfDisplayedCurrentPage = Number(pages[i]);
            queueRenderPage(pdfDisplayedCurrentPage, true, false, false);
            return;
        }
    }
    pdfDisplayedCurrentPage = Number(pages[0]);
    queueRenderPage(pdfDisplayedCurrentPage, true, false, false);
}
window.bringPDFIntoView = function() {
    if ($('#siac-right-side').hasClass("addon-hidden") || $('#switchBtn').is(":visible")) {
        toggleAddon();
    }
}
window.beforeNoteQuickOpen = function() {
    if (noteLoading || pdfLoading || modalShown) {
        return false;
    }
    if (pdfDisplayed) {
        noteLoading = true;
        greyoutBottom();
        destroyPDF();
    }
    bringPDFIntoView();
    return true;
}

window.centerTooltip = function() {
    let w = $('#siac-pdf-top').width();
    let h = $('#siac-pdf-top').height();
    let $tt = $('#siac-pdf-tooltip');
    $tt.css({ 'top': h / 2 - ($tt.height() / 2), 'left': w / 2 - ($tt.width() / 2) });
}
window.destroyPDF = function() {
    if (pdfDisplayed) {
        pdfDisplayed.destroy();
    }
    pdfDisplayed = null;
}
window.pdfUrlSearch = function(input) {
    if (!input.length) { return; }
    let url = "";
    $("#siac-iframe-btn tr").each(function () {
        if ($(this.children[1].children[0]).is(":checked")) {
            url = $(this.children[1].children[0]).data("url");
        }
    });
    pycmd('siac-url-srch $$$' + input + '$$$' + url);
    $('#siac-iframe-btn').removeClass('expanded');
}
window.showQueueInfobox = function(elem, nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd('siac-queue-info ' + nid);
    document.documentElement.style.setProperty('--ttop', (elem.offsetTop) + 'px');
    if (pdfLoading || noteLoading || modalShown) { return; }

}
window.leaveQueueItem = function(elem) {
    window.setTimeout(function () {
        if (!$('#siac-queue-infobox').is(":hover") && !$('#siac-queue-readings-list .siac-clickable-anchor:hover').length) {
            hideQueueInfobox();
        }
    }, 400);
}
window.hideQueueInfobox = function() {
    if (document.getElementById("siac-queue-infobox")) {
        document.getElementById("siac-queue-infobox").style.display = "none";
        document.getElementById("siac-pdf-bottom-tabs").style.visibility = "visible";
    }
}
window.greyoutBottom = function() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .fa,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn,#siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').addClass("siac-disabled");
}
window.ungreyoutBottom = function() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .fa,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn, #siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').removeClass("siac-disabled");
}
window.unhideQueue = function(nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-unhide-pdf-queue " + nid);
}
window.hideQueue = function(nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-hide-pdf-queue " + nid);
}
window.toggleReadingModalBars = function() {
    if (!pdfBarsHidden) {
        document.getElementById("siac-reading-modal-top-bar").style.display = "none";
        document.getElementById("siac-reading-modal-bottom-bar").style.display = "none";
        pdfBarsHidden = true;
    } else {
        document.getElementById("siac-reading-modal-top-bar").style.display = "flex";
        document.getElementById("siac-reading-modal-bottom-bar").style.display = "block";
        pdfBarsHidden = false;
    }
}

window.toggleReadingModalFullscreen = function() {
    pdfFullscreen = !pdfFullscreen;
    if (pdfFullscreen) {
        $(document.body).removeClass("siac-fullscreen-show-fields").addClass("siac-fullscreen-show-right");
        if (pdfDisplayed) {
            pdfFitToPage();
        }
        pdfBarsHidden = false;
        toggleReadingModalBars();
        pycmd("siac-notification Press toggle shortcut (default Ctrl+F) to switch.");

    } else {

        $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right");
        if ($('#switchBtn').is(":visible")) {
            $('#outerWr').addClass("onesided");
        }
        onWindowResize();
        if (pdfDisplayed) {
            pdfFitToPage();
        }
    }

}
window.activateReadingModalFullscreen = function() {
    pdfFullscreen = false;
    pdfBarsHidden = true;
    toggleReadingModalFullscreen();
}
window.onReadingModalClose = function() {
    if (pdfLoading) {
        return;
    }
    displayedNoteId = null;
    $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right").removeClass('siac-reading-modal-displayed');
    $('#siac-left-tab-browse,#siac-left-tab-pdfs,#siac-reading-modal-tabs-left').remove();
    $('#fields').show();
    $("#siac-reading-modal").hide();
    document.getElementById('resultsArea').style.display = 'block';
    document.getElementById('bottomContainer').style.display = 'block';
    document.getElementById('topContainer').style.display = 'flex';
    destroyPDF();
    document.getElementById("siac-reading-modal-center").innerHTML = "";
    onWindowResize();
    window.$fields = $('.field');
    if (siacState.searchOnTyping) {
        setSearchOnTyping(true, false);
    }
    pycmd("siac-on-reading-modal-close")
}
window.tryExtractTextFromTextNote = function() {
    saveTextNote($('#siac-reading-modal-top-bar').data('nid'));
    pycmd("siac-try-copy-text-note");
}



window.modalTabsLeftClicked = function(tab, elem) {
    $('#siac-reading-modal-tabs-left .siac-btn').removeClass("active");
    $(elem).addClass("active");
    pycmd("siac-reading-modal-tabs-left-" + tab);
}

window.setPdfTheme = function(theme) {
    let style_tag = document.getElementById("siac-pdf-css");
    style_tag.href = style_tag.href.substring(0, style_tag.href.lastIndexOf("/") + 1) + theme;
    pycmd("siac-eval update_config('pdf.theme', '" + theme + "')");
}
window.schedChange = function(slider) {
    document.getElementById('siac-sched-prio-val').innerHTML = prioVerbose(slider.value);
}
window.prioVerbose = function(prio) {
    if (prio >= 85)
        return `Very high (<b>${prio}</b>)`;
    if (prio >= 70)
        return `High (<b>${prio}</b>)`;
    if (prio >= 30)
        return `Medium (<b>${prio}</b>)`;
    if (prio >= 15)
        return `Low (<b>${prio}</b>)`;
    if (prio >= 1)
        return `Very low (<b>${prio}</b>)`;
    return "Remove from Queue (<b>0</b>)";
}
window.schedChanged = function(slider, nid) {
    $('#siac-quick-sched-btn').removeClass('expanded');
    pycmd("siac-requeue " + nid + " " + slider.value);
}
window.schedSmallChanged = function(slider, nid) {
    pycmd("siac-requeue " + nid + " " + slider.value);
}
window.schedSmallChange = function(slider) {
    document.getElementById('siac-slider-small-lbl').innerHTML = slider.value;
}

window.scheduleDialogQuickAction = function() {
    let cmd = $("input[name=sched]:checked").data("pycmd");
    pycmd(`siac-eval index.ui.reading_modal.schedule_note(${cmd})`);
}
window.removeDialogOk = function(nid) {
    if ($("input[name=del]:checked").data("pycmd") == "1") {
        pycmd("siac-remove-from-queue " + nid);
    } else {
        pycmd("siac-delete-current-user-note " + nid);
    }
    modalShown = false;
    $('#siac-var(--c-reading-modal-background)out').hide();
    $('#siac-schedule-dialog').hide();
}
window.updateSchedule = function() {
    let checked = $("input[name=sched]:checked").data("pycmd");
    if (checked == "4") {
        let td = document.getElementById("siac-sched-td-inp").value;
        if (!td) { pycmd('siac-notification Value is empty!'); return; }
        pycmd("siac-update-schedule td " + td);
    } else if (checked == "5") {
        let w = '';
        $('#siac-sched-wd input').each(function (ix) {
            if ($(this).is(":checked")) {
                w += (ix + 1).toString();
            }
        });
        if (!w.length) { pycmd('siac-notification Value is empty!'); return; }
        pycmd("siac-update-schedule wd " + w);
    } else {
        let id = document.getElementById("siac-sched-id-inp").value;
        if (!id) { pycmd('siac-notification Value is empty!'); return; }
        pycmd("siac-update-schedule id " + id);
    }
}

/**
 * Show or hide the pdf page sidebar.
 * @param {boolean} persist if the updated value should be sent to the backend 
 */
window.togglePageSidebar = function(persist = true) {
    pageSidebarDisplayed = !pageSidebarDisplayed; 
    if (pageSidebarDisplayed) {
        $('#siac-reading-modal-center').addClass('siac-page-sidebar');
        if (persist)
            pycmd("siac-linked-to-page " + pdfDisplayedCurrentPage);
    } else {
        $('#siac-reading-modal-center').removeClass('siac-page-sidebar');
    }
    if (persist) {
        pdfFitToPage();
        pycmd('siac-config-bool pdf.page_sidebar_shown ' + pageSidebarDisplayed);
    }
}
window.updatePageSidebarIfShown = function() {
    if (pdfDisplayed && pageSidebarDisplayed) {
        pycmd("siac-linked-to-page " + pdfDisplayedCurrentPage);
    }
}



window.editorMDInit = function() {
    textEditor = new SimpleMDE({ element: document.getElementById("siac-text-top").children[0],
    indentWithTabs: true,
    autoDownloadFontAwesome: false,
    autosave: { enabled: false },
    placeholder: "",
    status: false,
    tagSize: 4,
    toolbar: ["bold", "italic", "heading", "code", "quote", "unordered-list", "ordered-list", "horizontal-rule", "link"]
});
}

window.modalBgUpdate = function() {
    $("#siac-modal-bg-update .siac-clickable-anchor").addClass('siac-disabled');
    setTimeout(function() {
        $("#siac-modal-bg-update .siac-clickable-anchor").removeClass('siac-disabled');
    }, 1200);
}
//
// helpers
//

window.windowHasSelection = function() {
    return window.getSelection().toString().length;
}