from collections import deque
from collections.abc import Iterable

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from cracker.utils import get_logger


class AudioPlayer(QMediaPlayer):
    """Qt 6 media player that restores sequential playback across multiple files."""

    playback_failed = pyqtSignal(str)
    _logger = get_logger(__name__)

    def __init__(self) -> None:
        super().__init__()
        self.audio_output = QAudioOutput(self)
        self.setAudioOutput(self.audio_output)
        self._queued_sources: deque[QUrl] = deque()
        self.mediaStatusChanged.connect(self._handle_media_status)

    def play_file(self, filepath: str) -> None:
        self.play_files([filepath])

    def play_files(self, filepaths: Iterable[str]) -> None:
        self.stop()
        self._queued_sources.extend(QUrl.fromLocalFile(filepath) for filepath in filepaths)
        self._play_next()

    def stop(self) -> None:
        self._queued_sources.clear()
        super().stop()

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
            return
        self.setSource(self._queued_sources.popleft())
        self.play()
