import configparser
import json

class Configuration(object):
    """Holds configuration values for the application."""

    language_file = "voices.json"
    DEFAULT_CONFIG_PATH = "default_setting.ini"

    def __init__(self):
        self.languages = []
        self.default_values = {}  # Additional values

        self.speaker = None
        self.language = None
        self.voice = None
        self.voices = []
        self.speed = None

    def read_default_config(self):
        configuration = configparser.ConfigParser()
        configuration.read(self.DEFAULT_CONFIG_PATH)

        default_config = configuration['Default']
        config = {}
        config['speaker'] = self.speaker = default_config['speaker']
        config['language'] = self.language = default_config['language']
        config['speed'] = self.speed = int(default_config['speed'])
        config['voice'] = self.voice = configuration['Default'+self.speaker]['Voice']

        speaker_config = self.load_config(self.speaker, self.language)
        config.update(speaker_config)

        # Check for different than default AWS profile_name
        if self.speaker == "Polly" and "profile_name" in configuration['DefaultPolly']:
            self.default_values['profile_name'] = configuration['DefaultPolly']['profile_name']

        if self.voice not in self.lang_voices:
            config['voice'] = self.voice = self.lang_voices[0]
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

