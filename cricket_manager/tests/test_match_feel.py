"""v4.60.0: match-day momentum, a key-moments timeline, and crowd/atmosphere
feel. Deliberately additive/display-layer — these tests focus on confirming
the new bookkeeping (Innings.momentum/key_moments, Match.crowd_boost) behaves
correctly in isolation, and that existing match simulation/calibration is
unaffected (test_match_engine.py/test_realism_tuning.py continue to pass
unchanged, exercised separately).
"""
from __future__ import annotations

import unittest

from match_engine import Match


def player(player_id: int, rating: int = 66, role: str = "Batsman", team_id: int | None = None) -> dict:
    data = {
        "id": player_id, "name": f"Player {player_id}", "role": role, "overall": rating,
        "batting": {"attack": rating, "defence": rating, "technique_vs_pace": rating,
                    "technique_vs_spin": rating, "concentration": rating},
        "bowling": {"pace": rating, "accuracy": rating, "variation": rating,
                    "stamina": rating, "swing_or_spin": rating},
        "fielding": {"catching": rating, "throwing": rating, "reflexes": rating},
        "mental": {"experience": rating, "consistency": rating, "big_match": rating,
                   "fitness": rating, "morale": rating},
    }
    if team_id is not None:
        data["team_id"] = team_id
    return data


def lineup(start: int, rating: int = 66, team_id: int | None = None) -> list[dict]:
    return [player(start + i, rating, "Bowler" if i >= 6 else "All-Rounder" if i == 5 else "Batsman", team_id)
            for i in range(11)]


def make_match(seed: int = 7) -> Match:
    return Match({"id": 1, "name": "Home"}, {"id": 2, "name": "Away"},
                 lineup(1, 68), lineup(20, 66), "T20", seed=seed, batting_first_id=1)


class MomentumTests(unittest.TestCase):
    def test_a_wicket_swings_momentum_toward_the_bowling_side(self) -> None:
        match = make_match()
        innings = match.current_innings
        innings.momentum = 0
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        match._update_momentum(innings, "wicket", 0, "bowled", batter, bowler)
        self.assertLess(innings.momentum, 0)

    def test_a_cluster_of_wickets_swings_momentum_further_than_one(self) -> None:
        match = make_match()
        innings = match.current_innings
        innings.momentum = 50
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        for _ in range(4):
            match._update_momentum(innings, "wicket", 0, "bowled", batter, bowler)
        self.assertLess(innings.momentum, 0)

    def test_a_six_swings_momentum_toward_the_batting_side(self) -> None:
        match = make_match()
        innings = match.current_innings
        innings.momentum = 0
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        match._update_momentum(innings, "run", 6, None, batter, bowler)
        self.assertGreater(innings.momentum, 0)

    def test_momentum_never_exceeds_the_declared_bounds(self) -> None:
        match = make_match()
        innings = match.current_innings
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        innings.momentum = 100
        for _ in range(20):
            match._update_momentum(innings, "run", 6, None, batter, bowler)
        self.assertLessEqual(innings.momentum, 100)
        innings.momentum = -100
        for _ in range(20):
            match._update_momentum(innings, "wicket", 0, "bowled", batter, bowler)
        self.assertGreaterEqual(innings.momentum, -100)


class KeyMomentsTests(unittest.TestCase):
    def test_a_wicket_writes_a_key_moment(self) -> None:
        match = make_match()
        innings = match.current_innings
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        match._update_momentum(innings, "wicket", 0, "bowled", batter, bowler)
        self.assertEqual(len(innings.key_moments), 1)
        self.assertIn("WICKET", innings.key_moments[0]["description"])
        self.assertEqual(innings.key_moments[0]["swing"], -15)

    def test_a_dot_ball_does_not_write_a_key_moment(self) -> None:
        match = make_match()
        innings = match.current_innings
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        match._update_momentum(innings, "normal", 0, None, batter, bowler)
        self.assertEqual(innings.key_moments, [])

    def test_reaching_a_century_writes_a_key_moment(self) -> None:
        match = make_match()
        innings = match.current_innings
        batter, bowler = innings.striker_player, innings.bowling_squad[0]
        line = innings.batters[int(batter["id"])]
        line.runs = 100
        match._update_momentum(innings, "run", 4, None, batter, bowler)
        self.assertTrue(any("CENTURY" in km["description"] for km in innings.key_moments))

    def test_a_full_simulated_match_produces_a_bounded_momentum_and_a_timeline(self) -> None:
        match = make_match()
        match.simulate()
        for innings in match.innings:
            self.assertGreaterEqual(innings.momentum, -100)
            self.assertLessEqual(innings.momentum, 100)
        self.assertTrue(any(innings.key_moments for innings in match.innings))

    def test_scorecard_exposes_momentum_and_key_moments(self) -> None:
        match = make_match()
        match.simulate()
        card = match.scorecard(0)
        self.assertIn("momentum", card)
        self.assertIn("key_moments", card)


