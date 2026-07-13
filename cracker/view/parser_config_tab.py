import logging
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from cracker.config import Configuration

# Column stretch factors (On is fixed width): Name / Key / Value.
_NAME_STRETCH = 11
_KEY_STRETCH = 14
_VALUE_STRETCH = 8
_ON_WIDTH = 44


class ParserConfig(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        self.config = Configuration()

        self.regex_config: dict[str, dict[str, Any]] = {}
        self.rows: list[dict[str, Any]] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

    def init(self):
        regex_config = self.config.regex_config
        assert regex_config is not None
        self.regex_config = regex_config
        self._build_table(self.regex_config)

    def confirm_action(self) -> dict[str, dict[str, Any]]:
        self.check_update()
        return self.regex_config

    def _build_table(self, options: dict[str, dict[str, Any]]) -> None:
        card = QFrame()
        card.setObjectName("card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        column = QVBoxLayout(card)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._header_row())
        for index, (_, option) in enumerate(options.items()):
            column.addWidget(self._rule_row(option, index))
        column.addStretch(1)

        self._layout.addWidget(card)

    def _header_row(self) -> QWidget:
        row_widget = QWidget()
        row_widget.setObjectName("tableHeader")
        row_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(12, 7, 12, 7)
        row.setSpacing(10)
        for text, stretch, width in (
            ("ON", 0, _ON_WIDTH),
            ("NAME", _NAME_STRETCH, 0),
            ("KEY", _KEY_STRETCH, 0),
            ("VALUE", _VALUE_STRETCH, 0),
        ):
            label = QLabel(text)
            label.setProperty("colhead", True)
            if width:
                label.setFixedWidth(width)
            row.addWidget(label, stretch)
        return row_widget

    def _rule_row(self, option: dict[str, Any], index: int) -> QWidget:
        row_widget = QWidget()
        row_widget.setProperty("zebra", "a" if index % 2 == 0 else "b")
        row_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(10)

        active_widget = QCheckBox()
        active_widget.setChecked(option.get("active", False))
        active_widget.setFixedWidth(_ON_WIDTH)
        row.addWidget(active_widget)

        name_widget = QLineEdit(option.get("name", ""))
        name_widget.setProperty("mono", True)
        row.addWidget(name_widget, _NAME_STRETCH)

        key_widget = QLineEdit(option.get("key", ""))
        key_widget.setProperty("mono", True)
        row.addWidget(key_widget, _KEY_STRETCH)

        value_widget = QLineEdit(option.get("value", ""))
        value_widget.setProperty("mono", True)
        value_widget.setPlaceholderText("—")
        row.addWidget(value_widget, _VALUE_STRETCH)

        self.rows.append(
            {
                "name": name_widget,
                "active": active_widget,
                "key": key_widget,
                "value": value_widget,
            }
        )
        return row_widget

    def check_update(self) -> None:
        """Push each row's widget values back into the regex config by name."""
        assert self.regex_config, "Regex config hasn't been loaded"
        for row in self.rows:
            # TODO: Oopsy! Can't change name!
            name = row["name"].text()
            if name in self.regex_config:
                self.regex_config[name]["active"] = row["active"].isChecked()
                self.regex_config[name]["key"] = row["key"].text()
                self.regex_config[name]["value"] = row["value"].text()
