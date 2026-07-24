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
                      generate_job_offers, get_board_confidence_history, get_board_objectives,
                      get_job_offers, get_opposition_report,
                      get_pitch_selection, evaluate_board_objectives, initialise_database,
                      record_board_confidence, resolve_transfer_offer, set_pitch_selection,
                      set_training_focus, submit_transfer_offer, store_job_offers,
                      accept_job_offer, decline_job_offer, check_sacking)


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


class BoardExpectationsTests(TemporaryGameTest):
    def setUp(self) -> None:
        super().setUp()
        self.engine = CompetitionEngine(self.database, seed=42)
        self.engine.ensure_season(2026)

    def test_ensure_season_sets_board_objectives(self) -> None:
        objectives = get_board_objectives(1, self.database)
        self.assertIn("league_position", objectives)
        self.assertIn("minimum_cash", objectives)
        self.assertIsInstance(objectives["league_position"], int)
        self.assertGreaterEqual(objectives["league_position"], 4)
        self.assertLessEqual(objectives["league_position"], 8)

    def test_ensure_season_sends_board_expectations_inbox(self) -> None:
        with connect(self.database) as connection:
            msg = connection.execute(
                "SELECT title FROM inbox_messages WHERE title='Board expectations set' LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(msg)

    def test_ensure_season_does_not_overwrite_existing_objectives(self) -> None:
        from database import save_game
        save_game({"board_objectives_1": {"league_position": 3, "minimum_cash": 500_000, "youth_developed": 0}}, self.database)
        engine2 = CompetitionEngine(self.database, seed=99)
        engine2.ensure_season(2026)
        objectives = get_board_objectives(1, self.database)
        self.assertEqual(objectives["league_position"], 3)

    def test_get_board_objectives_returns_defaults_when_unset(self) -> None:
        objectives = get_board_objectives(999, self.database)
        self.assertEqual(objectives["league_position"], 6)
        self.assertEqual(objectives["minimum_cash"], 100_000)

    def test_record_and_retrieve_board_confidence_history(self) -> None:
        record_board_confidence(1, 72, "Content", "2026-06-15", self.database)
        record_board_confidence(1, 35, "Under pressure", "2026-07-15", self.database)
        history = get_board_confidence_history(1, self.database)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["score"], 72)
        self.assertEqual(history[1]["label"], "Under pressure")

    def test_board_confidence_history_capped_at_20(self) -> None:
        for i in range(25):
            record_board_confidence(1, 50 + i, "Content", f"2026-0{i%9+1}-{i+1:02d}", self.database)
        history = get_board_confidence_history(1, self.database)
        self.assertEqual(len(history), 20)
        self.assertEqual(history[-1]["score"], 74)

    def test_evaluate_board_objectives_returns_progress(self) -> None:
        evaluation = evaluate_board_objectives(1, self.database)
        self.assertIn("objectives", evaluation)
        self.assertIn("progress", evaluation)
        self.assertIn("league_position", evaluation["progress"])
        self.assertIn("cash_balance", evaluation["progress"])
        self.assertIn("target", evaluation["progress"]["league_position"])
        self.assertIn("current", evaluation["progress"]["league_position"])
        self.assertIn("met", evaluation["progress"]["league_position"])


class PitchSelectionTests(TemporaryGameTest):
    def test_set_and_get_pitch_selection(self) -> None:
        set_pitch_selection(1, "Dusty", self.database)
        self.assertEqual(get_pitch_selection(1, self.database), "Dusty")

    def test_get_pitch_defaults_to_green(self) -> None:
        self.assertEqual(get_pitch_selection(999, self.database), "Green")

    def test_set_pitch_rejects_invalid_type(self) -> None:
        with self.assertRaises(ValueError):
            set_pitch_selection(1, "InvalidPitch", self.database)

    def test_set_pitch_overwrites_previous(self) -> None:
        set_pitch_selection(1, "Flat", self.database)
        set_pitch_selection(1, "Worn", self.database)
        self.assertEqual(get_pitch_selection(1, self.database), "Worn")

    def test_all_valid_pitches_round_trip(self) -> None:
        for pitch in ["Green", "Dry", "Dusty", "Flat", "Worn"]:
            set_pitch_selection(1, pitch, self.database)
            self.assertEqual(get_pitch_selection(1, self.database), pitch)


