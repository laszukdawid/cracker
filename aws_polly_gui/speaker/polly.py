import html
import logging
import os

import boto3
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent
from PyQt5.QtMultimedia import QMediaPlaylist

from aws_polly_gui.text_parser import TextParser
from aws_polly_gui.ssml import SSML
from .abstract_speaker import AbstractSpeaker
from aws_polly_gui.mp3_helper import save_mp3


class Polly(AbstractSpeaker):
    """Interface for communication with AWS Polly"""

    _logger = logging.getLogger(__name__)

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    def __init__(self, player, profile_name="default"):
        self._cached_ssml = SSML()
        self._cached_filepath = ""
        self._cached_voice = ""
        self._connect_aws(profile_name)
        self.player = player

    def __del__(self):
        try:
            os.remove(self._cached_filepath)
        except (OSError, TypeError):
            pass

    def _connect_aws(self, profile_name):
        try:
            session = boto3.Session(profile_name=profile_name)
            self.client = session.client('polly')
        except Exception as e:
            self._logger.exception("Unable to connect to AWS with the profile '%s'. " \
                    "Please verify that configuration file exists.", profile_name)
            raise e

    def save_cache(self, ssml, filepaths, voice):
        self._cached_ssml = ssml
        self._cached_filepaths = filepaths
        self._cached_voice = voice

    def read_text(self, text, **config):
        """Reads out text."""
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text(text)

        voice = config['voice'] if 'voice' in config else None
        rate = config['rate'] if 'rate' in config else None
        volume = config['volume'] if 'volume' in config else None
        ssml = SSML(text, rate=rate, volume=volume)

        if self._cached_ssml == ssml and self._cached_voice == voice:
            self._logger.debug("Playing cached file")
            filepaths = self._cached_filepaths
        else:
            self._logger.debug("Re_cached_textquest from Polly")
            filepaths = []
            # TODO: This should obviously be asynchronous!
            for idx, parted_text in enumerate(split_text):
                parted_ssml = SSML(parted_text, rate=rate, volume=volume)
                response = self.ask_polly(str(parted_ssml), voice)
                filepath = save_mp3(response["AudioStream"].read(), AbstractSpeaker.TMP_FILEPATH, idx)
                filepaths.append(filepath)
            self.save_cache(ssml, filepaths, voice)
        self.play_files(filepaths)
        return

    def ask_polly(self, ssml_text, voice):
        """Connects to Polly and returns path to save mp3"""
        speech = self.create_speech(ssml_text, voice)
        response = self.client.synthesize_speech(**speech)
        return response

    @staticmethod
    def create_speech(ssml_text, voice):
        """Prepares speech query to Polly"""
        return dict(
            OutputFormat='mp3',
            TextType='ssml',
            Text=ssml_text,
            VoiceId=voice
        )

    def play_files(self, filepaths):
        playlist = QMediaPlaylist(self.player)
        for filepath in filepaths:
            url = QUrl.fromLocalFile(filepath)
            playlist.addMedia(QMediaContent(url))
        self.player.setPlaylist(playlist)
        self.player.play()

    def stop_text(self):
        self.player.stop()
