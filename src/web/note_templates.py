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

"""
HTML templates for search results.
"""
from aqt import mw
config = mw.addonManager.getConfig(__name__)

noteTemplate = """<div class='cardWrapper {grid_class}' id='nWr-{counter}'>
                    <div class='topLeftWr'>
                        <div id='cW-{nid}' class='rankingLbl' onclick="expandRankingLbl(this)">{counter}<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                        {ret}
                    </div>
                    <div id='btnBar-{nid}' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='editLbl' onclick='edit({nid})'>Edit</div>
                        <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                        <div id='pin-{nid}' class='pinLbl unselected' onclick='pinCard(this, {nid})'><span>&#128204;</span></div>
                        %s
                        <div id='rem-{nid}' class='remLbl' onclick='removeNote({nid})'><span>&times;</span></div>
                    </div>
                    <div class='cardR' onmouseup='getSelectionText()' onmouseenter='cardMouseEnter(this, {nid})' onmouseleave='cardMouseLeave(this, {nid})' id='{nid}' data-nid='{nid}'>{text}</div>
                    <div id='tags-{nid}'  style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' onclick='expandCard({nid}, this)'>&nbsp;INFO&nbsp;</div>
                </div>""" % ("<div class='floatLbl' onclick='addFloatingNote({nid})'>&#10063;</div>" if config["results.showFloatButton"] else "")

noteTemplateSimple = """<div class='cardWrapper' style="display: block;">
                    <div class='topLeftWr'>
                        <div class='rankingLbl'>{counter}<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                        {ret}
                    </div>
                    <div class='btnBar' id='btnBarSmp-{nid}' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='editLbl' onclick='edit({nid})'>Edit</div>
                    </div>
                    <div class='cardR' onmouseup='{mouseup}'  onmouseenter='cardMouseEnter(this, {nid}, "simple")' onmouseleave='cardMouseLeave(this, {nid}, "simple")'>{text}</div>
                    <div style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' onclick='expandCard({nid}, this)'>&nbsp;INFO&nbsp;</div>
                </div>"""

noteTemplateUserNoteSimple = """<div class='cardWrapper' style="display: block;">
                    <div class='topLeftWr'>
                        <div class='rankingLbl'>{counter}<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                    </div>
                    <div class='btnBar' id='btnBarSmp-{nid}' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='editLbl' onclick='pycmd("siac-edit-user-note {nid}")'>Edit</div>
                    </div>
                    <div class='cardR' onmouseup='{mouseup}'  onmouseenter='cardMouseEnter(this, {nid}, "simple")' onmouseleave='cardMouseLeave(this, {nid}, "simple")'>{text}</div>
                    <div style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' style='display: none' onclick=''></div>
                </div>"""

noteTemplateUserNote = """<div class='cardWrapper siac-user-note {pdf_class} {grid_class}' id='nWr-{counter}'>
                    <div class='topLeftWr'>
                        <div id='cW-{nid}' class='rankingLbl' onclick='pycmd("siac-copy-to-cb {nid}")'>{counter} &nbsp;SIAC<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                    </div>
                    <div id='btnBar-{nid}' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='deleteLbl' onclick='pycmd("siac-delete-user-note-modal {nid}"); '><div class='siac-trash-icn'></div></div>
                        <div class='editLbl' onclick='pycmd("siac-edit-user-note {nid}")'>Edit</div>
                        <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                        <div id='pin-{nid}' class='pinLbl unselected' onclick='pinCard(this, {nid})'><span>&#128204;</span></div>
                        %s 
                        <div id='rem-{nid}' class='remLbl' onclick='removeNote({nid})'><span>&times;</span></div>
                    </div>
                    <div class='cardR siac-user-note' onmouseup='{mouseup}' onmouseenter='cardMouseEnter(this, {nid})' onmouseleave='cardMouseLeave(this, {nid})' id='{nid}' data-nid='{nid}'>{text}</div>
                    <div id='tags-{nid}'  style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' onclick='pycmd("siac-read-user-note {nid}")'><div class='siac-read-icn'></div>{progress}</div>
                </div>""" % ("<div class='floatLbl' onclick='addFloatingNote({nid})'>&#10063;</div>" if config["results.showFloatButton"] else "")
