"""v4.87.0: historical match context — pure-function tests."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database, connect
from src.models.match_context import head_to_head, player_vs_opposition, generate_match_context


class HeadToHeadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)
        self._counter = 0

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _new_name(self, prefix: str = "Team") -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def _insert_team(self, name: str | None = None) -> int:
        name = name or self._new_name("Club")
        with connect(self.database) as conn:
            conn.execute(
                "INSERT INTO teams(name,division,cash,stadium_capacity) VALUES (?,?,?,?)",
                (name, 1, 1000000, 20000),
            )
            row = conn.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row["id"]

    def _insert_match(self, home: int, away: int,
                      result: dict | None = None, completed: int = 1) -> int:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO matches(home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (home, away, "T20", "2026-01-01", "Test Ground",
                 completed, json.dumps(result) if result else "{}"),
            )
            row = conn.execute("SELECT id FROM matches WHERE home_team=? AND away_team=?",
                               (home, away)).fetchone()
        return row["id"]

    def test_no_matches_returns_zeros(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(result["played"], 0)
        self.assertEqual(result["team_a_wins"], 0)

    def test_team_a_wins(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        self._insert_match(t1, t2, {"home_runs": 200, "away_runs": 150, "winner": t1})
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(result["played"], 1)
        self.assertEqual(result["team_a_wins"], 1)
        self.assertEqual(result["team_b_wins"], 0)

    def test_team_b_wins(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        self._insert_match(t1, t2, {"home_runs": 150, "away_runs": 200, "winner": t2})
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(result["team_b_wins"], 1)

    def test_draw(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        self._insert_match(t1, t2, {"home_runs": 300, "away_runs": 300, "winner": None, "drawn": True})
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(result["draws"], 1)

    def test_multiple_matches(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        self._insert_match(t1, t2, {"home_runs": 200, "away_runs": 150, "winner": t1})
        self._insert_match(t2, t1, {"home_runs": 180, "away_runs": 190, "winner": t1})
        self._insert_match(t1, t2, {"home_runs": 160, "away_runs": 170, "winner": t2})
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(result["played"], 3)
        self.assertEqual(result["team_a_wins"], 2)
        self.assertEqual(result["team_b_wins"], 1)

    def test_limit_works(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        for _ in range(5):
            self._insert_match(t1, t2, {"home_runs": 200, "away_runs": 150, "winner": t1})
        result = head_to_head(t1, t2, limit=3, database_path=self.database)
        self.assertEqual(result["played"], 3)

    def test_recent_results_populated(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        self._insert_match(t1, t2, {"home_runs": 200, "away_runs": 150, "winner": t1})
        result = head_to_head(t1, t2, database_path=self.database)
        self.assertEqual(len(result["recent_results"]), 1)
        self.assertEqual(result["recent_results"][0]["winner_id"], t1)


class PlayerVsOppositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)
        self._counter = 0

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _new_name(self, prefix: str = "Team") -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def _insert_team(self) -> int:
        name = self._new_name("Club")
        with connect(self.database) as conn:
            conn.execute(
                "INSERT INTO teams(name,division,cash,stadium_capacity) VALUES (?,?,?,?)",
                (name, 1, 1000000, 20000),
            )
            row = conn.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row["id"]

    def _insert_player(self, name: str, team_id: int) -> int:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO players(name,team_id,role,age,overall,form,potential,nationality,
                   batting_json,bowling_json,fielding_json,mental_json,physical_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, team_id, "Batsman", 25, 70, 50, 80,
                 "English", "{}", "{}", "{}", "{}", "{}"),
            )
            row = conn.execute("SELECT id FROM players WHERE name=? AND team_id=?",
                               (name, team_id)).fetchone()
        return row["id"]

    def _insert_match(self, home: int, away: int) -> int:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO matches(home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (home, away, "T20", "2026-01-01", "Ground", 1,
                 json.dumps({"home_runs": 200, "away_runs": 150, "winner": home})),
            )
            row = conn.execute(
                "SELECT id FROM matches WHERE home_team=? AND away_team=? ORDER BY id DESC LIMIT 1",
                (home, away)).fetchone()
        return row["id"]

    def _insert_events(self, player_id: int, match_id: int,
                       events: list[dict]) -> None:
        with connect(self.database) as conn:
            for ev in events:
                conn.execute(
                    """INSERT INTO player_match_events
                       (player_id,match_id,innings,event_type,x,y,runs,wicket,detail)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (player_id, match_id, 1, ev.get("event_type", "shot"),
                     0.5, 0.5, ev.get("runs", 0), ev.get("wicket", 0), ""),
                )

    def test_no_matches_returns_zeros(self) -> None:
        result = player_vs_opposition(99999, 99998, database_path=self.database)
        self.assertEqual(result["matches"], 0)
        self.assertEqual(result["runs"], 0)

    def test_batting_record(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        pid = self._insert_player(self._new_name("Batsman"), t1)
        mid = self._insert_match(t1, t2)
        self._insert_events(pid, mid, [
            {"event_type": "shot", "runs": 45},
            {"event_type": "shot", "runs": 30},
        ])
        result = player_vs_opposition(pid, t2, database_path=self.database)
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["runs"], 75)
        self.assertEqual(result["best_score"], 75)

    def test_bowling_record(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        pid = self._insert_player(self._new_name("Bowler"), t1)
        mid = self._insert_match(t1, t2)
        self._insert_events(pid, mid, [
            {"event_type": "delivery", "runs": 2, "wicket": 1},
            {"event_type": "delivery", "runs": 4, "wicket": 0},
            {"event_type": "delivery", "runs": 1, "wicket": 1},
        ])
        result = player_vs_opposition(pid, t2, database_path=self.database)
        self.assertEqual(result["wickets"], 2)
        self.assertEqual(result["best_bowling"], "2/7")

    def test_multiple_matches_aggregated(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        pid = self._insert_player(self._new_name("Batsman"), t1)
        mid1 = self._insert_match(t1, t2)
        mid2 = self._insert_match(t2, t1)
        self._insert_events(pid, mid1, [{"event_type": "shot", "runs": 50}])
        self._insert_events(pid, mid2, [{"event_type": "shot", "runs": 30}])
        result = player_vs_opposition(pid, t2, database_path=self.database)
        self.assertEqual(result["matches"], 2)
        self.assertEqual(result["runs"], 80)


class GenerateMatchContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)
        self._counter = 0

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _new_name(self, prefix: str = "Team") -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def _insert_team(self) -> int:
        name = self._new_name("Club")
        with connect(self.database) as conn:
            conn.execute(
                "INSERT INTO teams(name,division,cash,stadium_capacity) VALUES (?,?,?,?)",
                (name, 1, 1000000, 20000),
            )
            row = conn.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row["id"]

    def _insert_player(self, name: str, team_id: int) -> int:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO players(name,team_id,role,age,overall,form,potential,nationality,
                   batting_json,bowling_json,fielding_json,mental_json,physical_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, team_id, "Batsman", 25, 70, 50, 80,
                 "English", "{}", "{}", "{}", "{}", "{}"),
            )
            row = conn.execute("SELECT id FROM players WHERE name=? AND team_id=?",
                               (name, team_id)).fetchone()
        return row["id"]

    def _insert_match(self, home: int, away: int) -> int:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO matches(home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (home, away, "T20", "2026-01-01", "Ground", 1,
                 json.dumps({"home_runs": 200, "away_runs": 150, "winner": home})),
            )
            row = conn.execute(
                "SELECT id FROM matches WHERE home_team=? AND away_team=? ORDER BY id DESC LIMIT 1",
                (home, away)).fetchone()
        return row["id"]

    def _insert_events(self, player_id: int, match_id: int,
                       events: list[dict]) -> None:
        with connect(self.database) as conn:
            for ev in events:
                conn.execute(
                    """INSERT INTO player_match_events
                       (player_id,match_id,innings,event_type,x,y,runs,wicket,detail)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (player_id, match_id, 1, ev.get("event_type", "shot"),
                     0.5, 0.5, ev.get("runs", 0), ev.get("wicket", 0), ""),
                )

    def test_returns_h2h_and_key_players(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        pid = self._insert_player(self._new_name("Batsman"), t1)
        mid = self._insert_match(t1, t2)
        self._insert_events(pid, mid, [{"event_type": "shot", "runs": 65}])
        fixture = {"home_team": t1, "away_team": t2}
        ctx = generate_match_context(t1, fixture, database_path=self.database)
        self.assertIn("head_to_head", ctx)
        self.assertIn("key_batting", ctx)
        self.assertEqual(ctx["head_to_head"]["played"], 1)

    def test_empty_when_no_history(self) -> None:
        t1 = self._insert_team()
        t2 = self._insert_team()
        fixture = {"home_team": t1, "away_team": t2}
        ctx = generate_match_context(t1, fixture, database_path=self.database)
        self.assertEqual(ctx["head_to_head"]["played"], 0)
        self.assertEqual(ctx["key_batting"], [])


if __name__ == "__main__":
    unittest.main()
