
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