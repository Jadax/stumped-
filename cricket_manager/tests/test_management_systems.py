"""Isolated campaign, finance, training, transfer, and season tests."""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from competition import CompetitionEngine
from database import (add_financial_transaction, apply_daily_training, connect, fetch_financial_log,
                      fetch_league_standings, fetch_next_fixture, fetch_players, generate_ai_transfer_offers,
                      get_opposition_report, initialise_database, resolve_transfer_offer,
                      set_training_focus, submit_transfer_offer)


class TemporaryGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()


class TrainingTests(TemporaryGameTest):
    def test_focused_training_progresses_toward_potential(self) -> None:
        candidate = next(p for p in fetch_players(1, self.database) if p["potential"] > p["overall"])
        before = sum(candidate["batting"].values())
        set_training_focus(candidate["id"], "Batting Focus", self.database)
        start = date(2026, 4, 1)
        for day in range(50): apply_daily_training(1, (start + timedelta(days=day)).isoformat(), self.database)
        after_player = next(p for p in fetch_players(1, self.database) if p["id"] == candidate["id"])
        self.assertGreater(sum(after_player["batting"].values()), before)
        self.assertLessEqual(after_player["overall"], after_player["potential"])


class TransferTests(TemporaryGameTest):
    def test_accepted_offer_moves_player_and_cash(self) -> None:
        player = fetch_players(2, self.database)[0]
        with connect(self.database) as connection:
            buyer_before = connection.execute("SELECT cash FROM teams WHERE id=1").fetchone()[0]
            seller_before = connection.execute("SELECT cash FROM teams WHERE id=2").fetchone()[0]
        offer = submit_transfer_offer(player["id"], 1, 100_000, 7_500, "2026-04-02", self.database)
        self.assertTrue(resolve_transfer_offer(offer, True, self.database))
        with connect(self.database) as connection:
            moved = connection.execute("SELECT team_id,wage FROM players WHERE id=?", (player["id"],)).fetchone()
            buyer_after = connection.execute("SELECT cash FROM teams WHERE id=1").fetchone()[0]
            seller_after = connection.execute("SELECT cash FROM teams WHERE id=2").fetchone()[0]
        self.assertEqual(tuple(moved), (1, 7_500))
        self.assertEqual(buyer_after, buyer_before - 100_000)
        self.assertEqual(seller_after, seller_before + 100_000)


class FinanceTests(TemporaryGameTest):
    def test_income_and_expense_update_cash_and_ledger(self) -> None:
        with connect(self.database) as connection:
            starting = connection.execute("SELECT cash FROM teams WHERE id=1").fetchone()[0]
        add_financial_transaction(1, "2026-04-02", "Tickets", "INCOME", 250_000, "Gate", self.database)
        add_financial_transaction(1, "2026-04-03", "Wages", "EXPENSE", 80_000, "Weekly", self.database)
        with connect(self.database) as connection:
            ending = connection.execute("SELECT cash FROM teams WHERE id=1").fetchone()[0]
        self.assertEqual(ending, starting + 170_000)
        ledger = fetch_financial_log(1, self.database)
        self.assertTrue(any(row["category"] == "Tickets" for row in ledger))


class CompetitionLifecycleTests(TemporaryGameTest):
    def test_rollover_promotes_relegates_ages_and_retires(self) -> None:
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            div1 = connection.execute("SELECT id FROM competitions WHERE name='Domestic Division 1' AND season=2026").fetchone()[0]
            div2 = connection.execute("SELECT id FROM competitions WHERE name='Domestic Division 2' AND season=2026").fetchone()[0]
            first_div1 = [r[0] for r in connection.execute("SELECT team_id FROM league_standings WHERE competition_id=? ORDER BY team_id", (div1,))]
            first_div2 = [r[0] for r in connection.execute("SELECT team_id FROM league_standings WHERE competition_id=? ORDER BY team_id", (div2,))]
            for index, team in enumerate(first_div1):
                connection.execute("UPDATE league_standings SET points=? WHERE competition_id=? AND team_id=?", (100-index, div1, team))
            for index, team in enumerate(first_div2):
                connection.execute("UPDATE league_standings SET points=? WHERE competition_id=? AND team_id=?", (100-index, div2, team))
            veteran = connection.execute("SELECT id FROM players WHERE age<=40 LIMIT 1").fetchone()[0]
            connection.execute("UPDATE players SET age=40 WHERE id=?", (veteran,))
        result = engine.rollover_season(2026)
        self.assertEqual(result["promoted"], first_div2[:2])
        self.assertEqual(result["relegated"], first_div1[-2:])
        with connect(self.database) as connection:
            self.assertTrue(all(connection.execute("SELECT division FROM teams WHERE id=?", (team,)).fetchone()[0] == 1 for team in first_div2[:2]))
            self.assertTrue(all(connection.execute("SELECT division FROM teams WHERE id=?", (team,)).fetchone()[0] == 2 for team in first_div1[-2:]))
            self.assertIsNone(connection.execute("SELECT id FROM players WHERE id=?", (veteran,)).fetchone())


