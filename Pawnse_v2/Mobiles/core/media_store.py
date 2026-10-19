"""Offline music and sound-effect storage for Pawse."""

from __future__ import annotations

import math
import shutil
import struct
import wave
from pathlib import Path

from core.config import data_dir

PLAYABLE_MEDIA_EXTENSIONS = {".mp3", ".mp4"}
SOUND_EFFECTS = {
    "focus_click": ((587.33, 0.10),),
    "task_click": ((783.99, 0.09),),
    "edit_click": ((523.25, 0.08), (659.25, 0.10)),
    "meow_warning": ((659.25, 0.14), (523.25, 0.16), (440.00, 0.20)),
}


def music_directory() -> Path:
    return data_dir() / "music"


def sfx_directory() -> Path:
    return data_dir() / "sfx"


def ensure_default_track() -> Path:
    """Ensure the local music library has at least one playable media file."""
    directory = music_directory()
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if (path.is_file() and path.suffix.lower() in PLAYABLE_MEDIA_EXTENSIONS
                and path.stat().st_size > 0):
            return path

    bundled_track = Path(__file__).resolve().parent.parent / "assets" / "default_cozy_theme.mp3"
    if not bundled_track.is_file():
        raise FileNotFoundError(f"The bundled Pawse music track is missing: {bundled_track}")
    target = directory / "default_cozy_theme.mp3"
    shutil.copy2(bundled_track, target)
    return target


def _write_sound_effect(path: Path, notes) -> None:
    sample_rate = 22050
    samples = bytearray()
    for frequency, duration in notes:
        frame_count = int(sample_rate * duration)
        for index in range(frame_count):
            elapsed = index / sample_rate
            attack = min(1.0, elapsed / 0.012)
            release = min(1.0, (frame_count - index) / (sample_rate * 0.045))
            envelope = min(attack, release)
            tone = math.sin(2 * math.pi * frequency * elapsed)
            overtone = math.sin(2 * math.pi * frequency * 2 * elapsed) * 0.16
            sample = int(32767 * 0.18 * envelope * (tone + overtone))
            samples.extend(struct.pack("<h", sample))

    with wave.open(str(path), "wb") as sound_file:
        sound_file.setnchannels(1)
        sound_file.setsampwidth(2)
        sound_file.setframerate(sample_rate)
        sound_file.writeframes(samples)


def ensure_sound_effects() -> Path:
    """Create gentle local WAV defaults without replacing user-provided effects."""
    directory = sfx_directory()
    directory.mkdir(parents=True, exist_ok=True)
    for name, notes in SOUND_EFFECTS.items():
        path = directory / f"{name}.wav"
        if not path.exists():
            _write_sound_effect(path, notes)
    return directory
