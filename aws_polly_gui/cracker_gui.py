#!/usr/bin/python
# coding: UTF-8
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QMainWindow, QWidget
from PyQt5.QtWidgets import QComboBox, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSlider, QTextEdit
from PyQt5.QtMultimedia import QMediaPlayer


class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    _logger = logging.getLogger(__name__)

    def __init__(self, config, speakers):
        super().__init__()

        self.resize(800, 250)
        self.setWindowTitle('Cracker GUI')

        self.config = config

        self.speakers = speakers
        self.speaker = None
        self.player = None

    def init(self):
        self.set_action()
        self.set_widgets()
        self.init_values()

    def set_action(self):
        _exit = QAction('Exit', self)
        _exit.setShortcut('Ctrl+Q')
        _exit.setStatusTip('Exit application')
        _exit.triggered.connect(self.close)

        self.stop_action = QAction('Stop', self)
        self.stop_action.setShortcut('Ctrl+Shift+S')
        self.stop_action.setStatusTip('Stops text')

        self.read_action = QAction('Read', self)
        self.read_action.setShortcut('Ctrl+Shift+Space')
        self.read_action.setStatusTip('Reads text')

        # TODO: This, and above, should be buttons, so that the width doesn't change
        self.toggle_action = QAction('Pause', self)
        self.toggle_action.setDisabled(True)
        self.toggle_action.setShortcut('Ctrl+Space')
        self.toggle_action.setStatusTip('Toggle read')
        self.player.stateChanged.connect(self.toggle_label)

        self.reduce_action = QAction('Reduce', self)
        self.reduce_action.setShortcut('Ctrl+R')
        self.reduce_action.setStatusTip('Reduces unnecessary text')

        self.wiki_action = QAction('Wiki', self)
        self.wiki_action.setShortcut('Ctrl+W')
        self.wiki_action.setStatusTip('Reduces wiki citations')

        self.cite_action = QAction('Citation', self)
        self.cite_action.setShortcut('Ctrl+Shift+C')
        self.cite_action.setStatusTip('Citation')

        # MenuBar and ToolBar
        menubar = self.menuBar()

        fileAction = menubar.addMenu('&File')
        fileAction.addAction(_exit)
        textAction = menubar.addMenu('&Text')
        textAction.addAction(self.read_action)
        textAction.addAction(self.stop_action)
        reduceAction = menubar.addMenu('&Reduce')
        reduceAction.addAction(self.reduce_action)
        reduceAction.addAction(self.wiki_action)
        reduceAction.addAction(self.cite_action)

        toolbarExit = self.addToolBar('Exit')
        toolbarExit.addAction(_exit)
        toolbarText = self.addToolBar('Text')
        toolbarText.addAction(self.read_action)
        toolbarText.addAction(self.stop_action)
        toolbarText.addAction(self.toggle_action)
        toolbarReduce = self.addToolBar('Reduce')
        toolbarReduce.addAction(self.reduce_action)
        toolbarReduce.addAction(self.wiki_action)
        toolbarReduce.addAction(self.cite_action)

    def set_widgets(self):
        # todo: This should be a grid
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        # LAYOUT
        layout = QVBoxLayout(self.mainWidget)
        menuLayout = QHBoxLayout()

        # Speaker - label and widget
        self.speakerLabel = QLabel("Speaker:")
        self.speakerLabel.setGeometry(20, 27, 80, 30)
        self.speakerW = QComboBox(self)
        self.speakerW.addItems(self.speakers.keys())
        self.speakerW.setCurrentIndex(list(self.speakers.keys()).index(self.config.speaker))
        self.speakerW.setGeometry(70, 27, 80, 30)
        self.speakerW.currentTextChanged.connect(self.change_speaker)
        speakerBox = QVBoxLayout()
        speakerBox.addWidget(self.speakerLabel)
        speakerBox.addWidget(self.speakerW)

        # Voice - label and selector
        self.speedLabel = QLabel("Speed:")
        self.speedLabel.setGeometry(220, 27, 80, 30)
        self.speedW = QSpinBox()
        self.speedW.setFocusPolicy(Qt.NoFocus)
        self.speedW.setValue(self.config.speed)
        self.speedW.setGeometry(300, 27, 50, 30)
        self.speedW.setRange(1, 5)
        self.speedW.valueChanged.connect(self.change_speed)
        speedBox = QVBoxLayout()
        speedBox.addWidget(self.speedLabel)
        speedBox.addWidget(self.speedW)

        # Volume - label and slider
        self.volumeLabel = QLabel("Volume:")
        self.volumeLabel.setGeometry(380, 27, 80, 30)
        self.volumeW = QSlider(Qt.Horizontal, self)  # Range: 0 -- 100
        self.volumeW.setValue(50)
        self.volumeW.setFocusPolicy(Qt.NoFocus)
        self.volumeW.setGeometry(460, 27, 100, 30)
        self.volumeW.valueChanged.connect(self.change_volume)
        volumeBox = QVBoxLayout()
        volumeBox.addWidget(self.volumeLabel)
        volumeBox.addWidget(self.volumeW)

        # Language - label and selection
        langLabel = QLabel("Language:")
        langLabel.setGeometry(480, 27, 20, 20)
        langW = QComboBox(self)
        langW.addItems(self.config.languages)
        langW.setCurrentIndex(self.config.languages.index(self.config.language))
        langW.setGeometry(500, 27, 20, 20)
        langW.currentTextChanged.connect(self.change_language)
        langBox = QVBoxLayout()
        langBox.addWidget(langLabel)
        langBox.addWidget(langW)

        # Voice - label and selection
        voiceLabel = QLabel("Voice:")
        voiceLabel.setGeometry(480, 27, 20, 20)
        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.config.lang_voices)
        self.voiceW.setCurrentIndex(self.config.lang_voices.index(self.config.voice))
        self.voiceW.setGeometry(500, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.change_voice)
        voiceBox = QVBoxLayout()
        voiceBox.addWidget(voiceLabel)
        voiceBox.addWidget(self.voiceW)

        # Adding all widgets to the layout
        menuLayout.addLayout(speakerBox)
        menuLayout.addLayout(speedBox)
        menuLayout.addLayout(langBox)
        menuLayout.addLayout(voiceBox)
        menuLayout.addLayout(volumeBox)
        layout.addLayout(menuLayout)

        # Notepad
        self.textEdit = QTextEdit()
        layout.addWidget(self.textEdit)

    def init_values(self):
        self.change_volume(self.volumeW.value())
        self.change_speed(self.speedW.value())
        self.change_language(self.config.language)

    def closeEvent(self, close_event):
        self.speaker.__del__()

    def change_speaker(self, speaker_name):
        """Action on changing speaker.

        Important: Each speaker has its own configuration. These values should be updated on change."""
        self.speaker = self.speakers[speaker_name](self.player)
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
        voices = self.config.voices[language]
        self.voiceW.clear()
        self.voiceW.addItems(voices)
        self.change_voice(voices[0])

    def change_voice(self, voice):
        self.config.voice = voice

    def toggle_label(self, state):
        if QMediaPlayer.PlayingState == state:
            self.toggle_action.setText("Pause")
            self.toggle_action.setDisabled(False)
        elif QMediaPlayer.StoppedState == state:
            self.toggle_action.setText("Pause")
            self.toggle_action.setDisabled(True)
        elif QMediaPlayer.PausedState == state:
            self.toggle_action.setText("Resume")
            self.toggle_action.setDisabled(False)
        else:
            self._logger.error("Unrecognisible state '%s' in MediaPlayer", state)
