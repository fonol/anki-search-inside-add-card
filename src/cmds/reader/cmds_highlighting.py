import typing

from ...web.reading_modal import Reader
from ...notes import insert_highlights, delete_highlight, update_text_comment_coords, update_text_comment_text


def handle(editor, cmd: str) -> bool:

    if cmd.startswith("siac-hl-clicked "):
        # highlight btn clicked -> store current highlight color in reading modal
        id      = int(cmd.split()[1])
        color   = " ".join(cmd.split()[2:])
        Reader.highlight_color = color
        Reader.highlight_type = id
        return True

    elif cmd.startswith("siac-pdf-page-loaded "):
        # page loaded, so load highlights from db
        page = int(cmd.split()[1])
        Reader.show_highlights_for_page(page)
        return True

    elif cmd.startswith("siac-hl-new "):
        # highlights created, save to db
        # order is page group type [x0,y0,x1,y1]+ # text
        page    = int(cmd.split(" ")[1])
        group   = int(cmd.split(" ")[2])
        type    = int(cmd.split(" ")[3])
        nid     = Reader.note_id
        all     = []
        # [(nid,page,group,type,text,x0,y0,x1,y1)]
        text = cmd[cmd.index("#") + 1:]
        for ix, i in enumerate(cmd.split(" ")[4:]):
            if i == "#":
                break
            if ix % 4 == 0:
                x0 = float(i[:10])
            elif ix % 4 == 1:
                y0 = float(i[:10])
            elif ix % 4 == 2:
                x1 = float(i[:10])
            else:
                y1 = float(i[:10])
                all.append((nid,page,group,type,text,x0,y0,x1,y1))
        insert_highlights(all)
        Reader.show_highlights_for_page(page)
        return True

    elif cmd.startswith("siac-hl-del "):
        # delete highlight with given id
        id = int(cmd.split()[1])
        delete_highlight(id)
        return True

    elif cmd.startswith("siac-hl-text-update-coords "):
        # text comment was resized, so update coords in db
        id = int(cmd.split()[1])
        x0 = float(cmd.split()[2])
        y0 = float(cmd.split()[3])
        x1 = float(cmd.split()[4])
        y1 = float(cmd.split()[5])
        update_text_comment_coords(id, x0, y0, x1, y1)
        return True

    elif cmd.startswith("siac-hl-text-update-text "):
        # text comment content has changed, so update in db
        id      = int(cmd.split()[1])
        page    = int(cmd.split()[2])
        text    = " ".join(cmd.split(" ")[3:])

        update_text_comment_text(id, text)
        Reader.show_highlights_for_page(page)
        return True

    return False