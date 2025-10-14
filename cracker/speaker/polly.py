import logging
import os
from typing import List, Optional

import boto3
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlaylist
from PyQt5.QtWidgets import QMessageBox

from cracker.config import Configuration
from cracker.mp3_helper import create_filename, save_mp3
from cracker.speaker import POLLY_LANGUAGES
from cracker.ssml import SSML
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


class Polly(AbstractSpeaker):
    """Interface for communication with AWS Polly"""

    _logger = get_logger(__name__)

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    LANGUAGES = POLLY_LANGUAGES

    def __init__(self, player):
        self._cached_ssml = SSML()
        self._cached_filepaths = []
        self._cached_voice = ""

        self.config = Configuration()
        self.client = None
        self._connection_error = None
        polly_config = self.config.read_config()["polly"]
        aws_profile = polly_config["profile_name"]
        aws_region = polly_config.get("region_name", None)
        self._logger.debug("Using AWS profile: %s, region: %s", aws_profile, aws_region)
        try:
            self.client = self._connect_aws(aws_profile, aws_region)
        except Exception as e:
            self._logger.error("Error connecting to AWS: %s", e)
            self._connection_error = str(e)

        self.player = player

    def __del__(self):
        try:
            for filepath in self._cached_filepaths:
                os.remove(filepath)
        except (OSError, TypeError):
            pass

    @staticmethod
    def _connect_aws(
        profile_name: Optional[str] = None, region_name: Optional[str] = None
    ):
        """Connect to AWS and create Polly client"""
        try:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            return session.client("polly")
        except Exception as e:
            logging.exception(
                "Unable to connect to AWS with the profile '%s' and region '%s'. "
                "Please verify that configuration file exists.",
                profile_name,
                region_name,
            )
            raise e

    def reload_client(self):
        """Reload the AWS Polly client with updated configuration"""
        self._logger.info("Reloading AWS Polly client with updated configuration")
        polly_config = self.config.read_config()["polly"]
        aws_profile = polly_config["profile_name"]
        aws_region = polly_config.get("region_name", None)

        self._logger.debug(
            "Reloading with AWS profile: %s, region: %s", aws_profile, aws_region
        )

        try:
            self.client = self._connect_aws(aws_profile, aws_region)
            self._connection_error = None  # Clear any previous error
            self._logger.info("Successfully reloaded AWS Polly client")
        except Exception as e:
            self._logger.error("Error reloading AWS client: %s", e)
            self._connection_error = str(e)
            raise

    @staticmethod
    def test_connection(
        profile_name: Optional[str] = None, region_name: Optional[str] = None
    ):
        """
        Test AWS Polly connection with given profile and region.

        Args:
            profile_name: AWS profile name to use
            region_name: AWS region name to use (optional)

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create session and client
            client = Polly._connect_aws(profile_name, region_name)

            # Try to describe voices - this is a lightweight API call to verify connectivity
            response = client.describe_voices()

            # Count available voices
            voice_count = len(response.get("Voices", []))

            # Get the actual region being used
            actual_region = client.meta.region_name

            success_message = (
                f"Profile: {profile_name or 'default'}\n"
                f"Region: {actual_region}\n"
                f"Available voices: {voice_count}"
            )

            return True, success_message

        except Exception as e:
            error_message = (
                f"Failed to connect to AWS Polly.\n\n"
                f"Profile: {profile_name or 'default'}\n"
                f"Region: {region_name or 'default'}\n\n"
                f"Error: {str(e)}\n\n"
                f"Please verify:\n"
                f"1. Your AWS profile is configured correctly\n"
                f"2. You are logged into AWS\n"
                f"3. Your credentials have access to AWS Polly"
            )
            return False, error_message

    def save_cache(self, ssml: SSML, filepaths: List[str], voice):
        self._cached_ssml = ssml
        self._cached_filepaths = filepaths
        self._cached_voice = voice

    def read_text(self, text: str, **config) -> None:
        """Reads out text."""
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text(text)

        rate = config.get("rate")
        volume = config.get("volume")
        voice = config.get("voice")
        assert voice, "Voice needs to be provided"  # TODO: Does it?

        ssml = SSML(text, rate=rate, volume=volume)

        if self._cached_ssml == ssml and self._cached_voice == voice:
            self._logger.debug("Playing cached file")
            filepaths = self._cached_filepaths
        else:
            self._logger.debug("Request from Polly")
            filepaths = []
            # TODO: This should obviously be asynchronous!
            try:
                for idx, parted_text in enumerate(split_text):
                    parted_ssml = SSML(parted_text, rate=rate, volume=volume)
                    response = self.ask_polly(str(parted_ssml), voice)
                    filename = create_filename(AbstractSpeaker.TMP_FILEPATH, idx)
                    saved_filepath = save_mp3(response["AudioStream"].read(), filename)
                    filepaths.append(saved_filepath)
                self.save_cache(ssml, filepaths, voice)
            except (RuntimeError, Exception) as e:
                self._logger.error("Failed to read text with Polly: %s", e)
                return  # Exit gracefully without crashing
        self.play_files(filepaths)
        return

    def _show_error_dialog(self, message: str, details: str = ""):
        """Shows an error dialog to the user"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("AWS Polly Connection Error")
        msg_box.setText(message)
        if details:
            msg_box.setInformativeText(details)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def ask_polly(self, ssml_text: str, voice: str):
        """Connects to Polly and returns path to save mp3"""
        if self.client is None or self._connection_error:
            error_msg = (
                "Unable to connect to AWS Polly. Please check your AWS configuration.\n\n"
                "Please verify:\n"
                "1. Your AWS profile is configured correctly\n"
                "2. You are logged into AWS\n"
                "3. Your credentials have access to AWS Polly"
            )
            self._logger.error("Attempted to use Polly without valid AWS connection")
            self._show_error_dialog(
                error_msg, f"Error details: {self._connection_error}"
            )
            raise RuntimeError("AWS Polly client not initialized")

        try:
            speech = self.create_speech(ssml_text, voice)
            response = self.client.synthesize_speech(**speech)
            return response
        except Exception as e:
            error_msg = (
                "An error occurred while trying to synthesize speech with AWS Polly."
            )
            self._logger.error("Error calling Polly synthesize_speech: %s", e)
            self._show_error_dialog(error_msg, f"Error details: {str(e)}")
            raise

    @staticmethod
    def create_speech(ssml_text: str, voice: str):
        """Prepares speech query to Polly"""
        return dict(OutputFormat="mp3", TextType="ssml", Text=ssml_text, VoiceId=voice)

    def play_files(self, filepaths):
        playlist = QMediaPlaylist(self.player)
        for filepath in filepaths:
            url = QUrl.fromLocalFile(filepath)
            playlist.addMedia(QMediaContent(url))
        self.player.setPlaylist(playlist)
        self.player.play()

    def stop_text(self) -> None:
        self.player.stop()