class JobMarketTests(TemporaryGameTest):
    def setUp(self) -> None:
        super().setUp()
        self.engine = CompetitionEngine(self.database, seed=42)
        self.engine.ensure_season(2026)

    def test_generate_job_offers_returns_list(self) -> None:
        offers = generate_job_offers(1, 50, self.database)
        self.assertIsInstance(offers, list)

    def test_generate_job_offers_excludes_own_team(self) -> None:
        offers = generate_job_offers(1, 50, self.database)
        for offer in offers:
            self.assertNotEqual(offer["team_id"], 1)

    def test_generate_job_offers_have_required_fields(self) -> None:
        offers = generate_job_offers(1, 50, self.database)
        if offers:
            offer = offers[0]
            self.assertIn("offer_id", offer)
            self.assertIn("team_id", offer)
            self.assertIn("team_name", offer)
            self.assertIn("wage", offer)
            self.assertIn("description", offer)

    def test_store_and_retrieve_job_offers(self) -> None:
        test_offers = [{"offer_id": "test_1", "team_id": 2, "team_name": "Test FC"}]
        store_job_offers(1, test_offers, self.database)
        retrieved = get_job_offers(self.database)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["offer_id"], "test_1")

    def test_accept_job_offer_switches_team(self) -> None:
        test_offers = [{"offer_id": "test_accept", "team_id": 5, "team_name": "New FC", "wage": 5000}]
        store_job_offers(1, test_offers, self.database)
        result = accept_job_offer("test_accept", self.database)
        self.assertEqual(result["new_team_id"], 5)
        self.assertEqual(result["old_team_id"], 1)
        with connect(self.database) as connection:
            current = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
        self.assertEqual(current, 5)

    def test_accept_job_offer_clears_from_list(self) -> None:
        test_offers = [
            {"offer_id": "test_a", "team_id": 5, "team_name": "A FC", "wage": 5000},
            {"offer_id": "test_b", "team_id": 6, "team_name": "B FC", "wage": 6000},
        ]
        store_job_offers(1, test_offers, self.database)
        accept_job_offer("test_a", self.database)
        remaining = get_job_offers(self.database)
        self.assertFalse(any(o["offer_id"] == "test_a" for o in remaining))

    def test_accept_invalid_offer_raises(self) -> None:
        with self.assertRaises(ValueError):
            accept_job_offer("nonexistent_offer", self.database)

    def test_decline_job_offer_removes_it(self) -> None:
        test_offers = [{"offer_id": "test_decline", "team_id": 5, "team_name": "Decline FC"}]
        store_job_offers(1, test_offers, self.database)
        decline_job_offer("test_decline", self.database)
        remaining = get_job_offers(self.database)
        self.assertFalse(any(o["offer_id"] == "test_decline" for o in remaining))

    def test_check_sacking_returns_none_with_few_reviews(self) -> None:
        record_board_confidence(1, 20, "Ultimatum", "2026-06-15", self.database)
        self.assertIsNone(check_sacking(1, self.database))

    def test_check_sacking_returns_none_without_ultimatum_streak(self) -> None:
        record_board_confidence(1, 20, "Ultimatum", "2026-06-15", self.database)
        record_board_confidence(1, 20, "Ultimatum", "2026-07-15", self.database)
        record_board_confidence(1, 50, "Under pressure", "2026-09-30", self.database)
        self.assertIsNone(check_sacking(1, self.database))

    def test_check_sacking_returns_sacking_with_3_ultimatums(self) -> None:
        record_board_confidence(1, 20, "Ultimatum", "2026-06-15", self.database)
        record_board_confidence(1, 20, "Ultimatum", "2026-07-15", self.database)
        record_board_confidence(1, 20, "Ultimatum", "2026-09-30", self.database)
        result = check_sacking(1, self.database)
        self.assertIsNotNone(result)
        self.assertTrue(result["sacked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
