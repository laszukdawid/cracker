import logging
import os
import subprocess

from .abstract_speaker import AbstractSpeaker
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaPlaylist


class Espeak(AbstractSpeaker):
    """
    Uses Unix `espeak` command line interfrace.
    """

    _logger = logging.getLogger(__name__)

    MIN_VOLUME, MAX_VOLUME = 0, 200
    RATES = [80, 120, 160, 200, 240]
    VOLUMES = range(100)

    def __init__(self, rate=None, volume=100):
        self._rate = rate
        self._volume = volume
        self.pid = None
        self.player = QMediaPlayer()

    def __del__(self):
        self.stop_text()

    def read_text(self, text, **config):
        filepath = os.path.abspath(AbstractSpeaker.TMP_FILEPATH)
        command = ["espeak"]
        command += self._process_config(**config)
        command.append("'{}'".format(self.clean_text(text)))
        command += ["-w", filepath]
        self.pid = subprocess.Popen(command).pid
        self.play_file(filepath)
        return

    def play_file(self, filepath):
        """Plays mp3 file using UNIX cmd. Returns pid to the process."""
        url = QUrl.fromLocalFile(filepath)
        media = QMediaContent(url)
        self.player.setMedia(media)
        self.player.play()
        return

    def stop_text(self):
        self.player.stop()

    def pause_text(self):
        if self.player.state() == self.player.PausedState:
            self.player.play()
        else:
            self.player.pause()

    @staticmethod
    def _process_config(**config):
        options = []
        if "volume" in config:
            options += ['-a', str(config['volume'])]
        if 'rate' in config:
            options += ['-s', str(config['rate'])]
        if 'voice' in config:
            options += ['-v', str(config['voice'])]
        return options
