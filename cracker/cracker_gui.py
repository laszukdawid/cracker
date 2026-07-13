from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QIcon, QTextCharFormat, QTextCursor
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QSlider,
    QSpinBox,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cracker.audio_player import AudioPlayer
from cracker.config import Configuration
from cracker.read_along_controller import ReadAlongController
from cracker.speaker.abstract_speaker import AbstractSpeaker
from cracker.themes import active_tokens
from cracker.utils import get_logger
from cracker.view.config_window import ConfigWindow
from cracker.view.icons import render_icon

SpeakersType = dict[str, type[AbstractSpeaker]]

# Estimated words-per-minute per speed step (1..5), used to pace the read-along
# highlight when the speaker exposes no word marks.
READ_WPM = [110, 140, 170, 200, 230]


class MainWindow(QMainWindow):
    """Main GUI for text-to-speech, laid out as a compact command bar.

    Read-along behaviour lives in :class:`ReadAlongController`; this window only
    renders it (highlight / progress / status) via the small render API below.
    """

    _logger = get_logger(__name__)
    closeAppEvent = pyqtSignal()

    def __init__(self, config: Configuration, speakers: SpeakersType):
        super().__init__()

        self.resize(720, 260)
        self.setWindowTitle("Cracker")

        self.config = config

        self.speaker = None
        self.speakers = speakers
        self.speaker: AbstractSpeaker | None = None
        self.player: AudioPlayer | None = None

        self.config_window = ConfigWindow(speaker=None)
        self.read_along: ReadAlongController | None = None
        self._icons: dict[str, QIcon] = {}
        self._prev_read_only = False

    def init(self):
        self.set_action()
        self.set_widgets()
        self.init_values()
        self.config_window.init()
        assert self.player is not None, "Player must be set before init"
        self.read_along = ReadAlongController(self, self.player)

    def set_action(self):
        assert self.player, "Cannot set actions on non-defined Player"
        _exit = QAction("Exit", self)
        _exit.setShortcut("Ctrl+Q")
        _exit.setStatusTip("Exit application")
        _exit.triggered.connect(self.request_close)

        _save = QAction("Save config", self)
        _save.setShortcut("Ctrl+S")
        _save.setStatusTip("Save configure")
        _save.triggered.connect(self.save_config)

        self.stop_action = QAction("Stop", self)
        self.stop_action.setShortcut("Ctrl+Shift+S")
        self.stop_action.setStatusTip("Stops text")

        # Split "Read" button: main segment reads the text area (Ctrl+R),
        # the menu also offers reading from the clipboard (Ctrl+Shift+R).
        self.read_action = QAction("Read text area", self)
        self.read_action.setShortcut("Ctrl+R")
        self.read_action.setStatusTip("Read the text area aloud")

        self.clipboard_read_action = QAction("Read from clipboard", self)
        self.clipboard_read_action.setShortcut("Ctrl+Shift+R")
        self.clipboard_read_action.setStatusTip("Reads text from clipboard")

        self.toggle_action = QAction("Pause", self)
        self.toggle_action.setDisabled(True)
        self.toggle_action.setShortcut("Ctrl+Space")
        self.toggle_action.setStatusTip("Toggle read")

        # Button/icon state is driven by the player's queue-aware lifecycle
        # signals (not raw playbackStateChanged, which flickers to Stopped
        # between queued files). The read-along controller wires the rest.
        self.player.readStarted.connect(self._on_read_started)
        self.player.readFinished.connect(self._on_read_finished)
        self.player.playbackStateChanged.connect(self._on_playback_state)

        self.reduce_action = QAction("Reduce", self)
        self.reduce_action.setStatusTip("Reduces unnecessary text")

        self.wiki_action = QAction("Wiki", self)
        self.wiki_action.setShortcut("Ctrl+Shift+W")
        self.wiki_action.setStatusTip("Reduces wiki citations")

        self.cite_action = QAction("Citation", self)
        self.cite_action.setShortcut("Ctrl+Shift+C")
        self.cite_action.setStatusTip("Citation")

        self.toggle_config_window = QAction("Config", self)
        self.toggle_config_window.setStatusTip("Opens configuration")
        self.toggle_config_window.triggered.connect(self.config_window.show)

        # Menu bar keeps every action discoverable and keeps shortcuts active.
        menubar = self.menuBar()
        assert menubar is not None

        fileAction = menubar.addMenu("&File")
        assert fileAction is not None
        fileAction.addAction(_save)
        fileAction.addAction(_exit)
        textAction = menubar.addMenu("&Text")
        assert textAction is not None
        textAction.addAction(self.read_action)
        textAction.addAction(self.clipboard_read_action)
        textAction.addAction(self.stop_action)
        textAction.addAction(self.toggle_action)
        reduceAction = menubar.addMenu("&Reduce")
        assert reduceAction is not None
        reduceAction.addAction(self.reduce_action)
        reduceAction.addAction(self.wiki_action)
        reduceAction.addAction(self.cite_action)

    # --- Icons ------------------------------------------------------------

    def _theme_icon_set(self) -> dict[str, QIcon]:
        """Control-strip icons painted for the current theme (single source)."""
        tokens = active_tokens()
        neutral = tokens["text_secondary"]
        return {
            "read": render_icon("play", tokens["accent_text"], 14),
            "play": render_icon("play", neutral, 15),
            "pause": render_icon("pause", neutral, 15),
            "stop": render_icon("stop", neutral, 15),
            "sliders": render_icon("sliders", neutral, 15),
        }

    def refresh_theme_icons(self) -> None:
        """Rebuild control-strip icons for the current theme (OS theme switch)."""
        if not hasattr(self, "read_button"):
            return
        self._icons = self._theme_icon_set()
        self.read_button.setIcon(self._icons["read"])
        self.stop_button.setIcon(self._icons["stop"])
        self.config_button.setIcon(self._icons["sliders"])
        paused = self.player is not None and self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState
        self.pause_button.setIcon(self._icons["play"] if paused else self._icons["pause"])

    # --- Widget construction ---------------------------------------------

    def set_widgets(self):
        self._icons = self._theme_icon_set()

        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)

        layout = QVBoxLayout(self.mainWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_command_strip())
        layout.addWidget(self._build_voice_strip())
        layout.addWidget(self._build_progress_bar())
        layout.addWidget(self._build_text_area())

        self._build_status_bar()
        self.set_read_status(reading=False)

    def _build_command_strip(self) -> QWidget:
        strip = QWidget()
        strip.setObjectName("commandStrip")
        row = QHBoxLayout(strip)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(8)

        # Primary split "Read" button.
        self.read_button = QToolButton()
        self.read_button.setObjectName("readButton")
        self.read_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.read_button.setIcon(self._icons["read"])
        self.read_button.setText("Read")
        self.read_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        read_menu = QMenu(self.read_button)
        read_menu.addAction(self.read_action)
        read_menu.addAction(self.clipboard_read_action)
        self.read_button.setMenu(read_menu)
        self.read_button.clicked.connect(self.read_action.trigger)
        row.addWidget(self.read_button)

        # Stop / Pause icon buttons.
        self.stop_button = self._icon_button(self._icons["stop"], "Stop")
        self.stop_button.clicked.connect(self.stop_action.trigger)
        self.stop_button.setEnabled(False)
        row.addWidget(self.stop_button)

        self.pause_button = self._icon_button(self._icons["pause"], "Pause")
        self.pause_button.clicked.connect(self.toggle_action.trigger)
        self.pause_button.setEnabled(False)
        row.addWidget(self.pause_button)

        divider = QFrame()
        divider.setObjectName("vDivider")
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedWidth(1)
        row.addWidget(divider)

        for action in (self.reduce_action, self.wiki_action, self.cite_action):
            btn = QToolButton()
            btn.setProperty("flatlink", True)
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.setText(action.text())
            btn.clicked.connect(action.trigger)
            row.addWidget(btn)

        row.addStretch(1)

        self.config_button = QToolButton()
        self.config_button.setObjectName("configButton")
        self.config_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.config_button.setIcon(self._icons["sliders"])
        self.config_button.setText("Config")
        self.config_button.clicked.connect(self.toggle_config_window.trigger)
        row.addWidget(self.config_button)

        return strip

    def _icon_button(self, icon: QIcon, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setProperty("iconbtn", True)
        btn.setIcon(icon)
        btn.setIconSize(QSize(15, 15))
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        return btn

    def _build_voice_strip(self) -> QWidget:
        strip = QWidget()
        strip.setObjectName("voiceStrip")
        row = QHBoxLayout(strip)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)

        assert self.config.speaker, "Speaker needs to be defined"

        _speakers = [k.capitalize() for k in self.speakers.keys()]
        self.speakerW = QComboBox(self)
        self.speakerW.addItems(_speakers)
        self.speakerW.setMinimumContentsLength(8)
        self.speakerW.setCurrentIndex(_speakers.index(self.config.speaker.capitalize()))
        row.addWidget(self.speakerW)
        row.addWidget(self._separator())

        self.langW = QComboBox(self)
        self.langW.addItems(self.config.languages)
        language = self.config.language
        assert language is not None
        self.langW.setCurrentIndex(self.config.languages.index(language))
        self.langW.setMinimumContentsLength(8)
        self.langW.currentTextChanged.connect(self.change_language)
        row.addWidget(self.langW)
        row.addWidget(self._separator())

        self.voiceW = QComboBox(self)
        self.voiceW.addItems(self.config.lang_voices)
        voice = self.config.voice
        assert voice is not None
        self.voiceW.setCurrentIndex(self.config.lang_voices.index(voice))
        self.voiceW.setMinimumContentsLength(10)
        self.voiceW.currentTextChanged.connect(self.change_voice)
        row.addWidget(self.voiceW)

        row.addStretch(1)

        speed_label = QLabel("Speed")
        speed_label.setProperty("meta", True)
        row.addWidget(speed_label)
        self.speedW = QSpinBox()
        self.speedW.setRange(1, 5)
        self.speedW.setSuffix("×")
        self.speedW.setValue(self.config.speed)
        self.speedW.valueChanged.connect(self.change_speed)
        row.addWidget(self.speedW)

        vol_label = QLabel("Vol")
        vol_label.setProperty("meta", True)
        row.addWidget(vol_label)
        self.volumeW = QSlider(Qt.Orientation.Horizontal, self)  # Range: 0 -- 99
        self.volumeW.setFixedWidth(80)
        self.volumeW.setValue(50)
        self.volumeW.valueChanged.connect(self.change_volume)
        row.addWidget(self.volumeW)

        return strip

    def _separator(self) -> QLabel:
        sep = QLabel("·")
        sep.setProperty("sep", True)
        return sep

    def _build_progress_bar(self) -> QProgressBar:
        self.readProgress = QProgressBar()
        self.readProgress.setObjectName("readProgress")
        self.readProgress.setRange(0, 100)
        self.readProgress.setValue(0)
        self.readProgress.setTextVisible(False)
        self.readProgress.setFixedHeight(3)
        return self.readProgress

    def _build_text_area(self) -> QWidget:
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(12, 10, 12, 10)
        self.textEdit = QTextEdit()
        self.textEdit.setPlaceholderText("Paste or type text to read aloud…")
        box.addWidget(self.textEdit)
        return container

    def _build_status_bar(self) -> None:
        status = self.statusBar()
        assert status is not None

        left = QWidget()
        left_row = QHBoxLayout(left)
        left_row.setContentsMargins(8, 0, 0, 0)
        left_row.setSpacing(6)
        self.stateDot = QLabel()
        self.stateDot.setFixedSize(8, 8)
        self.statusLeftLabel = QLabel("Idle")
        left_row.addWidget(self.stateDot)
        left_row.addWidget(self.statusLeftLabel)
        status.addWidget(left)

        self.statusRightLabel = QLabel("")
        status.addPermanentWidget(self.statusRightLabel)

    def init_values(self):
        self.change_volume(self.volumeW.value())
        self.change_speed(self.speedW.value())
        self.change_language(self.config.language)

    # --- Read-along render API (called by ReadAlongController) -------------

    def current_wpm(self) -> int:
        speed = int(self.config.speed) if self.config.speed else 3
        speed = max(1, min(5, speed))
        return READ_WPM[speed - 1]

    def editor_text(self) -> str:
        return self.textEdit.toPlainText()

    def set_read_source(self, source: str, text: str = "") -> None:
        """Set by the app controller before each read: 'textarea' or 'clipboard'."""
        if self.read_along is not None:
            self.read_along.set_read_context(source, text)

    def set_reading_readonly(self, reading: bool) -> None:
        if reading:
            self._prev_read_only = self.textEdit.isReadOnly()
            self.textEdit.setReadOnly(True)
        else:
            self.textEdit.setReadOnly(self._prev_read_only)

    def set_read_progress(self, percent: int) -> None:
        self.readProgress.setValue(percent)

    def highlight_span(self, start: int, length: int, doc_len: int) -> None:
        hi_bg, hi_fg, muted = self._readalong_colors()
        selections = []
        dim_start = start + length
        if dim_start < doc_len:
            selections.append(self._extra_selection(dim_start, doc_len - dim_start, None, muted))
        selections.append(self._extra_selection(start, length, hi_bg, hi_fg))
        self.textEdit.setExtraSelections(selections)

    def clear_highlight(self) -> None:
        self.textEdit.setExtraSelections([])

    def set_read_status(self, reading: bool, words_done: int = 0, total: int = 0) -> None:
        tokens = active_tokens()
        if reading:
            dot_color = tokens["accent"]
            voice = self.config.voice or ""
            self.statusLeftLabel.setText(f"Reading · {voice}" if voice else "Reading")
            if total:
                remaining = max(0, total - words_done)
                left = remaining / (self.current_wpm() / 60.0)
                self.statusRightLabel.setText(f"{total} words · ~{int(left // 60)}:{int(left % 60):02d} left")
            else:
                self.statusRightLabel.setText("")
        else:
            dot_color = tokens["text_muted"]
            self.statusLeftLabel.setText("Idle")
            self.statusRightLabel.setText("")
        self.stateDot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")

    def _readalong_colors(self) -> tuple[QColor, QColor, QColor]:
        tokens = active_tokens()
        muted = QColor(tokens["text_muted"])
        if tokens["is_dark"]:
            bg = QColor(124, 140, 248)
            bg.setAlpha(62)
            return bg, QColor("#dfe3ff"), muted
        return QColor("#dbe7ff"), QColor("#15315e"), muted

    def _extra_selection(self, start: int, length: int, bg: QColor | None, fg: QColor | None):
        selection = QTextEdit.ExtraSelection()
        cursor = QTextCursor(self.textEdit.document())
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        fmt = QTextCharFormat()
        if bg is not None:
            fmt.setBackground(bg)
        if fg is not None:
            fmt.setForeground(fg)
        selection.format = fmt
        return selection

    # --- Playback button state -------------------------------------------

    def _on_read_started(self) -> None:
        self._set_playback_buttons(playing=True)

    def _on_read_finished(self) -> None:
        self._set_playback_buttons(playing=False)

    def _on_playback_state(self, state) -> None:
        # Only the pause/resume affordance changes here; start/stop are handled
        # via readStarted/readFinished (Stopped flickers between segments).
        if state == QMediaPlayer.PlaybackState.PausedState:
            self.toggle_action.setText("Resume")
            if hasattr(self, "pause_button"):
                self.pause_button.setIcon(self._icons["play"])
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.toggle_action.setText("Pause")
            if hasattr(self, "pause_button"):
                self.pause_button.setIcon(self._icons["pause"])

    def _set_playback_buttons(self, playing: bool, paused: bool = False) -> None:
        active = playing or paused
        if hasattr(self, "read_button"):
            self.read_button.setEnabled(not active)
            self.stop_button.setEnabled(active)
            self.pause_button.setEnabled(active)
            self.pause_button.setIcon(self._icons["play"] if paused else self._icons["pause"])
        self.read_action.setDisabled(active)
        self.clipboard_read_action.setDisabled(active)
        self.stop_action.setDisabled(not active)
        self.toggle_action.setDisabled(not active)
        if not active:
            self.toggle_action.setText("Pause")

    # --- Lifecycle / slots ------------------------------------------------

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Triggers CloseEvent and handles closing gracefully"""
        self.closeAppEvent.emit()
        if hasattr(self, "speaker"):
            del self.speaker
        if a0 is not None:
            a0.accept()

    def request_close(self) -> None:
        self.close()

    def save_config(self):
        self._logger.debug("Saving user config")
        self.config.save_user_config()

    def change_speaker(self, speaker_name: str, speaker: AbstractSpeaker):
        """Action on changing speaker.

        Important: Each speaker has its own configuration.
        These values should be updated on change.
        """
        self.speaker = speaker
        self.config.speaker = speaker_name
        self.config.load_speaker_config(speaker_name)
        self.init_values()
        # Update config window with new speaker reference
        self.config_window.speaker = self.speaker

    def change_volume(self, volume):
        """Volume should be on a percentage scale"""
        assert self.speaker, "Speaker doesn't exist. Can't change volume."
        discrete_vol = int(volume * len(self.speaker.VOLUMES) / 100)
        discrete_vol = min(discrete_vol, len(self.speaker.VOLUMES) - 1)
        self.volume = self.speaker.VOLUMES[discrete_vol]
        self.save_config()

    def change_speed(self, speed):
        assert self.speaker, "Speaker doesn't exist. Can't change speed."
        self.config.speed = speed
        self.rate = self.speaker.RATES[speed - 1]
        self.save_config()

    def change_language(self, language):
        self.config.language = language
        voices = self.config.voices[language]
        self.voiceW.clear()
        self.voiceW.addItems(voices)
        self.change_voice(voices[0])
        self.save_config()

    def change_voice(self, voice):
        self.config.voice = voice
        self.save_config()
