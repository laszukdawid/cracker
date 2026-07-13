"""Light/dark theme system for Cracker.

Exposes two token dictionaries (``LIGHT`` / ``DARK``) taken from the visual
refresh spec, a :func:`build_qss` that turns a token set into a global
stylesheet, and :func:`apply_theme` which applies both an owned ``QPalette``
(for unstyled/native chrome) and the stylesheet to the application.

Only sizes, weights, radii and colours are set here -- the system UI font is
left untouched so the app looks native on macOS/Windows/Linux.
"""

import re
from typing import TypedDict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPalette
from PyQt6.QtWidgets import QApplication


class ThemeTokens(TypedDict):
    """One theme's tokens: ``is_dark`` flag plus colour strings."""

    is_dark: bool
    bg_window: str
    bg_strip: str
    bg_titlebar: str
    bg_surface: str
    bg_field: str
    bg_chip: str
    border: str
    border_input: str
    text_primary: str
    text_secondary: str
    text_muted: str
    text_placeholder: str
    accent: str
    accent_hover: str
    accent_text: str
    readalong_bg: str
    readalong_text: str
    zebra_a: str
    zebra_b: str
    seg_track: str
    seg_active: str


# --- Design tokens ---------------------------------------------------------

LIGHT: ThemeTokens = {
    "is_dark": False,
    "bg_window": "#fbfbfa",
    "bg_strip": "#f6f5f3",
    "bg_titlebar": "#f6f5f3",
    "bg_surface": "#ffffff",
    "bg_field": "#faf9f7",
    "bg_chip": "#f0efec",
    "border": "rgba(0, 0, 0, 0.10)",
    "border_input": "rgba(0, 0, 0, 0.15)",
    "text_primary": "#292524",
    "text_secondary": "#57534e",
    "text_muted": "#a8a29e",
    "text_placeholder": "#b8b3ac",
    "accent": "#0a66ff",
    "accent_hover": "#2f7bff",
    "accent_text": "#ffffff",
    "readalong_bg": "#dbe7ff",
    "readalong_text": "#15315e",
    "zebra_a": "#ffffff",
    "zebra_b": "#faf9f7",
    "seg_track": "#e7e5e1",
    "seg_active": "#ffffff",
}

DARK: ThemeTokens = {
    "is_dark": True,
    "bg_window": "#1b1b1f",
    "bg_strip": "#212127",
    "bg_titlebar": "#26262b",
    "bg_surface": "#161619",
    "bg_field": "#2c2c33",
    "bg_chip": "#2c2c33",
    "border": "rgba(255, 255, 255, 0.06)",
    "border_input": "rgba(255, 255, 255, 0.12)",
    "text_primary": "#e4e4ea",
    "text_secondary": "#c4c4cc",
    "text_muted": "#9a9aa4",
    "text_placeholder": "#6a6a73",
    "accent": "#7c8cf8",
    "accent_hover": "#8f9dff",
    "accent_text": "#15151a",
    "readalong_bg": "rgba(124, 140, 248, 0.24)",
    "readalong_text": "#dfe3ff",
    "zebra_a": "#161619",
    "zebra_b": "#1b1b1f",
    "seg_track": "#2c2c33",
    "seg_active": "#3a3a42",
}

THEMES: dict[str, ThemeTokens] = {"light": LIGHT, "dark": DARK}


def tokens_for(theme: str | None) -> ThemeTokens:
    """Returns the token set for ``theme`` ("dark"/"light"), defaulting to light."""
    return DARK if (theme or "light").lower() == "dark" else LIGHT


def active_theme_name() -> str:
    """Best-effort detection of the current OS colour scheme.

    Prefers Qt's own ``colorScheme`` (Qt 6.5+); falls back to ``darkdetect``.
    """
    if QApplication.instance() is not None:
        try:
            hints = QGuiApplication.styleHints()
            scheme = hints.colorScheme() if hints is not None else Qt.ColorScheme.Unknown
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
            if scheme == Qt.ColorScheme.Light:
                return "light"
        except Exception:
            pass
    try:
        import darkdetect

        return (darkdetect.theme() or "light").lower()
    except Exception:
        return "light"


