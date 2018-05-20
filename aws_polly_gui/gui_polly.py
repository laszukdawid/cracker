#!/usr/bin/python
# coding: UTF-8
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QMainWindow, QWidget
from PyQt5.QtWidgets import QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSlider, QTextEdit
from PyQt5.QtMultimedia import QMediaPlayer

from aws_polly_gui.configuration import Configuration
from aws_polly_gui.text_parser import TextParser
from aws_polly_gui.speaker.espeak import Espeak
from aws_polly_gui.speaker.polly import Polly


class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    SPEAKER = {"Polly": Polly, "Espeak": Espeak}
    _logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        self.resize(800, 250)
        self.setWindowTitle('Cracker GUI')
        self.player = QMediaPlayer()

        self.config = Configuration()
        _ = self.config.read_default_config()
        self.speaker = self.SPEAKER[self.config.speaker](self.player)
        self.textParser = TextParser()

        self.set_action()
        self.set_widgets()
        self.init_values()

        self._last_pid = None

    def set_action(self):
        _exit = QAction('Exit', self)
        _exit.setShortcut('Ctrl+Q')
        _exit.setStatusTip('Exit application')
        _exit.triggered.connect(self.close)

        _stop = QAction('Stop', self)
        _stop.setShortcut('Ctrl+Shift+S')
        _stop.setStatusTip('Stops text')
        _stop.triggered.connect(self.stop_text)

        _read = QAction('Read', self)
        _read.setShortcut('Ctrl+Shift+Space')
        _read.setStatusTip('Reads text')
        _read.triggered.connect(self.read_text)

        # TODO: This, and above, should be buttons, so that the width doesn't change
        self._toggle = QAction('Pause', self)
        self._toggle.setDisabled(True)
        self._toggle.setShortcut('Ctrl+Space')
        self._toggle.setStatusTip('Toggle read')
        self._toggle.triggered.connect(self.toggle_read)
        self.player.stateChanged.connect(self.toggle_label)

        _reduce = QAction('Reduce', self)
        _reduce.setShortcut('Ctrl+R')
        _reduce.setStatusTip('Reduces unnecessary text')
        _reduce.triggered.connect(self.reduce_text)

        _wiki = QAction('Wiki', self)
        _wiki.setShortcut('Ctrl+W')
        _wiki.setStatusTip('Reduces wiki citations')
        _wiki.triggered.connect(self.wiki_text)

        _cite = QAction('Citation', self)
        _cite.setShortcut('Ctrl+Shift+C')
        _cite.setStatusTip('Citation')
        _cite.triggered.connect(self.reduce_cite)

        # MenuBar and ToolBar
        menubar = self.menuBar()

        fileAction = menubar.addMenu('&File')
        fileAction.addAction(_exit)
        textAction = menubar.addMenu('&Text')
        textAction.addAction(_read)
        textAction.addAction(_stop)
        reduceAction = menubar.addMenu('&Reduce')
        reduceAction.addAction(_reduce)
        reduceAction.addAction(_wiki)
        reduceAction.addAction(_cite)

        toolbarExit = self.addToolBar('Exit')
        toolbarExit.addAction(_exit)
        toolbarText = self.addToolBar('Text')
        toolbarText.addAction(_read)
        toolbarText.addAction(_stop)
        toolbarText.addAction(self._toggle)
        toolbarReduce = self.addToolBar('Reduce')
        toolbarReduce.addAction(_reduce)
        toolbarReduce.addAction(_wiki)
        toolbarReduce.addAction(_cite)

    def set_widgets(self):
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        # LAYOUT
        self.layout = QVBoxLayout(self.mainWidget)
        self.menuLayout = QHBoxLayout()

        # Speaker - label and widget
        self.speakerLabel = QLabel("Speaker:")
        self.speakerLabel.setGeometry(20, 27, 80, 30)
        self.speakerW = QComboBox(self)
        self.speakerW.addItems(self.SPEAKER.keys())
        self.speakerW.setCurrentIndex(list(self.SPEAKER.keys()).index(self.config.speaker))
        self.speakerW.setGeometry(70, 27, 80, 30)
        self.speakerW.currentTextChanged.connect(self.change_speaker)
        speaker = QVBoxLayout()
        speaker.addWidget(self.speakerLabel)
        speaker.addWidget(self.speakerW)

        # Voice - label and selector
        self.speedLabel = QLabel("Speed:")
        self.speedLabel.setGeometry(220, 27, 80, 30)
        self.speedW = QSpinBox()
        self.speedW.setFocusPolicy(Qt.NoFocus)
        self.speedW.setValue(self.config.speed)
        self.speedW.setGeometry(300, 27, 50, 30)
        self.speedW.setRange(1, 5)
        self.speedW.valueChanged.connect(self.change_speed)
        speed = QVBoxLayout()
        speed.addWidget(self.speedLabel)
        speed.addWidget(self.speedW)

        # Volume - label and slider
        self.volumeLabel = QLabel("Volume:")
        self.volumeLabel.setGeometry(380, 27, 80, 30)
        self.volumeW = QSlider(Qt.Horizontal, self)  # Range: 0 -- 100
        self.volumeW.setValue(50)
        self.volumeW.setFocusPolicy(Qt.NoFocus)
        self.volumeW.setGeometry(460, 27, 100, 30)
        self.volumeW.valueChanged.connect(self.change_volume)
        volume = QVBoxLayout()
        volume.addWidget(self.volumeLabel)
        volume.addWidget(self.volumeW)

        # Language - label and selection
        self.langLabel = QLabel("Language:")
        self.langLabel.setGeometry(480, 27, 20, 20)
        self.langW = QComboBox(self)
        self.langW.addItems(self.config.languages)
        self.langW.setCurrentIndex(self.config.languages.index(self.config.language))
        self.langW.setGeometry(500, 27, 20, 20)
        self.langW.currentTextChanged.connect(self.change_language)
        lang = QVBoxLayout()
        lang.addWidget(self.langLabel)
        lang.addWidget(self.langW)

        # Voice - label and selection
        self.voiceLabel = QLabel("Voice:")
        self.voiceLabel.setGeometry(480, 27, 20, 20)
        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.config.lang_voices)
        self.voiceW.setCurrentIndex(self.config.lang_voices.index(self.config.voice))
        self.voiceW.setGeometry(500, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.change_voice)
        voice = QVBoxLayout()
        voice.addWidget(self.voiceLabel)
        voice.addWidget(self.voiceW)

        # Adding all widgets to the layout
        self.menuLayout.addLayout(speaker)
        self.menuLayout.addLayout(speed)
        self.menuLayout.addLayout(lang)
        self.menuLayout.addLayout(voice)
        self.menuLayout.addLayout(volume)
        self.layout.addLayout(self.menuLayout)

        # Notepad
        self.textEdit = QTextEdit()
        self.layout.addWidget(self.textEdit)

    def closeEvent(self, close_event):
        self.speaker.__del__()

    def init_values(self):
        self.change_volume(self.volumeW.value())
        self.change_speed(self.speedW.value())
        self.change_language(self.config.language)
        self.voice = self.config.voice

    def change_speaker(self, speaker_name):
        """Action on changing speaker.

        Important: Each speaker has its own configuration. These values should be updated on change."""
        self.speaker = self.SPEAKER[speaker_name](self.player)
        self.config.load_config(speaker_name)
        self.init_values()

    def change_volume(self, volume):
        """Volume should be on a percentage scale"""
        discrete_vol = int(volume*len(self.speaker.VOLUMES)/100)
        self.volume = self.speaker.VOLUMES[discrete_vol]

    def change_speed(self, speed):
        self.speed = speed
        self.rate = self.speaker.RATES[speed-1]

    def change_language(self, language):
        self.config.language = language
        self.voiceW.clear()
        voices = self.config.voices[language]
        self.voiceW.addItems(voices)

        voice = voices[0]
        if hasattr(self.config, 'voice') and self.config.voice in voices:
            voice = self.config.voice
            self.voiceW.setCurrentIndex(voices.index(voice))
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

    def toggle_label(self, state):
        if QMediaPlayer.PlayingState == state:
            self._toggle.setText("Pause")
            self._toggle.setDisabled(False)
        elif QMediaPlayer.StoppedState == state:
            self._toggle.setText("Pause")
            self._toggle.setDisabled(True)
        elif QMediaPlayer.PausedState == state:
            self._toggle.setText("Resume")
            self._toggle.setDisabled(False)
        else:
            self._logger.error("Unrecognisible state '%s' in MediaPlayer", state)

    def toggle_read(self):
        if self.player.state() == QMediaPlayer.PausedState:
            self.player.play()
        else:
            self.player.pause()

    def stop_text(self):
        self.speaker.stop_text()

    def read_text(self):
        """Reads out text in the text_box with selected speaker."""
        self.stop_text()
        text = self.textEdit.toPlainText()  # TODO: toHtml() gives more control
        speaker_config = self._prepare_config()
        self._last_pid = self.speaker.read_text(text, **speaker_config)

    def _prepare_config(self):
        config = dict(rate=self.rate, volume=self.volume, voice=self.voice)
        return config
