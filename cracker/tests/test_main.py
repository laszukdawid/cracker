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

    # Dark window background comes from the DARK token set (#1b1b1f).
    assert qt_app.palette().color(QPalette.ColorRole.Window).getRgb()[:3] == (27, 27, 31)


def test_get_logger_prints_each_line_once():

    from cracker.utils import get_logger

    first = get_logger("cracker.tests.once")
    second = get_logger("cracker.tests.once")

    assert first is second
    assert len(first.handlers) == 1
    assert first.propagate is False


def test_singleton_does_not_install_a_root_handler():
    import logging

    from cracker.utils import Singleton

    class Thing(Singleton):
        pass

    before = list(logging.getLogger().handlers)
    Thing()

    assert logging.getLogger().handlers == before
