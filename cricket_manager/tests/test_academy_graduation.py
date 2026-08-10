"""v4.64.0: real academy graduation (roadmap.json academy_expansion's
"expanded development paths" sub-item). A genuine bug found while scoping
this: nothing anywhere ever cleared `players.academy_squad` once set
(world-seed time for under-20s, or every recruit_youth signing) — a player
stayed listed as a Youth Academy "prospect" forever, even well into their
30s, since ipc_server._academy_eligible includes anyone with the flag set,
not just genuine under-20s.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database
from competition import CompetitionEngine


class AcademyGraduationTests(unittest.TestCase):
    def _fresh(self) -> tuple[Path, CompetitionEngine, int]:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directory.cleanup)
        db = Path(directory.name) / "graduation.db"
        with database.connect(db) as connection:
            database.create_tables(connection)
            database.seed_database(connection)
        user_team_id = database.load_game(db)["user"]["current_team_id"]
        return db, CompetitionEngine(db, seed=13), user_team_id

    def _set_player_age_and_flag(self, db: Path, team_id: int, age: int) -> int:
        with database.connect(db) as connection:
            player_id = connection.execute(
                "SELECT id FROM players WHERE team_id=? LIMIT 1", (team_id,)
            ).fetchone()[0]
            connection.execute("UPDATE players SET age=?, academy_squad=1 WHERE id=?", (age, player_id))
        return player_id

    def test_a_20_year_old_does_not_graduate_after_rollover(self) -> None:
        db, engine, team_id = self._fresh()
        player_id = self._set_player_age_and_flag(db, team_id, 19)
        engine.rollover_season(2026)
        with database.connect(db) as connection:
            row = connection.execute("SELECT academy_squad FROM players WHERE id=?", (player_id,)).fetchone()
        if row is None:
            self.skipTest("player did not survive rollover (retired/released) - not what this test checks")
        self.assertEqual(row[0], 1)

    def test_a_player_turning_21_graduates_from_the_academy(self) -> None:
        db, engine, team_id = self._fresh()
        player_id = self._set_player_age_and_flag(db, team_id, 20)
        engine.rollover_season(2026)
        with database.connect(db) as connection:
            row = connection.execute("SELECT academy_squad, age FROM players WHERE id=?", (player_id,)).fetchone()
        if row is None:
            self.skipTest("player did not survive rollover (retired/released) - not what this test checks")
        self.assertEqual(row["age"], 21)
        self.assertEqual(row["academy_squad"], 0)

    def test_graduation_posts_an_inbox_message_for_the_users_own_club_only(self) -> None:
        db, engine, team_id = self._fresh()
        self._set_player_age_and_flag(db, team_id, 20)
        engine.rollover_season(2026)
        messages = database.fetch_inbox_messages(database_path=db)
        self.assertTrue(any("graduates from the academy" in m["title"] for m in messages))

    def test_graduation_writes_a_narrative_event(self) -> None:
        db, engine, team_id = self._fresh()
        self._set_player_age_and_flag(db, team_id, 20)
        engine.rollover_season(2026)
        events = database.fetch_narrative_events(team_id=team_id, database_path=db)
        self.assertTrue(any(e["category"] == "MILESTONE" and "graduates" in e["title"] for e in events))

    def test_an_ai_clubs_graduation_does_not_spam_the_users_inbox(self) -> None:
        db, engine, team_id = self._fresh()
        with database.connect(db) as connection:
            ai_team_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
        self._set_player_age_and_flag(db, ai_team_id, 20)
        engine.rollover_season(2026)
        messages = database.fetch_inbox_messages(database_path=db)
        self.assertFalse(any("graduates from the academy" in m["title"] for m in messages))


if __name__ == "__main__":
    unittest.main()
