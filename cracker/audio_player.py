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
    _logger = get_logger(__name__)

    def __init__(self) -> None:
        super().__init__()
        self.audio_output = QAudioOutput(self)
        self.setAudioOutput(self.audio_output)
        self._queued_sources: deque[QUrl] = deque()
        self._segment_marks: list[list[WordMark]] = []
        self._current_index = -1
        self._reading = False
        self.mediaStatusChanged.connect(self._handle_media_status)

    def play_file(self, filepath: str) -> None:
        self.play_files([filepath])

    def play_files(self, filepaths: Iterable[str]) -> None:
        """Plays plain audio files with no word timing (estimate fallback)."""
        self.play_segments([AudioSegment(path=filepath) for filepath in filepaths])

    def play_segments(self, segments: Iterable[AudioSegment]) -> None:
        """Plays audio segments in order, carrying their per-word marks."""
        segments = list(segments)
        self.stop()
        self._segment_marks = [list(segment.marks) for segment in segments]
        self._queued_sources.extend(QUrl.fromLocalFile(segment.path) for segment in segments)
        self._play_next()

    def stop(self) -> None:
        self._queued_sources.clear()
        self._segment_marks = []
        self._current_index = -1
        was_reading = self._reading
        self._reading = False
        super().stop()
        if was_reading:
            self.readFinished.emit()

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
        self.play()
