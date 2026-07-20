"""Steam preparation contract tests; no Steam client is required."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database
from src.steam_integration import ACHIEVEMENTS, SteamIntegration


class SteamStubTests(unittest.TestCase):
    def test_twenty_unique_achievements(self) -> None:
        self.assertEqual(len(ACHIEVEMENTS), 20)
        self.assertEqual(len({item.id for item in ACHIEVEMENTS}), 20)
        self.assertIn("ACH_CENTURY", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_FIVE_WICKET", {item.id for item in ACHIEVEMENTS})

    def test_stub_calls_succeed_and_achievement_persists(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); steam = SteamIntegration(root, 123, 456, root / "Steam")
            self.assertTrue(steam.initialise()); self.assertTrue(steam.open_overlay())
            self.assertTrue(steam.unlock_achievement("ACH_CENTURY")); self.assertTrue(steam.shutdown())
            restored = SteamIntegration(root, 123, 456, root / "Steam"); restored.initialise()
            self.assertIn("ACH_CENTURY", restored.unlocked)

    def test_cloud_round_trip(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); original = root / "original.db"; restored = root / "restored.db"
            initialise_database(original)
            steam = SteamIntegration(root, 123, 456, root / "Steam"); steam.initialise()
            self.assertTrue(steam.cloud_save(original)); self.assertTrue(steam.cloud_load(restored))
            self.assertGreater(restored.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
