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

from urllib.request import urlopen
from bs4 import BeautifulSoup
import re

"""
Not used atm.
"""

class FeedMessage:

    def __init__(self, title, text, date, link, categories):
        self.title = title
        self.text = text
        self.date = date
        self.link = link
        self.categories = categories



def read(url):

    xml = urlopen(url)
    xml_page = xml.read()
    xml.close()
    sp = BeautifulSoup(xml_page, "html.parser")
    res = sp.findAll("item")
    r_list = []
    for item in res:
        categories = []
        link_following = False
        for c in item.contents:
            if isinstance(c, str):
                if link_following:
                    link = c
                    link_following = False
                else:
                    continue
            elif c.name == "title":
                title = c.text
            elif c.name == "pubdate":
                date = c.text
            elif c.name == "category":
                if len(c.text) > 0:
                    categories.append(c.text)
            elif c.name == "link":
                link_following = True
            elif c.name.lower() in ["text","description","summary","content","content:encoded"]:
                text = clean_feed_html(c.text)
        #elif hasattr(feed, 'description'):
        #    text = feed.description.text
        #date = feed.pubDate.text
        link = link or ""
        r_list.append(FeedMessage(title, text, date, link, categories))
    return r_list


def clean_feed_html(html):
    if html is None or len(html) == 0:
        return ""
    html = re.sub("(?:id|class|style|name|alt|data)=['\"][^'\"]+['\"]", "", html, flags=re.I)
    return html