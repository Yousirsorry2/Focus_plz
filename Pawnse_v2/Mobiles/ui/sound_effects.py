"""Cached Qt sound effects loaded from Pawse's local sfx directory."""

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication

from core.media_store import SOUND_EFFECTS, sfx_directory

_sound_effects = None


class _SoundEffects:
    def __init__(self):
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("Qt must be initialized before loading Pawse sound effects.")
        self.effects = {}
        for name in SOUND_EFFECTS:
            effect = QSoundEffect(app)
            effect.setSource(QUrl.fromLocalFile(str(sfx_directory() / f"{name}.wav")))
            effect.setVolume(1)
            effect.statusChanged.connect(
                lambda name=name, effect=effect: self._report_error(name, effect))
            self.effects[name] = effect

    @staticmethod
    def _report_error(name, effect):
        if effect.status() == QSoundEffect.Error:
            print(f"[Pawse audio] could not load {name}.wav: {effect.source().toLocalFile()}")

    def play(self, name):
        effect = self.effects.get(name)
        if effect is None:
            raise ValueError(f"Unknown Pawse sound effect: {name}")
        effect.play()


def initialize_sound_effects() -> None:
    global _sound_effects
    if _sound_effects is None:
        _sound_effects = _SoundEffects()


def play_sound_effect(name: str) -> None:
    if _sound_effects is None:
        initialize_sound_effects()
    _sound_effects.play(name)
