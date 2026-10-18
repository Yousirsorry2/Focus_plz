"""Pawse - Focus Guard alert overlay."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGraphicsDropShadowEffect,
                               QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout,
                               QWidget)

from ui.mochi import MochiCat
from ui.tasks_theme import FULL_QSS
from ui.theme import COCOA

HEADINGS = {1: "A tiny detour?", 2: "Still wandering?", 3: "Mochi is getting worried"}
BUTTON_IDS = {"primary": "popupPrimary", "work": "popupWork",
              "outline": "popupOutline", "text": "popupText"}


class PawsePopup(QWidget):
    """Borderless, always-on-top, non-activating card in the bottom-right corner.

    buttons: a list of (label, kind, callback, enabled[, tooltip]) tuples, or a list of such
    lists to get several rows. kind is "primary" | "work" | "outline" | "text".
    A callback runs after the popup closes.
    """

    def __init__(self, *, badge, heading, message, buttons, detail="", footer="", on_closed=None):
        super().__init__()
        self.setObjectName("PopupRoot")
        self._on_closed = on_closed
        self.setStyleSheet(FULL_QSS)
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

        rows = buttons if buttons and isinstance(buttons[0], list) else [buttons]
        for r, spec in enumerate(rows):
            if r:
                lay.addSpacing(6)
            row = QHBoxLayout()
            row.setSpacing(6)
            for label, kind, cb, enabled, *extra in spec:
                b = QPushButton(label)
                b.setObjectName(BUTTON_IDS[kind])
                b.setEnabled(enabled)
                b.setFocusPolicy(Qt.NoFocus)
                b.setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)
                if extra and extra[0]:
                    b.setToolTip(extra[0])
                if enabled:
                    b.clicked.connect(lambda _=False, cb=cb: self.finish(cb))
                f = QFont(b.font())
                f.setPixelSize(12)
                f.setBold(True)
                b.setMinimumWidth(QFontMetrics(f).horizontalAdvance(label) + 34)   # never clip the label
                row.addWidget(b, 0 if kind == "text" else 1)
            lay.addLayout(row)

        if footer:
            f = QLabel(footer)
            f.setObjectName("popupFooter")
            f.setAlignment(Qt.AlignCenter)
            f.setContentsMargins(0, 8, 0, 0)
            lay.addWidget(f)

        screen = QApplication.primaryScreen().availableGeometry()
        width = min(420, screen.width() - 16)
        self.setFixedWidth(width)
        self.setFixedHeight(outer.totalHeightForWidth(width))
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


class MarkWorkDialog(QDialog):
    def __init__(self, target: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sheet")
        self.setWindowTitle("Check with Mochi")
        self.setStyleSheet(FULL_QSS)
        self.setModal(True)
        screen_width = QApplication.primaryScreen().availableGeometry().width()
        self.setFixedWidth(min(370, screen_width - 24))
        self.scope = "permanent"
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(10)
        root.addWidget(MochiCat("alert", width=110), 0, Qt.AlignHCenter)
        message = QLabel(f"Are you sure {target} is work? Mochi will remember this and won't warn you again.")
        message.setObjectName("popupMessage")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignCenter)
        root.addWidget(message)
        self.temporary = QRadioButton("Work for this session only (25 min)")
        self.permanent = QRadioButton("Always Work")
        self.permanent.setChecked(True)
        root.addWidget(self.temporary)
        root.addWidget(self.permanent)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel / Back to Focus")
        confirm = QPushButton("Confirm (Mark as Work)")
        cancel.setObjectName("capsule")
        confirm.setObjectName("capsulePrimary")
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self._confirm)
        row.addWidget(cancel)
        row.addWidget(confirm)
        root.addLayout(row)

    def _confirm(self):
        self.scope = "session" if self.temporary.isChecked() else "permanent"
        self.accept()


def alert_popup(payload: dict, task: str, tracker, on_mark_work, on_closed) -> PawsePopup:
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

    target = payload.get("target", "")
    work_tip = (f"Not a distraction? Teach Pawse that \u201c{target}\u201d is work."
                if target else "Not a distraction? Teach Pawse that this is work.")
    hard_blocked = tracker.current_target_is_hard_blocked()
    work_label = "Only in Settings \u2699" if hard_blocked else "Mark as Work \U0001F4CC"
    if hard_blocked:
        work_tip = "Major entertainment apps can only be whitelisted manually in Settings."
    return PawsePopup(
        badge=f"Reminder Level {lvl}",
        heading=HEADINGS.get(lvl, "Time to head back"),
        message=f"Hey! Aren't we focusing on {task} right now? \U0001F43E",
        detail=payload["detail"],
        footer=footer,
        buttons=[
             [("Back to Work", "primary", tracker.back_to_work, True)#,
            #  (work_label, "work", on_mark_work,
            #   bool(target) and not hard_blocked, work_tip)
            ],
            [(snooze_text, "outline", tracker.snooze, payload["can_snooze"]),
             ("Skip", "text", tracker.skip, True)],
        ],
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
