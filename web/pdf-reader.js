var pdfImgSel = { canvas : null, context : null, startX : null, endX : null, startY : null, endY : null, cvsOffLeft : null, cvsOffTop : null, mouseIsDown : false, canvasDispl : null};
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
var noteLoading = false;
var pdfLoading = false;
var pdfTooltipEnabled = true;
var iframeIsDisplayed = false;
var pdfFullscreen = false;
var pdfBarsHidden = false;

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
function queueRenderPage(num, shouldScrollUp=true, fitToPage=false, isInitial=false) {
    if (pdfPageRendering) {
        pageNumPending = num;
    } else {
        rerenderPDFPage(num, shouldScrollUp, fitToPage, isInitial);
    }
}
function rerenderPDFPage(num, shouldScrollUp= true, fitToPage=false, isInitial=false) {
    if (!pdfDisplayed || iframeIsDisplayed) {
        return;
    }
    document.getElementById("siac-pdf-tooltip").style.display = "none";
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
    let html = `<span style='margin-right: 10px;'>${Math.trunc(pagesRead.length * 100 / pdfDisplayed.numPages)} %</span>`;
    for (var c = 0; c < 10; c++) {
        if (c < percs) {
            html += `<div class='siac-prog-sq-filled'></div>`;
        } else {
            html += `<div class='siac-prog-sq'></div>`;
        }
    }
    document.getElementById("siac-prog-bar-wr").innerHTML = html;
}
function pdfHidePageReadMark() {
    document.getElementById("siac-pdf-overlay").style.display = "none";document.getElementById("siac-pdf-read-btn").innerHTML = "\u2713&nbsp; Read";
}
function pdfShowPageReadMark() {
    document.getElementById("siac-pdf-overlay").style.display = "block";document.getElementById("siac-pdf-read-btn").innerHTML = "&times; Unread";
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

function saveTextNote(nid) {
    let html = tinymce.get('siac-text-top').getContent();
    tinymce.remove();
    document.getElementById("siac-text-note-status").innerHTML = "Note Saved - " + new Date().toString();
    pycmd("siac-update-note-text " + nid + " " + html);
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
    $('.siac-queue-sched-btn').first().addClass("active").html('Unqueued');
}
function _startTimer(elementToUpdateId) {
    if (readingTimer) {clearInterval(readingTimer); }
    readingTimer = setInterval(function() {
        remainingSeconds --;
        document.getElementById(elementToUpdateId).innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
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
    document.getElementById("siac-reading-modal-timer").innerHTML = Math.floor(remainingSeconds / 60) + " : " + (remainingSeconds % 60 < 10 ? "0" + remainingSeconds % 60 : remainingSeconds % 60);
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

function swapReadingModal() {
    let modal = document.getElementById("siac-reading-modal");
    if (modal.parentNode.id === "siac-right-side")  {
	document.getElementById("leftSide").appendChild(modal);
    } else {
	document.getElementById("siac-right-side").appendChild(modal);
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
                case 1: html += "<div class='siac-pdf-mark-lbl'>Revisit &nbsp;<b onclick='$(\".siac-mark-btn-inner-1\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-1').first().addClass('active'); break;
                case 2: html += "<div class='siac-pdf-mark-lbl'>Hard &nbsp;<b onclick='$(\".siac-mark-btn-inner-2\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-2').first().addClass('active'); break;
                case 3: html += "<div class='siac-pdf-mark-lbl'>More Info &nbsp;<b onclick='$(\".siac-mark-btn-inner-3\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-3').first().addClass('active'); break;
                case 4: html += "<div class='siac-pdf-mark-lbl'>More Cards &nbsp;<b onclick='$(\".siac-mark-btn-inner-4\").trigger(\"click\");'>&times</b></div>"; $('.siac-mark-btn-inner-4').first().addClass('active');  break;
                case 5: html += "<div class='siac-pdf-mark-lbl'>Bookmark &nbsp;<b onclick='$(\".siac-mark-btn-inner-5\").trigger(\"click\");'>&times</b></div>";  $('.siac-mark-btn-inner-5').first().addClass('active'); break;
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
    onMarkBtnClicked(document.getElementById("siac-mark-jump-btn"));

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
    } else if (event.ctrlKey && event.keyCode === 74) {
        pdfPageRight();
    } else if (event.ctrlKey && (event.keyCode === 37 ||event.keyCode === 75)) {
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
function onMarkBtnClicked(elem) {
    if ($(elem).hasClass("expanded")) {
        if (pdfDisplayedMarks && Object.keys(pdfDisplayedMarks).length > 0) {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b onclick='event.stopPropagation(); jumpToNextMark();' style='vertical-align: middle;'>Jump to Next Mark</b>";
        } else {
            document.getElementById("siac-mark-jump-btn-inner").innerHTML = "<b style='vertical-align:middle; color: grey;'>No Marks in PDF</b>";
        }
    }
}
function jumpToNextMark() {
    if (!pdfDisplayed) {
        return;
    }
    let pages = Object.keys(pdfDisplayedMarks);
    for (var i = 0; i < pages.length; i++) {
        if (Number(pages[i]) > pdfDisplayedCurrentPage) {
            pdfDisplayedCurrentPage = Number(pages[i]);
            queueRenderPage(pdfDisplayedCurrentPage, true, false, false);
            return;
        }
    }
    pdfDisplayedCurrentPage = Number(pages[0]);
    queueRenderPage(pdfDisplayedCurrentPage, true, false, false);
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
    document.getElementById("siac-pdf-bottom-tabs").style.visibility = "visible";
}
function greyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .siac-queue-picker-icn,#siac-reading-modal-bottom-bar .blue-hover').addClass("siac-disabled");
}
function ungreyoutBottom() {
    $('#siac-reading-modal-bottom-bar .siac-clickable-anchor,#siac-reading-modal-bottom-bar .siac-queue-picker-icn, #siac-reading-modal-bottom-bar .blue-hover').removeClass("siac-disabled");
}
function unhideQueue(nid) {
    if(pdfLoading||noteLoading){return;}
    pycmd("siac-unhide-pdf-queue " + nid);
}
function hideQueue(nid) {
    if(pdfLoading||noteLoading){return;}
    pycmd("siac-hide-pdf-queue " + nid);
}
function toggleReadingModalBars() {
    if (!pdfBarsHidden) {
        document.getElementById("siac-reading-modal-top-bar").style.display = "none";
        document.getElementById("siac-reading-modal-bottom-bar").style.display = "none";
        pdfBarsHidden = true;
    } else {
        document.getElementById("siac-reading-modal-top-bar").style.display = "flex";
        document.getElementById("siac-reading-modal-bottom-bar").style.display = "block";
        pdfBarsHidden = false;
    }
}

function toggleReadingModalFullscreen() {
    pdfFullscreen = !pdfFullscreen;
    if (pdfFullscreen) {
        $(document.body).removeClass("siac-fullscreen-show-fields").addClass("siac-fullscreen-show-right");
        if (pdfDisplayed) {
            pdfFitToPage();
        } 
        pdfBarsHidden = false;
        toggleReadingModalBars();
        pycmd("siac-notification Press toggle shortcut (default Ctrl+F) to switch.");

    } else {
        $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right");
        if (pdfDisplayed) {
            pdfFitToPage();
        } 
    }
}
function activateReadingModalFullscreen() {
    pdfFullscreen = false;
    pdfBarsHidden = true;
    toggleReadingModalFullscreen();
}
function onReadingModalClose(shouldSave, nid) {
    if (pdfLoading) {
        return;
    }
    $(document.body).removeClass("siac-fullscreen-show-fields").removeClass("siac-fullscreen-show-right");
    $("#siac-reading-modal").hide(); 
    destroyPDF(); 
    if (shouldSave) { 
        saveTextNote(nid);
    }
    document.getElementById("siac-reading-modal-center").innerHTML = "";
}