def active_tokens() -> ThemeTokens:
    """Token set matching the current OS colour scheme."""
    return tokens_for(active_theme_name())


# --- Stylesheet ------------------------------------------------------------

# Placeholders use ``@token@`` markers (rather than ``str.format``) so the many
# literal ``{ }`` blocks in the QSS don't need escaping.
_QSS_TEMPLATE = """
QMainWindow, QDialog {
    background: @bg_window@;
    color: @text_primary@;
}
QWidget {
    color: @text_primary@;
}
QToolTip {
    background: @bg_surface@;
    color: @text_primary@;
    border: 1px solid @border_input@;
    padding: 4px 6px;
}

/* --- Command strip ---------------------------------------------------- */
#commandStrip {
    background: @bg_strip@;
    border-bottom: 1px solid @border@;
}
#voiceStrip {
    background: @bg_window@;
    border-bottom: 1px solid @border@;
}

/* Primary split "Read" button */
QToolButton#readButton {
    background: @accent@;
    color: @accent_text@;
    border: none;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}
QToolButton#readButton:hover { background: @accent_hover@; }
QToolButton#readButton::menu-button {
    border: none;
    width: 18px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QToolButton#readButton:disabled { background: @bg_chip@; color: @text_muted@; }

/* Square icon buttons (Stop / Pause) */
QToolButton[iconbtn="true"] {
    background: transparent;
    border: 1px solid @border_input@;
    border-radius: 8px;
    color: @text_secondary@;
}
QToolButton[iconbtn="true"]:hover { background: @bg_field@; }
QToolButton[iconbtn="true"]:disabled { color: @text_muted@; border-color: @border@; }

/* Flat text buttons (Reduce / Wiki / Citation) */
QToolButton[flatlink="true"] {
    background: transparent;
    border: none;
    color: @text_secondary@;
    padding: 6px 8px;
    font-size: 12px;
}
QToolButton[flatlink="true"]:hover { color: @text_primary@; }

/* Bordered Config button */
QToolButton#configButton {
    background: transparent;
    border: 1px solid @border_input@;
    border-radius: 8px;
    color: @text_secondary@;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}
QToolButton#configButton:hover { background: @bg_field@; color: @text_primary@; }

QFrame#vDivider { color: @border@; background: @border@; max-width: 1px; }

/* --- Voice strip ------------------------------------------------------ */
#voiceStrip QComboBox {
    background: @bg_chip@;
    border: 1px solid @border@;
    border-radius: 6px;
    padding: 3px 8px;
    min-height: 22px;
    color: @text_primary@;
}
#voiceStrip QComboBox:hover { border-color: @border_input@; }
#voiceStrip QComboBox::drop-down { border: none; width: 16px; }
QComboBox QAbstractItemView {
    background: @bg_surface@;
    color: @text_primary@;
    selection-background-color: @accent@;
    selection-color: @accent_text@;
    border: 1px solid @border_input@;
}
QLabel[sep="true"] { color: @text_muted@; }
QLabel[meta="true"] {
    color: @text_muted@;
    font-size: 11px;
    font-weight: 600;
}

QSpinBox {
    background: @bg_field@;
    border: 1px solid @border_input@;
    border-radius: 8px;
    padding: 2px 4px;
    min-height: 24px;
    color: @text_primary@;
}

QSlider::groove:horizontal {
    height: 4px;
    background: @bg_chip@;
    border-radius: 2px;
}
QSlider::sub-page:horizontal { background: @accent@; border-radius: 2px; }
QSlider::handle:horizontal {
    background: @accent@;
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}

/* --- Reading progress bar --------------------------------------------- */
QProgressBar#readProgress {
    background: @bg_chip@;
    border: none;
    max-height: 3px;
    min-height: 3px;
}
QProgressBar#readProgress::chunk { background: @accent@; }

/* --- Text area -------------------------------------------------------- */
QTextEdit {
    background: @bg_surface@;
    border: 1px solid @border@;
    border-radius: 11px;
    padding: 14px 16px;
    color: @text_primary@;
    selection-background-color: @accent@;
    selection-color: @accent_text@;
}

/* --- Status bar ------------------------------------------------------- */
QStatusBar {
    background: @bg_strip@;
    border-top: 1px solid @border@;
    color: @text_muted@;
}
QStatusBar::item { border: none; }
QStatusBar QLabel { color: @text_muted@; font-size: 11px; }

/* --- Config dialog ---------------------------------------------------- */
QFrame#card {
    background: @bg_surface@;
    border: 1px solid @border@;
    border-radius: 11px;
}
QLabel#cardTitle { font-size: 12px; font-weight: 600; color: @text_primary@; }

/* Segmented (pill) tabs */
QTabWidget::pane { border: none; top: -1px; }
QTabBar { qproperty-drawBase: 0; }
QTabBar::tab {
    background: @seg_track@;
    color: @text_secondary@;
    padding: 6px 20px;
    margin: 2px;
    border: none;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: @seg_active@;
    color: @text_primary@;
    border: 1px solid @border@;
    font-weight: 600;
}

/* Parser table + speaker cards */
QLineEdit {
    background: @bg_field@;
    border: 1px solid @border_input@;
    border-radius: 8px;
    padding: 4px 8px;
    color: @text_primary@;
}
QLineEdit:focus { border-color: @accent@; }
QLineEdit[mono="true"] {
    font-family: "ui-monospace", "SF Mono", "Menlo", "Consolas", monospace;
    font-size: 11px;
}
QLabel[colhead="true"] {
    color: @text_muted@;
    font-size: 10px;
    font-weight: 600;
}
#tableHeader { background: @bg_strip@; }
QWidget[zebra="a"] { background: @zebra_a@; }
QWidget[zebra="b"] { background: @zebra_b@; }
QLabel#rowLabel { color: @text_secondary@; }

/* Push buttons */
QPushButton {
    background: @bg_field@;
    border: 1px solid @border_input@;
    border-radius: 8px;
    padding: 6px 16px;
    min-height: 22px;
    color: @text_primary@;
}
QPushButton:hover { background: @bg_chip@; }
QPushButton#primary {
    background: @accent@;
    color: @accent_text@;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover { background: @accent_hover@; }
"""


