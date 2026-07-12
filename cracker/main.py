#!/usr/bin/python
import argparse
import importlib.resources
import logging
import sys
import threading

import darkdetect
from PyQt5.QtCore import QFile, Qt, QTextStream
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

import cracker.themes
from cracker.utils import LoggerConfig


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

    def toggle_palette(theme: str | None):
        theme = theme or "light"
        if theme.lower() == "dark":
            file = QFile(":/dark/stylesheet.qss")
        else:
            file = QFile(":/light/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())

    toggle_palette(darkdetect.theme())
    t = threading.Thread(target=darkdetect.listener, args=(toggle_palette,))
    t.daemon = True
    t.start()

    cracker = Cracker(app)
    cracker.run()

    icon_path = importlib.resources.files("cracker").joinpath("icon.png")
    icon = QIcon(str(icon_path))
    tray = QSystemTrayIcon(icon)
    tray.setIcon(icon)
    tray.setVisible(True)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
