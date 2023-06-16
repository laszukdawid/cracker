import json
import os
import pkgutil
from typing import Any, Dict, Optional

import yaml

from cracker.speaker import LANGUAGES
from cracker.utils import Singleton, deep_dict_merge, get_logger


class Configuration(Singleton):
    """Holds configuration values for the application."""

    singleton = None
    _logger = get_logger(__name__)

    language_file = "voices.json"
    DEFAULT_CONFIG_PATH = "config/default.yaml"
    DEFAULT_PARSER_PATH = "config/parser.json"
    USER_CONFIG_DIR_PATH = os.path.expanduser("~/.config/cracker")

    languages = []

    speaker = None
    language = None
    voice = None
    voices = []
    speed = 0
    credentials_file = {}

    regex_config = None
    raw_config: Optional[Dict] = None

    def read_config(self) -> Dict[str, Any]:
        """Reads configuration from file system.

        Firstly checks whether there are any user defined config in ~/.config/cracker/.
        If config isn't there then it takes the default.
        """
        # Check defaults
        self._default_config = config = self.read_default_config()

        # Check if user has created config
        if os.path.isdir(self.USER_CONFIG_DIR_PATH):
            config = self._read_user_config(self.default_config)

        self.raw_config = self.apply_config(config)
        return self.raw_config

    def read_default_config(self) -> Dict:
        data = pkgutil.get_data("cracker", self.DEFAULT_CONFIG_PATH)
        if data is None:
            raise FileNotFoundError(f"Could not find config file {self.DEFAULT_CONFIG_PATH}")
        return yaml.safe_load(data.decode("utf-8"))

    def _read_yaml(self, path: str) -> Dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def _write_yaml(self, config: Dict):
        """Writes configuration to file system."""
        with open(self.user_config_path, "w") as f:
            yaml.safe_dump(config, f)

    @property
    def user_config_path(self):
        return os.path.join(self.USER_CONFIG_DIR_PATH, "settings.yaml")

    @property
    def user_parser_path(self):
        return os.path.join(self.USER_CONFIG_DIR_PATH, "parser.json")

    @property
    def default_config(self) -> Dict:
        if self._default_config is None:
            return {}
        return self._default_config

    def _read_user_config(self, config: Dict) -> Dict:
        if not os.path.isdir(self.USER_CONFIG_DIR_PATH):
            self._logger.debug("Creating user dir in '%s'", self.USER_CONFIG_DIR_PATH)
            os.mkdir(self.USER_CONFIG_DIR_PATH)

        if not os.path.isfile(self.user_config_path):
            return config

        user_config = self._read_yaml(self.user_config_path)
        out_config = deep_dict_merge(config, user_config)

        return out_config

    def save_user_config(self, extra_config: Optional[Dict] = None) -> None:
        assert self.default_config
        config = self._read_user_config(self.default_config)

        config["cracker"] = {
            "speaker": self.speaker or self.default_config["cracker"]["speaker"],
            "language": self.language or self.default_config["cracker"]["language"],
            "speed": str(self.speed) or self.default_config["cracker"]["speed"],
            "voice": self.voice or self.default_config["cracker"].get("voice", ""),
        }
        if extra_config is not None:
            config = deep_dict_merge(config, extra_config)

        self.save_regex_config(self.user_parser_path)
        self._write_yaml(config)

    def apply_config(self, configuration: Dict) -> Dict[str, Any]:
        """Applies parsed config to Cracker and UI components.

        Returns:
            Dict of the most important values which might be used by other components.
            This includes: speaker, language, speed and voices with their settings.
        """
        config = configuration["cracker"]
        config_speakers = configuration["speakers"]

        # Current setting
        _config = {}
        _config["speaker"] = self.speaker = config["speaker"]
        _config["language"] = self.language = config["language"]
        _config["speed"] = self.speed = int(config["speed"])
        _config["voice"] = self.voice = config_speakers[self.speaker.lower()].get("voice", "")

        # Augment setting based on speaker
        speaker_config = self.load_speaker_config(self.speaker, self.language)
        _config.update(speaker_config)

        #
        for speaker, s_config in configuration["speakers"].items():
            self._logger.debug(speaker)
            _config[speaker.lower()] = {
                "voice": s_config["voice"],
                "credentials_file": s_config.get("credentials_file", ""),
            }

        # Check for different than default AWS profile_name
        _config["polly"]["profile_name"] = config_speakers.get("polly", {}).get("profile_name", "default")

        if self.voice not in self.lang_voices:
            _config["voice"] = self.voice = self.lang_voices[0]

        self.regex_config = self.load_regex_config()
        return _config

    def load_speaker_config(self, speaker, language=None):
        """Loads speaker's default and available configuration.

        Args:
            speaker: Name of the speaker.
            language: Language to be used. If None then the default language is used.

        Returns:
            Dict with available configuration for the speaker, e.g. all voices and languages.

        """
        config = {}
        config["voices"] = self.voices = LANGUAGES[speaker.lower()]
        config["languages"] = self.languages = list(self.voices.keys())
        if language is None:
            language = self.language
        config["lang_voices"] = self.lang_voices = self.voices[language]

        if self.voice not in self.lang_voices:
            config["voice"] = self.voice = self.lang_voices[0]

        return config

    def load_regex_config(self):
        """From provided path to a config it extracts configuration for the TextParser"""
        regex_config = None

        if not os.path.isdir(self.USER_CONFIG_DIR_PATH):
            self._logger.debug("Creating user dir in '%s'", self.USER_CONFIG_DIR_PATH)
            os.mkdir(self.USER_CONFIG_DIR_PATH)

        if not os.path.isfile(self.user_parser_path):
            file_content = pkgutil.get_data("cracker", self.DEFAULT_PARSER_PATH)
            file_content = file_content.decode("utf-8")
        else:
            with open(self.user_parser_path) as f:
                file_content = f.read()
        regex_config = json.loads(file_content)["parser_rules"]
        return regex_config

    def save_regex_config(self, parser_config_path: str) -> None:
        """Writes configuration to file system."""
        parser_rules = {"parser_rules": self.regex_config}
        with open(parser_config_path, "w") as f:
            json.dump(parser_rules, f, indent=4)
