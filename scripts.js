var selectedDecks = ["-1"];
var timeout;
var isFrozen = false;
var searchOnSelection = true;
var searchOnTyping = true;
var last = "";
var lastHadResults = false;
var loadingTimer;
var calTimer;
var gridView = false;
var renderImmediately = $renderImmediately$;
var tagHoverTimeout = 750;


function updateSelectedDecks(elem) {
    selectedDecks = [];
    let str = "";
    if (elem)
        $(elem).toggleClass("selected");
    $(".deck-list-item.selected").each(function () {
        selectedDecks.push($(this).data('id'));
        str += " " + $(this).data('id');
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
    if (elem.parentElement.getElementsByClassName("retMark").length > 0 && elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth.length == 0)
        elem.parentElement.getElementsByClassName("retMark")[0].style.maxWidth = elem.offsetWidth + "px";
}

function expandRankingLbl(elem) {
    fixRetMarkWidth(elem);
    if (elem.getElementsByClassName("rankingLblAddInfo")[0].offsetParent === null) {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "inline";
        elem.getElementsByClassName("editedStamp")[0].style.display = "none";
    } else {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "none";
        elem.getElementsByClassName("editedStamp")[0].style.display = "inline";
    }
}


function expandCard(id, icn) {
    pycmd("nStats " + id);
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
    setTimeout(function () {
            if (elem && elem.parentElement && elem.parentElement.querySelector(':hover') === elem && !document.getElementById('siac-tag-info-box-' + $(elem).data('stamp'))) {
                pycmd("tagInfo " + $(elem).data("stamp") + " " + $(elem).data("name"));
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
        $('.tagLbl').css("z-index", "999");
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
    $(`.tagLbl[data-stamp='${stamp}']`).first().css("z-index", "999");
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

function readingModalTextKeyup(event, elem, nid) {
    if (event.which == 13 || event.keyCode == 13) {
        let html = $(elem).html();
        pycmd("siac-update-note-text " + nid + " " + html);
    }
}

function getSelectionText() {
    if (!searchOnSelection || isFrozen)
        return;
    var text = "";
    if (window.getSelection) {
        text = window.getSelection().toString();
    } else if (document.selection && document.selection.type != "Control") {
        text = document.selection.createRange().text;
    }
    if (text.length > 0 && text != "&nbsp;") {
        showLoading("Selection");
        pycmd('fldSlctd ' + selectedDecks.toString() + ' ~ ' + text);
    }
}

function searchForUserNote(elem) {
    if (elem.value.length === 0) {
       return; 
    }
    pycmd('siac-user-note-search-enter ' + elem.value);
    elem.parentElement.style.display = 'none';
}


function specialSearch(mode) {
    document.getElementById("a-modal").style.display = 'none';
    showLoading("Special Search");
    pycmd(mode + " " + selectedDecks.toString());
}


function onResize() {
    let height = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    height -= ($('#topContainer').is(":hidden") ? -1 : $('#topContainer').outerHeight(true));
    height -= $('#topbutsOuter').outerHeight(true);
    height -= $('#bottomContainer').outerHeight(true);
    height -= 30;
    $("#resultsArea").css("height", (height - 9 + addToResultAreaHeight) + "px");
   
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
        pycmd('renderTags ' + $(elem).data('tags'));
        return;
    }
    let name = $(elem).data('target') || $(elem).data('name');
    $(".siac-tag-info-box").remove();
    $("#greyout").hide();
    pycmd('tagClicked ' + name);
}

function fieldKeydown(event, elem) {
    if ((event.which == 32 || event.keyCode == 32) && event.ctrlKey) {
        event.preventDefault();
        displaySearchInfoBox(event, elem);
        return false;
    }

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
    searchOnTyping = active;
    if (!active)
        $('.field').off('keyup', fieldKeypress);
    else {
        $('.field').on('keyup', fieldKeypress);
        sendContent();
    }
    sendSearchOnTyping();
}

function sendSearchOnTyping() {
    let cmd = searchOnTyping ? "on" : "off";
    pycmd("searchWhileTyping " + cmd);
}
function sendSearchOnSelection() {
    let cmd = searchOnSelection ? "on" : "off";
    pycmd("searchOnSelection " + cmd);
}
function fieldKeypress(event) {
    if (event.keyCode != 13 && !(event.keyCode >= 37 && event.keyCode <= 40) && !event.ctrlKey) {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
        }
        timeout = setTimeout(function () {
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
    pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
}
function searchCardFromFloated(id) {
    let html = document.getElementById(id).innerHTML;
    showLoading("Note Search");
    pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
}


function edit(nid) {
    pycmd('editN ' + nid);
}

function updatePinned() {
    let pincmd = 'pinCrd';
    $('.pinned').each(function (index) {
        pincmd += " " + $(this).children().first().children().first().attr('id').substring(3);
    });
    $('.noteFloating').each(function (index) {
        pincmd += " " + $(this).attr('id').substring(3);
    });
    pycmd(pincmd);
}

function setSearchResults(html, infoStr, infoMap, page = 1, pageMax = 1, total = 50) {
    if (html.length > 0) {
        $('#searchResults .cardWrapper').not('.pinned').remove();
        $("#startInfo,.gridRow:empty").remove();
    }
    $("#greyout").hide();
    $('.siac-tag-info-box').remove();
    $('.tagLbl').css("z-index", "999");
    document.getElementById("searchResults").style.overflowY = 'hidden';
    document.getElementById("searchResults").style.paddingRight = '24px';
    document.getElementById('searchResults').innerHTML += html;
    if (html.length > 0)
        document.getElementById('searchResults').scrollTop = 0;
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
            $('.cardWrapper').css("display", "inline-block");
        else
            $('.cardWrapper').show();
        document.getElementById("searchResults").style.overflowY = 'auto';
        document.getElementById("searchResults").style.paddingRight = '10px';
        $("#greyout").hide();
        displayPagination(page, pageMax, total, html.length > 0);
        if (gridView && document.getElementsByClassName("pinned").length > 1) { reflowGrid(); }
    }
    else {
        time = gridView ? 100 : 130;
        count = gridView ? 16 : 10;
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
                        $('.cardWrapper').css("display", "inline-block");
                    else
                        $('.cardWrapper').show();
                    document.getElementById("searchResults").style.overflowY = 'auto';
                    document.getElementById("searchResults").style.paddingRight = '10px';
                    if (gridView && document.getElementsByClassName("pinned").length > 1) { reflowGrid(); }
                    $("#greyout").hide();
                }
            }, time);
        }
        renderLoop();
        displayPagination(page, pageMax, total, html.length > 0);
    }
}

function displayPagination(page, pageMax, total, resultsFound) {
    let html = "";
    if (pageMax === 0 || !resultsFound) { return; }
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
    isFrozen = !isFrozen;
    if ($(elem).hasClass('frozen')) {
        $(elem).removeClass('frozen');
    } else {
        $(elem).addClass('frozen');
    }
}

function hideTop() {
    let height = $('#topContainer').outerHeight(true);
    let formerHeight =  $("#resultsArea").outerHeight(true);
    $('#topContainer').hide();
    $('#resultsArea').css('height', `${formerHeight + height}px`).css('border-top', '0px');
    $('#toggleTop').children().first().html('&#10097;');
    pycmd("toggleTop off");
}

function toggleTop(elem) {
    let height = $('#topContainer').outerHeight(true);
    $('#topContainer').toggle();

    let formerHeight = $("#resultsArea").outerHeight(true);
    
    if ($('#topContainer').is(":hidden")) {
        $('#resultsArea').css('height', `${formerHeight + height}px`).css('border-top', '0px');
        $(elem).children().first().html('&#10097;');
        pycmd("toggleTop off");

    } else {
        height = $('#topContainer').outerHeight(true);
        $('#resultsArea').css('height', `${formerHeight - height - 1}px`).css('border-top', '1px solid grey');
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
    $('#gridCb').prop("checked", true);
}
function disableGridView() {
    $('#gridCb').prop("checked", false);
    gridView = false;
}


function predefSearch() {
    let e = document.getElementById("predefSearchSelect");
    let search = e.options[e.selectedIndex].value;
    let c = document.getElementById("predefSearchNumberSel");
    let count = c.options[c.selectedIndex].value;
    let decks = selectedDecks.toString();
    pycmd("predefSearch " + search + " " + count + " " + decks);
}

function sort() {
    let e = document.getElementById("sortSelect");
    let sort = e.options[e.selectedIndex].value;
    pycmd("pSort " + sort);

}

function addFloatingNote(nid) {
    let content = document.getElementById(nid).innerHTML;
    $('#cW-' + nid).parent().parent().remove();
    let btnBar = `<div class='floatingBtnBar'>
        <div class="floatingBtnBarItem" onclick='edit(${nid})'>Edit</div>&nbsp;&#65372;
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
    if (gridView)
        reflowGrid();
}

function dragElement(elmnt, headerId) {
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
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


function reflowGrid() {
    $('.gridRow').each(function () {
        if ($(this).find(".cardWrapper").length == 1) {
            if ($(this).next('.gridRow').length) {
                if ($(this).next('.gridRow').find('.cardWrapper').length) {
                    $(this).next('.gridRow').find('.cardWrapper').first().appendTo(this);
                }
            }
        }
    });
}

function toggleAddon() {

    if ($('#outerWr').hasClass("onesided")) {
        showSearchPaneOnLeftSide();
        $('#infoBox').toggleClass("addon-hidden");

    } else if ($('#switchBtn').is(":visible")) {
        showSearchPaneOnLeftSide();
    } else {
        $('#infoBox').toggleClass("addon-hidden");
    }
    pycmd("toggleAll " + ($('#infoBox').hasClass("addon-hidden") ? "off" : "on"));
    onResize();

}

function showSearchPaneOnLeftSide() {
    if ($('#outerWr').hasClass("onesided")) {
        $('#leftSide').show();
        document.getElementById('switchBtn').innerHTML = "&#10149; Search";
        $('#outerWr').css('display', 'flex').removeClass('onesided');
    } else {
        $('#leftSide').hide();
        $('#infoBox').removeClass("addon-hidden");
        document.getElementById('switchBtn').innerHTML = "&#10149; Back";
        $('#outerWr').css('display', 'block').addClass('onesided');
        onResize();
    }
}

function updateSwitchBtn(count) {
    if (!$('#outerWr').hasClass("onesided"))
        document.getElementById('switchBtn').innerHTML = `&#10149; Search (${count})`;
}

function removeNote(nid) {
    $(document.getElementById("cW-" + nid).parentElement.parentElement).remove();
    updatePinned();

    if (gridView)
        reflowGrid();

}
function getOffset(el) {
    var _x = 0;
    var _y = 0;
    while (el && !isNaN(el.offsetLeft) && !isNaN(el.offsetTop)) {
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
    if (offsetLeft < 0) {
        offsetLeft -= (offset.left - 153);
        document.documentElement.style.setProperty('--tleft', (153 + offset.left - 153) + 'px')
    } else {
        document.documentElement.style.setProperty('--tleft', '50%%');
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


function showModalSubpage(html) {
    $('#modalText').hide();
    $('#modal-subpage-inner').html(html);
    $('#modal-subpage').show();
}
function hideModalSubpage() {
    $('#modal-subpage-inner').html('');
    $('#modal-subpage').hide();
    $('#modalText').show();
}