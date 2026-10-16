"""Pawse (Beta) - Focus Mode + Focus Guard.

Run:  python main.py        (Windows)
Ultra Focus (checkbox in the window) = test mode with ~10x faster reminders.
PAWSE_TEST_MODE=1 starts the app with it already on.
"""

import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.tracker import HAS_WIN32, START_ULTRA, Tracker
from ui.focus_window import FocusWindow
from ui.popup import alert_popup, checkin_popup
from ui.theme import make_paw_icon


class PawseApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("Pawse")
        self.app.setQuitOnLastWindowClosed(False)   # closing the window keeps us in the tray
        self.popup = None

        self.tracker = Tracker()
        self.window = FocusWindow()

        self._setup_tray()

        self.tracker.snapshot.connect(self.window.apply_snapshot)
        self.tracker.alert.connect(self.show_alert)
        self.tracker.checkin.connect(self.show_checkin)

        self.window.ultra_toggled.connect(self.tracker.set_ultra)
        if START_ULTRA:
            self.window.set_ultra(False)
        self.tracker.set_ultra(self.window.ultra)      # restore the remembered Ultra Focus choice

        self.window.session_state_changed.connect(self.on_session_state)
        self.window.session_started.connect(self.tracker.reset_episode)
        self.window.session_completed.connect(lambda: self.tray.showMessage(
            "Pawse", "Focus session complete. Time for a little stretch!", QSystemTrayIcon.Information, 5000))
        self.window.hidden_to_tray.connect(self._tray_hint)
        self._hint_shown = False

    # ---- tray -----------------------------------------------------------------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(make_paw_icon(), self.app)
        menu = QMenu()
        menu.addAction("Open Pawse").triggered.connect(self.window.show_normal)
        self.toggle_action = menu.addAction("Pause")
        self.toggle_action.triggered.connect(self.window.toggle_pause)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(self.quit)
        self.tray.setContextMenu(menu)
        self._menu = menu
        self.tray.activated.connect(
            lambda r: self.window.show_normal() if r == QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip("Pawse - Focus Mode")
        self.tray.show()

    def _tray_hint(self):
        if not self._hint_shown:
            self._hint_shown = True
            self.tray.showMessage("Pawse", "Still watching over your focus from the tray.",
                                  QSystemTrayIcon.Information, 3000)

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
        self.popup = alert_popup(payload, self.window.task, self.tracker, self._popup_closed)

    def show_checkin(self, idle_seconds):
        self.popup = checkin_popup(idle_seconds, self._popup_closed)

    # ---- run ---------------------------------------------------------------------------
    def quit(self):
        self.tracker.stop()
        if self.popup is not None:
            self.popup.hide()
        self.tray.hide()
        self.app.quit()

    def run(self):
        if not HAS_WIN32:
            print("[Pawse] pywin32/psutil unavailable or not on Windows: monitoring is inactive.")
        signal.signal(signal.SIGINT, lambda *_: self.quit())
        self.tracker.start()
        self.window.show()
        self.window.start_session()          # Focus Mode opens with the first session running
        return self.app.exec()


if __name__ == "__main__":
    sys.exit(PawseApp().run())
