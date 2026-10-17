"""Pawse - small custom-painted widgets (no image assets)."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from ui.theme import COCOA, CREAM, MINT


class PawCheck(QAbstractButton):
    """Round checkbox that fills mint and shows a little paw print when checked."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(30, 30)

    def sizeHint(self):
        return QSize(30, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        fill = QColor(MINT) if on else QColor(CREAM if self.underMouse() else "#FFFFFF")
        p.setBrush(fill)
        p.setPen(QPen(QColor(COCOA) if on else QColor(74, 64, 58, 130), 1.6))
        p.drawEllipse(QRectF(2, 2, 26, 26))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(COCOA) if on else QColor(74, 64, 58, 55))
        p.drawEllipse(QRectF(9.5, 15, 11, 8.5))                                  # main pad
        for x, y in ((6.5, 12), (10.5, 8.5), (15.5, 8.5), (19.5, 12)):          # toes
            p.drawEllipse(QRectF(x, y, 4, 5))


class ToggleSwitch(QAbstractButton):
    """iOS-style switch: mint track when on."""

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(46, 26)

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on = self.isChecked()
        p.setPen(QPen(QColor(COCOA) if on else QColor(74, 64, 58, 70), 1.4))
        p.setBrush(QColor(MINT) if on else QColor(74, 64, 58, 28))
        p.drawRoundedRect(QRectF(1, 1, 44, 24), 12, 12)
        p.setPen(QPen(QColor(COCOA), 1.4) if on else QPen(QColor(74, 64, 58, 90), 1.2))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(24 if on else 4, 4, 18, 18))
