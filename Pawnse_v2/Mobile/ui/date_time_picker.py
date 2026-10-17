"""Custom pastel date and time dialogs; avoids Qt/native date-time picker widgets."""

from __future__ import annotations

import calendar
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)

from ui.tasks_theme import FULL_QSS


class CalendarPopup(QDialog):
    def __init__(self, value: dt.datetime, parent=None):
        super().__init__(parent)
        self.setObjectName("sheet")
        self.setWindowTitle("Choose a date")
        self.setStyleSheet(FULL_QSS)
        self.setModal(True)
        screen_width = QApplication.primaryScreen().availableGeometry().width()
        parent_width = parent.window().width() if parent else screen_width
        self.setFixedWidth(min(330, screen_width - 24, parent_width - 24))
        self.value = value
        self._year, self._month = value.year, value.month

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)
        header = QHBoxLayout()
        prev = QPushButton("‹ 🐾")
        prev.setToolTip("Previous month")
        prev.clicked.connect(lambda: self._change_month(-1))
        self.month_label = QLabel()
        self.month_label.setObjectName("sheetTitle")
        self.month_label.setAlignment(Qt.AlignCenter)
        nxt = QPushButton("🐾 ›")
        nxt.setToolTip("Next month")
        nxt.clicked.connect(lambda: self._change_month(1))
        for button in (prev, nxt):
            button.setObjectName("calendarArrow")
            button.setCursor(Qt.PointingHandCursor)
        header.addWidget(prev)
        header.addWidget(self.month_label, 1)
        header.addWidget(nxt)
        root.addLayout(header)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(4)
        self.grid.setVerticalSpacing(5)
        root.addLayout(self.grid)
        self._render_month()

    def _change_month(self, delta):
        month = self._month + delta
        year = self._year
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        self._year, self._month = year, month
        self._render_month()

    def _render_month(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.month_label.setText(f"{calendar.month_name[self._month]} {self._year}")
        for column, day in enumerate(("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")):
            label = QLabel(day)
            label.setObjectName("calendarWeekday")
            label.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(label, 0, column)
        month = calendar.Calendar(firstweekday=6).monthdayscalendar(self._year, self._month)
        for row, week in enumerate(month, 1):
            for column, day in enumerate(week):
                if not day:
                    self.grid.addWidget(QLabel(""), row, column)
                    continue
                button = QPushButton(str(day))
                button.setObjectName("calendarDay")
                button.setCheckable(True)
                button.setChecked((self._year, self._month, day) ==
                                  (self.value.year, self.value.month, self.value.day))
                button.setCursor(Qt.PointingHandCursor)
                button.clicked.connect(lambda _=False, d=day: self._select_day(d))
                self.grid.addWidget(button, row, column)

    def _select_day(self, day):
        self.value = self.value.replace(year=self._year, month=self._month, day=day)
        self.accept()


class TimePicker(QDialog):
    def __init__(self, value: dt.datetime, parent=None):
        super().__init__(parent)
        self.setObjectName("sheet")
        self.setWindowTitle("Choose a time")
        self.setStyleSheet(FULL_QSS)
        self.setModal(True)
        screen_width = QApplication.primaryScreen().availableGeometry().width()
        parent_width = parent.window().width() if parent else screen_width
        self.setFixedWidth(min(300, screen_width - 24, parent_width - 24))
        self.value = value

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)
        title = QLabel("Choose a time")
        title.setObjectName("sheetTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)
        row = QHBoxLayout()
        self.hour = TimeSelector(value.hour % 12 or 12, 1, 12)
        colon = QLabel(":")
        colon.setObjectName("sheetTitle")
        self.minute = TimeSelector(value.minute, 0, 59)
        self.ampm = QButtonGroup(self)
        am = QPushButton("AM")
        pm = QPushButton("PM")
        for button in (am, pm):
            button.setCheckable(True)
            button.setObjectName("timePeriod")
        self.ampm.addButton(am)
        self.ampm.addButton(pm)
        (pm if value.hour >= 12 else am).setChecked(True)
        row.addStretch()
        row.addWidget(self.hour)
        row.addWidget(colon)
        row.addWidget(self.minute)
        period = QVBoxLayout()
        period.setSpacing(4)
        period.addWidget(am)
        period.addWidget(pm)
        row.addLayout(period)
        row.addStretch()
        root.addLayout(row)
        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        save = QPushButton("Set time")
        cancel.setObjectName("capsule")
        save.setObjectName("capsulePrimary")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._accept)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _accept(self):
        hour = self.hour.value % 12 + (12 if self.ampm.checkedButton().text() == "PM" else 0)
        self.value = self.value.replace(hour=hour, minute=self.minute.value, second=0, microsecond=0)
        self.accept()


class TimeSelector(QWidget):
    def __init__(self, value: int, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self.value = value
        self.minimum = minimum
        self.maximum = maximum

        row = QVBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.setAlignment(Qt.AlignCenter)  # จัดการจัดวางภายใน Layout ทั้งหมดให้อยู่ตรงกลาง

        previous = QPushButton(" ^ ")
        following = QPushButton(" v ")

        self.label = QLabel()
        self.label.setObjectName("timeValue")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedWidth(34)

        for button, delta in ((previous, -1), (following, 1)):
            button.setObjectName("timeStep")
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedWidth(34)  # กำหนดความกว้างให้เท่ากับ label (34px)
            button.clicked.connect(lambda _=False, step=delta: self._step(step))

        # จัด Align Widget แต่ละตัวให้อยู่ตรงกลางแนวนอน
        row.addWidget(previous, alignment=Qt.AlignCenter)
        row.addWidget(self.label, alignment=Qt.AlignCenter)
        row.addWidget(following, alignment=Qt.AlignCenter)

        self._refresh()

    def _step(self, delta):
        self.value = self.minimum + (self.value - self.minimum + delta) % (
            self.maximum - self.minimum + 1)
        self._refresh()

    def _refresh(self):
        self.label.setText(f"{self.value:02d}")


class DateTimeButton(QPushButton):
    """A field-like button that independently edits the date or time of a datetime."""

    def __init__(self, value: dt.datetime, mode: str, parent=None):
        super().__init__(parent)
        self.value = value
        self.mode = mode
        self.setObjectName("dateTimeField")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._choose)
        self._refresh()

    def _choose(self):
        picker = CalendarPopup(self.value, self) if self.mode == "date" else TimePicker(self.value, self)
        if picker.exec() == QDialog.Accepted:
            self.value = picker.value
            self._refresh()

    def _refresh(self):
        self.setText(f"  {self.value:%a, %d %b %Y}" if self.mode == "date"
                     else f"  {self.value:%I:%M %p}")
