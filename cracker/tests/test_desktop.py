from unittest.mock import patch

from pynput import keyboard
from PyQt5.QtMultimedia import QMediaPlayer

from cracker.keylogger import KeyBoardManager


def test_qt_multimedia_player_is_available():
    assert QMediaPlayer is not None


@patch("cracker.keylogger.keyboard.Listener")
def test_global_shortcut_emits_after_full_sequence(listener):
    manager = KeyBoardManager()
    emitted = []
    manager.GlobalReadSignal.connect(lambda: emitted.append(True))
    manager.sequence = [keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.space]

    for key in manager.sequence:
        manager.on_press(key)
    manager.on_release(keyboard.Key.space)

    assert emitted == [True]
    assert manager._pressed == set()
    listener.assert_called_once()
