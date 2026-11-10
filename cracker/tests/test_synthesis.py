import threading
import wave
from pathlib import Path

import pytest
from PyQt6.QtCore import QEventLoop, QTimer
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

    def set_preparing(self, preparing):
        self.calls.append(("preparing", preparing))


def _sync_job(chunks, synthesize):
    job = SynthesisJob(chunks, synthesize)
    job._start_thread = lambda target: target()
    return job


def test_queue_starts_playing_the_first_segment_and_appends_the_rest(qt_app: QApplication, tmp_path: Path):
    player, kept = FakePlayer(), []
    queue = SpeechQueue(player, on_error=lambda message: None)

    queue.start(["a", "b"], _writer(tmp_path), on_finished=kept.append, job_factory=_sync_job)

    assert player.calls == [
        ("preparing", True),
        ("play", ["chunk-0.mp3"], True),
        ("preparing", False),
        ("append", "chunk-1.mp3", False),
        ("preparing", False),  # repeated on finish; the real player ignores repeats
    ]
    assert len(kept[0]) == 2 and not queue.busy


def test_queue_stops_and_reports_a_failure(qt_app: QApplication, tmp_path: Path):
    player, errors = FakePlayer(), []
    queue = SpeechQueue(player, on_error=errors.append)

    queue.start(["a", "b"], _writer(tmp_path, fail_on=1), job_factory=_sync_job)

    assert player.calls[-2:] == [("preparing", False), ("stop",)]
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

    assert player.calls == [("preparing", True), ("preparing", False)] and kept == []
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


def test_cancel_skips_chunks_that_have_not_started(qt_app: QApplication, tmp_path: Path):
    release_first = threading.Event()
    first_started = threading.Event()
    started = []

    def synthesize(index, chunk):
        started.append(index)
        if index == 0:
            first_started.set()
            release_first.wait(2)
        return AudioSegment(path=str(tmp_path / f"{index}.mp3"))

    job = SynthesisJob([str(i) for i in range(20)], synthesize, max_workers=2)
    worker = threading.Thread(target=job._run)
    worker.start()
    assert first_started.wait(2)
    job.cancel()
    release_first.set()
    worker.join(2)

    assert len(started) <= 2  # only requests already in flight when Stop was pressed


def test_job_cancelled_before_it_runs_requests_nothing(qt_app: QApplication, tmp_path: Path):
    started = []

    def synthesize(index: int, chunk: str) -> AudioSegment:
        started.append(index)
        return AudioSegment(path=str(tmp_path / f"{index}.mp3"))

    job = SynthesisJob(["a", "b"], synthesize)
    job.cancel()
    _run_sync(job)
    assert started == []


def _silence(path: Path) -> AudioSegment:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8_000)
        output.writeframes(b"\0\0" * 400)
    return AudioSegment(path=str(path))


def _wait_for(player: AudioPlayer, condition, timeout_ms=3000) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: condition() and loop.quit())
    timer.start(10)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    timer.stop()


def test_pause_during_a_synthesis_gap_holds_the_next_segment(player: AudioPlayer, tmp_path: Path):
    player.audio_output.setMuted(True)
    player.play_segments([_silence(tmp_path / "a.wav")], more_coming=True)
    _wait_for(player, lambda: player.waiting_for_segment)
    assert player.waiting_for_segment

    player.pause()
    player.append_segment(_silence(tmp_path / "b.wav"))
    _wait_for(player, lambda: False, timeout_ms=200)

    assert player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    assert player.source().toLocalFile().endswith("b.wav")

    player.play()  # Resume
    assert player.playbackState() == QMediaPlayer.PlaybackState.PlayingState


def test_pause_resume_pause_during_a_gap_ends_paused(player: AudioPlayer, tmp_path: Path):
    paused = QSignalSpy(player.pausedChanged)
    player.audio_output.setMuted(True)
    player.play_segments([_silence(tmp_path / "a.wav")], more_coming=True)
    _wait_for(player, lambda: player.waiting_for_segment)

    player.pause()
    player.play()
    player.pause()
    assert player.is_paused and [event[0] for event in paused] == [True, False, True]

    player.append_segment(_silence(tmp_path / "b.wav"))
    _wait_for(player, lambda: False, timeout_ms=200)
    assert player.playbackState() == QMediaPlayer.PlaybackState.PausedState


def test_job_removes_submitted_files_when_submitting_fails_at_exit(qt_app: QApplication, tmp_path: Path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from cracker.speaker import synthesis

    class ShuttingDown(ThreadPoolExecutor):
        submitted = 0

        def submit(self, *args, **kwargs):
            if ShuttingDown.submitted == 1:
                raise RuntimeError("cannot schedule new futures after interpreter shutdown")
            ShuttingDown.submitted += 1
            return super().submit(*args, **kwargs)

    monkeypatch.setattr(synthesis, "ThreadPoolExecutor", ShuttingDown)
    job = SynthesisJob(["a", "b", "c"], _writer(tmp_path))
    _run_sync(job)

    assert job.cancelled and list(tmp_path.iterdir()) == []
