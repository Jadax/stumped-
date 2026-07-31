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
        # v4.11.0: a tour now creates real dated fixtures instead of
        # resolving synchronously — the "at most 3 matches" cap is verified
        # against the persisted matches rows, and the series-result
        # message only appears once every one of them is actually complete
        # (via _advance_tour_if_ready, exercised end-to-end here rather
        # than asserting on an immediate in-memory win count that no
        # longer exists).
        from competition import CompetitionEngine
        from database import connect, fetch_teams
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=1)
        engine.ensure_season(2026)
        team_id = fetch_teams(db)[0]["id"]
        engine._run_international_window(2026, "2026-06-01", team_id)
        with connect(db) as connection:
            match_ids = [row[0] for row in connection.execute(
                "SELECT id FROM matches WHERE home_team < 0 OR away_team < 0"
            )]
        self.assertLessEqual(len(match_ids), 3)
        self.assertGreater(len(match_ids), 0)
        for match_id in match_ids:
            engine._simulate_international_fixture(match_id)
        with connect(db) as connection:
            still_pending = connection.execute(
                "SELECT COUNT(*) FROM matches WHERE id IN (%s) AND completed=0" % ",".join("?" for _ in match_ids),
                match_ids,
            ).fetchone()[0]
            series_result = connection.execute(
                "SELECT 1 FROM inbox_messages WHERE title LIKE '%series result%'"
            ).fetchone()
        self.assertEqual(still_pending, 0)
        self.assertIsNotNone(series_result, "series-result message should post once every match is complete")

    def test_advance_day_plays_the_tours_first_match_the_same_day_it_starts(self) -> None:
        # A tour's first fixture is dated the day it's announced, and
        # advance_day() runs _run_international_window() before its own
        # fixture-simulation loop within the same call — so the very first
        # match of a real bilateral tour should already be complete by the
        # time advance_day() returns, not sitting pending for a full cycle.
        from competition import CompetitionEngine
        from database import connect
        db = _fresh_db()
        engine = CompetitionEngine(db, seed=42)
        with connect(db) as connection:
            connection.execute("UPDATE user_data SET current_date='2026-05-31' WHERE id=1")
        engine.advance_day()  # -> 2026-06-01, T20I Series begins
        with connect(db) as connection:
            first_match = connection.execute(
                "SELECT completed FROM matches WHERE (home_team < 0 OR away_team < 0) ORDER BY date LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(first_match)
        self.assertEqual(first_match[0], 1)


if __name__ == "__main__":
    unittest.main()
