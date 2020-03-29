#
# html templates for search results
#

noteTemplate = """<div class='cardWrapper {grid_class}' id='nWr-{counter}'>
                    <div class='topLeftWr'>
                        <div id='cW-{nid}' class='rankingLbl' onclick="expandRankingLbl(this)">{counter}<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                        {ret}
                    </div>
                    <div id='btnBar-{nid}' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='editLbl' onclick='edit({nid})'>Edit</div>
                        <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                        <div id='pin-{nid}' class='pinLbl unselected' onclick='pinCard(this, {nid})'><span>&#128204;</span></div>
                        <div class='floatLbl' onclick='addFloatingNote({nid})'>&#10063;</div>
                        <div id='rem-{nid}' class='remLbl' onclick='removeNote({nid})'><span>&times;</span></div>
                    </div>
                    <div class='cardR' onmouseup='getSelectionText()' onmouseenter='cardMouseEnter(this, {nid})' onmouseleave='cardMouseLeave(this, {nid})' id='{nid}' data-nid='{nid}'>{text}</div>
                    <div id='tags-{nid}'  style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' onclick='expandCard({nid}, this)'>&nbsp;INFO&nbsp;</div>
                </div>"""

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
                        <div id='cW-{nid}' class='rankingLbl'>{counter} &nbsp;SIAC<div class='rankingLblAddInfo'>{creation}</div><div class='editedStamp'>{edited}</div></div>
                    </div>
                    <div id='btnBar-{nid}' class='btnBar' onmouseLeave='pinMouseLeave(this)' onmouseenter='pinMouseEnter(this)'>
                        <div class='deleteLbl' onclick='pycmd("siac-delete-user-note-modal {nid}"); '><div class='siac-trash-icn'></div></div>
                        <div class='editLbl' onclick='pycmd("siac-edit-user-note {nid}")'>Edit</div>
                        <div class='srchLbl' onclick='searchCard(this)'><div class='siac-search-icn'></div></div>
                        <div id='pin-{nid}' class='pinLbl unselected' onclick='pinCard(this, {nid})'><span>&#128204;</span></div>
                        <div class='floatLbl' onclick='addFloatingNote({nid})'>&#10063;</div>
                        <div id='rem-{nid}' class='remLbl' onclick='removeNote({nid})'><span>&times;</span></div>
                    </div>
                    <div class='cardR siac-user-note' onmouseup='{mouseup}' onmouseenter='cardMouseEnter(this, {nid})' onmouseleave='cardMouseLeave(this, {nid})' id='{nid}' data-nid='{nid}'>{text}</div>
                    <div id='tags-{nid}'  style='position: absolute; bottom: 0px; right: 0px;'>{tags}</div>
                    <div class='cardLeftBot' onclick='pycmd("siac-read-user-note {nid}")'><div class='siac-read-icn'></div>{progress}</div>
                </div>"""
