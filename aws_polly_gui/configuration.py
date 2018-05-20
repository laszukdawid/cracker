import configparser
import json

class Configuration(object):

    language_file = "voices.json"
    DEFAULT_CONFIG_PATH = "default_setting.ini"

    def __init__(self):
        self.languages = []
        self.default_config = {}

    def read_default_config(self):
        default_config = configparser.ConfigParser()
        default_config.read(self.DEFAULT_CONFIG_PATH)

        default_values = default_config['Default']
        config = {}
        config['speaker'] = self.speaker = default_values['speaker']
        config['language'] = self.language = default_values['language']
        config['speed'] = self.speed = int(default_values['speed'])
        config['voice'] = self.voice = default_config['Default'+self.speaker]['Voice']

        speaker_config = self.load_config(self.speaker, self.language)
        config.update(speaker_config)

        if self.voice not in self.lang_voices:
            config['voice'] = self.voice = self.lang_voices[0]
        self.default_config.update(config)
        return config

    def load_config(self, speaker, language=None):
        config = {}
        config['voices'] = self.voices = self.load_languages(speaker)
        config['languages'] = self.languages = list(self.voices.keys())
        if language is None:
            language = self.language
        config['lang_voices'] = self.lang_voices = self.voices[language]

        if self.voice not in self.lang_voices:
            config['voice'] = self.voice = self.lang_voices[0]
        return config

    def load_languages(self, speaker):
        """Load JSON config with available languages and voices."""
        with open(self.language_file) as json_file:
            lang_map = json.loads(json_file.read())
        return lang_map[speaker]["Languages"]

