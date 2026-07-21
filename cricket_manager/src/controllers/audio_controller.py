"""Failure-safe audio playback and a tiny event bus for game sounds."""
from __future__ import annotations

from collections import defaultdict
import logging
from pathlib import Path
import sys
from typing import Any, Callable

try:
    import pygame
except ImportError:  # Packaging/startup code may inspect this module without SDL.
    pygame = None  # type: ignore[assignment]


LOGGER = logging.getLogger("stumped")


class AudioEventBus:
    """Simple synchronous event bus that isolates producers from pygame audio."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if callback in self._subscribers.get(event_name, []):
            self._subscribers[event_name].remove(callback)

    def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        for callback in tuple(self._subscribers.get(event_name, [])):
            try:
                callback(payload or {})
            except Exception:
                LOGGER.warning(f"Audio event subscriber failed for {event_name}", exc_info=True)


_EVENT_BUS = AudioEventBus()


def get_audio_event_bus() -> AudioEventBus:
    return _EVENT_BUS


class AudioManager:
    """Singleton owner for optional match-crowd effects, mute, and volume.

    Missing files, unavailable sound devices, and mixer errors are non-fatal.
    The game simply continues silently, which is important on remote desktops
    and machines without an enabled Windows audio device.
    """

    _instance: "AudioManager | None" = None
    EFFECT_FILES = {
        "boundary": "boundary.wav",
        "six": "crowd.wav",
        "wicket": "wicket.wav",
        "close_call": "run.wav",
        "applause": "crowd.wav",
        "ambience": "crowd.wav",
    }
    AMBIENCE_SCALE = 0.32

    def __new__(cls) -> "AudioManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._constructed = False
        return cls._instance

    def __init__(self) -> None:
        if self._constructed: return
        self._constructed = True
        self.initialised = False
        self.available = False
        self.muted = False
        self.master_volume = 70
        self.effects: dict[str, Any] = {}
        self._subscribed = False
        self._ambience_channel: Any = None

    @staticmethod
    def resource_path(path: Path) -> Path:
        """Resolve normal source paths and PyInstaller's temporary bundle."""
        root = Path(getattr(sys, "_MEIPASS", path.parents[1]))
        bundled = root / "assets" / "audio" / path.name
        return bundled if hasattr(sys, "_MEIPASS") else path

    def initialise(self, audio_directory: str | Path, *, volume: int = 70, muted: bool = False) -> bool:
        self.master_volume = max(0, min(100, int(volume)))
        self.muted = bool(muted)
        if pygame is None:
            LOGGER.warning("Pygame is unavailable; audio disabled")
            return False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44_100, -16, 2, 512)
                pygame.mixer.init()
            directory = Path(audio_directory)
            self.effects.clear()
            for name, filename in self.EFFECT_FILES.items():
                path = self.resource_path(directory / filename)
                if path.exists():
                    self.effects[name] = pygame.mixer.Sound(str(path))
                else:
                    LOGGER.warning(f"Optional audio file missing: {path}")
            self.initialised = self.available = True
            self._apply_volumes()
            if not self._subscribed:
                get_audio_event_bus().subscribe("match.delivery", self._on_match_delivery)
                self._subscribed = True
            LOGGER.info(f"Audio initialised with {len(self.effects)} effects")
            return True
        except Exception:
            self.initialised = self.available = False
            LOGGER.warning("Audio device could not be initialised; continuing silently", exc_info=True)
            return False

    @property
    def effective_volume(self) -> float:
        return 0.0 if self.muted else self.master_volume / 100.0

    def _apply_volumes(self) -> None:
        if not self.available or pygame is None: return
        for sound in self.effects.values(): sound.set_volume(self.effective_volume)
        ambience = self.effects.get("ambience")
        if ambience is not None: ambience.set_volume(self.effective_volume * self.AMBIENCE_SCALE)

    def start_ambience(self) -> None:
        """Loop a low continuous crowd bed under the match sounds."""
        if not self.available or pygame is None: return
        ambience = self.effects.get("ambience")
        if ambience is None: return
        try:
            if self._ambience_channel is None or not self._ambience_channel.get_busy():
                ambience.set_volume(self.effective_volume * self.AMBIENCE_SCALE)
                self._ambience_channel = ambience.play(loops=-1, fade_ms=1800)
        except pygame.error:
            LOGGER.warning("Could not start crowd ambience", exc_info=True)

    def stop_ambience(self) -> None:
        if self._ambience_channel is not None:
            try: self._ambience_channel.fadeout(700)
            except Exception: pass
            self._ambience_channel = None

    def _duck_ambience(self) -> None:
        """Dip the crowd bed under a big moment, then fade it back in."""
        ambience = self.effects.get("ambience")
        if ambience is None or self._ambience_channel is None or pygame is None: return
        try:
            if self._ambience_channel.get_busy():
                self._ambience_channel = ambience.play(loops=-1, fade_ms=4200)
        except pygame.error:
            pass

    def set_volume(self, value: int | float) -> None:
        self.master_volume = max(0, min(100, round(float(value))))
        self._apply_volumes()

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)
        self._apply_volumes()

    def play_effect(self, name: str, *, volume_scale: float = 1.0) -> bool:
        if not self.available or self.muted or pygame is None: return False
        sound = self.effects.get(name)
        if sound is None: return False
        try:
            sound.set_volume(max(0.0, min(1.0, self.effective_volume * volume_scale)))
            sound.play()
            return True
        except pygame.error:
            LOGGER.warning(f"Could not play sound effect: {name}", exc_info=True)
            return False

    def _on_match_delivery(self, event: dict[str, Any]) -> None:
        result = str(event.get("result", ""))
        self.start_ambience()
        if event.get("wicket") or result == "W":
            self._duck_ambience()
            self.play_effect("wicket")
        elif event.get("reviewable") and not event.get("wicket"):
            self.play_effect("close_call", volume_scale=.75)
        elif result == "6":
            self.play_effect("six", volume_scale=1.0)
        elif result == "4":
            self.play_effect("boundary", volume_scale=.82)
        elif event.get("kind") == "milestone":
            self.play_effect("applause", volume_scale=.9)

    def shutdown(self) -> None:
        self.stop_ambience()
        self.effects.clear()
        self.available = self.initialised = False
