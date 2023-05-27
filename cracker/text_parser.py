import html
import logging
import re
from collections import OrderedDict

from cracker.config import Configuration


class TextParser:
    _logger = logging.getLogger(__name__)

    citation_author_year = re.compile(r"[\(\[]\w+, \d{4}(;\s\w+, \d{4})*[\)\]]")
    citation_numbers_comma = re.compile(r"\[\d+(,\s*\d+)*\]")

    def __init__(self):
        self._parser_rules = None
        self._regex_rules = OrderedDict()

        global_config = Configuration()
        self.parser_rules = global_config.load_regex_config()

    @property
    def parser_rules(self):
        return self._parser_rules

    @parser_rules.setter
    def parser_rules(self, parser_rules):
        self._parser_rules = parser_rules
        self.update_config()

    def update_config(self):
        """Goes through the config and extracts regex rules."""
        if self.parser_rules is None:
            return

        # Clears all regex rules
        self._regex_rules.clear()

        for rule in self.parser_rules.values():
            if not rule["active"]:
                continue
            self._regex_rules[rule["key"]] = rule["value"]

    @classmethod
    def reduce_cite(cls, text: str) -> str:
        """Removes citations from pasted text."""
        text = cls.citation_numbers_comma.sub("", text)
        text = cls.citation_author_year.sub("", text)
        return text

    @staticmethod
    def wiki_text(text: str) -> str:
        """Convert direct copy from Wikipedia into human-readable form."""
        text = re.sub(r"\[+[0-9]+\]", "", text)
        text = text.replace("[clarification needed]", "")
        text = text.replace("[citation needed]", "")
        return text

    @staticmethod
    def split_text(text: str, max_char: int = 3000) -> str:
        doc_residue = text
        while len(doc_residue) > max_char:
            # TODO: Should the split be by whitespace if no '. ' ?
            part = doc_residue[:max_char].rsplit(". ", 1)[0]
            doc_residue = doc_residue[len(part) :]
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
