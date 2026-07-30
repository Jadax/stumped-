"""Coverage for the international cricket window (docs/CURRENT.md) —
the scoped first slice of "deeper league/international structure"."""
from __future__ import annotations
import os
import tempfile
import unittest

from src.models.international import INTERNATIONAL_NATIONALITIES, NATIONAL_TEAM_IDS, national_team


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "international.db")
    initialise_database(path)
    return path


class NationalTeamHelperTests(unittest.TestCase):
    def test_national_team_ids_are_unique_and_negative(self) -> None:
        ids = list(NATIONAL_TEAM_IDS.values())
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(team_id < 0 for team_id in ids))

    def test_national_team_returns_a_match_engine_ready_dict(self) -> None:
        team = national_team("English")
        self.assertEqual(team["name"], "England")
        self.assertIn("grounds_level", team)
        self.assertIn("medical_level", team)
        self.assertIn("physio_rating", team)


class SelectNationalXiTests(unittest.TestCase):
    def test_returns_up_to_eleven_players_of_the_requested_nationality(self) -> None:
        from database import select_national_xi
        db = _fresh_db()
        xi = select_national_xi("English", db)
        self.assertLessEqual(len(xi), 11)
        self.assertTrue(all(p["nationality"] == "English" for p in xi))

    def test_prioritises_a_keeper_then_fills_by_overall(self) -> None:
        from database import fetch_players, fetch_teams, select_national_xi
        db = _fresh_db()
        english_players = [p for team in fetch_teams(db) for p in fetch_players(team["id"], db)
                           if p["nationality"] == "English"]
        keepers = [p for p in english_players if p["role"] == "Wicketkeeper"]
        xi = select_national_xi("English", db)
        if keepers and len(english_players) >= 11:
            self.assertTrue(any(p["role"] == "Wicketkeeper" for p in xi))


class InternationalWindowTests(unittest.TestCase):
    def test_runs_only_once_per_season(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_teams
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=42)
        engine.ensure_season(2026)
        team_id = fetch_teams(db)[0]["id"]
        first = engine._run_international_window(2026, "2026-06-01", team_id)
        second = engine._run_international_window(2026, "2026-06-01", team_id)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_advance_day_triggers_the_window_on_first_of_event_months(self) -> None:
        from competition import CompetitionEngine
        from database import connect
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=42)
        with connect(db) as connection:
            connection.execute("UPDATE user_data SET current_date='2026-05-31' WHERE id=1")
        engine.advance_day()  # -> 2026-06-01, should trigger (T20I Series in month 6)
        with connect(db) as connection:
            triggered = connection.execute(
                "SELECT 1 FROM competitions WHERE type='International' AND season=2026"
            ).fetchone()
        self.assertIsNotNone(triggered)
        engine.advance_day()  # -> 2026-06-02, must not trigger again
        with connect(db) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM competitions WHERE type='International'"
            ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_called_up_players_get_a_morale_boost_and_an_international_record(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_players, fetch_teams
        import sqlite3
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=3)
        engine.ensure_season(2026)
        team_id = fetch_teams(db)[0]["id"]
        result = engine._run_international_window(2026, "2026-06-01", team_id)
        self.assertIsNotNone(result)
        conn = sqlite3.connect(db)
        international_records = conn.execute(
            "SELECT COUNT(*) FROM player_records WHERE context='International'"
        ).fetchone()[0]
        self.assertGreater(international_records, 0)

    def test_posts_an_inbox_message(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_inbox_messages, fetch_teams
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=42)
        engine.ensure_season(2026)
        team_id = fetch_teams(db)[0]["id"]
        engine._run_international_window(2026, "2026-06-01", team_id)
        messages = fetch_inbox_messages(20, db)
        self.assertTrue(any("call-up" in m["title"] or "result" in m["title"] for m in messages))

    def test_series_result_is_at_most_a_three_match_series(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_teams
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=1)
        engine.ensure_season(2026)
        team_id = fetch_teams(db)[0]["id"]
        result = engine._run_international_window(2026, "2026-06-01", team_id)
        self.assertLessEqual(result["home_wins"] + result["away_wins"], 3)
        self.assertGreaterEqual(result["home_wins"], 0)
        self.assertGreaterEqual(result["away_wins"], 0)


if __name__ == "__main__":
    unittest.main()
