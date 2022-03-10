

window.SIAC.fetch = new function() {

    var _waiting = {};
    var _sep     = '$&&$';

    this.json = function(...resourceArgs) {
        let key  = Date.now()+ '-' + resourceArgs.join(' ').split("").reduce(function(a,b){a=((a<<5)-a)+b.charCodeAt(0);return a&a},0);
        let promise = new Promise(function(resolve, reject) {
            _waiting[key] = resolve;
        });
        pycmd('siac-fetch-json ' + key + ' ' + resourceArgs.join(_sep));
        return promise;
    };

    this.callback = function(key, json) {
        if (!key in _waiting) {
            console.log("[SIAC] key not in fetch callback dict");
            return;
        }
        _waiting[key](json);
        delete _waiting.key;
    };
};
