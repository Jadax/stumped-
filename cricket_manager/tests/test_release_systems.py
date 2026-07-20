"""DLS/follow-on, launcher, recovery, and performance release tests."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from time import perf_counter
import unittest

from database import fetch_players, get_team_summary, initialise_database
from match_engine import Match
from src.utilities.launcher import (LaunchPaths, create_recovery_save, database_integrity,
                                    end_session, prepare_environment)


def make_match(database: Path, format_name: str, seed: int = 22) -> Match:
    return Match(get_team_summary(1, database), get_team_summary(2, database),
                 fetch_players(1, database)[:11], fetch_players(2, database)[:11],
                 format_name, seed=seed, batting_first_id=1)


class ReleaseMatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "match.db"; initialise_database(self.database)

    def tearDown(self) -> None: self.directory.cleanup()

    def test_dls_targets_scale_with_available_resources(self) -> None:
        match = make_match(self.database, "ODI")
        match.rain_overs = 40; forty = match.dls_target(300)
        match.rain_overs = 25; twenty_five = match.dls_target(300)
        match.rain_overs = 10; ten = match.dls_target(300)
        self.assertGreater(forty, twenty_five)
        self.assertGreater(twenty_five, ten)
        self.assertGreater(ten, 0)

    def test_follow_on_is_enforced_at_two_hundred_run_lead(self) -> None:
        match = make_match(self.database, "Test")
        first = match.current_innings; first.runs = 450; first.completed = True; match._advance_innings()
        second = match.current_innings; second.runs = 220; second.completed = True; second_team = second.batting_team
        match._advance_innings()
        self.assertEqual(len(match.innings), 3)
        self.assertEqual(match.current_innings.batting_team, second_team)

    def test_fifty_over_simulation_is_below_one_second(self) -> None:
        match = make_match(self.database, "ODI")
        started = perf_counter(); match.simulate(); elapsed = perf_counter() - started
        self.assertLess(elapsed, 1.0)


class LauncherTests(unittest.TestCase):
    def paths(self, root: Path) -> LaunchPaths:
        return LaunchPaths(root, root, root / "config.json", root / "data", root / "logs",
                           root / "data" / "cricket_manager.db", root / "data" / "recovery.db",
                           root / "data" / "session.lock")

    def test_first_run_creates_directories_config_and_marker(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); state = prepare_environment(self.paths(root))
            self.assertTrue(state.paths.data.is_dir()); self.assertTrue(state.paths.logs.is_dir())
            self.assertTrue(state.paths.config.exists()); self.assertTrue(state.paths.session_marker.exists())
            end_session(state, clean=True); self.assertFalse(state.paths.session_marker.exists())

    def test_recovery_backup_is_valid_sqlite(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); paths = self.paths(root); state = prepare_environment(paths)
            initialise_database(paths.database)
            self.assertTrue(create_recovery_save(paths.database, paths.recovery))
            self.assertEqual(database_integrity(paths.recovery), (True, "ok"))
            end_session(state, clean=True)

    def test_corrupt_database_is_quarantined(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory); paths = self.paths(root); paths.data.mkdir(parents=True)
            paths.database.write_bytes(b"not a sqlite database")
            state = prepare_environment(paths)
            self.assertIsNotNone(state.archived_corrupt_database)
            self.assertTrue(state.archived_corrupt_database.exists())
            end_session(state, clean=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
