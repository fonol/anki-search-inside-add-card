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


var siacState = {
    selectedDecks : ["-1"],
    timeout : null,
    isFrozen : false,
    searchOnSelection : true,
    searchOnTyping : true,
};

var last = "";
var lastHadResults = false;
var loadingTimer;
var calTimer;
var gridView = false;
var renderImmediately = $renderImmediately$;
var tagHoverCB;
var tagHoverTimeout = 750;
var searchMaskTimer;
var $fields;


function sendContent(event) {
    if ((event && event.repeat) || pdfDisplayed != null || siacState.isFrozen)
        return;
    if (!$fields.text())
        return;
    let html = "";
    showLoading("Typing");
    $fields.each(function(index, elem) {
        html += elem.innerHTML + "\u001f";
    });
    pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
function sendSearchFieldContent() {
    showLoading("Searchbar");
    html = document.getElementById('siac-browser-search-inp').value + "\u001f";
    pycmd('siac-srch-db ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}

function searchFor(text) {
    showLoading("Note Search");
    text += "\u001f";
    pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + text);
}


function updateSelectedDecks(elem) {
    siacState.selectedDecks = [];
    let str = "";
    if (elem)
        $(elem).toggleClass("selected");
    $(".deck-list-item.selected").each(function () {
        if ($(this).data('id')) {
            siacState.selectedDecks.push($(this).data('id'));
            str += " " + $(this).data('id');
        }
    });
    pycmd("deckSelection" + str);
}
function selectAllDecks() {
    $('.deck-list-item').addClass('selected');
    updateSelectedDecks();
}
function unselectAllDecks() {
    $('.deck-list-item').removeClass('selected');
    updateSelectedDecks();
}
function selectDeckWithId(did) {
    $('.deck-list-item').removeClass('selected');
    $(".deck-list-item").each(function () {
        if ($(this).data('id') == did) {
            $(this).addClass("selected");
        }
    });
    updateSelectedDecks();
}
function fixRetMarkWidth(elem) {
    if (elem && elem.parentElement.getElementsByClassName("retMark").length > 0 && elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth.length == 0)
        elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth = elem.offsetWidth + "px";
}
function expandRankingLbl(elem) {
    fixRetMarkWidth(elem);
    if (elem.getElementsByClassName("rankingLblAddInfo")[0].offsetParent === null) {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "inline";
        elem.getElementsByClassName("editedStamp")[0].style.display = "none";
        if (elem.parentElement.getElementsByClassName("siac-susp-lbl").length !== 0) {
            elem.parentElement.getElementsByClassName("siac-susp-lbl")[0].style.display = "none";
        }
    } else {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "none";
        elem.getElementsByClassName("editedStamp")[0].style.display = "inline";
        if (elem.parentElement.getElementsByClassName("siac-susp-lbl").length !== 0) {
            elem.parentElement.getElementsByClassName("siac-susp-lbl")[0].style.display = "block";
        }
    }
}
function expandCard(id, icn) {
    pycmd("siac-note-stats " + id);
}
function pinMouseLeave(elem) {
    $(elem).css('opacity', '0');
}
function pinMouseEnter(elem) {
    $(elem).css('opacity', '1');
}
function cardMouseEnter(elem, nid, mode = "full") {
    if (mode == "full") {
        $(`#btnBar-${nid}`).css('opacity', '1');
    } else {
        $(`#btnBarSmp-${nid}`).css('opacity', '1');
    }
}
function showLoading(source) {
    loadingTimer = setTimeout(function () {
        document.getElementById('searchInfo').innerHTML = `<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>${source}</i></td></tr></table>`;
    }, 1000);
}
function totalOffset(elem) {
    var top = 0, left = 0;
    do {
        top += elem.offsetTop || 0;
        left += elem.offsetLeft || 0;
        elem = elem.offsetParent;
    } while (elem);

    return {
        top: top,
        left: left
    };
}
function cardMouseLeave(elem, nid, mode = "full") {
    setTimeout(function () {
        if (mode == "full") {
            if (!$('#btnBar-' + nid).is(':hover')) {
                $('#btnBar-' + nid).css('opacity', '0');
            }
        } else {
            if (!$('#btnBarSmp-' + nid).is(':hover')) {
                $('#btnBarSmp-' + nid).css('opacity', '0');
            }
        }
    }, 100);
}
function tagMouseEnter(elem) {
    if (!showTagInfoOnHover || !elem || !elem.parentElement)
        return;
    tagHoverCB = setTimeout(function () {
            if (elem && elem.parentElement && elem.parentElement.querySelector(':hover') === elem && !document.getElementById('siac-tag-info-box-' + $(elem).data('stamp'))) {
                pycmd("siac-tag-info " + $(elem).data("stamp") + " " + $(elem).data("name"));
            }
    }, tagHoverTimeout);
}
function showTagInfo(elem) {
    let stamp = $(elem).data("stamp");
    $(elem).css("z-index", "9999");
    if (elem) {
        $("#greyout").show();
    }
    let offset = totalOffset(elem);
    offset.top += 17;
    let existing = document.getElementsByClassName("siac-tag-info-box");
        if (elem.parentElement.id && elem.parentElement.id ===  "tagContainer") {
            offset.top -= document.getElementById("tagContainer").scrollTop;
        } else if (existing.length > 1) {
            if (elem.parentElement.parentElement.parentElement.className.indexOf("siac-tag-info-box-left") >= 0) {
                offset.top -= elem.parentElement.parentElement.parentElement.scrollTop;
            }
        } else if (document.getElementById('cal-info').offsetParent !== null) {
            offset.top -= document.getElementById("cal-info-notes").scrollTop;
        } else {
            offset.top -= document.getElementById("searchResults").scrollTop;
        }
    let id = 'siac-tag-info-box-' + stamp;

    if (offset.left > window.outerWidth - offset.left) {
        offset.left -= $('#siac-tag-info-box-' + stamp).outerWidth();
        offset.left += $(elem).outerWidth() + 2;
    }
    let highestZ = 0;
    for (var i = 0; i < existing.length; i++)  {
        if (Number($(existing[i]).css("z-index")) > highestZ)
            highestZ = Number($(existing[i]).css("z-index"));
    }

    $('#siac-tag-info-box-' + stamp).css("top", offset.top).css("left", offset.left).css("z-index", highestZ + 1);
    if (offset.top > window.outerHeight - offset.top) {
        document.getElementById(id).style.visibility = "hidden";
        document.getElementById(id).style.display = "block";
        let diff = 17;
        if (existing.length > 1)
            diff = 15;
        $('#' + id).css('top', offset.top - $('#' + id).outerHeight() - diff);
        document.getElementById(id).style.visibility = "visible";
    } else {
        document.getElementById(id).style.display = "block";
    }
}

function tagMouseLeave(elem) {
    let stamp = $(elem).data('stamp');
    if ($('#siac-tag-info-box-' + stamp + ":hover").length || $(`.tagLbl[data-stamp='${stamp}']:hover`).length) {
        return;
    }
    let existing = document.getElementsByClassName("siac-tag-info-box");
    let elems_z = Number($(elem).css("z-index"));
    let hovered = $(".siac-tag-info-box:hover").first();
    if (!hovered.length && !$(`.tagLbl[data-stamp]:hover`).length) {
        $('.siac-tag-info-box').remove();
        $('.tagLbl').css("z-index", "4");
        $("#greyout").hide();
        return;
    }
    if (hovered.length){
        let hovered_z = Number(hovered.css("z-index"));
        if (elem.id && hovered_z > elems_z)
            return;

        for(var i = 0; i < existing.length; i++) {
            if (Number($(existing[i]).css("z-index")) > hovered_z) {
                $(existing[i]).remove();
                i--;
            }
        }
    }
    $(`.tagLbl[data-stamp='${stamp}']`).first().css("z-index", "4");
    if (document.getElementById("siac-tag-info-box-"+ stamp))
        $('#siac-tag-info-box-' + stamp).remove();
    if (!existing || existing.length < 1) {
         $("#greyout").hide();
    }

}
function tagInfoBoxClicked(elem) {
    let elems_z_index = Number($(elem).css("z-index"));
    let otherBoxes = document.getElementsByClassName("siac-tag-info-box");
    for (var i = 0; i < otherBoxes.length; i++) {
        if (Number($(otherBoxes[i]).css("z-index")) < elems_z_index) {
            $(otherBoxes[i]).remove();
            i--;
        }
    }
}
function appendToField(fldIx, html) {
    if ($(`.field:eq(${fldIx})`).text().length) { 
        $(`.field:eq(${fldIx})`).append('<br/>' + html);
    } else {
        $(`.field:eq(${fldIx})`).html(html);
    }
    pycmd(`blur:${fldIx}:${currentNoteId}:${$(`.field:eq(${fldIx})`).html()}`);
}
function getSelectionText() {
    if (!siacState.searchOnSelection || siacState.isFrozen)
        return;
    var text = "";
    if (window.getSelection) {
        text = window.getSelection().toString();
    } else if (document.selection && document.selection.type != "Control") {
        text = document.selection.createRange().text;
    }
    if (text.length > 0 && text != "&nbsp;") {
        showLoading("Selection");
        pycmd('fldSlctd ' + siacState.selectedDecks.toString() + ' ~ ' + text);
    }
}
function searchForUserNote(event, elem) {
    if (!elem || elem.value.length === 0) {
       return;
    }
    if (event.keyCode == 13) {
        if (elem.id){
            elem.parentElement.parentElement.style.display = 'none';
        }
        pycmd('siac-user-note-search-inp ' + elem.value);
    } else if (elem.id && (event.key === "Escape" || event.key === "Esc")) {
        elem.parentElement.style.display = 'none';
    } else {
        clearTimeout(searchMaskTimer);
        searchMaskTimer = setTimeout(function() {
            pycmd('siac-user-note-search-inp ' + elem.value);
        }, 800);
    }
}
function switchLeftRight() {
    let flds = document.getElementById("leftSide");
    let addon = document.getElementById("siac-right-side");
    if (flds.parentNode.children[0].id === "leftSide") {
        flds.parentNode.insertBefore(addon, flds);
        $(document.body).addClass("siac-left-right-switched");
        pycmd("siac-switch-left-right true");
    }
    else {
        flds.parentNode.insertBefore(flds, addon);
        $(document.body).removeClass("siac-left-right-switched");
        pycmd("siac-switch-left-right false");
    }
}

function onWindowResize() {
   
        let offsetTop = document.getElementById("topbutsOuter").offsetHeight + 3;
        document.getElementById("outerWr").style.marginTop = offsetTop + "px";
        document.getElementById("outerWr").style.height = `calc(100vh - ${offsetTop}px)`;

    if (!$('#switchBtn').is(":visible")) {
        $('#leftSide').show();
        $('#outerWr').css('display', 'flex').removeClass('onesided');
        document.getElementById('switchBtn').innerHTML = "&#10149; Search";
    }
}
function setHighlighting(elem) {
    let highlight = $(elem).is(":checked") ? "on" : "off";
    pycmd("highlight " + highlight);
}
function setTagSearch(elem) {
    let tagSearch = $(elem).is(":checked") ? "on" : "off";
    pycmd("tagSearch " + tagSearch);
}

function tagClick(elem) {
    if ($(elem).data('tags') && $(elem).data('tags') == $(elem).data('name')) {
        $('#a-modal').show();
        pycmd('siac-render-tags ' + $(elem).data('tags'));
        return;
    }
    let name = $(elem).data('target') || $(elem).data('name');
    $(".siac-tag-info-box").remove();
    $("#greyout").hide();
    pycmd('siac-tag-clicked ' + name);
}
function noteSidebarExpandAll() {
    $('#siac-notes-sidebar .exp').each(function(ix, elem) {
        let icn = $(elem);
        if (icn.text().length) {
            if (icn.text() === '[+]') {
                icn.text('[-]');
                icn.parent().parent().children('ul').toggle();
            }
        }
    });
}
function noteSidebarCollapseAll() {
    $('#siac-notes-sidebar .exp').each(function(ix, elem) {
        let icn = $(elem);
        if (icn.text().length) {
            if (icn.text() === '[-]') {
                icn.text('[+]');
                icn.parent().parent().children('ul').toggle();
            }
        }
    });
}
function deleteNote(id) {
    document.getElementById('siac-del-modal').innerHTML = '<center style="margin: 20px 0 20px 0;">Deleting...</center>';
    setTimeout(function() {
        pycmd("siac-delete-user-note " + id);
    }, 80);
}

function synInputKeyup(event, elem) {
    if (event.keyCode == 13 && elem.value)
        pycmd("saveSynonyms " + elem.value);
}

function synonymSetKeydown(event, elem, index) {
    if (event.keyCode == 13 && elem.innerHTML.length) {
        pycmd("editSynonyms " + index + " " + elem.innerHTML);
        event.preventDefault();
        $(elem).blur();
    }
}
function searchSynset(elem) {
    let set = elem.parentElement.parentElement.children[0].children[0].innerHTML;
    if (set) {
        pycmd("siac-synset-search " + set);
    }
}
function updateFieldToExclude(checkbox, mid, fldOrd) {
    if ($(checkbox).is(':checked')) {
        pycmd("siac-update-field-to-exclude " + mid + " " + fldOrd + " false");
    } else {
        pycmd("siac-update-field-to-exclude " + mid + " " + fldOrd + " true");
    }
}
function updateFieldToHideInResult(checkbox, mid, fldOrd) {
    if ($(checkbox).is(':checked')) {
        pycmd("siac-update-field-to-hide-in-results " + mid + " " + fldOrd + " false");
    } else {
        pycmd("siac-update-field-to-hide-in-results " + mid + " " + fldOrd + " true");
    }
}
function setSearchOnTyping(active) {
    siacState.searchOnTyping = active;
    if (!active)
        $('.field').off('keyup', fieldKeypress);
    else {
        $('.field').on('keyup', fieldKeypress);
        sendContent();
    }
    sendSearchOnTyping();
}
function sendSearchOnTyping() {
    pycmd("searchWhileTyping " + (siacState.searchOnTyping ? "on" : "off"));
}
function sendSearchOnSelection() {
    pycmd("searchOnSelection " + (siacState.searchOnSelection ? "on" : "off"));
}
function fieldKeypress(event) {
    if (event.keyCode != 13 && event.keyCode != 9 && event.keyCode != 32 && event.keyCode != 91 && !(event.keyCode >= 37 && event.keyCode <= 40) && !event.ctrlKey) {
        if (siacState.timeout) {
            clearTimeout(siacState.timeout);
            siacState.timeout = null;
        }
        siacState.timeout = setTimeout(function () {
            sendContent(event);
        }, $del$);
    }
}
function searchMaskKeypress(event) {
    if (event.keyCode === 13)
        sendSearchFieldContent();
}
function pinCard(elem, nid) {
    $('#cW-' + nid).css('padding', '3px 4px 5px 5px');
    $('#cW-' + nid).css('font-size', '9px');
    let info = document.getElementById('cW-' + nid).getElementsByClassName("rankingLblAddInfo")[0];
    let editedStamp = document.getElementById('cW-' + nid).getElementsByClassName("editedStamp")[0];
    $('#cW-' + nid).html('<span>&#128204;</span>');
    document.getElementById('cW-' + nid).appendChild(info);
    document.getElementById('cW-' + nid).appendChild(editedStamp);
    $('#' + nid).parents().first().addClass('pinned');
    updatePinned();
}
function searchCard(elem) {
    let html = $(elem).parent().next().html();
    showLoading("Note Search");
    pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
function searchCardFromFloated(id) {
    let html = document.getElementById(id).innerHTML;
    showLoading("Note Search");
    pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
function edit(nid) {
    pycmd('siac-edit-note ' + nid);
}
function updatePinned() {
    let pincmd = 'siac-pin';
    $('.pinned').each(function (index) {
        pincmd += " " + $(this).children().first().children().first().attr('id').substring(3);
    });
    $('.noteFloating').each(function (index) {
        pincmd += " " + $(this).attr('id').substring(3);
    });
    pycmd(pincmd);
}
function clearSearchResults() {
    let notes_old = document.querySelectorAll("#searchResults .cardWrapper:not(.pinned)");
    for (var i = 0; i < notes_old.length; i++) {
        notes_old[i].remove();
    }
    try {
        document.getElementById("startInfo").remove();
        document.getElementById("greyout").style.display = "none";
    } catch(e) {}

    $('.siac-tag-info-box').remove();
    $('.tagLbl').css("z-index", "999");
}

function setSearchResults(html, infoStr, infoMap, page = 1, pageMax = 1, total = 50, cacheSize = -1, stamp = -1, printTiming = false) {
    let rStart = new Date().getTime();
    clearSearchResults();
    var sr = document.getElementById("searchResults");
    sr.style.overflowY = 'hidden';
    sr.style.paddingRight = '24px';
    sr.innerHTML += html;
    if (html.length > 0)
        sr.scrollTop = 0;
    let c = 1;
    clearTimeout(loadingTimer);
    if (infoMap && lastHadResults && document.getElementById("info-Took")) {
        document.getElementById("info-Took").innerHTML = infoMap["Took"];
        document.getElementById("info-Found").innerHTML = infoMap["Found"];
        document.getElementById("tagContainer").innerHTML = infoMap["Tags"];
        document.getElementById("keywordContainer").innerHTML = infoMap["Keywords"];
    } else {
        document.getElementById('searchInfo').innerHTML = infoStr;
    }
    if (infoMap)
        lastHadResults = true;
    else
        lastHadResults = false;
    if (renderImmediately) {
        if (gridView)
            $('#searchResults .cardWrapper').css("display", "inline-block");
        else
            $('#searchResults .cardWrapper').show();
        sr.style.overflowY = 'auto';
        sr.style.paddingRight = '10px';
        document.getElementById("greyout").style.display = "none";
        displayPagination(page, pageMax, total, html.length > 0, cacheSize);

        if (stamp > -1 && document.getElementById("info-took")) {
            if (printTiming) {
                let took = new Date().getTime() - stamp;
                document.getElementById("info-Took").innerHTML = `<b>${took}</b> ms &nbsp;<b style='cursor: pointer' onclick='pycmd("lastTiming ${new Date().getTime() - rStart}")'>&#9432;</b>`;
            } else {
                document.getElementById("info-Took").innerHTML = `<b>${new Date().getTime() - stamp}</b> ms`;
            }
        }
    }
    else {
        time = gridView ? 100 : 130;
        count = gridView ? 16 : 10;
        if (stamp > -1 && document.getElementById("info-took")) {
            if (printTiming) {
                let took = new Date().getTime() - stamp;
                document.getElementById("info-Took").innerHTML = `<b>${took}</b> ms &nbsp;<b style='cursor: pointer' onclick='pycmd("lastTiming ${new Date().getTime() - rStart}")'>&#9432;</b>`;
            } else {
                document.getElementById("info-Took").innerHTML = `<b>${new Date().getTime() - stamp}</b> ms`;
            }
        }
        function renderLoop() {
            if (gridView)
                $("#nWr-" + (c + (50 * (page - 1)))).fadeIn().css("display", "inline-block");
            else
                $("#nWr-" + (c + (50 * (page - 1)))).fadeIn();
            setTimeout(function () {
                c++;
                if (c < count) {
                    renderLoop();
                } else {
                    if (gridView)
                        $('#searchResults .cardWrapper').css("display", "inline-block");
                    else
                        $('#searchResults .cardWrapper').show();
                    sr.style.overflowY = 'auto';
                    sr.style.paddingRight = '10px';
                    document.getElementById("greyout").style.display = "none";
                }
            }, time);
        }
        renderLoop();
        displayPagination(page, pageMax, total, html.length > 0, cacheSize);
    }
}
function displayPagination(page, pageMax, total, resultsFound, cacheSize) {
    if (cacheSize !== -1) {
        let c_html = "";
        if (cacheSize > 1) {
            c_html += "<div style='display: inline;'>Last Results: &nbsp;</div>"
            for (var i = 0; i < cacheSize - 1; i++) {
                c_html += `<span onclick='pycmd("siac-rerender ${cacheSize - i - 2}")'>${i+1}</span>`;
            }
        }
        document.getElementById("siac-cache-displ").innerHTML = c_html;
    }

    let html = "";
    if (pageMax === 0 || !resultsFound) { 
        document.getElementById("siac-pagination-status").innerHTML = "";
        document.getElementById("siac-pagination-wrapper").innerHTML = "";
        return; 
    }
    if (page === 1 && pageMax == 1) {
        html = "";
    } else {
            html += `<div class='siac-pg-icn' onclick='pycmd("siac-page 1")'>&#171;</div>`;
            html += `<div class='siac-pg-icn' onclick='pycmd("siac-page ${Math.max(page - 1, 1)}")'>&#8249;</div>`;
        let a = 0, b = 0;
        if (page + 5 > pageMax) {
            a = page + 5 - pageMax;
        }
        if (page - 5 <= 0) {
            b = Math.abs(page - 5) + 1;
        }
        for (var i = Math.max(page - 5 - a, 1); i <= page + 5 + b; i++) {
            if (i == page) {
                html += `<div class='siac-pg-icn siac-pg-icn-active' onclick='pycmd("siac-page ${i}")'>${i}</div>`;
            } else if (i <= pageMax){
                    html += `<div class='siac-pg-icn' onclick='pycmd("siac-page ${i}")'>${i}</div>`;
            }
        }
            html += `<div class='siac-pg-icn' onclick='pycmd("siac-page ${Math.min(page + 1, pageMax)}")'>&#8250;</div>`;
            html += `<div class='siac-pg-icn' onclick='pycmd("siac-page ${pageMax}")'>&#187;</div>`;

    }
    document.getElementById("siac-pagination-status").innerHTML = `Showing ${50 * (page - 1) + 1} - ${Math.min(total, 50 * page)} of ${total}`;
    document.getElementById("siac-pagination-wrapper").innerHTML = html;
}

function sendClickedInformation(x, y) {
    let el = document.elementFromPoint(x, y);
    if (el.tagName == "IMG") {
        return "img " + el.src;
    }
    if ((el.tagName == "SPAN" || el.tagName == "DIV" || el.tagName == "MARK") && el.parentElement.className == "cardR") {
        return "note " + el.parentElement.id + " " + el.parentElement.innerHTML;
    }
    if (el.className == "cardR") {
        return "note " + el.id + " " + el.innerHTML;
    }
}
function toggleTooltip(elem) {
    $(elem).children().first().toggle();
}
function toggleFreeze(elem) {
    siacState.isFrozen = !siacState.isFrozen;
    if ($(elem).hasClass('frozen')) {
        $(elem).removeClass('frozen');
    } else {
        $(elem).addClass('frozen');
    }
}
function hideTop() {
    // let height = $('#topContainer').outerHeight(true);
    // let formerHeight =  $("#resultsArea").outerHeight(true);
    $('#topContainer').hide();
    // $('#resultsArea').css('height', `${formerHeight + height}px`).css('border-top', '0px');
    $('#toggleTop').children().first().html('&#10097;');
    pycmd("toggleTop off");
}

function toggleTop(elem) {
    // let height = $('#topContainer').outerHeight(true);
    $('#topContainer').toggle();
    // let formerHeight = $("#resultsArea").outerHeight(true);
    if ($('#topContainer').is(":hidden")) {
        // $('#resultsArea').css('height', `${formerHeight + height}px`).css('border-top', '0px');
        $(elem).children().first().html('&#10097;');
        pycmd("toggleTop off");
    } else {
        // height = $('#topContainer').outerHeight(true);
        // $('#resultsArea').css('height', `${formerHeight - height - 1}px`).css('border-top', '1px solid grey');
        $(elem).children().first().html('&#10096;');
        pycmd("toggleTop on");
    }
}
function toggleGrid(elem) {

    if ($(elem).is(':checked')) {
        pycmd("toggleGrid on");
        gridView = true;
    } else {
        pycmd("toggleGrid off");
        gridView = false;
    }
}
function activateGridView() {
    gridView = true;
    window.setTimeout(function() {
        $('#gridCb').prop("checked", true);
    }, 400);
}

function predefSearch() {
    let e = document.getElementById("predefSearchSelect");
    let search = e.options[e.selectedIndex].value;
    let c = document.getElementById("predefSearchNumberSel");
    let count = c.options[c.selectedIndex].value;
    let decks = siacState.selectedDecks.toString();
    pycmd("predefSearch " + search + " " + count + " " + decks);
}
function sort() {
    let e = document.getElementById("sortSelect");
    let sort = e.options[e.selectedIndex].value;
    pycmd("pSort " + sort);

}
function addFloatingNote(nid) {
    let onedit = $('#' + nid.toString()).hasClass('siac-user-note') ? `pycmd("siac-edit-user-note ${nid}")`  : `edit(${nid})`;
    let content = document.getElementById(nid).innerHTML;
    $('#cW-' + nid).parent().parent().remove();
    let btnBar = `<div class='floatingBtnBar'>
        <div class="floatingBtnBarItem" onclick='${onedit}'>Edit</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" onclick='searchCardFromFloated("nFC-${nid}")'>Search</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" id='rem-${nid}' onclick='document.getElementById("nF-${nid}").outerHTML = ""; updatePinned();'><span>&#10006;&nbsp;&nbsp;</span></div>
    </div>`;
    let floatingNote = `<div id="nF-${nid}" class='noteFloating'>
            <div id="nFH-${nid}" class='noteFloatingHeader' onmousedown='dragElement(this.parentElement, "nFH-${nid}")'>&nbsp;${btnBar}</div>
            <div id="nFC-${nid}" class='noteFloatingContent'>${content}</div>
                </div>
            `;
    if ($('.field').length > 8)
        $('.field').first().after(floatingNote);
    else
        $('.field').last().after(floatingNote);
    dragElement(document.getElementById("nF-" + nid), `nFH-${nid}`);
    updatePinned();
}
function dragElement(elmnt, headerId, inModal=false) {
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0, lMYSum = 0, lMXSum = 0;
    if (document.getElementById(headerId)) {
        document.getElementById(headerId).onmousedown = dragMouseDown;
    } else {
        elmnt.onmousedown = dragMouseDown;
    }
    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }
    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
        elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
    }
    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}
function toggleAddon() {
    try {
        if (document.getElementById('siac-reading-modal').style.display !== "none" && pdfFullscreen) {
            if ($(document.body).hasClass("siac-fullscreen-show-fields")) {
                $(document.body).removeClass("siac-fullscreen-show-fields").addClass("siac-fullscreen-show-right");
            } else {
                $(document.body).addClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right");
            }
        }
        else {
            if ($('#outerWr').hasClass("onesided")) {
                showSearchPaneOnLeftSide();
                $('#siac-right-side').toggleClass("addon-hidden");
            } else if ($('#switchBtn').is(":visible")) {
                showSearchPaneOnLeftSide();
            } else {
                $('#siac-right-side').toggleClass("addon-hidden");
            }
            pycmd("toggleAll " + ($('#siac-right-side').hasClass("addon-hidden") ? "off" : "on"));
        }
        onWindowResize();
    } catch (e) {
        pycmd("siac-notification Failed to toggle: " + e.message);
    }
}
function showSearchPaneOnLeftSide() {
    if ($('#outerWr').hasClass("onesided")) {
        $('#leftSide').show();
        document.getElementById('switchBtn').innerHTML = "&#10149; Search";
        $('#outerWr').css('display', 'flex').removeClass('onesided');
    } else {
        $('#leftSide').hide();
        $('#siac-right-side').removeClass("addon-hidden");
        document.getElementById('switchBtn').innerHTML = "&#10149; Back";
        $('#outerWr').css('display', 'block').addClass('onesided');
        onWindowResize();
    }
}
function updateSwitchBtn(count) {
    if (!$('#outerWr').hasClass("onesided"))
        document.getElementById('switchBtn').innerHTML = `&#10149; Search (${count})`;
}
function removeNote(nid) {
    $(document.getElementById("cW-" + nid).parentElement.parentElement).remove();
    updatePinned();
}
function getOffset(el) {
    var _x = 0;
    var _y = 0;
    while (el && el.id !== "siac-right-side" && !isNaN(el.offsetLeft) && !isNaN(el.offsetTop)) {
        _x += el.offsetLeft - el.scrollLeft;
        _y += el.offsetTop - el.scrollTop;
        el = el.offsetParent;
    }
    return { top: _y, left: _x };
}
function calBlockMouseEnter(event, elem) {
    calTimer = setTimeout(function () {
        if ($('#cal-row').is(":hover") && event.ctrlKey) {
            displayCalInfo(elem);
            calTimer = null;
        }
    }, 100);
}
function displayCalInfo(elem) {

    let offset = getOffset(elem.children[0]);

    let offsetLeft = offset.left - 153;
    let offsetRight = document.getElementById("siac-second-col-wrapper").clientWidth  - offset.left - 153;
    if (offsetLeft < 0) {
        offsetLeft -= (offset.left - 153);
        document.documentElement.style.setProperty('--tleft', (offset.left) + 'px')
    } else {
        document.documentElement.style.setProperty('--tleft', '50%%');
    }
    if (offsetRight < 0) {
        document.documentElement.style.setProperty('--tleft', (-offsetRight + 153) + 'px')
        offsetLeft += offsetRight;
    }
    $('#cal-info').css("left", offsetLeft + "px").css("top", (offset.top - 275) + "px");
    document.getElementById('cal-info').style.display = "block";
    pycmd("calInfo " + $(elem.children[0]).data("index"));
}

function calMouseLeave() {
    calTimer = setTimeout(function () {
        if (!$('#cal-row').is(":hover") && !$('#cal-info').is(":hover"))
            document.getElementById('cal-info').style.display = "none";
        calTimer = null;
    }, 300);
}
function fieldsBtnClicked() {
    if (siacState.isFrozen) {
        pycmd("siac-notification Results are frozen.");
        return;
    }
    if (!$fields.text()) {
        pycmd("siac-notification Fields are empty.");
        return;
    }
    let html = "";
    showLoading("Typing");
    $fields.each(function(index, elem) {
        html += elem.innerHTML + "\u001f";
    });
    pycmd('siac-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}

function showModalSubpage(html) {
    $('#modalText').hide();
    $('#modal-subpage-inner').html(html);
    document.getElementById('modal-subpage').style.display = "flex";
}
function hideModalSubpage() {
    $('#modal-subpage-inner').html('');
    $('#modal-subpage').hide();
    $('#modalText').show();
}

function showLoader(target, text, voffset) {
    voffset = voffset ? voffset : 0;
    $('#' + target).append(`
    <div id='siac-loader-modal' class='siac-modal-small' contenteditable=false style='position: relative; text-align: center; margin-top: ${voffset}px;'>
        <div> <div class='signal' style='margin-left: auto; margin-right: auto;'></div><br/><div id='siac-loader-text'>${text}</div></div>
    </div>
    `);
}

function toggleSearchbarMode(elem) {
	if (elem.innerHTML === "Mode: Browser") {
	    elem.innerHTML = "Mode: Add-on";
	    pycmd("siac-searchbar-mode Add-on");
	} else {
	    elem.innerHTML = "Mode: Browser";
	    pycmd("siac-searchbar-mode Browser");
	}
}

function globalKeydown(e) {
    if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey) && e.shiftKey && e.keyCode === 78) {
        e.preventDefault();
        if ($('#siac-rd-note-btn').length) {
            $('#siac-rd-note-btn').trigger("click");
        } else {
            pycmd('siac-create-note');
        }
    } else if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey) && e.shiftKey && e.keyCode === 83 && $('#siac-reading-modal-top-bar').is(":visible")) {
       // pycmd("siac-quick-schedule " + $('#siac-reading-modal-top-bar').data('nid'));
    }
    
    
    else if (pdfDisplayed && !$('.field').is(':focus')) {
        pdfViewerKeyup(e);
    }
}

function toggleNoteSidebar(){
    if (document.getElementById("siac-notes-sidebar")) {
        pycmd("siac-hide-note-sidebar");
    } else {
        pycmd("siac-show-note-sidebar");
    }
}
