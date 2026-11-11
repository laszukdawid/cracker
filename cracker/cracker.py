import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QApplication

from cracker.audio_player import AudioPlayer
from cracker.config import Configuration
from cracker.config.configuration import DEFAULT_SHORTCUTS
from cracker.cracker_gui import MainWindow
from cracker.selection import SelectionReader
from cracker.speaker.abstract_speaker import AbstractSpeaker
from cracker.speaker.espeak import Espeak
from cracker.speaker.frogger import Frogger
from cracker.speaker.google import Google
from cracker.speaker.polly import Polly
from cracker.text_parser import TextParser
from cracker.utils import get_logger

if TYPE_CHECKING:
    from cracker.keylogger import KeyBoardManager


class Cracker(object):
    """Logic for running the Cracker program"""

    SPEAKER: dict[str, type[AbstractSpeaker]] = {
        speaker.__name__.lower(): speaker for speaker in [Polly, Espeak, Google, Frogger]
    }
    _logger = get_logger(__name__)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app

        self.config = Configuration()
        _ = self.config.read_config()

        self.player = AudioPlayer()
        self.speaker: AbstractSpeaker = self.get_speaker(self.config.speaker, self.player)
        self.text_parser = TextParser()

        self.gui = MainWindow(self.config, speakers=self.SPEAKER)
        self.gui.speaker = self.speaker
        self.gui.player = self.player
        # Pass speaker reference to config window
        self.gui.config_window.speaker = self.speaker

        # Created after the window shows: importing pynput loads AppKit and Quartz (~250 ms).
        self.key_manager: KeyBoardManager | None = None
        self._closed = False
        clipboard = self.app.clipboard()
        assert clipboard is not None
        self.selection_reader = SelectionReader(clipboard)

        # Event on closing GUI application
        self.gui.closeAppEvent.connect(self._close)

        self._last_pid = None

    def _close(self):
        "Handles closing whole application"
        self._closed = True
        if self.key_manager is not None:
            self.key_manager.stop()
        self.selection_reader.shutdown()
        self.speaker.shutdown()  # cancels synthesis and removes this session's audio files

    def get_speaker(self, speaker_name, player) -> AbstractSpeaker:
        config = self.config.read_config()
        _name = speaker_name.lower()
        if _name == Polly.__name__.lower():
            self._logger.info("Using AWS Polly")
            return Polly(player)
        elif _name == Google.__name__.lower():
            self._logger.info("Using Google TTS")
            credentials_file = config.get("google", {}).get("credentials_file")
            self._logger.debug("Using credentials file: %s", credentials_file)
            return Google(player, credentials_file)
        elif _name == Espeak.__name__.lower():
            self._logger.info("Using ESpeak")
            return Espeak(player)
        elif _name == Frogger.__name__.lower():
            self._logger.info("Using Frogger")
            return Frogger(player)
        # if speaker:
        #     return speaker(player)
        raise ValueError(f"No speaker was selected. Provided speaker name '{speaker_name}'")

    def run(self):
        self.gui.init()
        self.set_action()
        self.gui.show()

    def reduce_text(self):
        text = self.gui.textEdit.toPlainText()
        new_text = self.text_parser.reduce_text(text)
        self.gui.textEdit.setText(new_text)

    def reduce_cite(self):
        text = self.gui.textEdit.toPlainText()
        new_text = self.text_parser.reduce_cite(text)
        self.gui.textEdit.setText(new_text)

    def wiki_text(self):
        """Sets the text box with wikipedia specific cleaned text.
        Example of this is removing `citation needed` and other references.
        """
        text = self.gui.textEdit.toPlainText()
        text = self.text_parser.wiki_text(text)
        self.gui.textEdit.setText(text)

    def read_text_area(self):
        """Reads out text in the text_box with selected speaker."""
        self.stop_text()
        text = self.gui.textEdit.toPlainText()  # TODO: toHtml() gives more control

        self.text_parser.parser_rules = self.config.regex_config
        text = self.text_parser.reduce_text(text)
        self.gui.set_read_source("textarea", text)
        self._read(text)

    def toggle_read_text_clipboard(self):
        """Reads out text from the clipboard with selected speaker."""
        self._logger.debug("Reading text from clipboard")
        if self._is_reading():
            self.stop_text()
            self.player.stop()
        else:
            self.stop_text()
            # A selection read may have its Cmd+C copy on the clipboard; read once it's restored.
            self.selection_reader.when_idle(self._read_clipboard)

    def _read_clipboard(self):
        clipboard = self.app.clipboard()
        assert clipboard is not None
        text = clipboard.text()

        self.text_parser.parser_rules = self.config.regex_config
        text = self.text_parser.reduce_text(text)
        self.gui.set_read_source("clipboard", text)
        self._read(text)

    def toggle_read_selection(self):
        """Reads out the text selected in the frontmost app, or stops the current read."""
        self._logger.debug("Reading selected text")
        if self._is_reading():
            self.stop_text()
            self.player.stop()
        else:
            self.selection_reader.request()

    def _read_selection(self, text: str):
        if not text.strip():
            self.gui.show_notice("No selected text found.")
            return
        self.stop_text()
        self.text_parser.parser_rules = self.config.regex_config
        text = self.text_parser.reduce_text(text)
        self.gui.set_read_source("clipboard", text)
        self._read(text)

    def _start_global_shortcuts(self):
        if self._closed:
            return
        try:
            self._listen_for_global_shortcuts()
        except Exception as exc:
            # Runs from a Qt timer, where an uncaught exception aborts the whole app.
            self._logger.exception("Global shortcuts are unavailable")
            if self.key_manager is not None:
                self.key_manager.stop()
            self.gui.show_notice(f"Global shortcuts are unavailable: {exc}")

    def _listen_for_global_shortcuts(self):
        if self.key_manager is None:
            self.key_manager = self._make_key_manager()
        manager = self.key_manager
        if self.config.shortcut_warning:
            self.gui.show_notice(self.config.shortcut_warning)
        shortcuts = self.config.shortcuts
        swallow = sys.platform == "darwin" and self._accessibility_trusted()
        try:
            manager.start(shortcuts["read_clipboard"], shortcuts["read_selection"], swallow)
        except ValueError as exc:
            self._logger.error("Invalid shortcut in config, using defaults: %s", exc)
            self.gui.show_notice(f"Invalid shortcut in config, using defaults: {exc}")
            manager.start(DEFAULT_SHORTCUTS["read_clipboard"], DEFAULT_SHORTCUTS["read_selection"], swallow)

    def _make_key_manager(self) -> "KeyBoardManager":
        from cracker.keylogger import KeyBoardManager

        manager = KeyBoardManager(self.app)
        manager.GlobalReadSignal.connect(self.toggle_read_text_clipboard)
        manager.SelectionReadSignal.connect(self.toggle_read_selection)
        return manager

    @staticmethod
    def _accessibility_trusted() -> bool:
        from cracker import selection_macos

        return selection_macos.is_trusted(prompt=False)

    def _is_reading(self) -> bool:
        """Playing, waiting for the next chunk, or still synthesising the first one."""
        return (
            self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            or self.player.waiting_for_segment
            or self.speaker.is_synthesizing
        )

    def _read(self, text):
        self._logger.debug(f"Reading text: {text}")
        speaker_config = self._prepare_config()
        self._last_pid = self.speaker.read_text(text, **speaker_config)

    def toggle_read(self):
        if self.player.is_paused:
            self.player.play()
        else:
            self.player.pause()

    def stop_text(self):
        self.selection_reader.cancel()
        self.speaker.stop_text()
        self.player.stop()

    def _prepare_config(self):
        config = dict(rate=self.gui.rate, volume=self.gui.volume, voice=self.gui.config.voice)
        return config

    def change_speaker(self, speaker_name):
        """Action on changing speaker.

        Important: Each speaker has its own configuration. These values should be updated on change.
        """
        # Creating a speaker reloads the shared config from disk, which would drop an unsaved change.
        self.gui.flush_pending_save()
        self.speaker.shutdown()  # its synthesis would otherwise still play; also frees its files
        self.speaker = self.get_speaker(speaker_name, self.player)
        self.gui.change_speaker(speaker_name, self.speaker)

    def set_action(self):
        self.gui.stop_action.triggered.connect(self.stop_text)
        self.gui.read_action.triggered.connect(self.read_text_area)
        self.gui.clipboard_read_action.triggered.connect(self.toggle_read_text_clipboard)
        self.gui.toggle_action.triggered.connect(self.toggle_read)
        self.gui.reduce_action.triggered.connect(self.reduce_text)
        self.gui.wiki_action.triggered.connect(self.wiki_text)
        self.gui.cite_action.triggered.connect(self.reduce_cite)
        self.gui.speakerW.currentTextChanged.connect(self.change_speaker)

        self.selection_reader.textReady.connect(self._read_selection)
        self.selection_reader.failed.connect(self.gui.show_notice)
        # Runs once the event loop starts, so the window appears before pynput loads.
        QTimer.singleShot(0, self._start_global_shortcuts)
