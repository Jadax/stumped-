"""Tests for AI pitch selection and match ground persistence (v4.97.0)."""
import os
import sys
import tempfile
import unittest
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialise_database, get_ground_info
from src.models.ai_pitch_selection import choose_ai_pitch, describe_pitch_choice, PITCH_TYPES


class ChooseAIPitchTests(unittest.TestCase):
    """Test the AI pitch selection function."""

    def test_returns_valid_pitch(self):
        for _ in range(20):
            result = choose_ai_pitch("balanced", 60, 55)
            self.assertIn(result, PITCH_TYPES)

    def test_pace_affinity_prefers_green_or_dry(self):
        results = [choose_ai_pitch("pace", 60, 55, rng=random.Random(i)) for i in range(100)]
        green_dry = sum(1 for r in results if r in ("Green", "Dry"))
        self.assertGreater(green_dry, 30)

    def test_spin_affinity_prefers_dusty_or_worn(self):
        results = [choose_ai_pitch("spin", 60, 55, rng=random.Random(i)) for i in range(100)]
        dusty_worn = sum(1 for r in results if r in ("Dusty", "Worn"))
        self.assertGreater(dusty_worn, 30)

    def test_weak_pace_opponent_prefers_pace_pitches(self):
        results = [choose_ai_pitch("balanced", 60, 55, opp_technique_vs_pace=30,
                                   rng=random.Random(i)) for i in range(100)]
        green_dry = sum(1 for r in results if r in ("Green", "Dry"))
        self.assertGreater(green_dry, 35)

    def test_weak_spin_opponent_prefers_spin_pitches(self):
        results = [choose_ai_pitch("balanced", 60, 55, opp_technique_vs_spin=30,
                                   rng=random.Random(i)) for i in range(100)]
        dusty_worn = sum(1 for r in results if r in ("Dusty", "Worn"))
        self.assertGreater(dusty_worn, 35)

    def test_strong_batting_prefers_flat(self):
        results = [choose_ai_pitch("balanced", 75, 55, rng=random.Random(i)) for i in range(100)]
        flat = sum(1 for r in results if r == "Flat")
        self.assertGreater(flat, 15)

    def test_deterministic_with_seed(self):
        r1 = [choose_ai_pitch("balanced", 60, 55, rng=random.Random(42)) for _ in range(5)]
        r2 = [choose_ai_pitch("balanced", 60, 55, rng=random.Random(42)) for _ in range(5)]
        self.assertEqual(r1, r2)


class DescribePitchChoiceTests(unittest.TestCase):
    def test_with_reason(self):
        result = describe_pitch_choice("Green", "opposition weak against pace")
        self.assertIn("Green", result)
        self.assertIn("opposition weak against pace", result)

    def test_without_reason(self):
        result = describe_pitch_choice("Dusty")
        self.assertIn("Dusty", result)


class PitchUsedMigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_pitch_used_defaults_to_green(self):
        from database import connect
        with connect(self.db) as conn:
            conn.execute(
                "INSERT INTO matches (home_team,away_team,format,date,venue,completed,result_json) "
                "VALUES (1,2,'T20','2026-08-17','Test Ground',0,'{}')")
            row = conn.execute("SELECT pitch_used FROM matches LIMIT 1").fetchone()
        self.assertEqual(row["pitch_used"], "Green")


class GroundInfoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_ground_info_has_pitch_affinity(self):
        ground = get_ground_info(1, self.db)
        self.assertIn("pitch_affinity", ground)
        self.assertIn(ground["pitch_affinity"], ("pace", "spin", "balanced"))

    def test_ground_info_has_boundary_size(self):
        ground = get_ground_info(1, self.db)
        self.assertIn("boundary_size", ground)
        self.assertIsInstance(ground["boundary_size"], int)


if __name__ == "__main__":
    unittest.main()
