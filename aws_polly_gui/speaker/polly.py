import logging
import subprocess
import boto3

from aws_polly_gui.ssml import SSML
from .abstract_speaker import AbstractSpeaker


class Polly(AbstractSpeaker):

    _logger = logging.getLogger(__name__)

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    def __init__(self):
        self.client = boto3.client('polly')
        self._cached_ssml = SSML()
        self._cached_filepath = ""

    def read_text(self, text, **config):
        """Reads out text."""
        text = self.clean_text(text)

        voiceid = config['voiceid'] if 'voiceid' in config else None
        rate = config['rate'] if 'rate' in config else None
        volume_text = config['volume_text'] if 'volume_text' in config else None
        ssml = SSML(text, rate=rate, volume=volume_text)

        if self._cached_ssml == ssml:
            self._logger.debug("Playing cached file")
            filepath = self._cached_filepath
        else:
            self._logger.debug("Re_cached_textquest from Polly")
            filepath = self.ask_polly(str(ssml), voiceid)
            self._cached_ssml, self._cached_filepath = ssml, filepath
        self.play_file(filepath)

    def ask_polly(self, ssml_text, voiceid):
        speech = self.create_speech(ssml_text, voiceid)
        response = self.client.synthesize_speech(**speech)
        filepath = self.save_mp3(response)
        return filepath

    @staticmethod
    def create_speech(ssml_text, voiceid):
        return dict(
            OutputFormat='mp3',
            TextType='ssml',
            Text=ssml_text,
            VoiceId=voiceid
        )

    @classmethod
    def save_mp3(cls, response):
        """Stores downloaded response as an mp3."""
        mp3 = response["AudioStream"].read()
        filename = "tmp.mp3"
        with open(filename, 'wb') as tmp_file:
            tmp_file.write(mp3)
        return filename

    @staticmethod
    def play_file(filepath):
        """Plays mp3 file using UNIX cmd."""
        subprocess.call(["mpg123", filepath])

