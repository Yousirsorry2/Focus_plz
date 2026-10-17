"""Pawse design tokens, global QSS and the tray icon."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

CREAM = "#FDFBF7"    # canvas
PEACH = "#FFD1BA"    # primary / active
MINT = "#C8E6C9"     # success / accent
COCOA = "#4A403A"    # text & lines
COCOA_SOFT = "rgba(74, 64, 58, 0.62)"   # secondary text (cocoa at reduced opacity)
COCOA_LINE = "rgba(74, 64, 58, 0.18)"   # hairlines and outlines
PEACH_HOVER = "#FFC4A5"
PEACH_PRESS = "#FFB898"

FONT_STACK = '"Inter", "Segoe UI", "Segoe UI Emoji", sans-serif'

APP_QSS = f"""
* {{ font-family: {FONT_STACK}; color: {COCOA}; }}
QLabel {{ background: transparent; }}

/* ---------- Focus Mode window ---------- */
QWidget#FocusWindow {{ background: {CREAM}; }}
QLabel#title    {{ font-size: 28px; font-weight: 700; }}
QLabel#subtitle {{ font-size: 14px; color: {COCOA_SOFT}; }}
QLabel#statusChip {{
    background: {MINT}; border-radius: 13px; padding: 5px 16px;
    font-size: 13px; font-weight: 600;
}}
QLabel#statusChip[mode="paused"] {{ background: {PEACH}; }}
QLabel#statusChip[mode="idle"]   {{ background: rgba(74,64,58,0.08); }}
QLabel#statusNote {{ font-size: 12px; color: {COCOA_SOFT}; }}
QLabel#timer {{ font-size: 76px; font-weight: 600; letter-spacing: 2px; }}

QProgressBar#sessionBar {{
    background: rgba(74,64,58,0.08); border: none; border-radius: 3px;
    max-height: 6px; min-height: 6px;
}}
QProgressBar#sessionBar::chunk {{ background: {MINT}; border-radius: 3px; }}

QPushButton {{ font-size: 14px; font-weight: 600; }}
QPushButton#capsulePrimary, QPushButton#capsule {{
    min-height: 44px; padding: 0 20px; border-radius: 22px;
}}
QPushButton#capsulePrimary {{ background: {PEACH}; border: 1px solid {PEACH}; }}
QPushButton#capsulePrimary:hover {{ background: {PEACH_HOVER}; }}
QPushButton#capsulePrimary:pressed {{ background: {PEACH_PRESS}; }}
QPushButton#capsule {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; }}
QPushButton#capsule:hover {{ background: {CREAM}; border-color: {COCOA}; }}
QPushButton#capsule:disabled {{ color: rgba(74,64,58,0.35); border-color: rgba(74,64,58,0.10); }}

QPushButton#stepButton {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 15px;
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    padding: 0; font-size: 16px; font-weight: 600;
}}
QPushButton#stepButton:hover {{ background: {CREAM}; border-color: {COCOA}; }}
QPushButton#lengthButton {{
    background: transparent; border: none; font-size: 13px; font-weight: 600; padding: 4px 8px;
}}
QPushButton#lengthButton:hover {{ text-decoration: underline; }}

QCheckBox {{ font-size: 12px; font-weight: 500; }}

QFrame#taskBar {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 18px; }}
QLabel#taskCaption {{ font-size: 11px; font-weight: 600; letter-spacing: 1px; color: {COCOA_SOFT}; }}
QLabel#taskName    {{ font-size: 15px; font-weight: 600; }}
QPushButton#linkButton {{
    background: transparent; border: none; font-size: 12px; font-weight: 500;
    color: {COCOA_SOFT}; text-decoration: underline; padding: 4px 2px;
}}
QPushButton#linkButton:hover {{ color: {COCOA}; }}

/* ---------- Focus Guard popup (compact) ---------- */
QWidget#PopupRoot {{ background: transparent; }}
QFrame#card {{ background: {CREAM}; border: 1px solid {PEACH}; border-radius: 18px; }}
QLabel#brand {{ font-size: 11px; font-weight: 600; color: {COCOA_SOFT}; }}
QLabel#badge {{
    background: {PEACH}; border: none; border-radius: 10px; padding: 2px 10px;
    font-size: 11px; font-weight: 600;
}}
QLabel#popupHeading {{ font-size: 11px; font-weight: 600; color: {COCOA_SOFT}; }}
QLabel#popupMessage {{ font-size: 14px; font-weight: 600; }}
QLabel#popupDetail  {{ font-size: 11px; color: {COCOA_SOFT}; }}
QLabel#popupFooter  {{ font-size: 11px; color: {COCOA_SOFT}; }}

QPushButton#popupPrimary, QPushButton#popupOutline, QPushButton#popupText {{
    min-height: 32px; border-radius: 16px; padding: 0 14px; font-size: 12px;
}}
QPushButton#popupPrimary {{ background: {PEACH}; border: 1px solid {PEACH}; }}
QPushButton#popupPrimary:hover {{ background: {PEACH_HOVER}; }}
QPushButton#popupPrimary:pressed {{ background: {PEACH_PRESS}; }}
QPushButton#popupOutline {{ background: transparent; border: 1.5px solid {COCOA}; }}
QPushButton#popupOutline:hover {{ background: rgba(74,64,58,0.06); }}
QPushButton#popupOutline:disabled {{ color: rgba(74,64,58,0.35); border-color: rgba(74,64,58,0.20); }}
QPushButton#popupText {{ background: transparent; border: none; color: {COCOA_SOFT}; font-weight: 500; }}
QPushButton#popupText:hover {{ color: {COCOA}; background: rgba(74,64,58,0.06); }}

QInputDialog, QDialog {{ background: {CREAM}; }}
QLineEdit {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 10px; padding: 6px 10px; }}
"""


def make_paw_icon() -> QIcon:
    """Peach disc with a cocoa paw print, used for the tray and window icon."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(PEACH))
    p.drawEllipse(2, 2, 60, 60)
    p.setBrush(QColor(COCOA))
    p.drawEllipse(QRectF(20, 33, 24, 18))                       # main pad
    for x, y in ((14, 28), (24, 17), (36, 17), (46, 28)):        # toes
        p.drawEllipse(QRectF(x, y, 9, 11))
    p.end()
    return QIcon(pm)
