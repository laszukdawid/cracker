#!/usr/bin/python
# coding: UTF-8
import json
import os
import signal

from PyQt5 import QtCore
from PyQt5.QtWidgets import QAction, QMainWindow, QWidget
from PyQt5.QtWidgets import QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSlider, QTextEdit

from aws_polly_gui.text_parser import TextParser
from aws_polly_gui.speaker.espeak import Espeak
from aws_polly_gui.speaker.polly import Polly


class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    language_file = "voices.json"
    default_voice = "Joanna"
    default_language = "English"
    default_speaker = "Polly"

    SPEAKER = {"Polly": Polly, "Espeak": Espeak}

    def __init__(self):
        super().__init__()

        self.resize(800, 250)
        self.setWindowTitle('Simple GUI')
        self.setMinimumSize(QtCore.QSize(700, 150))
        self.setMaximumSize(QtCore.QSize(1000, 500))

        self.speaker = self.SPEAKER[self.default_speaker]()
        self.textParser = TextParser()

        self.load_languages()
        self.set_action()
        self.set_widgets()
        self.init_values()

        self._last_pid = None

    def load_languages(self):
        """Load JSON config with available languages and voices."""
        with open(self.language_file) as json_file:
            lang_map = json.loads(json_file.read())
        self.voices = lang_map["Languages"]
        self.languages = list(self.voices.keys())
        self.lang_voices = self.voices[self.default_language]

    def set_action(self):
        _exit = QAction('Exit', self)
        _exit.setShortcut('Ctrl+Q')
        _exit.setStatusTip('Exit application')
        _exit.triggered.connect(self.close)

        _read = QAction('Read', self)
        _read.setShortcut('Ctrl+Shift+Space')
        _read.setStatusTip('Reads text')
        _read.triggered.connect(self.read_text)

        _reduce = QAction('Reduce', self)
        _reduce.setShortcut('Ctrl+R')
        _reduce.setStatusTip('Reduces unnecessary text')
        _reduce.triggered.connect(self.reduce_text)

        _wiki = QAction('Wiki', self)
        _wiki.setShortcut('Ctrl+W')
        _wiki.setStatusTip('Reduces wiki citations')
        _wiki.triggered.connect(self.wiki_text)

        _paper = QAction('Paper', self)
        _paper.setShortcut('Ctrl+P')
        _paper.setStatusTip('Paper')
        _paper.triggered.connect(self.reduce_cite)

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

    def set_widgets(self):
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        # LAYOUT
        self.layout = QVBoxLayout(self.mainWidget)
        self.menuLayout = QHBoxLayout()

        # Speaker label widget
        self.speakerLabel = QLabel("Speaker:")
        self.speakerLabel.setGeometry(20, 27, 80, 30)

        # Speakers Widget
        self.speakerW = QComboBox(self)
        self.speakerW.addItems(self.SPEAKER.keys())
        self.speakerW.setCurrentIndex(list(self.SPEAKER.keys()).index(self.default_speaker))
        self.speakerW.setGeometry(70, 27, 80, 30)
        self.speakerW.currentTextChanged.connect(self.change_speaker)

        # Voice speed label widget
        self.speedLabel = QLabel("Speed:")
        self.speedLabel.setGeometry(220, 27, 80, 30)

        # Voice Speed Widget
        self.speedW = QSpinBox()
        self.speedW.setFocusPolicy(QtCore.Qt.NoFocus)
        self.speedW.setValue(3)
        self.speedW.setGeometry(300, 27, 50, 30)
        self.speedW.setRange(1, 5)
        self.speedW.valueChanged.connect(self.change_speed)

        # Voice volume label widget
        self.volumeLabel = QLabel("Volume:")
        self.volumeLabel.setGeometry(380, 27, 80, 30)

        # Voice volume widget
        self.volumeW = QSlider(QtCore.Qt.Horizontal, self)  # Range: 0 -- 100
        self.volumeW.setValue(50)
        self.volumeW.setFocusPolicy(QtCore.Qt.NoFocus)
        self.volumeW.setGeometry(460, 27, 100, 30)
        self.volumeW.valueChanged.connect(self.change_volume)

        # Voice language label widget
        self.langLabel = QLabel("Language:")
        self.langLabel.setGeometry(480, 27, 20, 20)

        # Voice language widget
        self.langW = QComboBox(self)
        self.langW.addItems(self.languages)
        self.langW.setCurrentIndex(self.languages.index(self.default_language))
        self.langW.setGeometry(500, 27, 20, 20)
        self.langW.currentTextChanged.connect(self.change_language)

        # Voice id label widget
        self.voiceLabel = QLabel("Voice:")
        self.voiceLabel.setGeometry(480, 27, 20, 20)

        # Voice id widget
        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.lang_voices)
        self.voiceW.setCurrentIndex(self.lang_voices.index(self.default_voice))
        self.voiceW.setGeometry(500, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.change_voice)

        # Adding all widgets to the layout
        self.menuLayout.addWidget(self.speakerLabel)
        self.menuLayout.addWidget(self.speakerW)
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

    def closeEvent(self, close_event):
        self.speaker.__del__()
        self.stop_process(self._last_pid)

    def init_values(self):
        self.change_volume(self.volumeW.value())
        self.change_speed(self.speedW.value())
        self.voice = self.default_voice

    def change_speaker(self, speaker_name):
        """Action on changing speaker.

        Important: Each speaker has its own configuration. These values should be updated on change."""
        self.speaker = self.SPEAKER[speaker_name]()
        self.init_values()

        # Currently only Polly has different voices
        if speaker_name == 'Polly':
            self.voiceLabel.show()
            self.voiceW.show()
        else:
            self.voiceLabel.hide()
            self.voiceW.hide()

    def change_volume(self, volume):
        """Volume should be on a percentage scale"""
        discrete_vol = int(volume*len(self.speaker.VOLUMES)/100)
        self.volume = self.speaker.VOLUMES[discrete_vol]

    def change_speed(self, speed):
        self.speed = speed
        self.rate = self.speaker.RATES[speed-1]

    def change_language(self, language):
        self.language = language
        voices = self.voices[language]
        self.voiceW.clear()
        self.voiceW.addItems(voices)

        voice = voices[0]
        if self.default_voice in voices:
            voice = self.default_voice
            self.voiceW.setCurrentIndex(voices.index(self.default_voice))
        self.voice = voice

    def change_voice(self, voice):
        self.voice = voice

    def reduce_text(self):
        text = self.textEdit.toPlainText()
        new_text = self.textParser.reduce_text(text)
        self.textEdit.setText(new_text)

    def reduce_cite(self):
        text = self.textEdit.toPlainText()
        new_text = self.textParser.reduce_cite(text)
        self.textEdit.setText(new_text)

    def wiki_text(self):
        """Sets the text box with wikipedia specific cleaned text.
        Example of this is removing `citation needed` and other references.
        """
        text = self.textEdit.toPlainText()
        text = self.textParser.wiki_text(text)
        self.textEdit.setText(text)

    @staticmethod
    def stop_process(pid):
        os.kill(pid, signal.SIGTERM)

    def read_text(self):
        """Reads out text in the text_box with selected speaker."""
        if self._last_pid is not None:
            self.stop_process(self._last_pid)
        text = self.textEdit.toPlainText()  # TODO: toHtml() gives more control
        speaker_config = self._prepare_config()
        self._last_pid = self.speaker.read_text(text, **speaker_config)

    def _prepare_config(self):
        config = dict( rate=self.rate, volume=self.volume)
        if self.speaker.__class__.__name__ == "Polly":
            config['voiceid'] = self.voice
        return config
