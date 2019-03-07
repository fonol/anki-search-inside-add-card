var selectedDecks = ["-1"];
var $hvrBox = $('#hvrBox');
var $hvrBoxSub = $('#hvrBoxSub');
var hvrBoxIndex = 0;
var hvrBoxLength = 0;
var fontSize = 12;
var hvrBoxPos = { x: 0, y: 0 };
var divTmp = document.createElement('span');
var timeout;
var boxIsDisplayed = false;
var isFrozen = false;
var searchOnSelection = true;
var useInfoBox = false;
var last = "";

function updateSelectedDecks() {
    selectedDecks = [];
    $(".dCheck:checked").each(function () {
        selectedDecks.push($(this).data('id'));
    });
}

function expandCard(elem) {
    if ($(elem).hasClass('expanded')) {
        $(elem).animate({ height: $(elem).height() - 80 }, 200);
        $(elem).removeClass("expanded");
        $(elem).css("padding-bottom", "25px")
        $('#i-' + $(elem).data('nid')).hide();

    } else {
        $(elem).css("padding-bottom", "90px")
        $(elem).animate({ height: $(elem).height() + 80 }, 200);
        if ($('#i-' + $(elem).data('nid')).length) {
            $('#i-' + $(elem).data('nid')).fadeIn();
        } else {
            pycmd('nStats ' + $(elem).data('nid'));
        }
        $(elem).addClass("expanded");

    }
}

function pinMouseLeave(elem) {
    $(elem).css('opacity', '0');
}
function pinMouseEnter(elem) {
    $(elem).css('opacity', '1');
}

function cardMouseEnter(elem, nid) {
    $(`#btnBar-${nid}`).css('opacity', '1');
}



function cardMouseLeave(elem, nid) {
    setTimeout(function () {
        if (!$('#btnBar-' + nid).is(':hover'))
            $('#btnBar-' + nid).css('opacity', '0');
        x
    }, 100);
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
    pycmd('fldSlctd ' + selectedDecks.toString() + ' ~ ' + text);
}

function onResize() {
    let vh = window.innerHeight * 0.01;
    document.getElementById('resultsArea').style.setProperty('--vh', `${vh}px`);
}


function getWordPrecedingCaret(containerEl) {
    var precedingChar = "", sel, range, precedingRange;
    if (window.getSelection) {
        sel = window.getSelection();
        if (sel.rangeCount > 0) {
            range = sel.getRangeAt(0).cloneRange();
            range.collapse(true);
            range.setStart(containerEl, 0);
            precedingChar = range.toString().slice(-20);
        }
    } else if ((sel = document.selection) && sel.type != "Control") {
        range = sel.createRange();
        precedingRange = range.duplicate();
        precedingRange.moveToElementText(containerEl);
        precedingRange.setEndPoint("EndToStart", range);
        precedingChar = precedingRange.text.slice(-20);
    }
    let spl = precedingChar.split(" ");
    return spl[spl.length - 1];

}

function setHighlighting(elem) {
    let highlight = $(elem).is(":checked") ? "on" : "off";
    pycmd("highlight " + highlight);
}

function lastWord(text, caretPos) {
    var index = text.indexOf(caretPos);
    var preText = text.substring(0, caretPos);
    if (preText.indexOf(" ") > 0) {
        var words = preText.split(" ");
        return words[words.length - 1]; //return last word
    }
    else {
        return preText;
    }
}

function getCursorCoords(input, selectionPoint) {
    var sel = window.getSelection();
    var range = sel.getRangeAt(0);
    range.insertNode(divTmp);
    let rect = divTmp.getBoundingClientRect();
    return { x: rect.left, y: rect.top };

}

function tagClick(elem) {
    let name = $(elem).data('name');
    pycmd('tagClicked ' + name);
}

function fieldKeydown(event, elem) {
    if ((event.which == 32 || event.keyCode == 32) && event.ctrlKey) {
        event.preventDefault();
        displaySearchInfoBox(event, elem);
        return false;
    }

}


function fieldKeypress(event, elem) {
    if (!boxIsDisplayed && event.keyCode != 13 && !(event.keyCode >= 37 && event.keyCode <= 40) && !event.ctrlKey) {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
        }
        timeout = setTimeout(function () {
            sendContent(event);
        }, 500)
    }
}

function searchMaskKeypress(event) {
    if (event.keyCode === 13)
        sendSearchFieldContent();
}

