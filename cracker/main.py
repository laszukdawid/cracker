#!/usr/bin/python
import argparse
import importlib.resources
import logging
import sys

from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from cracker.themes import active_theme_name, apply_theme
from cracker.utils import LoggerConfig


class ThemeFollower:
    """Re-applies Cracker's palette and icons when the OS switches between light and dark.

    Qt reports the change itself (``QStyleHints.colorSchemeChanged``) on the GUI thread.
    """

    def __init__(self, app: QApplication):
        self._app = app
        self._gui = None
        hints = QGuiApplication.styleHints()
        if hints is not None:
            hints.colorSchemeChanged.connect(self._apply_theme_change)

    def set_gui(self, gui):
        self._gui = gui

    def _apply_theme_change(self, _scheme=None):
        apply_theme(self._app, active_theme_name())
        if self._gui is not None:
            self._gui.refresh_theme_icons()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="cracker", description="GUI for text-to-speech")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_known_args(argv)


def main(argv=None):
    args, qt_args = parse_args(argv)
    logger_config = LoggerConfig()
    if args.debug:
        logger_config.level = logging.DEBUG

    # Imported after the level is set: module loggers take it when they're created.
    from cracker.cracker import Cracker

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Cracker")

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    apply_theme(app, active_theme_name())
    theme_follower = ThemeFollower(app)

    cracker = Cracker(app)
    cracker.run()

    # apply_theme swaps the stylesheet; painted QIcons also need rebuilding.
    theme_follower.set_gui(cracker.gui)

    icon_path = importlib.resources.files("cracker").joinpath("icon.png")
    icon = QIcon(str(icon_path))
    tray = QSystemTrayIcon(icon)
    tray.setIcon(icon)
    tray.setVisible(True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
