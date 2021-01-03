from aqt.qt import *
from aqt import mw

import state
from ...config import get_config_value, update_config


class GeneralSettingsTab(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.setup_values()
        self.setup_ui()

    def setup_values(self):
        self.previous_autofilltags        = get_config_value("pdf.onOpen.autoFillTagsWithPDFsTags")
        self.previous_autofillsource      = self.list_to_string(get_config_value("pdf.onOpen.autoFillFieldsWithPDFName"))
        self.previous_autofillsource_bool = get_config_value("pdf.onOpen.autoFillSourceFieldsBool")
        pass

    def list_to_string(self, inputlist):
        return "; ".join(inputlist)

    def string_to_list(self, inputstring):
        return inputstring.split("; ")

    def toggle_autofill_source_field(self, boolean):
        self.le_autofillsource.setEnabled(boolean)


    def setup_ui(self):
        vbox = QVBoxLayout()


        vbox.addWidget(QLabel("<b>Add Cards</b><br>"))

        self.cb_autofilltags = QCheckBox("Auto-fill tag field with tags from SIAC note")
        self.cb_autofilltags.setChecked(self.previous_autofilltags)
        vbox.addWidget(self.cb_autofilltags)

        fields_hbox = QHBoxLayout()
        self.cb_autofillsource_bool = QCheckBox("Auto-fill fields with SIAC title (Syntax: field1; field2):")
        self.cb_autofillsource_bool.setChecked(self.previous_autofillsource_bool)
        self.cb_autofillsource_bool.stateChanged.connect(self.toggle_autofill_source_field)

        fields_hbox.addWidget(self.cb_autofillsource_bool)
        self.le_autofillsource = QLineEdit()
        self.le_autofillsource.setText(self.previous_autofillsource)
        self.le_autofillsource.setEnabled(self.previous_autofillsource_bool)
        fields_hbox.addWidget(self.le_autofillsource)
        vbox.addLayout(fields_hbox)


        vbox.setAlignment(Qt.AlignTop)
        self.setLayout(vbox)

    def save_changes(self):
        return_string = ""

        autofill_tags = self.cb_autofilltags.isChecked()
        autofill_fields_bool = self.cb_autofillsource_bool.isChecked()
        autofill_fields = self.le_autofillsource.text()

        if autofill_tags != self.previous_autofilltags:
            update_config("pdf.onOpen.autoFillTagsWithPDFsTags", autofill_tags)
            if autofill_tags:
                return_string += "Enabled auto-fill tags. "
            else:
                return_string += "Disabled auto-fill tags. "

        if autofill_fields_bool != self.previous_autofillsource_bool:
            update_config("pdf.onOpen.autoFillSourceFieldsBool", autofill_fields_bool)
            if autofill_fields_bool:
                return_string += "Enabled auto-fill source. "
            else:
                return_string += "Disabled auto-fill source. "

        if autofill_fields != self.previous_autofillsource:
            list = self.string_to_list(autofill_fields)
            update_config("pdf.onOpen.autoFillFieldsWithPDFName", list)
            return_string += f"Changed source fields: {autofill_fields}"


        return return_string
