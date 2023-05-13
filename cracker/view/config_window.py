import logging

from PyQt5.QtWidgets import QGridLayout, QPushButton, QWidget, QTabWidget

from cracker.config import Configuration
from cracker.view.parser_config_tab import ParserConfig
from cracker.view.speaker_config_tab import SpeakerConfig


class ConfigWindow(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        self.config = Configuration()
        self.setWindowTitle("Configuration")

        self.tabs = QTabWidget()

        # Parser tab
        self.parser_tab = ParserConfig()
        self.tabs.addTab(self.parser_tab, "Parser")

        # Speakers tab
        self.speakers_tab = SpeakerConfig()
        self.tabs.addTab(self.speakers_tab, "Speakers")

        # Main layout
        self._layout = QGridLayout()
        self.setLayout(self._layout)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.released.connect(self.cancel_action)
        self.confirm_btn = QPushButton("Ok")
        self.confirm_btn.released.connect(self.confirm_action)

        self._layout.addWidget(self.tabs, 1, 0, 1, 4)
        self._layout.addWidget(self.cancel_btn, 2, 2)
        self._layout.addWidget(self.confirm_btn, 2, 3)

        self.resize(500, self.height())

    def init(self, regex_file_path=""):
        self._logger.debug("Init config window")
        self.parser_tab.init(regex_file_path)

    def cancel_action(self):
        self.hide()

    def confirm_action(self):
        self._logger.debug("Confirm action")
        self.config.regex_config = self.parser_tab.confirm_action()
        self.speakers_tab.confirm_action()
        self.hide()

    def clearLayout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
