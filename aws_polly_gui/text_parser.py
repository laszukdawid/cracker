import os
import re


class TextParser:

    citation = re.compile(r'[\(\[]\w+, \d{4}(;\s\w+, \d{4})*[\)\]]')

    @classmethod
    def reduce_cite(cls, text):
        """Removes citations from pasted text."""
        return cls.citation.sub("", text)

    @classmethod
    def reduce_text(cls, text):
        """Simplify text to strings only."""
        text = re.sub(r'-\n', '', text, re.U)
        text = re.sub(r'- ', '', text, re.U)
        text = re.sub(r"'", '', text)
        text = re.sub(r'\t', ' ', text)
        text = re.sub(r'\n', ' ', text)
        return text

    @classmethod
    def wiki_text(cls, text):
        """Convert direct copy from Wikipedia into human-readable form."""
        text = re.sub(r'\[+[0-9]+\]', '', text)
        text = text.replace("[clarification needed]", '')
        text = text.replace("[citation needed]", '')
        return text
