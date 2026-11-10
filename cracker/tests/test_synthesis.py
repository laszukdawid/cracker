import threading
from pathlib import Path

import pytest
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication

from cracker.audio_player import AudioPlayer
from cracker.read_along import AudioSegment, WordMark
from cracker.speaker.synthesis import SpeechQueue, SynthesisJob


def _writer(tmp_path: Path, fail_on: int | None = None, gate: threading.Event | None = None):
    def synthesize(index: int, chunk: str) -> AudioSegment:
        if gate is not None and index > 0:
            gate.wait(2)
        if index == fail_on:
            raise RuntimeError(f"chunk {index} failed")
        path = tmp_path / f"chunk-{index}.mp3"
        path.write_text(chunk)
        return AudioSegment(path=str(path))

    return synthesize


def _run_sync(job: SynthesisJob) -> None:
    job._start_thread = lambda target: target()
    job.start()


def test_job_emits_segments_in_order_then_finishes(qt_app: QApplication, tmp_path: Path):
    job = SynthesisJob(["a", "b", "c"], _writer(tmp_path))
    ready, finished = [], []
    job.segmentReady.connect(lambda segment, more: ready.append((Path(segment.path).name, more)))
    job.finished.connect(finished.append)

    _run_sync(job)

    assert ready == [("chunk-0.mp3", True), ("chunk-1.mp3", True), ("chunk-2.mp3", False)]
    assert [Path(s.path).name for s in finished[0]] == ["chunk-0.mp3", "chunk-1.mp3", "chunk-2.mp3"]


def test_job_requests_chunks_in_parallel(qt_app: QApplication, tmp_path: Path):
    started = threading.Barrier(3, timeout=2)

    def synthesize(index, chunk):
        started.wait()  # only passes if all three chunks are in flight together
        return AudioSegment(path=str(tmp_path / f"{index}.mp3"))

    job = SynthesisJob(["a", "b", "c"], synthesize)
    finished = []
    job.finished.connect(finished.append)
    _run_sync(job)

    assert len(finished[0]) == 3


def test_job_failure_reports_once_and_removes_its_files(qt_app: QApplication, tmp_path: Path):
    job = SynthesisJob(["a", "b", "c"], _writer(tmp_path, fail_on=1))
    failures, finished = [], []
    job.failed.connect(failures.append)
    job.finished.connect(finished.append)

    _run_sync(job)

    assert failures == ["chunk 1 failed"]
    assert finished == []
    assert list(tmp_path.iterdir()) == []


def test_cancelled_job_stops_emitting_and_removes_its_files(qt_app: QApplication, tmp_path: Path):
    gate = threading.Event()
    job = SynthesisJob(["a", "b", "c"], _writer(tmp_path, gate=gate))
    ready, finished = [], []

    def on_ready(segment, more):
        ready.append(segment)
        job.cancel()
        gate.set()

    job.segmentReady.connect(on_ready)
    job.finished.connect(finished.append)
    _run_sync(job)

    assert len(ready) == 1 and finished == []
    assert list(tmp_path.iterdir()) == []


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play_segments(self, segments, more_coming=False):
        self.calls.append(("play", [Path(s.path).name for s in segments], more_coming))

    def append_segment(self, segment, more_coming=False):
        self.calls.append(("append", Path(segment.path).name, more_coming))

    def stop(self):
        self.calls.append(("stop",))


def _sync_job(chunks, synthesize):
    job = SynthesisJob(chunks, synthesize)
    job._start_thread = lambda target: target()
    return job


def test_queue_starts_playing_the_first_segment_and_appends_the_rest(qt_app: QApplication, tmp_path: Path):
    player, kept = FakePlayer(), []
    queue = SpeechQueue(player, on_error=lambda message: None)

    queue.start(["a", "b"], _writer(tmp_path), on_finished=kept.append, job_factory=_sync_job)

    assert player.calls == [("play", ["chunk-0.mp3"], True), ("append", "chunk-1.mp3", False)]
    assert len(kept[0]) == 2 and not queue.busy


def test_queue_stops_and_reports_a_failure(qt_app: QApplication, tmp_path: Path):
    player, errors = FakePlayer(), []
    queue = SpeechQueue(player, on_error=errors.append)

    queue.start(["a", "b"], _writer(tmp_path, fail_on=1), job_factory=_sync_job)

    assert player.calls[-1] == ("stop",)
    assert errors == ["chunk 1 failed"]


def test_queue_drops_a_cancelled_job_that_finished_anyway(qt_app: QApplication, tmp_path: Path):
    player, kept = FakePlayer(), []
    queue = SpeechQueue(player, on_error=lambda message: None)
    pending = []

    def deferred_job(chunks, synthesize):
        job = SynthesisJob(chunks, synthesize)
        job._start_thread = pending.append
        return job

    queue.start(["a"], _writer(tmp_path), on_finished=kept.append, job_factory=deferred_job)
    job = queue._job
    assert job is not None
    queue.cancel()
    job._cancelled.clear()  # the worker passed its last cancel check before cancel() ran
    pending.pop()()

    assert player.calls == [] and kept == []
    assert list(tmp_path.iterdir()) == []  # the stale job's files were removed


@pytest.fixture
def player(qt_app: QApplication):
    player = AudioPlayer()
    yield player
    player.stop()
    qt_app.processEvents()


def test_player_waits_for_more_segments_instead_of_finishing(player: AudioPlayer, tmp_path: Path):
    finished = QSignalSpy(player.readFinished)
    added = QSignalSpy(player.segmentsAdded)
    first = AudioSegment(path=str(tmp_path / "first.mp3"), marks=[WordMark(0, "One")])
    second = AudioSegment(path=str(tmp_path / "second.mp3"), marks=[WordMark(0, "Two")])

    player.play_segments([first], more_coming=True)
    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)

    assert player.waiting_for_segment and len(finished) == 0

    player.append_segment(second, more_coming=False)

    assert not player.waiting_for_segment and len(added) == 1
    assert player.source().toLocalFile() == second.path
    assert player.current_segment() == 1
    assert [[m.value for m in marks] for marks in player.segment_marks()] == [["One"], ["Two"]]

    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)
    assert len(finished) == 1


def test_player_append_without_an_open_read_starts_one(player: AudioPlayer, tmp_path: Path):
    started = QSignalSpy(player.readStarted)
    segment = AudioSegment(path=str(tmp_path / "late.mp3"))

    player.append_segment(segment)

    assert len(started) == 1 and player.source().toLocalFile() == segment.path


def test_stop_ends_a_read_that_was_waiting(player: AudioPlayer, tmp_path: Path):
    finished = QSignalSpy(player.readFinished)
    player.play_segments([AudioSegment(path=str(tmp_path / "a.mp3"))], more_coming=True)
    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)

    player.stop()

    assert not player.waiting_for_segment and len(finished) == 1
