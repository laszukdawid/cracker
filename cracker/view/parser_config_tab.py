import logging
from typing import Any

from PyQt6.QtWidgets import QCheckBox, QGridLayout, QLabel, QLineEdit, QWidget

from cracker.config import Configuration


class ParserConfig(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        self.config = Configuration()

        self.regex_config: dict[str, dict[str, Any]] = {}

        self.grid_layout = QGridLayout()
        self.setLayout(self.grid_layout)

    def init(self):
        regex_config = self.config.regex_config
        assert regex_config is not None
        self.regex_config = regex_config
        self.create_options(self.regex_config)

    def confirm_action(self) -> dict[str, dict[str, Any]]:
        self.check_update()
        return self.regex_config

    def create_options(self, options):
        regex_config_options = RegexConfigOptions(options)
        self.grid_layout.addWidget(regex_config_options, 0, 0, 1, 5)

    def check_update(self) -> None:
        """Iterate through every option and see it they're active"""
        assert self.regex_config, "Regex config hasn't been loaded"
        options_item = self.grid_layout.itemAtPosition(0, 0)
        assert options_item is not None
        options_widget = options_item.widget()
        assert isinstance(options_widget, RegexConfigOptions)
        _layout = options_widget.grid_layout
        for row in range(1, _layout.rowCount()):
            active_item = _layout.itemAtPosition(row, RegexConfigOptions.ACTIVE_POS)
            key_item = _layout.itemAtPosition(row, RegexConfigOptions.KEY_POS)
            value_item = _layout.itemAtPosition(row, RegexConfigOptions.VALUE_POS)
            name_item = _layout.itemAtPosition(row, RegexConfigOptions.NAME_POS)
            assert active_item is not None
            assert key_item is not None
            assert value_item is not None
            assert name_item is not None
            active_box = active_item.widget()
            key_box = key_item.widget()
            value_box = value_item.widget()
            name_widget = name_item.widget()
            assert isinstance(active_box, QCheckBox)
            assert isinstance(key_box, QLineEdit)
            assert isinstance(value_box, QLineEdit)
            assert isinstance(name_widget, QLineEdit)
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

    def __init__(self, options: dict[str, dict[str, Any]]):
        super().__init__()

        self.grid_layout = QGridLayout()
        self.setLayout(self.grid_layout)

        # Always add header
        self.create_header()

        for num, (_, option) in enumerate(options.items()):
            self.create_config_row(option, num + 1)

    def create_header(self, row_num: int = 0) -> None:
        self.grid_layout.addWidget(QLabel("Active"), row_num, self.ACTIVE_POS)
        self.grid_layout.addWidget(QLabel("Name"), row_num, self.NAME_POS, 1, 4)
        self.grid_layout.addWidget(QLabel("Key"), row_num, self.KEY_POS, 1, 4)
        self.grid_layout.addWidget(QLabel("Value"), row_num, self.VALUE_POS, 1, 4)

    def create_config_row(self, options: dict[str, Any], row_num: int) -> None:
        active = options.get("active", False)
        name = options.get("name", "undefined")
        key = options.get("key", "")
        value = options.get("value", "")

        active_widget = QCheckBox()
        active_widget.setChecked(active)
        self.grid_layout.addWidget(active_widget, row_num, self.ACTIVE_POS)

        name_widget = QLineEdit(name)
        self.grid_layout.addWidget(name_widget, row_num, self.NAME_POS, 1, 4)

        key_widget = QLineEdit(key)
        self.grid_layout.addWidget(key_widget, row_num, self.KEY_POS, 1, 4)

        value_widget = QLineEdit(value)
        self.grid_layout.addWidget(value_widget, row_num, self.VALUE_POS, 1, 4)
