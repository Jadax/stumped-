"""Tests for fan sentiment system (v4.93.0)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import (
    fetch_fan_morale,
    initialise_database,
    update_fan_morale,
)
from src.models.fan_sentiment import (
    clamp_morale,
    demand_modifier,
    draw_delta,
    loss_delta,
    morale_description,
    morale_label,
    streak_bonus,
    streak_penalty,
    title_delta,
    trophy_delta,
    promotion_delta,
    relegation_delta,
    win_delta,
)


class WinDeltaTests(unittest.TestCase):
    def test_home_win(self):
        self.assertEqual(win_delta(True, False, False), 6)

    def test_away_win(self):
        self.assertEqual(win_delta(False, False, False), 4)

    def test_comfortable_win_bonus(self):
        self.assertEqual(win_delta(True, True, False), 8)

    def test_derby_bonus(self):
        self.assertEqual(win_delta(True, False, True), 9)

    def test_comfortable_derby_away_win(self):
        self.assertEqual(win_delta(False, True, True), 9)


class LossDeltaTests(unittest.TestCase):
    def test_home_loss(self):
        self.assertEqual(loss_delta(True, False, False), -5)

    def test_away_loss(self):
        self.assertEqual(loss_delta(False, False, False), -3)

    def test_heavy_defeat_penalty(self):
        self.assertEqual(loss_delta(True, True, False), -7)

    def test_derby_loss_extra_hit(self):
        self.assertEqual(loss_delta(True, False, True), -8)


class DrawDeltaTests(unittest.TestCase):
    def test_draw_positive(self):
        self.assertEqual(draw_delta(), 1)


class StreakTests(unittest.TestCase):
    def test_no_streak_below_three(self):
        self.assertEqual(streak_bonus(2), 0)
        self.assertEqual(streak_penalty(2), 0)

    def test_three_win_streak(self):
        self.assertEqual(streak_bonus(3), 3)

    def test_five_win_streak_capped(self):
        self.assertEqual(streak_bonus(5), 5)
        self.assertEqual(streak_bonus(10), 5)

    def test_three_loss_streak(self):
        self.assertEqual(streak_penalty(3), -3)

    def test_six_loss_streak_capped(self):
        self.assertEqual(streak_penalty(6), -6)
        self.assertEqual(streak_penalty(10), -6)


class TrophyPromotionRelegationTests(unittest.TestCase):
    def test_trophy_delta(self):
        self.assertEqual(trophy_delta(), 15)

    def test_promotion_delta(self):
        self.assertEqual(promotion_delta(), 10)

    def test_relegation_delta(self):
        self.assertEqual(relegation_delta(), -12)

    def test_title_delta(self):
        self.assertEqual(title_delta(), 10)


class ClampTests(unittest.TestCase):
    def test_clamps_low(self):
        self.assertEqual(clamp_morale(-5), 0)

    def test_clamps_high(self):
        self.assertEqual(clamp_morale(120), 100)

    def test_no_change_mid(self):
        self.assertEqual(clamp_morale(50), 50)


class DemandModifierTests(unittest.TestCase):
    def test_neutral_at_50(self):
        self.assertAlmostEqual(demand_modifier(50), 0.0)

    def test_positive_at_100(self):
        mod = demand_modifier(100)
        self.assertAlmostEqual(mod, 0.025, places=4)
        self.assertGreater(mod, 0)

    def test_negative_at_0(self):
        mod = demand_modifier(0)
        self.assertAlmostEqual(mod, -0.025, places=4)
        self.assertLess(mod, 0)


class LabelTests(unittest.TestCase):
    def test_ecstatic_at_90_plus(self):
        self.assertEqual(morale_label(95), "Ecstatic")
        self.assertEqual(morale_label(90), "Ecstatic")

    def test_happy_at_75_plus(self):
        self.assertEqual(morale_label(80), "Happy")
        self.assertEqual(morale_label(75), "Happy")

    def test_content_at_60_plus(self):
        self.assertEqual(morale_label(65), "Content")

    def test_restless_at_40_plus(self):
        self.assertEqual(morale_label(45), "Restless")

    def test_unhappy_at_25_plus(self):
        self.assertEqual(morale_label(30), "Unhappy")

    def test_furious_below_25(self):
        self.assertEqual(morale_label(10), "Furious")
        self.assertEqual(morale_label(0), "Furious")

    def test_description_high_morale(self):
        desc = morale_description(85, "Test CC")
        self.assertIn("Test CC", desc)
        self.assertIn("alive", desc)

    def test_description_low_morale(self):
        desc = morale_description(10, "Test CC")
        self.assertIn("Test CC", desc)
        self.assertIn("furious", desc.lower())


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_default_morale_is_50(self):
        # User's team should have default fan_morale
        morale = fetch_fan_morale(1, self.db)
        self.assertEqual(morale, 50)

    def test_update_fan_morale(self):
        new_morale = update_fan_morale(1, 10, self.db)
        self.assertEqual(new_morale, 60)

    def test_update_fan_morale_clamps(self):
        new_morale = update_fan_morale(1, 200, self.db)
        self.assertEqual(new_morale, 100)
        new_morale = update_fan_morale(1, -300, self.db)
        self.assertEqual(new_morale, 0)

    def test_update_fan_morale_returns_new_value(self):
        update_fan_morale(1, 5, self.db)
        update_fan_morale(1, 5, self.db)
        morale = fetch_fan_morale(1, self.db)
        self.assertEqual(morale, 60)

    def test_multiple_teams_independent(self):
        update_fan_morale(1, 10, self.db)
        # Team 2 starts at 50 (default)
        morale2 = fetch_fan_morale(2, self.db)
        self.assertEqual(morale2, 50)
        morale1 = fetch_fan_morale(1, self.db)
        self.assertEqual(morale1, 60)


class IntegrationTests(unittest.TestCase):
    def test_win_then_loss_morale_fluctuates(self):
        """Simulate: win (+6 home), loss (-5 home), net +1."""
        from src.models.fan_sentiment import clamp_morale
        morale = 50
        morale = clamp_morale(morale + win_delta(True, False, False))
        self.assertEqual(morale, 56)
        morale = clamp_morale(morale + loss_delta(True, False, False))
        self.assertEqual(morale, 51)

    def test_derby_win_big_boost(self):
        from src.models.fan_sentiment import clamp_morale
        morale = clamp_morale(50 + win_delta(True, True, True))
        self.assertEqual(morale, 61)

    def test_trophy_pushes_high(self):
        from src.models.fan_sentiment import clamp_morale
        morale = clamp_morale(70 + trophy_delta())
        self.assertEqual(morale, 85)


if __name__ == "__main__":
    unittest.main()
