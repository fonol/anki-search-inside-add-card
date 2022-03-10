
window.SIAC.epub = new function () {

    this.rendition = null;
    this.displayed = null;

    this.target = '';

    this.display = function(arrayBuffer, target) {

        console.log('[SIAC] rendering epub...');

        this.target = target;
        let book = ePub(arrayBuffer);

        // this.rendition = book.renderTo(this.target, { method: "default", flow: "paginated", width: '100%', height: '100%' });
        // this.rendition = book.renderTo(this.target, {  width: '100%', height: '100%' });
        this.rendition = book.renderTo(this.target, { flow: "paginated", width: '600px', height: '800px' });
        this.displayed = this.rendition.display();
     
        this.updatePageLbl();
    }

    this.calculatePages = function () {

        

    }

    this.updatePageLbl = function() {
        byId("siac-pdf-page-lbl").innerHTML = `${this.currentPage()} / ${this.totalPages()}`;
    }

    this.currentPage = function() {
        return this.rendition.location.start.displayed.page;
    }
    this.totalPages = function() {
        return this.rendition.location.start.displayed.total;
    }
    this.nextPage = function() {
        this.rendition.next().then(function(x) {
            this.updatePageLbl();
        });
    };
    this.previousPage = function() {
        this.rendition.prev();
        this.updatePageLbl();
    }

};