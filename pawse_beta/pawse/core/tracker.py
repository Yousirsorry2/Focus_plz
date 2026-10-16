"""
Pawse core tracker
==================
Active-window monitoring, weighted keyword scoring, sliding-window distraction
timing, escalating reminders, snooze limits and idle detection.

The detection lists and scoring rules are ported unchanged from focus_nanny.py.
The engine is a QObject driven by a QTimer (TICK_SECONDS) and talks to the UI
only through signals, so it keeps running while the window is hidden in the tray.

Set PAWSE_TEST_MODE=1 to shrink every interval (same scaling as TEST_MODE in
focus_nanny.py) when you want to see reminders quickly.
"""

from __future__ import annotations

import ctypes
import datetime
import os
import re
import sys
import time
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

try:  # Windows-only dependencies; the module still imports elsewhere for dev/testing
    import psutil
    import win32gui
    import win32process
    HAS_WIN32 = sys.platform == "win32"
except ImportError:  # pragma: no cover
    HAS_WIN32 = False

# =====================================================================
# Settings
# =====================================================================
# "Ultra Focus" in the UI switches the engine to the ULTRA profile (the same
# scaling as TEST_MODE in focus_nanny.py): reminders arrive ~10x faster so you
# can try the whole flow quickly. Set PAWSE_TEST_MODE=1 to start in that mode.
_BASE_INTERVALS = [5, 10, 7.5, 5, 4, 3, 2, 1.5, 1]

NORMAL = dict(
    warn_intervals=_BASE_INTERVALS,
    window_minutes=30,           # Look-back window
    reset_focus_minutes=3,       # Reset counters after 3 mins of continuous focus
    snooze_minutes=3,            # Snooze duration
    idle_away_minutes=7,         # Away threshold
    idle_notice_minutes=10,      # Idle check-in threshold
)
ULTRA = dict(
    warn_intervals=[x / 10 for x in _BASE_INTERVALS],
    window_minutes=5,
    reset_focus_minutes=1,
    snooze_minutes=0.3,
    idle_away_minutes=1,
    idle_notice_minutes=2,
)
START_ULTRA = os.environ.get("PAWSE_TEST_MODE") == "1"

MAX_SNOOZE_COUNT = 3         # Max snoozes allowed ...
SNOOZE_WINDOW_HOURS = 4      # ... per rolling window
TICK_SECONDS = 2             # Checking frequency


# =====================================================================
# Detection Lists (verbatim from focus_nanny.py)
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


# =====================================================================
# System probes
# =====================================================================
class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    """Seconds since the last keyboard/mouse input (GetLastInputInfo)."""
    if not HAS_WIN32:
        return 0.0
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    kernel = ctypes.windll.kernel32
    kernel.GetTickCount64.restype = ctypes.c_ulonglong
    now_ms = kernel.GetTickCount64() & 0xFFFFFFFF
    return ((now_ms - info.dwTime) & 0xFFFFFFFF) / 1000.0


def get_active_info():
    """(window title, lower-case process name) of the foreground window."""
    if not HAS_WIN32:
        return "", ""
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


# =====================================================================
# Distraction scoring (verbatim from focus_nanny.py)
# =====================================================================
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


