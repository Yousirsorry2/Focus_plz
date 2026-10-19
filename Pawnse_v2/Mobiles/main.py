"""Pawse (Beta) - Focus Mode + Focus Guard + My Tasks.

Run:  python main.py        (Windows)
Ultra Focus (checkbox in the window) = test mode with ~10x faster reminders.
PAWSE_TEST_MODE=1 starts the app with it already on.
PAWSE_DATA_DIR=<folder> keeps tasks.db / focus_nanny_config.json somewhere else.
"""

import datetime as dt
import sqlite3
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMenu, QStackedWidget, QSystemTrayIcon

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(REPO_DIR) not in sys.path:
    sys.path.append(str(REPO_DIR))

from core.task_store import TaskStore, due_reminders, parse_iso
from core.tracker import HAS_WIN32, START_ULTRA, Tracker, apply_user_config
from core.media_store import ensure_sound_effects
from ui.focus_window import FocusWindow
from ui.popup import MarkWorkDialog, TaskAlertPopup, alert_popup, checkin_popup
from ui.sound_effects import initialize_sound_effects
from ui.tasks_view import TasksView
from ui.theme import MOBILE_MINIMUM_WINDOW_SIZE, MOBILE_WINDOW_SIZE, make_paw_icon
from ui.utility_views import MusicView, SettingsView

REMINDER_CHECK_MS = 30_000


class PawseMainWindow(QStackedWidget):
    hidden_to_tray = Signal()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.hidden_to_tray.emit()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self._hide_to_tray)
        super().changeEvent(event)

    def _hide_to_tray(self):
        self.hide()
        self.hidden_to_tray.emit()


class PawseApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("Pawse")
        self.app.setQuitOnLastWindowClosed(False)   # closing the window keeps us in the tray
        self.popup = None
        self._task_alert_popup = None
        self._task_alert_queue = []
        try:
            ensure_sound_effects()
        except OSError as error:
            print(f"[Pawse audio] could not prepare local sound effects: {error}")
        initialize_sound_effects()

        self.store = TaskStore()
        apply_user_config(self.store.focus_rules())
        self.tracker = Tracker()
        self.tracker.rule_store = self.store
        self.window = FocusWindow()
        self.tasks = TasksView(self.store)
        self.music = MusicView()
        self.settings = SettingsView(self.tracker)
        self._screens = {"Tasks": self.tasks, "Focus": self.window,
                         "Music": self.music, "Settings": self.settings}
        self.main_window = PawseMainWindow()
        self.main_window.setWindowTitle("Pawse")
        self.main_window.setWindowIcon(make_paw_icon())
        self.main_window.setMinimumSize(*MOBILE_MINIMUM_WINDOW_SIZE)
        self.main_window.resize(*MOBILE_WINDOW_SIZE)
        for screen in self._screens.values():
            self.main_window.addWidget(screen)
        self.main_window.setCurrentWidget(self.tasks)
        self._notified = set()                       # (task id, kind, date) already reminded

        self._setup_tray()

        self.tracker.snapshot.connect(self.window.apply_snapshot)
        self.tracker.alert.connect(self.show_alert)
        self.tracker.checkin.connect(self.show_checkin)
        self.tracker.marked_work.connect(self._on_marked_work)

        self.window.ultra_toggled.connect(self.tracker.set_ultra)
        if START_ULTRA:
            self.window.set_ultra(True)
        self.tracker.set_ultra(self.window.ultra)      # restore the remembered Ultra Focus choice

        self.window.session_state_changed.connect(self.on_session_state)
        self.window.session_started.connect(self.tracker.reset_episode)
        self.window.session_completed.connect(self._on_session_completed)
        self.window.hidden_to_tray.connect(self._tray_hint)
        self.main_window.hidden_to_tray.connect(self._tray_hint)
        self._hint_shown = False

        # My Tasks <-> Focus Mode
        self.window.tasks_requested.connect(self.show_tasks)
        self.tasks.back_requested.connect(self.show_focus)
        self.tasks.start_focus.connect(self.start_focus_on_task)
        for screen in self._screens.values():
            screen.navigation_requested.connect(self.show_tab)

        self._reminder_timer = QTimer(self.app)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(REMINDER_CHECK_MS)

    # ---- tray -----------------------------------------------------------------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(make_paw_icon(), self.app)
        menu = QMenu()
        menu.addAction("Open Pawse").triggered.connect(self.show_tasks)
        menu.addAction("My Tasks").triggered.connect(self.show_tasks)
        self.toggle_action = menu.addAction("Pause")
        self.toggle_action.triggered.connect(self.window.toggle_pause)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(self.quit)
        self.tray.setContextMenu(menu)
        self._menu = menu
        self.tray.activated.connect(
            lambda r: self.show_tasks() if r == QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip("Pawse - Focus Mode")
        self.tray.show()

    def _tray_hint(self):
        if not self._hint_shown:
            self._hint_shown = True
            self.tray.showMessage("Pawse", "Still watching over your focus from the tray.",
                                  QSystemTrayIcon.Information, 3000)

    # ---- screens ----------------------------------------------------------------
    def show_tasks(self):
        self.show_tab("Tasks")

    def show_focus(self):
        self.show_tab("Focus")

    def show_tab(self, tab):
        selected = self._screens.get(tab)
        if selected is None:
            return
        self.main_window.setCurrentWidget(selected)
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def start_focus_on_task(self, title):
        """My Tasks -> Start Focus: 'FOCUSING ON: <title>' and a fresh running session."""
        self.window.begin_focus(title)
        self.show_tab("Focus")

    # ---- session <-> tracker -----------------------------------------------------
    def on_session_state(self, state):
        self.tracker.set_enabled(state == "running")
        self.toggle_action.setText({"running": "Pause", "paused": "Resume", "idle": "Start focus"}[state])
        self.tray.setToolTip({"running": "Pawse - Focus: ON", "paused": "Pawse - Paused",
                              "idle": "Pawse - Focus: OFF"}[state])
        if state != "running" and self.popup is not None:   # session ended/paused: dismiss open popup
            self.popup.finish()

    # ---- popups ----------------------------------------------------------------------
    def _popup_closed(self):
        self.popup = None
        self.tracker.popup_closed()

    def show_alert(self, payload):
        self.popup = alert_popup(payload, self.window.task, self.tracker,
                                 self._confirm_mark_as_work, self._popup_closed)

    def show_checkin(self, idle_seconds):
        self.popup = checkin_popup(idle_seconds, self._popup_closed)

    def _on_marked_work(self, label):
        self.window.mark_session_modified()
        scope = "for this focus session only" if self.tracker.last_mark_scope == "session" else "from now on"
        msg = f"Got it! \u201c{label}\u201d counts as work {scope}." if label else "Focus reminders were reset."
        self.tray.showMessage("Pawse", msg, QSystemTrayIcon.Information, 4000)

    def _confirm_mark_as_work(self):
        _, proc, _, match = self.tracker.current_target()
        target = (match or proc or "this app or site").strip()
        dialog = MarkWorkDialog(target, self.window)
        if dialog.exec() != MarkWorkDialog.Accepted:
            return
        try:
            if not self.tracker.mark_as_work(dialog.scope):
                self.tray.showMessage("Pawse", "This item cannot be allowed from the popup. Use Settings.",
                                      QSystemTrayIcon.Warning, 5000)
        except (OSError, sqlite3.Error) as error:
            print(f"[Pawse tracker] could not save work rule: {error}")
            self.tray.showMessage("Pawse", f"Could not save the work rule: {error}",
                                  QSystemTrayIcon.Warning, 6000)

    def _on_session_completed(self):
        if self.window.session_modified:
            message = "Focus session complete, but Mark as Work was used. The Canned Fish reward is forfeited."
        else:
            count = self.window.reward_canned_fish()
            message = f"Focus session complete. Canned Fish \U0001F96B earned! Total: {count}. Time to stretch."
        self.tray.showMessage("Pawse", message, QSystemTrayIcon.Information, 6000)

    # ---- task reminders ---------------------------------------------------------------
    def _check_reminders(self):
        now = dt.datetime.now()
        try:
            for task in self.store.list_tasks(completed=False):
                for kind in due_reminders(task, now):
                    key = (task["id"], kind, now.date())
                    if key in self._notified:
                        continue
                    self._notified.add(key)
                    label = kind.split(":", 1)[0]
                    scheduled_at = parse_iso(
                        task.get("deadline_time") if label == "smart" else task.get("start_time"))
                    if scheduled_at and label != "smart":
                        scheduled_at = now.replace(
                            hour=scheduled_at.hour, minute=scheduled_at.minute,
                            second=0, microsecond=0)
                    event_time = (scheduled_at.strftime("%A, %b %d at %I:%M %p")
                                  if scheduled_at else "Scheduled time unavailable")
                    self._task_alert_queue.append((task["title"], event_time))
        except Exception as e:      # a bad row must never stop the app
            print(f"[Pawse reminders] {e}")
        self._show_next_task_alert()

    def _show_next_task_alert(self):
        if self._task_alert_popup is not None or not self._task_alert_queue:
            return
        title, event_time = self._task_alert_queue.pop(0)
        self._task_alert_popup = TaskAlertPopup(title, event_time, self.window)
        self._task_alert_popup.finished.connect(self._on_task_alert_closed)
        self._task_alert_popup.show()
        self._task_alert_popup.raise_()
        self._task_alert_popup.activateWindow()

    def _on_task_alert_closed(self, _result):
        self._task_alert_popup = None
        QTimer.singleShot(0, self._show_next_task_alert)

    # ---- run ---------------------------------------------------------------------------
    def quit(self):
        self.tracker.stop()
        self._reminder_timer.stop()
        self._task_alert_queue.clear()
        if self._task_alert_popup is not None:
            self._task_alert_popup.finished.disconnect(self._on_task_alert_closed)
            self._task_alert_popup.close()
            self._task_alert_popup = None
        if self.popup is not None:
            self.popup.hide()
        self.tray.hide()
        self.main_window.hide()
        self.store.close()
        self.app.quit()

    def run(self):
        if not HAS_WIN32:
            print("[Pawse] pywin32/psutil unavailable or not on Windows: monitoring is inactive.")
        signal.signal(signal.SIGINT, lambda *_: self.quit())
        self.tracker.start()
        self.toggle_action.setText("Start focus")
        self.show_tasks()
        return self.app.exec()


if __name__ == "__main__":
    sys.exit(PawseApp().run())
