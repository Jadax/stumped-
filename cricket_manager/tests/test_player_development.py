"""Tests for the unified player age-curve and retirement story generation."""
from __future__ import annotations

import unittest

from src.models.player_development import (
    age_curve,
    training_age_factor,
    post_match_delta,
    retirement_probability,
    generate_retirement_message,
    generate_release_message,
    generate_young_retirement_message,
)


class AgeCurveTests(unittest.TestCase):
    def test_peak_is_at_27(self) -> None:
        self.assertAlmostEqual(age_curve(27), 1.0, places=2)

    def test_young_players_have_lower_ability(self) -> None:
        self.assertLess(age_curve(16), age_curve(21))
        self.assertLess(age_curve(21), age_curve(25))

    def test_veterans_decline(self) -> None:
        self.assertGreater(age_curve(30), age_curve(35))
        self.assertGreater(age_curve(35), age_curve(40))

    def test_curve_bounds(self) -> None:
        for age in range(16, 46):
            val = age_curve(age)
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_zero_age_returns_zero(self) -> None:
        self.assertEqual(age_curve(0), 0.0)

    def test_prime_ages_are_high(self) -> None:
        self.assertGreater(age_curve(25), 0.9)
        self.assertGreater(age_curve(27), 0.99)
        self.assertGreater(age_curve(30), 0.85)


class TrainingAgeFactorTests(unittest.TestCase):
    def test_young_players_train_fastest(self) -> None:
        self.assertGreater(training_age_factor(18), training_age_factor(25))

    def test_prime_age_is_baseline(self) -> None:
        self.assertAlmostEqual(training_age_factor(25), 1.0, places=2)

    def test_veterans_train_slowly(self) -> None:
        self.assertLess(training_age_factor(35), training_age_factor(25))

    def test_very_old_players_barely_improve(self) -> None:
        self.assertLess(training_age_factor(38), training_age_factor(35))


class PostMatchDeltaTests(unittest.TestCase):
    def test_young_player_with_room_grows(self) -> None:
        delta = post_match_delta(age=22, potential=85, overall=65)
        self.assertGreater(delta, 0)

    def test_player_at_potential_stays_stable(self) -> None:
        delta = post_match_delta(age=25, potential=75, overall=75)
        self.assertEqual(delta, 0.0)

    def test_35_year_old_declines(self) -> None:
        delta = post_match_delta(age=35, potential=80, overall=70)
        self.assertLess(delta, 0)

    def test_40_year_old_declines_faster(self) -> None:
        delta_35 = post_match_delta(age=35, potential=80, overall=70)
        delta_40 = post_match_delta(age=40, potential=80, overall=70)
        self.assertLess(delta_40, delta_35)

    def test_mid_30s_are_stable(self) -> None:
        delta = post_match_delta(age=33, potential=75, overall=72)
        self.assertEqual(delta, 0.0)


class RetirementProbabilityTests(unittest.TestCase):
    def test_young_never_retire(self) -> None:
        self.assertEqual(retirement_probability(25, 70), 0.0)

    def test_32_or_below_never_retire(self) -> None:
        self.assertEqual(retirement_probability(32, 60), 0.0)

    def test_35_has_some_chance(self) -> None:
        prob = retirement_probability(35, 50)
        self.assertGreater(prob, 0.0)
        self.assertLess(prob, 0.5)

    def test_probability_increases_with_age(self) -> None:
        self.assertLess(retirement_probability(35, 50), retirement_probability(40, 50))
        self.assertLess(retirement_probability(40, 50), retirement_probability(44, 50))

    def test_44_or_above_very_high(self) -> None:
        self.assertGreaterEqual(retirement_probability(44, 50), 0.8)

    def test_low_overall_increases_retirement_for_old_players(self) -> None:
        normal = retirement_probability(38, 60)
        declined = retirement_probability(38, 20)
        self.assertGreater(declined, normal)


class RetirementMessageTests(unittest.TestCase):
    def test_old_player_message(self) -> None:
        msg = generate_retirement_message({"name": "Smith", "age": 41, "role": "Batsman", "overall": 45})
        self.assertIn("Smith", msg)
        self.assertIn("41", msg)

    def test_declining_player_message(self) -> None:
        msg = generate_retirement_message({"name": "Jones", "age": 36, "role": "Bowler", "overall": 30})
        self.assertIn("Jones", msg)

    def test_legend_message(self) -> None:
        msg = generate_retirement_message({"name": "Great", "age": 38, "role": "Batsman", "overall": 90})
        self.assertIn("great", msg.lower())

    def test_with_career_stats(self) -> None:
        career = {"matches": 120, "runs": 4500, "wickets": 0, "hundreds": 8, "fifties": 22, "best_score": "187*"}
        msg = generate_retirement_message({"name": "Star", "age": 37, "role": "Batsman", "overall": 75}, career)
        self.assertIn("120", msg)
        self.assertIn("4,500", msg)
        self.assertIn("8 centuries", msg)
        self.assertIn("187*", msg)

    def test_bowler_career_stats(self) -> None:
        career = {"matches": 80, "wickets": 250, "best_bowling": "7/23"}
        msg = generate_retirement_message({"name": "Bowler", "age": 39, "role": "Bowler", "overall": 65}, career)
        self.assertIn("250", msg)
        self.assertIn("7/23", msg)


class ReleaseMessageTests(unittest.TestCase):
    def test_release_mentions_name(self) -> None:
        msg = generate_release_message({"name": "Weak"})
        self.assertIn("Weak", msg)


class YoungRetirementTests(unittest.TestCase):
    def test_young_retirement_mentions_age(self) -> None:
        msg = generate_young_retirement_message({"name": "Young", "age": 28})
        self.assertIn("Young", msg)
        self.assertIn("28", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
