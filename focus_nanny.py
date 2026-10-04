"""
Focus Nanny - เวอร์ชัน Qt (popup คมชัด ขอบมน ฟอนต์ลายมือ)
  - ตัวจับเวลาสะสม (sliding window) + ตรวจจับ idle
  - popup YES / WAIT / SKIP ข้ามได้ไม่จำกัด แต่เตือนถี่ขึ้นเรื่อยๆ

ติดตั้ง:  pip install psutil pywin32 PySide6
รัน:      python focus_nanny.py
ฟอนต์:    วางไฟล์ Itim-Regular.ttf ไว้ในโฟลเดอร์ fonts/ ข้างๆ ไฟล์นี้
"""

import ctypes
import datetime
import re
import time
import signal
import sys
from collections import deque
from pathlib import Path

import psutil
import win32gui
import win32process
from PySide6.QtCore import Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)

# =====================================================================
# ตั้งค่า (แก้ตรงนี้ได้เลย)
# =====================================================================
TEST_MODE = False            # True = ใช้ค่าสั้นๆ เพื่อทดสอบ

# ช่วงห่างระหว่างการเตือน (นาที) เตือนครั้งที่ 1,2,3,... ถี่ขึ้นเรื่อยๆ ค้างที่ค่าสุดท้าย
WARN_INTERVALS = [5,10, 7.5, 5, 4, 3, 2, 1.5, 1]

WINDOW_MINUTES = 30          # ดูย้อนหลังกี่นาที (ใช้กับการเตือนครั้งแรก)
RESET_FOCUS_MINUTES = 3      # กลับมาทำงานต่อเนื่องเกินกี่นาที ถึงล้างตัวนับ + ล้างระดับความถี่
SNOOZE_MINUTES = 3           # ปุ่ม WAIT พักการเตือนกี่นาที

IDLE_AWAY_MINUTES = 7        # ไม่แตะเมาส์/คีย์บอร์ดเกินนี้ = ถือว่าไม่อยู่หน้าจอ (ไม่นับเวลารบกวน)
IDLE_NOTICE_MINUTES = 10     # หน้าจอนิ่งเกิน n นาทีขณะทำงาน → เตือนเบาๆ ว่ายังอยู่ไหม

TICK_SECONDS = 2             # ตรวจทุกกี่วินาที

if TEST_MODE:
    WARN_INTERVALS = [x / 10 for x in WARN_INTERVALS]   # เร็วขึ้น 10 เท่า
    WINDOW_MINUTES, RESET_FOCUS_MINUTES = 5, 1
    SNOOZE_MINUTES = 0.3
    IDLE_AWAY_MINUTES, IDLE_NOTICE_MINUTES = 1, 2


def interval_minutes(level):
    """level = จำนวนครั้งที่เตือนไปแล้ว → ช่วงห่างก่อนเตือนครั้งถัดไป"""
    return WARN_INTERVALS[min(level, len(WARN_INTERVALS) - 1)]


# =====================================================================
# รายการคำสำหรับตรวจจับ (วางลิสต์ยาวๆ จากเวอร์ชันก่อนทับได้เลย)
# =====================================================================
distraction_processes = {
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe", "riotclientservices.exe",
    "valorant-win64-shipping.exe", "leagueclient.exe", "league of legends.exe",
    "battle.net.exe", "eadesktop.exe", "robloxplayerbeta.exe", "genshinimpact.exe",
    "yuanshen.exe", "minecraft.exe", "minecraftlauncher.exe", "discord.exe",
    "netflix.exe", "disneyplus.exe", "primevideo.exe", "vlc.exe", "potplayermini64.exe",
    "potplayermini.exe", "mpc-hc64.exe", "kmplayer.exe", "twitch.exe", "tiktok.exe",
}

