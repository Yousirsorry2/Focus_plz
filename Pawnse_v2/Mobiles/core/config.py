"""Pawse local storage paths + the persistent focus_nanny_config.json.

Everything lives next to the app by default (works fully offline). Set the
PAWSE_DATA_DIR environment variable to keep data somewhere else.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

def data_dir() -> Path:
    env = os.environ.get("PAWSE_DATA_DIR")
    local_appdata = os.environ.get("LOCALAPPDATA")
    if env:
        d = Path(env)
    elif local_appdata:
        # ดึงตำแหน่ง AppData/Local ของ Windows
        d = Path(local_appdata) / "Pawse"
    else:
        # Fallback กรณีระบบอื่น
        d = Path.home() / ".pawse"

    d.mkdir(parents=True, exist_ok=True)
    return d



CONFIG_PATH = data_dir() / "focus_nanny_config.json"

# What "Mark as Work" learns. All values are lower-case strings.
DEFAULTS = {
    "productive_keywords": [],              # pages / domains / keywords the user marked as work
    "productive_processes": [],             # apps the user marked as work
    "removed_distraction_processes": [],    # built-in distraction apps the user cleared
    "removed_distraction_sites": [],        # built-in distraction keywords the user cleared
    "custom_distraction_processes": [],
    "custom_distraction_sites": [],
    "manual_productive_processes": [],
    "manual_productive_keywords": [],
}


def load_config(path=None) -> dict:
    path = Path(path or CONFIG_PATH)
    cfg = {k: list(v) for k, v in DEFAULTS.items()}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for k, v in raw.items():
                if k in cfg:
                    cfg[k] = [str(x) for x in v] if isinstance(v, list) else cfg[k]
                else:
                    cfg[k] = v            # keep unknown keys untouched
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:    # corrupt file: start clean, don't crash the app
        print(f"[Pawse config] could not read {path.name}: {e}")
    return cfg


def save_config(cfg: dict, path=None) -> None:
    """Atomic write (temp file + replace) so a crash never leaves a half-written file."""
    path = Path(path or CONFIG_PATH)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".cfg_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