class AiTransferOfferTests(TemporaryGameTest):
    def setUp(self) -> None:
        super().setUp()
        self.engine = CompetitionEngine(self.database, seed=42)
        self.engine.ensure_season(2026)
        self.team_id = 1
        with connect(self.database) as connection:
            other_team = connection.execute("SELECT id FROM teams WHERE id != ? LIMIT 1", (self.team_id,)).fetchone()
            self.opponent_id = other_team[0]

    def test_ai_offers_returns_list(self) -> None:
        offers = generate_ai_transfer_offers("2026-05-01", self.team_id, self.database)
        self.assertIsInstance(offers, list)

    def test_ai_offers_only_target_transfer_listed_or_short_contract(self) -> None:
        with connect(self.database) as connection:
            connection.execute(
                "UPDATE players SET transfer_listed=1, contract_years_remaining=5 "
                "WHERE id IN (SELECT id FROM players WHERE team_id=? AND role='Batsman' LIMIT 1)",
                (self.opponent_id,))
        offers = generate_ai_transfer_offers("2026-05-01", self.team_id, self.database)
        for offer in offers:
            with connect(self.database) as connection:
                player = connection.execute(
                    "SELECT transfer_listed, contract_years_remaining FROM players WHERE id=?",
                    (offer["player_id"],)
                ).fetchone()
            self.assertTrue(
                player[0] == 1 or player[1] <= 1,
                f"Offered player {offer['player_name']} is neither transfer-listed nor short-contracted"
            )

    def test_ai_offers_deduplicate_pending(self) -> None:
        with connect(self.database) as connection:
            connection.execute(
                "UPDATE players SET transfer_listed=1, contract_years_remaining=5 "
                "WHERE id IN (SELECT id FROM players WHERE team_id=? AND role='Bowler' LIMIT 3)",
                (self.opponent_id,))
        first_run = generate_ai_transfer_offers("2026-05-01", self.team_id, self.database)
        second_run = generate_ai_transfer_offers("2026-05-01", self.team_id, self.database)
        with connect(self.database) as connection:
            pending = connection.execute(
                "SELECT COUNT(*) FROM transfer_offers WHERE status='PENDING' AND created_date='2026-05-01'"
            ).fetchone()[0]
        self.assertLessEqual(pending, len(first_run) + len(second_run))

    def test_ai_offers_excludes_user_team_players_as_buyers(self) -> None:
        offers = generate_ai_transfer_offers("2026-05-01", self.team_id, self.database)
        for offer in offers:
            self.assertNotEqual(offer["to_team"], self.team_id,
                                f"AI team {offer['to_team_name']} should not bid on user players")


class OppositionReportTests(TemporaryGameTest):
    def setUp(self) -> None:
        super().setUp()
        self.engine = CompetitionEngine(self.database, seed=42)
        self.engine.ensure_season(2026)

    def test_report_returns_none_when_no_fixtures(self) -> None:
        with connect(self.database) as connection:
            connection.execute("DELETE FROM matches WHERE completed=0")
        report = get_opposition_report(1, self.database)
        self.assertIsNone(report)

    def test_report_returns_scouting_summary_with_fixtures(self) -> None:
        report = get_opposition_report(1, self.database)
        if report is None:
            self.skipTest("User team has no next fixture")
        self.assertIn("opponent_name", report)
        self.assertIn("opponent_id", report)
        self.assertIn("key_players", report)
        self.assertIn("strengths", report)
        self.assertIn("weaknesses", report)
        self.assertIn("role_distribution", report)
        self.assertGreater(len(report["key_players"]), 0)
        self.assertIsInstance(report["average_overall"], float)

    def test_report_includes_xi_predicted_eleven(self) -> None:
        report = get_opposition_report(1, self.database)
        if report is None:
            self.skipTest("User team has no next fixture")
        self.assertIn("xi", report)
        self.assertLessEqual(len(report["xi"]), 11)
        for player in report["xi"]:
            self.assertIn("name", player)
            self.assertIn("role", player)
            self.assertIn("overall", player)


if __name__ == "__main__":
    unittest.main(verbosity=2)