# แอปที่ "ดูเฉยๆ ไม่ขยับเมาส์" เป็นเรื่องปกติ → ไม่ถือว่า idle
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
    "หนังสั้น",
    "อนิเมะ", "อนิเมชั่น", "anime", "พากย์ไทย", "ซับไทย", "สรุปอนิเมะ", "สปอยอนิเมะ", "ดูอนิเมะ",
    "นิยาย", "นิยายเสียง", "นิยายแชท", "มังงะ", "มังฮวา", "การ์ตูน", "อ่านมังงะ",
    "สปอยนิยาย", "สรุปนิยาย", "manga", "manhwa", "manhua", "webtoon", "light novel",
    "audiobook", "นิทานเสียง", "เรื่องผี", "ฟังนิยาย",
    "gameplay", "let's play", "lets play", "walkthrough", "playthrough", "speedrun",
    "แคสเกม", "เล่นเกม", "เกมมิ่ง", "gaming", "ไลฟ์เกม", "เกมใหม่",
    "montage", "clutch", "ranked", "highlight", "ช็อตเด็ด",
    "คลิปฮา", "meme", "มีม", "reaction", "รีแอค", "prank",
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
# ฟังก์ชันตรวจจับ
# =====================================================================
class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    """วินาทีนับจากที่ผู้ใช้แตะเมาส์/คีย์บอร์ดครั้งล่าสุด"""
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    kernel = ctypes.windll.kernel32
    kernel.GetTickCount64.restype = ctypes.c_ulonglong
    now_ms = kernel.GetTickCount64() & 0xFFFFFFFF
    return ((now_ms - info.dwTime) & 0xFFFFFFFF) / 1000.0


def get_active_info():
    """คืนค่า (title, process_name) ของหน้าต่างที่ใช้งานอยู่"""
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
    """คำอังกฤษสั้นๆ ใช้ word boundary กันจับผิด (เช่น 'rov' ใน 'improve')"""
    if re.fullmatch(r"[a-z0-9 .+'-]+", keyword) and len(keyword) <= 5:
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
    return keyword in text


def check_distraction(title, proc):
    t = title.lower()
    if proc in distraction_processes:
        return True, f"แอป {proc}"
    for site in distraction_sites:
        if contains(t, site):
            return True, f"'{site}'"

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
        return True, "สื่อบันเทิง (" + ", ".join(hits[:3]) + ")"
    return False, ""


def is_passive_media(title, proc):
    """หน้าต่างที่การดูโดยไม่ขยับเมาส์เป็นเรื่องปกติ (หนัง/วิดีโอ)"""
    t = title.lower()
    return proc in passive_media_processes or any(v in t for v in video_sites)


# =====================================================================
# หน้าตา popup (Qt)
# =====================================================================
FONT_FILE = Path(__file__).parent / "fonts" / "Itim-Regular.ttf"
FONT_FAMILY = "Tahoma"      # ใช้สำรองถ้าหาไฟล์ฟอนต์ไม่เจอ


def load_font():
    global FONT_FAMILY
    if FONT_FILE.exists():
        fid = QFontDatabase.addApplicationFont(str(FONT_FILE))
        if fid >= 0:
            FONT_FAMILY = QFontDatabase.applicationFontFamilies(fid)[0]
    return FONT_FAMILY


def font(size, bold=False):
    f = QFont(FONT_FAMILY, size)
    f.setBold(bold)
    return f


# (สีพื้น, สี hover, สีขอบ, สีตัวอักษร) เลียนแบบปุ่มในภาพร่าง
BTN_YES = ("#6BD97A", "#5CCB6C", "#4CB85C", "#0F3D1A")
BTN_WAIT = ("#FFC940", "#F5B92A", "#E5A410", "#4A3500")
BTN_SKIP = ("#F4502D", "#E24220", "#C93516", "#FFFFFF")


