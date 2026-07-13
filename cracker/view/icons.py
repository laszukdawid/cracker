"""Small monochrome control-strip icons drawn with QPainter.

Icons are painted at runtime in a single colour taken from the active theme
tokens, so no SVG/PNG assets need to ship and the glyphs stay crisp at any DPI.
Rebuild the icons (see ``theme_icons``) if the colour scheme changes.
"""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap

_Kind = str


def render_icon(kind: _Kind, color: str, size: int = 16) -> QIcon:
    """Renders ``kind`` (play/stop/pause/sliders) as a ``QIcon`` in ``color``."""
    scale = 4  # supersample then let QIcon downscale for smooth edges
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    qcolor = QColor(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(qcolor))

    s = size * scale
    if kind == "play":
        painter.drawPolygon(
            QPointF(s * 0.30, s * 0.22),
            QPointF(s * 0.30, s * 0.78),
            QPointF(s * 0.80, s * 0.50),
        )
    elif kind == "stop":
        painter.drawRoundedRect(QRectF(s * 0.26, s * 0.26, s * 0.48, s * 0.48), s * 0.06, s * 0.06)
    elif kind == "pause":
        bar_w = s * 0.16
        painter.drawRoundedRect(QRectF(s * 0.30, s * 0.24, bar_w, s * 0.52), s * 0.04, s * 0.04)
        painter.drawRoundedRect(QRectF(s * 0.54, s * 0.24, bar_w, s * 0.52), s * 0.04, s * 0.04)
    elif kind == "sliders":
        # Three horizontal rails, each with an offset knob (an adjustments glyph).
        pen = QPen(qcolor)
        pen.setWidthF(s * 0.055)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rows = (s * 0.30, s * 0.50, s * 0.70)
        knobs = (s * 0.62, s * 0.38, s * 0.58)
        for y, knob_x in zip(rows, knobs):
            painter.drawLine(QPointF(s * 0.22, y), QPointF(s * 0.78, y))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(qcolor))
        knob_r = s * 0.08
        for y, knob_x in zip(rows, knobs):
            painter.drawEllipse(QPointF(knob_x, y), knob_r, knob_r)

    painter.end()
    return QIcon(px)


def theme_icons(color: str, size: int = 16) -> dict[str, QIcon]:
    """Returns the control-strip icon set drawn in ``color``."""
    return {kind: render_icon(kind, color, size) for kind in ("play", "stop", "pause", "sliders")}
