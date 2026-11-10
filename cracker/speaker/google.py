import os
import uuid

from PyQt6.QtWidgets import QMessageBox

from cracker.mp3_helper import create_filename, save_mp3
from cracker.read_along import AudioSegment
from cracker.speaker import GOOGLE_LANGUAGES
from cracker.speaker.synthesis import SpeechQueue, remove_files
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


class Google(AbstractSpeaker):
    _logger = get_logger(__name__)

    MIN_VOLUME, MAX_VOLUME = 0, 200
    RATES = [80, 120, 160, 200, 240]
    VOLUMES = range(100)

    LANGUAGES = GOOGLE_LANGUAGES

    def __init__(self, player, credentials_file: str | None = None):
        self._connect_google(credentials_file)
        self.player = player
        self._queue = SpeechQueue(player, self._show_synthesis_error)
        self._segments: list[AudioSegment] = []

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
        remove_files(getattr(self, "_segments", []))
        self._segments = []

    def _connect_google(self, credentials_file=None):
        from google.cloud import texttospeech  # slow to import; only loaded when Google is used

        try:
            if credentials_file is not None:
                self._logger.info("Using credentials file: %s", credentials_file)
                full_path = os.path.expanduser(credentials_file)
                self.client = texttospeech.TextToSpeechClient.from_service_account_json(full_path)
            else:
                self._logger.info("Using default credentials file")
                self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            self._logger.exception(
                "Unable to connect to Google with the credentials file '%s'. "
                "Please verify that configuration file exists.",
                credentials_file,
            )
            raise e

    def read_text(self, text: str, **config) -> None:
        """Reads out text; synthesis runs in the background and playback starts with the first chunk."""
        from google.cloud import texttospeech

        text = self.clean_text(text)
        chunks = [TextParser.escape_tags(chunk) for chunk in TextParser.split_for_speech(text)]
        voice = texttospeech.VoiceSelectionParams(
            language_code=config.get("voice"),
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        token = uuid.uuid4().hex[:8]
        self._queue.start(
            chunks,
            lambda index, chunk: self._synthesize_chunk(token, index, chunk, voice),
            on_finished=self._keep_segments,
        )

    def _synthesize_chunk(self, token: str, index: int, text: str, voice) -> AudioSegment:
        """Runs on a worker thread."""
        response = self.ask_google(text, voice)
        filename = create_filename(f"google-{token}.mp3", index)
        return AudioSegment(path=save_mp3(response.audio_content, filename))

    def _keep_segments(self, segments: list[AudioSegment]) -> None:
        remove_files(self._segments)
        self._segments = segments

    def _show_synthesis_error(self, message: str) -> None:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Google Text-to-Speech Error")
        msg_box.setText("An error occurred while trying to synthesize speech with Google.")
        msg_box.setInformativeText(f"Error details: {message}")
        msg_box.exec()

    def ask_google(self, text: str, voice):
        from google.cloud import texttospeech

        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        synth_speech = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(input=synth_speech, voice=voice, audio_config=audio_config)
        return response

    def play_files(self, filepaths):
        self.player.play_files(filepaths)

    def stop_text(self) -> None:
        self._queue.cancel()
        self.player.stop()
