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

window.siacState = {
    selectedDecks : ["-1"],
    timeout : null,
    isFrozen : false,
    searchOnSelection : true,
    searchOnTyping : true,
    keepPositionAtRendering: false
};

window.lastHadResults = false;
window.loadingTimer = null;
window.calTimer = null;
window.gridView = false;
window.tagHoverCB = null;
window.tagHoverTimeout = 750;
window.searchMaskTimer = null;
window.$fields = null;

window.byId = function(id) {
    return document.getElementById(id);
};

window.sendContent = function(event) {
    if ((event && event.repeat) || pdf.instance != null || siacState.isFrozen) {
        return;
    }
    if (!$fields.text()) {
        return;
    }
    let html = "";
    showLoading("Typing");
    $fields.each(function(index, elem) {
        html += elem.innerHTML + "\u001f";
    });
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
};
window.searchCurrentField = function() {
    if (displayedNoteId || siacState.isFrozen) {return;}
    let f = $('.field:focus').first();
    if (!f.length) {return;}
    let t = f.text();
    if (!t || t.trim().length === 0) {return;}
    showLoading("Typing");
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + t);

};
window.sendSearchFieldContent = function() {
    showLoading("Searchbar");
    html = byId('siac-browser-search-inp').value + "\u001f";
    pycmd('siac-r-srch-db ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
window.searchFor = function(text) {
    showLoading("Note Search");
    text += "\u001f";
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + text);
}
window.searchForUserNote = function(event, elem) {
    if (!elem || elem.value.length === 0 || !elem.value.trim()) {
       return;
    }
    if (event.keyCode == 13) {
        if (elem.id !== "siac-sidebar-inp"){
            elem.parentElement.parentElement.style.display = 'none';
        }
        pycmd('siac-r-user-note-search-inp ' + elem.value);
    } else if (elem.id && (event.key === "Escape" || event.key === "Esc")) {
        elem.parentElement.style.display = 'none';
    } else {
        clearTimeout(searchMaskTimer);
        searchMaskTimer = setTimeout(function() {
            pycmd('siac-r-user-note-search-inp ' + elem.value);
        }, 800);
    }
}
window.updateSelectedDecks = function(elem) {
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
window.selectAllDecks = function() {
    $('.deck-list-item').addClass('selected');
    updateSelectedDecks();
}
window.unselectAllDecks = function() {
    $('.deck-list-item').removeClass('selected');
    updateSelectedDecks();
}
window.selectDeckWithId = function(did) {
    $('.deck-list-item').removeClass('selected');
    $(".deck-list-item").each(function () {
        if ($(this).data('id') == did) {
            $(this).addClass("selected");
        }
    });
    updateSelectedDecks();
}
window.selectDeckAndSubdecksWithId = function(did) {
    $('.deck-list-item').removeClass('selected');
    $(`.deck-list-item[data-id=${did}]`).addClass("selected");
    $(`.deck-list-item[data-id=${did}] .deck-list-item`).addClass("selected");
    updateSelectedDecks();
}
window.fixRetMarkWidth = function(elem) {
    if (elem && elem.parentElement.getElementsByClassName("retMark").length > 0 && elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth.length == 0)
        elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth = elem.offsetWidth + "px";
}
window.expandRankingLbl = function(elem) {
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
window.expandCard = function(id, icn) {
    pycmd("siac-note-stats " + id);
}
window.pinMouseLeave = function(elem) {
    $(elem).css('opacity', '0');
}
window.pinMouseEnter = function(elem) {
    $(elem).css('opacity', '1');
}
window.cardMouseEnter = function(elem, nid, mode = "full") {
    if (mode == "full") {
        $(`#btnBar-${nid}`).css('opacity', '1');
    } else {
        $(`#btnBarSmp-${nid}`).css('opacity', '1');
    }
}
window.showLoading = function(source) {
    loadingTimer = setTimeout(function () {
        byId('searchInfo').innerHTML = `<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>${source}</i></td></tr></table>`;
    }, 1000);
}
window.totalOffset = function(elem) {
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
window.cardMouseLeave = function(elem, nid, mode = "full") {
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
window.tagMouseEnter = function(elem) {
    if (!showTagInfoOnHover || !elem || !elem.parentElement || displayedNoteId)
        return;
    tagHoverCB = setTimeout(function () {
            if (elem && elem.parentElement && elem.parentElement.querySelector(':hover') === elem && !byId('siac-tag-info-box-' + $(elem).data('stamp'))) {
                pycmd("siac-tag-info " + $(elem).data("stamp") + " " + $(elem).data("name"));
            }
    }, tagHoverTimeout);
}
window.showTagInfo = function(elem) {
    let stamp = $(elem).data("stamp");
    $(elem).css("z-index", "9999");
    if (elem) {
        $("#greyout").show();
    }
    let offset = totalOffset(elem);
    offset.top += 17;
    let existing = document.getElementsByClassName("siac-tag-info-box");
        if (elem.parentElement.id && elem.parentElement.id ===  "tagContainer") {
            offset.top -= byId("tagContainer").scrollTop;
        } else if (existing.length > 1) {
            if (elem.parentElement.parentElement.parentElement.className.indexOf("siac-tag-info-box-left") >= 0) {
                offset.top -= elem.parentElement.parentElement.parentElement.scrollTop;
            }
        } else if (byId('cal-info').offsetParent !== null) {
            offset.top -= byId("cal-info-notes").scrollTop;
        } else {
            offset.top -= byId("searchResults").scrollTop;
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
        byId(id).style.visibility = "hidden";
        byId(id).style.display = "block";
        let diff = 17;
        if (existing.length > 1)
            diff = 15;
        $('#' + id).css('top', offset.top - $('#' + id).outerHeight() - diff);
        byId(id).style.visibility = "visible";
    } else {
        byId(id).style.display = "block";
    }
}

window.tagMouseLeave = function(elem) {
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
    if (byId("siac-tag-info-box-"+ stamp))
        $('#siac-tag-info-box-' + stamp).remove();
    if (!existing || existing.length < 1) {
         $("#greyout").hide();
    }

}
window.tagInfoBoxClicked = function(elem) {
    let elems_z_index = Number($(elem).css("z-index"));
    let otherBoxes = document.getElementsByClassName("siac-tag-info-box");
    for (var i = 0; i < otherBoxes.length; i++) {
        if (Number($(otherBoxes[i]).css("z-index")) < elems_z_index) {
            $(otherBoxes[i]).remove();
            i--;
        }
    }
}
window.appendToField = function(fldIx, html) {
    if ($(`.field:eq(${fldIx})`).text().length) { 
        $(`.field:eq(${fldIx})`).append('<br/>' + html);
    } else {
        $(`.field:eq(${fldIx})`).html(html);
    }
    pycmd(`blur:${fldIx}:${currentNoteId}:${$(`.field:eq(${fldIx})`).html()}`);
}
window.getSelectionText = function() {
    if (!siacState.searchOnSelection || siacState.isFrozen)
        return;
    var text = "";
    if (window.getSelection) {
        text = window.getSelection().toString();
    } else if (document.selection && document.selection.type != "Control") {
        text = document.selection.createRange().text;
    }
    if (text.trim().length > 0 && text != "&nbsp;") {
        showLoading("Selection");
        pycmd('siac-r-fld-selected ' + siacState.selectedDecks.toString() + ' ~ ' + text);
    }
}

window.searchUserNoteTag = function(e, tag) {
    if (e.ctrlKey || e.metaKey) {
        pycmd('siac-create-note-tag-prefill ' + tag);
    } else {
        pycmd('siac-r-user-note-search-tag ' + tag);
    }
}
window.switchLeftRight = function() {
    let flds = byId("leftSide");
    let addon = byId("siac-right-side");
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

window.onWindowResize = function(fitPdfToPage = true) {
   
    let offsetTop = byId("topbutsOuter").offsetHeight + 3;
    byId("outerWr").style.marginTop = offsetTop + "px";
    byId("outerWr").style.height = `calc(100vh - ${offsetTop}px)`;

    if (!$('#switchBtn').is(":visible")) {
        $('#leftSide').css("display", "flex");
        $('#outerWr').css('display', 'flex').removeClass('onesided');
        byId('switchBtn').innerHTML = "&#10149; Search";
    }
    if (fitPdfToPage && typeof pdf.instance !== "undefined" && pdf.instance) {
        if(this.resizeTimeout) clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(function() {
                if (pdf.instance) {
                    pdfFitToPage();
                }
            }, 300);
    }
}
window.setHighlighting = function(elem) {
    let highlight = $(elem).is(":checked") ? "on" : "off";
    pycmd("siac-toggle-highlight " + highlight);
}
window.setTagSearch = function(elem) {
    let tagSearch = $(elem).is(":checked") ? "on" : "off";
    pycmd("tagSearch " + tagSearch);
}

window.tagClick = function(elem) {
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
window.noteSidebarExpandAll = function() {
    $('#siac-notes-sidebar .exp').each(function(ix, elem) {
        let icn = $(elem);
        if (icn.text().length) {
            if (icn.text() === '[+]') {
                icn.text('[-]');
                icn.parent().parent().children('ul').toggle();
                let t = elem.dataset.t;
                if (_siacSidebar.tab === 1) {
                    if (_siacSidebar.addonTagsExpanded.indexOf(t) === -1) {
                        _siacSidebar.addonTagsExpanded.push(t);
                    }
                } else if (_siacSidebar.tab === 2) {
                    if (_siacSidebar.ankiTagsExpanded.indexOf(t) === -1) {
                        _siacSidebar.ankiTagsExpanded.push(t);
                    }
                }
            }
        }
    });
}
window.noteSidebarCollapseAll = function() {
    $('#siac-notes-sidebar .exp').each(function(ix, elem) {
        let icn = $(elem);
        if (icn.text().length) {
            if (icn.text() === '[-]') {
                icn.text('[+]');
                icn.parent().parent().children('ul').toggle();
                let t = elem.dataset.t;
                if (_siacSidebar.tab === 1) {
                    if (_siacSidebar.addonTagsExpanded.indexOf(t) !== -1) {
                        _siacSidebar.addonTagsExpanded.splice(_siacSidebar.addonTagsExpanded.indexOf(t), 1);
                    }
                } else if (_siacSidebar.tab === 2) {
                    if (_siacSidebar.ankiTagsExpanded.indexOf(t) !== -1) {
                        _siacSidebar.ankiTagsExpanded.splice(_siacSidebar.ankiTagsExpanded.indexOf(t), 1);
                    }
                }
            }
        }
    });
}
window.deleteNote = function(id) {
    byId('siac-del-modal').innerHTML = '<center style="margin: 20px 0 20px 0;">Deleting...</center>';
    setTimeout(function() {
        pycmd("siac-delete-user-note " + id);
    }, 80);
}

window.synInputKeyup = function(event, elem) {
    if (event.keyCode == 13 && elem.value)
        pycmd("siac-save-synonyms " + elem.value);
}

window.synonymSetKeydown = function(event, elem, index) {
    if (event.keyCode == 13 && elem.innerHTML.length) {
        pycmd("siac-edit-synonyms " + index + " " + elem.innerHTML);
        event.preventDefault();
        $(elem).blur();
    }
}
window.searchSynset = function(elem) {
    let set = elem.parentElement.parentElement.children[0].children[0].innerHTML;
    if (set) {
        pycmd("siac-r-synset-search " + set);
    }
}
window.updateFieldToExclude = function(checkbox, mid, fldOrd) {
    if ($(checkbox).is(':checked')) {
        pycmd("siac-update-field-to-exclude " + mid + " " + fldOrd + " false");
    } else {
        pycmd("siac-update-field-to-exclude " + mid + " " + fldOrd + " true");
    }
}
window.updateFieldToHideInResult = function(checkbox, mid, fldOrd) {
    if ($(checkbox).is(':checked')) {
        pycmd("siac-update-field-to-hide-in-results " + mid + " " + fldOrd + " false");
    } else {
        pycmd("siac-update-field-to-hide-in-results " + mid + " " + fldOrd + " true");
    }
}
window.setSearchOnTyping = function(active, trigger=true) {
    siacState.searchOnTyping = active;
    if (!active)
        $('.field').off('keydown.siac', fieldKeypress);
    else {
        $('.field').on('keydown.siac', fieldKeypress);
        if (trigger) {
            sendContent();
        }
    }
    sendSearchOnTyping();
}
window.sendSearchOnTyping = function() {
    pycmd("siac-config-bool searchOnTyping " + siacState.searchOnTyping);
}
window.sendSearchOnSelection = function() {
    pycmd("siac-config-bool searchOnSelection " + siacState.searchOnSelection);
}
window.fieldKeypress = function(event) {
    if (event.keyCode != 13 && event.keyCode != 9 && event.keyCode != 91 && !(event.keyCode >= 37 && event.keyCode <= 40) && !event.ctrlKey && !event.altKey) {
        if (siacState.timeout) {
            clearTimeout(siacState.timeout);
            siacState.timeout = null;
        }
        siacState.timeout = setTimeout(function () {
            sendContent(event);
        }, delayWhileTyping);
    }
    return true;
}
window.searchMaskKeypress = function(event) {
    if (event.keyCode === 13)
        sendSearchFieldContent();
}
window.pinCard = function(elem, nid) {
    $('#cW-' + nid).css('padding', '3px 4px 5px 5px');
    $('#cW-' + nid).css('font-size', '9px');
    let info = byId('cW-' + nid).getElementsByClassName("rankingLblAddInfo")[0];
    let editedStamp = byId('cW-' + nid).getElementsByClassName("editedStamp")[0];
    $('#cW-' + nid).html('<span>&#128204;</span>');
    byId('cW-' + nid).appendChild(info);
    byId('cW-' + nid).appendChild(editedStamp);
    $('#' + nid).parents().first().addClass('pinned');
    updatePinned();
}
window.searchCard = function(elem) {
    let html = $(elem).parent().next().html();
    showLoading("Note Search");
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
window.searchCardFromFloated = function(id) {
    let html = byId(id).innerHTML;
    showLoading("Note Search");
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}
window.edit = function(nid) {
    pycmd('siac-edit-note ' + nid);
}
window.updatePinned = function() {
    let pincmd = 'siac-pin';
    $('.pinned').each(function (index) {
        pincmd += " " + $(this).children().first().children().first().attr('id').substring(3);
    });
    $('.noteFloating').each(function (index) {
        pincmd += " " + $(this).attr('id').substring(3);
    });
    pycmd(pincmd);
}
window.clearSearchResults = function() {
    let notes_old = document.querySelectorAll("#searchResults .cardWrapper:not(.pinned)");
    for (var i = 0; i < notes_old.length; i++) {
        notes_old[i].remove();
    }
    try {
        byId("siac-start-info").remove();
        byId("greyout").style.display = "none";
    } catch(e) {}

    $('.siac-tag-info-box,#siac-results-loader-wrapper').remove();
    $('.tagLbl').css("z-index", "999");
}

window.setSearchResults = function(html, infoStr, infoMap, page = 1, pageMax = 1, total = 50, cacheSize = -1, stamp = -1, printTiming = false, isRerender= false) {
    let rStart = new Date().getTime();
    clearSearchResults();
    var sr = byId("searchResults");
    sr.style.overflowY = 'hidden';
    sr.style.paddingRight = '24px';
    sr.innerHTML += html;
    if (!isRerender && !siacState.keepPositionAtRendering && html.length > 0) {
        sr.scrollTop = 0;
    } else if (siacState.keepPositionAtRendering) {
        siacState.keepPositionAtRendering = false;
    }
    let c = 1;
    clearTimeout(loadingTimer);
    if (infoMap && lastHadResults && byId("info-Took")) {
        byId("info-Took").innerHTML = infoMap["Took"];
        byId("info-Found").innerHTML = infoMap["Found"];
        byId("tagContainer").innerHTML = infoMap["Tags"];
        byId("keywordContainer").innerHTML = infoMap["Keywords"];
    } else {
        byId('searchInfo').innerHTML = infoStr;
    }
  
    if (infoMap)
        lastHadResults = true;
    else
        lastHadResults = false;
    if (!$searchInfo.hasClass('hidden'))
        $searchInfo.get(0).style.display = "flex";
    if (renderImmediately) {
        if (gridView)
            $('#searchResults .cardWrapper').css("display", "inline-block");
        else
            $('#searchResults .cardWrapper').show();
        sr.style.overflowY = 'auto';
        sr.style.paddingRight = '10px';
        byId("greyout").style.display = "none";
        displayPagination(page, pageMax, total, html.length > 0, cacheSize);

        if (stamp > -1 && byId("info-took")) {
            if (printTiming) {
                let took = new Date().getTime() - stamp;
                byId("info-Took").innerHTML = `<b>${took}</b> ms &nbsp;<b style='cursor: pointer' onclick='pycmd("siac-last-timing ${new Date().getTime() - rStart}")'><i class='fa fa-info-circle'></i></b>`;
            } else {
                byId("info-Took").innerHTML = `<b>${new Date().getTime() - stamp}</b> ms`;
            }
        }
    }
    else {
        time = gridView ? 100 : 130;
        count = gridView ? 16 : 10;
        if (stamp > -1 && byId("info-took")) {
            if (printTiming) {
                let took = new Date().getTime() - stamp;
                byId("info-Took").innerHTML = `<b>${took}</b> ms &nbsp;<b style='cursor: pointer' onclick='pycmd("siac-last-timing ${new Date().getTime() - rStart}")'><i class='fa fa-info-circle'></i></b>`;
            } else {
                byId("info-Took").innerHTML = `<b>${new Date().getTime() - stamp}</b> ms`;
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
                    byId("greyout").style.display = "none";
                }
            }, time);
        }
        renderLoop();
        displayPagination(page, pageMax, total, html.length > 0, cacheSize);
    }
}
window.displayPagination = function(page, pageMax, total, resultsFound, cacheSize) {
    if (cacheSize !== -1) {
        let c_html = "";
        if (cacheSize > 1) {
            c_html += `<div onclick='pycmd("siac-rerender ${cacheSize - 2}")' style='display: inline; cursor: pointer;'>Last Results: &nbsp;</div>`;
            for (var i = 0; i < cacheSize - 1; i++) {
                c_html += `<span onclick='pycmd("siac-rerender ${cacheSize - i - 2}")'>${i+1}</span>`;
            }
        }
        byId("siac-cache-displ").innerHTML = c_html;
    }

    let html = "";
    if (pageMax === 0 || !resultsFound) { 
        byId("siac-pagination-status").innerHTML = "";
        byId("siac-pagination-wrapper").innerHTML = "";
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
    byId("siac-pagination-status").innerHTML = `Showing ${50 * (page - 1) + 1} - ${Math.min(total, 50 * page)} of ${total}`;
    byId("siac-pagination-wrapper").innerHTML = html;
}

window.sendClickedInformation = function(x, y) {
    let el = document.elementFromPoint(x, y);
    if (el.tagName == "IMG") {
        return "img " + el.src;
    }
    if ((el.tagName == "SPAN" || el.tagName == "DIV" || el.tagName == "MARK") && el.parentElement.className == "siac-inner-card") {
        return "note " + el.parentElement.id + " " + el.parentElement.innerHTML;
    }
    if (el.className == "siac-inner-card") {
        return "note " + el.id + " " + el.innerHTML;
    }
}
window.toggleTooltip = function(elem) {
    $(elem).children().first().toggle();
}
window.toggleFreeze = function(elem) {
    siacState.isFrozen = !siacState.isFrozen;
    if ($(elem).hasClass('frozen')) {
        $(elem).removeClass('frozen');
    } else {
        $(elem).addClass('frozen');
    }
}
window.hideTop = function() {
    $('#topContainer').hide();
    $('#toggleTop').children().first().html('&#10097;');
    pycmd("toggleTop off");
}

window.toggleTop = function(elem) {
    $('#topContainer').toggle();
    if ($('#topContainer').is(":hidden")) {
        $(elem).children().first().html('&#10097;');
        pycmd("toggleTop off");
    } else {
        $(elem).children().first().html('&#10096;');
        pycmd("toggleTop on");
    }
}
window.toggleGrid = function(elem) {

    if ($(elem).is(':checked')) {
        pycmd("toggleGrid on");
        gridView = true;
    } else {
        pycmd("toggleGrid off");
        gridView = false;
    }
}
window.activateGridView = function() {
    gridView = true;
    window.setTimeout(function() {
        $('#gridCb').prop("checked", true);
    }, 400);
}
/** Predefined searches, activated from the notes sidebar. */
window.predefSearchFromSidebar = function(type) {
    let decks = siacState.selectedDecks.toString();
    // show a loader for the longer-taking searches
    if (["lowestPerf", "highestPerf", "highestRet", "lowestRet"].indexOf(type) !== -1) {
        showSearchLoader("<i class='fa fa-spinner bold mb-10' style='font-size: 24px;' /><br>Computing ...");
        setTimeout(function() {
            pycmd('siac-predef-search ' + type + ' 200 ' + decks);
        }, 250);
    } else {
        pycmd('siac-predef-search ' + type + ' 200 ' + decks);
    }

}
/** Predefined searches, activated from the bottom row. */
window.predefSearch = function() {
    let e       = byId("predefSearchSelect");
    let search  = e.options[e.selectedIndex].value;
    let c       = byId("predefSearchNumberSel");
    let count   = c.options[c.selectedIndex].value;
    let decks   = siacState.selectedDecks.toString();
    // show a loader for the longer-taking searches
    if (["lowestPerf", "highestPerf", "highestRet", "lowestRet"].indexOf(search) !== -1) {
        showSearchLoader("<i class='fa fa-spinner bold mb-10' style='font-size: 24px;' /><br>Computing ...");
        setTimeout(function() {
            pycmd("siac-predef-search " + search + " " + count + " " + decks);
        }, 250);
    } else {
        pycmd("siac-predef-search " + search + " " + count + " " + decks);
    }
}
window.sort = function() {
    let e = byId("sortSelect");
    let sort = e.options[e.selectedIndex].value;
    pycmd("siac-p-sort " + sort);

}
window.toggleAddon = function() {
    try {
        if (byId('siac-reading-modal').style.display !== "none" && pdfFullscreen) {
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
        onWindowResize(false);
    } catch (e) {
        pycmd("siac-notification Failed to toggle: " + e.message);
    }
}
window.showSearchPaneOnLeftSide = function() {
    if ($('#outerWr').hasClass("onesided")) {
        $('#leftSide').show();
        byId('switchBtn').innerHTML = "&#10149; Search";
        $('#outerWr').css('display', 'flex').removeClass('onesided');
    } else {
        $('#leftSide').hide();
        $('#siac-right-side').removeClass("addon-hidden");
        byId('switchBtn').innerHTML = "&#10149; Back";
        $('#outerWr').css('display', 'block').addClass('onesided');
        onWindowResize();
    }
}
window.updateSwitchBtn = function(count) {
    if (!$('#outerWr').hasClass("onesided"))
        byId('switchBtn').innerHTML = `&#10149; Search (${count})`;
}
window.removeNote = function(nid) {
    $(byId("cW-" + nid).parentElement.parentElement).remove();
    updatePinned();
}
window.getOffset = function(el) {
    var _x = 0;
    var _y = 0;
    while (el && el.id !== "siac-right-side" && !isNaN(el.offsetLeft) && !isNaN(el.offsetTop)) {
        _x += el.offsetLeft - el.scrollLeft;
        _y += el.offsetTop - el.scrollTop;
        el = el.offsetParent;
    }
    return { top: _y, left: _x };
}
window.calBlockMouseEnter = function(event, elem) {
    calTimer = setTimeout(function () {
        if ($('#cal-row').is(":hover") && event.ctrlKey) {
            displayCalInfo(elem);
            calTimer = null;
        }
    }, 100);
}
window.displayCalInfo = function(elem) {

    let offset = getOffset(elem.children[0]);

    let offsetLeft = offset.left - 153;
    let offsetRight = byId("siac-second-col-wrapper").clientWidth  - offset.left - 153;
    if (offsetLeft < 0) {
        offsetLeft -= (offset.left - 153);
        document.documentElement.style.setProperty('--tleft', (offset.left) + 'px')
    } else {
        document.documentElement.style.setProperty('--tleft', '50%');
    }
    if (offsetRight < 0) {
        document.documentElement.style.setProperty('--tleft', (-offsetRight + 153) + 'px')
        offsetLeft += offsetRight;
    }
    $('#cal-info').css("left", offsetLeft + "px").css("top", (offset.top - 275) + "px");
    byId('cal-info').style.display = "block";
    pycmd("siac-cal-info " + $(elem.children[0]).data("index"));
}

window.calMouseLeave = function() {
    calTimer = setTimeout(function () {
        if (!$('#cal-row').is(":hover") && !$('#cal-info').is(":hover"))
            byId('cal-info').style.display = "none";
        calTimer = null;
    }, 300);
}
window.fieldsBtnClicked = function() {
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
    pycmd('siac-r-fld ' + siacState.selectedDecks.toString() + ' ~ ' + html);
}

window.showModalSubpage = function(html) {
    $('#modalText').hide();
    $('#modal-subpage-inner').html(html);
    byId('modal-subpage').style.display = "flex";
}
window.hideModalSubpage = function() {
    $('#modal-subpage-inner').html('');
    $('#modal-subpage').hide();
    $('#modalText').show();
}

window.showPDFLoader = function() {
    let margin = pageSidebarDisplayed ? 230 : 0;
    byId('siac-reading-modal-center').innerHTML += `
    <div id='siac-pdf-loader-wrapper'>
        <div class='siac-pdf-loader' style='margin-right: ${margin}px'>
            <div style='margin-top: 7px;'> 
                <div style='margin-bottom: 12px;'><i class="fa fa-download" style='font-size: 25px; color: lightgrey;'></i></div>
                <div id='siac-pdf-loader-text'>Loading PDF file...</div>
            </div>
        </div>
    </div>`;
}
window.showSearchLoader = function(text) {
    if (byId('siac-results-loader-wrapper')) {
        return;
    }
    let sr = byId("searchResults");
    sr.scrollTop = 0;
    sr.style.overflowY = 'hidden';
    $(sr).append(`
    <div id='siac-results-loader-wrapper' style='position: absolute; left: 0; right: 0; top: 0; bottom: 0; z-index: 5; height: 100%; text-align: center; background: rgba(0,0,0,0.4); display:flex; align-items: center; justify-content: center; border-radius: 5px;'>
        <div class='siac-search-loader' style='display: inline-block; vertical-align: middle;'>
            <b>${text}</b>
        </div>
    </div>`);
}

window.toggleSearchbarMode = function(elem) {
	if (elem.innerHTML === "Mode: Browser") {
	    elem.innerHTML = "Mode: Add-on";
	    pycmd("siac-searchbar-mode Add-on");
	} else {
	    elem.innerHTML = "Mode: Browser";
	    pycmd("siac-searchbar-mode Browser");
	}
}

window.globalKeydown = function(e) {
    // F11 : hide bars
    if (displayedNoteId && e.keyCode === 122) {
        toggleBothBars();
    }  
}

window.toggleNoteSidebar = function(){
    if (byId("siac-notes-sidebar")) {
        pycmd("siac-hide-note-sidebar");
    } else {
        pycmd("siac-show-note-sidebar");
    }
}

window.focusSearchShortcut = function() {
    if (displayedNoteId === null && byId("siac-browser-search-inp")) {
        byId("siac-browser-search-inp").focus();
    }
}
window.triggerSearchShortcut = function() {
    if (!displayedNoteId) {
        sendContent();
    }
}


/** ############# Floating notes */
window.addFloatingNote = function(nid) {
    let onedit = $('#' + nid.toString()).hasClass('siac-user-note') ? `pycmd("siac-edit-user-note ${nid}")`  : `edit(${nid})`;
    let content = byId(nid).innerHTML;
    content = content.replace(/<\/?mark>/g, "");
    $('#cW-' + nid).parent().parent().remove();
    let btnBar = `<div class='floatingBtnBar'>
        <div class="floatingBtnBarItem" onclick='${onedit}'>Edit</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" onclick='searchCardFromFloated("nFC-${nid}")'>Search</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" id='rem-${nid}' onclick='byId("nF-${nid}").outerHTML = ""; updatePinned();'><span>&#10006;&nbsp;&nbsp;</span></div>
    </div>`;
    let floatingNote = `<div id="nF-${nid}" class='noteFloating'>
            <div id="nFH-${nid}" class='noteFloatingHeader' onmousedown='dragElement(this.parentElement, "nFH-${nid}")'>&nbsp;${btnBar}</div>
            <div id="nFC-${nid}" class='noteFloatingContent'  onmouseup='getSelectionText()' >${content}</div>
                </div>
            `;
    if ($('.field').length > 8)
        $('.field').first().after(floatingNote);
    else
        $('.field').last().after(floatingNote);
    dragElement(byId("nF-" + nid), `nFH-${nid}`);
    updatePinned();
}
window.dragElement = function(elmnt, headerId, inModal=false) {
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0, lMYSum = 0, lMXSum = 0;
    if (byId(headerId)) {
        byId(headerId).onmousedown = dragMouseDown;
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



/**
 * Heatmap
 */

window.drawHeatmap = function(id, data) {
    // script might not be loaded yet
    if (typeof CalHeatMap === "undefined" || typeof d3 === "undefined") {
        setTimeout(() => { drawHeatmap(id, data); }, 200); 
        return;
    }
    var cal = new CalHeatMap();
    let legendColors = {
        // min: "#dae289",
        // max: "#3b6427",
        // min: "#8cecff",
        // max: "#008eab",
        min: "lightskyblue",     
        max: "steelblue",
        empty: "#e1e1e1"
    };
    if (document.body.classList.contains("nightMode")) {
        legendColors = {
            min: "#fed976",     
            max: "#800026",
            empty: "black"
        }
    }
    let cellSize = 11;
    let cellPadding = 2;
    let domainLabelFormat = "%B";
    // crude check for available size, reduce cell size if not enough space
    let srw = byId("searchResults").offsetWidth;

    if (srw < 500) {
        // cellSize = 4;
        // cellPadding = 1;
        domainLabelFormat = "%b";
    } else if (srw < 600) {
        // cellSize = 5;
        // cellPadding = 1;
        domainLabelFormat = "%b";
    } else if (srw < 700) {
        // cellSize = 7;
        domainLabelFormat = "%b";
    } else if (srw < 750) {
        // cellSize = 8;
    } else if (srw < 800) {
        // cellSize = 9;
    } else if (srw < 900) {
        // cellSize = 10;
    } 
	cal.init({
        data,
        legendColors,
        itemName: ["page", "pages"],
        itemSelector: id,
        considerMissingDataAsZero: true,
        dataType: "json",
        start: new Date(new Date().getFullYear(), 0), 
        maxDate: new Date(),
        range: 12,
        rowLimit: 7,
        cellSize,
        cellPadding,
        domain: "month",
        domainLabelFormat,
        subDomain: "day"
    });
    let el = document.getElementsByClassName("cal-heatmap-container")[0];
    if (el.getBBox().width > srw) {
        el.style.zoom = srw / (el.getBBox().width + 120);
    }

 }

 /**
  * Pie chart in Read stats.
  * 
  */
 window.drawTopics = function(id, topics) {
    if (typeof $ === "undefined" || typeof $.plot === "undefined") {
        setTimeout(() => { drawTopics(id, topics); }, 200); 
        return;
    }
    $.plot('#' + id, topics.map(t => { return { label: t[0], data: t[1]}; }), {
        series: {
            pie: {
                show: true,
                label: {
                    show: true,
                },
                combine: {
                    threshold: 0.02,
                    label: 'Others (< 2%)'
                },
                stroke: {
                    color: document.body.classList.contains("nightMode") ? '#ffffff' : 'black',
                }

            },
        },
        legend: {
            show: false
        },
    });

 }