def build_qss(tokens: ThemeTokens) -> str:
    """Renders the global stylesheet from a token set.

    Raises if any ``@token@`` placeholder is left unresolved (a typo'd token).
    """
    qss = _QSS_TEMPLATE
    for key, value in tokens.items():
        if isinstance(value, str):
            qss = qss.replace(f"@{key}@", value)
    unresolved = sorted(set(re.findall(r"@[a-z_]+@", qss)))
    if unresolved:
        raise ValueError(f"Unresolved theme tokens in stylesheet: {unresolved}")
    return qss


# --- Palette + application --------------------------------------------------


def palette_for_theme(app: QApplication, theme: str | None) -> QPalette:
    """Owns a palette derived from the token set (used for native chrome)."""
    tokens = tokens_for(theme)
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(tokens["bg_window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens["bg_surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["zebra_b"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens["bg_surface"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens["text_placeholder"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens["bg_strip"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 90, 90))
    palette.setColor(QPalette.ColorRole.Link, QColor(tokens["accent"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens["accent_text"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(tokens["text_muted"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(tokens["text_muted"]))
    return palette


def apply_theme(app: QApplication, theme: str | None) -> None:
    """Applies the owned palette and global stylesheet for ``theme``."""
    app.setPalette(palette_for_theme(app, theme))
    app.setStyleSheet(build_qss(tokens_for(theme)))
