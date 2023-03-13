#!/usr/bin/python
import sys
import threading

import darkdetect
from PyQt5.QtCore import QFile, Qt, QTextStream
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

import cracker.themes
from cracker.cracker import Cracker


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Cracker")

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    def toggle_pallet(theme: str):
        if theme.lower() == "dark":
            file = QFile(":/dark/stylesheet.qss")
        else:
            file = QFile(":/light/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())

    toggle_pallet(darkdetect.theme())
    t = threading.Thread(target=darkdetect.listener, args=(toggle_pallet,))
    t.daemon = True
    t.start()

    cracker = Cracker(app)
    cracker.run()

    icon = QIcon("icon.png")
    tray = QSystemTrayIcon(icon)
    tray.setIcon(icon)
    tray.setVisible(True)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