class CrowdBoostTests(unittest.TestCase):
    def test_crowd_boost_defaults_to_one(self) -> None:
        match = make_match()
        self.assertEqual(match.crowd_boost, 1.0)

    def _home_batter_and_away_bowler(self, match: Match) -> tuple[dict, dict]:
        innings = match.current_innings
        home_batter = dict(innings.striker_player); home_batter["team_id"] = match.home_team_id
        away_bowler = dict(innings.bowling_squad[0]); away_bowler["team_id"] = match.away_team_id
        return home_batter, away_bowler

    def test_crowd_boost_amplifies_the_existing_home_grounds_advantage(self) -> None:
        match = make_match()
        match.teams[match.home_team_id]["grounds_level"] = 5
        home_batter, away_bowler = self._home_batter_and_away_bowler(match)
        match.crowd_boost = 1.0
        baseline = match._weights(home_batter, away_bowler)
        match.crowd_boost = 3.0
        boosted = match._weights(home_batter, away_bowler)
        self.assertGreater(boosted["1"], baseline["1"])

    def test_crowd_boost_has_no_effect_without_grounds_investment(self) -> None:
        # grounds_level defaults to 1 — the existing home_grounds_pct gate
        # (`if grounds_level > 1`) must still apply unchanged; crowd_boost
        # is a multiplier on that mechanic, not a standalone one.
        match = make_match()
        home_batter, away_bowler = self._home_batter_and_away_bowler(match)
        match.crowd_boost = 1.0
        baseline = match._weights(home_batter, away_bowler)
        match.crowd_boost = 5.0
        boosted = match._weights(home_batter, away_bowler)
        self.assertEqual(boosted["1"], baseline["1"])


class CrowdAtmosphereIpcTests(unittest.TestCase):
    def _context_with_derby_fixture(self) -> dict:
        import os
        import tempfile
        from datetime import date, timedelta
        import database
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "derby.db")
        initialise_database(db)
        game_data = load_game(db)
        team_id = game_data["user"]["current_team_id"]
        with database.connect(db) as connection:
            rival_id = connection.execute(
                "SELECT id FROM teams WHERE id != ? ORDER BY id LIMIT 1", (team_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO rivalries (team_a, team_b, country_id, intensity) VALUES (?,?,?,0)",
                (min(team_id, rival_id), max(team_id, rival_id), "england"),
            )
            earliest = (date.fromisoformat(game_data["user"]["current_date"]) + timedelta(days=1)).isoformat()
            connection.execute(
                """INSERT INTO matches (home_team, away_team, format, date, venue, completed, result_json)
                   VALUES (?,?,?,?,?,0,'{}')""",
                (team_id, rival_id, "T20", earliest, "Home Ground"),
            )
        team = get_team_summary(team_id, db)
        return {"database_path": db, "team": team, "players": fetch_players(team_id, db), "game_data": load_game(db)}

    def test_a_derby_fixture_sets_crowd_boost_and_is_derby(self) -> None:
        import ipc_server
        ctx = self._context_with_derby_fixture()
        ipc_server._start_match({}, ctx)
        self.assertEqual(ctx["match"].crowd_boost, 1.15)
        self.assertTrue(ctx["_crowd_info"]["is_derby"])
        self.assertEqual(ctx["_crowd_info"]["attendance_pct"], 100)

    def test_match_state_surfaces_crowd_info(self) -> None:
        import ipc_server
        ctx = self._context_with_derby_fixture()
        result = ipc_server._start_match({}, ctx)
        self.assertIn("crowd", result)
        self.assertTrue(result["crowd"]["is_derby"])


if __name__ == "__main__":
    unittest.main()
