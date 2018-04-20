import logging
import subprocess

from .abstract_speaker import AbstractSpeaker


class Espeak(AbstractSpeaker):
    """
    Uses Unix `espeak` command line interfrace.
    """

    _logger = logging.getLogger(__name__)

    def read_text(self, text, voiceid, rate, volume_text):
        text = self.clean_text(text)
        subprocess.call(["espeak", text])

