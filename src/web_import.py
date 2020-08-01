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


import urllib.request
import typing
import re
from typing import Optional
from bs4 import BeautifulSoup, Comment
from requests import get

import utility.misc


def _fetch(url: str) -> BeautifulSoup:
    html    = ""
    req     = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}) 

    with urllib.request.urlopen(req) as response:
        html = response.read()

    page    = BeautifulSoup(html, "html.parser")

    for ignored_tag in ["script", "img", "input", "button", "style", "font", "iframe", "object", "embed"]:
        for tag in page.find_all(ignored_tag):
            tag.decompose()

    for tag in page.find_all(recursive=True):
        for attribute in ["class", "id", "name", "style", "role", "lang", "dir", "href", "src"]:
            del tag[attribute]
        for attribute in list(tag.attrs):
            if attribute.startswith("data-"):
                del tag.attrs[attribute]

    for node in page.find_all(text=lambda s: isinstance(s, Comment)):
        node.extract()

    return page

def import_webpage(url: str, inline_images: bool = False) -> Optional[str]:
    if url is None or len(url.strip()) == 0:
        return None
    try:
        webpage = _fetch(url)

    except Exception as e:
        return None
    
    body = "\n".join(map(str, webpage.find('body').children))

    base_path   = url.rsplit('/', 1)[0]
    if inline_images:
        body        = utility.misc.try_inline_images(body, base_path)
    # else:
    #     images = utility.misc.find_all_images(body)
    #     for i in images:
    #         url = re.search("src=(\"[^\"]+\"|'[^']+')", i, flags=re.IGNORECASE).group(1)[1:-1]
    #         if not url.startswith("http"):
    #             url = f"{base_path}{url}"
    #         body = body.replace(i, f"<img src='{url}'/>")

    return body