import os

from ssml import SSML
from .abstract_speaker import AbstractSpeaker

class Espeak(AbstractSpeaker):
    """
    Uses Unix `espeak` command line interfrace.
    """

    def read_text(self, text, voiceid, rate, volume_text):
        ssml = SSML(text, rate=rate, volume=volume_text)

        os.system("espeak '{text}'".format(text=text))

