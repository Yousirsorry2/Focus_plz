"""Pawse - Focus Guard alert overlay."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)

from ui.mochi import MochiCat
from ui.theme import APP_QSS, COCOA

HEADINGS = {1: "A tiny detour?", 2: "Still wandering?", 3: "Mochi is getting worried"}


class PawsePopup(QWidget):
    """Borderless, always-on-top, non-activating card in the bottom-right corner.

    buttons: list of (label, kind, callback, enabled) where kind is one of
    "primary" | "outline" | "text". A callback runs after the popup closes.
    """

    def __init__(self, *, badge, heading, message, buttons, detail="", footer="", on_closed=None):
        super().__init__()
        self.setObjectName("PopupRoot")
        self._on_closed = on_closed
        self.setStyleSheet(APP_QSS)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 12, 18, 24)   # room for the shadow

        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(74, 64, 58, 70))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(0)

        top = QHBoxLayout()
        brand = QLabel("Pawse")
        brand.setObjectName("brand")
        pill = QLabel(badge)
        pill.setObjectName("badge")
        pill.setFixedHeight(20)
        top.addWidget(brand)
        top.addStretch()
        top.addWidget(pill)
        lay.addLayout(top)
        lay.addSpacing(4)

        mid = QHBoxLayout()
        mid.setSpacing(10)
        mid.addWidget(MochiCat("alert", width=92), 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addStretch()
        for name, text in (("popupHeading", heading), ("popupMessage", message), ("popupDetail", detail)):
            if text:
                lab = QLabel(text)
                lab.setObjectName(name)
                lab.setWordWrap(True)
                col.addWidget(lab)
        col.addStretch()
        mid.addLayout(col, 1)
        lay.addLayout(mid)
        lay.addSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(6)
        for label, kind, cb, enabled in buttons:
            b = QPushButton(label)
            b.setObjectName({"primary": "popupPrimary", "outline": "popupOutline", "text": "popupText"}[kind])
            b.setEnabled(enabled)
            b.setFocusPolicy(Qt.NoFocus)
            b.setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)
            if enabled:
                b.clicked.connect(lambda _=False, cb=cb: self.finish(cb))
            f = QFont(b.font())
            f.setPixelSize(12)
            f.setBold(True)
            b.setMinimumWidth(QFontMetrics(f).horizontalAdvance(label) + 34)   # never clip the label
            row.addWidget(b, 1 if kind == "primary" else 0)
        lay.addLayout(row)

        if footer:
            f = QLabel(footer)
            f.setObjectName("popupFooter")
            f.setAlignment(Qt.AlignCenter)
            f.setContentsMargins(0, 8, 0, 0)
            lay.addWidget(f)

        self.setFixedWidth(420)
        self.setFixedHeight(outer.totalHeightForWidth(420))   # wrapped labels need width-aware height
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 4, screen.bottom() - self.height() - 4)

        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(180)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def finish(self, cb=None):
        """Close the popup, tell the tracker, then run the button's action."""
        self.hide()
        self.deleteLater()
        if self._on_closed:
            self._on_closed()
        if cb:
            cb()


def alert_popup(payload: dict, task: str, tracker, on_closed) -> PawsePopup:
    """Build the Focus Guard popup for a tracker.alert payload."""
    lvl = payload["level"]
    left = payload["snoozes_left"]
    snooze_text = (f"Snooze {payload['snooze_minutes']:g} min" if payload["can_snooze"]
                   else "Snooze used up")
    footer = f"Next reminder in {payload['next_interval']:g} min"
    if payload["can_snooze"]:
        footer += f"  \u00b7  {left} snooze{'s' if left != 1 else ''} left"
    else:
        footer += f"  \u00b7  snooze limit {payload['max_snoozes']}/{payload['snooze_window_hours']}h"
    return PawsePopup(
        badge=f"Reminder Level {lvl}",
        heading=HEADINGS.get(lvl, "Time to head back"),
        message=f"Hey! Aren't we focusing on {task} right now? \U0001F43E",
        detail=payload["detail"],
        footer=footer,
        buttons=[("Back to Work", "primary", tracker.back_to_work, True),
                 (snooze_text, "outline", tracker.snooze, payload["can_snooze"]),
                 ("Skip", "text", tracker.skip, True)],
        on_closed=on_closed,
    )


def checkin_popup(idle_seconds: int, on_closed) -> PawsePopup:
    return PawsePopup(
        badge="Check-in",
        heading="Still there?",
        message=f"It's been quiet for {max(1, idle_seconds // 60)} min. Maybe stretch for a moment? \U0001F43E",
        buttons=[("OK", "primary", None, True)],
        on_closed=on_closed,
    )
