import logging

from PyQt5.QtWidgets import QGridLayout, QPushButton, QTabWidget, QWidget

from cracker.config import Configuration
from cracker.view.parser_config_tab import ParserConfig
from cracker.view.speaker_config_tab import SpeakerConfig


class ConfigWindow(QWidget):
    _logger = logging.getLogger(__name__)

    def __init__(self, speaker=None):
        super().__init__()

        self.config = Configuration()
        self.speaker = speaker
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

    def init(self):
        self._logger.debug("Init config window")
        self.parser_tab.init()

    def cancel_action(self):
        self.hide()

    def confirm_action(self):
        self._logger.debug("Confirm action")
        self.config.regex_config = self.parser_tab.confirm_action()
        self.speakers_tab.confirm_action()

        # Reload Polly client if speaker is Polly and it has a reload method
        if self.speaker and hasattr(self.speaker, "reload_client"):
            try:
                self._logger.debug("Reloading Polly client with updated configuration")
                self.speaker.reload_client()
            except Exception as e:
                self._logger.error("Failed to reload Polly client: %s", e)

        self.hide()

    def clearLayout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
