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
var searchOnTyping = true;
var useInfoBox = false;
var last = "";

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

function expandRankingLbl(elem) {
    
    if (elem.getElementsByClassName("rankingLblAddInfo")[0].offsetParent === null) {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "inline";
    } else {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "none";
    }
}


function expandCard(id, icn) {
    let elem = document.getElementById(id);
    if ($(elem).hasClass('expanded')) {
        $(elem).animate({ height: $(elem).height() - 80 }, 200);
        $(elem).removeClass("expanded");
        $(elem).css("padding-bottom", "25px")
        $('#i-' + $(elem).data('nid')).hide();
        $(icn).children().first().html('&#10097;');

    } else {
        $(elem).css("padding-bottom", "90px")
        $(elem).animate({ height: $(elem).height() + 80 }, 200);
        if ($('#i-' + $(elem).data('nid')).length) {
            $('#i-' + $(elem).data('nid')).fadeIn();
        } else {
            pycmd('nStats ' + $(elem).data('nid'));
        }
        $(elem).addClass("expanded");
        $(icn).children().first().html('&#10096;');

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
    if (text.length > 1 && text != "&nbsp;") {
        document.getElementById('searchInfo').innerHTML = "<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>Selection</i></td></tr></table>";
        pycmd('fldSlctd ' + selectedDecks.toString() + ' ~ ' + text);
    }
}

function specialSearch(mode) {
    document.getElementById("a-modal").style.display = 'none'; 
    document.getElementById('searchInfo').innerHTML = "<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>Special Search</i></td></tr></table>";
    pycmd(mode  + " " + selectedDecks.toString());
}


function onResize() {
    let vh = window.innerHeight * 0.01;
    // let topHeight = $('#topContainer').height();
    // let bottomHeight = $('#bottomContainer').height();
    // $('#resultsArea').css("height", `calc(var(--vh, 1vh) * 100 - ${topHeight + bottomHeight + 50}px)`);
    document.getElementById('resultsArea').style.setProperty('--vh', `${vh}px`);
}

function toggleModalLoader(show) {
}


function setHighlighting(elem) {
    let highlight = $(elem).is(":checked") ? "on" : "off";
    pycmd("highlight " + highlight);
}
function setTagSearch(elem) {
    let tagSearch = $(elem).is(":checked") ? "on" : "off";
    pycmd("tagSearch " + tagSearch);
}

function getCursorCoords(input, selectionPoint) {
    var sel = window.getSelection();
    var range = sel.getRangeAt(0);
    range.insertNode(divTmp);
    let rect = divTmp.getBoundingClientRect();
    return { x: rect.left, y: rect.top };

}

function tagClick(elem) {
    if ($(elem).data('tags')) {
        $('#a-modal').show();
        pycmd('renderTags ' + $(elem).data('tags'));
        return
    }
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

function synInputKeyup(event,elem) {
    if (event.keyCode == 13 && elem.value)
        pycmd("saveSynonyms " + elem.value);
}

function synonymSetKeydown(event, elem, index) {
    if (event.keyCode == 13 && elem.innerHTML.length) {
        pycmd("editSynonyms " + index + " " +  elem.innerHTML);
        event.preventDefault();
        $(elem).blur();
    }
}



function setSearchOnTyping(active) {
    searchOnTyping = active;
    if (!active) 
        $('.field').unbind('keypress', fieldKeypress);
    else
        $('.field').on('keypress', fieldKeypress);

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

function fieldKeypress(event, elem) {
    if (searchOnTyping && !boxIsDisplayed && event.keyCode != 13 && !(event.keyCode >= 37 && event.keyCode <= 40) && !event.ctrlKey) {
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
    $('#cW-' + nid).css('font-size', '10px');
    let info = document.getElementById('cW-' + nid).getElementsByClassName("rankingLblAddInfo")[0];
    $('#cW-' + nid).html('<span>&#128204;</span>');
    document.getElementById('cW-' + nid).appendChild(info);
    $('#' + nid).parents().first().addClass('pinned');
    updatePinned();
}

function searchCard(elem) {
    let html = $(elem).parent().next().html();
    document.getElementById('searchInfo').innerHTML = "<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>Note Search</i></td></tr></table>";
    pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
}
function searchCardFromFloated(id) {
    let html = document.getElementById(id).innerHTML;
    document.getElementById('searchInfo').innerHTML = "<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>Note Search</i></td></tr></table>";
    pycmd('fldChgd ' + selectedDecks.toString() + ' ~ ' + html);
}


function edit(nid) {
    pycmd('editN ' +  nid);
}

function updatePinned() {
    let pincmd = 'pinCrd';
    $('.pinned').each(function (index) {
        pincmd += " " + $(this).children().first().attr('id').substring(3);
    });
    $('.noteFloating').each(function (index) {
        pincmd += " " + $(this).attr('id').substring(3);
    });
    pycmd(pincmd);
}

function setSearchResults(html, infoStr) {
    $("#startInfo").remove();
    $('.cardWrapper').not('.pinned').remove();
    document.getElementById("searchResults").style.overflowY = 'hidden';
    document.getElementById("searchResults").style.paddingRight = '24px';
    document.getElementById('searchInfo').innerHTML = infoStr;
    document.getElementById('searchResults').innerHTML += html;
    document.getElementById('searchResults').scrollTop = 0;
    let c = 1;
    function renderLoop() {

        $("#nWr-" + c).fadeIn();
        setTimeout(function () {   
            c++;                    
            if (c< 10) {            
               renderLoop();            
            } else {
                $('.cardWrapper').show();
                document.getElementById("searchResults").style.overflowY = 'auto';
                document.getElementById("searchResults").style.paddingRight = '10px';

            }  
         }, 130);
    }    
    renderLoop();

   
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

function toggleFreeze(elem) {
    isFrozen = ! isFrozen;
    if ($(elem).hasClass('frozen')) {
        $(elem).removeClass('frozen');
        $(elem).html("FREEZE &#10052;");
    } else {
        $(elem).addClass('frozen');
        $(elem).html("FROZEN &#10052;");
    }
}


function toggleTop(elem) {
    $('#topContainer').toggle();
    if ($('#topContainer').is(":hidden")) {
        $('#resultsArea').css('height', 'calc(var(--vh, 1vh) * 100 - $h-1$px)').css('border-top', '0px');
        $(elem).children().first().html('&#10097;');
        pycmd("toggleTop off");

    } else {
        $('#resultsArea').css('height', 'calc(var(--vh, 1vh) * 100 - $h-2$px)').css('border-top', '1px solid grey');;
        $(elem).children().first().html('&#10096;');
        pycmd("toggleTop on");
    }
}


function addFloatingNote(nid) {
    let content = document.getElementById(nid).innerHTML;
    $('#cW-' +nid).parent().remove();
    let btnBar =  `<div class='floatingBtnBar'>
        <div class="floatingBtnBarItem" onclick='edit(${nid})'>Edit</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" onclick='searchCardFromFloated("nFC-${nid}")'>Search</div>&nbsp;&#65372;
        <div class="floatingBtnBarItem" id='rem-${nid}' onclick='document.getElementById("nF-${nid}").outerHTML = ""; updatePinned();'><span>&#10006;&nbsp;&nbsp;</span></div> 
    </div>`


    let floatingNote = `<div id="nF-${nid}" class='noteFloating'>
            <div id="nFH-${nid}" class='noteFloatingHeader' onmousedown='dragElement(this.parentElement, "nFH-${nid}")'>&nbsp;${btnBar}</div>
            <div id="nFC-${nid}" class='noteFloatingContent'>${content}</div>
                </div>
            `;  
        if ($('.field').length > 8)
            $('.field').first().after(floatingNote );       
        else
            $('.field').last().after(floatingNote );       
        dragElement(document.getElementById("nF-" + nid), `nFH-${nid}`);
        updatePinned();
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




