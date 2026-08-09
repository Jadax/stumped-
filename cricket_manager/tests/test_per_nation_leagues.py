"""v4.57.0: wires the per-nation domestic leagues (built in v4.56.0 but never
called from anywhere) into the real season lifecycle. Validates the two real
bugs that made simply calling `ensure_per_nation_season` from `ensure_season`
unsafe on its own: (a) a nation's own multiple "league"-kind competitions
(e.g. a Test-format first-class league and a T20 league) used to all start on
the same date, double-booking any team playing in both; (b) promotion/
relegation had nothing real to move teams between, since divisions were
re-derived by blind team-id order every season regardless of results.
"""
from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

import database
from competition import CompetitionEngine


class PerNationSchedulingTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "nation.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_no_team_is_double_booked_within_its_own_nation(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            rows = connection.execute(
                """SELECT m.home_team, m.away_team, m.date FROM matches m
                   JOIN competitions c ON c.id = m.competition_id
                   JOIN leagues l ON l.name = c.name
                   WHERE l.kind = 'league' AND c.season = 2026"""
            ).fetchall()
        per_team_dates: dict[int, list[str]] = {}
        for home, away, match_date in rows:
            per_team_dates.setdefault(home, []).append(match_date)
            per_team_dates.setdefault(away, []).append(match_date)
        for team_id, dates in per_team_dates.items():
            counts = Counter(dates)
            duplicates = {d: n for d, n in counts.items() if n > 1}
            self.assertFalse(duplicates, f"team {team_id} double-booked on {duplicates}")

    def test_ensure_season_wires_in_per_nation_fixtures_automatically(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            row = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2026"
            ).fetchone()
        self.assertIsNotNone(row, "ensure_season should now also generate nation competitions")

    def test_global_and_nation_fixtures_still_do_not_collide(self) -> None:
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            global_row = connection.execute(
                "SELECT id FROM competitions WHERE name='County Championship' AND season=2026 AND type='League'"
            ).fetchone()
            nation_row = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2026"
            ).fetchone()
        self.assertIsNotNone(global_row)
        self.assertIsNotNone(nation_row)
        self.assertNotEqual(global_row[0], nation_row[0])

    def test_no_team_has_a_global_and_a_nation_fixture_on_the_same_date(self) -> None:
        # v4.60.3 regression: a screenshot-driven QA pass caught a team
        # (Lancashire) scheduled against the same opponent (Glamorgan) on
        # the exact same date via two independent competitions — the
        # global 5-division pyramid and the nation league both started
        # their round-robins on date(season,4,8).
        db, engine = self._fresh()
        engine.ensure_season(2026)
        with database.connect(db) as connection:
            rows = connection.execute(
                """SELECT m.home_team, m.away_team, m.date, c.type FROM matches m
                   JOIN competitions c ON c.id = m.competition_id
                   WHERE c.season = 2026 AND c.type = 'League'"""
            ).fetchall()
        per_team_dates: dict[int, set[str]] = {}
        collisions = []
        for home, away, match_date, _comp_type in rows:
            for team_id in (home, away):
                seen = per_team_dates.setdefault(team_id, set())
                if match_date in seen:
                    collisions.append((team_id, match_date))
                seen.add(match_date)
        self.assertFalse(collisions, f"teams double-booked across global/nation schedules: {collisions}")


class NationDivisionPersistenceTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "nation.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_first_generation_seeds_nation_division_for_multi_division_league(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            values = [row[0] for row in connection.execute(
                "SELECT nation_division FROM teams WHERE country_id='england'"
            )]
        self.assertTrue(values, "England should have teams")
        self.assertTrue(all(v in (1, 2) for v in values), values)

    def test_promotion_relegation_moves_teams_between_nation_divisions(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            comp = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2026"
            ).fetchone()
            team_ids = [row[0] for row in connection.execute(
                "SELECT team_id FROM league_standings WHERE competition_id=?", (comp[0],)
            )]
            # Fabricate a decisive result so promotion/relegation has a real
            # ranking to work from instead of an all-zero tie.
            connection.executemany(
                "UPDATE league_standings SET points=? WHERE competition_id=? AND team_id=?",
                [(len(team_ids) - i, comp[0], tid) for i, tid in enumerate(team_ids)],
            )
            before = dict(connection.execute("SELECT id, nation_division FROM teams WHERE country_id='england'"))
        engine.rollover_season(2026)
        with database.connect(db) as connection:
            after = dict(connection.execute("SELECT id, nation_division FROM teams WHERE country_id='england'"))
        self.assertNotEqual(before, after, "at least one England team should change nation_division")

    def test_second_season_generation_reads_back_persisted_divisions(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            connection.execute("UPDATE teams SET nation_division=2 WHERE country_id='england'")
            connection.execute("UPDATE teams SET nation_division=1 WHERE country_id='england' AND id=("
                               "SELECT id FROM teams WHERE country_id='england' LIMIT 1)")
        engine.ensure_per_nation_season(2027)
        with database.connect(db) as connection:
            comp = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2027"
            ).fetchone()
            fixture_count = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id=?", (comp[0],)
            ).fetchone()[0]
        self.assertGreater(fixture_count, 0)


class NationLeagueReadModelTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "nation.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_fetch_nation_leagues_lists_generated_competitions(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        leagues = database.fetch_nation_leagues(db)
        names = {row["name"] for row in leagues}
        self.assertIn("England County Championship", names)

    def test_fetch_nation_league_standings_returns_rows_for_generated_league(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        rows = database.fetch_nation_league_standings("england", "England County Championship", database_path=db)
        self.assertTrue(rows)
        self.assertIn("points", rows[0])


if __name__ == "__main__":
    unittest.main()
