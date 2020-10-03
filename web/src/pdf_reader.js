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

/** TODO: Move all the PDF stuff into some object, e.g. window.pdf = { ... }; */
/** PDF rendering */
window.pdfDisplayed = null;
window.pdfDisplayedViewPort = null;
window.pdfPageRendering = false;
window.pdfDisplayedCurrentPage = null;
window.pdfDisplayedScale = 2.0;
window.pdfHighDPIWasUsed = false;
window.pageNumPending = null;
window.latestRenderTimestamp = null;
window.pdfTOC = null;

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
window.bottomBarTabDisplayed = "marks";
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

window.activeCanvas = function () {
    let c = byId("siac-pdf-canvas");
    if (!c) {
        return null;
    }
    if (c.style.display === 'none') {
        return byId("siac-pdf-canvas_1");
    }
    return c;
};
window.checkTOC = function () {
    if (!pdfDisplayed) { return; }
    let pdf = pdfDisplayed;
    pdf.getOutline().then(function (outline) {
        if (!outline || outline.length === 0) { return Promise.reject(); }
        let dest = outline[0].dest;
        if (Array.isArray(dest)) {
            pdf.getPageIndex(dest[0]).catch((e) => { console.log(e); return Promise.reject(); }).then(function (id) {
                if (id) {
                    byId("siac-toc-btn").style.display = "block";
                }
            });
        } else {
            pdf.getDestination(dest).then(function (d) {
                if (!d) { return null; }
                const ref = d[0];
                return ref;
            }).then(pdf.getPageIndex.bind(pdf)).then(function (id) {
                if (id) {
                    byId("siac-toc-btn").style.display = "block";
                }
            })
        }
    })
};

/** Extract the TOC if possible. */
window.loadTOC = function () {

    if (!pdfDisplayed) {
        return;
    }
    let pdf = pdfDisplayed;
    window.pdfTOC = [];
    pdf.getOutline().then(function (outline) {
        console.log(outline)
        if (outline) {
            let promises = [];
            for (let i = 0; i < outline.length; i++) {
                let dest = outline[i].dest;
                const title = outline[i].title;
                if (Array.isArray(dest)) {
                    promises.push(
                        pdf.getPageIndex(dest).catch((e) => { console.log(e); return Promise.resolve(); }).then(function (id) {
                            if (id) {
                                window.pdfTOC.push({ title: title, page: parseInt(id) + 1 });
                                return Promise.resolve();
                            }
                        }));
                } else {

                    promises.push(
                        pdf.getDestination(dest).then(function (d) {
                            if (!d) { return null; }
                            const ref = d[0];
                            return ref;
                        }).then(pdf.getPageIndex.bind(pdf)).then(function (id) {
                            window.pdfTOC.push({ title: title, page: parseInt(id) + 1 });
                            return Promise.resolve();
                        })
                    );
                }
            }
            return Promise.all(promises);
        }
    }).then(function () {
        let html = "";
        if (pdfTOC && pdfTOC.length) {
            for (var i = 0; i < pdfTOC.length; i++) {
                html += `<div class='siac-toc-item blue-hover' onclick='pdfGotoPg(${pdfTOC[i].page})'>${pdfTOC[i].page}: ${pdfTOC[i].title}</div>`;
            }
            html = `<div style='text-align: center; margin-bottom: 5px;'><b style='font-size: 15px;'>Table of Contents</b></div><div style='overflow: auto; color: lightgrey;'>${html}</div>`;
        }
        byId("siac-toc").innerHTML = html;

    });
};
window.tocBtnClicked = function () {
    if (noteLoading || pdfLoading) {
        return;
    }
    if ($('#siac-toc').is(':visible')) {
        byId('siac-toc').style.display = "none";
    } else {
        byId('siac-toc').style.display = "flex";
        loadTOC();
    }
}

