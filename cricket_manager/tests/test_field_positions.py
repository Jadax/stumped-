"""Real per-fielder field positions (v4.13.0) — previously FIELD_PRESETS
only nudged one flat aggregate wicket-probability weight in _weights();
catches were resolved by picking a uniformly random fielder with a
cosmetic-only position label never cross-checked against the shot's actual
angle. This tests the real field_layout_by_team model that replaced it:
_covering_fielder's geometry, set_field_layout's validation, set_field's
preset-to-layout wiring, and that a well-covered field genuinely produces
different catch/boundary-save outcomes than an open one."""
from __future__ import annotations

import unittest

from match_engine import FIELD_LAYOUT_PRESETS, FIELD_POSITIONS, Match


def player(player_id: int, rating: int = 66, role: str = "Batsman") -> dict:
    return {
        "id": player_id, "name": f"Player {player_id}", "role": role, "overall": rating,
        "batting": {"attack": rating, "defence": rating, "technique_vs_pace": rating,
                    "technique_vs_spin": rating, "concentration": rating},
        "bowling": {"pace": rating, "accuracy": rating, "variation": rating,
                    "stamina": rating, "swing_or_spin": rating},
        "fielding": {"catching": rating, "throwing": rating, "reflexes": rating,
                     "agility": rating, "ground_fielding": rating},
        "mental": {"experience": rating, "consistency": rating, "big_match": rating,
                   "fitness": rating, "morale": rating},
    }


def lineup(start: int, rating: int = 66) -> list[dict]:
    return [player(start + i, rating, "Bowler" if i >= 6 else "All-Rounder" if i == 5 else "Batsman") for i in range(11)]


def make_match(seed: int = 7, format_name: str = "T20") -> Match:
    return Match({"id": 1, "name": "Home"}, {"id": 2, "name": "Away"},
                 lineup(1, 68), lineup(20, 66), format_name, seed=seed, batting_first_id=1)


class CoveringFielderTests(unittest.TestCase):
    def test_returns_none_for_an_empty_layout(self) -> None:
        match = make_match()
        name, strength = match._covering_fielder(90.0, 0.35, {})
        self.assertIsNone(name)
        self.assertEqual(strength, 0.0)

    def test_finds_a_position_whose_angle_and_radius_match(self) -> None:
        match = make_match()
        layout = {"Mid-off": {"angle": 22.0, "radius": 0.45}}
        name, strength = match._covering_fielder(22.0, 0.45, layout)
        self.assertEqual(name, "Mid-off")
        self.assertGreater(strength, 0.9)

    def test_a_position_far_outside_the_arc_tolerance_does_not_cover(self) -> None:
        match = make_match()
        layout = {"Cover": {"angle": 55.0, "radius": 0.65}}
        name, strength = match._covering_fielder(200.0, 0.65, layout)
        self.assertIsNone(name)
        self.assertEqual(strength, 0.0)

    def test_a_position_at_the_right_angle_but_wrong_depth_covers_weakly_or_not_at_all(self) -> None:
        match = make_match()
        # Third Man sits at radius 0.85 (boundary) — a catch check targets
        # radius 0.35 (the ring), far enough away that this shouldn't count
        # as real coverage for a catch, even though the angle lines up.
        layout = {"Third Man": {"angle": 160.0, "radius": 0.85}}
        name, strength = match._covering_fielder(160.0, 0.35, layout)
        self.assertIsNone(name)


class SetFieldLayoutTests(unittest.TestCase):
    def test_unknown_team_id_raises(self) -> None:
        match = make_match()
        with self.assertRaises(ValueError):
            match.set_field_layout(999, {"Cover": {"angle": 55.0, "radius": 0.65}})

    def test_unknown_position_names_are_dropped_not_rejected(self) -> None:
        match = make_match()
        layout = match.set_field_layout(1, {"Cover": {"angle": 55.0, "radius": 0.65},
                                            "Silly Mid-On": {"angle": 0.0, "radius": 0.1}})
        self.assertIn("Cover", layout)
        self.assertNotIn("Silly Mid-On", layout)

    def test_all_unknown_positions_raises(self) -> None:
        match = make_match()
        with self.assertRaises(ValueError):
            match.set_field_layout(1, {"Nonsense": {"angle": 0.0, "radius": 0.5}})

    def test_angle_and_radius_are_clamped(self) -> None:
        match = make_match()
        layout = match.set_field_layout(1, {"Cover": {"angle": 725.0, "radius": 5.0}})
        self.assertEqual(layout["Cover"]["angle"], 5.0)  # 725 % 360
        self.assertEqual(layout["Cover"]["radius"], 1.0)

    def test_applies_to_the_correct_team_only(self) -> None:
        match = make_match()
        match.set_field_layout(1, {"Cover": {"angle": 10.0, "radius": 0.5}})
        self.assertEqual(match.field_layout_by_team[1]["Cover"]["angle"], 10.0)
        self.assertEqual(match.field_layout_by_team[2], {k: v for k, v in FIELD_LAYOUT_PRESETS["Neutral"].items()})


class SetFieldPresetWiringTests(unittest.TestCase):
    def test_set_field_preset_loads_the_canonical_layout_for_the_bowling_team(self) -> None:
        match = make_match()
        bowling_team = match.current_innings.bowling_team
        match.set_field("Defensive")
        self.assertEqual(match.field_layout_by_team[bowling_team]["Third Man"]["radius"],
                         FIELD_LAYOUT_PRESETS["Defensive"]["Third Man"]["radius"])

    def test_every_preset_covers_every_catalog_position(self) -> None:
        for preset_name, layout in FIELD_LAYOUT_PRESETS.items():
            self.assertEqual(set(layout.keys()), set(FIELD_POSITIONS), preset_name)


class FieldCoverageAffectsOutcomesTests(unittest.TestCase):
    """A direct ball_outcome() loop (not simulate(), which re-picks the
    field every ball via AI) with the field locked to one preset for the
    whole sample — statistically confirms field_layout_by_team is actually
    load-bearing, not just stored and ignored."""

    def _run(self, seed: int, preset: str, balls: int = 600) -> Match:
        match = make_match(seed=seed)
        bowling_team = match.current_innings.bowling_team
        match.set_field(preset)
        delivered = 0
        while delivered < balls and not match.completed:
            bowling_team = match.current_innings.bowling_team
            # Re-assert every ball: a new innings/over could otherwise pick
            # a fresh AI-inferred field via other code paths this test
            # doesn't exercise, but staying explicit is cheap and clearer.
            if match.field_setting != preset:
                match.set_field(preset)
            event = match.ball_outcome()
            match.event_pool.release(event)
            if event.get("legal"):
                delivered += 1
        return match

    def test_defensive_field_saves_more_boundaries_than_aggressive(self) -> None:
        saved_counts = {"Aggressive": 0, "Defensive": 0}
        for preset in ("Aggressive", "Defensive"):
            for seed in range(6):
                match = self._run(seed, preset)
                # Fours actually recorded in the batting lines is a real,
                # cheap, already-tracked proxy for "boundary got through
                # vs. got cut off by a covering fielder."
                fours = sum(line.fours for innings in match.innings for line in innings.batters.values())
                saved_counts[preset] += fours
        # Defensive fields are built to cover the boundary-save target
        # radius (~0.90) far better than Aggressive's pulled-in ring, so
        # fewer fours should get through over the same sample.
        self.assertLess(saved_counts["Defensive"], saved_counts["Aggressive"])


if __name__ == "__main__":
    unittest.main()
