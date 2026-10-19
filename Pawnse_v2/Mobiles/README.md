# Pawse (Beta): My Tasks, Focus Guard & Smart Deadlines

## Install & run (Windows 10/11, Python 3.10+)
    pip install psutil pywin32 PySide6
    cd Mobile
    python main.py

Test mode: tick "Ultra Focus" in the window (reminders ~10x faster). `set PAWSE_TEST_MODE=1` starts with it on.
Data lives next to the app (`tasks.db`, `focus_nanny_config.json`); set `PAWSE_DATA_DIR` to move it.

## Layout
    main.py                    startup, four-tab navigation, tray notifications
    core/tracker.py            focus monitoring and scoped Focus Guard rules
    core/config.py             offline whitelist / blacklist JSON configuration
    core/task_store.py         SQLite tasks, reminder presets and milestone scheduling
    ui/focus_window.py         Focus session screen
    ui/popup.py                Focus Guard overlay and Mochi confirmation
    ui/tasks_view.py           My Tasks screen and task cards
    ui/add_task_dialog.py      Add / Edit sheet, split date/time and reminder options
    ui/date_time_picker.py     custom calendar and time picker dialogs
    ui/navigation.py           shared pastel four-tab mobile bottom navigation
    ui/utility_views.py        Offline music player, playlist library and Settings
    ui/sound_effects.py        Cached local Qt sound effects
    core/media_store.py        Music / SFX directories and generated WAV defaults
    ui/widgets.py              PawCheck and ToggleSwitch
    ui/tasks_theme.py          shared application QSS additions
    ui/mochi.py, ui/theme.py   Mochi illustration and palette

The app opens to **Tasks** in a 390 × 844 mobile-style layout with a persistent
bottom tab bar. Task lists and long forms scroll vertically; date and time are
edited in separate custom dialogs. Task dates, reminder selections, and saved
custom presets are stored locally. Scheduled task reminders use a separate
frameless Mochi modal showing the task and its event time.
Smart Deadline tasks schedule all nine milestone reminders. Focus Guard work
exceptions require confirmation and can be temporary (25 minutes) or permanent;
major entertainment targets can only be allowed manually from **Settings**.

The Music page imports MP3 audio and MP4 video into `PAWSE_DATA_DIR/music` for
offline playback. If that directory has no playable media, Pawse copies its
built-in cozy ambient MP3 there. Focus Guard and key task/focus interactions use
local WAV effects in `PAWSE_DATA_DIR/sfx`, generating gentle defaults when the
files are missing. Both folders remain alongside the app when `PAWSE_DATA_DIR`
is not set.

YouTube playlist/video links and Spotify playlist/track links are still
supported and saved locally, with playback embedded through Qt WebEngine.
Sign-in and playback availability for those links follow each provider's
account and embedded-player policies; no provider passwords are stored by
Pawse.
