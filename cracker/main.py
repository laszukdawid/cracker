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
    theme_changed = pyqtSignal(object)


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
    theme_bridge = ThemeBridge()
    theme_bridge.theme_changed.connect(lambda theme: apply_theme(app, theme))
    t = threading.Thread(target=darkdetect.listener, args=(theme_bridge.theme_changed.emit,))
    t.daemon = True
    t.start()

    cracker = Cracker(app)
    cracker.run()

    icon_path = importlib.resources.files("cracker").joinpath("icon.png")
    icon = QIcon(str(icon_path))
    tray = QSystemTrayIcon(icon)
    tray.setIcon(icon)
    tray.setVisible(True)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