window.pdfFitToPage = function () {
    if (!iframeIsDisplayed) {
        rerenderPDFPage(pdfDisplayedCurrentPage, false, true, false, '', false);
    }
}
window.queueRenderPage = function (num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (pdfPageRendering) {
        pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
    }
}
window.rerenderPDFPage = function (num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    byId("siac-pdf-tooltip").style.display = "none";
    byId("siac-pdf-page-lbl").innerHTML = `${pdfDisplayedCurrentPage} / ${pdfDisplayed.numPages}`;
    pdfLoading = true;
    if (isInitial) {
        pdfLoaderText('Initializing Reader...');
    }

    pdfDisplayed.getPage(num)
        .then(function (page) {

            pdfPageRendering = true;

            var lPage = page;
            var pageTimestamp = new Date().getTime();
            latestRenderTimestamp = pageTimestamp;
            var canvas = pdf_canvas_0;
            if (canvas.style.display !== 'none')
                canvas = pdf_canvas_1;
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
            var ctx = canvas.getContext('2d');
            var renderTask = page.render({
                canvasContext: ctx,
                viewport: viewport,
                transform: window.devicePixelRatio !== 1 ? [window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0] : null,
            });
            if (pageNumPending !== null) {
                rerenderPDFPage(pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                pageNumPending = null;
                return Promise.reject();
            }
            renderTask.promise.then(function () {

                pdfPageRendering = false;
                if (pageNumPending !== null) {
                    rerenderPDFPage(pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                    pageNumPending = null;
                    return Promise.reject();
                } else {

                    if (shouldScrollUp) {
                        canvas.parentElement.scrollTop = 0;
                    }

                    // hide other canvas after render
                    if (canvas.id === 'siac-pdf-canvas')
                        pdf_canvas_1.style.display = "none";
                    else
                        pdf_canvas_0.style.display = "none";
                    canvas.style.display = "inline-block";

                    Highlighting._removeAllHighlights();

                    if (fetchHighlights) {
                        updatePdfDisplayedMarks(true);
                    }
                    if (["Sand", "Peach", "Night", "X1", "X2", "Mud", "Coral", "Moss"].indexOf(pdfColorMode) !== -1) {
                        invertCanvas(ctx);
                    }
                }
                return lPage.getTextContent({ normalizeWhitespace: false, disableCombineTextItems: false });
            }).catch(function () { return Promise.reject(); }).then(function (textContent) {
                if (!textContent || pdfPageRendering) {
                    return Promise.reject();
                }
                if (pageNumPending) {
                    rerenderPDFPage(pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                    pageNumPending = null;
                    return null;
                }
                $("#text-layer").css({ height: canvas.height / window.devicePixelRatio, width: canvas.width / window.devicePixelRatio + 1, left: canvas.offsetLeft }).html('');
                pdfjsLib.renderTextLayer({
                    textContent: textContent,
                    container: byId("text-layer"),
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
                    $('#siac-pdf-loader-wrapper').remove();
                    // setTimeout(function () { refreshCanvas(); }, 3000);
                }
                pdfDisplayedViewPort = viewport;
                if (fetchHighlights) {
                    Highlighting.current = [];
                    pycmd("siac-pdf-page-loaded " + pdfDisplayedCurrentPage);
                } else {
                    Highlighting.displayHighlights();
                }
                if (!pageNumPending && !pdfPageRendering) {

                    if (pagesRead.indexOf(num) !== -1) {
                        byId('siac-pdf-overlay').style.display = 'block';
                        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book"></i>&nbsp; Unread';
                    } else {
                        byId('siac-pdf-overlay').style.display = 'none';
                        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book"></i>&nbsp; Read';
                    }
                    if (fetchHighlights && pdfExtract) {
                        if (pdfExtract[0] > pdfDisplayedCurrentPage || pdfExtract[1] < pdfDisplayedCurrentPage) {
                            $('#siac-pdf-top').addClass("extract");
                        } else {
                            $('#siac-pdf-top').removeClass("extract");
                        }
                    }
                    if (fetchHighlights && pageSidebarDisplayed) {
                        pycmd(`siac-linked-to-page ${pdfDisplayedCurrentPage} ${pdfDisplayed.numPages}`);
                    }
                    setLastReadPage();
                }
            });

        }).catch(function (err) { setTimeout(function () { console.log(err); }); });
}




/**
 * ###########################################
 *  Buttons & related functions
 * ###########################################
 */

window.pdfPageRight = function () {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage < pdfDisplayed.numPages) {
        pdfDisplayedCurrentPage++;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}
window.pdfPageLeft = function () {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage > 1) {
        pdfDisplayedCurrentPage--;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
}

window.togglePageRead = function (nid) {

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
        byId('siac-pdf-overlay').style.display = 'block';
        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Unread';
        pycmd("siac-pdf-page-read " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
    } else {
        byId('siac-pdf-overlay').style.display = 'none';
        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i>&nbsp; Read';
        pycmd("siac-pdf-page-unread " + nid + " " + pdfDisplayedCurrentPage + " " + numPagesExtract());
        pagesRead.splice(pagesRead.indexOf(pdfDisplayedCurrentPage), 1);
    }
    updatePdfProgressBar();
}
window.pdfHidePageReadMark = function () {
    byId("siac-pdf-overlay").style.display = "none"; byId("siac-pdf-read-btn").innerHTML = "\u2713&nbsp; Read";
}
window.pdfShowPageReadMark = function () {
    byId("siac-pdf-overlay").style.display = "block"; byId("siac-pdf-read-btn").innerHTML = "&times; Unread";
}
window.pdfJumpToPage = function (e, inp) {
    if (e.keyCode !== 13) {
        return;
    }
    let p = inp.value;
    p = Math.min(pdfDisplayed.numPages, p);
    pdfDisplayedCurrentPage = p;
    queueRenderPage(pdfDisplayedCurrentPage);
}
window.pdfScaleChange = function (mode) {
    if (mode === "up") {
        pdfDisplayedScale += 0.1;
    } else {
        pdfDisplayedScale -= 0.1;
        pdfDisplayedScale = Math.max(0.1, pdfDisplayedScale);
    }
    queueRenderPage(pdfDisplayedCurrentPage, false, false, false, '', false);
}
window.setAllPagesRead = function () {
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

window.toggleQueue = function () {
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
window.queueSchedBtnClicked = function (btn_el) {
    $('#siac-queue-lbl').hide();
    $('.siac-queue-sched-btn').removeClass("active");
    toggleQueue();
    $(btn_el).addClass("active");
}
window.onQuickSchedBtnClicked = function (elem) {
    if (!$(elem).hasClass("expanded")) {
        pycmd("siac-quick-schedule-fill");
    } else {
        $(elem).toggleClass('expanded');
    }
}
window.setLastReadPage = function () {
    pdfLastReadPages[displayedNoteId] = pdfDisplayedCurrentPage;
}
window.getLastReadPage = function () {
    if (displayedNoteId && displayedNoteId in pdfLastReadPages) {
        return pdfLastReadPages[displayedNoteId];
    }
    return null;
}

window.updatePdfProgressBar = function () {
    let percs = Math.floor(pagesRead.length * 10 / numPagesExtract());
    let html = `<span style='margin-right: 10px; display: inline-block; min-width: 35px; font-weight: bold; color: lightgrey;'>${Math.trunc(pagesRead.length * 100 / numPagesExtract())} %</span>`;
    for (var c = 0; c < 10; c++) {
        if (c < percs) {
            html += `<div class='siac-prog-sq-filled'></div>`;
        } else {
            html += `<div class='siac-prog-sq'></div>`;
        }
    }
    byId("siac-prog-bar-wr").innerHTML = html;
    if (bottomBarTabDisplayed === 'pages') {
        pycmd(`siac-pdf-show-bottom-tab ${displayedNoteId} pages`);
    }
}

/** Returns the number of pages for the currently loaded PDF. If the PDF is an extract, it will only 
 *  return the number of pages in the extract's range.
 */
window.numPagesExtract = function () {
    if (!pdfExtract) {
        return pdfDisplayed.numPages;
    }
    return pdfExtract[1] - pdfExtract[0] + 1;
}

window.markReadUpToCurrent = function () {
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


/**
 * ###########################################
 *  Pomodoro timer
 * ###########################################
 */


window._startTimer = function (elementToUpdateId) {
    if (readingTimer) { clearInterval(readingTimer); }
    readingTimer = setInterval(function () {
        remainingSeconds--;
        byId(elementToUpdateId).innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
        if (remainingSeconds <= 0) {
            clearInterval(readingTimer);
            remainingSeconds = 1800;
            $('#siac-timer-play-btn').html("Start").addClass("inactive");
            $('.siac-timer-btn').removeClass('active');
            $('.siac-timer-btn').eq(4).addClass('active');
            byId(elementToUpdateId).innerHTML = "30 : 00";
            pycmd('siac-timer-elapsed ' + $('#siac-reading-modal-top-bar').data('nid'));
            readingTimer = null;
        }
    }, 999);
}
window.toggleTimer = function (timer) {
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
window.resetTimer = function (elem) {
    clearInterval(readingTimer);
    readingTimer = null;
    $('.siac-timer-btn').removeClass('active');
    $(elem).addClass('active');
    remainingSeconds = Number(elem.innerHTML) * 60;
    byId("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
    $('#siac-timer-play-btn').addClass("inactive").html("Start");
}
window.startTimer = function (mins) {
    $('.siac-timer-btn').each((i, e) => {
        if (e.innerHTML === mins.toString()) {
            resetTimer(e);
            $('#siac-timer-play-btn').trigger('click');
        }
    });
}
window.escapeRegExp = function (string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


/**
 * Display a short message in bottom right area of the reader.
 */
window.readerNotification = function (html, immediate) {

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
    byId('siac-pdf-br-notify').innerHTML = html;
    byId('siac-pdf-br-notify').style.display = "block";

    window.setTimeout(() => {
        pdfNotification.current = "";
        if (byId('siac-pdf-br-notify')) {
            byId('siac-pdf-br-notify').style.display = "none";
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


/** Change the modal's position between the left and right side. */
window.swapReadingModal = function () {
    let modal = byId("siac-reading-modal");
    if (modal.parentNode.id === "siac-right-side") {
        byId("leftSide").appendChild(modal);
    } else {
        byId("siac-right-side").appendChild(modal);
    }
}

/**
 * When a new page is rendered, the marks display at the top has to be updated, as well as the "Marks" tab in the bottom bar.
 */
window.updatePdfDisplayedMarks = function (rerenderTop) {
    if (pdfDisplayedMarks == null) {
        return;
    }
    if (rerenderTop) {
        let html = "";
        $('.siac-mark-btn-inner').removeClass('active');
        if (pdfDisplayedCurrentPage in pdfDisplayedMarks) {
            for (var i = 0; i < pdfDisplayedMarks[pdfDisplayedCurrentPage].length; i++) {
                switch (pdfDisplayedMarks[pdfDisplayedCurrentPage][i]) {
                    case 1: html += "<div class='siac-pdf-mark-lbl'><i class='fa fa-star'></i>&nbsp; Revisit &nbsp;<b onclick='$(\".siac-mark-btn-inner-1\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-1').first().addClass('active'); break;
                    case 2: html += "<div class='siac-pdf-mark-lbl'><i class='fa fa-star'></i>&nbsp; Hard &nbsp;<b onclick='$(\".siac-mark-btn-inner-2\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-2').first().addClass('active'); break;
                    case 3: html += "<div class='siac-pdf-mark-lbl'><i class='fa fa-star'></i>&nbsp; More Info &nbsp;<b onclick='$(\".siac-mark-btn-inner-3\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-3').first().addClass('active'); break;
                    case 4: html += "<div class='siac-pdf-mark-lbl'><i class='fa fa-star'></i>&nbsp; More Cards &nbsp;<b onclick='$(\".siac-mark-btn-inner-4\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-4').first().addClass('active'); break;
                    case 5: html += "<div class='siac-pdf-mark-lbl'><i class='fa fa-star'></i>&nbsp; Bookmark &nbsp;<b onclick='$(\".siac-mark-btn-inner-5\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-5').first().addClass('active'); break;
                }
            }
        }
        if (byId("siac-pdf-overlay-top-lbl-wrap"))
            byId("siac-pdf-overlay-top-lbl-wrap").innerHTML = html;
    }
    let w1 = byId("siac-queue-readings-list").offsetWidth;
    let w2 = byId("siac-queue-actions").offsetWidth;
    let w = byId("siac-reading-modal-bottom-bar").clientWidth - w1 - w2 - 100;
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

    if (byId("siac-marks-display")) {
        if (tableHtml.length) {
            byId("siac-marks-display").innerHTML = tableHtml;
        } else {
            byId("siac-marks-display").innerHTML = `<div style='display: flex; flex-direction: column; justify-content: center; height: 80px; width: 135px; text-align: center; color: grey;'>
                    <div class='siac-caps'><i class="fa fa-star-o"></i>&nbsp; No marks</div>
                </div>`;
        }

    }
    onMarkBtnClicked(byId("siac-mark-jump-btn"));

}

/**
 * 'Done' Shortcut activated in qt.
 */
window.doneShortcut = function () {
    if (!pdfLoading && !noteLoading && !modalShown && document.body.classList.contains("siac-reading-modal-displayed")) {
        $('#siac-first-in-queue-btn').trigger("click");
    }
}
/**
 * 'Later' Shortcut activated in qt.
 */
window.laterShortcut = function () {
    if (!pdfLoading && !noteLoading && !modalShown && document.body.classList.contains("siac-reading-modal-displayed") && byId('siac-later-btn')) {
        $('#siac-later-btn').trigger("click");
    }
}
window.jumpLastPageShortcut = function () {
    if (pdfLoading || noteLoading || modalShown || !pdfDisplayed) {
        return;
    }
    pdfDisplayedCurrentPage = pdfDisplayed.numPages;
    queueRenderPage(pdfDisplayedCurrentPage, true);
}
window.jumpFirstPageShortcut = function () {
    if (pdfLoading || noteLoading || modalShown || !pdfDisplayed) {
        return;
    }
    pdfDisplayedCurrentPage = 1;
    queueRenderPage(1, true);
}
window.pdfGotoPg = function (page) {
    if (pdfLoading || noteLoading || modalShown || !pdfDisplayed) {
        return;
    }
    pdfDisplayedCurrentPage = page;
    queueRenderPage(page, true);
}

window.togglePDFSelect = function (elem) {
    if (!elem) {
        elem = byId('siac-pdf-tooltip-toggle');
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
window.onMarkBtnClicked = function (elem) {
    if ($(elem).hasClass("expanded")) {
        if (pdfDisplayedMarks && Object.keys(pdfDisplayedMarks).length > 0) {
            byId("siac-mark-jump-btn-inner").innerHTML = "<b onclick='event.stopPropagation(); jumpToNextMark();' style='vertical-align: middle;'>Jump to Next Mark</b>";
        } else {
            byId("siac-mark-jump-btn-inner").innerHTML = "<b style='vertical-align:middle; color: grey;'>No Marks in PDF</b>";
        }
    }
}
window.jumpToNextMark = function () {
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
window.bringPDFIntoView = function () {
    if ($('#siac-right-side').hasClass("addon-hidden") || $('#switchBtn').is(":visible")) {
        toggleAddon();
    }
}
window.beforeNoteQuickOpen = function () {
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

window.centerTooltip = function () {
    let w = $('#siac-pdf-top').width();
    let h = $('#siac-pdf-top').height();
    let $tt = $('#siac-pdf-tooltip');
    byId("siac-pdf-tooltip-results-area").style.removeProperty('max-height');
    byId("siac-pdf-tooltip").style.removeProperty('max-width');
    $tt.css({ 'top': h / 2 - ($tt.height() / 2), 'left': w / 2 - ($tt.width() / 2) });
}
window.destroyPDF = function () {
    if (pdfDisplayed) {
        pdfDisplayed.destroy();
    }
    pdfDisplayed = null;
}
window.pdfUrlSearch = function (input) {
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
window.showQueueInfobox = function (elem, nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd('siac-queue-info ' + nid);
    document.documentElement.style.setProperty('--ttop', (elem.offsetTop) + 'px');
    if (pdfLoading || noteLoading || modalShown) { return; }

}
window.leaveQueueItem = function (elem) {
    window.setTimeout(function () {
        if (!$('#siac-queue-infobox').is(":hover") && !$('#siac-queue-readings-list .siac-link-btn:hover').length) {
            hideQueueInfobox();
        }
    }, 400);
}
window.hideQueueInfobox = function () {
    if (byId("siac-queue-infobox")) {
        byId("siac-queue-infobox").style.display = "none";
        byId("siac-pdf-bottom-tabs").style.visibility = "visible";
    }
}
window.greyoutBottom = function () {
    $('#siac-reading-modal-bottom-bar .siac-link-btn,#siac-reading-modal-bottom-bar .fa,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn,#siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').addClass("siac-disabled");
}
window.ungreyoutBottom = function () {
    $('#siac-reading-modal-bottom-bar .siac-link-btn,#siac-reading-modal-bottom-bar .fa,.siac-queue-sched-btn,#siac-reading-modal-bottom-bar .siac-queue-picker-icn, #siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').removeClass("siac-disabled");
}
window.unhideQueue = function (nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-unhide-pdf-queue " + nid);
}
window.hideQueue = function (nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-hide-pdf-queue " + nid);
}
window.toggleReadingModalBars = function () {
    if (!pdfBarsHidden) {
        byId("siac-reading-modal-top-bar").style.display = "none";
        byId("siac-reading-modal-bottom-bar").style.display = "none";
        pdfBarsHidden = true;
    } else {
        byId("siac-reading-modal-top-bar").style.display = "flex";
        byId("siac-reading-modal-bottom-bar").style.display = "block";
        pdfBarsHidden = false;
    }
}

window.toggleReadingModalFullscreen = function () {
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
window.activateReadingModalFullscreen = function () {
    pdfFullscreen = false;
    pdfBarsHidden = true;
    toggleReadingModalFullscreen();
}
window.onReadingModalClose = function () {
    if (pdfLoading) {
        return;
    }
    displayedNoteId = null;
    $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right").removeClass('siac-reading-modal-displayed');
    $('#siac-left-tab-browse,#siac-left-tab-pdfs,#siac-reading-modal-tabs-left').remove();
    $('#fields').show();
    $("#siac-reading-modal").hide();
    byId('resultsArea').style.display = 'block';
    byId('bottomContainer').style.display = 'block';
    byId('topContainer').style.display = 'flex';
    destroyPDF();
    if (siacYt.player) {
        try {
            siacYt.player.destroy();
        } catch (e) { }
    }
    byId("siac-reading-modal-center").innerHTML = "";
    onWindowResize();
    window.$fields = $('.field');
    if (siacState.searchOnTyping) {
        setSearchOnTyping(true, false);
    }
    pycmd("siac-on-reading-modal-close")
}


window.modalTabsLeftClicked = function (tab, elem) {
    $('#siac-reading-modal-tabs-left .siac-btn').removeClass("active");
    $(elem).addClass("active");
    pycmd("siac-reading-modal-tabs-left-" + tab);
}

window.setPdfTheme = function (theme) {
    let style_tag = byId("siac-pdf-css");
    style_tag.href = style_tag.href.substring(0, style_tag.href.lastIndexOf("/") + 1) + theme;
    pycmd("siac-eval update_config('pdf.theme', '" + theme + "')");
}
window.schedChange = function (slider) {
    byId('siac-sched-prio-val').innerHTML = prioVerbose(slider.value);
}
window.prioVerbose = function (prio) {
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
window.schedChanged = function (slider, nid) {
    $('#siac-quick-sched-btn').removeClass('expanded');
    pycmd("siac-requeue " + nid + " " + slider.value);
}
window.schedSmallChanged = function (slider, nid) {
    pycmd("siac-requeue " + nid + " " + slider.value);
}
window.schedSmallChange = function (slider) {
    byId('siac-slider-small-lbl').innerHTML = slider.value;
}

window.scheduleDialogQuickAction = function () {
    let cmd = $("input[name=sched]:checked").data("pycmd");
    pycmd(`siac-eval index.ui.reading_modal.schedule_note(${cmd})`);
}
window.removeDialogOk = function (nid) {
    if ($("input[name=del]:checked").data("pycmd") == "1") {
        pycmd("siac-remove-from-queue " + nid);
    } else {
        pycmd("siac-delete-current-user-note " + nid);
    }
    modalShown = false;
    $('#siac-rm-greyout').hide();
    $('#siac-schedule-dialog').hide();
}
window.updateSchedule = function () {
    let checked = $("input[name=sched]:checked").data("pycmd");
    if (checked == "4") {
        let td = byId("siac-sched-td-inp").value;
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
        let id = byId("siac-sched-id-inp").value;
        if (!id) { pycmd('siac-notification Value is empty!'); return; }
        pycmd("siac-update-schedule id " + id);
    }
}

/**
 * Show or hide the pdf page sidebar.
 * @param {boolean} persist if the updated value should be sent to the backend 
 */
window.togglePageSidebar = function (persist = true) {
    pageSidebarDisplayed = !pageSidebarDisplayed;
    if (pageSidebarDisplayed) {
        $('#siac-reading-modal-center').addClass('siac-page-sidebar');
        if (persist)
            pycmd(`siac-linked-to-page ${pdfDisplayedCurrentPage} ${pdfDisplayed.numPages}`);
    } else {
        $('#siac-reading-modal-center').removeClass('siac-page-sidebar');
    }
    if (persist) {
        pdfFitToPage();
        pycmd('siac-config-bool pdf.page_sidebar_shown ' + pageSidebarDisplayed);
    }
}
window.updatePageSidebarIfShown = function () {
    if (pdfDisplayed && pageSidebarDisplayed) {
        pycmd(`siac-linked-to-page ${pdfDisplayedCurrentPage} ${pdfDisplayed.numPages}`);
    }
}

window.modalBgUpdate = function () {
    $("#siac-modal-bg-update .siac-link-btn").addClass('siac-disabled');
    setTimeout(function () {
        $("#siac-modal-bg-update .siac-link-btn").removeClass('siac-disabled');
    }, 1200);
}
//
// helpers
//
window.windowHasSelection = function () {
    return window.getSelection().toString().length;
}
window.pdfLoaderText = function (html) {
    try {
        byId("siac-pdf-loader-text").innerHTML = html;
    } catch (e) { }
}