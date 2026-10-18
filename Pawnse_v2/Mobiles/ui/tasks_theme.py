"""Additional QSS for task screens and dialogs, appended to the shared app theme."""

from ui.theme import APP_QSS, COCOA, COCOA_LINE, COCOA_SOFT, CREAM, MINT, PEACH, PEACH_HOVER, PEACH_PRESS

TASKS_QSS = f"""
QWidget#TasksWindow {{ background: {CREAM}; }}
QDialog#sheet {{ background: {CREAM}; }}
QFrame#bottomNavigation {{ background: {MINT}; border-top: 1px solid {COCOA_LINE}; }}
QToolButton#navTab {{
    border: none; border-radius: 14px; min-height: 62px;
    padding: 3px 2px; font-size: 12px; font-weight: 600;
    background: transparent; text-align: center;
}}
QToolButton#navTab:checked {{ background: {PEACH}; font-weight: 700; }}
QToolButton#navTab:hover {{ background: rgba(255,209,186,0.45); }}
QLabel#navIcon {{ font-size: 23px; }}
QLabel#navLabel {{ font-size: 11px; font-weight: 600; }}
QWidget#mobilePage {{ background: {CREAM}; }}
QLabel#title {{ font-size: 24px; }}
QLabel#timer {{ font-size: 68px; }}
QLabel#taskCaption {{ font-size: 10px; }}
QLabel#taskName {{ font-size: 14px; }}
QFrame#settingsCard {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 16px; }}
QLabel#settingsRules {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 14px; padding: 12px; }}
QFrame#dashboardCard, QFrame#musicCard {{
    background: #FFFFFF; border: 1px solid rgba(74,64,58,0.08); border-radius: 20px;
}}
QFrame#softCard {{ background: rgba(200,230,201,0.45); border: none; border-radius: 18px; }}
QLabel#sectionEyebrow {{ color: {COCOA_SOFT}; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLabel#sectionTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#cardTitle {{ font-size: 16px; font-weight: 700; }}
QLineEdit#musicLink {{
    background: {CREAM}; border: 1px solid {COCOA_LINE}; border-radius: 12px;
    padding: 10px 12px; min-height: 22px; font-size: 13px;
}}
QPushButton#providerButton {{
    border: 1px solid {COCOA_LINE}; border-radius: 12px; background: #FFFFFF;
    min-height: 38px; padding: 0 12px; font-size: 12px; font-weight: 600;
}}
QPushButton#providerButton:hover {{ background: {CREAM}; border-color: {COCOA}; }}
QPushButton#providerButton[provider="YouTube"] {{ color: #B3261E; }}
QPushButton#providerButton[provider="Spotify"] {{ color: #187A48; }}
QPushButton#playlistPlay {{
    background: {PEACH}; border: none; border-radius: 12px;
    min-height: 36px; padding: 0 12px; font-weight: 700;
}}
QPushButton#playlistRemove {{
    background: transparent; border: none; color: {COCOA_SOFT}; font-size: 15px;
}}
QLabel#musicHint {{ color: {COCOA_SOFT}; font-size: 11px; }}
QLabel#musicStatus {{ font-size: 12px; font-weight: 600; }}

/* ---------- category filter chips ---------- */
QPushButton#chip {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 15px;
    padding: 0 16px; min-height: 30px; max-height: 30px; font-size: 13px; font-weight: 600;
}}
QPushButton#chip:hover {{ border-color: {COCOA}; }}
QPushButton#chip:checked {{ background: {PEACH}; border-color: {PEACH}; }}

/* ---------- task cards ---------- */
QFrame#taskCard {{ background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 16px; }}
QFrame#taskCard[selected="true"] {{ background: #FFFAF6; border: 1.5px solid {PEACH_PRESS}; }}
QFrame#taskCard[done="true"] {{ background: rgba(255,255,255,0.55); }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#cardTitle[done="true"] {{ color: {COCOA_SOFT}; text-decoration: line-through; }}
QLabel#pill {{ border-radius: 9px; padding: 2px 10px; font-size: 11px; font-weight: 600; }}
QLabel#emptyNote {{ font-size: 13px; color: {COCOA_SOFT}; }}
QToolButton#moreButton {{
    border: none; background: transparent; font-size: 18px; font-weight: 700;
    padding: 2px 8px; border-radius: 10px;
}}
QToolButton#moreButton:hover {{ background: rgba(74,64,58,0.08); }}
QToolButton#moreButton::menu-indicator {{ image: none; width: 0px; }}
QPushButton#accordion {{
    background: transparent; border: none; text-align: left; font-size: 13px;
    font-weight: 600; color: {COCOA_SOFT}; padding: 8px 4px;
}}
QPushButton#accordion:hover {{ color: {COCOA}; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba(74,64,58,0.22); border-radius: 3px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: rgba(74,64,58,0.22); border-radius: 3px; min-width: 28px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QMenu {{ background: {CREAM}; border: 1px solid {COCOA_LINE}; border-radius: 10px; padding: 4px; }}
QMenu::item {{ padding: 6px 20px; border-radius: 6px; }}
QMenu::item:selected {{ background: {PEACH}; }}

/* ---------- Add / Edit task sheet ---------- */
QLabel#sheetTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#fieldCaption {{ font-size: 11px; font-weight: 600; letter-spacing: 1px; color: {COCOA_SOFT}; }}
QLabel#fieldTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#fieldHint {{ font-size: 12px; color: {COCOA_SOFT}; }}
QLabel#formError {{ font-size: 12px; font-weight: 600; background: {PEACH}; border-radius: 9px; padding: 5px 10px; }}
QLineEdit#taskInput {{ font-size: 15px; padding: 10px 12px; }}
QLineEdit:focus {{ border: 1px solid {COCOA}; }}
QComboBox, QSpinBox, QPushButton#dateTimeField {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 10px;
    padding: 6px 10px; min-height: 22px; font-size: 13px;
}}
QComboBox:disabled, QSpinBox:disabled, QPushButton#dateTimeField:disabled {{
    color: rgba(74,64,58,0.35); background: rgba(255,255,255,0.5);
}}
QPushButton#dateTimeField {{ text-align: left; }}
QPushButton#dateTimeField:hover {{ border-color: {COCOA}; background: #FFFCF8; }}
QPushButton#calendarArrow {{
    background: {PEACH}; border: 1px solid {PEACH}; border-radius: 15px;
    min-width: 62px; min-height: 30px; font-size: 13px;
}}
QLabel#calendarWeekday {{ color: {COCOA_SOFT}; font-size: 11px; font-weight: 600; }}
QPushButton#calendarDay {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 15px;
    min-width: 34px; max-width: 34px; min-height: 30px; max-height: 30px;
    padding: 0; font-size: 12px;
}}
QPushButton#calendarDay:hover {{ border-color: {PEACH_PRESS}; }}
QPushButton#calendarDay:checked {{ background: {PEACH}; border-color: {PEACH}; font-weight: 700; }}
QLabel#timeValue {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 10px;
    min-height: 38px; font-size: 18px; font-weight: 700;
}}
QPushButton#timeStep {{
    background: {PEACH}; border: 1px solid {PEACH}; border-radius: 13px;
    min-width: 26px; max-width: 26px; min-height: 30px; max-height: 30px; padding: 0;
}}
QPushButton#timePeriod {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 10px;
    min-width: 48px; min-height: 20px; padding: 2px 6px; font-size: 11px;
}}
QPushButton#timePeriod:checked {{ background: {MINT}; border-color: {MINT}; font-weight: 700; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE};
    selection-background-color: {PEACH}; selection-color: {COCOA}; outline: 0;
}}
QPushButton#chipAdd {{
    background: transparent; border: 1.5px dashed {COCOA_SOFT}; border-radius: 14px;
    padding: 0 12px; min-height: 28px; font-size: 12px; font-weight: 600;
}}
QPushButton#chipAdd:hover {{ background: rgba(74,64,58,0.06); }}
QPushButton#swatchMore {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 15px;
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0;
}}

/* ---------- Focus Guard: Mark as Work ---------- */
QPushButton#popupWork {{
    background: {MINT}; border: 1px solid {MINT};
    min-height: 32px; border-radius: 16px; padding: 0 14px; font-size: 12px;
}}
QPushButton#popupWork:hover {{ background: #B4DBB7; border-color: #B4DBB7; }}
QPushButton#popupWork:pressed {{ background: #A2CFA6; }}

QPushButton#linkButton:disabled {{ color: rgba(74,64,58,0.3); }}
QMessageBox {{ background: {CREAM}; }}
QMessageBox QPushButton {{
    background: #FFFFFF; border: 1px solid {COCOA_LINE}; border-radius: 14px;
    padding: 5px 18px; min-width: 60px; font-size: 13px;
}}
QMessageBox QPushButton:hover {{ background: {PEACH_HOVER}; }}
"""

FULL_QSS = APP_QSS + TASKS_QSS
