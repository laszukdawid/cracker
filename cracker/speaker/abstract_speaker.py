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
        (re.compile(r"\n"), ". "),
        (re.compile(r"&"), "and"),
    ]

    @abc.abstractmethod
    def read_text(self, text: str, **config) -> None:
        raise NotImplementedError(f"Class {self.__class__.__name__} doesn't implement `read_text()`")

    @abc.abstractmethod
    def stop_text(self) -> None:
        raise NotImplementedError(f"Class {self.__class__.__name__} doesn't implement `stop_text()`")

    @classmethod
    def clean_text(cls, text):
        text = text.translate(dict.fromkeys(range(8)))
        for compiled_regex, sub in cls.text_cleaners:
            text = compiled_regex.sub(sub, text)
        return text
