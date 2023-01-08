from typing import List

from pynput import keyboard
from PyQt5.QtCore import QObject, pyqtSignal


class KeyBoardManager(QObject):
    GlobalReadSignal = pyqtSignal()

    def __init__(self, *args):
        super(KeyBoardManager, self).__init__(*args)
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self._pressed = set()

    def stop(self):
        self._pressed.clear()
        self.listener.stop()
    
    def on_press(self, key):
        self._pressed |= {key}

    def on_release(self, key):
        if set(self.sequence) <= self._pressed:
            self.GlobalReadSignal.emit()
            for key in self.sequence:
                self._pressed -= {key}
        self._pressed -= {key}

    def run(self, sequence: List[str]):
        self.sequence = [keyboard.Key[s.lower()] for s in sequence]
        self.listener.start()
