"""Fetch the text the user has selected in another app."""

import sys
import threading
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QClipboard

from cracker.selection_macos import SelectionCancelled
from cracker.utils import get_logger

CANCELLED = -1

ACCESSIBILITY_HINT = (
    "To read selected text, allow Cracker's launcher in System Settings → Privacy & Security → Accessibility."
)


def _macos_selected_text(should_continue: Callable[[], bool]) -> str:
    from cracker import selection_macos

    return selection_macos.get_selected_text(should_continue)


def _macos_is_trusted(prompt: bool) -> bool:
    from cracker import selection_macos

    return selection_macos.is_trusted(prompt=prompt)


class SelectionReader(QObject):
    """Emits ``textReady`` with the current selection, or ``failed`` with a message for the user.

    Both are emitted on the Qt main thread. Text is dropped if ``cancel()`` was called after the
    request, so a Stop or a newer read wins over a selection that was still being fetched; errors
    are always reported, since one may mean the clipboard wasn't restored.
    """

    textReady = pyqtSignal(str)
    failed = pyqtSignal(str)
    _fetched = pyqtSignal(int, str, str)  # request id, text, error message

    _logger = get_logger(__name__)

    def __init__(
        self,
        clipboard: QClipboard,
        platform: str = sys.platform,
        fetch: Callable[[Callable[[], bool]], str] = _macos_selected_text,
        is_trusted: Callable[[bool], bool] = _macos_is_trusted,
        start_thread: Callable[[Callable[[], None]], None] | None = None,
    ):
        super().__init__()
        self._clipboard = clipboard
        self._platform = platform
        self._fetch = fetch
        self._is_trusted = is_trusted
        # Not a daemon: at exit Python waits for a running fetch, so it can put the clipboard back.
        self._start_thread = start_thread or (lambda target: threading.Thread(target=target).start())
        self._busy = threading.Lock()
        self._request_id = 0
        self._closing = False
        self._when_idle: list[tuple[int, Callable[[], None]]] = []
        self._fetched.connect(self._deliver)

    def request(self) -> None:
        """Start fetching the selection; call from the Qt main thread."""
        if self._closing:
            return
        if self._platform != "darwin":
            self._request_qt_selection()
            return
        try:
            self._request_macos()
        except Exception as exc:
            self._logger.exception("Couldn't start reading the selection")
            self.failed.emit(f"Couldn't read the selected text: {exc}")

    def cancel(self) -> None:
        """Drop the result of any request still in flight."""
        self._request_id += 1

    def when_idle(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` now, or once a running fetch has put the clipboard back.

        A later ``cancel()`` (a Stop or a newer read) or ``request()`` drops the queued callback.
        """
        if self._busy.locked():
            self._when_idle.append((self._request_id, callback))
        else:
            callback()

    def shutdown(self) -> None:
        """Stop accepting requests; a running fetch skips Cmd+C if it hasn't sent it yet."""
        self._closing = True
        self.cancel()

    def _request_qt_selection(self) -> None:
        if self._clipboard.supportsSelection():
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
        # Counted only once accepted, so an ignored press doesn't cancel the read in flight.
        self._request_id += 1
        request_id = self._request_id
        try:
            self._start_thread(lambda: self._fetch_in_background(request_id))
        except Exception:
            self._busy.release()
            raise

    def _fetch_in_background(self, request_id: int) -> None:
        text, error = "", ""
        try:
            text = self._fetch(lambda: request_id == self._request_id and not self._closing)
        except SelectionCancelled:
            request_id = CANCELLED
        except Exception as exc:
            self._logger.exception("Reading the selection failed")
            error = f"Couldn't read the selected text: {exc}"
        finally:
            self._busy.release()
        if not self._closing:
            self._fetched.emit(request_id, text, error)

    def _deliver(self, request_id: int, text: str, error: str) -> None:
        if error:
            self.failed.emit(error)
        elif request_id != self._request_id:
            self._logger.debug("Dropping a selection that was cancelled")
        else:
            self.textReady.emit(text)
        # A new fetch may have started before this queued call ran; its completion runs these instead.
        if not self._busy.locked():
            queued, self._when_idle = self._when_idle, []
            for queued_id, callback in queued:
                if queued_id == self._request_id and not self._closing:
                    callback()
