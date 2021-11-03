import json
import logging
import os
from configparser import ConfigParser
from typing import Any, Dict


class Configuration:
    """Holds configuration values for the application."""
    singleton = None
    _logger = logging.getLogger(__name__)
   
    language_file = "voices.json"
    DEFAULT_CONFIG_PATH = "default_setting.ini"
    USER_CONFIG_DIR_PATH = os.path.expanduser("~/.cracker")

    languages = []
    default_values = {}  # Additional values

    speaker = None
    language = None
    voice = None
    voices = []
    speed = 0

    regex_config = None
    
    def __new__(cls, *args, **kwargs):
        if not cls.singleton:
            cls.singleton = object.__new__(Configuration)
        return cls.singleton

    def read_config(self) -> Dict[str, Any]:
        """Reads configuration from file system.
        
        Firstly checks whether there are any user defined config in ~/.cracker/.
        If config isn't there then it takes the default.
        """
        # Check defaults
        self._default_config = config = self._read_default_config()

        # Check if user has created config
        if os.path.isdir(self.USER_CONFIG_DIR_PATH):
            config = self._read_user_config(self.default_config)
        
        return self.apply_config(config)

    def _read_default_config(self) -> ConfigParser:
        configuration = ConfigParser()
        configuration.read(self.DEFAULT_CONFIG_PATH)

        return configuration
    
    @property
    def user_config_path(self):
        return os.path.join(self.USER_CONFIG_DIR_PATH, "setting.ini")
    
    @property
    def default_config(self):
        if self._default_config is None:
            return ConfigParser()
        return self._default_config

    def _read_user_config(self, config: ConfigParser) -> ConfigParser:
        if not os.path.isdir(self.USER_CONFIG_DIR_PATH):
            self._logger.debug("Creating user dir in '%s'", self.USER_CONFIG_DIR_PATH)
            os.mkdir(self.USER_CONFIG_DIR_PATH)

        if not os.path.isfile(self.user_config_path):
            return config

        configuration = ConfigParser()
        configuration.read(self.user_config_path)
        for section in configuration.sections():
            for (key, value) in configuration[section].items():
                config.set(section, key, value)

        return config
    
    def save_user_config(self):
        assert self.default_config
        config = self._read_user_config(self.default_config)

        config['Cracker']['speaker'] = self.speaker or self.default_config['Cracker']['speaker']
        config['Cracker']['language'] = self.language or self.default_config['Cracker']['language']
        config['Cracker']['speed'] = str(self.speed) or self.default_config['Cracker']['speed']
        config['Cracker']['voice'] = self.voice or self.default_config['Cracker']['voice']

        with open(self.user_config_path, 'w') as f:
            config.write(f)

    def apply_config(self, configuration: ConfigParser) -> Dict[str, Any]:
        """Applies parsed config to Cracker and UI components.

        Returns:
            Dict of the most important values which might be used by other components.
            This includes: speaker, language, speed and voices with their settings.
        """
        config = configuration['Cracker']

        _config = {}
        _config['parser_config'] = self.parser_config = config['parser_config']
        _config['speaker'] = self.speaker = config['speaker']
        _config['language'] = self.language = config['language']
        _config['speed'] = self.speed = int(config['speed'])
        _config['voice'] = self.voice = configuration[self.speaker]['Voice']

        speaker_config = self.load_config(self.speaker, self.language)
        _config.update(speaker_config)

        # Check for different than default AWS profile_name
        if self.speaker == "Polly" and "profile_name" in configuration['Polly']:
            self.default_values['profile_name'] = configuration['Polly']['profile_name']

        if self.voice not in self.lang_voices:
            _config['voice'] = self.voice = self.lang_voices[0]

        if self.parser_config is not None:
            self.regex_config = self.load_regex_config()

        return _config

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
            self._logger.exception("While reading config")

        return regex_config
