"""Checks for the broadcast matchday presentation layer (v0.12.0)."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


class BroadcastPresentationTests(unittest.TestCase):
    def test_momentum_tab_is_registered(self) -> None:
        from ui.match_view import MatchScreen
        self.assertIn("Momentum", MatchScreen.STAT_TABS)

    def test_ambience_effect_is_declared(self) -> None:
        from src.controllers.audio_controller import AudioManager
        self.assertIn("ambience", AudioManager.EFFECT_FILES)
        self.assertTrue(0 < AudioManager.AMBIENCE_SCALE < 1)

    def test_ambience_controls_are_safe_without_audio_device(self) -> None:
        from src.controllers.audio_controller import AudioManager
        manager = AudioManager()
        manager.available = False
        manager.start_ambience()
        manager._duck_ambience()
        manager.stop_ambience()
        manager._on_match_delivery({"result": "W", "wicket": True})

    def test_delivery_bus_reaches_audio_manager(self) -> None:
        from src.controllers.audio_controller import get_audio_event_bus
        received = []
        bus = get_audio_event_bus()
        bus.subscribe("match.delivery", received.append)
        try:
            bus.emit("match.delivery", {"result": "4"})
        finally:
            bus.unsubscribe("match.delivery", received.append)
        self.assertEqual(received, [{"result": "4"}])


if __name__ == "__main__":
    unittest.main()
