"""
Focus Nanny (Minimal Version - No Music Player)
  - Sliding-window distraction timer with idle detection
  - Escalating reminder popups
  - Limited Snooze: Max 3 times per 4-hour window
"""

import ctypes
import datetime
import json
import re
import signal
import sys
import time
from collections import deque
from pathlib import Path

import psutil
import win32gui
import win32process
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QMenu, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget)

# =====================================================================
# Settings
# =====================================================================
TEST_MODE = False

WARN_INTERVALS = [5, 10, 7.5, 5, 4, 3, 2, 1.5, 1]
WINDOW_MINUTES = 30          # Look-back window
RESET_FOCUS_MINUTES = 3      # Reset counter after 3 mins of continuous focus
SNOOZE_MINUTES = 3           # Snooze duration

# Snooze Limits
MAX_SNOOZE_COUNT = 3         # Max snoozes allowed
SNOOZE_WINDOW_HOURS = 4      # Rolling window in hours

IDLE_AWAY_MINUTES = 7        # Away threshold
IDLE_NOTICE_MINUTES = 10     # Idle check-in threshold
TICK_SECONDS = 2             # Checking frequency

if TEST_MODE:
    WARN_INTERVALS = [x / 10 for x in WARN_INTERVALS]
    WINDOW_MINUTES, RESET_FOCUS_MINUTES = 5, 1
    SNOOZE_MINUTES = 0.3
    IDLE_AWAY_MINUTES, IDLE_NOTICE_MINUTES = 1, 2


def interval_minutes(level):
    return WARN_INTERVALS[min(level, len(WARN_INTERVALS) - 1)]


# =====================================================================
# Detection Lists
# =====================================================================
distraction_processes = {
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "riotclientservices.exe",
    "valorant-win64-shipping.exe", "leagueclient.exe", "league of legends.exe",
    "battle.net.exe", "eadesktop.exe", "robloxplayerbeta.exe", "genshinimpact.exe",
    "yuanshen.exe", "minecraft.exe", "minecraftlauncher.exe", "discord.exe",
    "netflix.exe", "disneyplus.exe", "primevideo.exe", "vlc.exe", "potplayermini64.exe",
    "potplayermini.exe", "mpc-hc64.exe", "kmplayer.exe", "twitch.exe", "tiktok.exe",
}

passive_media_processes = {
    "vlc.exe", "potplayermini64.exe", "potplayermini.exe", "mpc-hc64.exe",
    "kmplayer.exe", "netflix.exe", "disneyplus.exe", "primevideo.exe",
}

video_sites = ["youtube", "netflix", "disney+", "bilibili", "wetv", "iqiyi",
               "viu", "twitch", "crunchyroll", "hbo max", "prime video", "vimeo"]

distraction_sites = [
    "facebook", "instagram", "snapchat", "tiktok", "reddit", "threads", "pinterest",
    " / x", "twitter", "twitch", "discord",
    "netflix", "disney+", "disneyplus", "hbo max", "prime video", "iqiyi", "wetv", "viu",
    "bilibili", "crunchyroll", "muse thailand", "ani-one", "nungmovies", "kissanime",
    "9anime", "gogoanime", "hianime",
    "webtoon", "mangadex", "mangakakalot", "readawrite", "dek-d", "tunwalai",
    "fictionlog", "ookbee", "joylada", "wattpad",
    "steam", "epic games", "riot client", "battle.net", "ea app", "valorant",
    "league of legends", "minecraft", "roblox", "genshin", "honkai", "rov", "pubg",
    "free fire", "mobile legends", "fortnite", "garena", "y8.com", "poki.com",
    "itch.io", "crazygames",
]

