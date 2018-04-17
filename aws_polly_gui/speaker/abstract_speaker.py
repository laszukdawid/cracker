
class AbstractSpeaker(object):
    """
    Abstract class for all `Speaker` classes.

    To be inherited only.
    """
    def read_text(self, text, voiceid, rate, volume_text):
        return NotImplementedError("Class %s doesn't implement aMethod()" %self.__class__.__name__)
