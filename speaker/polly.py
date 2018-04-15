import os
import re

import boto3

from ssml import SSML
from .abstract_speaker import AbstractSpeaker

class Polly(AbstractSpeaker):

    def __init__(self):
        self.client = boto3.client('polly')
        self.speech = dict(
            OutputFormat="mp3",
            TextType="ssml",
        )

    def clean_text(self, text):
        text = text.translate(dict.fromkeys(range(8)))
        text = re.sub(r'\n', ' ', text)
        text = re.sub(r'&', 'and', text)
        return text

    def read_text(self, text, voiceid, rate, volume_text):
        """Reads out text."""
        text = self.clean_text(text)
        ssml = SSML(text, rate=rate, volume=volume_text)
        self.speech["Text"] = str(ssml)
        self.speech["VoiceId"] = voiceid
        response = self.client.synthesize_speech(**self.speech)
        filepath = self.saveMp3(response)
        self.playFile(filepath)


    @classmethod
    def saveMp3(cls, response):
        """Stores downloaded response as an mp3."""
        mp3 = response["AudioStream"].read()
        filename = "tmp.mp3"
        with open(filename, 'wb') as tmp_file:
            tmp_file.write(mp3)
        return filename

    @staticmethod
    def playFile(filepath):
        """Plays mp3 file using UNIX cmd."""
        os.system("mpg123 "+filepath)

