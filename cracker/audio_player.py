from collections import deque
from collections.abc import Iterable

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from cracker.read_along import AudioSegment, WordMark
from cracker.utils import get_logger


class AudioPlayer(QMediaPlayer):
    """Qt 6 media player that plays a queue of synthesized audio segments.

    Each segment may carry per-word timing marks (see :mod:`cracker.read_along`).
    Read-along consumers should use the ``readStarted`` / ``readFinished`` /
    ``segmentStarted`` signals rather than raw ``playbackStateChanged`` — the
    latter flickers to ``Stopped`` between queued files, which is *not* the end
    of the read.
    """

    playback_failed = pyqtSignal(str)
    readStarted = pyqtSignal()
    readFinished = pyqtSignal()
    segmentStarted = pyqtSignal(int)
    segmentsAdded = pyqtSignal()
    preparingChanged = pyqtSignal(bool)  # speech for a new read is being synthesised
    _logger = get_logger(__name__)

    def __init__(self) -> None:
        super().__init__()
        self.audio_output = QAudioOutput(self)
        self.setAudioOutput(self.audio_output)
        self._queued_sources: deque[QUrl] = deque()
        self._segment_marks: list[list[WordMark]] = []
        self._current_index = -1
        self._reading = False
        self._more_coming = False  # more segments will be appended to this read
        self._waiting = False  # the queue ran dry while more segments are coming
        self._user_paused = False  # paused by the user; kept across segments that arrive later
        self._preparing = False
        self.mediaStatusChanged.connect(self._handle_media_status)

    def play_file(self, filepath: str) -> None:
        self.play_files([filepath])

    def play_files(self, filepaths: Iterable[str]) -> None:
        """Plays plain audio files with no word timing (estimate fallback)."""
        self.play_segments([AudioSegment(path=filepath) for filepath in filepaths])

    def play_segments(self, segments: Iterable[AudioSegment], more_coming: bool = False) -> None:
        """Plays audio segments in order, carrying their per-word marks.

        With ``more_coming`` the read stays open for ``append_segment`` until one is appended
        with ``more_coming=False``.
        """
        segments = list(segments)
        self.stop()
        self._more_coming = more_coming
        self._segment_marks = [list(segment.marks) for segment in segments]
        self._queued_sources.extend(QUrl.fromLocalFile(segment.path) for segment in segments)
        self._play_next()

    def append_segment(self, segment: AudioSegment, more_coming: bool = False) -> None:
        """Adds a segment to the current read, or starts a new read if none is open."""
        if not self._reading:
            self.play_segments([segment], more_coming)
            return
        self._more_coming = more_coming
        self._segment_marks.append(list(segment.marks))
        self._queued_sources.append(QUrl.fromLocalFile(segment.path))
        self.segmentsAdded.emit()
        if self._waiting:
            self._waiting = False
            self._play_next()

    def pause(self) -> None:
        self._user_paused = True
        super().pause()

    def play(self) -> None:
        self._user_paused = False
        if self._waiting:
            return  # nothing is loaded yet; the next segment starts playing when it arrives
        super().play()

    def set_preparing(self, preparing: bool) -> None:
        if preparing != self._preparing:
            self._preparing = preparing
            self.preparingChanged.emit(preparing)

    @property
    def preparing(self) -> bool:
        return self._preparing

    def stop(self) -> None:
        self._queued_sources.clear()
        self._segment_marks = []
        self._current_index = -1
        self._more_coming = False
        self._waiting = False
        self._user_paused = False
        was_reading = self._reading
        self._reading = False
        super().stop()
        if was_reading:
            self.readFinished.emit()

    @property
    def is_reading(self) -> bool:
        return self._reading

    @property
    def waiting_for_segment(self) -> bool:
        """The read played everything it has so far and the next segment is still being made."""
        return self._waiting

    @property
    def has_marks(self) -> bool:
        return any(self._segment_marks)

    def segment_marks(self) -> list[list[WordMark]]:
        return self._segment_marks

    def current_segment(self) -> int:
        return self._current_index

    def _handle_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            source = self.source().toLocalFile() or self.source().toString()
            message = f"Unable to play audio source: {source or '<unknown>'}"
            self._logger.error(message)
            self.playback_failed.emit(message)
            self._play_next()
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()

    def _play_next(self) -> None:
        if not self._queued_sources:
            if self._reading and self._more_coming:
                self._waiting = True  # the next segment is still being synthesised
                return
            if self._reading:
                self._reading = False
                self._current_index = -1
                self.readFinished.emit()
            return
        if not self._reading:
            self._reading = True
            self.readStarted.emit()
        self._current_index += 1
        source = self._queued_sources.popleft()
        if self.source() == source:
            # QMediaPlayer caches media by URL and will not reload a file whose
            # contents changed at the same path (temp filenames are reused
            # across reads), so clear the source first to force a fresh decode.
            self.setSource(QUrl())
        self.setSource(source)
        self.segmentStarted.emit(self._current_index)
        if self._user_paused:
            super().pause()  # loaded, but waits for Resume
        else:
            super().play()