function hideHvrBox() {
    boxIsDisplayed = false;
    $hvrBox.hide();
    $hvrBoxSub.hide();
}

function moveInHover(event, elem) {

    //other keys, should hide box
    if (boxIsDisplayed && event.keyCode != 17 && event.keyCode != 13 && !(event.keyCode == 38 || event.keyCode == 40)) {
        hideHvrBox();
        return;
    }

    //enter when box is displayed
    if (boxIsDisplayed && event.keyCode == 13) {
        if ($('.hvrSelected').length && $('.hvrSelected').attr('id') == "hvrI-0") {
            event.preventDefault();
            searchFor(last);
            hideHvrBox();
            return false;
        } else if ($('.hvrSelected').length && $('.hvrSelected').attr('id') == "hvrI-1") {
            event.preventDefault();
            pycmd('tagClicked ' + last);
            hideHvrBox();
            return false;
        }
    }

    //ctrl + space  
    if (useInfoBox && (event.which == 32 || event.keyCode == 32) && event.ctrlKey) {
        event.preventDefault();
        displaySearchInfoBox(event, elem);
        return false;
    }

    //up down when box is displayed
    if (boxIsDisplayed && event.keyCode == 38 || event.keyCode == 40) {
        event.preventDefault();
        moveInsideHvrBox(event.keyCode);
    }
}

function displaySearchInfoBox(event, elem) {
    last = getWordPrecedingCaret(elem);
    let pos = getCursorCoords(elem, elem.selectionStart);
    fontSize = parseFloat(window.getComputedStyle(elem, null).getPropertyValue('font-size'));
    $hvrBox.css("left", pos.x + 3);
    $hvrBox.css("top", pos.y + fontSize + 3);
    $('#wiki').html('');
    $hvrBox.show();

    //get last word
    $('#hvrI-0').html(`<b>search</b> for <i>${last}</i>`);
    $('#hvrI-1').html(`add as <b>tag</b>: <i>${last}</i>`);
  
    hvrBoxIndex = -1; hvrBoxLength = 3;
    $('.hvrLeftItem').removeClass('hvrSelected');
    hvrBoxPos.x = pos.x; hvrBoxPos.y = pos.y;
    pycmd('wiki ' + last);
    boxIsDisplayed = true;
}

function displayInfoBoxSubMenu(index) {
    $hvrBoxSub.css("left", hvrBoxPos.x + 231);
    $hvrBoxSub.css("top", hvrBoxPos.y + 5 + (21 * (index + 1)));
    $hvrBoxSub.show();
}


function pinCard(elem, nid) {
    $('#cW-' + nid).css('padding', '5px 4px 5px 5px');
    $('#cW-' + nid).css('font-size', '10px');
    $('#cW-' + nid).html('<span>&#128204;</span>');
    $('#' + nid).parents().first().addClass('pinned');
    updatePinned();
}

function searchCard(elem) {
    let html = $(elem).parent().next().html();
    pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
}

function updatePinned() {
    let pincmd = 'pinCrd';
    $('.pinned').each(function (index) {
        pincmd += " " + $(this).children().first().attr('id').substring(3);
    });
    pycmd(pincmd);
}

function setSearchResults(html) {
    $('.cardWrapper').not('.pinned').remove();
    document.getElementById('searchResults').innerHTML += html;
}

function moveInsideHvrBox(keyCode) {
    if (keyCode == 38 && hvrBoxIndex > 0) {
        document.getElementById('hvrI-' + hvrBoxIndex).className = 'hvrLeftItem';
        document.getElementById('hvrI-' + (hvrBoxIndex - 1)).className += ' hvrSelected';
        hvrBoxIndex -= 1;

    } else if (keyCode == 40 && hvrBoxLength - 1 > hvrBoxIndex) {
        if (hvrBoxIndex >= 0)
            document.getElementById('hvrI-' + hvrBoxIndex).className = 'hvrLeftItem';
        document.getElementById('hvrI-' + (hvrBoxIndex + 1)).className += ' hvrSelected';
        hvrBoxIndex += 1;

    }
    if (hvrBoxIndex == 2) {
        displayInfoBoxSubMenu(2);
        pycmd("lastnote");
    }
    else
        $hvrBoxSub.hide();

}


function toggleTooltip(elem) {
    $(elem).children().first().toggle();
}
