"""Synthesise speech off the GUI thread and hand the audio over chunk by chunk."""

import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from cracker.read_along import AudioSegment
from cracker.utils import get_logger

MAX_PARALLEL_REQUESTS = 4

SynthesizeChunk = Callable[[int, str], AudioSegment]


def remove_files(segments: list[AudioSegment]) -> None:
    for segment in segments:
        try:
            os.remove(segment.path)
        except OSError:
            pass


class SynthesisJob(QObject):
    """Synthesises ``chunks`` in parallel and emits each segment in order on the GUI thread.

    Create and connect it on the GUI thread; the signals are then delivered there. After ``cancel()``
    nothing more is emitted and the job deletes the files it wrote.
    """

    segmentReady = pyqtSignal(object, bool)  # AudioSegment, more segments follow
    finished = pyqtSignal(list)  # every segment, once all are ready
    failed = pyqtSignal(str)

    _logger = get_logger(__name__)

    def __init__(
        self,
        chunks: list[str],
        synthesize: SynthesizeChunk,
        max_workers: int = MAX_PARALLEL_REQUESTS,
        start_thread: Callable[[Callable[[], None]], None] | None = None,
    ):
        super().__init__()
        self._chunks = chunks
        self._synthesize = synthesize
        self._max_workers = max_workers
        # Not a daemon: at exit Python waits for requests already sent, so their files are removed.
        self._start_thread = start_thread or (lambda target: threading.Thread(target=target, name="synthesis").start())
        self._cancelled = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def start(self) -> None:
        self._start_thread(self._run)

    def cancel(self) -> None:
        self._cancelled.set()

    def _synthesize_unless_cancelled(self, index: int, chunk: str) -> AudioSegment | None:
        # Chunks still queued when the read is cancelled must not be requested (or billed).
        if self.cancelled:
            return None
        return self._synthesize(index, chunk)

    def _run(self) -> None:
        if self.cancelled:
            return
        done: list[AudioSegment] = []
        futures: list[Future[AudioSegment | None]] = []
        with ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="synthesis") as pool:
            try:
                for index, chunk in enumerate(self._chunks):
                    if self.cancelled:
                        break
                    # Raises at interpreter exit; the finally below still collects what was submitted.
                    futures.append(pool.submit(self._synthesize_unless_cancelled, index, chunk))
                for index, future in enumerate(futures):
                    segment = future.result()
                    if segment is None:  # skipped after cancel
                        break
                    done.append(segment)
                    if self.cancelled:
                        break
                    self.segmentReady.emit(segment, index < len(self._chunks) - 1)
            except Exception as error:
                self._logger.exception("Speech synthesis failed")
                if not self.cancelled:
                    self.failed.emit(str(error))
                self._cancelled.set()
            finally:
                for future in futures:
                    future.cancel()
                # Requests already running finish; keep their files too so they can be removed.
                for future in futures:
                    if not future.cancelled() and future.exception() is None:
                        segment = future.result()
                        if segment is not None and segment not in done:
                            done.append(segment)
        if self.cancelled:
            remove_files(done)
        else:
            self.finished.emit(done)


class SpeechQueue:
    """Runs one synthesis job at a time for a speaker and feeds its segments to the player.

    Starting a job, or ``cancel()``, drops the previous one. Call everything on the GUI thread.
    """

    def __init__(self, player, on_error: Callable[[str], None]):
        self._player = player
        self._on_error = on_error
        self._job: SynthesisJob | None = None
        self._started_playing = False
        self._on_finished: Callable[[list[AudioSegment]], None] = remove_files

    def start(
        self,
        chunks: list[str],
        synthesize: SynthesizeChunk,
        on_finished: Callable[[list[AudioSegment]], None] = remove_files,
        job_factory: Callable[[list[str], SynthesizeChunk], SynthesisJob] = SynthesisJob,
    ) -> None:
        """``on_finished`` receives every segment once all are ready and then owns their files."""
        self.cancel()
        job = job_factory(chunks, synthesize)
        self._job = job
        self._started_playing = False
        self._on_finished = on_finished
        self._player.set_preparing(True)
        job.segmentReady.connect(lambda segment, more: self._segment_ready(job, segment, more))
        job.finished.connect(lambda segments: self._finished(job, segments))
        job.failed.connect(lambda message: self._failed(job, message))
        job.start()

    def cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self._job = None
            self._player.set_preparing(False)

    @property
    def busy(self) -> bool:
        return self._job is not None

    def _segment_ready(self, job: SynthesisJob, segment: AudioSegment, more: bool) -> None:
        if job is not self._job:
            return  # cancelled; the job removes its own files
        if self._started_playing:
            self._player.append_segment(segment, more)
        else:
            self._started_playing = True
            self._player.play_segments([segment], more)
            self._player.set_preparing(False)

    def _finished(self, job: SynthesisJob, segments: list[AudioSegment]) -> None:
        if job is not self._job:
            remove_files(segments)  # cancelled after the job's last check; the files are ours now
            return
        self._job = None
        self._player.set_preparing(False)
        self._on_finished(segments)

    def _failed(self, job: SynthesisJob, message: str) -> None:
        if job is not self._job:
            return
        self._job = None
        self._player.set_preparing(False)
        self._player.stop()
        self._on_error(message)
