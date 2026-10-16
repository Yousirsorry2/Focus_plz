"""Pawse - local, offline task storage (SQLite: tasks.db).

Every mutating call commits immediately, so nothing is lost if the app is
killed. Times are stored as naive local ISO strings ("2026-10-16T09:30").
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import json

from core.config import data_dir

DB_PATH = data_dir() / "tasks.db"

FREQUENCIES = ["Once", "Daily", "Weekdays", "Weekly", "Monthly"]
DEFAULT_CATEGORIES = [("Work", "#FFD1BA"), ("Personal", "#C8E6C9"), ("Study", "#D6E4F5")]
SWATCHES = ["#FFD1BA", "#C8E6C9", "#D6E4F5", "#E8DAEF", "#FFF1B8", "#F8C8DC"]
REMINDER_WINDOW_MINUTES = 2  # short enough to keep adjacent Smart Deadline milestones distinct
SMART_LEAD_MINUTES = 15  # retained for compatibility with older callers
SMART_MILESTONES = [10080, 2880, 1440, 120, 60, 30, 15, 5, 0]
DEFAULT_REMINDER_PRESETS = [0, 5, 15, 30, 60, 120, 1440, 2880, 10080]

_COLUMNS = {"title", "category_name", "category_color", "start_time", "frequency",
            "is_smart_deadline", "deadline_time", "reminder_minutes", "is_completed"}


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def parse_iso(value):
    try:
        return dt.datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


class TaskStore:
    def __init__(self, path=None):
        self.db = sqlite3.connect(str(path or DB_PATH))
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    # ---- schema -----------------------------------------------------
    def _init_schema(self):
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    title             TEXT    NOT NULL,
                    category_name     TEXT    NOT NULL DEFAULT 'Personal',
                    category_color    TEXT    NOT NULL DEFAULT '#C8E6C9',
                    start_time        TEXT,
                    frequency         TEXT    NOT NULL DEFAULT 'Once',
                    is_smart_deadline INTEGER NOT NULL DEFAULT 0,
                    deadline_time     TEXT,
                    reminder_minutes  TEXT    NOT NULL DEFAULT '[0]',
                    is_completed      INTEGER NOT NULL DEFAULT 0,
                    created_at        TEXT    NOT NULL
                )""")
            # Safe migration for databases created by an earlier Pawse version.
            columns = {r[1] for r in self.db.execute("PRAGMA table_info(tasks)")}
            if "reminder_minutes" not in columns:
                self.db.execute("ALTER TABLE tasks ADD COLUMN reminder_minutes TEXT NOT NULL DEFAULT '[0]'")
            self.db.execute("""CREATE TABLE IF NOT EXISTS reminder_presets (
                minutes INTEGER PRIMARY KEY
            )""")
            for minutes in DEFAULT_REMINDER_PRESETS:
                self.db.execute("INSERT OR IGNORE INTO reminder_presets(minutes) VALUES (?)", (minutes,))
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    name  TEXT PRIMARY KEY,
                    color TEXT NOT NULL,
                    pos   INTEGER NOT NULL
                )""")
            if self.db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
                self.db.executemany("INSERT INTO categories (name, color, pos) VALUES (?, ?, ?)",
                                    [(n, c, i) for i, (n, c) in enumerate(DEFAULT_CATEGORIES)])

    @staticmethod
    def _task(row) -> dict:
        d = dict(row)
        d["is_smart_deadline"] = bool(d["is_smart_deadline"])
        d["is_completed"] = bool(d["is_completed"])
        try:
            d["reminder_minutes"] = sorted({max(0, int(x)) for x in json.loads(d["reminder_minutes"] or "[0]")}, reverse=True)
        except (TypeError, ValueError, json.JSONDecodeError):
            d["reminder_minutes"] = [0]
        return d

    # ---- tasks ------------------------------------------------------
    def add_task(self, title, category_name="Personal", category_color="#C8E6C9", start_time=None,
                 frequency="Once", is_smart_deadline=False, deadline_time=None, reminder_minutes=None) -> int:
        values = [0] if reminder_minutes is None else reminder_minutes
        reminders = json.dumps(sorted({max(0, int(x)) for x in values}, reverse=True))
        with self.db:
            cur = self.db.execute(
                "INSERT INTO tasks (title, category_name, category_color, start_time, frequency,"
                " is_smart_deadline, deadline_time, reminder_minutes, is_completed, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (title.strip(), category_name, category_color, start_time, frequency,
                 int(bool(is_smart_deadline)), deadline_time if is_smart_deadline else None, reminders, now_iso()))
        return cur.lastrowid

    def update_task(self, task_id, **fields):
        fields = {k: v for k, v in fields.items() if k in _COLUMNS}
        if not fields:
            return
        for k in ("is_smart_deadline", "is_completed"):
            if k in fields:
                fields[k] = int(bool(fields[k]))
        if "reminder_minutes" in fields:
            values = [0] if fields["reminder_minutes"] is None else fields["reminder_minutes"]
            fields["reminder_minutes"] = json.dumps(sorted({max(0, int(x)) for x in values}, reverse=True))
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.db:
            self.db.execute(f"UPDATE tasks SET {sets} WHERE id = ?", (*fields.values(), task_id))

    def set_completed(self, task_id, done: bool):
        self.update_task(task_id, is_completed=done)

    def delete_task(self, task_id):
        with self.db:
            self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def get_task(self, task_id):
        row = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task(row) if row else None

    def list_tasks(self, category=None, completed=None):
        q, args = "SELECT * FROM tasks WHERE 1=1", []
        if category and category != "All":
            q += " AND category_name = ?"
            args.append(category)
        if completed is not None:
            q += " AND is_completed = ?"
            args.append(int(completed))
        q += " ORDER BY is_completed, COALESCE(start_time, '9999'), id"
        return [self._task(r) for r in self.db.execute(q, args)]

    def counts(self):
        done, total = self.db.execute(
            "SELECT COALESCE(SUM(is_completed), 0), COUNT(*) FROM tasks").fetchone()
        return int(done), int(total)

    # ---- categories -------------------------------------------------
    def list_categories(self):
        return [dict(r) for r in self.db.execute("SELECT name, color FROM categories ORDER BY pos, name")]

    def category_color(self, name, default="#C8E6C9"):
        row = self.db.execute("SELECT color FROM categories WHERE name = ?", (name,)).fetchone()
        return row["color"] if row else default

    def add_category(self, name, color):
        name = name.strip()
        with self.db:
            pos = self.db.execute("SELECT COALESCE(MAX(pos), -1) + 1 FROM categories").fetchone()[0]
            self.db.execute(
                "INSERT INTO categories (name, color, pos) VALUES (?, ?, ?)"
                " ON CONFLICT(name) DO UPDATE SET color = excluded.color", (name, color, pos))
            self.db.execute("UPDATE tasks SET category_color = ? WHERE category_name = ?", (color, name))

    def reminder_presets(self):
        return [r["minutes"] for r in self.db.execute("SELECT minutes FROM reminder_presets ORDER BY minutes DESC")]

    def add_reminder_preset(self, minutes):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO reminder_presets(minutes) VALUES (?)", (max(0, int(minutes)),))

    def close(self):
        self.db.close()


# =====================================================================
# Reminder rules (pure functions, easy to test)
# =====================================================================
def occurs_on(start: dt.datetime, frequency: str, day: dt.date) -> bool:
    if day < start.date():
        return False
    return {
        "Once": day == start.date(),
        "Daily": True,
        "Weekdays": day.weekday() < 5,
        "Weekly": day.weekday() == start.weekday(),
        "Monthly": day.day == start.day,
    }.get(frequency, day == start.date())


def due_reminders(task: dict, now: dt.datetime):
    """Return named reminders whose small delivery window contains ``now``."""
    if task["is_completed"]:
        return []
    out = []
    start = parse_iso(task["start_time"])
    if start and occurs_on(start, task["frequency"], now.date()):
        at = dt.datetime.combine(now.date(), start.time())
        for minutes in task.get("reminder_minutes", [0]):
            due = at - dt.timedelta(minutes=minutes)
            if due <= now < due + dt.timedelta(minutes=REMINDER_WINDOW_MINUTES):
                out.append(f"reminder:{minutes}")
    deadline = parse_iso(task["deadline_time"]) if task["is_smart_deadline"] else None
    if deadline:
        for minutes in SMART_MILESTONES:
            due = deadline - dt.timedelta(minutes=minutes)
            if due <= now < due + dt.timedelta(minutes=REMINDER_WINDOW_MINUTES):
                out.append(f"smart:{minutes}")
    return out