strong_keywords = [
    "สรุปหนัง", "สปอยหนัง", "สปอยล์", "สปอย", "เล่าหนัง", "รีวิวหนัง", "สรุปซีรีส์",
    "ซีรีส์", "ซีรีย์", "ภาพยนตร์", "หนังเต็มเรื่อง", "เต็มเรื่อง", "หนังใหม่", "ดูหนัง",
    "trailer", "full movie", "movie recap", "movie explained", "ending explained", "recap",
    "หนังสั้น", "อนิเมะ", "อนิเมชั่น", "anime", "พากย์ไทย", "ซับไทย", "สรุปอนิเมะ", "สปอยอนิเมะ", "ดูอนิเมะ",
    "นิยาย", "นิยายเสียง", "นิยายแชท", "มังงะ", "มังฮวา", "การ์ตูน", "อ่านมังงะ",
    "สปอยนิยาย", "สรุปนิยาย", "manga", "manhwa", "manhua", "webtoon", "light novel",
    "audiobook", "นิทานเสียง", "เรื่องผี", "ฟังนิยาย",
    "gameplay", "let's play", "lets play", "walkthrough", "playthrough", "speedrun",
    "แคสเกม", "เล่นเกม", "เกมมิ่ง", "gaming", "ไลฟ์เกม", "เกมใหม่",
    "montage", "clutch", "ranked", "highlight", "ช็อตเด็ด", "คลิปฮา", "meme", "มีม", "reaction", "รีแอค", "prank",
]

weak_keywords = [
    "ตอนที่", "ep.", "episode", "season", "ซีซั่น", "review", "รีวิว", "สตรีม", "stream",
    "live", "ไลฟ์", "ไฮไลท์", "ตัวอย่าง", "movie", "film", "game", "เกม",
]

productive_keywords = [
    "tutorial", "course", "lecture", "บทเรียน", "สอน", "เรียน", "docs", "documentation",
    "github", "stackoverflow", "stack overflow", "leetcode", "coursera", "udemy",
    "khan academy", "visual studio", "vs code", "pycharm", "jupyter", "notion",
    "google docs", "google sheets", "excel", "word", "powerpoint",
]


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    kernel = ctypes.windll.kernel32
    kernel.GetTickCount64.restype = ctypes.c_ulonglong
    now_ms = kernel.GetTickCount64() & 0xFFFFFFFF
    return ((now_ms - info.dwTime) & 0xFFFFFFFF) / 1000.0


def get_active_info():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return "", ""
    title = win32gui.GetWindowText(hwnd).strip()
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid).name().lower()
    except Exception:
        proc = ""
    return title, proc


def contains(text, keyword):
    if re.fullmatch(r"[a-z0-9 .+'-]+", keyword) and len(keyword) <= 5:
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
    return keyword in text


def check_distraction(title, proc):
    t = title.lower()
    if proc in distraction_processes:
        return True, f"app {proc}"
    for site in distraction_sites:
        if contains(t, site):
            return True, f"'{site.strip()}'"

    score, hits = 0, []
    for k in strong_keywords:
        if contains(t, k):
            score += 2
            hits.append(k)
    for k in weak_keywords:
        if contains(t, k):
            score += 1
            hits.append(k)
    if any(v in t for v in video_sites) and hits:
        score += 1
    if any(contains(t, p) for p in productive_keywords):
        score -= 2
    if score >= 2:
        return True, "entertainment (" + ", ".join(hits[:3]) + ")"
    return False, ""


def is_passive_media(title, proc):
    t = title.lower()
    return proc in passive_media_processes or any(v in t for v in video_sites)


FONT_FAMILY = "Segoe UI"


def font(size, bold=False):
    f = QFont(FONT_FAMILY, size)
    f.setBold(bold)
    return f


def make_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#111111"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(24, 24, 16, 16)
    p.end()
    return QIcon(pm)


APP_QSS = """
QWidget { background:#FFFFFF; color:#111111; font-family:'Segoe UI'; font-size:13px; }
QLabel { background:transparent; }
QPushButton { border:1px solid #E5E5E5; border-radius:8px; padding:8px 14px; background:#FFFFFF; color:#111111; }
QPushButton:hover { background:#F5F5F5; }
QPushButton:disabled { background:#F0F0F0; color:#AAAAAA; border-color:#E0E0E0; }
QPushButton#primary { background:#111111; color:#FFFFFF; border-color:#111111; }
QPushButton#primary:hover { background:#333333; }
QFrame#line { background:#EEEEEE; border:none; min-height:1px; max-height:1px; }
"""


def make_label(text, size=10, color="#111111", bold=False):
    lab = QLabel(text)
    lab.setFont(font(size, bold))
    lab.setStyleSheet(f"color:{color};")
    return lab


def make_line():
    ln = QFrame()
    ln.setObjectName("line")
    return ln


