import time
from aqt import mw
from .state import get_index, check_index


def perf_time(fn):
    """
        Decorator to measure function execution time.
    """
    def _perf_wrapper(*args, **kwargs):
        start = time.time() * 1000
        res = fn(*args, **kwargs)
        print(f"{fn.__name__}: {time.time() * 1000 - start}")
        return res
    return _perf_wrapper

def js(fn):
    """
        Decorator to execute the returned javascript of a function.
    """
    def _eval_js_dec(*args, **kwargs):
        ix = get_index()
        if ix is not None and ix.output is not None and ix.output.editor is not None and ix.output.editor.web is not None:
            ix.output.js(fn(*args, **kwargs))
        else:
            mw.app.activeWindow().editor.web.eval(fn(*args, **kwargs))
    return _eval_js_dec

def requires_index_loaded(fn):
    """
        Decorator to only enter a function if the index has been loaded.
    """
    def _check_ix(*args, **kwargs):
        if not check_index():
            return
        return fn(*args, **kwargs)
    return _check_ix