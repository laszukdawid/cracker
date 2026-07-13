"""Qt wiring that drives the pure read-along engine from playback.

Keeps the read-along runtime out of ``MainWindow``: this controller connects
the ``AudioPlayer`` lifecycle/position signals (and a fallback timer) to a
:class:`~cracker.read_along.ReadAlongSession`, then pushes render calls to a
view that only knows how to draw (highlight / progress / status).
"""

from typing import Protocol

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtMultimedia import QMediaPlayer

from cracker.audio_player import AudioPlayer
from cracker.read_along import Progress, ReadAlongSession, build_session


class ReadAlongView(Protocol):
    """The render surface the controller needs (implemented by MainWindow)."""

    def editor_text(self) -> str: ...
    def current_wpm(self) -> int: ...
    def highlight_span(self, start: int, length: int, doc_len: int) -> None: ...
    def clear_highlight(self) -> None: ...
    def set_read_progress(self, percent: int) -> None: ...
    def set_read_status(self, reading: bool, words_done: int = 0, total: int = 0) -> None: ...
    def set_reading_readonly(self, reading: bool) -> None: ...


class ReadAlongController(QObject):
    """Turns playback progress into highlight/progress/status render calls."""

    def __init__(self, view: ReadAlongView, player: AudioPlayer):
        super().__init__()
        self._view = view
        self._player = player
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._on_tick)
        self._pending_source = "textarea"
        self._pending_text = ""
        self._session: ReadAlongSession | None = None
        self._mode = "idle"
        self._elapsed = 0.0

        player.readStarted.connect(self._on_started)
        player.readFinished.connect(self._on_finished)
        player.positionChanged.connect(self._on_position)
        player.playbackStateChanged.connect(self._on_state)

    def set_read_context(self, source: str, text: str = "") -> None:
        """Set by the controller before each read: 'textarea' or 'clipboard'."""
        self._pending_source = source
        self._pending_text = text

    def _on_started(self) -> None:
        self._session = build_session(
            source=self._pending_source,
            editor_text=self._view.editor_text(),
            read_text=self._pending_text,
            segment_marks=self._player.segment_marks(),
            wpm=self._view.current_wpm(),
        )
        self._mode = "marks" if self._player.has_marks else "estimate"
        self._elapsed = 0.0
        self._view.set_reading_readonly(True)
        self._view.set_read_progress(0)
        self._view.set_read_status(reading=True, words_done=0, total=self._session.total)
        # The estimate timer starts on PlayingState (see _on_state), not here, so
        # it doesn't advance during media load / stalls / invalid media.

    def _on_position(self, position_ms: int) -> None:
        if self._session is None or self._mode != "marks":
            return
        self._apply(
            self._session.progress_source.progress(
                segment_index=self._player.current_segment(),
                position_ms=position_ms,
                elapsed_sec=0.0,
            )
        )

    def _on_tick(self) -> None:
        if self._session is None or self._mode != "estimate":
            return
        self._elapsed += self._timer.interval() / 1000.0
        progress = self._session.progress_source.progress(segment_index=-1, position_ms=0, elapsed_sec=self._elapsed)
        self._apply(progress)
        if progress is not None and progress.fraction >= 1.0:
            self._timer.stop()

    def _on_state(self, state) -> None:
        # Pause/resume only affects the estimate timer; marks mode freezes on its
        # own because positionChanged stops firing while paused.
        if self._session is None or self._mode != "estimate":
            return
        if state == QMediaPlayer.PlaybackState.PausedState:
            self._timer.stop()
        elif state == QMediaPlayer.PlaybackState.PlayingState and not self._timer.isActive():
            self._timer.start()

    def _on_finished(self) -> None:
        self._timer.stop()
        self._session = None
        self._mode = "idle"
        self._view.clear_highlight()
        self._view.set_reading_readonly(False)
        self._view.set_read_progress(0)
        self._view.set_read_status(reading=False)

    def _apply(self, progress: Progress | None) -> None:
        if progress is None or self._session is None:
            return
        self._view.set_read_progress(int(progress.fraction * 100))
        if progress.word_index is not None and progress.word_index != self._session.index:
            self._session.index = progress.word_index
            span = self._session.highlight_for(progress.word_index)
            if span is not None:
                self._view.highlight_span(span[0], span[1], self._session.doc_len)
        self._view.set_read_status(reading=True, words_done=progress.words_done, total=self._session.total)
