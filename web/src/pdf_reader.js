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

/** Tomato timer */
window.tomato = {
    remainingSeconds: 30 * 60,
    readingTimer: null,
    lastStart: 30
};

window.pdf = {
    /** PDF rendering */
    instance: null,
    displayedViewPort: null,
    pageRendering: false,
    page: null,
    displayedScale: 2.0,
    highDPIWasUsed: false,
    pageNumPending: null,
    latestRenderTimestamp: null,
    TOC: null,

    /** PDF meta (pages read, marks, extract) */
    pagesRead: [],
    extract: null,
    extractExclude: null,
    displayedMarks: null,
    displayedMarksTable: null,
    lastReadPages: {},

    notification: {
        queue: [],
        current: ""
    },

    tooltip: {
        lastEvent: null,
    },

};

/** State variables */
window.noteLoading = false;
window.pdfLoading = false;
window.modalShown = false;
window.pdfTooltipEnabled = true;
window.pdfLinksEnabled = false;
window.iframeIsDisplayed = false;
window.pageSidebarDisplayed = true;
window.pdfFullscreen = false;
window.displayedNoteId = null;
window.pdfTextLayerMetaKey = false;
window.bottomBarTabDisplayed = "marks";

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
    if (!pdf.instance) { return; }
    let pdf_i = pdf.instance;
    pdf_i.getOutline().then(function (outline) {
        if (!outline || outline.length === 0) { return Promise.reject(); }
        let dest = outline[0].dest;
        if (Array.isArray(dest)) {
            pdf_i.getPageIndex(dest[0]).catch((e) => { console.log(e); return Promise.reject(); }).then(function (id) {
                if (id != null) {
                    byId("siac-toc-btn").style.display = "block";
                }
            });
        } else {
            pdf_i.getDestination(dest).then(function (d) {
                if (!d) { return null; }
                const ref = d[0];
                return ref;
            }).then(pdf_i.getPageIndex.bind(pdf_i)).then(function (id) {
                if (id != null) {
                    byId("siac-toc-btn").style.display = "block";
                }
            })
        }
    })
};


