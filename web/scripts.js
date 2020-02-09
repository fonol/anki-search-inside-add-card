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
var remainingSeconds = 30 * 60;
var readingTimer;
var pdfDisplayed;
var pdfPageRendering = false;
var pdfDisplayedCurrentPage;
var pdfDisplayedScale = 2.0;
var pdfColorMode = "Day";
var pageNumPending = null;
var pagesRead = [];
var pdfDisplayedMarks = null;
var pdfDisplayedMarksTable = null;
var timestamp;
var pdfLoading = false;
var noteLoading = false;
var pdfTooltipEnabled = true;
var iframeIsDisplayed = false;
var pdfImgSel = { canvas : null, context : null, startX : null, endX : null, startY : null, endY : null, cvsOffLeft : null, cvsOffTop : null, mouseIsDown : false, canvasDispl : null};

function pdfImgMouseUp(event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.mouseIsDown = false;
        drawSquare();
        var pdfC = document.getElementById("siac-pdf-canvas");
        cropSelection(pdfC, pdfImgSel.startX, pdfImgSel.startY, pdfImgSel.endX - pdfImgSel.startX , pdfImgSel.endY - pdfImgSel.startY, insertImage);
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
    }
}
function cropSelection(canvasSrc, offsetX, offsetY, width, height, callback) {
    let temp = document.createElement('canvas');
    let tctx = temp.getContext('2d');
    temp.width = width;
    temp.height = height;
    tctx.drawImage(canvasSrc, offsetX, offsetY, width, height, 0, 0, temp.width, temp.height);
    callback(temp.toDataURL());
}
function insertImage(data) {
   pycmd("siac-add-image 1 " + data.replace("image/png", ""));
}
function pdfImgMouseDown(event) {
    pdfImgSel.canvasDispl = document.getElementById("siac-pdf-canvas").offsetLeft;
    pdfImgSel.mouseIsDown = true;
    pdfImgSel.cvsOffLeft = $(pdfImgSel.canvas).offset().left;
    pdfImgSel.cvsOffTop = $(pdfImgSel.canvas).offset().top;
    pdfImgSel.startX = pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
    pdfImgSel.startY = pdfImgSel.endY = event.clientY- pdfImgSel.cvsOffTop;
    drawSquare();
}
function initImageSelection() {
    if ($('#text-layer').is(":hidden")) {
        $(pdfImgSel.canvas).remove();
        $('#text-layer').show();
        return;
    } 
    $('#text-layer').hide();
    pdfImgSel.canvas = document.getElementById("siac-pdf-canvas");
    var lCanvasOverlay = document.createElement("canvas");
    pdfImgSel.canvas.parentNode.insertBefore(lCanvasOverlay, pdfImgSel.canvas.nextSibling);
    $(lCanvasOverlay).css({"width": pdfImgSel.canvas.width + "px", "height" : pdfImgSel.canvas.height + "px", "top": "0", "left": document.getElementById('text-layer').style.left, "position" : "absolute", "z-index": 999999, "opacity": 0.3, "cursor": "crosshair"});
    lCanvasOverlay.setAttribute('width', pdfImgSel.canvas.width);
    lCanvasOverlay.setAttribute('height', pdfImgSel.canvas.height);
    pdfImgSel.context = lCanvasOverlay.getContext("2d");
    lCanvasOverlay.addEventListener("mousedown", function(e) {pdfImgMouseDown(e); }, false);
    lCanvasOverlay.addEventListener("mouseup", function(e) {pdfImgMouseUp(e); }, false);
    lCanvasOverlay.addEventListener("mousemove", function(e) {pdfImgMouseXY(e); }, false);
    pdfImgSel.canvas = lCanvasOverlay;
}
function pdfImgMouseXY(event) {
    if (pdfImgSel.mouseIsDown) {
        pdfImgSel.endX = event.clientX - pdfImgSel.cvsOffLeft;
        pdfImgSel.endY = event.clientY - pdfImgSel.cvsOffTop;
        drawSquare();
    }
}
function drawSquare() {
    pdfImgSel.context.clearRect(0, 0, pdfImgSel.context.canvas.width, pdfImgSel.context.canvas.height);
    pdfImgSel.context.fillRect(pdfImgSel.startX, pdfImgSel.startY, Math.abs(pdfImgSel.startX - pdfImgSel.endX), Math.abs(pdfImgSel.startY - pdfImgSel.endY));
    pdfImgSel.context.fillStyle = "yellow";
    pdfImgSel.context.fill();
}
function pdfFitToPage() {
    if (!iframeIsDisplayed) {
        rerenderPDFPage(pdfDisplayedCurrentPage, false, true);
    }
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
function rerenderPDFPage(num, shouldScrollUp= true, fitToPage=false, isInitial=false) {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    $("#siac-pdf-tooltip").hide();
    document.getElementById("siac-pdf-page-lbl").innerHTML = `${pdfDisplayedCurrentPage} / ${pdfDisplayed.numPages}`;
    pdfLoading = true;
    pdfDisplayed.getPage(num)
       .then(function(page) {
            updatePdfDisplayedMarks();
            pdfPageRendering = true;
            var lPage = page;
            var canvas = document.getElementById("siac-pdf-canvas");
	        if (fitToPage) {
                var viewport = page.getViewport({scale : 1.0});
                pdfDisplayedScale = (canvas.parentNode.clientWidth - 23) / viewport.width;
            }
            var viewport = page.getViewport({scale : pdfDisplayedScale});
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            if (pdfColorMode !== "Day")
                canvas.style.display = "none";
            var ctx = canvas.getContext('2d');
            var pageTimestamp = new Date().getTime();
            timestamp = pageTimestamp;
            var renderTask = page.render({
                canvasContext: ctx,
                viewport: viewport,
                continueCallback: function(cont) {
                    if(timestamp != pageTimestamp) {
                        return;
                    }
                    cont();
                }
            });
            renderTask.promise.then(function () {
                pdfPageRendering = false;
                if (pageNumPending !== null) {
                    rerenderPDFPage(pageNumPending, shouldScrollUp);
                    pageNumPending = null;
                } else {
                    if (pdfColorMode !== "Day") {
                        invertCanvas(ctx);
                    }
                }
                return lPage.getTextContent({ normalizeWhitespace: true, disableCombineTextItems: false});
            }).then(function(textContent) {
                   $("#text-layer").css({ height: canvas.height , width: canvas.width, left: canvas.offsetLeft  }).html('');
                   pdfjsLib.renderTextLayer({
                       textContent: textContent,
                       container: document.getElementById("text-layer"),
                       viewport: viewport,
                       textDivs: []
                   });
                   pdfLoading = false;
                   if (isInitial) {
                       ungreyoutBottom();
                   }
               });
           if (shouldScrollUp)  {
               canvas.parentElement.scrollTop = 0;
           }
	    if (pagesRead.indexOf(num) !== -1) {
            document.getElementById('siac-pdf-overlay').style.display = 'block';
            document.getElementById('siac-pdf-read-btn').innerHTML = '&times; Unread';
	    } else {
            document.getElementById('siac-pdf-overlay').style.display = 'none';
            document.getElementById('siac-pdf-read-btn').innerHTML = '\u2713&nbsp; Read';
	    }
        });
}
function invertCanvas(ctx) {
    var imgData = ctx.getImageData(0,0, ctx.canvas.width, ctx.canvas.height);
    var data = imgData.data;
    var mapped;
    if (pdfColorMode === "Sand") {
        for (var i = 0; i < data.length; i += 4) {
            mapped = pxToSandScheme(data[i], data[i + 1], data[i + 2]) ;
            data[i]     = mapped.r;  
            data[i + 1] = mapped.g;
            data[i + 2] = mapped.b;
        }
    } else {
        for (var i = 0; i < data.length; i += 4) {
             data[i]     = 255 - data[i];  
             data[i + 1] = 255 - data[i + 1];
             data[i + 2] = 255 - data[i + 2];
        }

    }
    ctx.putImageData(imgData, 0, 0);  
    ctx.canvas.style.display = "inline-block";
}
function queueRenderPage(num, shouldScrollUp=true, fitToPage=false, isInitial=false) {
    if (pdfPageRendering) {
        pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial);
    }
}
function togglePageRead(nid) {

	if (pagesRead.indexOf(pdfDisplayedCurrentPage) === -1) {
        document.getElementById('siac-pdf-overlay').style.display = 'block';
        document.getElementById('siac-pdf-read-btn').innerHTML = '&times; Unread';
		pycmd("siac-pdf-page-read " + nid + " " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages);
		if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
	} else {
        document.getElementById('siac-pdf-overlay').style.display = 'none';
        document.getElementById('siac-pdf-read-btn').innerHTML = '\u2713&nbsp; Read';
		pycmd("siac-pdf-page-unread " + nid + " " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages);
		pagesRead.splice(pagesRead.indexOf(pdfDisplayedCurrentPage), 1);
    }
    updatePdfProgressBar();
}
function updatePdfProgressBar() {
    let percs = Math.floor(pagesRead.length * 10 / pdfDisplayed.numPages);
    let html = `<span style='margin-right: 10px;'>${Math.trunc(pagesRead.length * 100 / pdfDisplayed.numPages)} %%</span>`;
    for (var c = 0; c < 10; c++) {
        if (c < percs) {
            html += `<div class='siac-prog-sq-filled'></div>`;
        } else {
            html += `<div class='siac-prog-sq'></div>`;
        }
    }
    document.getElementById("siac-prog-bar-wr").innerHTML = html;
}
function pdfJumpToPage(e, inp) {
    if (e.keyCode !== 13) {
        return;
    }
    let p = inp.value;
    p = Math.min(pdfDisplayed.numPages, p);
    pdfDisplayedCurrentPage = p;
    queueRenderPage(pdfDisplayedCurrentPage);
}
function pdfScaleChange(mode) {
    if (mode === "up") {
        pdfDisplayedScale += 0.1;
    } else {
        pdfDisplayedScale -= 0.1;
        pdfDisplayedScale = Math.max(0.1, pdfDisplayedScale);
    }
    queueRenderPage(pdfDisplayedCurrentPage, shouldScrollUp=false);
}

