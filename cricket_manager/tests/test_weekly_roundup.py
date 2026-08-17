"""v4.83.0: weekly roundup — pure-function + database helper tests."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import (connect, create_inbox_message, initialise_database,
                      fetch_week_completed_matches, fetch_week_injuries,
                      fetch_week_top_performances, fetch_week_transfers)
from src.models.weekly_roundup import build_roundup, format_roundup_as_text


class TemporaryGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()


class BuildRoundupTests(unittest.TestCase):
    def test_assembles_all_fields(self) -> None:
        roundup = build_roundup(
            user_results=[{"home_name": "A", "away_name": "B", "home_score": 200, "away_score": 180}],
            division_results=[],
            top_performers=[{"name": "X", "stat_line": "100* (League)"}],
            table_snapshot=[{"name": "A", "points": 30, "played": 5}],
            transfer_activity=[],
            injury_news=[],
            storyline_highlights=[],
            week_ending="2026-08-15",
        )
        self.assertEqual(roundup["week_ending"], "2026-08-15")
        self.assertEqual(len(roundup["user_results"]), 1)
        self.assertEqual(roundup["top_performers"][0]["name"], "X")


class FormatRoundupTests(unittest.TestCase):
    def test_user_results_section(self) -> None:
        roundup = build_roundup(
            user_results=[{"home_name": "Lions", "away_name": "Tigers",
                           "home_score": "245/6", "away_score": "189",
                           "result_text": "Lions won by 56 runs"}],
            division_results=[], top_performers=[], table_snapshot=[],
            transfer_activity=[], injury_news=[], storyline_highlights=[],
            week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("RESULTS (your team)", text)
        self.assertIn("Lions", text)
        self.assertIn("245/6", text)

    def test_division_results_section(self) -> None:
        results = [{"home_name": f"Team {i}", "away_name": f"Team {i+10}",
                    "home_score": 200, "away_score": 180, "result_text": ""}
                   for i in range(12)]
        roundup = build_roundup(
            user_results=[], division_results=results,
            top_performers=[], table_snapshot=[],
            transfer_activity=[], injury_news=[], storyline_highlights=[],
            week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("DIVISION RESULTS", text)
        self.assertIn("2 more", text)

    def test_top_performers_section(self) -> None:
        roundup = build_roundup(
            user_results=[], division_results=[],
            top_performers=[{"name": "J. Smith", "stat_line": "142* (League)"},
                            {"name": "K. Patel", "stat_line": "5/23 (League)"}],
            table_snapshot=[], transfer_activity=[], injury_news=[],
            storyline_highlights=[], week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("TOP PERFORMERS", text)
        self.assertIn("J. Smith", text)
        self.assertIn("142*", text)

    def test_table_snapshot_section(self) -> None:
        standings = [{"name": f"Team {i}", "points": 30 - i*5, "played": 5 + i}
                     for i in range(8)]
        roundup = build_roundup(
            user_results=[], division_results=[], top_performers=[],
            table_snapshot=standings, transfer_activity=[], injury_news=[],
            storyline_highlights=[], week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("STANDINGS", text)
        self.assertIn("Team 0", text)
        # Only top 6 shown
        self.assertNotIn("Team 6", text)

    def test_transfer_activity_section(self) -> None:
        roundup = build_roundup(
            user_results=[], division_results=[], top_performers=[],
            table_snapshot=[],
            transfer_activity=[{"player_name": "A. Jones", "from_name": "Lions",
                                "to_name": "Tigers", "fee": 500000}],
            injury_news=[], storyline_highlights=[], week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("TRANSFERS", text)
        self.assertIn("A. Jones", text)
        self.assertIn("£500,000", text)

    def test_injury_news_section(self) -> None:
        roundup = build_roundup(
            user_results=[], division_results=[], top_performers=[],
            table_snapshot=[], transfer_activity=[],
            injury_news=[{"player_name": "B. Khan", "team_name": "Eagles",
                          "severity": "Major", "return_date": "2026-09-15"}],
            storyline_highlights=[], week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("INJURY NEWS", text)
        self.assertIn("B. Khan", text)
        self.assertIn("Major", text)

    def test_empty_roundup_fallback(self) -> None:
        roundup = build_roundup(
            user_results=[], division_results=[], top_performers=[],
            table_snapshot=[], transfer_activity=[], injury_news=[],
            storyline_highlights=[], week_ending="2026-08-15")
        text = format_roundup_as_text(roundup)
        self.assertIn("Quiet week", text)


class FetchWeekMatchesTests(TemporaryGameTest, unittest.TestCase):
    def _make_teams(self, conn, suffix=""):
        conn.execute(f"INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('Host{suffix}',1,100000,20000)")
        conn.execute(f"INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('Visit{suffix}',1,100000,20000)")
        return conn.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 2").fetchall()

    def test_returns_completed_matches_in_range(self) -> None:
        with connect(self.database) as conn:
            ids = self._make_teams(conn)
            home_id, away_id = ids[0][0], ids[1][0]
            conn.execute(
                """INSERT INTO matches(home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (? ,?,'T20','2026-08-12','Venue',1,
                   '{"home_runs":200,"away_runs":180,"summary":"Host won by 20 runs"}')""",
                (home_id, away_id))
        results = fetch_week_completed_matches("2026-08-10", "2026-08-15", self.database)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["home_score"], 200)

    def test_excludes_matches_outside_range(self) -> None:
        with connect(self.database) as conn:
            ids = self._make_teams(conn, "2")
            home_id, away_id = ids[0][0], ids[1][0]
            conn.execute(
                """INSERT INTO matches(home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (? ,?,'T20','2026-08-01','Venue',1,'{}')""",
                (home_id, away_id))
        results = fetch_week_completed_matches("2026-08-10", "2026-08-15", self.database)
        self.assertEqual(len(results), 0)


class FetchWeekTransfersTests(TemporaryGameTest, unittest.TestCase):
    def test_returns_transfers_in_range(self) -> None:
        with connect(self.database) as conn:
            conn.execute("INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('TransferA',1,100000,20000)")
            conn.execute("INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('TransferB',1,100000,20000)")
            ids = conn.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 2").fetchall()
            home_id, away_id = ids[0][0], ids[1][0]
            conn.execute(
                "INSERT INTO players(name,age,nationality,role,batting_json,bowling_json,fielding_json,mental_json,overall,form,potential,team_id,wage) "
                "VALUES ('A. Jones',25,'ENG','Batsman','{}','{}','{}','{}',75,75,85,?,10000)",
                (home_id,))
            pid = conn.execute("SELECT id FROM players ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO transfers(player_id,from_team,to_team,fee,date,status) "
                "VALUES (?,?,?,?,?,?)",
                (pid, home_id, away_id, 500000, '2026-08-12', 'Completed'))
        transfers = fetch_week_transfers("2026-08-10", "2026-08-15", self.database)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0]["player_name"], "A. Jones")
        self.assertEqual(transfers[0]["fee"], 500000)


class FetchWeekInjuriesTests(TemporaryGameTest, unittest.TestCase):
    def test_returns_new_injuries_in_range(self) -> None:
        with connect(self.database) as conn:
            conn.execute("INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('InjuryTeam',1,100000,20000)")
            tid = conn.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO players(name,age,nationality,role,batting_json,bowling_json,fielding_json,mental_json,overall,form,potential,team_id,wage) "
                "VALUES ('B. Khan',28,'PAK','Bowler','{}','{}','{}','{}',80,80,82,?,12000)",
                (tid,))
            pid = conn.execute("SELECT id FROM players ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO injuries(player_id,severity,start_date,return_date,active) "
                "VALUES (?,'Major','2026-08-12','2026-09-15',1)",
                (pid,))
        injuries = fetch_week_injuries("2026-08-10", "2026-08-15", self.database)
        self.assertEqual(len(injuries), 1)
        self.assertEqual(injuries[0]["player_name"], "B. Khan")
        self.assertEqual(injuries[0]["team_name"], "InjuryTeam")


class FetchWeekTopPerformancesTests(TemporaryGameTest, unittest.TestCase):
    def test_returns_top_performances_in_range(self) -> None:
        with connect(self.database) as conn:
            conn.execute("INSERT INTO teams(name,division,cash,stadium_capacity) VALUES ('PerfTeam',1,100000,20000)")
            tid = conn.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO players(name,age,nationality,role,batting_json,bowling_json,fielding_json,mental_json,overall,form,potential,team_id,wage) "
                "VALUES ('C. Davis',22,'ENG','Batsman','{}','{}','{}','{}',70,70,80,?,8000)",
                (tid,))
            pid = conn.execute("SELECT id FROM players ORDER BY id DESC LIMIT 1").fetchone()[0]
            conn.execute(
                "INSERT INTO player_form_history(player_id,match_date,performance,context) "
                "VALUES (?,'2026-08-12',85.0,'League')",
                (pid,))
            conn.execute(
                "INSERT INTO player_form_history(player_id,match_date,performance,context) "
                "VALUES (?,'2026-08-14',92.0,'League')",
                (pid,))
        perfs = fetch_week_top_performances("2026-08-10", "2026-08-15",
                                            limit=5, database_path=self.database)
        self.assertEqual(len(perfs), 2)
        self.assertEqual(perfs[0]["player_name"], "C. Davis")
        self.assertEqual(perfs[0]["performance"], 92.0)


if __name__ == "__main__":
    unittest.main()
