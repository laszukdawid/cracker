import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List

import boto3
from botocore.config import Config
from PyQt6.QtWidgets import QMessageBox

from cracker.config import Configuration
from cracker.mp3_helper import create_filename, save_mp3
from cracker.read_along import AudioSegment, WordMark, parse_speech_marks
from cracker.speaker import POLLY_LANGUAGES
from cracker.speaker.synthesis import MAX_PARALLEL_REQUESTS, SpeechQueue, remove_files
from cracker.ssml import SSML
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker

CONNECTION_HELP = (
    "Unable to connect to AWS Polly. Please check your AWS configuration.\n\n"
    "Please verify:\n"
    "1. Your AWS profile is configured correctly\n"
    "2. You are logged into AWS\n"
    "3. Your credentials have access to AWS Polly"
)


# botocore waits 60 s by default; a dead connection would hold up Stop and quitting that long.
# A 3,000-character synthesis takes about 1.3 s.
CLIENT_CONFIG = Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 3, "mode": "standard"})


class Polly(AbstractSpeaker):
    """Interface for communication with AWS Polly"""

    _logger = get_logger(__name__)

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    LANGUAGES = POLLY_LANGUAGES

    def __init__(self, player):
        self._cached_ssml = SSML()
        self._cached_segments: list[AudioSegment] = []
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
            self._warm_up()
        except Exception as e:
            self._logger.error("Error connecting to AWS: %s", e)
            self._connection_error = str(e)

        self.player = player
        self._queue = SpeechQueue(player, self._show_synthesis_error)
        self._marks_executor: ThreadPoolExecutor | None = None

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    def shutdown(self) -> None:
        # Once only: __del__ may run after the player has moved on to another speaker.
        if getattr(self, "_shut_down", False):
            return
        self._shut_down = True
        queue = getattr(self, "_queue", None)
        if queue is not None:
            queue.cancel()
        player = getattr(self, "player", None)
        if player is not None:
            player.stop()
        executor = getattr(self, "_marks_executor", None)
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
            self._marks_executor = None
        remove_files(getattr(self, "_cached_segments", []))
        self._cached_ssml = SSML()
        self._cached_segments = []
        self._cached_voice = ""

    def _warm_up(self) -> None:
        """Resolve credentials and open a connection in the background, so the first read starts sooner.

        SSO credentials alone take most of a second; ``describe_voices`` is a free call.
        """
        client = self.client
        if client is None:
            return

        def warm() -> None:
            try:
                client.describe_voices(LanguageCode="en-US")
            except Exception as error:
                self._logger.debug("Polly warm-up failed: %s", error)

        threading.Thread(target=warm, daemon=True, name="polly-warm-up").start()

    @staticmethod
    def _connect_aws(profile_name: str | None = None, region_name: str | None = None):
        """Connect to AWS and create Polly client"""
        try:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            return session.client("polly", config=CLIENT_CONFIG)
        except Exception as e:
            Polly._logger.exception(
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

        self._logger.debug("Reloading with AWS profile: %s, region: %s", aws_profile, aws_region)

        try:
            self.client = self._connect_aws(aws_profile, aws_region)
            self._warm_up()
            self._connection_error = None  # Clear any previous error
            self._logger.info("Successfully reloaded AWS Polly client")
        except Exception as e:
            self._logger.error("Error reloading AWS client: %s", e)
            self._connection_error = str(e)
            raise

    @staticmethod
    def test_connection(profile_name: str | None = None, region_name: str | None = None):
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
                f"Profile: {profile_name or 'default'}\nRegion: {actual_region}\nAvailable voices: {voice_count}"
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

    def save_cache(self, ssml: SSML, segments: List[AudioSegment], voice):
        # Remove previously cached temp files that the new cache no longer uses
        # (a shorter read leaves higher-indexed mp3s orphaned otherwise).
        new_paths = {segment.path for segment in segments}
        for old_segment in self._cached_segments:
            if old_segment.path not in new_paths:
                try:
                    os.remove(old_segment.path)
                except OSError:
                    pass
        self._cached_ssml = ssml
        self._cached_segments = segments
        self._cached_voice = voice

    def read_text(self, text: str, **config) -> None:
        """Reads out text, attaching per-word speech marks to each segment.

        Synthesis runs in the background; playback starts as soon as the first chunk is ready.
        """
        text = self.clean_text(text)
        # Split before escaping so a chunk boundary can't fall inside an entity such as "&amp;".
        chunks = [TextParser.escape_tags(chunk) for chunk in TextParser.split_for_speech(text)]
        text = TextParser.escape_tags(text)

        rate = config.get("rate")
        volume = config.get("volume")
        voice = config.get("voice")
        assert voice, "Voice needs to be provided"  # TODO: Does it?

        ssml = SSML(text, rate=rate, volume=volume)

        if self._cached_ssml == ssml and self._cached_voice == voice:
            self._logger.debug("Playing cached file")
            self._queue.cancel()
            self.player.play_segments(self._cached_segments)
            return

        if self.client is None or self._connection_error:
            self._logger.error("Attempted to use Polly without valid AWS connection")
            self._show_error_dialog(CONNECTION_HELP, f"Error details: {self._connection_error}")
            return

        self._logger.debug("Request from Polly")
        token = uuid.uuid4().hex[:8]
        self._queue.start(
            chunks,
            lambda index, chunk: self._synthesize_chunk(token, index, chunk, rate, volume, voice),
            on_finished=lambda segments: self.save_cache(ssml, segments, voice),
        )

    def _synthesize_chunk(self, token: str, index: int, text: str, rate, volume, voice: str) -> AudioSegment:
        """Runs on a worker thread: fetches the audio and its word marks at the same time."""
        parted_ssml = str(SSML(text, rate=rate, volume=volume))
        marks = self._marks_pool().submit(self._fetch_marks, parted_ssml, voice)
        response = self.ask_polly(parted_ssml, voice)
        filename = create_filename(f"polly-{token}.mp3", index)
        saved_filepath = save_mp3(response["AudioStream"].read(), filename)
        return AudioSegment(path=saved_filepath, marks=marks.result())

    def _marks_pool(self) -> ThreadPoolExecutor:
        if self._marks_executor is None:
            self._marks_executor = ThreadPoolExecutor(MAX_PARALLEL_REQUESTS, thread_name_prefix="polly-marks")
        return self._marks_executor

    def _show_synthesis_error(self, message: str) -> None:
        self._show_error_dialog(
            "An error occurred while trying to synthesize speech with AWS Polly.", f"Error details: {message}"
        )

    def _fetch_marks(self, ssml_text: str, voice: str) -> List[WordMark]:
        """Requests word-level speech marks for one SSML chunk.

        Returns an empty list on any failure so playback (and the estimated
        read-along fallback) still works without the marks.
        """
        if self.client is None:
            return []
        try:
            response = self.client.synthesize_speech(
                OutputFormat="json",
                TextType="ssml",
                Text=ssml_text,
                VoiceId=voice,
                SpeechMarkTypes=["word"],
            )
            return parse_speech_marks(response["AudioStream"].read())
        except Exception as error:
            self._logger.warning("Could not fetch Polly speech marks: %s", error)
            return []

    def _show_error_dialog(self, message: str, details: str = ""):
        """Shows an error dialog to the user"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("AWS Polly Connection Error")
        msg_box.setText(message)
        if details:
            msg_box.setInformativeText(details)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def ask_polly(self, ssml_text: str, voice: str):
        """Synthesises ``ssml_text``; may run on a worker thread, so it raises instead of showing dialogs."""
        if self.client is None or self._connection_error:
            raise RuntimeError(f"AWS Polly client not initialized: {self._connection_error}")
        try:
            return self.client.synthesize_speech(**self.create_speech(ssml_text, voice))
        except Exception as e:
            self._logger.error("Error calling Polly synthesize_speech: %s", e)
            raise

    @staticmethod
    def create_speech(ssml_text: str, voice: str):
        """Prepares speech query to Polly"""
        return dict(OutputFormat="mp3", TextType="ssml", Text=ssml_text, VoiceId=voice)

    def stop_text(self) -> None:
        self._queue.cancel()
        self.player.stop()