function pdfPageRight() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage < pdfDisplayed.numPages) {
        pdfDisplayedCurrentPage++;
    queueRenderPage(pdfDisplayedCurrentPage);
    }
}
function pdfPageLeft() {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    if (pdfDisplayedCurrentPage > 1) {
        pdfDisplayedCurrentPage--;
        queueRenderPage(pdfDisplayedCurrentPage);
    }
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
function readingModalTextKeyup(elem, nid) {
        let html = tinymce.get('siac-text-top').getContent();
        tinymce.remove();
        document.getElementById("siac-text-note-status").innerHTML = "Note Saved - " + new Date().toString();
        pycmd("siac-update-note-text " + nid + " " + html);
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
function toggleQueue() {
    let $wr = $("#siac-queue-sched-wrapper");
    if ($wr.hasClass('active')) {
        $wr.css( { "max-width" : "0px" , "overflow": "hidden"});
        $('.siac-queue-sched-btn:first').addClass("active");
    } else {
        $wr.css({ "max-width": "500px", "overflow": "visible"});
        $('.siac-queue-sched-btn:first').removeClass("active");
    }
    $wr.toggleClass('active');
}
function queueSchedBtnClicked(btn_el) {
    $('#siac-queue-lbl').hide();
    $('.siac-queue-sched-btn,.siac-queue-sched-btn-hor').removeClass("active");
    toggleQueue();
    $(btn_el).addClass("active");
}
function afterRemovedFromQueue() {
    toggleQueue();
    $('.siac-queue-sched-btn,.siac-queue-sched-btn-hor').removeClass("active");
    $('.siac-queue-sched-btn').first().addClass("active").html('Not In Queue');
}
function _startTimer(elementToUpdateId) {
    if (readingTimer) {clearInterval(readingTimer); }
    readingTimer = setInterval(function() {
        remainingSeconds --;
        document.getElementById(elementToUpdateId).innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds %% 60 < 10 ? "0" + remainingSeconds %% 60 : remainingSeconds %% 60);
        if (remainingSeconds <= 0) {
            clearInterval(readingTimer);
            remainingSeconds = 1800;
            $('#siac-timer-play-btn').html("Start").addClass("inactive");
            $('.siac-timer-btn').removeClass('active');
            $('.siac-timer-btn').eq(4).addClass('active');
            document.getElementById(elementToUpdateId).innerHTML = "30 : 00";
            pycmd('siac-timer-elapsed ' + $('#siac-reading-modal-top-bar').data('nid'));
            readingTimer = null;
        }
    }, 999);
}
function toggleTimer(timer) {
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
function resetTimer(elem) {
    clearInterval(readingTimer);
    readingTimer = null;
    $('.siac-timer-btn').removeClass('active');
    $(elem).addClass('active');
    remainingSeconds =  Number(elem.innerHTML) * 60;
    document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds %% 60 < 10 ? "0" + remainingSeconds %% 60 : remainingSeconds %% 60);
    $('#siac-timer-play-btn').addClass("inactive").html("Start");
}
function startTimer(mins) {
    $('.siac-timer-btn').each((i, e) => {
        if (e.innerHTML === mins.toString()) {
            resetTimer(e);
            $('#siac-timer-play-btn').trigger('click');
        }
    });
}
function pdfMouseWheel(event)  {
    if(!event.ctrlKey) { return; }
    if (event.deltaY < 0)
    {
        pdfScaleChange("up");
    }
    else if (event.deltaY > 0)
    {
       pdfScaleChange("down");
    }
}
function onResize() {
    let height = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    height -= ($('#topContainer').is(":hidden") ? -1 : $('#topContainer').outerHeight(true));
    height -= $('#topbutsOuter').outerHeight(true);
    height -= $('#bottomContainer').outerHeight(true);
    height -= 39;
    height += addToResultAreaHeight;
    $("#resultsArea").css("height", height + "px");
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
    pycmd('tagClicked ' + name);
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
    pycmd("searchWhileTyping " + siacState.searchOnTyping ? "on" : "off");
}
function sendSearchOnSelection() {
    pycmd("searchOnSelection " + siacState.searchOnSelection ? "on" : "off");
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
            $('.cardWrapper').css("display", "inline-block");
        else
            $('.cardWrapper').show();
        sr.style.overflowY = 'auto';
        sr.style.paddingRight = '10px';
        document.getElementById("greyout").style.display = "none";
        displayPagination(page, pageMax, total, html.length > 0, cacheSize);

        if (stamp > -1) {
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
        if (stamp > -1) {
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
                        $('.cardWrapper').css("display", "inline-block");
                    else
                        $('.cardWrapper').show();
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
    window.setTimeout(function() {
        $('#gridCb').prop("checked", true);
    }, 400);
}
function toggleReadingModalBars() {
    $('#siac-reading-modal-top-bar,#siac-reading-modal-bottom-bar').toggle();
    if ($('#siac-reading-modal-top-bar').is(":hidden")) {
        $('#siac-reading-modal-text').css('height', 'calc(100%% - 35px)').css('max-height', '').css('margin-top', '15px');
    } else {
        $('#siac-reading-modal-text').css('height', 'calc(90%% - 145px)').css('max-height', 'calc(100%% - 235px)').css('margin-top', '0px');
    }
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
    let offsetRight = document.getElementsByTagName("BODY")[0].clientWidth  - offset.left - 153;
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
function swapReadingModal() {
    let modal = document.getElementById("siac-reading-modal");
    if (modal.parentNode.id === "infoBox")  {
	document.getElementById("leftSide").appendChild(modal);
    } else {
	document.getElementById("infoBox").appendChild(modal);
    }
}
function togglePDFNightMode(elem) {
    if (pdfColorMode === "Day") {
        pdfColorMode = "Night";

    } else if (pdfColorMode === "Night") {
        pdfColorMode = "Sand";
    } else {
        pdfColorMode = "Day";
    }
    elem.innerHTML = pdfColorMode;
    rerenderPDFPage(pdfDisplayedCurrentPage, false);
}
function pdfKeyup() {
	if (pdfTooltipEnabled && window.getSelection().toString().length) {
		let s = window.getSelection();
        let r = s.getRangeAt(0);
        let text = s.toString();
        if (text === " " || text.length > 500) { return; }
        let nodesInSel = nodesInSelection(r);
        let sentences = getSentencesAroundSelection(r, nodesInSel, text);
        if (nodesInSel.length > 1) {
            text = joinTextLayerNodeTexts(nodesInSel, text);
        }
		let rect = r.getBoundingClientRect();
		let prect = document.getElementById("siac-reading-modal").getBoundingClientRect();
        document.getElementById('siac-pdf-tooltip-results-area').innerHTML = 'Searching...';
        document.getElementById('siac-pdf-tooltip-searchbar').value = "";
        let left =  rect.left - prect.left;
        if (prect.width - left < 250) {
            left -= 200;
        }
        $('#siac-pdf-tooltip').css({'top': (rect.top - prect.top + rect.height) + "px", 'left':left + "px" }).show();
        pycmd("siac-pdf-selection " + text);
        $('#siac-pdf-tooltip').data("sentences", sentences);
        $('#siac-pdf-tooltip').data("selection", text);
	}
}
function joinTextLayerNodeTexts(nodes, text) {
    let total = "";
    for (var i = 0; i <nodes.length; i++) {
        if (nodes[i].innerHTML === text) {
            return text;
        }
        total += nodes[i].innerHTML += " ";
    }
    total = total.replace("  ", " ");
    let spl = total.split(" ");
    total = "";
    for (var i = 0; i < spl.length; i++) {
        if (spl[i].length > 0 && text.indexOf(spl[i]) >= 0) {
            total += spl[i] + " ";
        }
    }
    return total.trim();
}

function nodesInSelection(range) {

    var lAllChildren = document.getElementById("text-layer").children;
    let nodes = [];
    let inside = false;
    let start = range.startContainer.nodeName === "#text" ? range.startContainer.parentNode : range.startContainer;
    let end = range.endContainer.nodeName === "#text" ? range.endContainer.parentNode : range.endContainer;
    for (var i = 0; i < lAllChildren.length; i++) {
        if (lAllChildren[i] == start) {
            inside = true;
        }
        if (inside) {
            nodes.push(lAllChildren[i]);
        }
        if (lAllChildren[i] == end) {
            break;
        }
    }
    return nodes;
}
function globalKeydown(e) {
    if ((window.navigator.platform.match("Mac") ? e.metaKey : e.ctrlKey) && e.shiftKey && e.keyCode == 78) {
        e.preventDefault();
        if ($('#siac-rd-note-btn').length) {
            $('#siac-rd-note-btn').trigger("click");
        } else {
            pycmd('siac-create-note');
        }
    } else if (pdfDisplayed && !$('.field').is(':focus')) {
        pdfViewerKeyup(e);
    }
}
function getSentencesAroundSelection(range, nodesInSel, selection) {
    if (!range.startContainer) {
        return;
    }
    selection = selection.replace(/  +/g, " ").trim();
    let currentNode = range.startContainer.parentElement.previousSibling;
    let text = "";
    let height = 0;
    let lastOffsetTop = 0;
    if (nodesInSel.length === 1) {
        text = nodesInSel[0].innerHTML;
        height = nodesInSel[0].clientHeight;
    } else {
        for (var i = 0; i< nodesInSel.length; i++) {
            text += nodesInSel[i].innerHTML + " ";
            height = nodesInSel[i].clientHeight;
        }
    }
    lastOffsetTop = nodesInSel[0].offsetTop;
    text = text.replace(/  +/g, " ").trim();
    let extracted = [];
    if (!currentNode) {
        extracted.push(text);
    }
    while(currentNode) {
        if (Math.abs(currentNode.clientHeight - height) > 3 || lastOffsetTop - currentNode.offsetTop > height * 1.5) {
            extracted.push(text);
            break;
        } 
        lastOffsetTop = currentNode.offsetTop;
        text = (currentNode.innerHTML + " " + text).replace(/  +/g, " ").trim();        
        let ext = extractPrev(text, extracted, selection);
        extracted = ext[1];
        if (ext[0]) {
            break;
        }
        currentNode = currentNode.previousSibling; 
        if (!currentNode) {
            extracted.push(text);
            break;
        }
    }
    let extractedFinal = [];
    for (var i = 0; i < extracted.length; i++) {
        text = extracted[i];
        currentNode = range.endContainer.parentElement.nextSibling;
        if (!currentNode) {
            extractedFinal.push(text);
        }
        while(currentNode) {
            text = (text + " " + currentNode.innerHTML).replace(/  +/g, " ").trim();        
            let ext = extractNext(text, extractedFinal, selection);
            extractedFinal = ext[1];
            if (ext[0]) {
                break;
            }
            currentNode = currentNode.nextSibling; 
            if (!currentNode) {
                extractedFinal.push(text);
                break;
            }
        }
    }
    return extractedFinal;
}

function sendClozes() {
    let sentences = $('#siac-pdf-tooltip').data("sentences");
    let selection = $('#siac-pdf-tooltip').data("selection");
    pycmd("siac-show-cloze-modal " + selection + "$$$" + sentences.join("$$$"));

}
function generateClozes() {
    let cmd = "";
    $('.siac-cl-row').each(function(i, elem) {
        if($(elem.children[1].children[0]).is(":checked")) {
           cmd += "$$$" + $(elem.children[0].children[0]).text();
        }
    });
    let pdfPath = $('#siac-pdf-top').data("pdfpath");
    let pdfTitle = $('#siac-pdf-top').data("pdftitle");
    pycmd('siac-generate-clozes $$$' + pdfTitle + "$$$" + pdfPath + "$$$" + pdfDisplayedCurrentPage + cmd);
    $('#siac-pdf-tooltip').hide();
}

function extractPrev(text, extracted, selection) {
    text = text.substring(0, text.lastIndexOf(selection)+ selection.length) + text.substring(text.lastIndexOf(selection) + selection.length).replace(/\./g, "$DOT$");
    let matches = text.match(/.*[^.\d][.!?]"? (.+)/);
    if (!matches || matches[1].indexOf(selection) === -1 ) {
        return [false, extracted];
    }
    let ext = matches[1].replace(/\$DOT\$/g, ".");
    if (extracted.indexOf(ext) === -1) {
        extracted.push(ext);
    }
    return [true, extracted];

}
function extractNext(text, extracted, selection) {
    text = text.substring(0, text.indexOf(selection)).replace(/\./g, "$DOT$") + text.substring(text.indexOf(selection));

    let matches = text.match(/(.+?(\.\.\.(?!,| [a-z])|[^.]\.(?!(\.|[0-9]|[A-Z]{2,20}))|[!?]|[^0-9]\. [A-Z])).*/);
    if (!matches || matches[1].indexOf(selection) === -1) {
        return [false, extracted];
    }
    let ext = matches[1].replace(/\$DOT\$/g, ".");
    if (extracted.indexOf(ext) === -1) {
        extracted.push(ext);
    }
    return [true, extracted];

}

function pxToSandScheme(red, green, blue){
    if (red > 210 && green > 210 && blue > 210) {return {r:241,g:206,b:147}; }
    if (red <  35 && green < 35 && blue < 35) {return {r:0,g:0,b:0}; }
    var p = [{r:241,g:206,b:147},{r:0,g:0,b:0},{r:146,g:146,b:146},{r:64,g:64,b:64},{r:129,g:125,b:113},{r:204,g:0,b:0},{r:0,g:102,b:151}]
    var color, diffR, diffG, diffB, diff, chosen;
    var distance= 25000;
    for (var i=0; i < p.length; i++) {
        color = p[i];
        diffR = (color.r - red);
        diffG = (color.g - green);
        diffB = (color.b - blue);
        diff = Math.sqrt(diffR * diffR + diffG * diffG + diffB * diffB);
        if( diff < distance) { 
            distance = diff; 
            chosen = p[i]; 
        }
    }
    return chosen;
}

function updatePdfDisplayedMarks() {
    if (pdfDisplayedMarks == null) {
        return;
    }
    let html = "";
    $('.siac-mark-btn-inner').removeClass('active'); 
    if (pdfDisplayedCurrentPage in pdfDisplayedMarks) {
        for (var i = 0; i < pdfDisplayedMarks[pdfDisplayedCurrentPage].length; i++) {
            switch(pdfDisplayedMarks[pdfDisplayedCurrentPage][i]) {
                case 1: html += "<div class='siac-pdf-mark-lbl'>Revisit <b onclick='$(\".siac-mark-btn-inner-1\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-1').first().addClass('active'); break;
                case 2: html += "<div class='siac-pdf-mark-lbl'>Hard <b onclick='$(\".siac-mark-btn-inner-2\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-2').first().addClass('active'); break;
                case 3: html += "<div class='siac-pdf-mark-lbl'>More Info <b onclick='$(\".siac-mark-btn-inner-3\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-3').first().addClass('active'); break;
                case 4: html += "<div class='siac-pdf-mark-lbl'>More Cards <b onclick='$(\".siac-mark-btn-inner-4\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-4').first().addClass('active');  break;
                case 5: html += "<div class='siac-pdf-mark-lbl'>Bookmark <b onclick='$(\".siac-mark-btn-inner-5\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-5').first().addClass('active'); break;
            }
        }
    }
    let w1 = document.getElementById("siac-queue-readings-list").offsetWidth;
    let w2 = document.getElementById("siac-queue-actions").offsetWidth;
    let w = document.getElementById("siac-reading-modal-bottom-bar").clientWidth - w1 - w2 - 100;
    var tableHtml = "";
    Object.keys(pdfDisplayedMarksTable).forEach(function(key) {
        let name = "";
        switch(key) {
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
        pages = pages.length > 0 ? pages.substring(0, pages.length -2) : pages;
        tableHtml += `<tr style='color: grey;'><td><b>${name}</b></td><td>${pages}</td></tr>`;
    });
    if (tableHtml.length) {
        tableHtml = `<table style='user-select: none; table-layout: fixed; max-width: ${w}px;'>` + tableHtml + "</table>";
    }
    document.getElementById("siac-pdf-overlay-top-lbl-wrap").innerHTML = html;
    if (document.getElementById("siac-marks-display")) { document.getElementById("siac-marks-display").innerHTML = tableHtml; }

}
function markClicked(event) {
    if (event.target.className === "siac-page-mark-link") {
        pdfDisplayedCurrentPage = Number(event.target.innerHTML);
        queueRenderPage(pdfDisplayedCurrentPage, true);
    }
}
function pdfViewerKeyup(event) {
    if (event.ctrlKey && (event.keyCode === 32 || event.keyCode === 39)) {
        if (event.shiftKey && pdfDisplayed && pagesRead.indexOf(pdfDisplayedCurrentPage) === -1) {
            pycmd("siac-pdf-page-read " + $('#siac-pdf-top').data("pdfid") + " " + pdfDisplayedCurrentPage + " " + pdfDisplayed.numPages);
            if (pagesRead.length) { pagesRead.push(pdfDisplayedCurrentPage); } else { pagesRead = [pdfDisplayedCurrentPage]; }
            updatePdfProgressBar();
        }
        pdfPageRight();
    } else if (event.ctrlKey && event.keyCode === 37) {
        pdfPageLeft();
    } 
}
function pdfTooltipClozeKeyup(event) {
    if (event.ctrlKey && event.shiftKey && event.keyCode === 67) {
        let text = window.getSelection().toString();
        if (!text || text.length === 0) {
            return;
        }
        let c_text = document.getElementById("siac-pdf-tooltip-results-area").innerHTML;
        for (var i = 1; i < 20; i++) {
            if (c_text.indexOf("{{c" + i + "::") === -1) {
                c_text = c_text.split(text).join("<span style='color: lightblue;'>{{c"+ i + "::" + text + "}}</span>");
                document.getElementById("siac-pdf-tooltip-results-area").innerHTML = c_text;
                break;
            }
        }
    }
}
function togglePDFSelect(elem) {
    pdfTooltipEnabled = !pdfTooltipEnabled;
    if (pdfTooltipEnabled) {
        $(elem).addClass('active');
    } else {
        $(elem).removeClass('active');
    }
}

function centerTooltip() {
    let w = $('#siac-pdf-top').width();
    let h = $('#siac-pdf-top').height();
    let $tt = $('#siac-pdf-tooltip');
    $tt.css({ 'top': h / 2 - ($tt.height() / 2), 'left': w / 2 - ($tt.width() / 2) });
}
function destroyPDF() {
    if (pdfDisplayed) {
        pdfDisplayed.destroy();
    }
    pdfDisplayed = null;
}
function pdfUrlSearch(input) {
    if (!input.length) {return; }
    let url = "";
    $("#siac-iframe-btn tr").each(function () {
        if ($(this.children[1].children[0]).is(":checked")) {
            url = $(this.children[1].children[0]).data("url");
        }
    });
    pycmd('siac-url-srch $$$' + input + '$$$' + url); 
    $('#siac-iframe-btn').removeClass('expanded');
}
function showQueueInfobox(elem, nid) {
    if (pdfLoading || noteLoading) {return;}
    pycmd('siac-queue-info ' + nid);
    document.documentElement.style.setProperty('--ttop', (elem.offsetTop) + 'px');
    if (pdfLoading || noteLoading) {return;}
   
}
function leaveQueueItem(elem) {
    window.setTimeout(function() {
        if (!$('#siac-queue-infobox').is(":hover") && !$('#siac-queue-readings-list .siac-clickable-anchor:hover').length) {
           hideQueueInfobox();
        }
    }, 400);
}
function hideQueueInfobox() {
    document.getElementById("siac-queue-infobox").style.display = "none";
    document.getElementById("siac-pdf-bottom-tabs").style.display = "inline-block";
}
function toggleNoteSidebar(){
    if (document.getElementById("siac-notes-sidebar")) {
        pycmd("siac-hide-note-sidebar");
    } else {
        pycmd("siac-show-note-sidebar");
    }
}
function greyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .siac-queue-picker-icn,#siac-reading-modal-bottom-bar .blue-hover').addClass("siac-disabled");
}
function ungreyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .siac-queue-picker-icn, #siac-reading-modal-bottom-bar .blue-hover').removeClass("siac-disabled");
}