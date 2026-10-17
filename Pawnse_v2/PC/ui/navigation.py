"""Pastel sidebar navigation shared by Pawse screens."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class BottomNavigation(QFrame):
    selected = Signal(str)
    TABS = (("Tasks", "🐾"), ("Focus", "🌿"), ("Music", "🎵"), ("Settings", "⚙"))

    def __init__(self, active: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sideNavigation")
        self.setFixedWidth(190)
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 20, 18, 16)
        column.setSpacing(8)

        brand = QLabel("🐾  Pawse")
        brand.setObjectName("navBrand")
        column.addWidget(brand)
        column.addSpacing(28)

        self.buttons = {}
        for name, icon in self.TABS:
            button = QPushButton(f"{icon}     {name}")
            button.setObjectName("navTab")
            button.setProperty("tab", name)
            button.setCheckable(True)
            button.setChecked(name == active)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, tab=name: self.selected.emit(tab))
            column.addWidget(button)
            self.buttons[name] = button

        column.addStretch(1)
        footer = QLabel("✿\nA little progress is\nstill progress.")
        footer.setObjectName("navFooter")
        footer.setWordWrap(True)
        column.addWidget(footer)
        column.addSpacing(16)
        profile = QLabel("🐱  Mochi's corner")
        profile.setObjectName("navProfile")
        column.addWidget(profile)
