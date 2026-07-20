"""Rules and accounting tests for the ball-by-ball engine."""
from __future__ import annotations

import unittest

from match_engine import Match, overs_text


def player(player_id: int, rating: int = 66, role: str = "Batsman") -> dict:
    return {
        "id": player_id, "name": f"Player {player_id}", "role": role, "overall": rating,
        "batting": {"attack": rating, "defence": rating, "technique_vs_pace": rating,
                    "technique_vs_spin": rating, "concentration": rating},
        "bowling": {"pace": rating, "accuracy": rating, "variation": rating,
                    "stamina": rating, "swing_or_spin": rating},
        "fielding": {"catching": rating, "throwing": rating, "reflexes": rating},
        "mental": {"experience": rating, "consistency": rating, "big_match": rating,
                   "fitness": rating, "morale": rating},
    }


def lineup(start: int, rating: int = 66) -> list[dict]:
    return [player(start + i, rating, "Bowler" if i >= 6 else "All-Rounder" if i == 5 else "Batsman") for i in range(11)]


class MatchEngineTests(unittest.TestCase):
    def make_match(self, format_name: str = "T20", seed: int = 7, knockout: bool = False) -> Match:
        return Match({"id": 1, "name": "Home"}, {"id": 2, "name": "Away"},
                     lineup(1, 68), lineup(20, 66), format_name,
                     seed=seed, batting_first_id=1, knockout=knockout)

    def test_overs_notation(self) -> None:
        self.assertEqual(overs_text(0), "0.0")
        self.assertEqual(overs_text(17), "2.5")
        self.assertEqual(overs_text(18), "3.0")

    def test_t20_completes_and_obeys_bowler_limit(self) -> None:
        match = self.make_match("T20")
        result = match.simulate()
        self.assertTrue(match.completed)
        self.assertTrue(result)
        self.assertEqual(len(match.innings), 2)
        for innings in match.innings:
            self.assertLessEqual(innings.legal_balls, 120)
            self.assertTrue(all(line.balls <= 24 for line in innings.bowlers.values()))

    def test_odi_score_is_conserved(self) -> None:
        match = self.make_match("ODI")
        match.simulate()
        for innings in match.innings:
            batter_runs = sum(line.runs for line in innings.batters.values())
            self.assertEqual(innings.runs, batter_runs + sum(innings.extras.values()))
            self.assertLessEqual(innings.legal_balls, 300)

    def test_wides_and_no_balls_are_not_legal_deliveries(self) -> None:
        match = self.make_match("T20", seed=19)
        found_extra = False
        for _ in range(300):
            before = match.current_innings.legal_balls
            event = match.ball_outcome()
            if event["result"] in {"Wd", "Nb"}:
                found_extra = True
                self.assertFalse(event["legal"])
                self.assertEqual(match.current_innings.legal_balls, before)
                break
            if match.completed: break
        self.assertTrue(found_extra)

    def test_dls_reduces_target(self) -> None:
        match = self.make_match("ODI")
        match.rain_overs = 25
        adjusted = match.dls_target(300)
        self.assertGreater(adjusted, 1)
        self.assertLess(adjusted, 301)

    def test_test_match_has_up_to_four_innings(self) -> None:
        match = self.make_match("Test", seed=11)
        match.simulate()
        self.assertTrue(match.completed)
        self.assertGreaterEqual(len(match.innings), 3)
        self.assertLessEqual(len(match.innings), 4)
        self.assertTrue(match.result)

    def test_scorecard_is_json_safe_shape(self) -> None:
        match = self.make_match()
        for _ in range(12): match.ball_outcome()
        card = match.scorecard()
        self.assertEqual(card["team"], "Home")
        self.assertEqual(len(card["batting"]), 11)
        self.assertIn("economy", card["bowling"][0])

    def test_knockout_tie_uses_super_over(self) -> None:
        match = self.make_match(knockout=True)
        first = match.current_innings
        first.runs = 150; first.completed = True
        match._advance_innings()
        second = match.current_innings
        second.runs = 150; second.completed = True
        match._advance_innings()
        self.assertTrue(match.is_super_over)
        self.assertIsNotNone(match.winner_id)
        self.assertIn("Super Over", match.result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
