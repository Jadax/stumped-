"""v4.65.0: the Weekly Challenge (roadmap.json's daily_tournaments item —
"optional daily and weekly challenge competitions with rewards"). A
quick-resolved side match, deliberately not a scheduled live fixture in
the `matches` table — that would risk the same class of fixture-collision
bug v4.60.3 found and fixed for the real domestic calendar.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import database
from competition import CompetitionEngine


def _fresh_db() -> str:
    db = os.path.join(tempfile.mkdtemp(), "challenge.db")
    database.initialise_database(db)
    return db


def _team_id(db: str) -> int:
    return database.load_game(db)["user"]["current_team_id"]


class EnsureChallengeTests(unittest.TestCase):
    def test_a_new_challenge_becomes_available(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        result = database.ensure_weekly_challenge(team_id, "2026-04-06", db)
        self.assertIsNotNone(result)
        self.assertIn("opponent_name", result)
        status = database.get_weekly_challenge(team_id, db)
        self.assertTrue(status["available"])
        self.assertIsNotNone(status["opponent"])
        self.assertGreater(status["potential_reward"], 0)

    def test_ensure_does_not_replace_an_already_available_challenge(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        database.ensure_weekly_challenge(team_id, "2026-04-06", db)
        first_status = database.get_weekly_challenge(team_id, db)
        second_call = database.ensure_weekly_challenge(team_id, "2026-04-13", db)
        self.assertIsNone(second_call)
        second_status = database.get_weekly_challenge(team_id, db)
        self.assertEqual(first_status["opponent"]["id"], second_status["opponent"]["id"])

    def test_no_challenge_available_by_default(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        status = database.get_weekly_challenge(team_id, db)
        self.assertFalse(status["available"])
        self.assertEqual(status["streak"], 0)


class PlayChallengeTests(unittest.TestCase):
    def test_playing_with_no_challenge_available_raises(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        with self.assertRaises(ValueError):
            database.play_weekly_challenge(team_id, "2026-04-06", db)

    def test_playing_resolves_the_challenge_and_clears_availability(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        database.ensure_weekly_challenge(team_id, "2026-04-06", db)
        result = database.play_weekly_challenge(team_id, "2026-04-06", db)
        self.assertIn("won", result)
        self.assertIn("streak", result)
        status = database.get_weekly_challenge(team_id, db)
        self.assertFalse(status["available"])

    def test_a_win_pays_the_reward_into_the_clubs_cash(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        # Stack the deck: a much weaker opponent all but guarantees a win
        # given the win_chance formula (advantage-driven, clamped 0.15-0.85).
        with database.connect(db) as connection:
            connection.execute("UPDATE players SET overall=95 WHERE team_id=?", (team_id,))
            opponent_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE players SET overall=20 WHERE team_id=?", (opponent_id,))
        cash_before = database.get_team_summary(team_id, db)["cash"]
        won_at_least_once = False
        for day in range(1, 20):
            database.ensure_weekly_challenge(team_id, f"2026-04-{day:02d}", db)
            result = database.play_weekly_challenge(team_id, f"2026-04-{day:02d}", db)
            if result["won"]:
                won_at_least_once = True
                self.assertGreater(result["reward"], 0)
                break
        self.assertTrue(won_at_least_once, "a heavily-favoured team should win at least once in 19 tries")
        cash_after = database.get_team_summary(team_id, db)["cash"]
        self.assertGreater(cash_after, cash_before)

    def test_a_loss_resets_the_streak_to_zero(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        with database.connect(db) as connection:
            connection.execute("UPDATE players SET overall=20 WHERE team_id=?", (team_id,))
            opponent_id = connection.execute("SELECT id FROM teams WHERE id!=? LIMIT 1", (team_id,)).fetchone()[0]
            connection.execute("UPDATE players SET overall=95 WHERE team_id=?", (opponent_id,))
        database.ensure_weekly_challenge(team_id, "2026-04-06", db)
        result = database.play_weekly_challenge(team_id, "2026-04-06", db)
        self.assertFalse(result["won"])
        self.assertEqual(result["streak"], 0)


class CompetitionEngineIntegrationTests(unittest.TestCase):
    def test_advance_day_offers_a_challenge_on_monday_and_posts_an_inbox_message(self) -> None:
        db = _fresh_db()
        team_id = _team_id(db)
        engine = CompetitionEngine(db, seed=17)
        engine.ensure_season(2026)
        # 2026-04-06 is a Monday.
        with database.connect(db) as connection:
            connection.execute("UPDATE user_data SET current_date='2026-04-05' WHERE id=1")
        engine.advance_day(auto_sim_user=True)
        status = database.get_weekly_challenge(team_id, db)
        self.assertTrue(status["available"])
        messages = database.fetch_inbox_messages(database_path=db)
        self.assertTrue(any("Weekly Challenge" in m["title"] for m in messages))


class IpcChallengeTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "challenge_ipc.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_get_and_play_round_trip_through_ipc(self) -> None:
        import ipc_server
        ctx = self._context()
        database.ensure_weekly_challenge(ctx["team"]["id"], ctx["game_data"]["user"]["current_date"], ctx["database_path"])
        status = ipc_server._get_weekly_challenge({}, ctx)
        self.assertTrue(status["available"])
        result = ipc_server._play_weekly_challenge({}, ctx)
        self.assertIn("won", result)


if __name__ == "__main__":
    unittest.main()
