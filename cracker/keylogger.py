import importlib
import sys
from typing import Any, Callable, Sequence

from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

MODIFIERS = {
    keyboard.Key.alt,
    keyboard.Key.alt_r,
    keyboard.Key.cmd,
    keyboard.Key.cmd_r,
    keyboard.Key.ctrl,
    keyboard.Key.ctrl_r,
    keyboard.Key.shift,
    keyboard.Key.shift_r,
}


def parse_hotkey(names: Sequence[str]) -> frozenset:
    """Turn names such as ``["ctrl", "shift", "space"]`` or ``["f6"]`` into pynput keys."""
    if isinstance(names, str) or not names:
        raise ValueError(f"Shortcut must be a non-empty list of key names, got {names!r}")
    keys = set()
    for name in names:
        key_name = str(name).strip().lower()
        if key_name not in keyboard.Key.__members__:
            raise ValueError(f"Unknown key {name!r} in shortcut {list(names)}")
        keys.add(keyboard.Key[key_name])
    return frozenset(keys)


class KeyBoardManager(QObject):
    """Listens for the global shortcuts while Cracker runs in the background."""

    GlobalReadSignal = pyqtSignal()
    SelectionReadSignal = pyqtSignal()

    def __init__(self, *args):
        super(KeyBoardManager, self).__init__(*args)
        self.listener: Any = None
        self._hotkeys: list[tuple[frozenset, Any]] = []
        self._pressed = set()
        self._swallowed_vks: set[int] = set()

    def start(self, clipboard: Sequence[str], selection: Sequence[str], swallow_selection: bool = False) -> None:
        """Start listening; raises ValueError for an unknown key name.

        ``swallow_selection`` stops the selection shortcut's key from reaching the frontmost
        app on macOS. It needs the Accessibility permission, without which macOS refuses the tap.
        """
        selection_keys = parse_hotkey(selection)
        self._hotkeys = [
            (parse_hotkey(clipboard), self.GlobalReadSignal),
            (selection_keys, self.SelectionReadSignal),
        ]
        options = {}
        if swallow_selection and sys.platform == "darwin":
            options["darwin_intercept"] = self._darwin_interceptor(selection_keys)
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release, **options)
        self.listener.start()

    def stop(self):
        self._pressed.clear()
        if self.listener is not None:
            self.listener.stop()

    def on_press(self, key):
        self._pressed.add(key)

    def on_release(self, key):
        for hotkey, signal in self._hotkeys:
            if hotkey <= self._pressed:
                signal.emit()
                self._pressed -= hotkey
                break
        self._pressed.discard(key)

    def _darwin_interceptor(self, hotkey: frozenset) -> Callable[[Any, Any], Any]:
        quartz: Any = importlib.import_module("Quartz")
        triggers = hotkey - MODIFIERS
        modifiers = hotkey & MODIFIERS
        trigger_vks = {key.value.vk for key in triggers}

        def intercept(event_type, event):
            if event_type not in (quartz.kCGEventKeyDown, quartz.kCGEventKeyUp):
                return event
            vk = quartz.CGEventGetIntegerValueField(event, quartz.kCGKeyboardEventKeycode)
            if vk not in trigger_vks:
                return event
            if event_type == quartz.kCGEventKeyDown and modifiers <= self._pressed:
                self._swallowed_vks.add(vk)
                return None
            if event_type == quartz.kCGEventKeyUp and vk in self._swallowed_vks:
                self._swallowed_vks.discard(vk)
                return None
            return event

        return intercept
