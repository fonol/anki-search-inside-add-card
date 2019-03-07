import platform
import os

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
    if platform.system().lower() == "darwin":
        script = script.replace("event.ctrlKey", "event.metaKey")
    
    return all % (css, script)