/** Extract the TOC if possible. 
*/
window.loadTOC = function () {

    if (!pdf.instance) {
        return;
    }
    let pdf_i = pdf.instance;
    if (pdf.TOC && pdf.TOC.length > 0) {
        return;
    }
    window.pdf.TOC = [];
    pdf_i.getOutline().then(function (outline) {
        if (outline) {
            let promises = [];
            for (let i = 0; i < outline.length; i++) {
                let dest = outline[i].dest;
                const title = outline[i].title;
                if (Array.isArray(dest)) {
                    promises.push(
                        pdf_i.getPageIndex(dest[0]).catch((e) => { console.log(e); return Promise.resolve(); }).then(function (id) {
                            if (id != null) {
                                window.pdf.TOC.push({ title: title, page: parseInt(id) + 1 });
                                return Promise.resolve();
                            }
                        }));
                } else {
                    promises.push(
                        pdf_i.getDestination(dest).then(function (d) {
                            if (!d) { return null; }
                            const ref = d[0];
                            return ref;
                        }).then(pdf_i.getPageIndex.bind(pdf_i)).then(function (id) {
                            window.pdf.TOC.push({ title: title, page: parseInt(id) + 1 });
                            return Promise.resolve();
                        })
                    );
                }
                if (outline[i].items && outline[i].items.length > 0) {
                    let items = outline[i].items;
                    for (let j = 0; j < items.length; j++) {
                        let dest = items[j].dest;
                        let title = items[j].title;
                        if (Array.isArray(dest)) {
                            promises.push(
                                pdf_i.getPageIndex(dest[0]).catch((e) => { console.log(e); return Promise.resolve(); }).then(function (id) {
                                    if (id != null) {
                                        if (!window.pdf.TOC[i].children) {
                                            window.pdf.TOC[i].children = [];
                                        }
                                        window.pdf.TOC[i].children.push({ title: title, page: parseInt(id) + 1 });
                                        return Promise.resolve();
                                    }
                                }));
                        } else {
                            promises.push(
                                pdf_i.getDestination(dest).then(function (d) {
                                    if (!d) { return null; }
                                    const ref = d[0];
                                    return ref;
                                }).then(pdf_i.getPageIndex.bind(pdf_i)).then(function (id) {
                                    if (!window.pdf.TOC[i].children) {
                                        window.pdf.TOC[i].children = [];
                                    }
                                    window.pdf.TOC[i].children.push({ title: title, page: parseInt(id) + 1 });
                                    return Promise.resolve();
                                })
                            );
                        }
                     
                    } 
                }
            }
            return Promise.all(promises);
        }
    }).then(function () {
        let html = "<ul style='margin-top: 0;'>";
        if (pdf.TOC && pdf.TOC.length) {
            for (var i = 0; i < pdf.TOC.length; i++) {
                html += `<li class='siac-toc-item blue-hover' onclick='pdfGotoPg(${pdf.TOC[i].page})'><div><div>${pdf.TOC[i].page}:</div><div class='siac_toc_title'>${pdf.TOC[i].title || '&lt;Untitled&gt;'}</div></div>`;
                if (pdf.TOC[i].children && pdf.TOC[i].children.length > 0) {
                    html += `<ul>`;
                    for (var j = 0; j < pdf.TOC[i].children.length; j++) {
                        let c = pdf.TOC[i].children[j];
                        html += `<li class='siac-toc-item blue-hover' onclick='pdfGotoPg(${c.page})'><div><div>${c.page}:</div><div class='siac_toc_title'>${c.title || '&lt;Untitled&gt;'}</div></div></li>`;
                    }
                    html += "</ul>"
                }
                html += "</li>"
            }
            html = `<div class='ta_center siac-note-header mb-10'><b style='font-size: 14px;'>Table of Contents</b></div>
                    <div style='overflow: auto;' class='p-10 fg_lightgrey'>${html}</div>`;
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
    pdfFitToPage();
}

window.pdfFitToPage = function () {
    if (!iframeIsDisplayed) {
        rerenderPDFPage(pdf.page, false, true, false, '', false);
    }
}
window.queueRenderPage = function (num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (pdf.pageRendering) {
        pdf.pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
    }
}
window.setupAnnotations = function (page, viewport, canvas, $annotationLayerDiv) {
    var canvasOffset = $(canvas).offset();

    var promise = page.getAnnotations().then(function (annotationsData) {
        viewport = viewport.clone({
            dontFlip: true
        });

        $annotationLayerDiv.children().remove();

        // Find the largest annotation rectangle, for later use.
        var maxArea = 0.001;
        for (var i = 0; i < annotationsData.length; i++) {
            var data = annotationsData[i];
            var rect = data.rect;
            var width = rect[2] - rect[0];
            var height = rect[3] - rect[1];
            var area = width * height;
            if (area > maxArea) {
                maxArea = area;
            }
        }

        for (var i = 0; i < annotationsData.length; i++) {
            var data = annotationsData[i];
            var rect = data.rect;
            var width = rect[2] - rect[0];
            var height = rect[3] - rect[1];
            var area = width * height;
            // From 0 to 1, what is the ratio from this area to the largest one?
            var indexFactor = area / maxArea;

            if (data.subtype !== 'Link') {
                continue; // We don't handle non-link annotations
            }
            if (!data.url) {
                continue; // We don't handle document-internal links (yet?)
            }

            var element = $("<a>").attr("href", data.url).get(0);

            var rect = data.rect;
            var view = page.view;

            rect = pdfjsLib.Util.normalizeRect([
                rect[0],
                view[3] - rect[1] + view[1],
                rect[2],
                view[3] - rect[3] + view[1]]);

            var width = rect[2] - rect[0];
            var height = rect[3] - rect[1];
            var area = width * height;

            // I have no idea why this magic "12" is necessary, but stuff isn't
            // aligned correctly without it.
            element.style.left = (12 + canvasOffset.left + rect[0]) + 'px';
            element.style.top = (canvasOffset.top + rect[1]) + 'px';
            element.style.width = width + 'px';
            element.style.height = height + 'px';
            element.style.position = 'absolute';

            // This is a kind of lazy way of accomplishing what we're trying to
            // accomplish here:
            //
            // With all of the links set to zIndex 4, we have problems because the
            // annotation data from pdfjsLib doesn't actually just cover the linked
            // text; it gives the maximum bounding rectangle of the link. This covers
            // the entirety of two lines of text if a link spans two lines. While
            // unappealing, this works ok in general use, but it can sometimes
            // overshadow a smaller link that lives entirely within one of those
            // lines.
            //
            // Here, we assign all links a zIndex in the range 4 to 12
            // (siac-rev-overlay is 13), with a higher value the smaller the bounding
            // rectangle of the link. This makes smaller links take higher precedence
            // than larger ones.
            //
            // A better solution would be to somehow get better link/annotation data
            // that just covers the text rather than the weird max bounding box data
            // we have right now.
            element.style.zIndex = 12 - Math.round(8 * indexFactor);

            var transform = viewport.transform;
            var transformStr = 'matrix(' + transform.join(',') + ')';
            element.style.transform = transformStr;
            var transformOriginStr = -rect[0] + 'px ' + -rect[1] + 'px';
            element.style.transformOrigin = transformOriginStr;

            $annotationLayerDiv.append(element);
        }
    });
    return promise;
}

window.refreshPDFPage = function () {
    rerenderPDFPage(pdf.page, false, false, false, '', true);
}

window.rerenderPDFPage = function (num, shouldScrollUp = true, fitToPage = false, isInitial = false, query = '', fetchHighlights = true) {
    if (!pdf.instance || iframeIsDisplayed) {
        return;
    }
    byId("siac-pdf-tooltip").style.display = "none";
    pdfLoading = true;
    if (isInitial) {
        pdfLoaderText('Initializing Reader...');
    }

    pdf.instance.getPage(num)
        .then(function (page) {

            pdf.pageRendering = true;

            var lPage = page;
            var pageTimestamp = new Date().getTime();
            pdf.latestRenderTimestamp = pageTimestamp;
            var canvas = pdf_canvas_0;
            if (canvas.style.display !== 'none')
                canvas = pdf_canvas_1;
            if (fitToPage) {
                var viewport = page.getViewport({ scale: 1.0 });
                pdf.displayedScale = (canvas.parentNode.clientWidth - 23) / viewport.width;
            }
            var viewport = page.getViewport({ scale: pdf.displayedScale });
            canvas.height = viewport.height * window.devicePixelRatio;
            canvas.width = viewport.width * window.devicePixelRatio;
            if (window.devicePixelRatio !== 1 || pdf.highDPIWasUsed) {
                pdf.highDPIWasUsed = true;
                canvas.style.height = viewport.height + "px";
                canvas.style.width = viewport.width + "px";
            }
            var ctx = canvas.getContext('2d');
            var renderTask = page.render({
                canvasContext: ctx,
                viewport: viewport,
                transform: window.devicePixelRatio !== 1 ? [window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0] : null,
            });
            if (pdf.pageNumPending !== null) {
                rerenderPDFPage(pdf.pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                pdf.pageNumPending = null;
                return Promise.reject();
            }
            renderTask.promise.then(function () {
                if (pdfLinksEnabled) {
                    setupAnnotations(page, viewport, canvas, $('.annotationLayer'));
                }

                byId("siac-pdf-page-lbl").innerHTML = `${pdf.page} / ${pdf.instance.numPages}`;
                pdf.pageRendering = false;
                if (pdf.pageNumPending !== null) {
                    rerenderPDFPage(pdf.pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                    pdf.pageNumPending = null;
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
                    if (SIAC.Colors.shouldChangeColors()) {
                        SIAC.Colors.invertCanvas(ctx);
                    }
                }
                return lPage.getTextContent({ normalizeWhitespace: false, disableCombineTextItems: false });
            }).catch(function () { return Promise.reject(); }).then(function (textContent) {
                if (!textContent || pdf.pageRendering) {
                    return Promise.reject();
                }
                if (pdf.pageNumPending) {
                    rerenderPDFPage(pdf.pageNumPending, shouldScrollUp, fitToPage, isInitial, query, fetchHighlights);
                    pdf.pageNumPending = null;
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
                }
                pdf.displayedViewPort = viewport;
                if (fetchHighlights) {
                    Highlighting.current = [];
                    pycmd("siac-pdf-page-loaded " + pdf.page);
                } else {
                    Highlighting.displayHighlights();
                }
                if (!pdf.pageNumPending && !pdf.pageRendering) {

                    if (pdf.pagesRead.indexOf(num) !== -1) {
                        byId('siac-pdf-overlay').style.display = 'block';
                        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book"></i><b>&nbsp; Unread</b>';
                    } else {
                        byId('siac-pdf-overlay').style.display = 'none';
                        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book"></i><b>&nbsp; Read</b>';
                    }
                    // check if current note is an extract 
                    // if yes, and we are outside the extract boundaries, the page is blue'd out
                    if (fetchHighlights) {
                        if (pdf.extract && pdf.extract.length > 0 && (pdf.extract[0] > pdf.page || pdf.extract[1] < pdf.page)) {
                            $('#siac-pdf-top').addClass("extract");
                        } else {
                            // check for pages that should be blue'd-out because there exists another note 
                            // which is an extract that includes that page
                            if (pdf.extractExclude.length > 0) {
                                if (pdf.extractExclude.find(t => t[0] <= pdf.page && t[1] >= pdf.page)) {
                                    $('#siac-pdf-top').addClass("extract");
                                } else {
                                    $('#siac-pdf-top').removeClass("extract");
                                }
                            } else {
                                $('#siac-pdf-top').removeClass("extract");
                            }
                        }
                    }

                    if (fetchHighlights && pageSidebarDisplayed) {
                        pycmd(`siac-linked-to-page ${pdf.page} ${pdf.instance.numPages}`);
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
    if (!pdf.instance || iframeIsDisplayed) {
        return;
    }
    if (pdf.page < pdf.instance.numPages) {
        pdf.page++;
        queueRenderPage(pdf.page);
    }
}
window.pdfPageLeft = function () {
    if (!pdf.instance || iframeIsDisplayed) {
        return;
    }
    if (pdf.page > 1) {
        pdf.page--;
        queueRenderPage(pdf.page);
    }
}
window.pdfToggleReadAndPageRight = function () {
    if (!pdf.instance || iframeIsDisplayed) {
        return;
    }
    if (pdf.instance && pdf.pagesRead.indexOf(pdf.page) === -1 && (!pdf.extract || (pdf.extract[0] <= pdf.page && pdf.extract[1] >= pdf.page))) {
        pycmd("siac-pdf-page-read " + $('#siac-pdf-top').data("pdfid") + " " + pdf.page + " " + numPagesExtract());
        if (pdf.pagesRead.length) { pdf.pagesRead.push(pdf.page); } else { pdf.pagesRead = [pdf.page]; }
        updatePdfProgressBar();
    }
    pdfPageRight();
}

window.togglePageRead = function (nid) {

    // function can be called from pyqt shortcut, so it might be that no PDF is displayed when shortcut is triggered
    if (!pdf.instance) {
        return;
    }

    // don't allow for blue'd out pages in pdf extracts to be marked as read
    if (pdf.extract && (pdf.page < pdf.extract[0] || pdf.page > pdf.extract[1])) {
        return;
    }

    if (!nid) {
        nid = displayedNoteId;
    }

    if (pdf.pagesRead.indexOf(pdf.page) === -1) {
        byId('siac-pdf-overlay').style.display = 'block';
        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i><b>&nbsp; Unread</b>';
        pycmd("siac-pdf-page-read " + nid + " " + pdf.page + " " + numPagesExtract());
        if (pdf.pagesRead.length) { pdf.pagesRead.push(pdf.page); } else { pdf.pagesRead = [pdf.page]; }
    } else {
        byId('siac-pdf-overlay').style.display = 'none';
        byId('siac-pdf-read-btn').innerHTML = '<i class="fa fa-book" aria-hidden="true"></i><b>&nbsp; Read</b>';
        pycmd("siac-pdf-page-unread " + nid + " " + pdf.page + " " + numPagesExtract());
        pdf.pagesRead.splice(pdf.pagesRead.indexOf(pdf.page), 1);
    }
    updatePdfProgressBar();
}
window.pdfHidePageReadMark = function () {
    byId("siac-pdf-overlay").style.display = "none"; byId("siac-pdf-read-btn").innerHTML = "\u2713<b>&nbsp; Read</b>";
}
window.pdfShowPageReadMark = function () {
    byId("siac-pdf-overlay").style.display = "block"; byId("siac-pdf-read-btn").innerHTML = "&times;<b> Unread</b>";
}
window.pdfJumpToPage = function (e, inp) {
    if (e.keyCode !== 13) {
        return;
    }
    let p = inp.value;
    p = Math.min(pdf.instance.numPages, p);
    pdf.page = p;
    queueRenderPage(pdf.page);
}
window.pdfScaleChange = function (mode) {
    if (mode === "up") {
        pdf.displayedScale += 0.1;
    } else {
        pdf.displayedScale -= 0.1;
        pdf.displayedScale = Math.max(0.1, pdf.displayedScale);
    }
    queueRenderPage(pdf.page, false, false, false, '', false);
}
window.setAllPagesRead = function () {
    if (!pdf.extract) {
        pdf.pagesRead = Array.from(Array(pdf.instance.numPages).keys()).map(x => ++x)
    } else {
        pdf.pagesRead = [];
        for (var i = pdf.extract[0]; i <= pdf.extract[1]; i++) {
            pdf.pagesRead.push(i);
        }
    }
    if (pdf.pagesRead.indexOf(pdf.page) !== -1) {
        pdfShowPageReadMark();
    }
}

window.setLastReadPage = function () {
    pdf.lastReadPages[displayedNoteId] = pdf.page;
}
window.getLastReadPage = function () {
    if (displayedNoteId && displayedNoteId in pdf.lastReadPages) {
        return pdf.lastReadPages[displayedNoteId];
    }
    return null;
}

window.updatePdfProgressBar = function () {
    let percs = Math.floor(pdf.pagesRead.length * 10 / numPagesExtract());
    let html = `<span style='margin-right: 10px; display: inline-block; min-width: 35px; font-weight: bold; color: lightgrey;'>${Math.trunc(pdf.pagesRead.length * 100 / numPagesExtract())} %</span>`;
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
    if (!pdf.extract) {
        return pdf.instance.numPages;
    }
    return pdf.extract[1] - pdf.extract[0] + 1;
}

window.markReadUpToCurrent = function () {
    for (var i = 0; i < pdf.page; i++) {
        if (pdf.pagesRead.indexOf(i + 1) === -1) {
            if (!pdf.extract || ((i + 1) >= pdf.extract[0] && (i + 1) <= pdf.extract[1])) {
                pdf.pagesRead.push(i + 1);
            }
        }
    }
    if (pdf.pagesRead.indexOf(pdf.page) !== -1) {
        pdfShowPageReadMark();
    }
}


/**
 * ###########################################
 *  Tomato timer
 * ###########################################
 */


window._startTimer = function () {
    if (tomato.readingTimer) { clearInterval(tomato.readingTimer); }
    tomato.readingTimer = setInterval(function () {
        tomato.remainingSeconds--;
        $('.siac-reading-modal-timer-lbl').text(Math.floor(tomato.remainingSeconds / 60) + " : " + (tomato.remainingSeconds % 60 < 10 ? "0" + tomato.remainingSeconds % 60 : tomato.remainingSeconds % 60));
        if (tomato.remainingSeconds <= 0) {
            clearInterval(tomato.readingTimer);
            tomato.remainingSeconds = tomato.lastStart * 60;
            $('.siac-timer-play-btn').html("<i class='fa fa-play mr-5'></i><b>Start</b>").addClass("inactive");
            setTimerActive(tomato.lastStart);
            let rs = tomato.remainingSeconds;
            $('.siac-reading-modal-timer-lbl').text(Math.floor(rs / 60) + " : " + (rs % 60 < 10 ? "0" + rs % 60 : rs % 60));
            pycmd('siac-timer-elapsed');
            tomato.readingTimer = null;
        }
    }, 999);
}
window.toggleTimer = function () {
    if ($('.siac-timer-play-btn').first().hasClass('inactive')) {
        $('.siac-timer-play-btn').removeClass("inactive");
        $('.siac-timer-play-btn').html("<i class='fa fa-pause mr-5'></i><b>Pause</b>");
        _startTimer();
    } else {
        clearInterval(tomato.readingTimer);
        tomato.readingTimer = null;
        $('.siac-timer-play-btn').addClass("inactive");
        $('.siac-timer-play-btn').html("<i class='fa fa-play mr-5'></i><b>Start</b>");
    }
}
window.resetTimer = function (elem) {
    clearInterval(tomato.readingTimer);
    tomato.readingTimer = null;
    $('.siac-timer-btn').removeClass('active');
    let period = Number(elem.innerHTML);
    $('.siac-timer-btn.' + period).addClass('active');
    tomato.remainingSeconds = period * 60;
    tomato.lastStart = period;
    let rs = tomato.remainingSeconds;
    $('.siac-reading-modal-timer-lbl').text(Math.floor(rs / 60) + " : " + (rs % 60 < 10 ? "0" + rs % 60 : rs % 60));
    $('.siac-timer-play-btn').addClass("inactive").html("<i class='fa fa-play mr-5'></i><b>Start</b>");
}
/**
 * Called from the timer elapsed popup dialog. 
 */
window.startTimer = function (mins) {
    resetTimer($('.siac-timer-btn.' + mins).get(0));
    $('.siac-timer-play-btn').first().trigger('click');
}
window.setTimerActive = function (min) {
    $('.siac-timer-btn').removeClass('active');
    $('.siac-timer-btn.' + min).addClass('active');
}
window.escapeRegExp = function (string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


/**
 * Display a short message in bottom right area of the reader.
 */
window.readerNotification = function (html, immediate) {

    if (!html) { return; }
    if (!immediate && pdf.notification.current != "") {
        if (pdf.notification.queue.length > 0) {
            if (html === pdf.notification.queue[pdf.notification.queue.length - 1]) {
                return;
            }
        } else if (pdf.notification.current === html) {
            return;
        }
        pdf.notification.queue.push(html);
        return;
    }
    pdf.notification.current = html;
    byId('siac-pdf-br-notify').innerHTML = html;
    byId('siac-pdf-br-notify').style.display = "block";

    window.setTimeout(() => {
        pdf.notification.current = "";
        if (byId('siac-pdf-br-notify')) {
            byId('siac-pdf-br-notify').style.display = "none";
            if (pdf.notification.queue.length) {
                setTimeout(function () {
                    let next = pdf.notification.queue.shift();
                    readerNotification(next, true);
                }, 800);
            }
        } else {
            pdf.notification.queue = [];
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
    if (pdf.displayedMarks == null) {
        return;
    }
    if (rerenderTop) {
        let html = "";
        $('.siac-mark-btn-inner').removeClass('active');
        if (pdf.page in pdf.displayedMarks) {
            let template = "<div class='siac-pdf-mark-lbl'><span><i class='fa fa-star'></i>&nbsp; -1 &nbsp;</span><b onclick='$(\".siac-mark-btn-inner--2\").trigger(\"click\");'>&times</b></div>";
            for (var i = 0; i < pdf.displayedMarks[pdf.page].length; i++) {
                switch (pdf.displayedMarks[pdf.page][i]) {
                    case 1: html += template.replace("-1", "Revisit").replace("-2", "1"); $('.siac-mark-btn-inner-1').first().addClass('active'); break;
                    case 2: html += template.replace("-1", "Hard").replace("-2", "2"); $('.siac-mark-btn-inner-2').first().addClass('active'); break;
                    case 3: html += template.replace("-1", "More Info").replace("-2", "3"); $('.siac-mark-btn-inner-3').first().addClass('active'); break;
                    case 4: html += template.replace("-1", "More Cards").replace("-2", "4"); $('.siac-mark-btn-inner-4').first().addClass('active'); break;
                    case 5: html += template.replace("-1", "Bookmark").replace("-2", "5"); $('.siac-mark-btn-inner-5').first().addClass('active'); break;
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
    Object.keys(pdf.displayedMarksTable).forEach(function (key) {
        let name = "";
        switch (key) {
            case "1": name = "Revisit"; break;
            case "2": name = "Hard"; break;
            case "3": name = "More Info"; break;
            case "4": name = "More Cards"; break;
            case "5": name = "Bookmark"; break;
        }
        let pages = "";

        for (var i = 0; i < pdf.displayedMarksTable[key].length; i++) {
            pages += "<span class='siac-page-mark-link'>" + pdf.displayedMarksTable[key][i] + "</span>, ";
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
    if (pdfLoading || noteLoading || modalShown || !pdf.instance) {
        return;
    }
    pdf.page = pdf.instance.numPages;
    queueRenderPage(pdf.page, true);
}
window.jumpFirstPageShortcut = function () {
    if (pdfLoading || noteLoading || modalShown || !pdf.instance) {
        return;
    }
    pdf.page = 1;
    queueRenderPage(1, true);
}
window.pdfGotoPg = function (page) {
    if (pdfLoading || noteLoading || modalShown || !pdf.instance) {
        return;
    }
    pdf.page = page;
    queueRenderPage(page, true);
}

window.togglePDFLinks = function (elem) {
    if (!elem) {
        elem = byId('siac-pdf-links-toggle');
    }
    if (!elem) {
        return;
    }
    pdfLinksEnabled = !pdfLinksEnabled;
    if (pdfLinksEnabled) {
        $(elem).addClass('active');
        $('.annotationLayer').show();
        readerNotification("PDF Links enabled.", true);
    } else {
        $(elem).removeClass('active');
        $('.annotationLayer').hide();
        readerNotification("PDF Links disabled.", true);
    }
    refreshPDFPage();
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
        if (pdf.displayedMarks && Object.keys(pdf.displayedMarks).length > 0) {
            byId("siac-mark-jump-btn-inner").innerHTML = "<b onclick='event.stopPropagation(); jumpToNextMark();' style='vertical-align: middle;'>Jump to Next Mark</b>";
        } else {
            byId("siac-mark-jump-btn-inner").innerHTML = "<b style='vertical-align:middle; color: grey;'>No Marks in PDF</b>";
        }
    }
}
window.jumpToNextMark = function () {
    if (!pdf.instance) {
        return;
    }
    let pages = Object.keys(pdf.displayedMarks);
    for (var i = 0; i < pages.length; i++) {
        if (Number(pages[i]) > pdf.page) {
            pdf.page = Number(pages[i]);
            queueRenderPage(pdf.page, true, false, false);
            return;
        }
    }
    pdf.page = Number(pages[0]);
    queueRenderPage(pdf.page, true, false, false);
}
window.bringPDFIntoView = function () {
    if (document.body.classList.contains("siac-wm-fields")) {
        pycmd('siac-window-mode Addon');
    }
}
window.beforeNoteQuickOpen = function () {
    if (noteLoading || pdfLoading || modalShown) {
        return false;
    }
    if (pdf.instance) {
        noteLoading = true;
        greyoutBottom();
        destroyPDF();
    }
    bringPDFIntoView();
    return true;
}

/**
 * Go back to the pdf tooltip start page (search results).
 */
window.pdfTooltipBack = function() {
    if (pdf.tooltip) {
        renderTooltip(pdf.tooltip.sentences, pdf.tooltip.selection, pdf.tooltip.top, pdf.tooltip.left);
    }
};

window.centerTooltip = function () {
    let w = $('#siac-pdf-top').width();
    let h = $('#siac-pdf-top').height();
    let $tt = $('#siac-pdf-tooltip');
    byId("siac-pdf-tooltip-results-area").style.removeProperty('max-height');
    byId("siac-pdf-tooltip").style.removeProperty('max-width');
    let top = h / 2 - ($tt.height() / 2);
    let left =  w / 2 - ($tt.width() / 2);
    $tt.css({ 'top': top, 'left': left });
    pdf.tooltip.top = top;
    pdf.tooltip.left = left;
}
window.destroyPDF = function () {
    if (pdf.instance) {
        pdf.instance.destroy();
    }
    pdf.instance = null;
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
    $('#siac-reading-modal-bottom-bar .siac-link-btn,#siac-reading-modal-bottom-bar .fa,.siac-bb-btn,.siac-prio-lbl,.siac-queue-btn,#siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').addClass("siac-disabled");
}
window.ungreyoutBottom = function () {
    $('#siac-reading-modal-bottom-bar .siac-link-btn,#siac-reading-modal-bottom-bar .fa,.siac-bb-btn,.siac-prio-lbl,.siac-queue-btn, #siac-reading-modal-bottom-bar .blue-hover, .siac-page-mark-link,.siac-sched-icn').removeClass("siac-disabled");
}
window.unhideQueue = function (nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-unhide-pdf-queue " + nid);
}
window.hideQueue = function (nid) {
    if (pdfLoading || noteLoading || modalShown) { return; }
    pycmd("siac-hide-pdf-queue " + nid);
}
window.toggleBottomBar = function () {
    if (byId('siac-reading-modal-bottom-bar').classList.contains('bottom-hidden')) {
        byId('siac-reading-modal-bottom-bar').classList.remove('bottom-hidden');
        pycmd('siac-config-bool notes.queue.hide_bottom_bar false');
    } else {
        byId('siac-reading-modal-bottom-bar').classList.add('bottom-hidden');
        pycmd('siac-config-bool notes.queue.hide_bottom_bar true');
    }
}
window.toggleTopBar = function () {
    if (byId('siac-reading-modal-top-bar').classList.contains('top-hidden')) {
        byId('siac-reading-modal-top-bar').classList.remove('top-hidden');
        byId('siac-reading-modal-top-btns').classList.remove('top-hidden');
        pycmd('siac-config-bool notes.queue.hide_top_bar false');
    } else {
        byId('siac-reading-modal-top-bar').classList.add('top-hidden');
        byId('siac-reading-modal-top-btns').classList.add('top-hidden');
        pycmd('siac-config-bool notes.queue.hide_top_bar true');
    }
}
window.hideBothBars = function () {
    byId('siac-reading-modal-top-bar').classList.add('top-hidden');
    byId('siac-reading-modal-top-btns').classList.add('top-hidden');
    byId('siac-reading-modal-bottom-bar').classList.add('bottom-hidden');
    pycmd('siac-config-bool notes.queue.hide_top_bar true');
    pycmd('siac-config-bool notes.queue.hide_bottom_bar true');
}
window.toggleBothBars = function () {
    if (byId('siac-reading-modal-bottom-bar').classList.contains('bottom-hidden')) {
        byId('siac-reading-modal-bottom-bar').classList.remove('bottom-hidden');
        byId('siac-reading-modal-top-bar').classList.remove('top-hidden');
        byId('siac-reading-modal-top-btns').classList.remove('top-hidden');
        pycmd('siac-config-bool notes.queue.hide_bottom_bar false');
        pycmd('siac-config-bool notes.queue.hide_top_bar false');
    } else {
        byId('siac-reading-modal-bottom-bar').classList.add('bottom-hidden');
        byId('siac-reading-modal-top-bar').classList.add('top-hidden');
        byId('siac-reading-modal-top-btns').classList.add('top-hidden');
        pycmd('siac-config-bool notes.queue.hide_bottom_bar true');
        pycmd('siac-config-bool notes.queue.hide_top_bar true');
    }
}
window.bothBarsAreHidden = function () {
    return byId('siac-reading-modal-top-bar').classList.contains('top-hidden') &&
        byId('siac-reading-modal-bottom-bar').classList.contains('bottom-hidden');

}
window.topBarIsHidden = function() {
    return byId('siac-reading-modal-top-bar').classList.contains('top-hidden');
}

window.toggleReadingModalFullscreen = function () {
    pdfFullscreen = !pdfFullscreen;
    if (pdfFullscreen) {
        $(document.body).removeClass("siac-fullscreen-show-fields").addClass("siac-fullscreen-show-right");
        if (pdf.instance) {
            pdfFitToPage();
        }
        hideBothBars();
    } else {
        $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right");
        onWindowResize();
        if (pdf.instance) {
            pdfFitToPage();
        }
    }

}
window.activateReadingModalFullscreen = function () {
    pdfFullscreen = false;
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
    SIAC.Fields.cacheFields();
    if (SIAC.State.searchOnTyping) {
        setSearchOnTyping(true, false);
    }
    pycmd("siac-on-reading-modal-close");
}


window.modalTabsLeftClicked = function (tab, elem) {
    $('#siac-reading-modal-tabs-left .siac-btn').removeClass("active");
    $(elem).addClass("active");
    pycmd("siac-reading-modal-tabs-left-" + tab);
}

window.setPdfTheme = function (theme) {
    document.documentElement.style.setProperty('--c-reading-modal-theme-color', theme);
    pycmd("siac-eval update_config('styles.readingModalThemeColor', '" + theme + "')");
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


window.scheduleDialogQuickAction = function () {
    let cmd = $("input[name=sched]:checked").data("pycmd");
    pycmd(`siac-eval Reader.schedule_note(${cmd})`);
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
        if (byId('siac-page-sidebar')) {
            byId('siac-page-sidebar').style.display = 'flex';
        }
        $('#siac-reading-modal-center').addClass('siac-page-sidebar');
        if (persist) {
            if (pdf.instance) {
                pycmd(`siac-linked-to-page ${pdf.page} ${pdf.instance.numPages}`);
            } else {
                pycmd(`siac-linked-to-page -1 -1`);
            }
    
        }
    } else {
        if (byId('siac-page-sidebar')) {
            $('#siac-page-sidebar').hide();
        }
        $('#siac-reading-modal-center').removeClass('siac-page-sidebar');
    }
    if (persist) {
        if (pdf.instance) {
            pdfFitToPage();
        }
        pycmd('siac-config-bool pdf.page_sidebar_shown ' + pageSidebarDisplayed);
    }
}
window.updatePageSidebarIfShown = function () {
    if (pdf.instance && pageSidebarDisplayed) {
        pycmd(`siac-linked-to-page ${pdf.page} ${pdf.instance.numPages}`);
    } else {
        pycmd(`siac-linked-to-page -1 -1`);
    }
}

window.modalBgUpdate = function () {
    $(".siac-link-btn").addClass('siac-disabled');
    setTimeout(function () {
        $(".siac-link-btn").removeClass('siac-disabled');
    }, 1400);
}
//
// helpers
//
window.windowHasSelection = function () {
    return window.getSelection().toString().trim().length > 0;
}
window.pdfLoaderText = function (html) {
    try {
        byId("siac-pdf-loader-text").innerHTML = html;
    } catch (e) { }
}

window.registerButtonWidthObserver = function () {
    if ('ResizeObserver' in self) {
        window.siac_ro = new ResizeObserver(function (entries) {
            let entry = entries[0];
            let el = document.getElementsByClassName('siac-reading-modal-button-bar-wrapper');
            if (!el || el.length === 0) { return; }
            if ($('#siac-page-sidebar').is(':visible')) {
                el[0].classList.add("sidebar")
            } else {
                el[0].classList.remove("sidebar")
            }
            if (entry.contentRect.width <= 560) {
                el[0].classList.add("smaller");
                el[0].classList.add("small");
            }
            else if (entry.contentRect.width <= 690) {
                el[0].classList.remove("smaller");
                el[0].classList.add("small");
            } else {
                el[0].classList.remove("small");
                el[0].classList.remove("smaller");
            }
        });
        siac_ro.observe(byId("siac-pdf-overflow"));
    }
};
