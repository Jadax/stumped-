"""Tests for pre-season friendlies system (v4.98.0)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialise_database, add_financial_transaction
from src.models.pre_season import (
    format_friendly_fixtures,
    friendly_attendance,
    friendly_gate_revenue,
    generate_pre_season_schedule,
)


class GeneratePreSeasonScheduleTests(unittest.TestCase):
    def setUp(self):
        self.teams = [1, 2, 3, 4, 5, 6]
        self.names = {1: "Team A", 2: "Team B", 3: "Team C",
                      4: "Team D", 5: "Team E", 6: "Team F"}

    def _schedule(self):
        return generate_pre_season_schedule(self.teams, self.names, 2026)

    def test_even_clubs_play_four_matches_each(self):
        fixtures = self._schedule()
        for tid in self.teams:
            played = sum(1 for f in fixtures if tid in (f["home_team"], f["away_team"]))
            self.assertEqual(played, 4, f"team {tid} should play four friendlies")

    def test_no_double_booking(self):
        fixtures = self._schedule()
        seen = set()
        for f in fixtures:
            key = (f["date"], f["home_team"])
            key2 = (f["date"], f["away_team"])
            self.assertNotIn(key, seen)
            self.assertNotIn(key2, seen)
            seen.add(key)
            seen.add(key2)

    def test_home_away_balance(self):
        fixtures = self._schedule()
        for tid in self.teams:
            home = sum(1 for f in fixtures if f["home_team"] == tid)
            away = sum(1 for f in fixtures if f["away_team"] == tid)
            self.assertEqual(home, 2, f"team {tid} home count")
            self.assertEqual(away, 2, f"team {tid} away count")

    def test_no_self_fixtures(self):
        for f in self._schedule():
            self.assertNotEqual(f["home_team"], f["away_team"])

    def test_dates_in_march(self):
        for f in self._schedule():
            self.assertTrue(f["date"].startswith("2026-03"))

    def test_format_is_t20(self):
        for f in self._schedule():
            self.assertEqual(f["format"], "T20")

    def test_empty_or_single_team_list(self):
        self.assertEqual(generate_pre_season_schedule([], self.names, 2026), [])
        self.assertEqual(generate_pre_season_schedule([1], self.names, 2026), [])

    def test_deterministic_with_seed(self):
        r1 = generate_pre_season_schedule(self.teams, self.names, 2026)
        r2 = generate_pre_season_schedule(self.teams, self.names, 2026)
        self.assertEqual(r1, r2)


class FriendlyGateRevenueTests(unittest.TestCase):
    def test_gate_revenue_basic(self):
        revenue = friendly_gate_revenue(15000, 25)
        self.assertEqual(revenue, 15000 * 0.65 * 25)

    def test_gate_revenue_custom_attendance(self):
        revenue = friendly_gate_revenue(20000, 30, 0.8)
        self.assertEqual(revenue, 20000 * 0.8 * 30)

    def test_attendance_basic(self):
        att = friendly_attendance(15000)
        self.assertEqual(att, int(15000 * 0.65))

    def test_attendance_custom_pct(self):
        att = friendly_attendance(20000, 0.5)
        self.assertEqual(att, 10000)


class FormatFriendlyFixturesTests(unittest.TestCase):
    def test_empty(self):
        result = format_friendly_fixtures([], 1)
        self.assertEqual(result, "No pre-season friendlies scheduled.")

    def test_with_fixtures(self):
        fixtures = [
            {"home_team": 1, "away_team": 2, "home_name": "A", "away_name": "B",
             "date": "2026-03-01", "format": "T20"},
            {"home_team": 3, "away_team": 1, "home_name": "C", "away_name": "A",
             "date": "2026-03-05", "format": "T20"},
        ]
        result = format_friendly_fixtures(fixtures, 1)
        self.assertIn("Pre-season", result)
        self.assertIn("A vs B", result)
        self.assertIn("C vs A", result)
        # Venue labels follow the subject club, not list order
        home_lines = [ln for ln in result.splitlines() if "(Home" in ln]
        away_lines = [ln for ln in result.splitlines() if "(Away" in ln]
        self.assertEqual(len(home_lines), 1)
        self.assertEqual(len(away_lines), 1)


class FriendlyMatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_friendly_round_name_persists(self):
        from database import connect
        with connect(self.db) as conn:
            conn.execute(
                """INSERT INTO matches
                   (home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (1,2,'T20','2026-03-01','Ground',0,'{}')""")
            # round_name defaults to 'League' from the schema migration
            row = conn.execute("SELECT round_name FROM matches LIMIT 1").fetchone()
        self.assertEqual(row["round_name"], "League")
        # Now explicitly set to Friendly
        with connect(self.db) as conn:
            conn.execute("UPDATE matches SET round_name='Friendly' WHERE id=1")
            row = conn.execute("SELECT round_name FROM matches LIMIT 1").fetchone()
        self.assertEqual(row["round_name"], "Friendly")


if __name__ == "__main__":
    unittest.main()
