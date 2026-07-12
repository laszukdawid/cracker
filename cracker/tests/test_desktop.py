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
from cracker.speaker.polly import Polly


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
