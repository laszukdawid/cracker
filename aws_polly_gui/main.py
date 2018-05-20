#!/usr/bin/python
# coding: UTF-8
import sys

from PyQt5.QtWidgets import QApplication
from aws_polly_gui.cracker import Cracker

if __name__ == "__main__":
    app = QApplication(sys.argv)
    cracker = Cracker()
    cracker.run()
    sys.exit(app.exec_())
