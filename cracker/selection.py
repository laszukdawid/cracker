"""Fetch the text the user has selected in another app."""

import sys
import threading
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QClipboard

from cracker.utils import get_logger

ACCESSIBILITY_HINT = (
    "To read selected text, allow Cracker's launcher in System Settings → Privacy & Security → Accessibility."
)


def _macos_selected_text() -> str:
    from cracker import selection_macos

    return selection_macos.get_selected_text()


def _macos_is_trusted(prompt: bool) -> bool:
    from cracker import selection_macos

    return selection_macos.is_trusted(prompt=prompt)


class SelectionReader(QObject):
    """Emits ``textReady`` with the current selection, or ``failed`` with a message for the user."""

    textReady = pyqtSignal(str)
    failed = pyqtSignal(str)

    _logger = get_logger(__name__)

    def __init__(
        self,
        clipboard: QClipboard,
        platform: str = sys.platform,
        fetch: Callable[[], str] = _macos_selected_text,
        is_trusted: Callable[[bool], bool] = _macos_is_trusted,
        start_thread: Callable[[Callable[[], None]], None] | None = None,
    ):
        super().__init__()
        self._clipboard = clipboard
        self._platform = platform
        self._fetch = fetch
        self._is_trusted = is_trusted
        self._start_thread = start_thread or (lambda target: threading.Thread(target=target, daemon=True).start())
        self._busy = threading.Lock()

    def request(self) -> None:
        """Start fetching the selection; call from the Qt main thread."""
        if self._platform == "darwin":
            self._request_macos()
        elif self._clipboard.supportsSelection():
            self.textReady.emit(self._clipboard.text(QClipboard.Mode.Selection))
        else:
            self.failed.emit("Reading the selection isn't supported here; use the clipboard shortcut instead.")

    def _request_macos(self) -> None:
        if not self._is_trusted(True):
            self.failed.emit(ACCESSIBILITY_HINT)
            return
        if not self._busy.acquire(blocking=False):
            self._logger.debug("Selection read already in progress")
            return
        try:
            self._start_thread(self._fetch_in_background)
        except Exception:
            self._busy.release()
            raise

    def _fetch_in_background(self) -> None:
        try:
            text = self._fetch()
        except Exception as exc:
            self._logger.exception("Reading the selection failed")
            self.failed.emit(f"Couldn't read the selected text: {exc}")
        else:
            self.textReady.emit(text)
        finally:
            self._busy.release()
