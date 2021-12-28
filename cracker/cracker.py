import logging
from threading import Thread

from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QApplication

from cracker.configuration import Configuration
from cracker.cracker_gui import MainWindow
from cracker.keylogger import KeyBoardManager
from cracker.speaker.abstract_speaker import AbstractSpeaker
from cracker.speaker.espeak import Espeak
from cracker.speaker.polly import Polly
from cracker.text_parser import TextParser


class Cracker(object):
    """Logic for running the Cracker program"""

    SPEAKER = {Polly.__name__: Polly, Espeak.__name__: Espeak}
    _logger = logging.getLogger(__name__)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app

        self.config = Configuration()
        _ = self.config.read_config()

        self.player = QMediaPlayer()
        self.speaker: AbstractSpeaker = self.get_speaker(self.config.speaker, self.player)
        self.textParser = TextParser(config_path=self.config.parser_config)

        self.gui = MainWindow(self.config, speakers=self.SPEAKER)
        self.gui.speaker = self.speaker
        self.gui.player = self.player

        self.key_manager = KeyBoardManager(self.app)

        # Event on closing GUI application
        self.gui.closeAppEvent.connect(self._close)

        self._last_pid = None

    def _close(self):
        "Handles closing whole application"
        self.key_manager.stop()

    def get_speaker(self, speaker_name, player) -> AbstractSpeaker:
        if speaker_name == Polly.__name__:
            if "profile_name" in self.config.default_values:
                profile_name = self.config.default_values["profile_name"]
                return Polly(player, profile_name)
            else:
                return Polly(player)
        elif speaker_name == Espeak.__name__:
            return Espeak(player)
        raise ValueError(f"No speaker was selected. Provided speaker name '{speaker_name}'")

    def run(self):
        self.gui.init()
        self.set_action()
        self.gui.show()

    def reduce_text(self):
        text = self.gui.textEdit.toPlainText()
        new_text = self.textParser.reduce_text(text)
        self.gui.textEdit.setText(new_text)

    def reduce_cite(self):
        text = self.gui.textEdit.toPlainText()
        new_text = self.textParser.reduce_cite(text)
        self.gui.textEdit.setText(new_text)

    def wiki_text(self):
        """Sets the text box with wikipedia specific cleaned text.
        Example of this is removing `citation needed` and other references.
        """
        text = self.gui.textEdit.toPlainText()
        text = self.textParser.wiki_text(text)
        self.gui.textEdit.setText(text)

    def read_text_area(self):
        """Reads out text in the text_box with selected speaker."""
        self.stop_text()
        text = self.gui.textEdit.toPlainText()  # TODO: toHtml() gives more control

        self.textParser.parser_rules = self.config.regex_config
        text = self.textParser.reduce_text(text)
        self._read(text)

    def toggle_read_text_clipboard(self):
        """Reads out text from the clipboard with selected speaker."""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.stop_text()
            self.player.stop()
        else:
            self.stop_text()
            text = self.app.clipboard().text()

            self.textParser.parser_rules = self.config.regex_config
            text = self.textParser.reduce_text(text)
            self._read(text)

    def _read(self, text):
        speaker_config = self._prepare_config()
        self._last_pid = self.speaker.read_text(text, **speaker_config)

    def toggle_read(self):
        if self.player.state() == QMediaPlayer.PausedState:
            self.player.play()
        else:
            self.player.pause()

    def stop_text(self):
        self.speaker.stop_text()

    def _prepare_config(self):
        config = dict(rate=self.gui.rate, volume=self.gui.volume, voice=self.gui.config.voice)
        return config

    def change_speaker(self, speaker_name):
        """Action on changing speaker.

        Important: Each speaker has its own configuration. These values should be updated on change."""
        self.speaker = self.SPEAKER[speaker_name](self.player)
        self.gui.change_speaker(speaker_name)

    def set_action(self):
        self.gui.stop_action.triggered.connect(self.stop_text)
        self.gui.read_action.triggered.connect(self.read_text_area)
        self.gui.clipboard_read_action.triggered.connect(self.toggle_read_text_clipboard)
        self.gui.toggle_action.triggered.connect(self.toggle_read)
        self.gui.reduce_action.triggered.connect(self.reduce_text)
        self.gui.wiki_action.triggered.connect(self.wiki_text)
        self.gui.speakerW.currentTextChanged.connect(self.change_speaker)

        self.key_manager.GlobalReadSignal.connect(self.toggle_read_text_clipboard)

        args = (["space", "control", "shift"], )
        p = Thread(target=self.key_manager.run, args=args)
        p.start()
