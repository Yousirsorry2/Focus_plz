"""Pawse - "Add / Edit Task" sheet (modal)."""

from __future__ import annotations

import datetime as dt
import os
import tempfile

from PySide6.QtCore import QLocale, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractSpinBox, QButtonGroup, QCheckBox, QColorDialog, QComboBox,
                               QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QVBoxLayout, QWidget)

from core.task_store import DEFAULT_REMINDER_PRESETS, FREQUENCIES, SWATCHES, parse_iso
from ui.date_time_picker import DateTimeButton
from ui.tasks_theme import FULL_QSS
from ui.theme import COCOA
from ui.widgets import ToggleSwitch


def _next_half_hour() -> dt.datetime:
    n = dt.datetime.now().replace(second=0, microsecond=0)
    return n + dt.timedelta(minutes=30 - n.minute % 30)


def _caption(text):
    lab = QLabel(text)
    lab.setObjectName("fieldCaption")
    return lab


# ---- minimal style for checkboxes / combo boxes / spin box --------------------
def _make_icons():
    """Draw the tick + chevron icons once and return their file paths."""
    folder = os.path.join(tempfile.gettempdir(), "pawse_icons")
    os.makedirs(folder, exist_ok=True)

    def save(name, size, color, points, width):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(x, y) for x, y in points])
        p.end()
        path = os.path.join(folder, name)
        pm.save(path)
        return path.replace("\\", "/")

    check = save("check.png", 16, "#FFFFFF", [(4, 8.5), (7, 11.5), (12, 5)], 2)
    chevron = save("chevron.png", 10, COCOA, [(2, 3.5), (5, 6.5), (8, 3.5)], 1.5)
    return check, chevron


def _minimal_qss():
    check, chevron = _make_icons()
    line = "rgba(74,64,58,0.28)"
    return f"""
    QDialog#sheet QCheckBox {{
        spacing: 8px; color: {COCOA}; font-size: 12px; background: transparent;
    }}
    QDialog#sheet QCheckBox:disabled {{ color: rgba(74,64,58,0.4); }}
    QDialog#sheet QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 5px;
        border: 1.5px solid {line}; background: transparent;
    }}
    QDialog#sheet QCheckBox::indicator:hover {{ border-color: {COCOA}; }}
    QDialog#sheet QCheckBox::indicator:checked {{
        background: {COCOA}; border-color: {COCOA}; image: url({check});
    }}
    QDialog#sheet QCheckBox::indicator:disabled {{
        border-color: rgba(74,64,58,0.15); background: transparent;
    }}
    QDialog#sheet QCheckBox::indicator:checked:disabled {{
        background: rgba(74,64,58,0.3); border-color: transparent;
    }}
    QDialog#sheet QCheckBox#customReminderCheck {{ min-width: 70px; }}

    QDialog#sheet QSpinBox, QDialog#sheet QComboBox {{
        background: transparent; color: {COCOA}; font-size: 12px;
        border: 1.5px solid {line}; border-radius: 10px;
        padding: 3px 10px; min-height: 22px;
    }}
    QDialog#sheet QSpinBox:hover, QDialog#sheet QComboBox:hover,
    QDialog#sheet QSpinBox:focus, QDialog#sheet QComboBox:focus {{ border-color: {COCOA}; }}
    QDialog#sheet QSpinBox:disabled, QDialog#sheet QComboBox:disabled {{
        color: rgba(74,64,58,0.4); border-color: rgba(74,64,58,0.15);
    }}
    QDialog#sheet QComboBox::drop-down {{ border: none; width: 24px; }}
    QDialog#sheet QComboBox::down-arrow {{ image: url({chevron}); width: 10px; height: 10px; }}
    QDialog#sheet QComboBox QAbstractItemView {{
        background: white; color: {COCOA}; border: 1px solid {line};
        selection-background-color: rgba(74,64,58,0.08); selection-color: {COCOA};
        outline: 0; padding: 4px;
    }}
    """


