import typing
from ..config import update_config, get_config_value_or_default
from ..output import UI
from aqt.utils import tooltip


def handle(editor, cmd: str) -> bool:

    if cmd.startswith("siac-config-bool "):
        key = cmd.split()[1]
        b   = cmd.split()[2].lower() == "true" or cmd.split()[2].lower() == "on"
        update_config(key, b) 
        return True

    elif cmd.startswith("siac-scale "):
        factor      = float(cmd.split()[1])
        UI.scale    = factor

        update_config("noteScale", factor)

        if factor != 1.0:
            UI.js("SIAC.State.showTagInfoOnHover = false;")
        else:
            UI.js("SIAC.State.showTagInfoOnHover = true;")
        return True

    elif cmd.startswith("siac-left-side-width "):
        value = int(cmd.split()[1])
        if value > 70:
            tooltip("Value capped at 70%.")
            value = 70
        update_config("leftSideWidthInPercent", value)
        right = 100 - value
        UI.js("""document.getElementById('leftSide').style.width = '%s%%';
                    document.getElementById('siac-right-side').style.width = '%s%%';
                    document.getElementById('siac-partition-slider').value = '%s';
                    if (pdf.instance) {pdfFitToPage();}""" % (value, right, value) )
        return True

    elif cmd.startswith("siac-switch-left-right "):
        update_config("switchLeftRight", cmd.split()[1]  == "true")
        tooltip("Layout switched.")
        return True

    elif cmd.startswith("siac-zoom-"):
        # zoom in/out webview
        z       = get_config_value_or_default("searchpane.zoom", 1.0)
        delta   = 0.05 if cmd == "siac-zoom-in" else -0.05
        new     = round(min(max(0.3, z + delta), 2.0), 2)
        editor.web.setZoomFactor(new)
        add     = ""
        period  = 2000
        if int(new * 100) != 100:
            add     = "<br>Note: Currently, for zoom levels other than 100%,<br>rendered PDF text may be blurry sometimes."
            period  = 5000
        tooltip(f"""
            Set Zoom to <b>{str(int(new * 100))}%</b>.
            {add}
        """, period=period)
        update_config("searchpane.zoom", new)
        return True

    return False