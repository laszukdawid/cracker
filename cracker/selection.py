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
SHUTDOWN_WAIT_S = 2.0


def _macos_selected_text() -> str:
    from cracker import selection_macos

    return selection_macos.get_selected_text()


def _macos_is_trusted(prompt: bool) -> bool:
    from cracker import selection_macos

    return selection_macos.is_trusted(prompt=prompt)


class SelectionReader(QObject):
    """Emits ``textReady`` with the current selection, or ``failed`` with a message for the user.

    Both are emitted on the Qt main thread. A result is dropped if ``cancel()`` was called after
    the request, so a Stop or a newer read wins over a selection that was still being fetched.
    """

    textReady = pyqtSignal(str)
    failed = pyqtSignal(str)
    _fetched = pyqtSignal(int, str, str)  # request id, text, error message

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
        self._request_id = 0
        self._closing = False
        self._fetched.connect(self._deliver)

    def request(self) -> None:
        """Start fetching the selection; call from the Qt main thread."""
        if self._closing:
            return
        self._request_id += 1
        if self._platform != "darwin":
            self._request_qt_selection()
            return
        try:
            self._request_macos(self._request_id)
        except Exception as exc:
            self._logger.exception("Couldn't start reading the selection")
            self.failed.emit(f"Couldn't read the selected text: {exc}")

    def cancel(self) -> None:
        """Drop the result of any request still in flight."""
        self._request_id += 1

    def shutdown(self) -> None:
        """Stop accepting requests and wait for a running fetch to restore the clipboard."""
        self._closing = True
        self.cancel()
        if self._busy.acquire(timeout=SHUTDOWN_WAIT_S):
            self._busy.release()
        else:
            self._logger.warning("Selection read still running at shutdown")

    def _request_qt_selection(self) -> None:
        if self._clipboard.supportsSelection():
            self.textReady.emit(self._clipboard.text(QClipboard.Mode.Selection))
        else:
            self.failed.emit("Reading the selection isn't supported here; use the clipboard shortcut instead.")

    def _request_macos(self, request_id: int) -> None:
        if not self._is_trusted(True):
            self.failed.emit(ACCESSIBILITY_HINT)
            return
        if not self._busy.acquire(blocking=False):
            self._logger.debug("Selection read already in progress")
            return
        try:
            self._start_thread(lambda: self._fetch_in_background(request_id))
        except Exception:
            self._busy.release()
            raise

    def _fetch_in_background(self, request_id: int) -> None:
        try:
            text, error = self._fetch(), ""
        except Exception as exc:
            self._logger.exception("Reading the selection failed")
            text, error = "", f"Couldn't read the selected text: {exc}"
        finally:
            self._busy.release()
        self._fetched.emit(request_id, text, error)

    def _deliver(self, request_id: int, text: str, error: str) -> None:
        if request_id != self._request_id or self._closing:
            self._logger.debug("Dropping a selection result that was cancelled")
            return
        if error:
            self.failed.emit(error)
        else:
            self.textReady.emit(text)
