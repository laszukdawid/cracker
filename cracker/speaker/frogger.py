import requests
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlaylist

from cracker.speaker import FROGGER_LANGUAGES
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


class Frogger(AbstractSpeaker):
    """
    Uses Unix `espeak` command line interfrace.
    """

    _logger = get_logger(__name__)

    MIN_VOLUME, MAX_VOLUME = 0, 200
    RATES = [80, 120, 160, 200, 240]
    VOLUMES = range(100)

    LANGUAGES = FROGGER_LANGUAGES
    URL = "http://localhost:8000/tts"

    def __init__(self, player):
        self.player = player

    def __del__(self):
        self.stop_text()

    def read_text(self, text: str, **config) -> None:
        self._logger.debug("Reading test: %s", text)
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text(text)

        self._logger.debug("Requesting from local server")
        filepaths = []
        # TODO: This should obviously be asynchronous!
        for parted_text in split_text:
            filename = self.ask(parted_text, voice=config["voice"])
            filepaths.append(filename)
        # self.save_cache(ssml, filepaths, voice)

        print(filepaths)
        self.play_files(filepaths)
        return

    def play_files(self, filepaths):
        playlist = QMediaPlaylist(self.player)
        for filepath in filepaths:
            url = QUrl.fromLocalFile(filepath)
            playlist.addMedia(QMediaContent(url))
        self.player.setPlaylist(playlist)
        self.player.play()

    def stop_text(self):
        self.player.stop()

    def pause_text(self):
        if self.player.state() == self.player.PausedState:
            self.player.play()
        else:
            self.player.pause()

    def ask(self, text: str, voice: str):
        """Connect to local server on host localhost:5002 and extract wav from stream"""
        response = requests.get(self.URL, params={"text": text, "voice": voice})

        if response.status_code != 200:
            raise Exception(f"Error: Unexpected response {response}")
        return response.json()["filename"]
