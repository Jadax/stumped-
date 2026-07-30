"""World-seeding migration robustness (found via a real crash during
v4.6.0 release verification): initialise_database()/_expand_world_to_
twenty_four() previously only guarded against team-ID collisions when
migrating an older save into the current TEAM_DEFINITIONS roster, not
NAME collisions. TEAM_DEFINITIONS' composition has been reshuffled across
several "expand the world" versions, so a save from before one of those
reshuffles could have a team ID that's "missing" from the new roster but
whose NAME already belongs to a different ID that IS present — violating
teams.name's UNIQUE constraint and crashing initialise_database (and
therefore every subsequent launch) entirely for that save."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from database import TEAM_DEFINITIONS, _expand_world_to_twenty_four, connect, create_tables, initialise_database


class WorldMigrationRobustnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _minimal_legacy_world(self) -> None:
        """A database with only the first 20 teams, mimicking a save
        started before the roster grew to its current size."""
        with connect(self.database) as connection:
            create_tables(connection)
            for team_id, (name, division, nationality) in enumerate(TEAM_DEFINITIONS[:20], start=1):
                connection.execute(
                    """INSERT INTO teams (id, name, division, cash, stadium_capacity,
                       training_level, medical_level, academy_level, country_id)
                       VALUES (?, ?, ?, 1000000, 10000, 2, 2, 2, 'england')""",
                    (team_id, name, division),
                )
            connection.execute(
                """INSERT INTO user_data
                   (id, current_team_id, current_date, game_speed, sound_on, resolution, auto_save_frequency)
                   VALUES (1, 1, '2026-04-01', 'Normal', 1, '1280x720', 'Monthly')"""
            )

    def test_expanding_a_legacy_world_does_not_crash_on_a_name_collision(self) -> None:
        self._minimal_legacy_world()
        # Simulate a roster reshuffle: a real, custom-renamed team already
        # sits under id 999 (well outside the legacy 20 and outside
        # TEAM_DEFINITIONS' own id range), but its name collides with
        # TEAM_DEFINITIONS[50] — a "missing by ID" definition that would,
        # pre-fix, still get inserted and crash on the name collision.
        colliding_name = TEAM_DEFINITIONS[50][0]
        with connect(self.database) as connection:
            connection.execute(
                """INSERT INTO teams (id, name, division, cash, stadium_capacity,
                   training_level, medical_level, academy_level, country_id)
                   VALUES (999, ?, 1, 1000000, 10000, 2, 2, 2, 'england')""",
                (colliding_name,),
            )
            # Should not raise sqlite3.IntegrityError.
            _expand_world_to_twenty_four(connection, seed=1)
            names = [row[0] for row in connection.execute("SELECT name FROM teams")]
        self.assertEqual(len(names), len(set(names)), "no duplicate team names after migration")

    def test_initialise_database_on_a_legacy_world_boots_without_crashing(self) -> None:
        self._minimal_legacy_world()
        colliding_name = TEAM_DEFINITIONS[50][0]
        with connect(self.database) as connection:
            connection.execute(
                """INSERT INTO teams (id, name, division, cash, stadium_capacity,
                   training_level, medical_level, academy_level, country_id)
                   VALUES (999, ?, 1, 1000000, 10000, 2, 2, 2, 'england')""",
                (colliding_name,),
            )
        # This is the exact call that crashed in the field (via run_diagnostics
        # -> initialise_database -> seed_database -> _expand_world_to_twenty_four).
        initialise_database(self.database)

    def test_a_genuinely_fresh_database_still_gets_the_full_roster(self) -> None:
        """The fix must not degrade the normal, no-collision path."""
        initialise_database(self.database)
        with connect(self.database) as connection:
            count = connection.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        self.assertEqual(count, len(TEAM_DEFINITIONS))


if __name__ == "__main__":
    unittest.main()
