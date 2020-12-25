from aqt.qt import *
from aqt import mw

from ...web.web import reload_styles

from aqt.utils import showInfo
from ...config import get_config_value_or_default, update_config

class ColorItem:

    def __init__(self, config_key, description, sort_id, default_value=""):

        self.config_key     = config_key
        self.description    = description
        self.sort_id        = sort_id
        self.previous_color = get_config_value_or_default(self.config_key, None)
        self.current_color  = self.previous_color
        self.color_button   = QPushButton()
        self.default_value  = default_value

        self.color_button.clicked.connect(self.get_new_color)
        self.change_button_color()


    def get_new_color(self):
        """Set color via color selection dialog"""

        dialog = QColorDialog()
        if self.default_value != "":
            dialog.setCustomColor(0, QColor(self.default_value))
        else:
            dialog.setCustomColor(0, QColor(self.current_color))
        color = dialog.getColor()

        if color.isValid():
            color = color.name()
            self.current_color = color
       
        self.change_button_color()

    def change_button_color(self):
        """Generate color preview pixmap and place it on button"""

        pixmap  = QPixmap(48, 18)
        qcolour = QColor(0, 0, 0)
        qcolour.setNamedColor(self.current_color)

        pixmap.fill(qcolour)
        self.color_button.setIcon(QIcon(pixmap))
        self.color_button.setIconSize(QSize(128, 18))
        self.color_button.setMaximumWidth(80)


class AppearanceSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setup_ui()

    def setup_ui(self):
        # setup vbox
        gridbox = QGridLayout()

        # group_ids, arbitrary
        id_tags         = 0
        id_highlight    = 1
        id_suspended    = 2
        id_modal        = 3
        id_general      = 4

        # group colors logically, this determines the order!
        list_order = ( # name of section, id
            ("General Colors",          id_general),
            ("Tag Colors",              id_tags),
            ("Highlight Colors",        id_highlight),
            ("Suspended Label Colors",  id_suspended),
            ("Reading Modal Colors ",   id_modal)
        )

        # add items
        self.color_list = (
            ColorItem("styles.primaryColor"                  , "Primary Color",              id_general, "#2e6286"),
            ColorItem("styles.night.primaryColor"            , "Primary Color (Night Mode)", id_general, "#2e6286"),
            ColorItem("styles.tagBackgroundColor"            , "Tag Background Color",              id_tags),
            ColorItem("styles.tagForegroundColor"            , "Tag Foreground Color",              id_tags),
            ColorItem("styles.night.tagBackgroundColor"      , "Tag Background Color (Night Mode)", id_tags),
            ColorItem("styles.night.tagForegroundColor"      , "Tag Foreground Color (Night Mode)", id_tags),

            ColorItem("styles.highlightForegroundColor"      , "Highlight Foreground Color", id_highlight),
            ColorItem("styles.highlightBackgroundColor"      , "Highlight Background Color", id_highlight),
            ColorItem("styles.night.highlightForegroundColor", "Highlight Foreground Color (Night Mode)", id_highlight),
            ColorItem("styles.night.highlightBackgroundColor", "Highlight Background Color (Night Mode)", id_highlight),

            ColorItem("styles.suspendedForegroundColor"      , "Suspended Foreground Color", id_suspended),
            ColorItem("styles.suspendedBackgroundColor"      , "Suspended Background Color", id_suspended),

            ColorItem("styles.modalBorderColor"              , "Modal Border Color", id_modal),
            ColorItem("styles.night.modalBorderColor"        , "Modal Border Color (Night Mode)", id_modal),
            ColorItem("styles.readingModalBackgroundColor"   , "Modal Background Color", id_modal)
        )

        line = -1

        for group_name, group_id in list_order:
            # initialise counter
            line += 1
            i = 0

            if line != 0:
                gridbox.addWidget(QLabel(" "), line, 0, 1, 6)
                line +=1

            # add header, colspan over all columns
            gridbox.addWidget(QLabel("""<b>""" + group_name + "</b></span>"), line, 0, 1, -1)
            line +=1

            # find colors
            for item in self.color_list:
                if item.sort_id is group_id:
                    # set up two columns, each with 4 elements (description, label, edit button, remove button)
                    column_shift = (i%2)*2

                    # reached new line
                    if column_shift == 0:
                        line +=1

                    gridbox.addWidget(QLabel(item.description), line, 0 + column_shift)
                    gridbox.addWidget(item.color_button, line, 1 + column_shift)

                    i+=1

            gridbox.setColumnStretch(0, 1)
            gridbox.setColumnStretch(2, 1)
            gridbox.setAlignment(Qt.AlignTop)


        self.setLayout(gridbox)

    def setupUi(self):
        grid                    = QGridLayout()

        self.colorcloze_btn     = QPushButton()
        self.colorextract_btn   = QPushButton()

        self.colorcloze_btn.clicked.connect(lambda _,
            t="color-cloze",   b=self.colorcloze_btn:   self.getNewColor(t, b))
        self.colorextract_btn.clicked.connect(lambda _,
            t="color-extract", b=self.colorextract_btn: self.getNewColor(t, b))

        grid.addWidget(QLabel("<b>Cloze color:</b>"),0,0)
        grid.addWidget(self.colorcloze_btn, 0, 1)
        grid.addWidget(QLabel("<b>Extract color:</b>"), 1,0)
        grid.addWidget(self.colorextract_btn, 1, 1)

        self.setLayout(grid)

    def save_changes(self):
        count_changes = 0

        for item in self.color_list:
            if item.previous_color is not item.current_color:
                update_config(item.config_key, item.current_color)
                count_changes += 1

        if count_changes == 0:
            return ""
        reload_styles()

        return str(count_changes) + " colors changed.<br>"
