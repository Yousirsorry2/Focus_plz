"""Mobile bottom navigation shared by Pawse screens."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout


class BottomNavigation(QFrame):
    selected = Signal(str)
    TABS = (("Tasks", "🐾"), ("Focus", "🌿"), ("Music", "🎵"), ("Settings", "⚙"))

    def __init__(self, active: str, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomNavigation")
        self.setFixedHeight(78)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(4)

        self.buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for name, icon in self.TABS:
            button = QToolButton()
            button.setObjectName("navTab")
            button.setProperty("tab", name)
            button.setToolTip(name)
            button.setCheckable(False)
            button.setChecked(name == active)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedWidth(int(self.width() * 0.50))
            button.setStyleSheet("""
                QPushButton {
                    background-color: blue;
                    color: white;
                }
                QPushButton:hover {
                    background-color: darkblue; /* เปลี่ยนสีตอนเมาส์ชี้ */
                }
            """)
            content = QVBoxLayout(button)
            content.setContentsMargins(0, 2, 0, 2)
            content.setSpacing(0)
            icon_label = QLabel(icon)
            icon_label.setObjectName("navIcon")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
            name_label = QLabel(name)
            name_label.setObjectName("navLabel")
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
            content.addWidget(icon_label)
            content.addWidget(name_label)
            button.clicked.connect(lambda _=False, tab=name: self.selected.emit(tab))
            group.addButton(button)
            row.addWidget(button, 1)
            self.buttons[name] = button
