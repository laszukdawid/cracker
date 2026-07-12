from unittest.mock import MagicMock

from cracker.cracker import Cracker


def test_set_action_connects_citation_reducer():
    cracker = object.__new__(Cracker)
    cracker.gui = MagicMock()
    cracker.key_manager = MagicMock()

    cracker.set_action()

    cracker.gui.cite_action.triggered.connect.assert_called_once_with(cracker.reduce_cite)


def test_change_speaker_reuses_one_backend_in_gui():
    cracker = object.__new__(Cracker)
    cracker.player = MagicMock()
    cracker.gui = MagicMock()
    speaker = MagicMock()
    cracker.get_speaker = MagicMock(return_value=speaker)

    cracker.change_speaker("espeak")

    cracker.get_speaker.assert_called_once_with("espeak", cracker.player)
    cracker.gui.change_speaker.assert_called_once_with("espeak", speaker)
    assert cracker.speaker is speaker
