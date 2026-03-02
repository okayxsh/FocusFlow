"""
glass_widgets.py — Shared glassmorphism base widgets for FocusFlow.
"""
from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient
from PyQt5.QtCore import Qt, QRectF, QPointF


class GlassPanel(QFrame):
    """
    A rounded, semi-transparent glass card.
    alpha: 0–255  (lower = more transparent)
    """
    def __init__(self, parent=None, radius=20, alpha=18, border_alpha=35,
                 accent=False):
        super().__init__(parent)
        self._radius = radius
        self._alpha = alpha
        self._border_alpha = border_alpha
        self._accent = accent
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        rect = QRectF(r.x() + 1, r.y() + 1, r.width() - 2, r.height() - 2)

        # Fill
        fill_color = QColor(255, 255, 255, self._alpha)
        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # Border
        if self._accent:
            border = QColor(99, 102, 241, 120)   # indigo glow
        else:
            border = QColor(255, 255, 255, self._border_alpha)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border, 1.2))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        super().paintEvent(event)


class GlowLabel(QWidget):
    """Renders a large number/text with a soft indigo glow."""
    def __init__(self, text="", font_size=80, parent=None):
        super().__init__(parent)
        self._text = text
        self._font_size = font_size
        self.setMinimumHeight(font_size + 20)

    def set_text(self, t):
        self._text = t
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Glow halo
        cx, cy = self.width() / 2, self.height() / 2
        from PyQt5.QtGui import QFont
        for glow_alpha, glow_size in [(15, 120), (25, 80), (40, 50)]:
            g = QRadialGradient(cx, cy, glow_size)
            g.setColorAt(0, QColor(99, 102, 241, glow_alpha))
            g.setColorAt(1, QColor(99, 102, 241, 0))
            painter.setBrush(QBrush(g))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), glow_size, glow_size * 0.4)

        # Text
        font = QFont("Segoe UI Variable Display", self._font_size, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(248, 250, 252))
        painter.drawText(self.rect(), Qt.AlignCenter, self._text)
