import typing
from ..config import get_config_value
from ..md import *

import utility.text

def handle(editor, cmd: str) -> bool:

    if cmd.startswith("siac-create-md-file "):
        path    = utility.text.b64_decode_str(cmd.split()[1])
        name    = utility.text.b64_decode_str(cmd.split()[2])
        mdf     = get_config_value("md.folder_path").replace("\\", "/")
        create_md_file(mdf, path, name)
        return True
    
    elif cmd.startswith("siac-delete-md-file "):
        path    = utility.text.b64_decode_str(cmd.split()[1])
        mdf     = get_config_value("md.folder_path").replace("\\", "/")
        mdf     = mdf + "/" if not mdf.endswith("/") else mdf
        delete_md_file(mdf + path)
        return True
    
    elif cmd.startswith("siac-update-md-file "):
        path    = utility.text.b64_decode_str(cmd.split()[1])
        content = utility.text.b64_decode_str(cmd.split()[2])
        mdf     = get_config_value("md.folder_path").replace("\\", "/")
        mdf     = mdf + "/" if not mdf.endswith("/") else mdf
        update_markdown_file(mdf + path, content)
        return True

    return False