class ActionButton(QPushButton):
    """ปุ่มมนเล็กน้อย: ข้อความหลักตัวใหญ่ + คำอธิบายเล็กๆ ด้านล่าง"""

    def __init__(self, title, sub, colors):
        super().__init__()
        base, hover, border, fg = colors
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(62)
        self.setMinimumWidth(116)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(f"""
            QPushButton {{ background:{base}; border:2px solid {border}; border-radius:10px; }}
            QPushButton:hover {{ background:{hover}; }}
            QPushButton:pressed {{ background:{border}; }}
            QLabel {{ background:transparent; color:{fg}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)
        t = QLabel(title)
        t.setFont(font(17))
        t.setAlignment(Qt.AlignCenter)
        s = QLabel(sub)
        s.setFont(font(10))
        s.setAlignment(Qt.AlignCenter)
        for w in (t, s):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)


class NannyPopup(QWidget):
    """buttons = [(title, sub, colors, callback), ...]"""

    def __init__(self, msg, buttons, accent="#4CAF50", badge="", footer="", on_closed=None):
        super().__init__()
        self._on_closed = on_closed
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)   # ไม่แย่งโฟกัสตอนพิมพ์งานอยู่

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 26)          # เผื่อที่ให้เงา

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            #card {{ background:#FFFFFF; border:2px solid {accent}; border-radius:18px; }}
            QLabel {{ background:transparent; }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 18, 26, 18)
        lay.setSpacing(0)

        # แถบหัว
        top = QHBoxLayout()
        brand = QLabel("Focus Nanny")
        brand.setFont(font(11))
        brand.setStyleSheet("color:#9A9A9A;")
        top.addWidget(brand)
        top.addStretch()
        if badge:
            pill = QLabel(badge)
            pill.setFont(font(10))
            pill.setStyleSheet(f"color:white; background:{accent}; border-radius:10px; padding:2px 12px;")
            top.addWidget(pill)
        lay.addLayout(top)

        # ข้อความหลัก
        text = QLabel(msg)
        text.setFont(font(20))
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("color:#1E1E1E;")
        text.setMinimumWidth(440)
        text.setContentsMargins(0, 26, 0, 26)
        lay.addWidget(text)

        # ปุ่ม
        row = QHBoxLayout()
        row.setSpacing(12)
        for title, sub, colors, cb in buttons:
            b = ActionButton(title, sub, colors)
            b.clicked.connect(lambda _=False, cb=cb: self.finish(cb))
            row.addWidget(b)
        lay.addLayout(row)

        if footer:
            f = QLabel(footer)
            f.setFont(font(10))
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


# =====================================================================
# ตัวบอทหลัก
# =====================================================================
class FocusNanny:
    # สีขอบ/ป้ายตามระดับความเข้มข้นของการเตือน
    LEVEL_COLORS = ["#4CAF50", "#F5B335", "#F28C28", "#E5493A"]

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        load_font()

        self.samples = deque()          # (timestamp, วินาทีที่เป็นสิ่งรบกวน) ใน sliding window
        self.last_tick = time.time()
        self.focus_streak = 0.0         # วินาทีที่ทำงานต่อเนื่องล่าสุด
        self.since_warn = 0.0           # วินาทีรบกวนสะสมนับจากเตือนครั้งล่าสุด
        self.warn_level = 0             # จำนวนครั้งที่เตือนไปแล้ว
        self.snooze_until = 0.0
        self.popup = None
        self.popup_open = False
        self.idle_notified = False
        self.last_reason = ""
        self.today = datetime.date.today()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)

    # ---------- ตัวนับเวลา ----------
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

    # ---------- วนตรวจ ----------
    def tick(self):
        try:
            self._tick()
        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")

    def _tick(self):
        now = time.time()
        dt = min(now - self.last_tick, 10)   # กันเครื่อง sleep แล้วนับเวลาก้อนใหญ่
        self.last_tick = now

        if datetime.date.today() != self.today:
            self.today = datetime.date.today()
            self.reset_episode()

        if self.popup_open:
            return

        title, proc = get_active_info()
        idle = get_idle_seconds()
        distracted, reason = check_distraction(title, proc) if title else (False, "")
        passive = distracted and is_passive_media(title, proc)

        # ไม่ได้แตะเครื่องนานแล้วไม่ใช่การดูวิดีโอ = ไม่อยู่หน้าจอ → ไม่นับ
        away = idle >= IDLE_AWAY_MINUTES * 60 and not passive
        counted = distracted and not away

        if counted:
            self.samples.append((now, dt))
            self.since_warn += dt
            self.focus_streak = 0.0
            self.last_reason = reason
        elif not distracted and not away:
            self.focus_streak += dt
            if self.focus_streak >= RESET_FOCUS_MINUTES * 60:
                self.reset_episode()

        total = self.window_total(now)
        need = interval_minutes(self.warn_level) * 60
        # ครั้งแรกดูจากยอดรวมใน sliding window, ครั้งต่อๆ ไปดูจากเวลานับตั้งแต่เตือนล่าสุด
        ready = total >= need if self.warn_level == 0 else self.since_warn >= need

        state = "รบกวน" if counted else ("ไม่อยู่หน้าจอ" if away else "โฟกัส")
        progress = total if self.warn_level == 0 else self.since_warn
        print(f"\r[{state}] {progress/60:4.1f}/{need/60:g} นาที (เตือนแล้ว {self.warn_level} ครั้ง) "
              f"| idle {idle:4.0f}s | {title[:35]:<35}", end="", flush=True)

        if counted and now >= self.snooze_until and ready:
            self.warn_distraction(total)
            return

        if not distracted and idle >= IDLE_NOTICE_MINUTES * 60:
            if not self.idle_notified:
                self.idle_notified = True
                self.notice_idle(idle)
        elif idle < 5:
            self.idle_notified = False

    # ---------- การแจ้งเตือน ----------
    def warn_distraction(self, total):
        self.warn_level += 1
        self.since_warn = 0.0
        lvl = self.warn_level
        mins = round(total / 60)

        if lvl == 1:
            msg = (f"ช่วง {WINDOW_MINUTES} นาทีที่ผ่านมา\nอยู่กับ {self.last_reason}\n"
                   f"รวมประมาณ {mins} นาทีแล้ว พักพอหรือยัง?")
        elif lvl == 2:
            msg = "งานยังรออยู่นะ\nลองกลับไปทำอีกนิด แล้วค่อยมาพักใหม่?"
        elif lvl == 3:
            msg = "นี่เตือนครั้งที่ 3 แล้วนะ\nเป้าหมายของวันนี้ยังไม่ขยับเลย"
        else:
            msg = f"เตือนครั้งที่ {lvl} แล้ว\nกลับไปทำงานกันเถอะ!"

        nxt = interval_minutes(lvl)
        accent = self.LEVEL_COLORS[min(lvl - 1, len(self.LEVEL_COLORS) - 1)]
        buttons = [
            ("YES", "กลับไปทำงาน", BTN_YES, self.on_back_to_work),
            ("WAIT", f"พัก {SNOOZE_MINUTES:g} นาที", BTN_WAIT, self.on_snooze),
            ("SKIP", "ไม่สนใจ", BTN_SKIP, self.on_skip),
        ]
        self.show_popup(msg, buttons, accent=accent, badge=f"เตือนครั้งที่ {lvl}",
                        footer=f"ถ้ายังไม่กลับไปทำงาน จะเตือนอีกใน {nxt:g} นาที")

    def notice_idle(self, idle):
        msg = f"หน้าจอนิ่งมา {int(idle // 60)} นาทีแล้ว\nยังอยู่ไหม? ลุกยืดเส้นยืดสายหน่อยก็ดีนะ"
        self.show_popup(msg, [("OK", "รับทราบ", BTN_YES, lambda: None)],
                        accent="#4CAF50", badge="ยังอยู่ไหม?")

    def on_back_to_work(self):
        self.reset_episode()      # ล้างทั้งตัวนับและระดับความถี่

    def on_snooze(self):
        self.snooze_until = time.time() + SNOOZE_MINUTES * 60
        print(f"\n[i] พักการเตือน {SNOOZE_MINUTES:g} นาที")

    def on_skip(self):
        
        
        print(f"\n[i] ข้าม (เตือนครั้งถัดไปใน {interval_minutes(self.warn_level):g} นาที)")

    def _popup_closed(self):
        self.popup_open = False
        self.last_tick = time.time()

    def show_popup(self, msg, buttons, **kw):
        self.popup_open = True
        self.popup = NannyPopup(msg, buttons, on_closed=self._popup_closed, **kw)

    def run(self):
        print("Focus Nanny เริ่มทำงาน (กด Ctrl+C ที่ console เพื่อหยุด)")
        seq = " → ".join(f"{x:g}" for x in WARN_INTERVALS)
        print(f"ช่วงห่างการเตือน (นาที): {seq} (ค้างที่ค่าสุดท้าย)\n")
        signal.signal(signal.SIGINT, lambda *_: self.app.quit())
        self.timer.start(int(TICK_SECONDS * 1000))   # timer นี้ปลุก Python ให้รับ Ctrl+C ด้วย
        self.app.exec()
        print("\nหยุดทำงานแล้ว")


if __name__ == "__main__":
    FocusNanny().run()




