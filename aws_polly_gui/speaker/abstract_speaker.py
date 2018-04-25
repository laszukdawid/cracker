import re


class AbstractSpeaker(object):
    """
    Abstract class for all `Speaker` classes.

    To be inherited only.
    """

    RATES = []
    VOLUMES = []
    text_cleaners = [(re.compile(r'\n'), '. '),
                     (re.compile(r'&'), 'and'),
                    ]

    def read_text(self, text, **config):
        return NotImplementedError("Class %s doesn't implement `read_text()`" % self.__class__.__name__)

    def stop_text(self):
        return NotImplementedError("Class %s doesn't implement `stop_text()`" % self.__class__.__name__)

    @classmethod
    def clean_text(cls, text):
        text = text.translate(dict.fromkeys(range(8)))
        for compiled_regex, sub in cls.text_cleaners:
            text = compiled_regex.sub(sub, text)
        return text
