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
        self._start_thread = start_thread or (lambda target: threading.Thread(target=target, daemon=True).start())
        self._cancelled = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def start(self) -> None:
        self._start_thread(self._run)

    def cancel(self) -> None:
        self._cancelled.set()

    def _run(self) -> None:
        done: list[AudioSegment] = []
        with ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="synthesis") as pool:
            futures: list[Future[AudioSegment]] = [
                pool.submit(self._synthesize, index, chunk) for index, chunk in enumerate(self._chunks)
            ]
            try:
                for index, future in enumerate(futures):
                    segment = future.result()
                    done.append(segment)
                    if self.cancelled:
                        break
                    self.segmentReady.emit(segment, index < len(futures) - 1)
            except Exception as error:
                self._logger.exception("Speech synthesis failed")
                if not self.cancelled:
                    self.failed.emit(str(error))
                self._cancelled.set()
            finally:
                for future in futures:
                    future.cancel()
                # Requests already running finish; keep their files too so they can be removed.
                done.extend(f.result() for f in futures[len(done) :] if not f.cancelled() and f.exception() is None)
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
        job.segmentReady.connect(lambda segment, more: self._segment_ready(job, segment, more))
        job.finished.connect(lambda segments: self._finished(job, segments))
        job.failed.connect(lambda message: self._failed(job, message))
        job.start()

    def cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self._job = None

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

    def _finished(self, job: SynthesisJob, segments: list[AudioSegment]) -> None:
        if job is not self._job:
            remove_files(segments)  # cancelled after the job's last check; the files are ours now
            return
        self._job = None
        self._on_finished(segments)

    def _failed(self, job: SynthesisJob, message: str) -> None:
        if job is not self._job:
            return
        self._job = None
        self._player.stop()
        self._on_error(message)
