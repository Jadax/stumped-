"""Phase 8 long-save stability: a genuine multi-season headless stress
test. Nothing like this existed before — season-boundary logic
(rollover_season, recruit_youth, retirement) had only ever been tested
one or two seasons at a time, never enough to reveal that squads grew
without bound (a 20-season run took a 25-player squad to 59)."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from database import connect, fetch_legends, fetch_season_records, initialise_database
from src.utilities.launcher import database_integrity
from competition import CompetitionEngine

SEASONS_TO_SIMULATE = 20


class LongSaveStabilityTests(unittest.TestCase):
    """One 20-season simulation shared across assertions (expensive to
    re-run per test) — each test method inspects a different facet of
    the same long save rather than re-simulating from scratch."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.database = Path(cls.directory.name) / "long_save.db"
        initialise_database(cls.database)
        cls.engine = CompetitionEngine(cls.database, seed=2026)
        cls.engine.ensure_season(2026)
        with connect(cls.database) as connection:
            cls.user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
        for offset in range(SEASONS_TO_SIMULATE):
            cls.engine.rollover_season(2026 + offset)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def test_squad_size_stays_capped_across_many_seasons(self) -> None:
        with connect(self.database) as connection:
            sizes = dict(connection.execute("SELECT team_id, COUNT(*) FROM players GROUP BY team_id").fetchall())
        self.assertTrue(sizes, "no players left after long simulation")
        for team_id, size in sizes.items():
            self.assertLessEqual(size, CompetitionEngine.SQUAD_SIZE_CAP,
                                 f"team {team_id} grew to {size} players — squad-size cap not enforced")

    def test_no_player_ever_exceeds_the_hard_retirement_age(self) -> None:
        with connect(self.database) as connection:
            max_age = connection.execute("SELECT MAX(age) FROM players").fetchone()[0]
        self.assertLessEqual(max_age, 45)

    def test_database_integrity_holds_after_many_seasons(self) -> None:
        healthy, message = database_integrity(self.database)
        self.assertTrue(healthy, message)

    def test_no_orphaned_player_records_after_repeated_retirements(self) -> None:
        with connect(self.database) as connection:
            orphans = connection.execute(
                "SELECT COUNT(*) FROM player_records WHERE player_id NOT IN (SELECT id FROM players)"
            ).fetchone()[0]
            no_team = connection.execute(
                "SELECT COUNT(*) FROM players WHERE team_id IS NOT NULL AND team_id NOT IN (SELECT id FROM teams)"
            ).fetchone()[0]
        self.assertEqual(orphans, 0)
        self.assertEqual(no_team, 0)

    def test_legends_archive_grows_without_erroring_and_stays_queryable(self) -> None:
        legends = fetch_legends(database_path=self.database)
        self.assertGreater(len(legends), 0, "20 seasons of retirement should produce some legends")

    def test_season_records_accumulate_one_row_per_season_not_zero_or_duplicated(self) -> None:
        seasons = fetch_season_records(self.user_team_id, database_path=self.database)
        self.assertEqual(len(seasons), SEASONS_TO_SIMULATE)
        self.assertEqual(len(seasons), len({row["season"] for row in seasons}))


class DailyAdvancementStabilityTests(unittest.TestCase):
    """A closer proxy for real play than season-boundary-only simulation:
    every daily/weekly/monthly hook actually fires, not just rollover."""

    def test_one_season_of_daily_advancement_stays_bounded_and_healthy(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            database = Path(folder) / "daily.db"
            initialise_database(database)
            engine = CompetitionEngine(database, seed=9)
            engine.ensure_season(2026)
            for _ in range(365):
                engine.advance_day(auto_sim_user=True)
            with connect(database) as connection:
                team1_size = connection.execute("SELECT COUNT(*) FROM players WHERE team_id=1").fetchone()[0]
            self.assertLessEqual(team1_size, CompetitionEngine.SQUAD_SIZE_CAP)
            healthy, message = database_integrity(database)
            self.assertTrue(healthy, message)


if __name__ == "__main__":
    unittest.main()