# =====================================================================
# Engine
# =====================================================================
class Tracker(QObject):
    """Sliding-window distraction tracker with escalating reminders.

    Signals
    -------
    snapshot(dict)  Emitted every tick and after user actions; drives the UI.
    alert(dict)     A distraction reminder is due (payload documented in _warn).
    checkin(int)    The user has been idle past the idle-notice threshold (payload: seconds).
    """

    snapshot = Signal(dict)
    alert = Signal(dict)
    checkin = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = deque()          # (timestamp, seconds) of counted distraction
        self.snooze_history = deque()   # timestamps of snoozes used

        self.ultra = START_ULTRA
        self.cfg = ULTRA if self.ultra else NORMAL
        self.enabled = False            # True only while a focus session is running
        self.popup_open = False

        self.current_app_info = "Detecting..."
        self.last_tick = time.time()
        self.focus_streak = 0.0
        self.since_warn = 0.0
        self.warn_level = 0
        self.snooze_until = 0.0
        self.idle_notified = False
        self.last_reason = ""
        self.today = datetime.date.today()

        self.state_label = "Focused"
        self.progress = 0.0
        self.need = self.interval_minutes(0) * 60
        self.day_focus = 0.0
        self.day_distract = 0.0
        self.day_warns = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)

    # ---- lifecycle ---------------------------------------------------
    def start(self):
        self.last_tick = time.time()
        self._timer.start(int(TICK_SECONDS * 1000))

    def stop(self):
        self._timer.stop()

    def set_enabled(self, on: bool):
        """Enable while a session runs; disabled (paused/ended) ticks count nothing."""
        self.enabled = on
        self.last_tick = time.time()
        self._emit_snapshot()

    def interval_minutes(self, level):
        iv = self.cfg["warn_intervals"]
        return iv[min(level, len(iv) - 1)]

    def set_ultra(self, on: bool):
        """Switch between the normal and the fast test profile at runtime."""
        self.ultra = bool(on)
        self.cfg = ULTRA if self.ultra else NORMAL
        self.snooze_until = 0.0
        self.reset_episode()
        self.last_tick = time.time()
        self._emit_snapshot()

    # ---- snooze bookkeeping -----------------------------------------
    def get_recent_snoozes(self):
        cutoff = time.time() - SNOOZE_WINDOW_HOURS * 3600
        while self.snooze_history and self.snooze_history[0] < cutoff:
            self.snooze_history.popleft()
        return self.snooze_history

    def window_total(self, now):
        cutoff = now - self.cfg['window_minutes'] * 60
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
        return sum(s for _, s in self.samples)

    def reset_episode(self):
        self.samples.clear()
        self.warn_level = 0
        self.since_warn = 0.0
        self.focus_streak = 0.0
        self.need = self.interval_minutes(0) * 60
        self.progress = 0.0

    # ---- popup button handlers --------------------------------------
    def back_to_work(self):
        
        self._emit_snapshot()

    def snooze(self):
        if len(self.get_recent_snoozes()) < MAX_SNOOZE_COUNT:
            now = time.time()
            self.snooze_history.append(now)
            self.snooze_until = now + self.cfg['snooze_minutes'] * 60
        self._emit_snapshot()

    def skip(self):
        """Ignore this reminder; counters keep running toward the next one."""
        self._emit_snapshot()

    def popup_closed(self):
        self.popup_open = False
        self.last_tick = time.time()

    # ---- main loop ---------------------------------------------------
    def tick(self):
        try:
            self._tick()
        except Exception as e:  # never let a probe error kill the timer
            print(f"[Pawse tracker] {e}")

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
        if proc and title:
            short = title[:25] + "..." if len(title) > 25 else title
            self.current_app_info = f"{proc} ({short})"
        else:
            self.current_app_info = proc or "Desktop / None"

        if not self.enabled:  # session paused or not started: observe, don't count
            self.state_label = "Paused"
            self._emit_snapshot()
            return

        idle = get_idle_seconds()
        distracted, reason = check_distraction(title, proc) if title else (False, "")
        passive = distracted and is_passive_media(title, proc)

        away = idle >= self.cfg['idle_away_minutes'] * 60 and not passive
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
            if self.focus_streak >= self.cfg['reset_focus_minutes'] * 60:
                self.reset_episode()

        total = self.window_total(now)
        need = self.interval_minutes(self.warn_level) * 60
        ready = total >= need if self.warn_level == 0 else self.since_warn >= need

        self.need = need
        self.progress = total if self.warn_level == 0 else self.since_warn
        self.state_label = "Distracted" if counted else ("Away" if away else "Focused")
        self._emit_snapshot()

        if counted and now >= self.snooze_until and ready:
            self._warn(total)
            return

        if not distracted and idle >= self.cfg['idle_notice_minutes'] * 60:
            if not self.idle_notified:
                self.idle_notified = True
                self.popup_open = True
                self.checkin.emit(int(idle))
        elif idle < 5:
            self.idle_notified = False

    def _warn(self, total):
        self.warn_level += 1
        self.day_warns += 1
        self.since_warn = 0.0
        lvl = self.warn_level
        spent = f"{round(total / 60)} min" if total >= 60 else f"{int(total)} sec"

        if lvl == 1:
            detail = (f"About {spent} spent on {self.last_reason} "
                      f"in the last {self.cfg['window_minutes']} min.")
        elif lvl == 2:
            detail = "Your work is still waiting. Try a little more, then take a proper break."
        elif lvl == 3:
            detail = "This is the third reminder. Today's goal has not moved yet."
        else:
            detail = f"Reminder {lvl}. Let's get back to work."

        used = len(self.get_recent_snoozes())
        self.popup_open = True
        self.alert.emit({
            "level": lvl,
            "detail": detail,
            "reason": self.last_reason,
            "next_interval": self.interval_minutes(lvl),
            "snooze_minutes": self.cfg['snooze_minutes'],
            "can_snooze": used < MAX_SNOOZE_COUNT,
            "snoozes_left": MAX_SNOOZE_COUNT - used,
            "max_snoozes": MAX_SNOOZE_COUNT,
            "snooze_window_hours": SNOOZE_WINDOW_HOURS,
        })
        self._emit_snapshot()

    def _emit_snapshot(self):
        now = time.time()
        self.snapshot.emit({
            "state": self.state_label,
            "app": self.current_app_info,
            "progress": self.progress,
            "need": self.need,
            "day_focus": self.day_focus,
            "day_distract": self.day_distract,
            "day_warns": self.day_warns,
            "snoozed": now < self.snooze_until,
            "snooze_remaining": max(0.0, self.snooze_until - now),
            "snoozes_used": len(self.get_recent_snoozes()),
            "ultra": self.ultra,
        })
