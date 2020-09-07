
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
