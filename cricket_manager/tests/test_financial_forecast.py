"""Tests for the financial forecasting feature (roadmap: finance_forecasting).

The forecast projects committed cash flow (player wages, the active
sponsorship) plus estimated matchday income from home fixtures already on
the calendar, and flags months where the projected balance drops below the
board's minimum-cash objective.
"""
from __future__ import annotations
import json
import os
import tempfile
import unittest

from database import (add_financial_transaction, connect, forecast_finances,
                      get_team_summary, initialise_database, set_board_objectives)


def _fresh_db(pin_date: str = "2026-04-01") -> tuple[str, int]:
    """Initialise a throwaway DB and return (path, seeded team id). The
    forecast is anchored via its explicit ``current_date`` parameter rather
    than the save's game date, which the seed does not reliably pin."""
    db = os.path.join(tempfile.mkdtemp(), "forecast.db")
    initialise_database(db)
    team_id = get_team_summary(1, db)["id"]
    return db, team_id


def _wages_per_month(db: str, team_id: int) -> int:
    with connect(db) as connection:
        weekly = connection.execute(
            "SELECT COALESCE(SUM(wage), 0) FROM players WHERE team_id=?", (team_id,)).fetchone()[0]
    return int(round(weekly * 4.33))


def _active_sponsor(db: str, team_id: int) -> tuple[int, str] | None:
    with connect(db) as connection:
        row = connection.execute(
            "SELECT monthly_value, end_date FROM sponsorships "
            "WHERE team_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", (team_id,)).fetchone()
    return (int(row[0]), row[1]) if row else None


def _gate_per_fixture(db: str, team_id: int) -> int:
    team = get_team_summary(team_id, db)
    atmosphere = (team.get("stadium_level", 1) - 1) * .025
    demand = max(.48, min(.99, 1.12 - (team.get("ticket_price", 24) - 20) * .012 + atmosphere))
    attendance = int(team["stadium_capacity"] * demand)
    return int(attendance * team.get("ticket_price", 24))


class ForecastBackendTests(unittest.TestCase):
    def test_projects_committed_wages_and_sponsorship(self) -> None:
        db, team_id = _fresh_db()
        forecast = forecast_finances(team_id, db, months=12, current_date="2026-04-01")
        self.assertEqual(len(forecast["months"]), 12)
        self.assertEqual(forecast["months"][0]["month"], "2026-05")
        sponsor = _active_sponsor(db, team_id)
        self.assertIsNotNone(sponsor)
        first = forecast["months"][0]
        self.assertGreaterEqual(first["income"], sponsor[0])
        self.assertEqual(first["expenses"], _wages_per_month(db, team_id))
        # Cash balance is a running total built from net each month.
        expected = forecast["starting_cash"]
        for month in forecast["months"]:
            expected += month["net"]
            self.assertEqual(month["cash"], expected)
        self.assertEqual(forecast["ending_cash"], expected)
        # Wages line is committed (never estimated); sponsorship through end_date is not.
        categories = {ln["category"]: ln for ln in first["lines"]}
        self.assertFalse(categories["Wages"]["estimated"])
        self.assertFalse(categories["Sponsorships"]["estimated"])

    def test_matchday_income_uses_scheduled_home_fixtures(self) -> None:
        db, team_id = _fresh_db()
        with connect(db) as connection:
            connection.execute(
                """INSERT INTO matches (home_team, away_team, format, date, venue, completed,
                                        result_json, competition_id, round_name)
                   VALUES (?, 2, 'T20', '2026-05-10', 'Ground', 0, '{}', 1, 'League Round 1')""",
                (team_id,))
            connection.execute(
                """INSERT INTO matches (home_team, away_team, format, date, venue, completed,
                                        result_json, competition_id, round_name)
                   VALUES (?, 2, 'T20', '2026-05-17', 'Ground', 0, '{}', 1, 'League Round 2')""",
                (team_id,))
        forecast = forecast_finances(team_id, db, months=12, current_date="2026-04-01")
        may = next(m for m in forecast["months"] if m["month"] == "2026-05")
        gate = _gate_per_fixture(db, team_id)
        matchday = next(ln for ln in may["lines"] if ln["category"] == "Matchday Revenue")
        self.assertEqual(matchday["amount"], 2 * gate)
        self.assertTrue(matchday["estimated"])

    def test_sponsorship_renews_after_end_date(self) -> None:
        db, team_id = _fresh_db()
        sponsor = _active_sponsor(db, team_id)
        self.assertIsNotNone(sponsor)
        forecast = forecast_finances(team_id, db, months=24, current_date="2026-04-01")
        sponsor_months = [m for m in forecast["months"] if m["month"] <= sponsor[1][:7]]
        renewal_months = [m for m in forecast["months"] if m["month"] > sponsor[1][:7]]
        self.assertTrue(sponsor_months)
        self.assertTrue(renewal_months)
        original = sponsor[0]
        for month in renewal_months:
            renewal = next(ln for ln in month["lines"] if ln["category"] == "Sponsorships")
            self.assertGreater(renewal["amount"], original)
            self.assertTrue(renewal["estimated"])

    def test_flags_months_below_board_minimum_cash(self) -> None:
        db, team_id = _fresh_db()
        set_board_objectives(team_id, {"league_position": 6, "minimum_cash": 100_000_000,
                                       "youth_developed": 0}, db)
        forecast = forecast_finances(team_id, db, months=12, current_date="2026-04-01")
        self.assertTrue(forecast["risk_months"])
        for month in forecast["months"]:
            if month["month"] in forecast["risk_months"]:
                self.assertLess(month["cash"], forecast["minimum_cash"])

    def test_unknown_team_returns_empty(self) -> None:
        db, _team_id = _fresh_db()
        forecast = forecast_finances(999_999, db, months=12, current_date="2026-04-01")
        self.assertEqual(forecast["starting_cash"], 0)
        self.assertEqual(forecast["ending_cash"], 0)
        self.assertEqual(forecast["months"], [])

    def test_result_is_json_serialisable(self) -> None:
        db, team_id = _fresh_db()
        encoded = json.loads(json.dumps(forecast_finances(team_id, db, current_date="2026-04-01")))
        self.assertEqual(len(encoded["months"]), 12)


class ForecastIpcTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, load_game
        db, team_id = _fresh_db()
        game_data = load_game(db)
        team = get_team_summary(team_id, db)
        return {"database_path": db, "team": team, "players": fetch_players(team_id, db),
                "game_data": game_data}

    def test_get_financial_forecast_ipc_returns_display_fields(self) -> None:
        import ipc_server
        context = self._context()
        result = ipc_server._get_financial_forecast({"months": 6}, context)
        encoded = json.loads(json.dumps(result))
        self.assertIn("ending_cash_display", encoded)
        self.assertIn("minimum_cash_display", encoded)
        self.assertEqual(len(encoded["months"]), 6)
        first = encoded["months"][0]
        for key in ("month", "income", "expenses", "net", "cash", "income_display",
                    "expenses_display", "net_display", "cash_display", "lines"):
            self.assertIn(key, first)

    def test_get_financial_forecast_ipc_clamps_month_count(self) -> None:
        import ipc_server
        context = self._context()
        result = ipc_server._get_financial_forecast({"months": 999}, context)
        self.assertEqual(len(result["months"]), 36)


if __name__ == "__main__":
    unittest.main()
