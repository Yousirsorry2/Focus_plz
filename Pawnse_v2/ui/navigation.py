"""Pastel capsule navigation shared by Pawse screens."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class BottomNavigation(QFrame):
    selected = Signal(str)
    TABS = (("Tasks", "🐾"), ("Focus", "🌿"), ("Music", "🎵"), ("Settings", "⚙"))

    def __init__(self, active: str, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomNavigation")
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(6)
        self.buttons = {}
        for name, icon in self.TABS:
            button = QPushButton(f"{icon}  {name}")
            button.setObjectName("navTab")
            button.setProperty("tab", name)
            button.setCheckable(True)
            button.setChecked(name == active)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, tab=name: self.selected.emit(tab))
            row.addWidget(button, 1)
            self.buttons[name] = button
