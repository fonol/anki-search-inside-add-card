window.SIAC.Filetree = new function () {

    this.init = function() {
        if (typeof(window.ftreeVue) === 'undefined' || window.ftreeVue === null) {
            window.ftreeVue = new Vue({
                el: '#siac-left-tab-md',
            });
        }

    };
    this.destroy = function() {
        if (typeof(window.ftreeVue) !== 'undefined') {
            window.ftreeVue = null;
        }
    };
};