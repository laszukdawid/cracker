import html
import json
import logging
import re
from collections import OrderedDict
from typing import Optional


class TextParser:

    _logger = logging.getLogger(__name__)

    citation_author_year = re.compile(r'[\(\[]\w+, \d{4}(;\s\w+, \d{4})*[\)\]]')
    citation_numbers_comma = re.compile(r'\[\d+(,\s*\d+)*\]')

    # TODO: There shoudldn't be both `config_path` and `config`
    def __init__(self, config_path: Optional[str] = None):

        self._config = None
        self._parser_rules = None
        self._regex_rules = OrderedDict()

        # Check that this is a file
        if self._config is None and config_path is not None:
            self.config = self.read_config_path(config_path)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        self.update_config()
    
    @property
    def parser_rules(self):
        return self._parser_rules
    
    @parser_rules.setter
    def parser_rules(self, parser_rules):
        assert self._config, "Need to provide config before parser"
        self._config["parser_rules"] = parser_rules
        self.update_config()

    def read_config_path(self, config_path: str):
        """From provided path to a config it extracts configuration for the TextParser"""
        self._logger.info("parsing read config path")

        config = None
        # TODO: There should be a check whether file exists
        with open(config_path) as f:
            config = json.loads(f.read())
        return config

    def update_config(self):
        """Goes through the config and extracts regex rules."""
        if self.config is None:
            return

        # Clears all regex rules
        self._regex_rules.clear()

        for rule in self.config["parser_rules"]:
            if not rule['active']:
                continue
            self._regex_rules[rule['key']] = rule['value']

    @classmethod
    def reduce_cite(cls, text: str) -> str:
        """Removes citations from pasted text."""
        text = cls.citation_numbers_comma.sub("", text)
        text = cls.citation_author_year.sub("", text)
        return text

    @staticmethod
    def wiki_text(text: str) -> str:
        """Convert direct copy from Wikipedia into human-readable form."""
        text = re.sub(r'\[+[0-9]+\]', '', text)
        text = text.replace("[clarification needed]", '')
        text = text.replace("[citation needed]", '')
        return text

    @staticmethod
    def split_text(text: str, max_char: int = 3000) -> str:
        doc_residue = text
        while len(doc_residue) > max_char:
            # TODO: Should the split be by whitespace if no '. ' ?
            part = doc_residue[:max_char].rsplit(". ", 1)[0]
            doc_residue = doc_residue[len(part):]
            yield part
        yield doc_residue

    @staticmethod
    def escape_tags(text: str) -> str:
        return html.escape(text, quote=False)

    def reduce_text(self, text: str) -> str:
        # For each method process text
        for key, value in self._regex_rules.items():
            text = re.sub(key, value, text)
        return text
