import html
import logging
import os

import boto3
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent

from aws_polly_gui.ssml import SSML
from .abstract_speaker import AbstractSpeaker


class Polly(AbstractSpeaker):
    """Interface for communcation with AWS Polly"""

    _logger = logging.getLogger(__name__)

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    def __init__(self, player, profile_name="default"):
        session = boto3.Session(profile_name=profile_name)
        self.client = session.client('polly')
        self._cached_ssml = SSML()
        self._cached_filepath = ""
        self._cached_voice = ""
        self.player = player

    def __del__(self):
        try:
            os.remove(self._cached_filepath)
        except (OSError, TypeError):
            pass

    @staticmethod
    def _escape_tags(text):
        return html.escape(text, quote=False)

    def read_text(self, text, **config):
        """Reads out text."""
        text = self.clean_text(text)
        text = self._escape_tags(text)

        voice = config['voice'] if 'voice' in config else None
        rate = config['rate'] if 'rate' in config else None
        volume = config['volume'] if 'volume' in config else None
        ssml = SSML(text, rate=rate, volume=volume)

        if self._cached_ssml == ssml and self._cached_voice == voice:
            self._logger.debug("Playing cached file")
            filepath = self._cached_filepath
        else:
            self._logger.debug("Re_cached_textquest from Polly")
            filepath = self.ask_polly(str(ssml), voice)
            self._cached_ssml, self._cached_filepath = ssml, filepath
            self._cached_voice = voice
        self.play_file(filepath)
        return

    def ask_polly(self, ssml_text, voice):
        """Connects to Polly and returns path to save mp3"""
        speech = self.create_speech(ssml_text, voice)
        response = self.client.synthesize_speech(**speech)
        filepath = self.save_mp3(response)
        return filepath

    @staticmethod
    def create_speech(ssml_text, voice):
        """Prepares speech query to Polly"""
        return dict(
            OutputFormat='mp3',
            TextType='ssml',
            Text=ssml_text,
            VoiceId=voice
        )

    @classmethod
    def save_mp3(cls, response):
        """Stores downloaded response as an mp3."""
        mp3 = response["AudioStream"].read()
        filename = os.path.abspath(AbstractSpeaker.TMP_FILEPATH)
        with open(filename, 'wb') as tmp_file:
            tmp_file.write(mp3)
        return filename

    def play_file(self, filepath):
        """Plays mp3 file using UNIX cmd. Returns pid to the process."""
        url = QUrl.fromLocalFile(filepath)
        media = QMediaContent(url)
        self.player.setMedia(media)
        self.player.play()
        return

    def stop_text(self):
        self.player.stop()
