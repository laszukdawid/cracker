import json
import logging
import pkgutil
from typing import Any, Dict, List, Optional

from PyQt5.QtWidgets import QCheckBox, QGridLayout, QLabel, QLineEdit, QWidget

from cracker.config import Configuration


class ParserConfig(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        self.config = Configuration()

        self.regex_config = {}

        self.layout = QGridLayout()
        self.setLayout(self.layout)

    def init(self):
        self.regex_config = self.config.regex_config
        self.create_options(self.regex_config)

    def confirm_action(self) -> List:
        self.check_update()
        return self.regex_config

    def clearLayout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def create_options(self, options):
        regex_config_options = RegexConfigOptions(options)
        self.layout.addWidget(regex_config_options, 0, 0, 1, 5)

    def check_update(self) -> None:
        """Iterate through every option and see it they're active"""
        assert self.regex_config, "Regex config hasn't been loaded"
        _layout = self.layout.itemAtPosition(0, 0).widget().layout
        for row in range(1, _layout.rowCount()):
            active_box = _layout.itemAtPosition(row, RegexConfigOptions.ACTIVE_POS).widget()
            key_box = _layout.itemAtPosition(row, RegexConfigOptions.KEY_POS).widget()
            value_box = _layout.itemAtPosition(row, RegexConfigOptions.VALUE_POS).widget()
            name_widget = _layout.itemAtPosition(row, RegexConfigOptions.NAME_POS).widget()
            name = name_widget.text()

            # TODO: Oopsy! Can't change name!
            if name in self.regex_config:
                self.regex_config[name]["active"] = active_box.isChecked()
                self.regex_config[name]["key"] = key_box.text()
                self.regex_config[name]["value"] = value_box.text()


class RegexConfigOptions(QWidget):
    ACTIVE_POS = 1
    NAME_POS = 2
    KEY_POS = 6
    VALUE_POS = 10

    def __init__(self, options: Dict[str, Any]):
        super().__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # Always add header
        self.create_header()

        for num, (_, option) in enumerate(options.items()):
            self.create_config_row(option, num + 1)

    def create_header(self, row_num: int = 0) -> None:
        self.layout.addWidget(QLabel("Active"), row_num, self.ACTIVE_POS)
        self.layout.addWidget(QLabel("Name"), row_num, self.NAME_POS, 1, 4)
        self.layout.addWidget(QLabel("Key"), row_num, self.KEY_POS, 1, 4)
        self.layout.addWidget(QLabel("Value"), row_num, self.VALUE_POS, 1, 4)

    def create_config_row(self, options: Dict, row_num: int) -> None:
        active = options.get("active", False)
        name = options.get("name", "undefined")
        key = options.get("key", "")
        value = options.get("value", "")

        active_widget = QCheckBox()
        active_widget.setChecked(active)
        self.layout.addWidget(active_widget, row_num, self.ACTIVE_POS)

        name_widget = QLineEdit(name)
        self.layout.addWidget(name_widget, row_num, self.NAME_POS, 1, 4)

        key_widget = QLineEdit(key)
        self.layout.addWidget(key_widget, row_num, self.KEY_POS, 1, 4)

        value_widget = QLineEdit(value)
        self.layout.addWidget(value_widget, row_num, self.VALUE_POS, 1, 4)
