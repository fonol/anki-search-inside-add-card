var selectedDecks = ["-1"];
var timeout;
var isFrozen = false;
var searchOnSelection = true;
var searchOnTyping = true;
var useInfoBox = false;
var last = "";
var lastHadResults = false;
var loadingTimer;
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

function expandRankingLbl(elem) {
    
    if (elem.getElementsByClassName("rankingLblAddInfo")[0].offsetParent === null) {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "inline";
        elem.getElementsByClassName("editedStamp")[0].style.display = "none";
    } else {
        elem.getElementsByClassName("rankingLblAddInfo")[0].style.display = "none";
        elem.getElementsByClassName("editedStamp")[0].style.display = "inline";
    }
}


function expandCard(id, icn) {
    let elem = document.getElementById(id);
    pycmd('nStats ' + $(elem).data('nid'))
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
 
function showLoading(source) {
    loadingTimer = setTimeout(function() {
        document.getElementById('searchInfo').innerHTML = `<table><tr><td>Status</td><td><b>Searching</b></td></tr><tr><td>Source</td><td><i>${source}</i></td></tr></table>`;
    }, 1000);
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
        showLoading("Selection");
        pycmd('fldSlctd ' + selectedDecks.toString() + ' ~ ' + text);

    }
}

function specialSearch(mode) {
    document.getElementById("a-modal").style.display = 'none'; 
    showLoading("Special Search");
    pycmd(mode  + " " + selectedDecks.toString());
}


function onResize() {
    let vh = window.innerHeight * 0.01;
    // let topHeight = $('#topContainer').height();
    // let bottomHeight = $('#bottomContainer').height();
    // $('#resultsArea').css("height", `calc(var(--vh, 1vh) * 100 - ${topHeight + bottomHeight + 50}px)`);
    document.getElementById('resultsArea').style.setProperty('--vh', `${vh}px`);
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
    $('#cW-' + nid).css('font-size', '10px');
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

function setSearchResults(html, infoStr, infoMap) {
    
    $('.cardWrapper').not('.pinned').remove();
    $("#startInfo,.gridRow:empty").remove();
    document.getElementById("searchResults").style.overflowY = 'hidden';
    document.getElementById("searchResults").style.paddingRight = '24px';
    document.getElementById('searchResults').innerHTML += html;
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
                if (c< count) {            
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

function hideTop(){
    $('#topContainer').hide();
    $('#resultsArea').css('height', 'calc(var(--vh, 1vh) * 100 - $h-1$px)').css('border-top', '0px');
    $('#toggleTop').children().first().html('&#10097;');
    pycmd("toggleTop off");
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


function reflowGrid() {
    let shouldReflow = false;   
    $('.gridRow').each(function() {
        if( $(this).find(".cardWrapper").length == 1) {
            if ($(this).next('.gridRow').length) {
               if ($(this).next('.gridRow').find('.cardWrapper').length) {
                    $(this).next('.gridRow').find('.cardWrapper').first().appendTo(this);
               }
            }
        }
    });
}

  function removeNote(nid){
    $("#cW-" + nid).parents().first().remove(); 
    updatePinned();
    if (gridView)
         reflowGrid();

  }


