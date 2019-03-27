import platform
import os
import json
import re
from aqt import mw
from .textutils import cleanSynonym

#css + js + hvrBox
all = """
<style>
%s
</style>

 <div id="hvrBox">
    <div class='hvrLeftItem' id='hvrI-0'></div>
    <div class='hvrLeftItem' id='hvrI-1'></div>
    <div class='hvrLeftItem' id='hvrI-2'>last note</div>
    <div id="wiki"></div>
 </div>

<div id="hvrBoxSub">

</div>

<script>
%s
</script>
"""


synonymEditor = """
    <div style='max-height: 300px; overflow-y: auto; padding-right: 10px;'>
        <table id='synTable' style='width: 100%%;'>
            <thead><tr style='margin-bottom: 20px;'><th style='word-wrap: break-word; max-width: 100px;'>Set</th><th style='width: 100px; text-align: center;'></th></thead>
            %s
        </table>
    </div>
    <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
"""

config = mw.addonManager.getConfig(__name__)

def getSynonymEditor():
    synonyms = loadSynonyms()
    st = ""
    for c, sList in enumerate(synonyms):
        st += "<tr><td><div contenteditable='true' onkeydown='synonymSetKeydown(event, this, %s)'>%s</div></td><td style='text-align: right;'><button class='modal-close' onclick='pycmd(\"deleteSynonyms %s\")'>Delete</button></td></tr>" % (c, ", ".join(sList), c)
    if not synonyms:
        return """No synonyms defined yet. Input a set of terms, separated by ',' and hit enter.
        <input type='text' id='synonymInput' onkeyup='synInputKeyup(event, this)'/>
        """
    return synonymEditor % st

def saveSynonyms(synonyms):
    filtered = []
    for sList in synonyms:
        filtered.append(sorted(sList))
    
    # dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    # with open(dir + '/synonyms.json', 'w') as outfile:
    #     json.dump(filtered, outfile)
    config["synonyms"] = filtered
    mw.addonManager.writeConfig(__name__, config)

def newSynonyms(sListStr):
    existing = loadSynonyms()
    sList = [cleanSynonym(s) for s in sListStr.split(",") if len(cleanSynonym(s)) > 1]
    if not sList:
        return
    found = []
    foundIndex = []
    for c, eList in enumerate(existing):
        for s in sList:
            if s in eList:
                found += eList
                foundIndex.append(c)
    if found:
        existing = [i for j, i in enumerate(existing) if j not in foundIndex]
        existing.append(list(set(sList + found)))
    else:
        existing.append(sList)
    saveSynonyms(existing)

def deleteSynonymSet(cmd):
    index = int(cmd.strip())
    existing = loadSynonyms()
    if index >= 0 and index < len(existing):
        existing.pop(index)
    saveSynonyms(existing)

def editSynonymSet(cmd):
    index = int(cmd.strip().split()[0])
    existing = loadSynonyms()
    existing.pop(index)
    sList = [cleanSynonym(s) for s in cmd[len(cmd.strip().split()[0]):].split(",") if len(cleanSynonym(s)) > 1]
    if not sList:
        return
    found = []
    foundIndex = []
    for c, eList in enumerate(existing):
        for s in sList:
            if s in eList:
                found += eList
                foundIndex.append(c)
    if found:
        existing = [i for j, i in enumerate(existing) if j not in foundIndex]
        existing.append(list(set(sList + found)))
    else:
        existing.append(sList)
    saveSynonyms(existing)

def loadSynonyms():
    # dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    # if not os.path.exists(dir + '/synonyms.json'):
    #     open(dir + '/synonyms.json', 'w').close() 
    
    # with open(dir + '/synonyms.json') as s_file:  
    #     try:
    #         synonyms = json.load(s_file)
    #     except:
    #         synonyms = []

    try:
        synonyms = config['synonyms']
    except KeyError:
        synonyms = []

    return synonyms


def getScriptPlatformSpecific(addToHeight, delayWhileTyping):
    
    #get path 
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    
    with open(dir + "/scripts.js") as f:
        script = f.read()
    with open(dir + "/styles.css") as f:
        css = f.read().replace("%", "%%")
    script = script.replace("$del$", str(delayWhileTyping))
    script = script.replace("$h-1$", str(108 - addToHeight))
    script = script.replace("$h-2$", str(280 - addToHeight))
    
    #replace command key with meta key for mac
    cplatform = platform.system().lower()
    if cplatform == "darwin":
        script = script.replace("event.ctrlKey", "event.metaKey")
    else:
        css = re.sub(r'/\*MAC\*/(.|\n|\r\n)*/\*ENDMAC\*/', "", css, re.S)
    return all % (css, script)



