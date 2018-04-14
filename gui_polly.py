#!/usr/bin/python
# coding: UTF-8
import sys, os, re
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QAction, QComboBox
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QSlider, QTextEdit

from PyQt5 import QtMultimedia

import boto3

class SSML:
    """Converts text to annotated SSML form."""

    def __init__(self, text=None, rate=None, volume=None):
        self._rate = rate
        self._volume = volume
        if text is not None:
            self.text(text)

    def text(self, text):
        self._text = text
        self.ssml = text
        if self._rate is not None or self._volume is not None:
            _prosody = ["prosody"]
            if self._rate is not None:
                _prosody.append('rate="{rate}"'.format(rate=self._rate))
            if self._volume is not None:
                _prosody.append('volume="{volume}"'.format(volume=self._volume))
            prosody = "<" + ' '.join(_prosody) + ">"
            self.ssml = prosody + self.ssml + "</prosody>"

    def __str__(self):
        return "<speak>{ssml}</speak>".format(ssml=self.ssml)


class MainWindow(QMainWindow):
    """Main GUI for Polly text-to-speech."""

    default_voice = "Joanna"

    ENGLISH_VOICES = ["Sali", "Kimberly", "Kendra", "Joanna", "Ivy", "Matthew", "Justin", "Joey"]
    RATES = ["x-slow", "slow", "medium", "fast", "x-fast"]
    VOLUMES = ["x-soft", "soft", "medium", "loud", "x-loud"]


    def __init__(self):
        super().__init__()

        self.resize(600, 250)
        self.setWindowTitle('Simple GUI')
        self.setMinimumSize(QtCore.QSize(500, 150))
        self.setMaximumSize(QtCore.QSize(700, 500))

        self.setAction()
        self.setWidgets()
        self.initValues()

        self.initPolly()

    def initPolly(self):
        self.client = boto3.client('polly')
        self.speech = dict(
            OutputFormat="mp3",
            VoiceId=self.default_voice,
            TextType="ssml",
            )

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

        self.voiceLabel = QLabel("Voice:")
        self.voiceLabel.setGeometry(380, 27, 20, 20)

        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.ENGLISH_VOICES)
        self.voiceW.setCurrentIndex(self.ENGLISH_VOICES.index(self.default_voice))
        self.voiceW.setGeometry(400, 27, 20, 20)
        self.voiceW.currentTextChanged.connect(self.changeVoice)
        #self.connect(self.voiceW, QtCore.SIGNAL('valueChanged(int)'), self.changeVoice)

        self.menuLayout.addWidget(self.speedLabel)
        self.menuLayout.addWidget(self.speedW)
        self.menuLayout.addWidget(self.volumeLabel)
        self.menuLayout.addWidget(self.volumeW)
        self.menuLayout.addWidget(self.voiceLabel)
        self.menuLayout.addWidget(self.voiceW)

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

    def changeVoice(self, voice):
        self.voice = voice
        self.speech["VoiceId"] = voice

    def reduceCite(self):
        """Removes citations from pasted text."""
        text = self.textEdit.toPlainText()
        text = re.sub(r'\w+ and \w+, \d{4}(;?)', '', text)
        text = re.sub(r'\w+ et al., \d\{4}(;?)', '', text)
        text = re.sub(r'\w+, \d{4}(;?)', '', text)
        text = re.sub(r'\(;[^\)]*\)', '', text)
        text = re.sub(r'\(( *)\)', '', text)
        self.textEdit.setText(text)

    def reduceText(self):
        """Simplify text to strings only."""
        text = self.textEdit.toPlainText()
        text = re.sub(r'-\n', '', text, re.U)
        text = re.sub(r'- ', '', text, re.U)
        text = re.sub(r"'", '', text)
        text = re.sub(r'\t', ' ', text)
        text = re.sub(r'\n', ' ', text)
        self.textEdit.setText(text)

    def wikiText(self):
        """Convert direct copy from Wikipedia into human-readable form."""
        print('wiki pressed')

        text = str(self.textEdit.toPlainText())
        text = re.sub(r'\[+[0-9]+\]', '', text)
        text = text.replace("[clarification needed]", '')
        text = text.replace("[citation needed]", '')

        self.textEdit.setText(text)

    def readText(self):
        """Reads out text."""
        text = self.textEdit.toPlainText()
        text = text.translate(dict.fromkeys(range(8)))
        text = re.sub(r'\n', ' ', text)
        text = re.sub(r'&', 'and', text)

        ssml = SSML(text, rate=self.rate, volume=self.volume_text)
        self.speech["Text"] = str(ssml)
        response = self.client.synthesize_speech(**self.speech)
        filepath = self.saveMp3(response)
        self.playFile(filepath)

    def saveMp3(self, response):
        """Stores downloaded response as an mp3."""
        mp3 = response["AudioStream"].read()
        filename = "tmp.mp3"
        with open(filename, 'wb') as tmp_file:
            tmp_file.write(mp3)
        return filename

    def playFile(self, filepath):
        """Plays mp3 file using UNIX cmd."""
        os.system("mpg123 "+filepath)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
