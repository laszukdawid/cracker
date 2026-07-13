import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from pynput import keyboard
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication

from cracker.audio_player import AudioPlayer
from cracker.config import Configuration
from cracker.cracker_gui import MainWindow
from cracker.keylogger import KeyBoardManager
from cracker.read_along import AudioSegment, WordMark
from cracker.speaker.polly import Polly


def _make_main_window(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Configuration, "USER_CONFIG_DIR_PATH", str(tmp_path / "config"))
    monkeypatch.setattr("cracker.view.speaker_config_tab.list_aws_profiles", lambda: [])
    monkeypatch.setattr("cracker.view.speaker_config_tab.load_sso_profile", lambda _profile: None)
    config = Configuration()
    config.read_config()
    speaker = MagicMock()
    speaker.VOLUMES = list(range(100))
    speaker.RATES = [80, 120, 160, 200, 240]
    player = AudioPlayer()
    with patch.object(config, "save_user_config"):
        window = MainWindow(config, speakers={"polly": Polly})
        window.speaker = speaker
        window.player = player
        window.init()
    return window, player


def test_qt_multimedia_player_is_available():
    assert QMediaPlayer is not None


def test_audio_player_advances_through_queued_files(qt_app: QApplication, tmp_path: Path):
    player = AudioPlayer()
    first_file = tmp_path / "first.mp3"
    second_file = tmp_path / "second.mp3"

    player.play_files([str(first_file), str(second_file)])
    assert player.source().toLocalFile() == str(first_file)

    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)
    assert player.source().toLocalFile() == str(second_file)

    player.stop()
    qt_app.processEvents()


def test_audio_player_skips_invalid_media(qt_app: QApplication, tmp_path: Path):
    player = AudioPlayer()
    invalid_file = tmp_path / "invalid.mp3"
    next_file = tmp_path / "next.mp3"
    failures = QSignalSpy(player.playback_failed)

    player.play_files([str(invalid_file), str(next_file)])
    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.InvalidMedia)

    assert player.source().toLocalFile() == str(next_file)
    assert len(failures) == 1
    player.stop()
    qt_app.processEvents()


def test_audio_player_loads_and_finishes_real_audio(qt_app: QApplication, tmp_path: Path):
    audio_file = tmp_path / "silence.wav"
    with wave.open(str(audio_file), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8_000)
        output.writeframes(b"\0\0" * 800)

    player = AudioPlayer()
    player.audio_output.setMuted(True)
    statuses = QSignalSpy(player.mediaStatusChanged)
    event_loop = QEventLoop()

    def stop_after_terminal_status(status: QMediaPlayer.MediaStatus) -> None:
        if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
            event_loop.quit()

    player.mediaStatusChanged.connect(stop_after_terminal_status)
    QTimer.singleShot(3_000, event_loop.quit)
    player.play_file(str(audio_file))
    event_loop.exec()

    observed_statuses = [event[0] for event in statuses]
    assert QMediaPlayer.MediaStatus.InvalidMedia not in observed_statuses
    assert QMediaPlayer.MediaStatus.EndOfMedia in observed_statuses
    player.stop()
    qt_app.processEvents()


def test_audio_player_reloads_changed_file_at_same_path(qt_app: QApplication, tmp_path: Path):
    # QMediaPlayer caches media by URL; a second read that overwrites the same
    # temp filename must still pick up the new (longer) audio, otherwise the
    # position/duration stall at the first clip and read-along freezes partway.
    reused = tmp_path / "reused.wav"

    def write_wav(seconds: float) -> None:
        with wave.open(str(reused), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8_000)
            output.writeframes(b"\0\0" * int(8_000 * seconds))

    def play_and_measure_duration(player: AudioPlayer) -> int:
        loop = QEventLoop()

        def stop_on_terminal(status: QMediaPlayer.MediaStatus) -> None:
            if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia):
                loop.quit()

        player.mediaStatusChanged.connect(stop_on_terminal)
        QTimer.singleShot(4_000, loop.quit)
        player.play_file(str(reused))
        loop.exec()
        player.mediaStatusChanged.disconnect(stop_on_terminal)
        return player.duration()

    player = AudioPlayer()
    player.audio_output.setMuted(True)

    started = QSignalSpy(player.readStarted)
    finished = QSignalSpy(player.readFinished)
    segment_started = QSignalSpy(player.segmentStarted)

    write_wav(0.3)
    first_duration = play_and_measure_duration(player)
    write_wav(1.5)  # overwrite the SAME path with a longer clip
    second_duration = play_and_measure_duration(player)

    assert first_duration > 0
    assert second_duration > first_duration  # reloaded the changed file

    # The transient setSource(QUrl()) reload must not inject spurious lifecycle
    # events: exactly one read start/segment/finish per read, no double-advance.
    assert len(started) == 2
    assert len(segment_started) == 2
    assert len(finished) == 2

    player.stop()
    player.deleteLater()
    qt_app.processEvents()


def test_main_window_initializes_under_the_active_qt_platform(qt_app: QApplication, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Configuration, "USER_CONFIG_DIR_PATH", str(tmp_path / "config"))
    monkeypatch.setattr("cracker.view.speaker_config_tab.list_aws_profiles", lambda: [])
    monkeypatch.setattr("cracker.view.speaker_config_tab.load_sso_profile", lambda _profile: None)
    config = Configuration()
    config.read_config()
    speaker = MagicMock()
    speaker.VOLUMES = list(range(100))
    speaker.RATES = [80, 120, 160, 200, 240]
    player = AudioPlayer()

    with patch.object(config, "save_user_config"):
        window = MainWindow(config, speakers={"polly": Polly})
        window.speaker = speaker
        window.player = player
        window.init()

    assert window.centralWidget() is not None
    assert window.menuBar() is not None
    assert window.config_window.tabs.count() == 2
    assert window.speakerW.currentText() == "Polly"

    window.close()
    player.stop()
    window.deleteLater()
    player.deleteLater()
    qt_app.processEvents()


