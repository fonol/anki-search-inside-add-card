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



var pdfImgSel = { canvas: null, context: null, startX: null, endX: null, startY: null, endY: null, cvsOffLeft: null, cvsOffTop: null, mouseIsDown: false, canvasDispl: null };
var remainingSeconds = 30 * 60;
var readingTimer;
var pdfTextLayerMetaKey = false;
var pdfDisplayed;
var pdfDisplayedViewPort;
var pdfPageRendering = false;
var pdfDisplayedCurrentPage;
var pdfDisplayedScale = 2.0;
var pdfHighDPIWasUsed = false;
var pdfColorMode = "Day";
var pageNumPending = null;
var pagesRead = [];
var pdfExtract = null;
var pdfDisplayedMarks = null;
var pdfDisplayedMarksTable = null;
var timestamp;
var noteLoading = false;
var pdfLoading = false;
var modalShown = false;
var pdfTooltipEnabled = true;
var iframeIsDisplayed = false;
var pdfFullscreen = false;
var pdfBarsHidden = false;
var pdfSearchOngoing = false;
var pdfCurrentSearch = {
    query: null,
    lastStart: null,
    lastEnd: null,
    breakOnNext: null
};


function pdfImgMouseUp(event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.mouseIsDown = false;
        drawSquare();
        var pdfC = document.getElementById("siac-pdf-canvas");
        cropSelection(pdfC, pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX, pdfImgSel.endY - pdfImgSel.startY, insertImage);
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
    }
}
function cropSelection(canvasSrc, offsetX, offsetY, width, height, callback) {
    let temp = document.createElement('canvas');
    let tctx = temp.getContext('2d');
    temp.width = width;
    temp.height = height;
    tctx.drawImage(canvasSrc, offsetX * window.devicePixelRatio, offsetY * window.devicePixelRatio, width * window.devicePixelRatio, height * window.devicePixelRatio, 0, 0, temp.width, temp.height);
    callback(temp.toDataURL());
}
function insertImage(data) {
    pycmd("siac-add-image 1 " + data.replace("image/png", ""));
}
function pdfImgMouseDown(event) {
    pdfImgSel.canvasDispl = document.getElementById("siac-pdf-canvas").offsetLeft;
    pdfImgSel.mouseIsDown = true;
    pdfImgSel.cvsOffLeft = $(pdfImgSel.canvas).offset().left;
    pdfImgSel.cvsOffTop = $(pdfImgSel.canvas).offset().top;
    pdfImgSel.startX = pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
    pdfImgSel.startY = pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
    drawSquare();
}
function initImageSelection() {
    if ($('#text-layer').is(":hidden")) {
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
        return;
    }
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
function pdfImgMouseXY(event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
        pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
        drawSquare();
    }
}
function drawSquare() {
    pdfImgSel.context.clearRect(0, 0, pdfImgSel.context.canvas.width, pdfImgSel.context.canvas.height);
    pdfImgSel.context.fillRect(pdfImgSel.startX * window.devicePixelRatio, pdfImgSel.startY * window.devicePixelRatio, Math.abs(pdfImgSel.startX - pdfImgSel.endX) * window.devicePixelRatio, Math.abs(pdfImgSel.startY - pdfImgSel.endY) * window.devicePixelRatio);
    pdfImgSel.context.fillStyle = "yellow";
    pdfImgSel.context.fill();
}
function pdfFitToPage() {
    if (!iframeIsDisplayed) {
        rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
    }
}
function queueRenderPage(num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (pdfPageRendering) {
        pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
    }
}
function rerenderPDFPage(num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
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
            if (["Peach", "Sand"].indexOf(pdfColorMode) !== -1)
                canvas.style.display = "none";
            var ctx = canvas.getContext('2d');
            var pageTimestamp = new Date().getTime();
            timestamp = pageTimestamp;
            var renderTask = page.render({
                canvasContext: ctx,
                viewport: viewport,
                transform: window.devicePixelRatio !== 1 ? [window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0] : null,
                continueCallback: function (cont) {
                    if (timestamp != pageTimestamp) {
                        return;
                    }
                    cont();
                }
            });
            renderTask.promise.then(function () {
                pdfPageRendering = false;
                if (pageNumPending !== null) {
                    rerenderPDFPage(pageNumPending, shouldScrollUp);
                    pageNumPending = null;
                } else {
                    if (["Sand", "Peach"].indexOf(pdfColorMode) !== -1) {
                        invertCanvas(ctx);
                    }
                }
                return lPage.getTextContent({ normalizeWhitespace: true, disableCombineTextItems: false });
            }).then(function (textContent) {
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
                pdfDisplayedViewPort = viewport;
                if (fetchHighlights) {
                    pycmd("siac-pdf-page-loaded " + pdfDisplayedCurrentPage);
                } else {
                    displayHighlights();
                }
            });
            if (shouldScrollUp) {
                canvas.parentElement.scrollTop = 0;
            }
            if (pagesRead.indexOf(num) !== -1) {
                document.getElementById('siac-pdf-overlay').style.display = 'block';
                document.getElementById('siac-pdf-read-btn').innerHTML = '&times; Unread';
            } else {
                document.getElementById('siac-pdf-overlay').style.display = 'none';
                document.getElementById('siac-pdf-read-btn').innerHTML = '\u2713&nbsp; Read';
            }
            if (pdfExtract) {
                if (pdfExtract[0] > pdfDisplayedCurrentPage || pdfExtract[1] < pdfDisplayedCurrentPage) {
                    $('#siac-pdf-top').addClass("extract");
                } else {
                    $('#siac-pdf-top').removeClass("extract");
                }
            }
        });
}
function invertCanvas(ctx) {
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
    ctx.canvas.style.display = "inline-block";
}
function numPagesExtract() {
    if (!pdfExtract) {
        return pdfDisplayed.numPages;
    }
    return pdfExtract[1] - pdfExtract[0] + 1;
}

