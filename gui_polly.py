#!/usr/bin/python
# coding: UTF-8
import json
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QAction
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSlider, QTextEdit, QComboBox

from text_parser import TextParser
from speaker.polly import Polly
from speaker.espeak import Espeak

class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    language_file = "voices.json"
    default_voice = "Joanna"
    default_language = "English"

    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]

    def __init__(self):
        super().__init__()

        self.resize(600, 250)
        self.setWindowTitle('Simple GUI')
        self.setMinimumSize(QtCore.QSize(500, 150))
        self.setMaximumSize(QtCore.QSize(700, 500))

        self.loadLanguages()
        self.setAction()
        self.setWidgets()
        self.initValues()

        self.textParser = TextParser()
        self.speaker = Polly()
        # TODO: Allow to select speaker
        #self.speaker = Espeak()

    def loadLanguages(self):
        """Load JSON config with available languages and voices."""
        with open(self.language_file) as json_file:
            lang_map = json.loads(json_file.read())
        self.voices = lang_map["Languages"]
        self.languages = list(self.voices.keys())
        self.lang_voices = self.voices[self.default_language]

    def setAction(self):
        _exit = QAction('Exit', self)
        _exit.setShortcut('Ctrl+Q')
        _exit.setStatusTip('Exit application')
        _exit.triggered.connect(self.close)

        _read = QAction('Read', self)
        _read.setShortcut('Ctrl+Shift+Space')
        _read.setStatusTip('Reads text')
        _read.triggered.connect(self.readText)

        _reduce = QAction('Reduce', self)
        _reduce.setShortcut('Ctrl+R')
        _reduce.setStatusTip('Reduces unnecessary text')
        _reduce.triggered.connect(self.reduceText)

        _wiki = QAction('Wiki', self)
        _wiki.setShortcut('Ctrl+W')
        _wiki.setStatusTip('Reduces wiki citations')
        _wiki.triggered.connect(self.wikiText)

        _paper = QAction('Paper', self)
        _paper.setShortcut('Ctrl+P')
        _paper.setStatusTip('Paper')
        _paper.triggered.connect(self.reduceCite)

        # MenuBar and ToolBar
        menubar = self.menuBar()

        fileAction = menubar.addMenu('&File')
        fileAction.addAction(_exit)
        readAction = menubar.addMenu('&Read')
        readAction.addAction(_read)
        reduceAction = menubar.addMenu('&Reduce')
        reduceAction.addAction(_reduce)
        wikiAction = menubar.addMenu('&Wiki')
        wikiAction.addAction(_wiki)
        paperAction = menubar.addMenu('&Paper')
        paperAction.addAction(_paper)

        toolbarExit = self.addToolBar('Exit')
        toolbarExit.addAction(_exit)
        toolbarRead = self.addToolBar('Read')
        toolbarRead.addAction(_read)
        toolbarReduce = self.addToolBar('Reduce')
        toolbarReduce.addAction(_reduce)
        toolbarWiki = self.addToolBar('Wiki')
        toolbarWiki.addAction(_wiki)
        toolbarPaper = self.addToolBar('Paper')
        toolbarPaper.addAction(_paper)

    def setWidgets(self):
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        # LAYOUT
        self.layout = QVBoxLayout(self.mainWidget)
        self.menuLayout = QHBoxLayout()

        # Voice speed label widget
        self.speedLabel = QLabel("Speed:")
        self.speedLabel.setGeometry(120, 27, 80, 30)

        # Voice Speed Widget
        self.speedW = QSpinBox()
        self.speedW.setFocusPolicy(QtCore.Qt.NoFocus)
        self.speedW.setValue(3)
        self.speedW.setGeometry(200, 27, 50, 30)
        self.speedW.setRange(1, 5)
        self.speedW.valueChanged.connect(self.changeSpeed)

        # Voice volume label widget
        self.volumeLabel = QLabel("Volume:")
        self.volumeLabel.setGeometry(280, 27, 80, 30)

        # Voice volume widget
        self.volumeW = QSlider(QtCore.Qt.Horizontal, self)
        self.volumeW.setValue(50)
        self.volumeW.setFocusPolicy(QtCore.Qt.NoFocus)
        self.volumeW.setGeometry(360, 27, 100, 30)
        self.volumeW.valueChanged.connect(self.changeVolume)

        # Voice language label widget
        self.langLabel = QLabel("Language:")
        self.langLabel.setGeometry(380, 27, 20, 20)

        # Voice language widget
        self.langW = QComboBox(self)
        self.langW.addItems(self.languages)
        self.langW.setCurrentIndex(self.languages.index(self.default_language))
        self.langW.setGeometry(400, 27, 20, 20)
        self.langW.currentTextChanged.connect(self.changeLanguage)

        # Voice id label widget
        self.voiceLabel = QLabel("Voice:")
        self.voiceLabel.setGeometry(380, 27, 20, 20)

        # Voice id widget
        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.lang_voices)
        self.voiceW.setCurrentIndex(self.lang_voices.index(self.default_voice))
        self.voiceW.setGeometry(400, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.changeVoice)

        # Adding all widgets to the layout
        self.menuLayout.addWidget(self.speedLabel)
        self.menuLayout.addWidget(self.speedW)
        self.menuLayout.addWidget(self.langLabel)
        self.menuLayout.addWidget(self.langW)
        self.menuLayout.addWidget(self.voiceLabel)
        self.menuLayout.addWidget(self.voiceW)
        self.menuLayout.addWidget(self.volumeLabel)
        self.menuLayout.addWidget(self.volumeW)

        self.layout.addLayout(self.menuLayout)

        # Notepad
        self.textEdit = QTextEdit()
        self.layout.addWidget(self.textEdit)

    def initValues(self):
        self.volume = self.changeVolume(self.volumeW.value())
        self.speed = self.changeSpeed(self.speedW.value())
        self.voice = self.default_voice

    def changeVolume(self, volume):
        discrete_vol = int(volume*len(self.VOLUMES)/100)
        self.volume_text = self.VOLUMES[discrete_vol]

    def changeSpeed(self, speed):
        self.speed = speed
        self.rate = self.RATES[speed-1]

    def changeLanguage(self, language):
        self.language = language
        voices = self.voices[language]
        self.voiceW.clear()
        self.voiceW.addItems(voices)

        voice = voices[0]
        if self.default_voice in voices:
            voice = self.default_voice
            self.voiceW.setCurrentIndex(voices.index(self.default_voice))
        self.voice = voice

    def changeVoice(self, voice):
        self.voice = voice

    def reduceText(self):
        text = self.textEdit.toPlainText()
        new_text = self.textParser.reduceText(text)
        self.textEdit.setText(text)

    def reduceCite(self):
        text = self.textEdit.toPlainText()
        new_text = self.textParser.reduceCite(text)
        self.textEdit.setText(text)

    def readText(self):
        text = self.textEdit.toPlainText()
        self.speaker.read_text(text, self.voice, self.rate, self.volume_text)

    def wikiText(self):
        text = self.textEdit.toPlainText()
        text = self.textParser.wikiText(text)
        self.textEdit.setText(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

