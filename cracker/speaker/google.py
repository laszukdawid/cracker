from google.cloud import texttospeech
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlaylist

from cracker.mp3_helper import create_filename, save_mp3
from cracker.speaker.abstract_speaker import AbstractSpeaker
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


class Google(AbstractSpeaker):

    _logger = get_logger(__name__)

    MIN_VOLUME, MAX_VOLUME = 0, 200
    RATES = [80, 120, 160, 200, 240]
    VOLUMES = range(100)

    def __init__(self, player, credentials_file=None):
        self._connect_google(credentials_file)
        self.player = player

    def _connect_google(self, credentials_file):
        try:
            if credentials_file is not None:
                self.client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_file)
            else:
                self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            self._logger.exception("Unable to connect to Google with the credentials file '%s'. "
                                   "Please verify that configuration file exists.", credentials_file)
            raise e

    def read_text(self, text: str, **config) -> None:
        """Reads out text."""
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text(text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=config.get("voice"), 
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )

        filepaths = []
        for idx, parted_text in enumerate(split_text):
            self._logger.debug("Reading text: %s", parted_text)
            response = self.ask_google(parted_text, voice)
            filename = create_filename(AbstractSpeaker.TMP_FILEPATH, idx)
            saved_filepath = save_mp3(response.audio_content, filename)
            filepaths.append(saved_filepath)
        self.play_files(filepaths)

    def ask_google(self, text: str, voice):
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        synth_speech = texttospeech.SynthesisInput(text=text)

        response = self.client.synthesize_speech(input=synth_speech, voice=voice, audio_config=audio_config)
        return response

    def play_files(self, filepaths):
        playlist = QMediaPlaylist(self.player)
        for filepath in filepaths:
            url = QUrl.fromLocalFile(filepath)
            playlist.addMedia(QMediaContent(url))
        self.player.setPlaylist(playlist)
        self.player.play()

    def stop_text(self) -> None:
        self.player.stop()

