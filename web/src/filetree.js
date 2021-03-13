window.SIAC.Filetree = new function () {

    /** tree item clicked */
    this.itemClicked = function (event, item) {
        event.stopPropagation();
        /** item is folder */
        if (item.classList.contains('folder')) {
            if (item.classList.contains('open')) {
                item.classList.remove('open');
            } else {
                item.classList.add('open');
            }
        } 
        /** item is file */
        else {
            let b64Path = item.dataset.path;
            pycmd('siac-open-file ' + b64Path);
        }
    };


}