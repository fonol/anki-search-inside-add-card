# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import io
import typing
from typing import Dict

from ..internals import HTML
import state

HTML_TEMPLATES = {}

def _load_template(name: str):
    global HTML_TEMPLATES

    folder = _template_folder()
    with open(f"{folder}{name}.html", "r") as tf:
        html = tf.read()
        HTML_TEMPLATES[name] = html

def filled_template(name: str, values: Dict[str, str]) -> HTML:
    """ Returns the given template with all {placeholders} filled out according to the given dict. """

    if state.dev_mode or not name in HTML_TEMPLATES:
        _load_template(name)
    tmp = HTML_TEMPLATES[name]
    for k,v in values.items():
        tmp = tmp.replace("{" + k + "}", str(v))
    return tmp

def _template_folder() -> str:
    """ Path ends with / """
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")
    if not dir.endswith("/"):
        return dir + "/templates/"
    return dir + "templates/"