class MainWindow(QWidget):
    def __init__(self, nanny):
        super().__init__()
        self.nanny = nanny
        self._tray_hint_shown = False
        self.active_app_label = make_label("Active App: Detecting...", 9, "#8A8A8A")
        
        self.setWindowTitle("Focus Nanny")
        self.setFixedWidth(400)
        self.setStyleSheet(APP_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)
        root.addWidget(self.active_app_label)
        
        # Header
        head = QHBoxLayout()
        head.addWidget(make_label("Focus Nanny", 15, bold=True))
        head.addStretch()
        self.status = make_label("Focused", 11, "#111111", True)
        head.addWidget(self.status)
        root.addLayout(head)

        self.status_detail = make_label("", 10, "#8A8A8A")
        self.status_detail.setContentsMargins(0, 4, 0, 0)
        root.addWidget(self.status_detail)

        root.addSpacing(18)
        root.addWidget(make_line())
        root.addSpacing(18)

        # Stats
        stats = QHBoxLayout()
        self.stat_focus = self._stat_cell(stats, "Focused today")
        self.stat_distract = self._stat_cell(stats, "Distracted today")
        self.stat_warn = self._stat_cell(stats, "Reminders today")
        root.addLayout(stats)

        root.addSpacing(18)
        root.addWidget(make_line())
        root.addSpacing(14)

        # Snooze Status
        self.snooze_info = make_label("Snooze limit: 0/3 used in last 4 hrs", 10, "#8A8A8A")
        root.addWidget(self.snooze_info)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh)
        self.poll_timer.start(500)

    def _stat_cell(self, layout, caption):
        cell = QVBoxLayout()
        cell.setSpacing(0)
        value = make_label("0", 17, bold=True)
        cell.addWidget(value)
        cell.addWidget(make_label(caption, 9, "#8A8A8A"))
        layout.addLayout(cell)
        layout.addStretch()
        return value

    def refresh(self):
        n = self.nanny
        # อัปเดตข้อความแสดงชื่อแอปปัจจุบันบน UI
        self.active_app_label.setText(f"Active App: {n.current_app_info}")
        self.status.setText(n.state_label)
        remaining = max(0.0, n.need - n.progress)
        if time.time() < n.snooze_until:
            self.status_detail.setText("Reminders snoozed")
        else:
            self.status_detail.setText(
                f"{n.progress / 60:.1f} of {n.need / 60:g} min toward next reminder"
                f"  /  {remaining / 60:.1f} min left")
        self.stat_focus.setText(f"{int(n.day_focus // 60)} min")
        self.stat_distract.setText(f"{int(n.day_distract // 60)} min")
        self.stat_warn.setText(str(n.day_warns))

        snoozes_used = len(n.get_recent_snoozes())
        self.snooze_info.setText(f"Snooze limit: {snoozes_used}/{MAX_SNOOZE_COUNT} used in last {SNOOZE_WINDOW_HOURS} hrs")

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if not self._tray_hint_shown and self.nanny.tray:
            self._tray_hint_shown = True
            self.nanny.tray.showMessage("Focus Nanny", "Still running in system tray.",
                                        QSystemTrayIcon.Information, 3000)


