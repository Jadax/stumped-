"""Phase 7 realism tuning: per-team squad-strength variance within a
division, and a bell-curve-plus-tail youth-intake distribution replacing
the old flat randint rolls."""
from __future__ import annotations

from pathlib import Path
import random
import tempfile
import unittest
from statistics import mean

from database import (_target_rating, _team_quality_modifier, _youth_current_and_potential,
                      fetch_players, fetch_teams, generate_player, initialise_database, recruit_youth)


class TeamQualityModifierTests(unittest.TestCase):
    def test_modifier_bounds_at_division_cash_extremes(self) -> None:
        self.assertAlmostEqual(_team_quality_modifier(8_000_000, 1), -5.0)
        self.assertAlmostEqual(_team_quality_modifier(15_000_000, 1), 5.0)
        self.assertAlmostEqual(_team_quality_modifier(3_000_000, 2), -5.0)
        self.assertAlmostEqual(_team_quality_modifier(8_000_000, 2), 5.0)

    def test_modifier_is_zero_at_division_cash_midpoint(self) -> None:
        self.assertAlmostEqual(_team_quality_modifier(11_500_000, 1), 0.0)

    def test_richer_team_statistically_fields_a_stronger_squad(self) -> None:
        rng = random.Random(7)
        rich = [_target_rating(1, 26, rng, team_modifier=5.0) for _ in range(500)]
        poor = [_target_rating(1, 26, rng, team_modifier=-5.0) for _ in range(500)]
        self.assertGreater(mean(rich), mean(poor) + 5)

    def test_seeded_world_shows_within_division_squad_strength_spread(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "world.db"
            initialise_database(database)
            teams = [t for t in fetch_teams(database) if t["division"] == 1]
            by_cash = sorted(teams, key=lambda t: t["cash"])
            richest, poorest = by_cash[-3:], by_cash[:3]
            richest_avg = mean(p["overall"] for team in richest for p in fetch_players(team["id"], database))
            poorest_avg = mean(p["overall"] for team in poorest for p in fetch_players(team["id"], database))
            self.assertGreater(richest_avg, poorest_avg)


class YouthIntakeCurveTests(unittest.TestCase):
    def test_potential_is_mostly_average_with_a_rare_elite_tail(self) -> None:
        rng = random.Random(3)
        samples = [_youth_current_and_potential(2, rng) for _ in range(2000)]
        potentials = [p for _, p in samples]
        elite = sum(1 for p in potentials if p >= 85)
        self.assertLess(elite / len(potentials), 0.06, "elite (85+) potential should be rare, not common")
        self.assertTrue(any(p >= 85 for p in potentials), "an elite wonderkid should still be possible")
        typical = [p for p in potentials if p < 78]
        self.assertGreater(len(typical) / len(potentials), 0.7, "most prospects should be well short of elite")

    def test_potential_never_falls_below_current_ability(self) -> None:
        rng = random.Random(11)
        for _ in range(500):
            current, potential = _youth_current_and_potential(3, rng)
            self.assertGreaterEqual(potential, current)

    def test_better_academy_level_raises_the_potential_centre(self) -> None:
        rng = random.Random(5)
        weak_academy = [_youth_current_and_potential(1, rng)[1] for _ in range(400)]
        strong_academy = [_youth_current_and_potential(5, rng)[1] for _ in range(400)]
        self.assertGreater(mean(strong_academy), mean(weak_academy))

    def test_recruit_youth_produces_varied_not_flat_potentials(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "youth.db"
            initialise_database(database)
            recruited = recruit_youth(1, count=20, database_path=database)
            potentials = [p["potential"] for p in recruited]
            self.assertGreater(len(set(potentials)), 1, "a real distribution shouldn't collapse to one value")
            for p in recruited:
                self.assertLessEqual(p["potential"], 100)
                self.assertGreaterEqual(p["potential"], 0)


if __name__ == "__main__":
    unittest.main()
