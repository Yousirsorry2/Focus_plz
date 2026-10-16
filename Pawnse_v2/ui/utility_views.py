"""Small Music and Settings destinations for the shared bottom navigation."""

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (QFrame, QLabel, QLineEdit,
                               QPushButton, QRadioButton, QVBoxLayout, QWidget)

from core.config import load_config
from ui.navigation import BottomNavigation
from ui.tasks_theme import FULL_QSS
from ui.theme import make_paw_icon


class _NavigationPage(QWidget):
    navigation_requested = Signal(str)

    def __init__(self, active):
        super().__init__()
        self.setObjectName("TasksWindow")
        self.setWindowTitle(f"Pawse - {active}")
        self.setWindowIcon(make_paw_icon())
        self.setStyleSheet(FULL_QSS)
        self.setFixedSize(420, 760)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(24, 24, 24, 0)
        self.root.addStretch(1)
        self.navigation = BottomNavigation(active, self)
        self.navigation.selected.connect(self.navigation_requested.emit)
        self.root.addWidget(self.navigation)


class MusicView(_NavigationPage):
    def __init__(self, parent=None):
        super().__init__("Music")
        title = QLabel("Music \U0001F3B5")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        note = QLabel("A calm space for your focus soundtrack.")
        note.setObjectName("subtitle")
        note.setAlignment(Qt.AlignCenter)
        self.root.insertWidget(0, title)
        self.root.insertWidget(1, note)
        self.root.insertSpacing(2, 12)


class SettingsView(_NavigationPage):
    def __init__(self, tracker, parent=None):
        super().__init__("Settings")
        self.tracker = tracker
        title = QLabel("Settings \u2699")
        title.setObjectName("title")
        note = QLabel("Manage Focus Guard allow and block rules.\nMajor entertainment apps can only be allowed here.")
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        self.root.insertWidget(0, title)
        self.root.insertWidget(1, note)
        self.root.insertSpacing(2, 20)

        card = QFrame()
        card.setObjectName("settingsCard")
        col = QVBoxLayout(card)
        col.setContentsMargins(18, 18, 18, 18)
        col.setSpacing(10)
        self.allow = QRadioButton("Always allow as work")
        self.allow.setChecked(True)
        self.block = QRadioButton("Always block as a distraction")
        col.addWidget(self.allow)
        col.addWidget(self.block)
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText("App name (.exe) or site / keyword")
        self.rule_input.setMaxLength(100)
        col.addWidget(self.rule_input)
        save = QPushButton("Save rule")
        save.setObjectName("capsulePrimary")
        save.clicked.connect(self._save_rule)
        col.addWidget(save)
        self.status = QLabel("")
        self.status.setObjectName("fieldHint")
        self.status.setWordWrap(True)
        col.addWidget(self.status)
        self.root.insertWidget(3, card)
        self.root.insertSpacing(4, 12)
        self.rules = QLabel()
        self.rules.setObjectName("settingsRules")
        self.rules.setWordWrap(True)
        self.root.insertWidget(5, self.rules)
        self.fish_count = QLabel()
        self.fish_count.setObjectName("fieldHint")
        self.root.insertWidget(6, self.fish_count)
        self.root.insertStretch(7, 1)
        self._refresh_rules()

    def _save_rule(self):
        value = self.rule_input.text().strip()
        if not value:
            self.status.setText("Enter an app name or site first.")
            return
        try:
            self.tracker.add_manual_target(value, blocked=self.block.isChecked())
        except OSError as error:
            self.status.setText(f"Could not save the rule: {error}")
            return
        self.rule_input.clear()
        self.status.setText("Rule saved locally and applied immediately.")
        self._refresh_rules()

    def _refresh_rules(self):
        cfg = load_config()
        allowed = cfg.get("productive_processes", []) + cfg.get("productive_keywords", [])
        blocked = (cfg.get("custom_distraction_processes", []) +
                   cfg.get("custom_distraction_sites", []))
        allowed_text = ", ".join(allowed) if allowed else "None"
        blocked_text = ", ".join(blocked) if blocked else "None"
        self.rules.setText(f"Always allowed: {allowed_text}\n\nCustom blocked: {blocked_text}")
        fish = int(QSettings("Pawse", "Pawse").value("canned_fish", 0))
        self.fish_count.setText(f"Canned Fish earned: {fish} \U0001F96B")

    def showEvent(self, event):
        self._refresh_rules()
        super().showEvent(event)
