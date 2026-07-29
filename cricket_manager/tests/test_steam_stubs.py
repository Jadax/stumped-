"""Steam preparation contract tests; no Steam client is required."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database
from src.steam_integration import ACHIEVEMENTS, SteamIntegration


class SteamStubTests(unittest.TestCase):
    def test_forty_unique_achievements(self) -> None:
        self.assertEqual(len(ACHIEVEMENTS), 40)
        self.assertEqual(len({item.id for item in ACHIEVEMENTS}), 40)
        self.assertIn("ACH_CENTURY_MAKER", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_FIVE_WICKET_HAUL", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_FIRST_WIN", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_PROMOTION_PARTY", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_ASHES_LEGEND", {item.id for item in ACHIEVEMENTS})
        self.assertIn("ACH_TEST_DEBUT", {item.id for item in ACHIEVEMENTS})

    def test_stub_calls_succeed_and_achievement_persists(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); steam = SteamIntegration(root, 123, 456, root / "Steam")
            self.assertTrue(steam.initialise()); self.assertTrue(steam.open_overlay())
            self.assertTrue(steam.unlock_achievement("ACH_CENTURY_MAKER")); self.assertTrue(steam.shutdown())
            restored = SteamIntegration(root, 123, 456, root / "Steam"); restored.initialise()
            self.assertIn("ACH_CENTURY_MAKER", restored.unlocked)

    def test_cloud_round_trip(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); original = root / "original.db"; restored = root / "restored.db"
            initialise_database(original)
            steam = SteamIntegration(root, 123, 456, root / "Steam"); steam.initialise()
            self.assertTrue(steam.cloud_save(original)); self.assertTrue(steam.cloud_load(restored))
            self.assertGreater(restored.stat().st_size, 0)

    def test_evaluate_match_unlocks_achievements(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); steam = SteamIntegration(root, 123, 456, root / "Steam"); steam.initialise()
            # Test match with a century
            result = {"format": "T20", "innings": [{"batting": [{"runs": 105, "balls": 80}], "bowling": []}]}
            self.assertTrue(steam.evaluate_match(result, 1))
            self.assertIn("ACH_CENTURY_MAKER", steam.unlocked)
            # Test match with a five-wicket haul
            result2 = {"format": "T20", "innings": [{"batting": [], "bowling": [{"wickets": 5}]}]}
            self.assertTrue(steam.evaluate_match(result2, 1))
            self.assertIn("ACH_FIVE_WICKET_HAUL", steam.unlocked)
            # Test Test match
            result3 = {"format": "Test", "innings": []}
            self.assertTrue(steam.evaluate_match(result3, 1))
            self.assertIn("ACH_TEST_DEBUT", steam.unlocked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