class ActionButton(QPushButton):
    STYLES = {
        "primary": ("#111111", "#333333", "#111111", "#FFFFFF"),
        "outline": ("#FFFFFF", "#F5F5F5", "#D4D4D4", "#111111"),
        "text":    ("#FFFFFF", "#F5F5F5", "#FFFFFF", "#8A8A8A"),
        "disabled": ("#F0F0F0", "#F0F0F0", "#E0E0E0", "#AAAAAA"),
    }

    def __init__(self, title, sub, kind, enabled=True):
        super().__init__()
        style_key = kind if enabled else "disabled"
        base, hover, border, fg = self.STYLES[style_key]
        self.setEnabled(enabled)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)
        self.setFixedHeight(54)
        self.setMinimumWidth(116)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(f"""
            QPushButton {{ background:{base}; border:1px solid {border}; border-radius:10px; }}
            QPushButton:hover {{ background:{hover}; }}
            QLabel {{ background:transparent; color:{fg}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)
        t = QLabel(title)
        t.setFont(font(12, True))
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(sub)
        s.setFont(font(9))
        s.setAlignment(Qt.AlignCenter)
        for w in (t, s):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)


class NannyPopup(QWidget):
    def __init__(self, msg, buttons, accent="#D4D4D4", badge="", footer="", on_closed=None):
        super().__init__()
        self._on_closed = on_closed
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 26)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            #card {{ background:#FFFFFF; border:1px solid {accent}; border-radius:16px; }}
            QLabel {{ background:transparent; }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 55))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 18, 26, 18)
        lay.setSpacing(0)

        top = QHBoxLayout()
        brand = QLabel("Focus Nanny")
        brand.setFont(font(10))
        brand.setStyleSheet("color:#9A9A9A;")
        top.addWidget(brand)
        top.addStretch()
        if badge:
            pill = QLabel(badge)
            pill.setFont(font(9))
            pill.setStyleSheet("color:#111111; border:1px solid #D4D4D4; border-radius:9px; padding:2px 10px;")
            top.addWidget(pill)
        lay.addLayout(top)

        text = QLabel(msg)
        text.setFont(font(15))
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("color:#111111;")
        text.setMinimumWidth(420)
        text.setContentsMargins(0, 24, 0, 24)
        lay.addWidget(text)

        row = QHBoxLayout()
        row.setSpacing(10)
        for title, sub, kind, cb, enabled in buttons:
            b = ActionButton(title, sub, kind, enabled=enabled)
            if enabled:
                b.clicked.connect(lambda _=False, cb=cb: self.finish(cb))
            row.addWidget(b)
        lay.addLayout(row)

        if footer:
            f = QLabel(footer)
            f.setFont(font(9))
            f.setAlignment(Qt.AlignCenter)
            f.setStyleSheet("color:#9A9A9A;")
            f.setContentsMargins(0, 14, 0, 0)
            lay.addWidget(f)

        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 10, screen.bottom() - self.height() - 10)

        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(180)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def finish(self, cb):
        self.hide()
        self.deleteLater()
        if self._on_closed:
            self._on_closed()
        cb()


class FocusNanny:
    LEVEL_COLORS = ["#D4D4D4", "#A3A3A3", "#525252", "#111111"]

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.samples = deque()
        self.snooze_history = deque()  # Stores timestamps of snoozes

        self.current_app_info = "Detecting..."

        self.last_tick = time.time()
        self.focus_streak = 0.0
        self.since_warn = 0.0
        self.warn_level = 0
        self.snooze_until = 0.0
        self.popup = None
        self.popup_open = False
        self.idle_notified = False
        self.last_reason = ""
        self.today = datetime.date.today()

        self.state_label = "Focused"
        self.progress = 0.0
        self.need = interval_minutes(0) * 60
        self.day_focus = 0.0
        self.day_distract = 0.0
        self.day_warns = 0

        self.tray = None
        self.window = MainWindow(self)
        self._setup_tray()
        self.window.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self.app)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("Open").triggered.connect(self.window.show_normal)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("Quit").triggered.connect(self.app.quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(
            lambda reason: self.window.show_normal() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.setToolTip("Focus Nanny")
        self.tray.show()

    def get_recent_snoozes(self):
        now = time.time()
        cutoff = now - (SNOOZE_WINDOW_HOURS * 3600)
        while self.snooze_history and self.snooze_history[0] < cutoff:
            self.snooze_history.popleft()
        return self.snooze_history

    def window_total(self, now):
        cutoff = now - WINDOW_MINUTES * 60
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
        return sum(s for _, s in self.samples)

    def reset_episode(self):
        self.samples.clear()
        self.warn_level = 0
        self.since_warn = 0.0
        self.focus_streak = 0.0

    def tick(self):
        try:
            self._tick()
        except Exception as e:
            print(f"Error: {e}")

    def _tick(self):
        now = time.time()
        dt = min(now - self.last_tick, 10)
        self.last_tick = now

        if datetime.date.today() != self.today:
            self.today = datetime.date.today()
            self.reset_episode()
            self.day_focus = self.day_distract = 0.0
            self.day_warns = 0

        if self.popup_open:
            return

        title, proc = get_active_info()
        
        # --- เพิ่มส่วนอัปเดตชื่อแอปตรงนี้ ---
        if proc and title:
            short_title = title[:25] + "..." if len(title) > 25 else title
            self.current_app_info = f"{proc} ({short_title})"
        elif proc:
            self.current_app_info = proc
        else:
            self.current_app_info = "Desktop / None"
        # -----------------------------------

        idle = get_idle_seconds()
        distracted, reason = check_distraction(title, proc) if title else (False, "")
        passive = distracted and is_passive_media(title, proc)

        away = idle >= IDLE_AWAY_MINUTES * 60 and not passive
        counted = distracted and not away

        if counted:
            self.samples.append((now, dt))
            self.since_warn += dt
            self.focus_streak = 0.0
            self.last_reason = reason
            self.day_distract += dt
        elif not distracted and not away:
            self.focus_streak += dt
            self.day_focus += dt
            if self.focus_streak >= RESET_FOCUS_MINUTES * 60:
                self.reset_episode()

        total = self.window_total(now)
        need = interval_minutes(self.warn_level) * 60
        ready = total >= need if self.warn_level == 0 else self.since_warn >= need

        self.need = need
        self.progress = total if self.warn_level == 0 else self.since_warn
        self.state_label = "Distracted" if counted else ("Away" if away else "Focused")

        if counted and now >= self.snooze_until and ready:
            self.warn_distraction(total)
            return

        if not distracted and idle >= IDLE_NOTICE_MINUTES * 60:
            if not self.idle_notified:
                self.idle_notified = True
                self.notice_idle(idle)
        elif idle < 5:
            self.idle_notified = False

    def warn_distraction(self, total):
        self.warn_level += 1
        self.day_warns += 1
        self.since_warn = 0.0
        lvl = self.warn_level
        mins = round(total / 60)

        if lvl == 1:
            msg = (f"About {mins} min spent on {self.last_reason}\n"
                   f"in the last {WINDOW_MINUTES} min. Ready to get back to it?")
        elif lvl == 2:
            msg = "Your work is still waiting.\nTry a little more, then take a proper break."
        elif lvl == 3:
            msg = "This is the third reminder.\nToday's goal has not moved yet."
        else:
            msg = f"Reminder {lvl}.\nLet's get back to work."

        nxt = interval_minutes(lvl)
        accent = self.LEVEL_COLORS[min(lvl - 1, len(self.LEVEL_COLORS) - 1)]

        recent_snoozes = len(self.get_recent_snoozes())
        can_snooze = recent_snoozes < MAX_SNOOZE_COUNT
        snooze_sub = f"Pause {SNOOZE_MINUTES:g} min ({MAX_SNOOZE_COUNT - recent_snoozes} left)" if can_snooze else f"Limit {MAX_SNOOZE_COUNT}/{SNOOZE_WINDOW_HOURS}h reached"

        buttons = [
            ("Back to work", "Reset the counter", "primary", self.on_back_to_work, True),
            ("Snooze", snooze_sub, "outline", self.on_snooze, can_snooze),
            ("Skip", "Ignore this one", "text", self.on_skip, True),
        ]
        self.show_popup(msg, buttons, accent=accent, badge=f"Reminder {lvl}",
                        footer=f"If you stay distracted, the next reminder is in {nxt:g} min")

    def notice_idle(self, idle):
        msg = f"The screen has been still for {int(idle // 60)} min.\nStill there? Maybe stretch for a moment."
        self.show_popup(msg, [("OK", "Got it", "primary", lambda: None, True)],
                        accent="#D4D4D4", badge="Check-in")

    def on_back_to_work(self):
        self.reset_episode()

    def on_snooze(self):
        if len(self.get_recent_snoozes()) < MAX_SNOOZE_COUNT:
            self.snooze_history.append(time.time())
            self.snooze_until = time.time() + SNOOZE_MINUTES * 60
            print(f"Snoozed for {SNOOZE_MINUTES:g} min (Used {len(self.snooze_history)}/{MAX_SNOOZE_COUNT})")

    def on_skip(self):
        print(f"Skipped (next reminder in {interval_minutes(self.warn_level):g} min)")

    def _popup_closed(self):
        self.popup_open = False
        self.last_tick = time.time()

    def show_popup(self, msg, buttons, **kw):
        self.popup_open = True
        self.popup = NannyPopup(msg, buttons, on_closed=self._popup_closed, **kw)

    def run(self):
        print("Focus Nanny running (No Music, Max 3 Snoozes per 4 Hrs)")
        signal.signal(signal.SIGINT, lambda *_: self.app.quit())
        self.timer.start(int(TICK_SECONDS * 1000))
        self.app.exec()


if __name__ == "__main__":
    FocusNanny().run()