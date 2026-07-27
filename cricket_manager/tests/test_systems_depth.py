"""Systems-depth checks: T10 format, keeper byes accounting, monthly P&L."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "depth.db")
    initialise_database(path)
    return path


class T10FormatTests(unittest.TestCase):
    def _play(self, fmt: str):
        from database import fetch_players, fetch_teams
        from match_engine import Match
        db = _fresh_db()
        teams = fetch_teams(db)
        home, away = dict(teams[0]), dict(teams[1])
        match = Match(home, away, fetch_players(home["id"], db)[:11],
                      fetch_players(away["id"], db)[:11], fmt)
        for _ in range(4000):
            if match.completed: break
            match.event_pool.release(match.ball_outcome())
        return match

    def test_t10_is_a_valid_completing_format(self) -> None:
        match = self._play("T10")
        self.assertEqual(match.overs_limit(), 10)
        self.assertTrue(match.completed)
        for innings in match.innings:
            self.assertLessEqual(innings.legal_balls, 60)

    def test_hundred_uses_five_ball_sets_and_twenty_ball_bowler_cap(self) -> None:
        match = self._play("Hundred")
        self.assertEqual(match.balls_per_set, 5)
        self.assertEqual(match.overs_limit(), 20)
        self.assertTrue(match.completed)
        for innings in match.innings:
            self.assertLessEqual(innings.legal_balls, 100)
            self.assertEqual(innings.balls_per_set, 5)
            self.assertTrue(all(line.balls <= 20 for line in innings.bowlers.values()))

    def test_hundred_scorecard_and_notation_are_set_aware(self) -> None:
        from database import fetch_players, fetch_teams
        from match_engine import Match, overs_text
        db = _fresh_db(); teams = fetch_teams(db)
        match = Match(dict(teams[0]), dict(teams[1]), fetch_players(teams[0]["id"], db)[:11],
                      fetch_players(teams[1]["id"], db)[:11], "Hundred", seed=14)
        while match.current_innings.legal_balls < 10:
            match.event_pool.release(match.ball_outcome())
        self.assertEqual(overs_text(9, 5), "1.4")
        self.assertEqual(match.scorecard()["overs"], "2.0")

    def test_innings_totals_reconcile_including_byes(self) -> None:
        match = self._play("T20")
        for innings in match.innings:
            batter_runs = sum(line.runs for line in innings.batters.values())
            extras = sum(innings.extras.values())
            self.assertEqual(innings.runs, batter_runs + extras,
                             f"{innings.batting_name}: {innings.runs} != {batter_runs}+{extras}")


class MonthlyPnlTests(unittest.TestCase):
    def test_monthly_report_lands_in_inbox(self) -> None:
        from competition import CompetitionEngine
        from database import add_financial_transaction, fetch_inbox_messages, fetch_teams
        db = _fresh_db()
        team_id = fetch_teams(db)[0]["id"]
        add_financial_transaction(team_id, "2026-06-05", "Matchday", "INCOME", 40_000, "Gate receipts", db)
        add_financial_transaction(team_id, "2026-06-08", "Wages", "EXPENSE", 25_000, "Weekly player wages", db)
        CompetitionEngine(db)._send_monthly_pnl_report(team_id, date(2026, 7, 1))
        messages = fetch_inbox_messages(5, db)
        report = next((m for m in messages if "Monthly accounts" in m["title"]), None)
        self.assertIsNotNone(report)
        self.assertIn("June 2026", report["title"])
        self.assertIn("40,000", report["content"])
        self.assertIn("Closing balance", report["content"])


class VersionConsistencyTests(unittest.TestCase):
    def test_app_version_matches_shipped_config(self) -> None:
        import json
        from src.utilities.launcher import app_version
        with open("config.json", encoding="utf-8") as handle:
            shipped = json.load(handle)
        self.assertEqual(app_version(), shipped["version"])

    def test_stale_user_config_is_migrated_on_launch(self) -> None:
        import json
        from pathlib import Path
        from src.utilities.launcher import LaunchPaths, ensure_config
        base = Path(tempfile.mkdtemp())
        paths = LaunchPaths(Path("."), base, base / "config.json", base / "data",
                            base / "logs", base / "data" / "x.db", base / "data" / "r.db",
                            base / "data" / "s.lock")
        stale = json.loads(Path("config.json").read_text(encoding="utf-8"))
        stale["version"] = "0.9.0"
        stale["colours"]["background"] = "#0d1117"
        paths.config.write_text(json.dumps(stale), encoding="utf-8")
        config = ensure_config(paths)
        self.assertNotEqual(config["version"], "0.9.0")
        shipped_background = json.loads(Path("config.json").read_text(encoding="utf-8"))["colours"]["background"]
        self.assertEqual(config["colours"]["background"], shipped_background)


if __name__ == "__main__":
    unittest.main()