function togglePageRead(nid) {
    if (pdfExtract && (pdfDisplayedCurrentPage < pdfExtract[0] || pdfDisplayedCurrentPage > pdfExtract[1])) {
        return;
    }
    if (pagesRead.indexOf(pdfDisplayedCurrentPage) === -1) {
        document.getElementById('siac-pdf-overlay').style.display = 'block';
        document.getElementById('siac-pdf-read-btn').innerHTML = '&times; Unread';
        pycmd("siac-pdf-page-read " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
    } else {
        document.getElementById('siac-pdf-overlay').style.display = 'none';
        document.getElementById('siac-pdf-read-btn').innerHTML = '\u2713&nbsp; Read';
        pycmd("siac-pdf-page-unread " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        pagesRead.splice(pagesRead.indexOf(pdfDisplayedCurrentPage), 1);
    }
    updatePdfProgressBar();
}
function updatePdfProgressBar() {
    let percs = Math.floor(pagesRead.length * 10 / numPagesExtract());
    let html = `<span style='margin-right: 10px;'>${Math.trunc(pagesRead.length * 100 / numPagesExtract())} %</span>`;
    for (var c = 0; c < 10; c++) {
        if (c < percs) {
            html += `<div class='siac-prog-sq-filled'></div>`;
        } else {
            html += `<div class='siac-prog-sq'></div>`;
        }
    }
    document.getElementById("siac-prog-bar-wr").innerHTML = html;
}
function pdfHidePageReadMark() {
    document.getElementById("siac-pdf-overlay").style.display = "none"; document.getElementById("siac-pdf-read-btn").innerHTML = "\u2713&nbsp; Read";
}
function pdfShowPageReadMark() {
    document.getElementById("siac-pdf-overlay").style.display = "block"; document.getElementById("siac-pdf-read-btn").innerHTML = "&times; Unread";
}
function pdfJumpToPage(e, inp) {
    if (e.keyCode !== 13) {
        return;
    }
    let p = inp.value;
    p = Math.min(pdfDisplayed.numPages, p);
    pdfDisplayedCurrentPage = p;
    queueRenderPage(pdfDisplayedCurrentPage);
}
function pdfScaleChange(mode) {
    if (mode === "up") {
        pdfDisplayedScale += 0.1;
    } else {
        pdfDisplayedScale -= 0.1;
        pdfDisplayedScale = Math.max(0.1, pdfDisplayedScale);
    }
    queueRenderPage(pdfDisplayedCurrentPage, shouldScrollUp = false, fetchHighlights = false);
}

function pdfPageRight() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage < pdfDisplayed.numPages) {
        pdfDisplayedCurrentPage++;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}
function pdfPageLeft() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage > 1) {
        pdfDisplayedCurrentPage--;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}
