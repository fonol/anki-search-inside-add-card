from aqt.qt import *
import aqt
import aqt.webview
import typing
from typing import List, Dict, Any, Optional, Tuple


from ..state import check_index, get_index
from ..special_searches import get_random_notes
from ..internals import requires_index_loaded
from ..output import UI
from ..tag_find import findBySameTag
from ..config import get_config_value

import state
import utility.misc



def handle(editor, cmd: str) -> bool:

    if cmd.startswith("siac-r-fld "):
        # keyup in fields -> search
        rerender_info(editor, cmd[10:])
        return True

    elif cmd.startswith("siac-r-srch-db "):
        # bottom search input used, so trigger either an add-on search or a browser search
        if get_index().searchbar_mode.lower() == "add-on":
            rerender_info(editor, cmd[15:])
        else:
            rerender_info(editor, cmd[15:], searchDB = True)
        return True

    elif cmd.startswith("siac-r-fld-selected ") and check_index():
        # selection in field or note
        rerender_info(editor, cmd[20:])
        return True

    elif cmd.startswith("siac-r-random-notes ") and check_index():
        # RANDOM clicked
        index               = get_index()
        stamp               = set_stamp()
        decks               = [s for s in cmd[19:].split(" ") if s != ""]
        index.lastSearch    = (None, decks, "random")
        UI.print_search_results(["Anki", "Random notes"],  get_random_notes(decks, index.limit), stamp)
        return True
    
    elif cmd.startswith("siac-r-search-tag "):
        search_by_tags(cmd[18:].strip())
        return True

    elif cmd.startswith("siac-tag-clicked ") and get_config_value("tagClickShouldSearch"):
        # clicked on a tag -> either trigger a search or add the tag to the tag bar
        state.last_search_cmd = cmd
        search_by_tags(cmd[17:].strip())
        return True


    return False

@requires_index_loaded
def rerender_info(editor: aqt.editor.Editor, content: str = "", searchDB: bool = False):
    """
    Main function that is executed when a user has typed or manually entered a search.
    Args:
        content: string containing the decks selected (did) + ~ + all input fields content / search masks content
    """
    index = get_index()

    if len(content) < 1:
        UI.empty_result("No results found for empty string")

    decks = []
    if "~" in content:
        decks = [s.strip() for s in content[:content.index('~')].split(',') if s.strip() != ""]

    if searchDB:
        content             = content[content.index('~ ') + 2:].strip()
        if len(content) == 0:
            UI.empty_result("No results found for empty string")
            return
        index.lastSearch    = (content, decks, "db")
        search_res          = index.searchDB(content, decks)
        if editor and editor.web:
            UI.print_search_results(["Anki", "Browser Search", content],  search_res["result"], search_res["stamp"], editor)

    else:
        if len(content[content.index('~ ') + 2:]) > 3000:
            UI.empty_result("Query was <b>too long</b>")
            return
        content             = content[content.index('~ ') + 2:]
        search_res          = index.search(content, decks)


@requires_index_loaded
def search_by_tags(query: str):
    """ Searches for notes with at least one fitting tag. """

    index               = get_index()
    stamp               = utility.misc.get_milisec_stamp()
    UI.latest           = stamp
    index.lastSearch    = (query, ["-1"], "tags")
    res                 = findBySameTag(query, index.limit, [], index.pinned)

    UI.print_search_results(["Anki", "Tag", query],  res["result"], stamp, UI._editor)


def set_stamp() -> Optional[str]:
    """
    Generate a milisec stamp and give it to the index.
    The result of a search is not printed if it has a non-matching stamp.
    """
    stamp     = utility.misc.get_milisec_stamp()
    UI.latest = stamp
    return stamp