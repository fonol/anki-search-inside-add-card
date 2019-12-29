from aqt import mw

search_index = None
contextEvt = None
corpus = None
deck_map = None
output = None
edit = None

old_on_bridge = None

def check_index():
    return search_index is not None and search_index.output is not None and search_index.output.editor is not None and search_index.output.editor.web is not None

def set_index(index):
    global search_index
    search_index = index

def get_index():
    return search_index

def corpus_is_loaded():
    return corpus is not None

def set_corpus(c):
    global corpus
    corpus = c

def get_corpus():
    return corpus

def set_edit(e):
    global edit
    edit = e

def get_edit():
    return edit

def set_deck_map(dm):
    global deck_map
    deck_map = dm

def set_old_on_bridge_cmd(fn):
    global old_on_bridge
    old_on_bridge = fn

def get_old_on_bridge_cmd():
    return old_on_bridge
    