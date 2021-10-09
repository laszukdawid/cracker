import configparser
import json


class Configuration(object):
    """Holds configuration values for the application."""
    singleton = None  
   
    language_file = "voices.json"
    DEFAULT_CONFIG_PATH = "default_setting.ini"

    languages = []
    default_values = {}  # Additional values

    speaker = None
    language = None
    voice = None
    voices = []
    speed = None

    regex_config = None


    def __new__(cls, *args, **kwargs):  
        if not cls.singleton:  
            cls.singleton = object.__new__(Configuration)  
        return cls.singleton  

    def read_default_config(self):
        configuration = configparser.ConfigParser()
        configuration.read(self.DEFAULT_CONFIG_PATH)

        default_config = configuration['Default']
        config = {}
        config['parser_config'] = self.parser_config = default_config['parser_config']
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

        if self.parser_config is not None:
            self.regex_config = self.load_regex_config()

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

    def load_regex_config(self):
        """From provided path to a config it extracts configuration for the TextParser"""
        regex_config = None
        try:
            with open(self.parser_config) as f:
                regex_config = json.loads(f.read())["parser_rules"]
        except Exception as e:
            print("While reading config", e)
            self._logger.error(e)

        return regex_config
