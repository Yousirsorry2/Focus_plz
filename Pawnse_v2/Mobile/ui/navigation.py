"""Mobile bottom navigation shared by Pawse screens."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QToolButton


class BottomNavigation(QFrame):
    selected = Signal(str)
    TABS = (("Tasks", "🐾"), ("Focus", "🌿"), ("Music", "🎵"), ("Settings", "⚙"))

    def __init__(self, active: str, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomNavigation")
        self.setFixedHeight(74)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(4)

        self.buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for name, icon in self.TABS:
            button = QToolButton()
            button.setObjectName("navTab")
            button.setText(f"{icon}\n{name}")
            button.setProperty("tab", name)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setToolTip(name)
            button.setCheckable(True)
            button.setChecked(name == active)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, tab=name: self.selected.emit(tab))
            group.addButton(button)
            row.addWidget(button, 1)
            self.buttons[name] = button
