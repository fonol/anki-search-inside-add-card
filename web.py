import platform
import os
import re
from aqt.utils import showInfo


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



def getScriptPlatformSpecific():
    
    #get path 
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/web.py", "")
    
    with open(dir + "/scripts.js") as f:
        script = f.read()
    with open(dir + "/styles.css") as f:
        css = f.read().replace("%", "%%")
    #replace command key with meta key for mac
    cplatform = platform.system().lower()
    if cplatform == "darwin":
        script = script.replace("event.ctrlKey", "event.metaKey")
    else:
        css = re.sub(r'/\*MAC\*/(.|\n|\r\n)*/\*ENDMAC\*/', "", css, re.S)
    return all % (css, script)
