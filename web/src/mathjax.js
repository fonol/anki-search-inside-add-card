window.MathJax = {
    tex: {
        displayMath: [["\\[", "\\]"]],
        processRefs: false,
        processEnvironments: false,
        packages: {
            "[+]": ["noerrors", "mhchem"],
        },
    },
    startup: {
        typeset: false,
        pageReady: () => {
            return MathJax.startup.defaultPageReady();
        },
    },
    options: {
        renderActions: {
            addMenu: [],
            checkLoading: [],
        },
        ignoreHtmlClass: "tex2jax_ignore",
        processHtmlClass: "siac-inner-card",
    },
    loader: {
        load: ["[tex]/noerrors", "[tex]/mhchem"],
    },

    
};
//http://docs.mathjax.org/en/latest/web/typeset.html#typeset-async
window._mathjaxActivePromise = Promise.resolve();

window.refreshMathJax = function() {
    if (typeof(MathJax) !== "undefined") { 
        if (typeof(MathJax.typesetPromise) !== 'undefined') {
            window._mathjaxActivePromise = window._mathjaxActivePromise.then(MathJax.typesetPromise); 
        } else {
            console.log("[SIAC] Mathjax typeset fn not found.");
        }
    } else { 
        console.log("[SIAC] Seems like MathJax is not loaded."); 
    }
};
