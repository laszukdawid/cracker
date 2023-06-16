import html
import logging
import re
from collections import OrderedDict

from cracker.config import Configuration

alphabets = "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = (
    "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
)
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r"\.{2,}"


# TODO:
# This was found on the internet. It kind of works, but it is not perfect.
def split_into_sentences(text: str) -> list[str]:
    """
    Split the text into sentences.

    If the text contains substrings "<prd>" or "<stop>", they would lead
    to incorrect splitting because they are used as markers for splitting.

    :param text: text to be split into sentences
    :type text: str

    :return: list of sentences
    :rtype: list[str]
    """
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    text = re.sub(multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text)
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>\\3<prd>", text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]:
        sentences = sentences[:-1]
    return sentences


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

    @classmethod
    def split_text_per_sentence(cls, text: str) -> str:
        return split_into_sentences(text)

    @staticmethod
    def escape_tags(text: str) -> str:
        return html.escape(text, quote=False)

    def reduce_text(self, text: str) -> str:
        # For each method process text
        for key, value in self._regex_rules.items():
            text = re.sub(key, value, text)
        return text
