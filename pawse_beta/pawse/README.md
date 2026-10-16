# Pawse (Beta): Focus Mode + Focus Guard

## Install & run (Windows 10/11, Python 3.10+)
    pip install psutil pywin32 PySide6
    python main.py

Test mode: tick the "Ultra Focus" box in the window (reminders ~10x faster). `set PAWSE_TEST_MODE=1` starts with it on.

## Layout
    main.py              entry point, system tray, wires tracker <-> UI
    core/tracker.py      window/idle probes, keyword scoring, sliding window, escalation, snooze
    ui/focus_window.py   Focus Mode screen (25:00 timer, Pause/Resume, End session, task bar)
    ui/popup.py          Focus Guard overlay (Back to Work / Snooze / Skip)
    ui/mochi.py          Mochi the cat, vector-drawn with QPainter
    ui/theme.py          palette tokens + QSS (#FDFBF7 #FFD1BA #C8E6C9 #4A403A)
