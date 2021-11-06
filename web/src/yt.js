// anki-search-inside-add-card
// Copyright (C) 2019 - 2021 Tom Z.

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


window.siacYt = {
    player: null,
    ready: false,

};

window.onYouTubeIframeAPIReady = function() {
    siacYt.ready = true;
};

window.initYtPlayer = function(videoId, start, tryCounter) {

    if (!tryCounter) {
        tryCounter = 1;
    }
    if (!siacYt.ready && tryCounter < 10) {
        setTimeout(() => { initYtPlayer(videoId, start, tryCounter + 1); }, 100);

    }

    if (typeof YT === "undefined") {
        readerNotification("Seems like Youtube API is not loaded. Maybe check your internet connection?");
        return;
    }
    siacYt.player = new YT.Player('siac-yt-player', {
        height: '360',
        width: '640',
        videoId,
        playerVars: {
            start
        }
      });
};

window.ytCurrentTime = function() {
    return Math.trunc(siacYt.player.getCurrentTime());
};

window.ytScreenCapture = function() {
    let playerEl = document.getElementById("siac-yt-player");
    if (!playerEl) { return; }
    let r =  playerEl.getBoundingClientRect();
    pycmd(`siac-screen-capture -1 ${Math.trunc(r.top)} ${Math.trunc(r.left)} ${Math.trunc(r.width)} ${Math.trunc(r.height)}`);

};

window.ytSavePosition = function() {
    let time = ytCurrentTime();
    let secs = time%60;
    if (secs < 10) { secs = "0" + secs; }
    pycmd("siac-yt-save-time " + time); 
    readerNotification(`Saved Position.<br>Video will resume at ${Math.trunc(time / 60.0)}:${secs}`);
};