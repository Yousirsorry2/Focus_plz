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
    ui/utility_views.py        Music playlist library and Settings destination
    ui/widgets.py              PawCheck and ToggleSwitch
    ui/tasks_theme.py          shared application QSS additions
    ui/mochi.py, ui/theme.py   Mochi illustration and palette

The app opens to **Tasks** in a 390 × 844 mobile-style layout with a persistent
bottom tab bar. Task lists and long forms scroll vertically; date and time are
edited in separate custom dialogs. Task dates, reminder selections, and saved
custom presets are stored locally.
Smart Deadline tasks schedule all nine milestone reminders. Focus Guard work
exceptions require confirmation and can be temporary (25 minutes) or permanent;
major entertainment targets can only be allowed manually from **Settings**.

The Music page accepts YouTube playlist/video links and Spotify playlist/track
links, saves them locally, and embeds each provider's player in the app using
Qt WebEngine. Sign-in and playback availability follow each provider's account
and embedded-player policies; no provider passwords are stored by Pawse.
