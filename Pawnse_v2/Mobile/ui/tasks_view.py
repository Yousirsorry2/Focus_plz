"""Pawse - "My Tasks" screen (offline to-do list backed by core.task_store)."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QMenu,
                               QMessageBox, QProgressBar, QPushButton, QScrollArea, QToolButton,
                               QVBoxLayout, QWidget)

from PC.core.task_store import parse_iso
from ui.add_task_dialog import AddTaskDialog
from ui.tasks_theme import FULL_QSS
from ui.theme import PEACH_HOVER, make_paw_icon
from ui.widgets import PawCheck
from ui.navigation import BottomNavigation


def _repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _pill(text, bg):
    lab = QLabel(text)
    lab.setObjectName("pill")
    lab.setStyleSheet(f"background: {bg}; border-radius: 9px; padding: 2px 10px; font-size: 11px; font-weight: 600;")
    return lab


def when_text(task):
    start = parse_iso(task["start_time"])
    if not start:
        return None
    if task["frequency"] != "Once":
        return f"\U0001F501 {task['frequency']} {start:%H:%M}"
    today = dt.date.today()
    day = ("Today" if start.date() == today else
           "Tomorrow" if start.date() == today + dt.timedelta(days=1) else f"{start:%a %d %b}")
    return f"\u23F0 {day} {start:%H:%M}"


def deadline_pill(task):
    """(text, bg) for the Smart Deadline cat indicator, or None."""
    if not task["is_smart_deadline"]:
        return None
    d = parse_iso(task["deadline_time"])
    if not d:
        return None
    if not task["is_completed"] and d < dt.datetime.now():
        return "\U0001F431 overdue", PEACH_HOVER
    return f"\U0001F431 due {d:%a %H:%M}", "#FFF1B8"


class TaskCard(QFrame):
    clicked = Signal(int)
    toggled = Signal(int, bool)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, task, selected=False):
        super().__init__()
        self.task_id = task["id"]
        done = task["is_completed"]
        self.setObjectName("taskCard")
        self.setProperty("done", done)
        self.setProperty("selected", selected)
        self.setCursor(Qt.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 12, 10, 12)
        h.setSpacing(12)

        self.check = PawCheck()
        self.check.setChecked(done)
        self.check.setToolTip("Mark as not done" if done else "Mark as done")
        self.check.clicked.connect(lambda checked: self.toggled.emit(self.task_id, checked))
        h.addWidget(self.check, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(6)
        title = QLabel(task["title"])
        title.setObjectName("cardTitle")
        title.setProperty("done", done)
        title.setWordWrap(True)
        col.addWidget(title)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(_pill(task["category_name"], task["category_color"]))
        when = when_text(task)
        if when:
            row1.addWidget(_pill(when, "rgba(74,64,58,0.08)"))
        row1.addStretch()
        col.addLayout(row1)
        dl = deadline_pill(task)
        if dl:
            row2 = QHBoxLayout()
            row2.addWidget(_pill(*dl))
            row2.addStretch()
            col.addLayout(row2)
        h.addLayout(col, 1)

        more = QToolButton()
        more.setObjectName("moreButton")
        more.setText("\u22EF")
        more.setCursor(Qt.PointingHandCursor)
        more.setFocusPolicy(Qt.NoFocus)
        more.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(more)
        menu.addAction("Edit").triggered.connect(lambda: self.edit_requested.emit(self.task_id))
        menu.addAction("Delete").triggered.connect(lambda: self.delete_requested.emit(self.task_id))
        more.setMenu(menu)
        h.addWidget(more, 0, Qt.AlignTop)

    def set_selected(self, on):
        self.setProperty("selected", on)
        _repolish(self)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.task_id)
        super().mousePressEvent(e)


class TasksView(QWidget):
    """My Tasks: category chips, task cards, collapsible Completed section, Add + Start Focus."""

    start_focus = Signal(str)      # task title -> Focus Mode "FOCUSING ON: ..."
    back_requested = Signal()
    navigation_requested = Signal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.filter = "All"
        self.selected_id = None
        self.completed_open = False
        self.cards = {}
        self._chip_names = []

        self.setObjectName("TasksWindow")
        self.setWindowTitle("Pawse - My Tasks")
        self.setWindowIcon(make_paw_icon())
        self.setStyleSheet(FULL_QSS)
        self.resize(390, 844)
        self.setMinimumSize(320, 600)
        self._build()
        self.refresh()

    # ---- layout ---------------------------------------------------------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 0)
        root.setSpacing(0)

        head = QVBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)

        trow = QHBoxLayout()
        title = QLabel("My Tasks \U0001F43E")
        title.setObjectName("title")
        self.add_btn = QPushButton("+ Add a task")
        self.add_btn.setObjectName("capsulePrimary")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFocusPolicy(Qt.NoFocus)
        self.add_btn.clicked.connect(self.add_task)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("statusChip")
        trow.addWidget(title)
        trow.addStretch()
        trow.addWidget(self.add_btn)
        head.addLayout(trow)
        head.addSpacing(4)
        summary = QHBoxLayout()
        date_label = QLabel(dt.date.today().strftime("%A, %B %d"))
        date_label.setObjectName("subtitle")
        summary.addWidget(date_label)
        summary.addStretch()
        summary.addWidget(self.progress_label, 0, Qt.AlignVCenter)
        head.addLayout(summary)
        self.bar = QProgressBar()
        self.bar.setObjectName("sessionBar")
        self.bar.setTextVisible(False)
        head.addWidget(self.bar)
        head.addSpacing(12)
        root.addLayout(head)

        # category chips (scroll sideways if the user adds many categories)
        self.chip_scroll = QScrollArea()
        self.chip_scroll.setWidgetResizable(True)
        self.chip_scroll.setFrameShape(QFrame.NoFrame)
        self.chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chip_scroll.setFixedHeight(48)
        self.chip_host = QWidget()
        self.chip_lay = QHBoxLayout(self.chip_host)
        self.chip_lay.setContentsMargins(0, 0, 0, 6)
        self.chip_lay.setSpacing(6)
        self.chip_scroll.setWidget(self.chip_host)
        root.addWidget(self.chip_scroll)

        # task list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        self.list_lay = QVBoxLayout(host)
        self.list_lay.setContentsMargins(0, 4, 0, 12)
        self.list_lay.setSpacing(10)
        self.scroll.setWidget(host)
        root.addWidget(self.scroll, 1)

        # Keep the selected-task action above the fixed mobile tab bar.
        bar = QFrame()
        bar.setObjectName("taskBar")
        bar.setFixedHeight(62)
        b = QHBoxLayout(bar)
        b.setContentsMargins(10, 6, 10, 6)
        b.setSpacing(8)
        self.start_btn = QPushButton("Start Focus")
        self.start_btn.setObjectName("capsulePrimary")
        self.start_btn.setToolTip("Select a task, then start a focus session on it")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFocusPolicy(Qt.NoFocus)
        self.start_btn.clicked.connect(self._start_focus)
        b.addWidget(self.start_btn, 1)
        root.addWidget(bar)
        self.navigation = BottomNavigation("Tasks", self)
        self.navigation.selected.connect(self.navigation_requested.emit)
        root.addWidget(self.navigation)

    # ---- chips ---------------------------------------------------------------------
    def _sync_chips(self):
        names = ["All"] + [c["name"] for c in self.store.list_categories()]
        if names != self._chip_names:               # rebuild only when categories changed
            _clear(self.chip_lay)
            self._chip_group = QButtonGroup(self)
            self._chip_group.setExclusive(True)
            self._chips = {}
            for n in names:
                c = QPushButton(n)
                c.setObjectName("chip")
                c.setCheckable(True)
                c.setCursor(Qt.PointingHandCursor)
                c.setFocusPolicy(Qt.NoFocus)
                c.clicked.connect(lambda _=False, n=n: self._set_filter(n))
                self._chip_group.addButton(c)
                self.chip_lay.addWidget(c)
                self._chips[n] = c
            self.chip_lay.addStretch()
            self._chip_names = names
        if self.filter not in self._chips:
            self.filter = "All"
        self._chips[self.filter].setChecked(True)

    def _set_filter(self, name):
        self.filter = name
        self.refresh()

    # ---- list ---------------------------------------------------------------------
    def refresh(self):
        done, total = self.store.counts()
        self.progress_label.setText(f"{done} of {total} done")
        self.bar.setRange(0, max(total, 1))
        self.bar.setValue(done)
        self._sync_chips()

        _clear(self.list_lay)
        self.cards = {}
        open_tasks = self.store.list_tasks(self.filter, completed=False)
        done_tasks = self.store.list_tasks(self.filter, completed=True)

        for t in open_tasks:
            self._add_card(t)
        if not open_tasks:
            msg = ("All caught up! \U0001F389" if done_tasks else
                   "Nothing here yet.\nAdd a task and Mochi will cheer you on \U0001F43E")
            note = QLabel(msg)
            note.setObjectName("emptyNote")
            note.setAlignment(Qt.AlignCenter)
            note.setContentsMargins(0, 36, 0, 24)
            self.list_lay.addWidget(note)

        if done_tasks:
            arrow = "\u25BE" if self.completed_open else "\u25B8"
            acc = QPushButton(f"{arrow}  Completed Tasks ({len(done_tasks)})")
            acc.setObjectName("accordion")
            acc.setCursor(Qt.PointingHandCursor)
            acc.setFocusPolicy(Qt.NoFocus)
            acc.clicked.connect(self._toggle_completed)
            self.list_lay.addWidget(acc)
            if self.completed_open:
                for t in done_tasks:
                    self._add_card(t)
        self.list_lay.addStretch(1)

        if self.selected_id not in self.cards:
            self.selected_id = None
        self._sync_start()

    def _add_card(self, task):
        card = TaskCard(task, selected=(task["id"] == self.selected_id))
        card.clicked.connect(self._select)
        card.toggled.connect(self._toggle)
        card.edit_requested.connect(self.edit_task)
        card.delete_requested.connect(self.delete_task)
        self.cards[task["id"]] = card
        self.list_lay.addWidget(card)

    def _later(self):
        QTimer.singleShot(0, self.refresh)    # sender widgets get rebuilt, so defer one tick

    def _toggle_completed(self):
        self.completed_open = not self.completed_open
        self._later()

    def _select(self, task_id):
        self.selected_id = None if self.selected_id == task_id else task_id
        for tid, card in self.cards.items():
            card.set_selected(tid == self.selected_id)
        self._sync_start()

    def _sync_start(self):
        task = self.store.get_task(self.selected_id) if self.selected_id else None
        ok = bool(task) and not task["is_completed"]
        self.start_btn.setEnabled(ok)

    # ---- actions (each one hits the database immediately) -----------------------------------
    def _toggle(self, task_id, done):
        self.store.set_completed(task_id, done)
        self._later()

    def add_task(self):
        dlg = AddTaskDialog(self.store, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.task_data():
            self.store.add_task(**dlg.task_data())
        self._later()          # categories may have been added even if the sheet was cancelled

    def edit_task(self, task_id):
        task = self.store.get_task(task_id)
        if not task:
            return
        dlg = AddTaskDialog(self.store, task=task, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.task_data():
            self.store.update_task(task_id, **dlg.task_data())
        self._later()

    def delete_task(self, task_id):
        task = self.store.get_task(task_id)
        if not task:
            return
        box = QMessageBox(QMessageBox.Question, "Delete task", f"Delete \u201c{task['title']}\u201d?",
                          QMessageBox.Yes | QMessageBox.No, self)
        box.setDefaultButton(QMessageBox.No)
        if box.exec() == QMessageBox.Yes:
            self.store.delete_task(task_id)
            if self.selected_id == task_id:
                self.selected_id = None
        self._later()

    def _start_focus(self):
        task = self.store.get_task(self.selected_id) if self.selected_id else None
        if task and not task["is_completed"]:
            self.start_focus.emit(task["title"])

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)
