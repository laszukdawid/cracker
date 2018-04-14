import os
import re

class TextParser:

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

