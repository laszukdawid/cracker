#!/usr/bin/python
import argparse
import importlib.resources
import logging
import sys
import threading

import darkdetect
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from cracker.themes import apply_theme
from cracker.utils import LoggerConfig


class ThemeBridge(QObject):
    """Marshals OS colour-scheme changes onto the GUI thread.

    ``darkdetect.listener`` emits ``theme_changed`` from a background thread;
    because the slot is a bound method of this main-thread QObject, a cross-thread
    emit is delivered via a queued connection, so palette/stylesheet/icon updates
    always run on the GUI thread.
    """

    theme_changed = pyqtSignal(object)

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._gui = None
        self.theme_changed.connect(self._apply_theme_change)

    def set_gui(self, gui):
        self._gui = gui

    def _apply_theme_change(self, theme):
        apply_theme(self._app, theme)
        if self._gui is not None:
            self._gui.refresh_theme_icons()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="cracker", description="GUI for text-to-speech")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_known_args(argv)


def main(argv=None):
    from cracker.cracker import Cracker

    args, qt_args = parse_args(argv)
    logger_config = LoggerConfig()
    if args.debug:
        logger_config.level = logging.DEBUG

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Cracker")

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    apply_theme(app, darkdetect.theme())
    theme_bridge = ThemeBridge(app)
    listener_thread = threading.Thread(target=darkdetect.listener, args=(theme_bridge.theme_changed.emit,))
    listener_thread.daemon = True
    listener_thread.start()

    cracker = Cracker(app)
    cracker.run()

    # apply_theme swaps the stylesheet; painted QIcons also need rebuilding.
    theme_bridge.set_gui(cracker.gui)

    icon_path = importlib.resources.files("cracker").joinpath("icon.png")
    icon = QIcon(str(icon_path))
    tray = QSystemTrayIcon(icon)
    tray.setIcon(icon)
    tray.setVisible(True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
