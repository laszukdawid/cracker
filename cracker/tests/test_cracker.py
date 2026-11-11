import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtMultimedia import QMediaPlayer

from cracker.config.configuration import DEFAULT_SHORTCUTS
from cracker.cracker import Cracker


def _cracker():
    cracker = object.__new__(Cracker)
    cracker.gui = MagicMock()
    cracker.key_manager = MagicMock()
    cracker._closed = False
    cracker.selection_reader = MagicMock()
    cracker.config = MagicMock(shortcuts=dict(DEFAULT_SHORTCUTS), shortcut_warning=None)
    cracker.player = MagicMock(waiting_for_segment=False)
    cracker.speaker = MagicMock(is_synthesizing=False)
    cracker.text_parser = MagicMock()
    cracker._accessibility_trusted = MagicMock(return_value=False)
    return cracker


def test_set_action_connects_citation_reducer():
    cracker = _cracker()

    cracker.set_action()

    cracker.gui.cite_action.triggered.connect.assert_called_once_with(cracker.reduce_cite)


def test_change_speaker_reuses_one_backend_in_gui():
    cracker = object.__new__(Cracker)
    cracker.player = MagicMock()
    cracker.gui = MagicMock()
    old_speaker = cracker.speaker = MagicMock()
    speaker = MagicMock()
    cracker.get_speaker = MagicMock(return_value=speaker)

    cracker.change_speaker("espeak")

    old_speaker.shutdown.assert_called_once()  # its pending synthesis must not play later
    cracker.get_speaker.assert_called_once_with("espeak", cracker.player)
    cracker.gui.change_speaker.assert_called_once_with("espeak", speaker)
    assert cracker.speaker is speaker


def test_change_speaker_saves_pending_settings_before_reloading_config():
    cracker = object.__new__(Cracker)
    cracker.player = MagicMock()
    calls = MagicMock()
    cracker.gui = calls.gui
    cracker.speaker = calls.old_speaker
    cracker.get_speaker = calls.get_speaker

    cracker.change_speaker("google")

    assert [c[0] for c in calls.mock_calls[:3]] == ["gui.flush_pending_save", "old_speaker.shutdown", "get_speaker"]


def test_set_action_starts_global_shortcuts_once_the_event_loop_runs():
    cracker = _cracker()

    with patch("cracker.cracker.QTimer.singleShot") as single_shot:
        cracker.set_action()

    cracker.key_manager.start.assert_not_called()  # the window shows first
    single_shot.assert_called_once_with(0, cracker._start_global_shortcuts)
    cracker.selection_reader.textReady.connect.assert_called_once_with(cracker._read_selection)


def test_start_global_shortcuts_listens_for_both():
    cracker = _cracker()

    cracker._start_global_shortcuts()

    cracker.key_manager.start.assert_called_once()
    args = cracker.key_manager.start.call_args.args
    assert args[:2] == (["ctrl", "shift", "space"], ["f6"])


def test_key_manager_is_created_and_connected_on_first_start():
    cracker = _cracker()
    cracker.key_manager = None
    cracker.app = None

    with patch("cracker.keylogger.KeyBoardManager") as manager_class:
        cracker._start_global_shortcuts()

    manager = manager_class.return_value
    assert cracker.key_manager is manager
    manager.GlobalReadSignal.connect.assert_called_once_with(cracker.toggle_read_text_clipboard)
    manager.SelectionReadSignal.connect.assert_called_once_with(cracker.toggle_read_selection)
    manager.start.assert_called_once()


def test_global_shortcuts_do_not_start_after_close():
    cracker = _cracker()
    cracker.key_manager = None
    cracker._make_key_manager = MagicMock()

    cracker._close()
    cracker._start_global_shortcuts()

    cracker._make_key_manager.assert_not_called()


def test_shortcut_backend_failure_is_reported_not_raised():
    cracker = _cracker()
    cracker.key_manager = None
    cracker._make_key_manager = MagicMock(side_effect=ImportError("no keyboard backend"))

    cracker._start_global_shortcuts()

    cracker.gui.show_notice.assert_called_once_with("Global shortcuts are unavailable: no keyboard backend")


def test_shortcut_start_failure_stops_the_listener():
    cracker = _cracker()
    cracker.key_manager.start.side_effect = OSError("event tap refused")

    cracker._start_global_shortcuts()

    cracker.key_manager.stop.assert_called_once()
    cracker.gui.show_notice.assert_called_once_with("Global shortcuts are unavailable: event tap refused")


