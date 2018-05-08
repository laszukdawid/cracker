import re


class TextParser:

    citation_author_year = re.compile(r'[\(\[]\w+, \d{4}(;\s\w+, \d{4})*[\)\]]')
    citation_numbers_comma = re.compile(r'\[\d+(,\s*\d+)*\]')

    @classmethod
    def reduce_cite(cls, text):
        """Removes citations from pasted text."""
        text = cls.citation_numbers_comma.sub("", text)
        text = cls.citation_author_year.sub("", text)
        return text

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
