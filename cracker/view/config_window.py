import logging

from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout, QWidget

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

        # Tabs rendered as a segmented (pill) control via the global stylesheet.
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        tab_bar = self.tabs.tabBar()
        if tab_bar is not None:
            tab_bar.setExpanding(False)

        self.parser_tab = ParserConfig()
        self.tabs.addTab(self.parser_tab, "Parser")

        self.speakers_tab = SpeakerConfig()
        self.tabs.addTab(self.speakers_tab, "Speakers")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(10)
        self._layout.addWidget(self.tabs)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.released.connect(self.cancel_action)
        self.confirm_btn = QPushButton("OK")
        self.confirm_btn.setObjectName("primary")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.released.connect(self.confirm_action)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.confirm_btn)
        self._layout.addLayout(footer)

        self.resize(560, 460)

    def init(self):
        self._logger.debug("Init config window")
        self.parser_tab.init()

    def cancel_action(self):
        self.hide()

    def confirm_action(self):
        self._logger.debug("Confirm action")
        self.config.regex_config = self.parser_tab.confirm_action()
        if not self.speakers_tab.confirm_action():
            return

        # Reload Polly client if speaker is Polly and it has a reload method
        if self.speaker and hasattr(self.speaker, "reload_client"):
            try:
                self._logger.debug("Reloading Polly client with updated configuration")
                self.speaker.reload_client()
            except Exception as e:
                self._logger.error("Failed to reload Polly client: %s", e)

        self.hide()
