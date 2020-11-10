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



/** PDF search state */
window.pdfSearchOngoing = false;
window.pdfCurrentSearch = {
    query: null,
    lastStart: null,
    lastEnd: null,
    breakOnNext: null
};

/**
 * ###########################################
 *  PDF Search
 * ###########################################
 */

window.onPDFSearchBtnClicked = function(elem) {
    if ($(elem).hasClass("expanded")) {
        $(elem).find("input").focus();
    } else {
        $(elem).find("input").val("");
        pdfCurrentSearch = { query: null, lastEnd: null, lastStart: null };
    }
}
window.onPDFSearchInput = function(value, event) {
    if (event.keyCode === 13 && value && value.trim().length) {
        readerNotification("Searching ...");
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
window.getContents = async function(s = 1, n = 10000) {
    var countPromises = [];
    for (var j = s; j <= pdf.instance.numPages && j <= s + n; j++) {
        var page = pdf.instance.getPage(j);
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
window.resetSearch = function() {
    pdfCurrentSearch.lastStart = null;
    pdfCurrentSearch.lastEnd = null;
}
window.nextPDFSearchResult = async function (dir = "right") {
    if (pdfSearchOngoing) {
        return;
    }
    let value = $("#siac-pdf-search-btn-inner input").first().val().toLowerCase();
    if (pdfCurrentSearch.query === null) {
        pdfCurrentSearch.query = value;
    } else {
        if (value !== pdfCurrentSearch.query || (pdf.page !== pdfCurrentSearch.lastStart && pdfCurrentSearch.lastStart === pdfCurrentSearch.lastEnd)) {
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
                    if (pdf.page === pdfPagesContents[n].page) {
                        readerNotification("Text found on current page", true);
                    } else {
                        readerNotification("Text found on page " + pdfPagesContents[n].page, true);
                    }
                    pdf.page = pdfPagesContents[n].page;
                    queueRenderPage(pdf.page, true, false, false, pdfCurrentSearch.query);
                    pdfCurrentSearch.lastStart = pdf.page;
                    pdfCurrentSearch.lastEnd = pdf.page;
                    shouldBreak = true;
                    found = true;
                    break;
                }
            }
        }
        if (it > Math.round(pdf.instance.numPages / 25.0) + 2) {
            readerNotification("Search aborted, took too long.", true);
            break;
        }
    } while (!shouldBreak);

    if (!found) {
        readerNotification("Text was not found.", true);
        ungreyoutBottom();
    }
    pdfSearchOngoing = false;
}
window.getNextPagesToSearchIn = function(dir) {
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
            s = Math.max(pdf.page - ivl, 1);
            n = Math.min(ivl, pdf.page - s);
        }
        // last search block was up to first page, so start at the end
        else if (lastStart === 1) {
            s = Math.max(pdf.instance.numPages - ivl, 1);
        }
        // page rendered with highlighted search results 
        else if (lastEnd === lastStart && lastEnd !== 1 && pdf.instance.numPages > 1) {
            s = Math.max(lastStart - ivl - 1, 1);
            if (s === 1)
                n = Math.max(0, Math.min(ivl, pdf.page - 3));
            else
                n = Math.min(ivl, pdf.page - s - 1);
        }
        // else
        else {
            s = Math.max(lastStart - ivl, 1);
            if (s === 1)
                n = Math.max(0, lastStart - 2);
        }
        // went from end of pdf to search start again, so stop
        if (lastStart !== null && lastStart > pdf.page && s <= pdf.page) {
            s = pdf.page;
            pdfCurrentSearch.breakOnNext = true;
        }
        // 1 page, so range to look at should be 1 and stop after
        else if (pdf.instance.numPages === 1) {
            n = 0;
            pdfCurrentSearch.breakOnNext = true;
        }

    } else {
        if (lastStart === null) {
            s = pdf.page;
            n = Math.min(pdf.instance.numPages - s, ivl);
        }
        else if (lastEnd === pdf.instance.numPages) {
            s = 1;
            n = Math.min(ivl, pdf.instance.numPages);
        } else {
            s = lastEnd + 1;
            n = Math.min(pdf.instance.numPages - s, ivl);
        }
        if (lastEnd !== null && lastEnd < pdf.page && s + ivl >= pdf.page) {
            n = pdf.page - s;
            pdfCurrentSearch.breakOnNext = true;
        } else if (lastEnd !== null && lastEnd === pdf.instance.numPages && 1 + ivl >= pdf.page) {
            n = pdf.page - s;
            pdfCurrentSearch.breakOnNext = true;
        }

        else if (pdf.instance.numPages === 1) {
            n = 0;
            pdfCurrentSearch.breakOnNext = true;
        }
    }
    if (s === 1 && pdf.instance.numPages <= n) {
        pdfCurrentSearch.breakOnNext = true;
    }
    pdfCurrentSearch.lastStart = s;
    pdfCurrentSearch.lastEnd = Math.min(pdf.instance.numPages, s + n);
    return { s, n };
}
window.highlightPDFText = function(query, n = 0) {
    var tlEls = byId('text-layer').querySelectorAll('span');
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
    byId("siac-pdf-top").scrollTop = Math.max(0, $('#text-layer .tl-highlight').first()[0].parentElement.offsetTop - 50);
}


