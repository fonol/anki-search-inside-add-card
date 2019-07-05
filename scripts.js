var selectedDecks = ["-1"];
var timeout;
var isFrozen = false;
var searchOnSelection = true;
var searchOnTyping = true;
var useInfoBox = false;
var last = "";
var lastHadResults = false;
var loadingTimer;
var calTimer;
var gridView = false;
var renderImmediately = $renderImmediately$;


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
    if (!showTagInfoOnHover)
        return;
    setTimeout(function () {
        if (elem.parentElement.querySelector(':hover') === elem && $('#resultsArea').height() > 400 && $('#resultsArea').width() > 450) {
            $(elem).css("z-index", "9999");
            $("#greyout").show();
            let offsetTop = $(elem.parentElement.parentElement).offset().top;
            if (!$('#topContainer').is(":hidden"))
                offsetTop -= $('#topContainer').height();
            let offsetBot = $('#searchResults').height() - offsetTop - $('#bottomContainer').height() + 20;
            if (offsetTop < 0 || elem.parentElement.previousElementSibling.getElementsByTagName('img').length > 0) {
                offsetTop += $(elem.parentElement.parentElement).height();
                offsetBot = $('#searchResults').height() - offsetTop;
            }
            if (offsetTop > 0 && offsetTop < offsetBot) {
                $(elem).children().first().addClass("t-inverted");
            }
            if (gridView && $(elem.parentElement.parentElement).is(':first-child')) {
                $(elem).children().first().addClass("t-right");
            }
            $(elem).children().first().addClass("shouldFill");
            pycmd("tagInfo " + $(elem).data("name"));
        }
    }, 800);
}
function tagMouseLeave(elem) {
    $("#greyout").hide();
    $(elem).css("z-index", "999");
    $(elem).children().first().removeClass('t-inverted').removeClass("shouldFill").removeClass("t-right").css('margin-bottom', '0px').html('').hide();
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
    height -= 20;
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
    if ($(elem).data('tags')) {
        $('#a-modal').show();
        pycmd('renderTags ' + $(elem).data('tags'));
        return;
    }
    let name = $(elem).data('name');
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

function setSearchResults(html, infoStr, infoMap) {
    if (html.length > 0) {
        $('#searchResults .cardWrapper').not('.pinned').remove();
        $("#startInfo,.gridRow:empty").remove();
    }
    $("#greyout").hide();
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
    }
    else {
        time = gridView ? 100 : 130;
        count = gridView ? 16 : 10;
        function renderLoop() {

            if (gridView)
                $("#nWr-" + c).fadeIn().css("display", "inline-block");
            else
                $("#nWr-" + c).fadeIn();

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

                }
            }, time);
        }
        renderLoop();
    }
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

    $(elem).toggleClass('active');
    if ($(elem).hasClass('active')) {
        pycmd("toggleGrid on");
        gridView = true;
    } else {
        pycmd("toggleGrid off");
        gridView = false;
    }
}

function activateGridView() {
    $('#grid-icon').addClass('active');
    gridView = true;
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

function calBlockMouseEnter(elem) {
    calTimer = setTimeout(function () {
        if ($('#cal-row').is(":hover")) {
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
            calTimer = null;
        }
    }, 100);

}


function calMouseLeave() {
    calTimer = setTimeout(function () {
        if (!$('#cal-row').is(":hover") && !$('#cal-info').is(":hover"))
            document.getElementById('cal-info').style.display = "none";
        calTimer = null;
    }, 300);
}