class NewCategoryDialog(QDialog):
    """Name + colour for a custom category tag."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sheet")
        self.setWindowTitle("New category")
        self.setStyleSheet(FULL_QSS)
        self.setModal(True)
        self.setFixedWidth(340)
        self.color = SWATCHES[0]
        self.name = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(0)
        t = QLabel("New category")
        t.setObjectName("sheetTitle")
        lay.addWidget(t)
        lay.addSpacing(14)
        self.edit = QLineEdit()
        self.edit.setObjectName("taskInput")
        self.edit.setPlaceholderText("e.g. Health, Chores, Side project")
        self.edit.setMaxLength(20)
        self.edit.textChanged.connect(self._sync)
        lay.addWidget(self.edit)
        lay.addSpacing(14)
        lay.addWidget(_caption("COLOR"))
        lay.addSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.group = QButtonGroup(self)
        self._swatches = []
        for i, c in enumerate(SWATCHES):
            self._add_swatch(row, c, checked=(i == 0))
        more = QPushButton("+")
        more.setObjectName("swatchMore")
        more.setToolTip("Pick a custom colour")
        more.setCursor(Qt.PointingHandCursor)
        more.setFocusPolicy(Qt.NoFocus)
        more.clicked.connect(self._custom_color)
        row.addWidget(more)
        row.addStretch()
        self._row = row
        lay.addLayout(row)
        lay.addSpacing(18)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("capsule")
        self.ok = QPushButton("Add")
        self.ok.setObjectName("capsulePrimary")
        self.ok.setDefault(True)
        for b in (cancel, self.ok):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self._accept)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(self.ok)
        lay.addLayout(btns)
        self._sync()

    def _add_swatch(self, row, color, checked=False, insert=False):
        b = QPushButton()
        b.setCheckable(True)
        b.setChecked(checked)
        b.setFixedSize(30, 30)
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        b.setStyleSheet(f"QPushButton{{background:{color};border:1.5px solid rgba(74,64,58,0.18);"
                        f"border-radius:15px;}} QPushButton:checked{{border:2.5px solid {COCOA};}}")
        b.clicked.connect(lambda _=False, c=color: setattr(self, "color", c))
        self.group.addButton(b)
        if insert:
            row.insertWidget(row.count() - 2, b)   # before the "+" button and the stretch
        else:
            row.addWidget(b)
        if checked:
            self.color = color

    def _custom_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Pick a category colour")
        if c.isValid():
            self.color = c.name().upper()
            self._add_swatch(self._row, self.color, checked=True, insert=True)

    def _sync(self):
        self.ok.setEnabled(bool(self.edit.text().strip()))

    def _accept(self):
        self.name = self.edit.text().strip()
        if self.name:
            self.accept()


class AddTaskDialog(QDialog):
    """Create (task=None) or edit (task=dict) a task. Read the result with task_data()."""

    def __init__(self, store, task=None, parent=None):
        super().__init__(parent)

        self.store = store
        self.task = task
        self._data = None
        self.setObjectName("sheet")
        self.setWindowTitle("Edit task" if task else "Add a task")
        self.setStyleSheet(FULL_QSS + _minimal_qss())
        self.setModal(True)
        self.setFixedWidth(520)

        cats = store.list_categories()
        self._cat = task["category_name"] if task else cats[0]["name"]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 22)
        lay.setSpacing(0)

        title = QLabel("Edit task \U0001F43E" if task else "Add a task \U0001F43E")
        title.setObjectName("sheetTitle")
        lay.addWidget(title)
        lay.addSpacing(16)

        self.input = QLineEdit(task["title"] if task else "")
        self.input.setObjectName("taskInput")
        self.input.setPlaceholderText("What are we doing today?")
        self.input.setMaxLength(120)
        self.input.textChanged.connect(self._sync_save)
        lay.addWidget(self.input)
        lay.addSpacing(18)

        lay.addWidget(_caption("CATEGORY"))
        lay.addSpacing(8)
        self.cat_wrap = QWidget()
        self.cat_grid = QGridLayout(self.cat_wrap)
        self.cat_grid.setContentsMargins(0, 0, 0, 0)
        self.cat_grid.setSpacing(8)
        lay.addWidget(self.cat_wrap)
        self._rebuild_categories()
        lay.addSpacing(18)

        # ---- reminder -----------------------------------------------------
        start = parse_iso(task["start_time"]) if task else _next_half_hour()
        r = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel("Remind me")
        t.setObjectName("fieldTitle")
        h = QLabel("A gentle nudge from Mochi at this time")
        h.setObjectName("fieldHint")
        col.addWidget(t)
        col.addWidget(h)
        r.addLayout(col, 1)
        self.remind = ToggleSwitch(start is not None)
        r.addWidget(self.remind)
        lay.addLayout(r)
        lay.addSpacing(8)
        start_value = start or _next_half_hour()
        start_row = QHBoxLayout()
        self.start_date = DateTimeButton(start_value, "date")
        self.start_time = DateTimeButton(start_value, "time")
        start_row.addWidget(self.start_date, 3)
        start_row.addWidget(self.start_time, 2)
        lay.addLayout(start_row)
        lay.addSpacing(10)

        lay.addWidget(_caption("ADVANCE REMINDERS"))
        lay.addSpacing(5)
        reminder_values = set(DEFAULT_REMINDER_PRESETS + store.reminder_presets())
        if task:
            reminder_values.update(task.get("reminder_minutes", []))
        reminder_values = sorted(reminder_values, reverse=True)
        reminder_grid = QGridLayout()
        reminder_grid.setHorizontalSpacing(8)
        reminder_grid.setVerticalSpacing(6)
        selected_reminders = set(task.get("reminder_minutes", [0])) if task else {0}
        self.reminder_checks = {}
        for index, minutes in enumerate(reminder_values):
            check = QCheckBox(self._reminder_label(minutes))
            check.setChecked(minutes in selected_reminders)
            check.setCursor(Qt.PointingHandCursor)
            self.reminder_checks[minutes] = check
            reminder_grid.addWidget(check, index // 3, index % 3)
        lay.addLayout(reminder_grid)
        lay.addSpacing(6)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        self.custom_reminder = QCheckBox("Custom")
        self.custom_reminder.setObjectName("customReminderCheck")
        self.custom_reminder.setCursor(Qt.PointingHandCursor)

        self.custom_minutes = QSpinBox()
        self.custom_minutes.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))  # no Thai digits
        self.custom_minutes.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.custom_minutes.setAlignment(Qt.AlignCenter)
        self.custom_minutes.setRange(1, 999)
        self.custom_minutes.setValue(3)
        self.custom_minutes.setFixedWidth(60)

        self.custom_unit = QComboBox()
        self.custom_unit.setMinimumWidth(100)
        self.custom_unit.addItem("minutes", 1)
        self.custom_unit.addItem("hours", 60)
        self.custom_unit.addItem("days", 1440)

        self.save_custom_preset = QCheckBox("Save custom preset to app")
        self.save_custom_preset.setToolTip("Otherwise, use this reminder for this task only.")
        self.save_custom_preset.setCursor(Qt.PointingHandCursor)
        self.custom_reminder.toggled.connect(self._sync_custom_reminder)
        custom_row.addWidget(self.custom_reminder)
        custom_row.addWidget(self.custom_minutes)
        custom_row.addWidget(self.custom_unit)
        custom_row.addStretch()
        lay.addLayout(custom_row)
        lay.addSpacing(6)
        lay.addWidget(self.save_custom_preset)
        task_only_hint = QLabel("Unchecked: use this custom reminder for this task only.")
        task_only_hint.setObjectName("fieldHint")
        lay.addWidget(task_only_hint)
        lay.addSpacing(10)

        rep = QHBoxLayout()
        rl = QLabel("Repeat")
        rl.setObjectName("fieldTitle")
        self.freq = QComboBox()
        self.freq.addItems(FREQUENCIES)
        if task and task["frequency"] in FREQUENCIES:
            self.freq.setCurrentText(task["frequency"])
        rep.addWidget(rl)
        rep.addStretch()
        rep.addWidget(self.freq)
        lay.addLayout(rep)
        lay.addSpacing(18)

        # ---- smart deadline -------------------------------------------------
        sd = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel("Smart Deadline")
        t.setObjectName("fieldTitle")
        self.sd_hint = QLabel("")
        self.sd_hint.setObjectName("fieldHint")
        col.addWidget(t)
        col.addWidget(self.sd_hint)
        sd.addLayout(col, 1)
        self.smart = ToggleSwitch(bool(task and task["is_smart_deadline"]))
        sd.addWidget(self.smart)
        lay.addLayout(sd)
        lay.addSpacing(8)
        dl = parse_iso(task["deadline_time"]) if task else None
        deadline_value = dl or (start_value + dt.timedelta(hours=1))
        deadline_row = QHBoxLayout()
        self.deadline_date = DateTimeButton(deadline_value, "date")
        self.deadline_time = DateTimeButton(deadline_value, "time")
        deadline_row.addWidget(self.deadline_date, 3)
        deadline_row.addWidget(self.deadline_time, 2)
        lay.addLayout(deadline_row)

        self.error = QLabel("")
        self.error.setObjectName("formError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addSpacing(10)
        lay.addWidget(self.error)
        lay.addSpacing(18)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("capsule")
        self.save_btn = QPushButton("Save changes" if task else "Add task")
        self.save_btn.setObjectName("capsulePrimary")
        self.save_btn.setDefault(True)
        for b in (cancel, self.save_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        cancel.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(cancel)
        btns.addWidget(self.save_btn)
        lay.addLayout(btns)

        self.remind.toggled.connect(self._sync_remind)
        self.smart.toggled.connect(self._sync_smart)
        self._sync_remind()
        self._sync_smart()
        self._sync_custom_reminder()
        self._sync_save()
        self.input.setFocus()

    # ---- categories ---------------------------------------------------------
    def _rebuild_categories(self):
        while self.cat_grid.count():
            w = self.cat_grid.takeAt(0).widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)
        cols = 3
        cats = self.store.list_categories()
        for i, c in enumerate(cats):
            b = QPushButton(c["name"])
            b.setCheckable(True)
            b.setChecked(c["name"] == self._cat)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setStyleSheet(
                f"QPushButton{{background:{c['color']};border:1.5px solid transparent;border-radius:14px;"
                f"padding:0 14px;min-height:28px;font-size:12px;font-weight:600;}}"
                f"QPushButton:checked{{border:1.5px solid {COCOA};}}")
            b.clicked.connect(lambda _=False, n=c["name"]: setattr(self, "_cat", n))
            self.cat_group.addButton(b)
            self.cat_grid.addWidget(b, i // cols, i % cols)
        add = QPushButton("+ Add Category")
        add.setObjectName("chipAdd")
        add.setCursor(Qt.PointingHandCursor)
        add.setFocusPolicy(Qt.NoFocus)
        add.clicked.connect(self._new_category)
        n = len(cats)
        self.cat_grid.addWidget(add, n // cols, n % cols)

    def _new_category(self):
        dlg = NewCategoryDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.name:
            self.store.add_category(dlg.name, dlg.color)
            self._cat = dlg.name
            QTimer.singleShot(0, self._rebuild_categories)   # the clicked button is about to be replaced

    # ---- toggles -----------------------------------------------------------
    def _sync_remind(self):
        on = self.remind.isChecked()
        self.start_date.setEnabled(on)
        self.start_time.setEnabled(on)
        self.freq.setEnabled(on)
        for check in self.reminder_checks.values():
            check.setEnabled(on)
        self.custom_reminder.setEnabled(on)
        self.custom_minutes.setEnabled(on and self.custom_reminder.isChecked())
        self.custom_unit.setEnabled(on and self.custom_reminder.isChecked())
        self.save_custom_preset.setEnabled(on and self.custom_reminder.isChecked())
        if not on:
            self.freq.setCurrentText("Once")

    def _sync_custom_reminder(self):
        enabled = self.remind.isChecked() and self.custom_reminder.isChecked()
        self.custom_minutes.setEnabled(enabled)
        self.custom_unit.setEnabled(enabled)
        self.save_custom_preset.setEnabled(enabled)

    def _sync_smart(self):
        on = self.smart.isChecked()
        self.deadline_date.setVisible(on)
        self.deadline_time.setVisible(on)
        self.sd_hint.setText("Mochi sends 9 gentle milestone alerts before the deadline" if on
                             else "Optional: add a due time and Mochi keeps watch")
        if on and self.remind.isChecked() and self._deadline_value() <= self._start_value():
            value = self._start_value() + dt.timedelta(hours=1)
            self.deadline_date.value = value
            self.deadline_date._refresh()
            self.deadline_time.value = value
            self.deadline_time._refresh()
        self.error.hide()
        self.adjustSize()

    def _sync_save(self):
        self.save_btn.setEnabled(bool(self.input.text().strip()))

    # ---- result ---------------------------------------------------------------
    def _save(self):
        title = self.input.text().strip()
        if not title:
            return
        start = self._start_value() if self.remind.isChecked() else None
        smart = self.smart.isChecked()
        deadline = self._deadline_value() if smart else None
        if smart and start and deadline <= start:
            self.error.setText("The deadline needs to be after the start time.")
            self.error.show()
            self.adjustSize()
            return
        reminders = [minutes for minutes, check in self.reminder_checks.items() if check.isChecked()]
        custom_minutes = self._custom_reminder_minutes() if self.custom_reminder.isChecked() else None
        if custom_minutes is not None:
            reminders.append(custom_minutes)
            if self.save_custom_preset.isChecked():
                self.store.add_reminder_preset(custom_minutes)
        self._data = {
            "title": title,
            "category_name": self._cat,
            "category_color": self.store.category_color(self._cat),
            "start_time": start.isoformat(timespec="minutes") if start else None,
            "frequency": self.freq.currentText() if start else "Once",
            "is_smart_deadline": smart,
            "deadline_time": deadline.isoformat(timespec="minutes") if deadline else None,
            "reminder_minutes": sorted(set(reminders), reverse=True),
        }
        self.accept()

    def _start_value(self):
        return self.start_date.value.replace(hour=self.start_time.value.hour,
                                             minute=self.start_time.value.minute, second=0, microsecond=0)

    def _deadline_value(self):
        return self.deadline_date.value.replace(hour=self.deadline_time.value.hour,
                                                minute=self.deadline_time.value.minute, second=0, microsecond=0)

    def _custom_reminder_minutes(self):
        return self.custom_minutes.value() * self.custom_unit.currentData()

    @staticmethod
    def _reminder_label(minutes: int) -> str:

        labels = {
            0: "At event time",
            5: "5 min before",
            15: "15 min before",
            30: "30 min before",
            60: "1 hr before",
            120: "2 hrs before",
            1440: "1 day before",
            2880: "2 days before",
            10080: "7 days before"
        }
        if minutes in labels:
            return labels[minutes]

        if minutes % 1440 == 0:
            return f"{minutes // 1440} days before"
        if minutes % 60 == 0:
            return f"{minutes // 60} hrs before"
        return f"{minutes} min before"

    def task_data(self):
        return self._data