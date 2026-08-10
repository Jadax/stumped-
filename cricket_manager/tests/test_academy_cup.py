"""v4.67.0: the Academy Cup — a real youth competition closing the last
open sub-item of roadmap.json's academy_expansion ("youth competitions").
A knockout cup among every club's academy-eligible talent, resolved by a
dedicated lightweight simulator rather than the full first-team squad
average simulate_fixture would otherwise use, and always auto-resolved
(never a blocking live match for the user, even when their own club is
involved) — a youth showcase, not something a manager plays ball-by-ball.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database
from competition import CompetitionEngine


class AcademyCupGenerationTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "academy_cup.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=5)

    def test_ensure_season_creates_the_academy_cup(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            row = connection.execute(
                "SELECT id, type FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["type"], "Cup")

    def test_academy_cup_has_real_bracket_fixtures(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            comp_id = connection.execute(
                "SELECT id FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()[0]
            fixture_count = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id=?", (comp_id,)
            ).fetchone()[0]
        self.assertGreater(fixture_count, 0)

    def test_generation_is_idempotent(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            comp_count = connection.execute(
                "SELECT COUNT(*) FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()[0]
        self.assertEqual(comp_count, 1)


class YouthSimulationTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "academy_cup2.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=5)

    def test_simulate_youth_fixture_resolves_and_marks_completed(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            comp_id = connection.execute(
                "SELECT id FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()[0]
            match_id = connection.execute(
                "SELECT id FROM matches WHERE competition_id=? LIMIT 1", (comp_id,)
            ).fetchone()[0]
        result = engine.simulate_youth_fixture(match_id)
        self.assertIn("winner", result)
        self.assertIsNotNone(result["winner"])
        with database.connect(db) as connection:
            completed = connection.execute("SELECT completed FROM matches WHERE id=?", (match_id,)).fetchone()[0]
        self.assertEqual(completed, 1)

    def test_is_youth_competition_identifies_only_the_academy_cup(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            academy_id = connection.execute(
                "SELECT id FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()[0]
            other_id = connection.execute(
                "SELECT id FROM competitions WHERE name='T20 Cup' AND season=2026"
            ).fetchone()[0]
        self.assertTrue(engine._is_youth_competition(academy_id))
        self.assertFalse(engine._is_youth_competition(other_id))


class AdvanceDayAcademyCupTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine, int]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "academy_cup3.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        user_team_id = database.load_game(db)["user"]["current_team_id"]
        return db, CompetitionEngine(db, seed=5), user_team_id

    def test_an_academy_cup_fixture_involving_the_user_never_blocks_advance_day(self) -> None:
        db, engine, team_id = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            comp_id = connection.execute(
                "SELECT id FROM competitions WHERE name='Academy Cup' AND season=2026"
            ).fetchone()[0]
            user_fixture = connection.execute(
                "SELECT id, date FROM matches WHERE competition_id=? AND (home_team=? OR away_team=?) LIMIT 1",
                (comp_id, team_id, team_id),
            ).fetchone()
            connection.execute("UPDATE user_data SET current_date=? WHERE id=1", (user_fixture["date"],))
        events = engine.advance_day(auto_sim_user=False)
        # A real (non-academy) user fixture on the same date would set
        # events["user_fixture"] and refuse to advance the date — the
        # Academy Cup fixture must never trigger that block.
        with database.connect(db) as connection:
            completed = connection.execute(
                "SELECT completed FROM matches WHERE id=?", (user_fixture["id"],)
            ).fetchone()[0]
        self.assertEqual(completed, 1)


if __name__ == "__main__":
    unittest.main()
