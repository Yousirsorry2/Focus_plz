"""Pawse - Focus Mode screen."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QEvent, QPointF, QRectF, QSettings, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QInputDialog, QLabel,
                               QProgressBar, QPushButton, QVBoxLayout, QWidget)

from ui.mochi import MochiCat
from ui.tasks_theme import FULL_QSS
from ui.theme import COCOA, MINT, make_paw_icon
from ui.navigation import BottomNavigation

SESSION_MINUTES = 25
MIN_MINUTES, MAX_MINUTES = 1, 180


def _repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


class CheckPill(QCheckBox):
    """Small tick-box with a mint fill when checked (custom painted, no image assets)."""

    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def sizeHint(self):
        return QSize(28 + self.fontMetrics().horizontalAdvance(self.text()) + 6, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(1.5, (self.height() - 16) / 2, 16, 16)
        on = self.isChecked()
        p.setBrush(QColor(MINT) if on else QColor("#FFFFFF"))
        p.setPen(QPen(QColor(COCOA) if on else QColor(74, 64, 58, 120), 1.5))
        p.drawRoundedRect(box, 5, 5)
        if on:
            tick = QPainterPath(QPointF(box.left() + 3.8, box.center().y() + 0.3))
            tick.lineTo(box.left() + 6.9, box.bottom() - 4.2)
            tick.lineTo(box.right() - 3.6, box.top() + 4.4)
            pen = QPen(QColor(COCOA), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(tick)
        p.setPen(QColor(COCOA))
        p.setFont(self.font())
        p.drawText(QRectF(26, 0, self.width() - 26, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class FocusWindow(QWidget):
    """25-minute focus session with Pause / Resume / End and an editable task.

    session_state_changed("running" | "paused" | "idle") tells the app when the
    tracker should count. session_started fires only for a brand-new session
    (not for resume) so the tracker can reset its counters.
    """

    session_state_changed = Signal(str)
    session_started = Signal()
    session_completed = Signal()
    hidden_to_tray = Signal()
    ultra_toggled = Signal(bool)
    tasks_requested = Signal()          # "My Tasks" link was clicked
    navigation_requested = Signal(str)

    def __init__(self, task=None, minutes=None):
        super().__init__()
        self.setObjectName("FocusWindow")
        self.setWindowTitle("Pawse - Focus Mode")
        self.setWindowIcon(make_paw_icon())
        self.setStyleSheet(FULL_QSS)
        self.setFixedSize(420, 760)

        # remembered between launches (session length, task, Ultra Focus)
        self.settings = QSettings("Pawse", "Pawse")
        if minutes is None:
            minutes = int(self.settings.value("minutes", SESSION_MINUTES))
        minutes = max(MIN_MINUTES, min(MAX_MINUTES, int(minutes)))
        if task is None:
            task = str(self.settings.value("task", "Finish project outline"))

        # Ultra Focus is off the first time the app runs
        self.ultra = str(self.settings.value("ultra", "false")).lower() == "true"

        self.total = minutes * 60.0
        self.remaining = self.total
        self.state = "idle"
        self._last = 0.0
        self.task = task
        self._tracker_state = "Focused"
        self._snoozed = False
        self.session_modified = False

        self._build()
        self._clock = QTimer(self)
        self._clock.setInterval(250)
        self._clock.timeout.connect(self._on_clock)
        self._clock.start()
        self._render()
        self._render_ultra()

    # ---- UI ---------------------------------------------------------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QVBoxLayout()
        body.setContentsMargins(36, 18, 36, 22)
        body.setSpacing(0)
        root.addLayout(body, 1)

        top = QHBoxLayout()
        self.tasks_btn = QPushButton("My Tasks \U0001F43E")
        self.tasks_btn.setObjectName("linkButton")
        self.tasks_btn.setCursor(Qt.PointingHandCursor)
        self.tasks_btn.setFocusPolicy(Qt.NoFocus)
        self.tasks_btn.clicked.connect(self.tasks_requested.emit)
        top.addStretch()
        top.addWidget(self.tasks_btn)
        body.addLayout(top)
        body.addSpacing(6)

        title = QLabel("Focus Mode")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel("One thing at a time, little human.")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignCenter)
        body.addWidget(title)
        body.addSpacing(4)
        body.addWidget(sub)
        body.addSpacing(18)

        self.cat = MochiCat("sleeping", width=232)
        body.addWidget(self.cat, 0, Qt.AlignHCenter)
        body.addSpacing(6)

        self.chip = QLabel("Focus: ON")
        self.chip.setObjectName("statusChip")
        body.addWidget(self.chip, 0, Qt.AlignHCenter)
        body.addSpacing(8)
        self.note = QLabel("")
        self.note.setObjectName("statusNote")
        self.note.setAlignment(Qt.AlignCenter)
        body.addWidget(self.note)

        body.addStretch(1)
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("timer")
        self.timer_label.setAlignment(Qt.AlignCenter)
        body.addWidget(self.timer_label)
        body.addSpacing(8)
        self.bar = QProgressBar()
        self.bar.setObjectName("sessionBar")
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        self.bar.setFixedWidth(220)
        body.addWidget(self.bar, 0, Qt.AlignHCenter)
        body.addSpacing(10)

        lrow = QHBoxLayout()
        lrow.setSpacing(4)
        self.minus_btn = QPushButton("\u2212")
        self.plus_btn = QPushButton("+")
        self.length_btn = QPushButton("")
        self.length_btn.setObjectName("lengthButton")
        self.length_btn.setToolTip("Click to type a session length")
        for b in (self.minus_btn, self.plus_btn):
            b.setObjectName("stepButton")
        for b in (self.minus_btn, self.plus_btn, self.length_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        self.minus_btn.clicked.connect(lambda: self.adjust_minutes(-1))
        self.plus_btn.clicked.connect(lambda: self.adjust_minutes(+1))
        self.length_btn.clicked.connect(self.type_minutes)
        lrow.addStretch()
        lrow.addWidget(self.minus_btn)
        lrow.addWidget(self.length_btn)
        lrow.addWidget(self.plus_btn)
        lrow.addStretch()
        body.addLayout(lrow)
        body.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(12)
        self.primary_btn = QPushButton("Pause")
        self.primary_btn.setObjectName("capsulePrimary")
        self.end_btn = QPushButton("End session")
        self.end_btn.setObjectName("capsule")
        for b in (self.primary_btn, self.end_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        self.primary_btn.clicked.connect(self.toggle_pause)
        self.end_btn.clicked.connect(self.end_session)
        row.addStretch()
        row.addWidget(self.primary_btn)
        row.addWidget(self.end_btn)
        row.addStretch()
        body.addLayout(row)
        body.addSpacing(12)

        self.ultra_box = CheckPill("Ultra Focus")
        self.ultra_box.setToolTip("Test mode: reminders arrive about 10x faster so you can try the whole flow.")
        self.ultra_box.setChecked(self.ultra)
        self.ultra_box.toggled.connect(self._on_ultra)
        body.addWidget(self.ultra_box, 0, Qt.AlignHCenter)
        self.ultra_hint = QLabel("")
        self.ultra_hint.setObjectName("statusNote")
        self.ultra_hint.setAlignment(Qt.AlignCenter)
        self.ultra_hint.setFixedHeight(18)
        body.addWidget(self.ultra_hint)
        body.addSpacing(14)

        # bottom bar: current task
        bar = QFrame()
        bar.setObjectName("taskBar")
        bar.setFixedHeight(76)
        h = QHBoxLayout(bar)
        h.setContentsMargins(28, 0, 24, 0)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addStretch()
        cap = QLabel("FOCUSING ON:")
        cap.setObjectName("taskCaption")
        self.task_label = QLabel(self.task)
        self.task_label.setObjectName("taskName")
        col.addWidget(cap)
        col.addWidget(self.task_label)
        col.addStretch()
        h.addLayout(col, 1)
        edit = QPushButton("Change")
        edit.setObjectName("linkButton")
        edit.setCursor(Qt.PointingHandCursor)
        edit.clicked.connect(self.edit_task)
        h.addWidget(edit)
        root.addWidget(bar)
        self.navigation = BottomNavigation("Focus", self)
        self.navigation.selected.connect(self.navigation_requested.emit)
        root.addWidget(self.navigation)

    # ---- session control --------------------------------------------------
    def start_session(self):
        self.remaining = self.total
        self.session_modified = False
        self._last = time.monotonic()
        self._set_state("paused")
        self.session_started.emit()

    def begin_focus(self, task: str):
        """From My Tasks -> 'Start Focus': adopt the task and start a fresh, running session."""
        self.set_task(task)
        self.start_session()                  # fresh countdown, tracker counters reset
        self.toggle_pause()                   # paused -> running

    def toggle_pause(self):
        if self.state == "running":
            self._set_state("paused")
        elif self.state == "paused":
            self._last = time.monotonic()
            self._set_state("running")
        else:
            self.start_session()

    def end_session(self):
        self.remaining = self.total
        self._set_state("idle")

    def _set_state(self, state):
        self.state = state
        self._render()
        self.session_state_changed.emit(state)

    def _on_clock(self):
        if self.state != "running":
            return
        now = time.monotonic()
        self.remaining -= now - self._last
        self._last = now
        if self.remaining <= 0:
            self.remaining = self.total
            self._set_state("idle")
            self.chip.setText("Session complete")
            self.note.setText("Lovely work. Mochi is proud of you.")
            self.session_completed.emit()
            return
        self._render_time()

    def set_task(self, text: str):
        """Change the 'FOCUSING ON' task (also used by My Tasks)."""
        text = (text or "").strip()
        if text:
            self.task = text
            self.task_label.setText(text)
            self.settings.setValue("task", text)

    def mark_session_modified(self):
        if self.state in ("running", "paused"):
            self.session_modified = True

    def reward_canned_fish(self):
        count = int(self.settings.value("canned_fish", 0)) + 1
        self.settings.setValue("canned_fish", count)
        return count

    def edit_task(self):
        text, ok = QInputDialog.getText(self, "Focus task", "What are we focusing on?", text=self.task)
        if ok:
            self.set_task(text)

    # ---- session length (no code edits needed) ---------------------------------
    @property
    def minutes(self):
        return int(round(self.total / 60))

    def adjust_minutes(self, direction):
        m = self.minutes
        if direction < 0:
            m = m - 5 if m > 5 else m - 1
        else:
            m = m + 1 if m < 5 else m + 5
        self.set_minutes(m)

    def type_minutes(self):
        m, ok = QInputDialog.getInt(self, "Session length", f"Minutes ({MIN_MINUTES}-{MAX_MINUTES}):",
                                    self.minutes, MIN_MINUTES, MAX_MINUTES, 1)
        if ok:
            self.set_minutes(m)

    def set_minutes(self, m):
        """Change the session length; a running/paused session shifts by the same amount."""
        m = max(MIN_MINUTES, min(MAX_MINUTES, int(m)))
        delta = m * 60.0 - self.total
        self.total = m * 60.0
        self.remaining = self.total if self.state == "idle" else max(1.0, self.remaining + delta)
        self.settings.setValue("minutes", m)
        if self.state == "idle" and self.chip.text() == "Session complete":
            self.note.setText("")
        self._render()

    # ---- Ultra Focus (test mode) ------------------------------------------------
    def set_ultra(self, on):
        self.ultra_box.setChecked(bool(on))     # fires _on_ultra if the value changed
        self._render_ultra()

    def _on_ultra(self, on):
        self.ultra = bool(on)
        self.settings.setValue("ultra", "true" if on else "false")
        self._render_ultra()
        self.ultra_toggled.emit(self.ultra)

    def _render_ultra(self):
        self.ultra_hint.setText("Test mode on: reminders come ~10x faster" if self.ultra_box.isChecked() else "")

    # ---- state from tracker -------------------------------------------------
    def apply_snapshot(self, snap: dict):
        self._tracker_state = snap["state"]
        self._snoozed = snap["snoozed"]
        self._render_note()

    # ---- rendering ----------------------------------------------------------
    def _render_time(self):
        secs = max(0, math.ceil(self.remaining))
        self.timer_label.setText(f"{secs // 60:02d}:{secs % 60:02d}")
        self.bar.setValue(max(0, min(1000, int(1000 * (1 - self.remaining / self.total)))))
        self.length_btn.setText(f"{self.minutes} min")
        self.minus_btn.setEnabled(self.minutes > MIN_MINUTES)
        self.plus_btn.setEnabled(self.minutes < MAX_MINUTES)

    def _render_note(self):
        if self.state == "paused":
            text = "Reminders are off while paused."
        elif self.state == "idle":
            text = self.note.text() if self.chip.text() == "Session complete" else "Ready when you are."
        elif self._snoozed:
            text = "Reminders snoozed for a bit."
        else:
            text = {"Focused": "Mochi is napping while you work.",
                    "Distracted": "Mochi noticed a little detour.",
                    "Away": "Looks like you stepped away."}.get(self._tracker_state, "")
        self.note.setText(text)

    def _render(self):
        mode, chip = {"running": ("on", "Focus: ON"),
                      "paused": ("paused", "Paused"),
                      "idle": ("idle", "Focus: OFF")}[self.state]
        self.chip.setText(chip)
        self.chip.setProperty("mode", mode)
        _repolish(self.chip)
        self.primary_btn.setText({"running": "Pause", "paused": "Resume", "idle": "Start"}[self.state])
        self.end_btn.setEnabled(self.state != "idle")
        self._render_time()
        self._render_note()

    # ---- tray behaviour -------------------------------------------------------
    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _to_tray(self):
        self.hide()
        self.hidden_to_tray.emit()

    def changeEvent(self, e):
        if e.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self._to_tray)
        super().changeEvent(e)

    def closeEvent(self, e):
        e.ignore()
        self._to_tray()
