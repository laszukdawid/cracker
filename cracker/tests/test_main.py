from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from cracker.main import parse_args
from cracker.themes import apply_theme


def test_parse_args_enables_debug_and_preserves_qt_arguments():
    args, qt_args = parse_args(["--debug", "--platform", "offscreen"])

    assert args.debug is True
    assert qt_args == ["--platform", "offscreen"]


def test_parse_args_defaults_to_info_mode():
    args, qt_args = parse_args([])

    assert args.debug is False
    assert qt_args == []


def test_dark_theme_applies_an_owned_qt_palette(qt_app: QApplication):
    apply_theme(qt_app, "dark")

    assert qt_app.palette().color(QPalette.ColorRole.Window).getRgb()[:3] == (45, 45, 45)
