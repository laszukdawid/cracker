import logging
import os
import signal
import subprocess

from .abstract_speaker import AbstractSpeaker


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

    def __del__(self):
        self.stop_text()

    def read_text(self, text, **config):
        command = ["espeak"]
        command += self._process_config(**config)
        command.append(self.clean_text(text))
        self.pid = subprocess.Popen(command).pid
        return self.pid

    @staticmethod
    def _process_config(**config):
        options = []
        if "volume" in config:
            options += ['-a', str(config['volume'])]
        if 'rate' in config:
            options += ['-s', str(config['rate'])]
        return options

    def stop_text(self):
        if self.pid is not None:
            os.kill(self.pid, signal.SIGTERM)
            self.pid = None

