"""Tests for squad cohesion system (v4.95.0)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import (
    fetch_squad_cohesion,
    initialise_database,
    update_squad_cohesion,
)
from src.models.squad_cohesion import (
    clamp_cohesion,
    cohesion_description,
    cohesion_label,
    consistency_bonus,
    draw_delta,
    loss_delta,
    match_modifier,
    promotion_delta,
    relegation_delta,
    rotation_penalty,
    trophy_delta,
    win_delta,
)


class ConsistencyBonusTests(unittest.TestCase):
    def test_fewer_than_six_repeated(self):
        self.assertEqual(consistency_bonus(0), 0)
        self.assertEqual(consistency_bonus(5), 0)

    def test_six_repeated(self):
        self.assertEqual(consistency_bonus(6), 1)

    def test_eight_repeated(self):
        self.assertEqual(consistency_bonus(8), 3)

    def test_full_xi_unchanged(self):
        self.assertEqual(consistency_bonus(11), 5)

    def test_scaling(self):
        self.assertEqual(consistency_bonus(7), 2)
        self.assertEqual(consistency_bonus(9), 4)
        self.assertEqual(consistency_bonus(10), 5)


class RotationPenaltyTests(unittest.TestCase):
    def test_three_or_fewer_new(self):
        self.assertEqual(rotation_penalty(0), 0)
        self.assertEqual(rotation_penalty(3), 0)

    def test_four_new(self):
        self.assertEqual(rotation_penalty(4), -1)

    def test_heavy_rotation(self):
        self.assertEqual(rotation_penalty(7), -4)
        self.assertEqual(rotation_penalty(11), -4)

    def test_scaling(self):
        self.assertEqual(rotation_penalty(5), -2)
        self.assertEqual(rotation_penalty(6), -3)


class WinLossDrawTests(unittest.TestCase):
    def test_home_win(self):
        self.assertEqual(win_delta(True, False), 4)

    def test_away_win(self):
        self.assertEqual(win_delta(False, False), 3)

    def test_comfortable_win_bonus(self):
        self.assertEqual(win_delta(True, True), 5)

    def test_home_loss(self):
        self.assertEqual(loss_delta(True, False), -3)

    def test_away_loss(self):
        self.assertEqual(loss_delta(False, False), -2)

    def test_heavy_loss_extra(self):
        self.assertEqual(loss_delta(True, True), -4)

    def test_draw(self):
        self.assertEqual(draw_delta(), 1)


class SeasonEventTests(unittest.TestCase):
    def test_promotion(self):
        self.assertEqual(promotion_delta(), 5)

    def test_relegation(self):
        self.assertEqual(relegation_delta(), -8)

    def test_trophy(self):
        self.assertEqual(trophy_delta(), 8)


class MatchModifierTests(unittest.TestCase):
    def test_neutral_at_50(self):
        self.assertAlmostEqual(match_modifier(50), 0.0)

    def test_high_cohesion_positive(self):
        mod = match_modifier(80)
        self.assertAlmostEqual(mod, 0.9, places=4)
        self.assertGreater(mod, 0)

    def test_low_cohesion_negative(self):
        mod = match_modifier(20)
        self.assertAlmostEqual(mod, -0.9, places=4)
        self.assertLess(mod, 0)

    def test_max_range(self):
        self.assertAlmostEqual(match_modifier(100), 1.5)
        self.assertAlmostEqual(match_modifier(0), -1.5)


class ClampTests(unittest.TestCase):
    def test_clamps_low(self):
        self.assertEqual(clamp_cohesion(-10), 0)

    def test_clamps_high(self):
        self.assertEqual(clamp_cohesion(120), 100)

    def test_no_change(self):
        self.assertEqual(clamp_cohesion(50), 50)


class LabelTests(unittest.TestCase):
    def test_united_at_90_plus(self):
        self.assertEqual(cohesion_label(95), "United")

    def test_solid_at_75_plus(self):
        self.assertEqual(cohesion_label(80), "Solid")

    def test_settled_at_60_plus(self):
        self.assertEqual(cohesion_label(65), "Settled")

    def test_uncertain_at_40_plus(self):
        self.assertEqual(cohesion_label(45), "Uncertain")

    def test_fragmented_at_25_plus(self):
        self.assertEqual(cohesion_label(30), "Fragmented")

    def test_toxic_below_25(self):
        self.assertEqual(cohesion_label(10), "Toxic")

    def test_description_high(self):
        desc = cohesion_description(85, "Test CC")
        self.assertIn("Test CC", desc)
        self.assertIn("know each other", desc)

    def test_description_low(self):
        desc = cohesion_description(10, "Test CC")
        self.assertIn("Test CC", desc)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_default_cohesion_is_50(self):
        cohesion = fetch_squad_cohesion(1, self.db)
        self.assertEqual(cohesion, 50)

    def test_update_squad_cohesion(self):
        new_cohesion = update_squad_cohesion(1, 10, self.db)
        self.assertEqual(new_cohesion, 60)

    def test_update_clamps(self):
        new_cohesion = update_squad_cohesion(1, 200, self.db)
        self.assertEqual(new_cohesion, 100)
        new_cohesion = update_squad_cohesion(1, -300, self.db)
        self.assertEqual(new_cohesion, 0)

    def test_multiple_updates(self):
        update_squad_cohesion(1, 10, self.db)
        update_squad_cohesion(1, -3, self.db)
        self.assertEqual(fetch_squad_cohesion(1, self.db), 57)


class IntegrationTests(unittest.TestCase):
    def test_consistency_plus_win(self):
        from src.models.squad_cohesion import clamp_cohesion
        cohesion = 50
        cohesion = clamp_cohesion(cohesion + consistency_bonus(10))
        cohesion = clamp_cohesion(cohesion + win_delta(True, True))
        self.assertEqual(cohesion, 60)

    def test_heavy_rotation_plus_loss(self):
        from src.models.squad_cohesion import clamp_cohesion
        cohesion = 50
        cohesion = clamp_cohesion(cohesion + rotation_penalty(8))
        cohesion = clamp_cohesion(cohesion + loss_delta(True, True))
        self.assertEqual(cohesion, 42)


if __name__ == "__main__":
    unittest.main()
