import re


class AbstractSpeaker(object):
    """
    Abstract class for all `Speaker` classes.

    To be inherited only.
    """

    RATES = []
    VOLUMES = []

    def read_text(self, text, **config):
        return NotImplementedError("Class %s doesn't implement aMethod()" % self.__class__.__name__)

    @staticmethod
    def clean_text(text):
        text = text.translate(dict.fromkeys(range(8)))
        text = re.sub(r'\n', ' ', text)
        text = re.sub(r'&', 'and', text)
        return text
