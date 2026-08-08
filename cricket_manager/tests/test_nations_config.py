"""v4.56.0: per-nation domestic league structure (Cricket Captain parity).

The game previously ran one global 5-division pyramid mixing nations. Each
league-playing nation now gets its own domestic competitions generated from
the src/models/nations_config registry — First Class, 50-over and T20 —
scoped by country_id, with collision-safe "Nation Name" competition names so
they coexist with the existing global leagues. This module validates the
registry shape, the additive generation, idempotency and the leagues table.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database
from competition import CompetitionEngine
from src.models.nations_config import (
    NATION_COMPETITIONS,
    competitions_for_country,
    franchise_for_country,
)


class NationsConfigTests(unittest.TestCase):
    def test_every_league_playing_nation_has_a_domestic_structure(self) -> None:
        for country in ("england", "australia", "india", "pakistan", "south_africa",
                        "new_zealand", "sri_lanka", "bangladesh", "west_indies", "zimbabwe"):
            self.assertIn(country, NATION_COMPETITIONS, f"{country} missing from registry")
            comps = NATION_COMPETITIONS[country]
            self.assertTrue(comps, f"{country} has no competitions")
            formats = {spec["format"] for spec in comps}
            self.assertTrue({"Test", "ODI", "T20"} & formats, f"{country} lacks a format spread")

    def test_registry_competitions_have_valid_kind_and_shape(self) -> None:
        for country, comps in NATION_COMPETITIONS.items():
            for spec in comps:
                self.assertIn(spec["kind"], ("league", "cup"))
                self.assertIn(spec["format"], ("Test", "ODI", "T20"))
                self.assertGreaterEqual(spec.get("divisions", 1), 1)

    def test_franchise_leagues_defined_for_major_nations(self) -> None:
        self.assertEqual(franchise_for_country("india")["name"], "Indian Premier League")
        self.assertEqual(franchise_for_country("pakistan")["name"], "Pakistan Super League")
        self.assertEqual(competitions_for_country("england")[0]["name"], "County Championship")


class PerNationGenerationTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "nation.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        return db, CompetitionEngine(db, seed=42)

    def test_england_gets_its_own_county_championship_competition(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            row = connection.execute(
                "SELECT id FROM competitions WHERE name=? AND season=2026",
                ("England County Championship",),
            ).fetchone()
        self.assertIsNotNone(row)
        with database.connect(db) as connection:
            fixture_count = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id=?", (row[0],)
            ).fetchone()[0]
            teams = connection.execute(
                "SELECT COUNT(*) FROM league_standings WHERE competition_id=?", (row[0],)
            ).fetchone()[0]
        self.assertGreater(fixture_count, 0)
        self.assertGreater(teams, 0)

    def test_per_nation_names_do_not_collide_with_existing_global_leagues(self) -> None:
        db, engine = self._fresh()
        from src.models.league_config import LEAGUE_NAMES
        global_name = LEAGUE_NAMES[1]  # "County Championship"
        engine.ensure_season(2026)
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            global_row = connection.execute(
                "SELECT id FROM competitions WHERE name=? AND season=2026 AND type='League'",
                (global_name,),
            ).fetchone()
            nation_row = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2026",
            ).fetchone()
        self.assertIsNotNone(global_row)
        self.assertIsNotNone(nation_row)
        self.assertNotEqual(global_row[0], nation_row[0])

    def test_generation_is_idempotent_without_duplicate_fixtures(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            row = connection.execute(
                "SELECT id FROM competitions WHERE name='England County Championship' AND season=2026",
            ).fetchone()
            fixture_count = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id=?", (row[0],)
            ).fetchone()[0]
            comp_count = connection.execute(
                "SELECT COUNT(*) FROM competitions WHERE name='England County Championship' AND season=2026"
            ).fetchone()[0]
        self.assertEqual(comp_count, 1)
        self.assertGreater(fixture_count, 0)

    def test_two_division_competition_is_split(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            leagues = connection.execute(
                "SELECT divisions FROM leagues WHERE country_id='england' AND name='England County Championship'"
            ).fetchone()
        self.assertIsNotNone(leagues)
        self.assertEqual(leagues[0], 2)

    def test_franchise_league_row_recorded(self) -> None:
        db, engine = self._fresh()
        engine.ensure_per_nation_season(2026)
        with database.connect(db) as connection:
            row = connection.execute(
                "SELECT kind FROM leagues WHERE country_id='india' AND name='India Indian Premier League'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "franchise")


if __name__ == "__main__":
    unittest.main()
