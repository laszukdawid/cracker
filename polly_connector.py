import os
import re

import boto3

from ssml import SSML

class PollyConnector:

    def __init__(self):
        self.client = boto3.client('polly')
        self.speech = dict(
            OutputFormat="mp3",
            TextType="ssml",
        )

    def readText(self, text, voiceid, rate, volume_text):
        """Reads out text."""
        text = text.translate(dict.fromkeys(range(8)))
        text = re.sub(r'\n', ' ', text)
        text = re.sub(r'&', 'and', text)

        ssml = SSML(text, rate=rate, volume=volume_text)
        self.speech["Text"] = str(ssml)
        self.speech["VoiceId"] = voiceid
        response = self.client.synthesize_speech(**self.speech)
        filepath = self.saveMp3(response)
        self.playFile(filepath)

    @classmethod
    def reduceCite(cls, text):
        """Removes citations from pasted text."""
        text = re.sub(r'\w+ and \w+, \d{4}(;?)', '', text)
        text = re.sub(r'\w+ et al., \d\{4}(;?)', '', text)
        text = re.sub(r'\w+, \d{4}(;?)', '', text)
        text = re.sub(r'\(;[^\)]*\)', '', text)
        text = re.sub(r'\(( *)\)', '', text)
        return text

    @classmethod
    def reduceText(cls, text):
        """Simplify text to strings only."""
        text = re.sub(r'-\n', '', text, re.U)
        text = re.sub(r'- ', '', text, re.U)
        text = re.sub(r"'", '', text)
        text = re.sub(r'\t', ' ', text)
        text = re.sub(r'\n', ' ', text)
        return text

    @classmethod
    def wikiText(cls, text):
        """Convert direct copy from Wikipedia into human-readable form."""
        print('wiki pressed')
        text = re.sub(r'\[+[0-9]+\]', '', text)
        text = text.replace("[clarification needed]", '')
        text = text.replace("[citation needed]", '')
        return text

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

