"""Domestic Knockout Cup bracket (v0.88.0) — get_cup_bracket previously
didn't exist; the only bracket-shaped endpoint (get_tournament_bracket)
covered the separate, in-career "custom tournament" system only."""
from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from competition import CompetitionEngine
from database import connect, get_cup_bracket, initialise_database


class TemporaryGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()


class CupBracketTests(TemporaryGameTest):
    def test_no_cup_yet_reports_not_started(self) -> None:
        result = get_cup_bracket(self.database)
        self.assertEqual(result["bracket"], {})
        self.assertEqual(result["rounds"], [])
        self.assertEqual(result["status"], "not_started")
        self.assertIsNone(result["season"])

    def test_round_of_first_round_populated_with_resolved_team_names_after_ensure_season(self) -> None:
        engine = CompetitionEngine(self.database, seed=11)
        engine.ensure_season(2026)
        result = get_cup_bracket(self.database)
        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["season"], 2026)
        self.assertEqual(len(result["rounds"]), 1)
        first_round_name = result["rounds"][0]
        matches = result["bracket"][first_round_name]
        self.assertGreater(len(matches), 0)
        for match in matches:
            self.assertIsInstance(match["home"], str)
            self.assertNotEqual(match["home"], "?")
            self.assertIsInstance(match["away"], str)
            self.assertFalse(match["completed"])
            self.assertIsNone(match["winner"])

    def test_completing_first_round_generates_next_round_in_the_bracket(self) -> None:
        engine = CompetitionEngine(self.database, seed=11)
        engine.ensure_season(2026)
        result_before = get_cup_bracket(self.database)
        first_round_name = result_before["rounds"][0]
        with connect(self.database) as connection:
            competition_id = connection.execute(
                """SELECT c.id FROM competitions c
                   JOIN matches m ON m.competition_id = c.id
                   WHERE c.type='Cup' AND c.season=2026 AND m.round_name=?
                   GROUP BY c.id ORDER BY COUNT(m.id) DESC LIMIT 1""",
                (first_round_name,)
            ).fetchone()[0]
            match_ids = [row[0] for row in connection.execute(
                "SELECT id FROM matches WHERE competition_id=? AND round_name=?", (competition_id, first_round_name)
            ).fetchall()]
        self.assertGreater(len(match_ids), 0)
        for match_id in match_ids:
            engine.simulate_fixture(match_id)
        result = get_cup_bracket(self.database)
        self.assertGreaterEqual(len(result["rounds"]), 2)
        self.assertEqual(result["status"], "in_progress")
        first_round = result["bracket"][first_round_name]
        self.assertTrue(all(match["completed"] for match in first_round))
        self.assertTrue(all(match["winner"] is not None for match in first_round))
        second_round_name = result["rounds"][1]
        second_round = result["bracket"][second_round_name]
        self.assertGreater(len(second_round), 0)
        for match in second_round:
            self.assertFalse(match["completed"])

    def test_ipc_method_is_registered_and_json_safe(self) -> None:
        import ipc_server
        from database import fetch_teams
        db = str(self.database)
        team = fetch_teams(db)[0]
        engine = CompetitionEngine(db, seed=11)
        engine.ensure_season(2026)
        context = {"database_path": db, "team": team}
        handler = ipc_server.METHODS["get_cup_bracket"]
        result = handler({}, context)
        encoded = json.dumps(result)  # raises if not JSON-safe
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], "in_progress")
        self.assertIn(decoded["rounds"][0], decoded["bracket"])


if __name__ == "__main__":
    unittest.main()