def test_audio_player_carries_word_marks_across_segments(qt_app: QApplication, tmp_path: Path):
    player = AudioPlayer()
    seg0 = AudioSegment(
        path=str(tmp_path / "a.mp3"),
        marks=[WordMark(0, "Hello"), WordMark(300, "world")],
    )
    seg1 = AudioSegment(path=str(tmp_path / "b.mp3"), marks=[WordMark(0, "again")])

    read_started = QSignalSpy(player.readStarted)
    segment_started = QSignalSpy(player.segmentStarted)

    player.play_segments([seg0, seg1])
    assert player.has_marks
    assert player.current_segment() == 0
    assert [mark.value for mark in player.segment_marks()[0]] == ["Hello", "world"]

    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)
    assert player.current_segment() == 1

    assert len(read_started) == 1
    assert len(segment_started) == 2  # one per segment

    player.stop()
    qt_app.processEvents()


def test_audio_player_play_files_has_no_marks(qt_app: QApplication, tmp_path: Path):
    player = AudioPlayer()
    finished = QSignalSpy(player.readFinished)

    player.play_files([str(tmp_path / "a.mp3")])
    assert player.has_marks is False

    player.stop()
    assert len(finished) == 1  # stopping mid-read emits readFinished
    qt_app.processEvents()


def test_read_along_marks_mode_tracks_playback_position(qt_app: QApplication, tmp_path: Path, monkeypatch):
    window, player = _make_main_window(tmp_path, monkeypatch)
    controller = window.read_along
    assert controller is not None
    window.set_read_source("textarea")
    window.textEdit.setPlainText("Hello world again")

    segments = [
        AudioSegment(path=str(tmp_path / "a.mp3"), marks=[WordMark(0, "Hello"), WordMark(400, "world")]),
        AudioSegment(path=str(tmp_path / "b.mp3"), marks=[WordMark(0, "again")]),
    ]
    player.play_segments(segments)  # emits readStarted -> controller begins marks mode

    assert controller._mode == "marks"
    assert controller._session is not None and controller._session.total == 3

    player.positionChanged.emit(450)  # Hello(0) and world(400) started -> "world"
    assert controller._session.index == 1
    assert window.textEdit.extraSelections()  # highlight rendered
    assert window.readProgress.value() > 0

    player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)  # advance to segment 1
    player.positionChanged.emit(10)  # "again"
    assert controller._session.index == 2

    player.stop()  # emits readFinished -> controller clears read-along
    assert window.textEdit.extraSelections() == []

    window.close()
    player.stop()
    window.deleteLater()
    player.deleteLater()
    qt_app.processEvents()


def test_read_along_estimate_paces_clipboard_by_read_text(qt_app: QApplication, tmp_path: Path, monkeypatch):
    window, player = _make_main_window(tmp_path, monkeypatch)
    controller = window.read_along
    assert controller is not None
    window.textEdit.setPlainText("one two three four five")  # 5 editor words (ignored)
    window.set_read_source("clipboard", "alpha beta gamma")  # 3 spoken words

    player.play_files([str(tmp_path / "clip.mp3")])  # no marks -> estimate mode

    assert controller._mode == "estimate"
    assert controller._session is not None and controller._session.total == 3  # from read text, not editor
    assert window.textEdit.extraSelections() == []  # clipboard reads don't highlight

    player.stop()
    window.close()
    window.deleteLater()
    player.deleteLater()
    qt_app.processEvents()


def test_clipboard_estimate_status_counts_down(qt_app: QApplication, tmp_path: Path, monkeypatch):
    window, player = _make_main_window(tmp_path, monkeypatch)
    controller = window.read_along
    assert controller is not None
    read_text = " ".join(str(number) for number in range(100))  # 100 words
    window.set_read_source("clipboard", read_text)

    player.play_files([str(tmp_path / "clip.mp3")])  # no marks -> estimate mode
    assert controller._mode == "estimate"
    assert controller._session is not None and controller._session.total == 100
    start_status = window.statusRightLabel.text()

    total_sec = 100 / (window.current_wpm() / 60.0)
    controller._elapsed = total_sec * 0.5  # simulate ~half the read elapsed
    controller._on_tick()
    mid_status = window.statusRightLabel.text()

    assert "100 words" in start_status and "100 words" in mid_status
    assert start_status != mid_status  # remaining time actually decreased

    player.stop()
    window.close()
    window.deleteLater()
    player.deleteLater()
    qt_app.processEvents()


def test_refresh_theme_icons_rebuilds_control_icons(qt_app: QApplication, tmp_path: Path, monkeypatch):
    window, player = _make_main_window(tmp_path, monkeypatch)

    window.refresh_theme_icons()  # must not raise; icons stay populated

    assert not window.read_button.icon().isNull()
    assert not window.stop_button.icon().isNull()
    assert not window.config_button.icon().isNull()

    window.close()
    player.stop()
    window.deleteLater()
    player.deleteLater()
    qt_app.processEvents()


@patch("cracker.keylogger.keyboard.Listener")
def test_global_shortcut_emits_after_full_sequence(listener):
    manager = KeyBoardManager()
    emitted = []
    manager.GlobalReadSignal.connect(lambda: emitted.append(True))
    manager.sequence = [keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.space]

    for key in manager.sequence:
        manager.on_press(key)
    manager.on_release(keyboard.Key.space)

    assert emitted == [True]
    assert manager._pressed == set()
    listener.assert_called_once()