function markReadUpToCurrent() {
    for (var i = 0; i < pdfDisplayedCurrentPage; i++) {
        if (pagesRead.indexOf(i + 1) === -1) {
            if (!pdfExtract || ((i+1) >= pdfExtract[0] && (i+1) <= pdfExtract[1])) {
                pagesRead.push(i + 1);
            }
        }
    }
    if (pagesRead.indexOf(pdfDisplayedCurrentPage) !== -1) {
        pdfShowPageReadMark();
    }
}
function setAllPagesRead() {
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
function saveTextNote(nid, remove = true) {
    let html = "";
    try {
        html = tinymce.activeEditor.getContent();
    } catch (e) {
        pycmd("siac-notification Could not save text note for some reason.");
        return;
    } finally {
        if (remove) {
            tinymce.remove();
        }
    }
    showPDFBottomRightNotification("&nbsp;Note saved.&nbsp;", 4000);
    pycmd("siac-update-note-text " + nid + " " + html);
}
function destroyTinyMCE() {
    if (tinymce) {
        try {
            tinymce.remove();
        } catch (e) { }
    }
}

function toggleQueue() {
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
function queueSchedBtnClicked(btn_el) {
    $('#siac-queue-lbl').hide();
    $('.siac-queue-sched-btn').removeClass("active");
    toggleQueue();
    $(btn_el).addClass("active");
}
function afterRemovedFromQueue() {
    toggleQueue();
    $('.siac-queue-sched-btn').first().addClass("active").html('Unqueued');
}
function _startTimer(elementToUpdateId) {
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
function toggleTimer(timer) {
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
function onQuickSchedBtnClicked(elem) {
    if (!$(elem).hasClass("expanded")) {
        pycmd("siac-quick-schedule-fill");
    } else {
        $(elem).toggleClass('expanded');
    }
}
function onPDFSearchBtnClicked(elem) {
    if ($(elem).hasClass("expanded")) {
        $(elem).find("input").focus();
    } else {
        $(elem).find("input").val("");
        pdfCurrentSearch = { query: null, lastEnd: null, lastStart: null };
    }
}
function onPDFSearchInput(value, event) {
    if (event.keyCode === 13 && value && value.trim().length) {
        showPDFBottomRightNotification("Searching ...");
        if (value.toLowerCase() !== pdfCurrentSearch.query) {
            pdfCurrentSearch.lastStart = null;
            pdfCurrentSearch.lastEnd = null;
            pdfCurrentSearch.query = value.toLowerCase();
        }
        setTimeout(function () {
            nextPDFSearchResult();
        }, 10);
    }
}

async function getContents(s = 1, n = 10000) {
    var countPromises = [];
    for (var j = s; j <= pdfDisplayed.numPages && j <= s + n; j++) {
        var page = pdfDisplayed.getPage(j);
        countPromises.push(page.then(function (page) {
            var n = page.pageIndex + 1;
            var txt = "";
            var textContent = page.getTextContent();
            return textContent.then(function (page) {
                for (var i = 0; i < page.items.length; i++) {
                    txt += " " + page.items[i].str;
                }
                return { page: n, text: txt.toLowerCase() };
            });
        }));
    }
    return Promise.all(countPromises).then(function (counts) {
        return counts;
    });
}
function resetSearch() {
    pdfCurrentSearch.lastStart = null;
    pdfCurrentSearch.lastEnd = null;
}
async function nextPDFSearchResult(dir = "right") {
    if (pdfSearchOngoing) {
        return;
    }
    let value = $("#siac-pdf-search-btn-inner input").first().val().toLowerCase();
    if (pdfCurrentSearch.query === null) {
        pdfCurrentSearch.query = value;
    } else {
        if (value !== pdfCurrentSearch.query || (pdfDisplayedCurrentPage !== pdfCurrentSearch.lastStart && pdfCurrentSearch.lastStart === pdfCurrentSearch.lastEnd)) {
            pdfCurrentSearch.lastStart = null;
            pdfCurrentSearch.lastEnd = null;
            pdfCurrentSearch.query = value;
        }
    }
    if (!pdfCurrentSearch.query) {
        return;
    }
    pdfCurrentSearch.breakOnNext = false;
    pdfSearchOngoing = true;
    greyoutBottom();

    var shouldBreak = false;
    var found = false;
    var spl = pdfCurrentSearch.query.toLowerCase().split(" ");
    var it = 0;
    do {
        it++;
        var next = getNextPagesToSearchIn(dir);
        if (dir === "left")
            var pdfPagesContents = (await getContents(next.s, next.n)).reverse();
        else
            var pdfPagesContents = await getContents(next.s, next.n);
        if (pdfPagesContents.length === 0) {
            shouldBreak = true;
        }
        for (var n = 0; n < pdfPagesContents.length; n++) {
            if (shouldBreak)
                break;
            for (var i = 0; i < spl.length; i++) {
                if (pdfPagesContents[n].text.indexOf(spl[i]) !== -1) {
                    if (pdfDisplayedCurrentPage === pdfPagesContents[n].page) {
                        showPDFBottomRightNotification("Text found on current page", true);
                    } else {
                        showPDFBottomRightNotification("Text found on page " + pdfPagesContents[n].page, true);
                    }
                    pdfDisplayedCurrentPage = pdfPagesContents[n].page;
                    queueRenderPage(pdfDisplayedCurrentPage, true, false, false, pdfCurrentSearch.query);
                    pdfCurrentSearch.lastStart = pdfDisplayedCurrentPage;
                    pdfCurrentSearch.lastEnd = pdfDisplayedCurrentPage;
                    shouldBreak = true;
                    found = true;
                    break;
                }
            }
        }
        if (it > Math.round(pdfDisplayed.numPages / 25.0) + 2) {
            showPDFBottomRightNotification("Search aborted, took too long.", true);
            break;
        }
    } while (!shouldBreak);

    if (!found) {
        showPDFBottomRightNotification("Text was not found.", true);
        ungreyoutBottom();
    }
    pdfSearchOngoing = false;

}


function getNextPagesToSearchIn(dir) {
    if (pdfCurrentSearch.breakOnNext) {
        return [];
    }
    let lastStart = pdfCurrentSearch.lastStart;
    let lastEnd = pdfCurrentSearch.lastEnd;
    let ivl = 25;
    let s = -1;
    let n = ivl;

    if (dir === "left") {
        // button or enter just pressed
        if (lastStart === null) {
            s = Math.max(pdfDisplayedCurrentPage - ivl, 1);
            n = Math.min(ivl, pdfDisplayedCurrentPage - s);
        }
        // last search block was up to first page, so start at the end
        else if (lastStart === 1) {
            s = Math.max(pdfDisplayed.numPages - ivl, 1);
        }
        // page rendered with highlighted search results 
        else if (lastEnd === lastStart && lastEnd !== 1 && pdfDisplayed.numPages > 1) {
            s = Math.max(lastStart - ivl - 1, 1);
            if (s === 1)
                n = Math.max(0, Math.min(ivl, pdfDisplayedCurrentPage - 3));
            else
                n = Math.min(ivl, pdfDisplayedCurrentPage - s - 1);
        }
        // else
        else {
            s = Math.max(lastStart - ivl, 1);
            if (s === 1)
                n = Math.max(0, lastStart - 2);
        }
        // went from end of pdf to search start again, so stop
        if (lastStart !== null && lastStart > pdfDisplayedCurrentPage && s <= pdfDisplayedCurrentPage) {
            s = pdfDisplayedCurrentPage;
            pdfCurrentSearch.breakOnNext = true;
        }
        // 1 page, so range to look at should be 1 and stop after
        else if (pdfDisplayed.numPages === 1) {
            n = 0;
            pdfCurrentSearch.breakOnNext = true;
        }

    } else {
        if (lastStart === null) {
            s = pdfDisplayedCurrentPage;
            n = Math.min(pdfDisplayed.numPages - s, ivl);
        }
        else if (lastEnd === pdfDisplayed.numPages) {
            s = 1;
            n = Math.min(ivl, pdfDisplayed.numPages);
        } else {
            s = lastEnd + 1;
            n = Math.min(pdfDisplayed.numPages - s, ivl);
        }
        if (lastEnd !== null && lastEnd < pdfDisplayedCurrentPage && s + ivl >= pdfDisplayedCurrentPage) {
            n = pdfDisplayedCurrentPage - s;
            pdfCurrentSearch.breakOnNext = true;
        } else if (lastEnd !== null && lastEnd === pdfDisplayed.numPages && 1 + ivl >= pdfDisplayedCurrentPage) {
            n = pdfDisplayedCurrentPage - s;
            pdfCurrentSearch.breakOnNext = true;
        }

        else if (pdfDisplayed.numPages === 1) {
            n = 0;
            pdfCurrentSearch.breakOnNext = true;
        }
    }
    if (s === 1 && pdfDisplayed.numPages <= n) {
        pdfCurrentSearch.breakOnNext = true;
    }
    pdfCurrentSearch.lastStart = s;
    pdfCurrentSearch.lastEnd = Math.min(pdfDisplayed.numPages, s + n);
    // showPDFBottomRightNotification(`Searching pages ${s} - ${Math.min(s + n, pdfDisplayed.numPages)}`);
    return { s, n };
}
function highlightPDFText(query, n = 0) {
    var tlEls = document.getElementById('text-layer').querySelectorAll('span');
    if (tlEls.length === 0) {
        if (n < 3)
            setTimeout(function () { highlightPDFText(query, n + 1); }, 200);
        return;
    }
    let spl = query.toLowerCase().split(" ");
    for (var i = 0; i < spl.length; i++) {
        for (var t = 0; t < tlEls.length; t++) {
            if (tlEls[t].innerHTML.toLowerCase().indexOf(spl[i]) !== -1) {
                var regEx = new RegExp(escapeRegExp(spl[i]), "ig");
                tlEls[t].innerHTML = tlEls[t].innerHTML.replace(regEx, "<span class='tl-highlight'>$&</span>");
            }
        }
    }
    document.getElementById("siac-pdf-top").scrollTop = Math.max(0, $('#text-layer .tl-highlight').first()[0].parentElement.offsetTop - 50);
}
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
function resetTimer(elem) {
    clearInterval(readingTimer);
    readingTimer = null;
    $('.siac-timer-btn').removeClass('active');
    $(elem).addClass('active');
    remainingSeconds = Number(elem.innerHTML) * 60;
    document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
    $('#siac-timer-play-btn').addClass("inactive").html("Start");
}
function startTimer(mins) {
    $('.siac-timer-btn').each((i, e) => {
        if (e.innerHTML === mins.toString()) {
            resetTimer(e);
            $('#siac-timer-play-btn').trigger('click');
        }
    });
}
function pdfMouseWheel(event) {
    if (!event.ctrlKey) { return; }
    if (event.deltaY < 0) {
        pdfScaleChange("up");
    }
    else if (event.deltaY > 0) {
        pdfScaleChange("down");
    }
}
function showPDFBottomRightNotification(html, fadeout = false) {
    document.getElementById('siac-pdf-br-notify').innerHTML = html;
    document.getElementById('siac-pdf-br-notify').style.display = "block";
    // $('#siac-pdf-br-notify').html(html).show();
    if (fadeout) {
        window.setTimeout(() => {
            removePDFBottomRightNotification();
        }, 3000);
    }
}
function removePDFBottomRightNotification() {
    $('#siac-pdf-br-notify').hide();
}
function swapReadingModal() {
    let modal = document.getElementById("siac-reading-modal");
    if (modal.parentNode.id === "siac-right-side") {
        document.getElementById("leftSide").appendChild(modal);
    } else {
        document.getElementById("siac-right-side").appendChild(modal);
    }
}
function setPDFColorMode(mode) {
    $('#siac-pdf-color-mode-btn > span').first().text(mode);
    pdfColorMode = mode;
    rerenderPDFPage(pdfDisplayedCurrentPage, false);
    $('#siac-pdf-top').removeClass("siac-pdf-sand siac-pdf-night siac-pdf-peach siac-pdf-day siac-pdf-rose siac-pdf-moss siac-pdf-coral").addClass("siac-pdf-" + pdfColorMode.toLowerCase());
}


/**
 *  executed after keyup in the pdf pane
 */
function pdfKeyup(e) {
    // selected text, no ctrl key -> show tooltip if enabled 
    if (!e.ctrlKey && !e.metaKey && pdfTooltipEnabled && windowHasSelection()) {
        $('#text-layer .tl-highlight').remove();
        let s = window.getSelection();
        let r = s.getRangeAt(0);
        let text = s.toString();
        if (text === " " || text.length > 500) { return; }
        // spans in textlayer have a max height to prevent selection jumping, but here we have to temporarily 
        // disable it, to get the actual bounding client rect
        $('#text-layer > span').css("height", "auto");
        let nodesInSel = nodesInSelection(r);
        let sentences = getSentencesAroundSelection(r, nodesInSel, text);
        if (nodesInSel.length > 1) {
            text = joinTextLayerNodeTexts(nodesInSel, text);
        }
        let rect = r.getBoundingClientRect();
        let prect = document.getElementById("siac-reading-modal").getBoundingClientRect();
        document.getElementById('siac-pdf-tooltip-results-area').innerHTML = 'Searching...';
        document.getElementById('siac-pdf-tooltip-searchbar').value = "";
        let left = rect.left - prect.left;
        if (prect.width - left < 250) {
            left -= 200;
        }
        $('#siac-pdf-tooltip').css({ 'top': (rect.top - prect.top + rect.height) + "px", 'left': left + "px" }).show();
        pycmd("siac-pdf-selection " + text);
        $('#siac-pdf-tooltip').data("sentences", sentences);
        $('#siac-pdf-tooltip').data("selection", text);
        // limit height again to prevent selection jumping
        $('#text-layer > span').css("height", "200px");
    } else if ((e.ctrlKey || e.metaKey) && Highlighting.colorSelected.id > 0 && windowHasSelection()) {
        // selected text, ctrl key pressed -> highlight 
        Highlighting.highlight();
        pdfTextLayerMetaKey = false;
    } else if ((e.ctrlKey || e.metaKey) && Highlighting.colorSelected.id === 0 && !windowHasSelection()) {
        // clicked with ctrl, text insert btn is active -> insert text area at coordinates
        Highlighting.insertText(e);
    }


}



// clicked on the text layer, should
// 1. hide the tooltip if present
// 2. trigger the click on a highlight if it is below the textlayer at the given coords
function textlayerClicked(event, el) {
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


function joinTextLayerNodeTexts(nodes, text) {
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

function nodesInSelection(range) {
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
function getSentencesAroundSelection(range, nodesInSel, selection) {
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
        if (Math.abs(currentNode.clientHeight - height) > 3 || lastOffsetTop - currentNode.offsetTop > height * 1.5) {
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

function sendClozes() {
    let sentences = $('#siac-pdf-tooltip').data("sentences");
    let selection = $('#siac-pdf-tooltip').data("selection");
    pycmd("siac-show-cloze-modal " + selection + "$$$" + sentences.join("$$$"));
}
function generateClozes() {
    let cmd = "";
    $('.siac-cl-row').each(function (i, elem) {
        if ($(elem.children[1].children[0]).is(":checked")) {
            cmd += "$$$" + $(elem.children[0].children[0]).text();
        }
    });
    let pdfPath = $('#siac-pdf-top').data("pdfpath");
    let pdfTitle = $('#siac-pdf-top').data("pdftitle");
    pycmd('siac-generate-clozes $$$' + pdfTitle + "$$$" + pdfPath + "$$$" + pdfDisplayedCurrentPage + cmd);
    $('#siac-pdf-tooltip').hide();
}

function extractPrev(text, extracted, selection) {
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
function extractNext(text, extracted, selection) {
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
function pxToSandScheme(red, green, blue) {
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
function pxToPeachScheme(red, green, blue) {
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
function pxToNightScheme(red, green, blue) {
    if (red >= 160 && green >= 160 && blue >= 160) {
        red = 17; green = 36; blue = 53;
    } else {
        red = red ^ 255;
        green = green ^ 255;
        blue = blue ^ 255;
    }
    return { r: red, g: green, b: blue };
}

function updatePdfDisplayedMarks() {
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
function markClicked(event) {
    if (event.target.className === "siac-page-mark-link") {
        pdfDisplayedCurrentPage = Number(event.target.innerHTML);
        queueRenderPage(pdfDisplayedCurrentPage, true);
    }
}
function pdfViewerKeyup(event) {
    if (event.ctrlKey && (event.keyCode === 32 || event.keyCode === 39)) {
        if (event.shiftKey && pdfDisplayed && pagesRead.indexOf(pdfDisplayedCurrentPage) === -1 && (!pdfExtract || (pdfExtract[0] <= pdfDisplayedCurrentPage && pdfExtract[1] >= pdfDisplayedCurrentPage))) {
            pycmd("siac-pdf-page-read " + $('#siac-pdf-top').data("pdfid") + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
            if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
            updatePdfProgressBar();
        }
        pdfPageRight();
    } else if (event.ctrlKey && event.keyCode === 74) {
        pdfPageRight();
    } else if (event.ctrlKey && (event.keyCode === 37 || event.keyCode === 75)) {
        pdfPageLeft();
    } else if (event.keyCode === 122) {
        toggleReadingModalBars();
    }
}
function pdfTooltipClozeKeyup(event) {
    try {
        if (event.ctrlKey && event.shiftKey && event.keyCode === 67) {
            let text = window.getSelection().toString();
            if (!text || text.length === 0) {
                return;
            }
            let c_text = document.getElementById("siac-pdf-tooltip-results-area").innerHTML;
            for (var i = 1; i < 20; i++) {
                if (c_text.indexOf("{{c" + i + "::") === -1) {
                    c_text = c_text.split(text).join("<span style='color: lightblue;'>{{c" + i + "::" + text + "}}</span>");
                    document.getElementById("siac-pdf-tooltip-results-area").innerHTML = c_text;
                    break;
                }
            }
        }
    } catch (ex) {
        pycmd("siac-notification Something went wrong during clozing:<br> " + ex.message);
    }
}
function togglePDFSelect(elem) {
    pdfTooltipEnabled = !pdfTooltipEnabled;
    if (pdfTooltipEnabled) {
        $(elem).addClass('active');
        showPDFBottomRightNotification("Search on select enabled.", true);
    } else {
        $(elem).removeClass('active');
        showPDFBottomRightNotification("Search on select disabled.", true);
    }
}
function onMarkBtnClicked(elem) {
    if ($(elem).hasClass("expanded")) {
        if (pdfDisplayedMarks && Object.keys(pdfDisplayedMarks).length > 0) {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b onclick='event.stopPropagation(); jumpToNextMark();' style='vertical-align: middle;'>Jump to Next Mark</b>";
        } else {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b style='vertical-align:middle; color: grey;'>No Marks in PDF</b>";
        }
    }
}
function jumpToNextMark() {
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
function bringPDFIntoView() {
    if ($('#siac-right-side').hasClass("addon-hidden") || $('#switchBtn').is(":visible")) {
        toggleAddon();
    }
}
function beforeNoteQuickOpen() {
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

function centerTooltip() {
    let w = $('#siac-pdf-top').width();
    let h = $('#siac-pdf-top').height();
    let $tt = $('#siac-pdf-tooltip');
    $tt.css({ 'top': h / 2 - ($tt.height() / 2), 'left': w / 2 - ($tt.width() / 2) });
}
function destroyPDF() {
    if (pdfDisplayed) {
        pdfDisplayed.destroy();
    }
    pdfDisplayed = null;
}
function pdfUrlSearch(input) {
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
function showQueueInfobox(elem, nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd('siac-queue-info ' + nid);
    document.documentElement.style.setProperty('--ttop', (elem.offsetTop) + 'px');
    if (pdfLoading || noteLoading || modalShown) { return; }

}
function leaveQueueItem(elem) {
    window.setTimeout(function () {
        if (!$('#siac-queue-infobox').is(":hover") && !$('#siac-queue-readings-list .siac-clickable-anchor:hover').length) {
            hideQueueInfobox();
        }
    }, 400);
}
function hideQueueInfobox() {
    if (document.getElementById("siac-queue-infobox")) {
        document.getElementById("siac-queue-infobox").style.display = "none";
        document.getElementById("siac-pdf-bottom-tabs").style.visibility = "visible";
    }
}
function greyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn,#siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').addClass("siac-disabled");
}
function ungreyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn, #siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').removeClass("siac-disabled");
}
function unhideQueue(nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-unhide-pdf-queue " + nid);
}
function hideQueue(nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-hide-pdf-queue " + nid);
}
function toggleReadingModalBars() {
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

function toggleReadingModalFullscreen() {
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
function activateReadingModalFullscreen() {
    pdfFullscreen = false;
    pdfBarsHidden = true;
    toggleReadingModalFullscreen();
}
function onReadingModalClose() {
    if (pdfLoading) {
        return;
    }
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
        setSearchOnTyping(true);
    }
    pycmd("siac-on-reading-modal-close")
}
function tryExtractTextFromTextNote() {
    saveTextNote($('#siac-reading-modal-top-bar').data('nid'), remove = false);
    pycmd("siac-try-copy-text-note");
}

function pdfLeftTabAnkiSearchKeyup(value, event) {
    if (event.keyCode !== 13) {
        return;
    }
    if (value && value.trim().length > 0) {
        pycmd("siac-pdf-left-tab-anki-search " + value);
    }
}
function pdfLeftTabPdfSearchKeyup(value, event) {
    if (event.keyCode !== 13) {
        return;
    }
    if (value && value.trim().length > 0) {
        pycmd("siac-pdf-left-tab-pdf-search " + value);
    }
}
function modalTabsLeftClicked(tab, elem) {
    $('#siac-reading-modal-tabs-left .siac-btn').removeClass("active");
    $(elem).addClass("active");
    pycmd("siac-reading-modal-tabs-left-" + tab);
}

function setPdfTheme(theme) {
    let style_tag = document.getElementById("siac-pdf-css");
    style_tag.href = style_tag.href.substring(0, style_tag.href.lastIndexOf("/") + 1) + theme;
    pycmd("siac-eval update_config('pdf.theme', '" + theme + "')");
}

function schedChange(slider) {
    document.getElementById('siac-sched-prio-val').innerHTML = prioVerbose(slider.value);
}
function prioVerbose(prio) {
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
function schedChanged(slider, nid) {
    $('#siac-quick-sched-btn').removeClass('expanded');
    pycmd("siac-requeue " + nid + " " + slider.value);
}
function schedSmallChanged(slider, nid) {
    pycmd("siac-requeue " + nid + " " + slider.value);
}
function schedSmallChange(slider) {
    document.getElementById('siac-slider-small-lbl').innerHTML = slider.value;
}

function scheduleDialogQuickAction() {
    let cmd = $("input[name=sched]:checked").data("pycmd");
    pycmd(`siac-eval index.ui.reading_modal.schedule_note(${cmd})`);
}
function removeDialogOk() {
    if ($("input[name=del]:checked").data("pycmd") == "1") {
        pycmd("siac-remove-from-queue");
    } else {
        pycmd("siac-delete-current-user-note");
    }
}
function updateSchedule() {
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
//
// helpers
//

function windowHasSelection() {
    return window.getSelection().toString().length;
}