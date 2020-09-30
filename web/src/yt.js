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


window.siacYt = {
    player: null
};


window.initYtPlayer = function(videoId, start) {

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
}

window.ytCurrentTime = function() {
    return Math.round(siacYt.player.getCurrentTime());
};

window.ytScreenCapture = function() {
    let playerEl = document.getElementById("siac-yt-player");
    if (!playerEl) { return; }
    let r =  playerEl.getBoundingClientRect();
    pycmd(`siac-screen-capture ${Math.trunc(r.top)} ${Math.trunc(r.right)} ${Math.trunc(r.bottom)} ${Math.trunc(r.left)}`);

};

window.ytSavePosition = function() {
    let time = ytCurrentTime();
    let secs = time%60;
    if (secs === 0) { secs = "00"; }
    pycmd("siac-yt-save-time " + time); 
    readerNotification(`Saved Position.<br>Video will resume at ${Math.trunc(time / 60.0)}:${secs}`);
};