def test_shortcut_failure_in_the_event_loop_keeps_the_app_running():
    code = """
import sys
from unittest.mock import MagicMock
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from cracker.cracker import Cracker

app = QApplication([])
cracker = object.__new__(Cracker)
cracker._closed = False
cracker.key_manager = None
cracker.gui = MagicMock()
cracker._make_key_manager = MagicMock(side_effect=ImportError("no keyboard backend"))
QTimer.singleShot(0, cracker._start_global_shortcuts)
QTimer.singleShot(50, lambda: app.exit(0 if cracker.gui.show_notice.called else 3))
sys.exit(app.exec())
"""
    env = {**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}
    assert subprocess.run([sys.executable, "-c", code], env=env, timeout=30).returncode == 0


def test_importing_cracker_does_not_load_pynput():
    code = "import sys, cracker.cracker; sys.exit('pynput' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_invalid_shortcut_falls_back_to_defaults():
    cracker = _cracker()
    cracker.config.shortcuts = {"read_clipboard": ["ctrl", "shift", "space"], "read_selection": ["nope"]}
    cracker.key_manager.start.side_effect = [ValueError("Unknown key 'nope'"), None]

    cracker._start_global_shortcuts()

    assert cracker.key_manager.start.call_count == 2
    assert cracker.key_manager.start.call_args.args[1] == ["f6"]
    cracker.gui.show_notice.assert_called_once()


def test_selection_shortcut_stops_playback_instead_of_reading():
    cracker = _cracker()
    cracker.player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState

    cracker.toggle_read_selection()

    cracker.speaker.stop_text.assert_called_once()
    cracker.player.stop.assert_called()
    cracker.selection_reader.request.assert_not_called()


def test_selection_shortcut_requests_selection_when_idle():
    cracker = _cracker()
    cracker.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState

    cracker.toggle_read_selection()

    cracker.selection_reader.request.assert_called_once()


def test_empty_selection_shows_notice_and_reads_nothing():
    cracker = _cracker()
    cracker._read = MagicMock()

    cracker._read_selection("   ")

    cracker.gui.show_notice.assert_called_once_with("No selected text found.")
    cracker._read.assert_not_called()


def test_selection_text_is_reduced_and_read():
    cracker = _cracker()
    cracker._read = MagicMock()
    cracker.text_parser.reduce_text.return_value = "clean text"

    cracker._read_selection("raw text [1]")

    cracker.gui.set_read_source.assert_called_once_with("clipboard", "clean text")
    cracker._read.assert_called_once_with("clean text")


def test_config_shortcut_warning_is_shown():
    cracker = _cracker()
    cracker.config.shortcut_warning = "Ignoring 'shortcuts' in settings"

    cracker._start_global_shortcuts()

    cracker.gui.show_notice.assert_called_once_with("Ignoring 'shortcuts' in settings")
    cracker.key_manager.start.assert_called_once()


def test_stop_cancels_pending_selection():
    cracker = _cracker()

    cracker.stop_text()

    cracker.selection_reader.cancel.assert_called_once()


def test_read_shortcut_stops_while_speech_is_still_being_made():
    cracker = _cracker()
    cracker.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    cracker.speaker.is_synthesizing = True

    cracker.toggle_read_selection()

    cracker.selection_reader.request.assert_not_called()
    cracker.speaker.stop_text.assert_called_once()


def test_read_shortcut_stops_while_waiting_for_the_next_chunk():
    cracker = _cracker()
    cracker.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    cracker.player.waiting_for_segment = True

    cracker.toggle_read_text_clipboard()

    cracker.selection_reader.when_idle.assert_not_called()
    cracker.speaker.stop_text.assert_called_once()


def test_clipboard_read_waits_for_selection_read():
    cracker = _cracker()
    cracker.player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState

    cracker.toggle_read_text_clipboard()

    cracker.selection_reader.cancel.assert_called_once()
    cracker.selection_reader.when_idle.assert_called_once_with(cracker._read_clipboard)


def test_closing_the_app_shuts_the_speaker_down():
    cracker = _cracker()

    cracker._close()

    cracker.speaker.shutdown.assert_called_once()


def test_pause_toggle_follows_the_players_pause_state():
    cracker = _cracker()
    cracker.player.is_paused = True
    cracker.toggle_read()
    cracker.player.play.assert_called_once()

    cracker.player.is_paused = False
    cracker.toggle_read()
    cracker.player.pause.assert_called_once()
