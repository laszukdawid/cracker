import abc
import re


class AbstractSpeaker(abc.ABC):
    """
    Abstract class for all `Speaker` classes.

    To be inherited only.
    """

    TMP_FILEPATH = "tmp.mp3"
    RATES = []
    VOLUMES = []
    text_cleaners = [
        (re.compile(r'\n'), '. '),
        (re.compile(r'&'), 'and'),
    ]

    @abc.abstractmethod
    def read_text(self, text: str, **config) -> None:
        return NotImplementedError("Class %s doesn't implement `read_text()`" % self.__class__.__name__)

    @abc.abstractmethod
    def stop_text(self) -> None:
        return NotImplementedError("Class %s doesn't implement `stop_text()`" % self.__class__.__name__)

    @classmethod
    def clean_text(cls, text):
        text = text.translate(dict.fromkeys(range(8)))
        for compiled_regex, sub in cls.text_cleaners:
            text = compiled_regex.sub(sub, text)
        return text
