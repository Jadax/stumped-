"""v4.59.0: the narrative layer — rivalries and a permanent, queryable
"story so far" feed distinct from the transient inbox. Confirmed before
this version: no rivalry/derby concept existed anywhere, and the only
discrete persisted achievement-style table (`ground_honours`) was scoped to
grounds, not a general feed.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import database
from competition import CompetitionEngine


class RivalrySeedingTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "narrative.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_ensure_per_nation_season_seeds_one_rivalry_per_nation(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            row = connection.execute("SELECT team_a, team_b FROM rivalries WHERE country_id='england'").fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], row[1])

    def test_rivalry_seeding_is_idempotent(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        engine.ensure_per_nation_season(2027)
        with database.connect(db) as connection:
            count = connection.execute("SELECT COUNT(*) FROM rivalries WHERE country_id='england'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_fetch_rivalry_for_team_finds_either_side(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            row = connection.execute("SELECT team_a, team_b FROM rivalries WHERE country_id='england'").fetchone()
        found_a = database.fetch_rivalry_for_team(row[0], db)
        found_b = database.fetch_rivalry_for_team(row[1], db)
        self.assertIsNotNone(found_a)
        self.assertEqual(found_a["id"], found_b["id"])


class RivalryMatchResultTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "narrative.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_a_derby_result_writes_a_narrative_event_and_bumps_intensity(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            rivalry = connection.execute("SELECT id, team_a, team_b FROM rivalries WHERE country_id='england'").fetchone()
            match = connection.execute(
                """SELECT m.id FROM matches m JOIN competitions c ON c.id=m.competition_id
                   WHERE c.name='England County Championship'
                     AND ((m.home_team=? AND m.away_team=?) OR (m.home_team=? AND m.away_team=?))
                   LIMIT 1""",
                (rivalry[1], rivalry[2], rivalry[2], rivalry[1]),
            ).fetchone()
        self.assertIsNotNone(match, "the seeded rivalry pair should have a fixture in their nation's league")
        engine.simulate_fixture(match[0])
        with database.connect(db) as connection:
            intensity = connection.execute("SELECT intensity FROM rivalries WHERE id=?", (rivalry[0],)).fetchone()[0]
        self.assertEqual(intensity, 1)
        events = database.fetch_narrative_events(database_path=db)
        self.assertTrue(any(e["category"] == "RIVALRY" for e in events))

    def test_a_non_rivalry_match_does_not_write_a_rivalry_event(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            rivalry = connection.execute("SELECT team_a, team_b FROM rivalries WHERE country_id='england'").fetchone()
            match = connection.execute(
                """SELECT m.id FROM matches m JOIN competitions c ON c.id=m.competition_id
                   WHERE c.name='England County Championship'
                     AND m.home_team NOT IN (?,?) AND m.away_team NOT IN (?,?)
                   LIMIT 1""",
                (rivalry[0], rivalry[1], rivalry[0], rivalry[1]),
            ).fetchone()
        self.assertIsNotNone(match)
        engine.simulate_fixture(match[0])
        events = database.fetch_narrative_events(database_path=db)
        self.assertFalse(any(e["category"] == "RIVALRY" for e in events))


class NarrativeEventReadModelTests(unittest.TestCase):
    def test_record_and_fetch_round_trip(self) -> None:
        db = os.path.join(tempfile.mkdtemp(), "events.db")
        database.initialise_database(db)
        database.record_narrative_event("2026-05-01", "MILESTONE", "Big ton", "Body text",
                                         team_id=1, player_id=7, importance=2, database_path=db)
        events = database.fetch_narrative_events(team_id=1, database_path=db)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Big ton")
        self.assertEqual(events[0]["player_id"], 7)

    def test_fetch_scoped_to_team_excludes_others(self) -> None:
        db = os.path.join(tempfile.mkdtemp(), "events2.db")
        database.initialise_database(db)
        database.record_narrative_event("2026-05-01", "MILESTONE", "Ton for team 1", "x", team_id=1, database_path=db)
        database.record_narrative_event("2026-05-02", "MILESTONE", "Ton for team 2", "x", team_id=2, database_path=db)
        team1_events = database.fetch_narrative_events(team_id=1, database_path=db)
        self.assertEqual(len(team1_events), 1)
        self.assertEqual(team1_events[0]["title"], "Ton for team 1")


class MatchHonoursNarrativeTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "honours.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_a_century_and_a_five_for_write_milestone_narrative_events(self) -> None:
        import ipc_server
        ctx = self._context()
        team_id = ctx["team"]["id"]
        player = ctx["players"][0]
        fixture = {"id": 1, "home_team": team_id, "away_team": team_id + 1,
                   "format": "T20", "away_team_name": "Rivals CC"}
        career_lines = {int(player["id"]): {"batting": [{"runs": 105}], "bowling": [{"wickets": 5, "runs": 22}]}}
        ipc_server._record_match_honours(ctx, None, fixture, career_lines)
        events = database.fetch_narrative_events(team_id=team_id, database_path=ctx["database_path"])
        self.assertGreaterEqual(len(events), 2)
        self.assertTrue(all(e["category"] == "MILESTONE" for e in events))


if __name__ == "__main__":
    unittest.main()
