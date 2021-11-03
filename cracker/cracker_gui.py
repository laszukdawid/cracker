import logging
from typing import Dict, Optional, Type, Union

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import (QAction, QComboBox, QGridLayout, QLabel, QMainWindow, QSlider, QSpinBox, QTextEdit,
                             QVBoxLayout, QWidget)

from cracker.configuration import Configuration
from cracker.speaker.abstract_speaker import AbstractSpeaker
from cracker.speaker.espeak import Espeak
from cracker.speaker.polly import Polly
from cracker.view.config_window import ConfigWindow

SpeakersType = Dict[str, Union[Type[Espeak], Type[Polly]]]


class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    _logger = logging.getLogger(__name__)
    closeAppEvent = pyqtSignal()

    def __init__(self, config: Configuration, speakers: SpeakersType):
        super().__init__()

        self.resize(800, 250)
        self.setWindowTitle('Cracker GUI')

        self.config = config

        self.speakers = speakers
        self.speaker: Optional[AbstractSpeaker] = None
        self.player: Optional[QMediaPlayer] = None

        self.config_window = ConfigWindow()

    def init(self):
        self.set_action()
        self.set_widgets()
        self.init_values()
        self.config_window.init(regex_file_path=self.config.parser_config)

    def set_action(self):
        assert self.player, "Cannot set actions on non-defined Player"
        _exit = QAction('Exit', self)
        _exit.setShortcut('Ctrl+Q')
        _exit.setStatusTip('Exit application')
        _exit.triggered.connect(self.closeEvent)

        _save = QAction('Save config', self)
        _save.setShortcut('Ctrl+S')
        _save.setStatusTip('Save configure')
        _save.triggered.connect(self.save_config)

        self.stop_action = QAction('Stop', self)
        self.stop_action.setShortcut('Ctrl+Shift+S')
        self.stop_action.setStatusTip('Stops text')

        self.read_action = QAction('Read', self)
        self.read_action.setShortcut('Ctrl+Shift+R')
        self.read_action.setStatusTip('Reduces provided text')

        self.clipboard_read_action = QAction('Read (clipboard)', self)
        self.clipboard_read_action.setShortcut('Ctrl+Shift+Space')
        self.clipboard_read_action.setStatusTip('Reads text from clipboard')

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
        self.wiki_action.setShortcut('Ctrl+Shift+W')
        self.wiki_action.setStatusTip('Reduces wiki citations')

        self.cite_action = QAction('Citation', self)
        self.cite_action.setShortcut('Ctrl+Shift+C')
        self.cite_action.setStatusTip('Citation')

        self.toggle_config_window = QAction('Config', self)
        self.toggle_config_window.setStatusTip('Opens configuration')
        self.toggle_config_window.triggered.connect(self.config_window.show)

        # MenuBar and ToolBar
        menubar = self.menuBar()

        fileAction = menubar.addMenu('&File')
        fileAction.addAction(_save)
        fileAction.addAction(_exit)
        textAction = menubar.addMenu('&Text')
        textAction.addAction(self.read_action)
        textAction.addAction(self.clipboard_read_action)
        textAction.addAction(self.stop_action)
        textAction.addAction(self.toggle_action)
        reduceAction = menubar.addMenu('&Reduce')
        reduceAction.addAction(self.reduce_action)
        reduceAction.addAction(self.wiki_action)
        reduceAction.addAction(self.cite_action)

        # toolbarExit = self.addToolBar('Exit')
        # toolbarExit.addAction(_exit)
        toolbarText = self.addToolBar('Text')
        toolbarText.addAction(self.read_action)
        toolbarText.addAction(self.clipboard_read_action)
        toolbarText.addAction(self.stop_action)
        toolbarText.addAction(self.toggle_action)
        toolbarReduce = self.addToolBar('Reduce')
        toolbarReduce.addAction(self.reduce_action)
        toolbarReduce.addAction(self.wiki_action)
        toolbarReduce.addAction(self.cite_action)

        toolbarConfig = self.addToolBar('Config')
        toolbarConfig.addAction(self.toggle_config_window)

    def set_widgets(self):
        # todo: This should be a grid
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        # LAYOUT
        layout = QVBoxLayout(self.mainWidget)
        menuLayout = QGridLayout()

        # Speaker - label and widget
        assert self.config.speaker, "Speaker needs to be defined"

        self.speakerLabel = QLabel("Speaker:")
        self.speakerW = QComboBox(self)
        self.speakerW.addItems(self.speakers.keys())
        self.speakerW.setCurrentIndex(list(self.speakers.keys()).index(self.config.speaker))
        self.speakerW.currentTextChanged.connect(self.change_speaker)
        menuLayout.addWidget(self.speakerLabel, 0, 0)
        menuLayout.addWidget(self.speakerW, 1, 0)

        # Voice - label and selector
        self.speedLabel = QLabel("Speed:")
        self.speedW = QSpinBox()
        self.speedW.setValue(self.config.speed)
        self.speedW.setRange(1, 5)
        self.speedW.valueChanged.connect(self.change_speed)
        menuLayout.addWidget(self.speedLabel, 0, 3)
        menuLayout.addWidget(self.speedW, 1, 3)

        # Volume - label and slider
        self.volumeLabel = QLabel("Volume:")
        self.volumeW = QSlider(Qt.Horizontal, self)  # Range: 0 -- 100
        self.volumeW.setValue(50)
        self.volumeW.valueChanged.connect(self.change_volume)
        menuLayout.addWidget(self.volumeLabel, 0, 4)
        menuLayout.addWidget(self.volumeW, 1, 4)

        # Language - label and selection
        langLabel = QLabel("Language:")
        langW = QComboBox(self)
        langW.addItems(self.config.languages)
        langW.setCurrentIndex(self.config.languages.index(self.config.language))
        langW.currentTextChanged.connect(self.change_language)
        menuLayout.addWidget(langLabel, 0, 1)
        menuLayout.addWidget(langW, 1, 1)

        # Voice - label and selection
        voiceLabel = QLabel("Voice:")
        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.config.lang_voices)
        self.voiceW.setCurrentIndex(self.config.lang_voices.index(self.config.voice))
        self.voiceW.setGeometry(500, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.change_voice)
        menuLayout.addWidget(voiceLabel, 0, 2)
        menuLayout.addWidget(self.voiceW, 1, 2)

        # Spacing between all widgets and tighten layout (stretch last column)
        menuLayout.setSpacing(10)
        menuLayout.setColumnStretch(99, 1)
        layout.addLayout(menuLayout)

        # Notepad
        self.textEdit = QTextEdit()
        layout.addWidget(self.textEdit)

    def init_values(self):
        self.change_volume(self.volumeW.value())
        self.change_speed(self.speedW.value())
        self.change_language(self.config.language)

    def closeEvent(self, close_event):
        """Triggers CloseEvent and handles closing gracefully"""
        self.closeAppEvent.emit()
        del self.speaker
        self.close()

    def save_config(self):
        self._logger.info("Saving user config")
        self.config.save_user_config()

    def change_speaker(self, speaker_name: str):
        """Action on changing speaker.

        Important: Each speaker has its own configuration.
        These values should be updated on change.
        """
        self.speaker = self.speakers[speaker_name](self.player)
        self.config.speaker = speaker_name
        self.config.load_config(speaker_name)
        self.init_values()

    def change_volume(self, volume):
        """Volume should be on a percentage scale"""
        assert self.speaker, "Speaker doesn't exist. Can't change volume."
        discrete_vol = int(volume * len(self.speaker.VOLUMES) / 100)
        self.volume = self.speaker.VOLUMES[discrete_vol]

    def change_speed(self, speed):
        assert self.speaker, "Speaker doesn't exist. Can't change speed."
        self.config.speed = speed
        self.rate = self.speaker.RATES[speed - 1]

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
            self.stop_action.setDisabled(False)
            self.read_action.setDisabled(True)
            self.clipboard_read_action.setDisabled(True)
        elif QMediaPlayer.StoppedState == state:
            self.toggle_action.setText("Pause")
            self.toggle_action.setDisabled(True)
            self.stop_action.setDisabled(True)
            self.read_action.setDisabled(False)
            self.clipboard_read_action.setDisabled(False)
        elif QMediaPlayer.PausedState == state:
            self.toggle_action.setText("Resume")
            self.stop_action.setDisabled(False)
            self.toggle_action.setDisabled(False)
        else:
            self._logger.error("Unrecognisible state '%s' in MediaPlayer", state)
