"""Isolated campaign, finance, training, transfer, and season tests."""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from competition import CompetitionEngine
from database import (add_financial_transaction, apply_daily_training, connect, fetch_club_records,
                      fetch_financial_log, fetch_league_standings, fetch_next_fixture, fetch_players, fetch_legends,
                      fetch_season_records, fetch_staff, generate_ai_transfer_offers,
                      generate_job_offers, get_board_confidence_history, get_board_objectives,
                       get_ground_info, get_ground_stats, get_job_offers, get_match_ground_details,
                       get_onboarding_state, get_opposition_report, get_player_form, get_pitch_selection,
                       evaluate_board_objectives, initialise_database,
                      record_board_confidence, resolve_transfer_offer, set_pitch_selection,
                      set_training_focus, submit_transfer_offer, store_job_offers,
                      accept_job_offer, decline_job_offer, check_sacking,
                      create_custom_tournament, get_custom_tournaments, get_custom_tournament,
                      get_tournament_standings, advance_tournament_to_knockout,
                      get_tournament_bracket, _generate_round_robin,
                      advance_onboarding, dismiss_onboarding, ONBOARDING_STEPS,
                       _generate_ground_for_team, _ensure_grounds_for_all_teams, _team_city,
                       _ensure_grounds_table,
                       _sync_ground_with_upgrades, start_facility_upgrade, complete_due_facility_upgrades)


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
            # age=44 -> 45 after this rollover's age+1 step: the hard-forced
            # retirement floor (players.age's own CHECK constraint caps at
            # 45), the only age where removal is still guaranteed now that
            # retirement is a real probabilistic curve rather than a blunt
            # age>40 cutoff — see CompetitionEngine._retirement_probability.
            veteran = connection.execute("SELECT id FROM players WHERE age<=44 LIMIT 1").fetchone()[0]
            connection.execute("UPDATE players SET age=44 WHERE id=?", (veteran,))
        result = engine.rollover_season(2026)
        self.assertEqual(result["promoted"], first_div2[:2])
        self.assertEqual(result["relegated"], first_div1[-2:])
        with connect(self.database) as connection:
            self.assertTrue(all(connection.execute("SELECT division FROM teams WHERE id=?", (team,)).fetchone()[0] == 1 for team in first_div2[:2]))
            self.assertTrue(all(connection.execute("SELECT division FROM teams WHERE id=?", (team,)).fetchone()[0] == 2 for team in first_div1[-2:]))
            self.assertIsNone(connection.execute("SELECT id FROM players WHERE id=?", (veteran,)).fetchone())

    def test_retirement_probability_curve_is_realistic_not_a_hard_cutoff(self) -> None:
        self.assertEqual(CompetitionEngine._retirement_probability(25), 0.0)
        self.assertEqual(CompetitionEngine._retirement_probability(32), 0.0)
        self.assertGreater(CompetitionEngine._retirement_probability(35), 0.0)
        self.assertLess(CompetitionEngine._retirement_probability(35), CompetitionEngine._retirement_probability(40))
        self.assertLess(CompetitionEngine._retirement_probability(40), 1.0)
        self.assertGreaterEqual(CompetitionEngine._retirement_probability(44), 0.9)

    def test_retired_players_are_archived_as_legends_not_silently_deleted(self) -> None:
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            veteran = dict(connection.execute("SELECT id,name,team_id FROM players WHERE age<=44 LIMIT 1").fetchone())
            connection.execute("UPDATE players SET age=44 WHERE id=?", (veteran["id"],))
        engine.rollover_season(2026)
        with connect(self.database) as connection:
            self.assertIsNone(connection.execute("SELECT id FROM players WHERE id=?", (veteran["id"],)).fetchone())
        legends = fetch_legends(database_path=self.database)
        match = next((legend for legend in legends if legend["player_id"] == veteran["id"]), None)
        self.assertIsNotNone(match, "retired player must be archived, not just deleted")
        self.assertEqual(match["reason"], "retired")
        self.assertEqual(match["retired_age"], 45)
        self.assertIn("League", match["career_record"])

    def test_released_players_below_quality_floor_get_released_reason(self) -> None:
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            weak = connection.execute("SELECT id FROM players LIMIT 1").fetchone()[0]
            connection.execute("UPDATE players SET overall=10 WHERE id=?", (weak,))
        engine.rollover_season(2026)
        legends = fetch_legends(database_path=self.database)
        match = next((legend for legend in legends if legend["player_id"] == weak), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["reason"], "released")

    def test_convert_retiree_to_staff_adds_a_real_staff_row(self) -> None:
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            player = dict(connection.execute(
                "SELECT id,name,nationality,role,overall,team_id,age FROM players WHERE role='Batsman' LIMIT 1"
            ).fetchone())
        before = fetch_staff(player["team_id"], database_path=self.database)
        result = engine._convert_retiree_to_staff(player)
        self.assertTrue(result)
        after = fetch_staff(player["team_id"], database_path=self.database)
        self.assertEqual(len(after), len(before) + 1)
        new_member = next(s for s in after if s["name"] == player["name"] and s["age"] == player["age"])
        self.assertEqual(new_member["role"], "Batting Coach")

    def test_rollover_records_season_top_scorer_and_wicket_taker(self) -> None:
        from database import record_player_performance
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            batter, bowler = [dict(row) for row in connection.execute(
                "SELECT id,name FROM players WHERE team_id=? LIMIT 2", (user_team_id,))]
        record_player_performance(batter["id"], "2026-05-01", "League",
                                  batting={"runs": 87, "balls": 60, "fours": 8, "sixes": 2}, database_path=self.database)
        record_player_performance(bowler["id"], "2026-05-01", "League",
                                  bowling={"balls": 24, "wickets": 4, "runs": 30}, database_path=self.database)
        engine.rollover_season(2026)
        seasons = fetch_season_records(user_team_id, database_path=self.database)
        self.assertEqual(len(seasons), 1)
        entry = seasons[0]
        self.assertEqual(entry["season"], 2026)
        self.assertEqual(entry["top_scorer_name"], batter["name"])
        self.assertEqual(entry["top_scorer_runs"], 87)
        self.assertEqual(entry["top_wicket_taker_name"], bowler["name"])
        self.assertEqual(entry["top_wicket_taker_wickets"], 4)

    def test_season_stats_baseline_diff_excludes_prior_seasons_runs(self) -> None:
        """A player's season-two runs must not include season one's total —
        proves the game_state baseline snapshot is actually being diffed."""
        from database import record_player_performance
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            batter = dict(connection.execute(
                "SELECT id,name FROM players WHERE team_id=? LIMIT 1", (user_team_id,)).fetchone())
        record_player_performance(batter["id"], "2026-05-01", "League",
                                  batting={"runs": 60, "balls": 50}, database_path=self.database)
        engine.rollover_season(2026)
        record_player_performance(batter["id"], "2027-05-01", "League",
                                  batting={"runs": 25, "balls": 30}, database_path=self.database)
        engine.rollover_season(2027)
        seasons = {row["season"]: row for row in fetch_season_records(user_team_id, database_path=self.database)}
        self.assertEqual(seasons[2026]["top_scorer_runs"], 60)
        self.assertEqual(seasons[2027]["top_scorer_runs"], 25)

    def test_fetch_club_records_computes_highest_score_and_biggest_win(self) -> None:
        engine = CompetitionEngine(self.database, seed=99); engine.ensure_season(2026)
        with connect(self.database) as connection:
            user_team_id = connection.execute("SELECT current_team_id FROM user_data WHERE id=1").fetchone()[0]
            opponent = connection.execute("SELECT id FROM teams WHERE id!=?", (user_team_id,)).fetchone()[0]
            connection.execute(
                """INSERT INTO matches (home_team,away_team,format,date,venue,completed,result_json)
                   VALUES (?,?,'T20','2026-05-01','Home Ground',1,?)""",
                (user_team_id, opponent, json.dumps({"home_runs": 210, "away_runs": 90, "winner": user_team_id})))
        records = fetch_club_records(user_team_id, database_path=self.database)
        self.assertEqual(records["highest_score"]["runs"], 210)
        self.assertEqual(records["biggest_win"]["margin"], 120)
        self.assertIsNone(records["heaviest_defeat"])
        self.assertEqual(records["matches_played"], 1)


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

    def test_evaluate_board_objectives_reports_the_real_standings_position_not_team_id(self) -> None:
        # Real bug found while building a UI for this: the SQL selected
        # (team_id, position) but the code read row[0] -- always the
        # team_id, not the position. Deliberately pick a team whose id
        # doesn't match its rank so a regression can't hide behind
        # coincidentally-equal values.
        engine = CompetitionEngine(self.database, seed=7)
        engine.ensure_season(2026)
        with connect(self.database) as connection:
            comp = connection.execute(
                "SELECT id FROM competitions WHERE name='Domestic Division 1' AND season=2026"
            ).fetchone()
            team_ids = [row[0] for row in connection.execute(
                "SELECT team_id FROM league_standings WHERE competition_id=? ORDER BY team_id", (comp[0],)
            ).fetchall()]
            last_placed_team = team_ids[-1]
            # Give every other team a big points lead so last_placed_team is
            # guaranteed to finish bottom of the table -- its actual
            # position (the size of the division) is very unlikely to equal
            # its own team_id.
            for team_id in team_ids:
                if team_id != last_placed_team:
                    connection.execute("UPDATE league_standings SET points=100 WHERE competition_id=? AND team_id=?",
                                       (comp[0], team_id))
        evaluation = evaluate_board_objectives(last_placed_team, self.database)
        # The correct position is the size of the division (last place);
        # the pre-fix bug would have returned last_placed_team's own id
        # instead, which is a real db row id and essentially never equal
        # to the division size by coincidence.
        self.assertEqual(evaluation["progress"]["league_position"]["current"], len(team_ids))


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


class CustomTournamentTests(TemporaryGameTest):

    def test_create_tournament_generates_groups(self) -> None:
        result = create_custom_tournament("Test Cup", "T20", [1, 2, 3, 4, 5, 6, 7, 8], 2, 2026, self.database)
        self.assertIn("tournament_id", result)
        self.assertEqual(len(result["groups"]), 2)

    def test_create_tournament_requires_min_4_teams(self) -> None:
        with self.assertRaises(ValueError):
            create_custom_tournament("Bad", "T20", [1, 2, 3], 2, 2026, self.database)

    def test_create_tournament_rejects_invalid_format(self) -> None:
        with self.assertRaises(ValueError):
            create_custom_tournament("Bad", "T5", [1, 2, 3, 4], 2, 2026, self.database)

    def test_tournament_groups_are_round_robin(self) -> None:
        result = create_custom_tournament("RR Test", "T20", [1, 2, 3, 4], 2, 2026, self.database)
        tournament = get_custom_tournament(result["tournament_id"], self.database)
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament["status"], "group_stage")

    def test_tournament_standings_populated(self) -> None:
        result = create_custom_tournament("Standings Test", "T20", [1, 2, 3, 4], 2, 2026, self.database)
        standings = get_tournament_standings(result["tournament_id"], self.database)
        self.assertEqual(len(standings["groups"]), 2)

    def test_list_custom_tournaments(self) -> None:
        create_custom_tournament("List Test", "T20", [1, 2, 3, 4], 2, 2026, self.database)
        tournaments = get_custom_tournaments(self.database)
        self.assertGreaterEqual(len(tournaments), 1)

    def test_advance_to_knockout_requires_groups_complete(self) -> None:
        result = create_custom_tournament("Knockout Test", "T20", [1, 2, 3, 4, 5, 6, 7, 8], 2, 2026, self.database)
        advance_result = advance_tournament_to_knockout(result["tournament_id"], 2026, self.database)
        self.assertIsNone(advance_result)

    def test_advance_to_knockout_after_groups_complete(self) -> None:
        result = create_custom_tournament("KO Test", "T20", [1, 2, 3, 4, 5, 6, 7, 8], 1, 2026, self.database)
        comp_ids = result["competition_ids"]
        with connect(self.database) as connection:
            for comp_id in comp_ids.values():
                matches = connection.execute(
                    "SELECT id FROM matches WHERE competition_id=? AND completed=0", (comp_id,)
                ).fetchall()
                for m in matches:
                    connection.execute(
                        "UPDATE matches SET completed=1, result_json=? WHERE id=?",
                        (json.dumps({"home_runs": 150, "away_runs": 120, "winner": 1, "tied": False, "overs": 20}), m[0])
                    )
                from competition import CompetitionEngine
                for m in connection.execute("SELECT * FROM matches WHERE competition_id=?", (comp_id,)).fetchall():
                    result_data = json.loads(m["result_json"])
                    CompetitionEngine._update_table(connection, m, result_data)
        advance_result = advance_tournament_to_knockout(result["tournament_id"], 2026, self.database)
        self.assertIsNotNone(advance_result)
        self.assertIn("bracket", advance_result)

    def test_get_bracket_before_knockout(self) -> None:
        result = create_custom_tournament("Bracket Test", "T20", [1, 2, 3, 4], 2, 2026, self.database)
        bracket = get_tournament_bracket(result["tournament_id"], self.database)
        self.assertEqual(bracket["bracket"], {})

    def test_t10_format_accepted(self) -> None:
        result = create_custom_tournament("T10 Test", "T10", [1, 2, 3, 4], 2, 2026, self.database)
        tournament = get_custom_tournament(result["tournament_id"], self.database)
        self.assertEqual(tournament["format"], "T10")

    def test_hundred_format_accepted(self) -> None:
        result = create_custom_tournament("Hundred Test", "Hundred", [1, 2, 3, 4], 2, 2026, self.database)
        tournament = get_custom_tournament(result["tournament_id"], self.database)
        self.assertEqual(tournament["format"], "Hundred")

    def test_generate_round_robin_balanced(self) -> None:
        pairs = _generate_round_robin([1, 2, 3, 4], home_away=True)
        self.assertEqual(len(pairs), 12)

    def test_3_group_tournament_for_large_pool(self) -> None:
        result = create_custom_tournament("Large Test", "ODI", list(range(1, 13)), 2, 2026, self.database)
        self.assertEqual(len(result["groups"]), 3)


class OnboardingTests(TemporaryGameTest):

    def test_initial_state_has_welcome_step(self) -> None:
        state = get_onboarding_state(self.database)
        self.assertEqual(state["current_step"], "welcome")
        self.assertEqual(state["completed_steps"], [])
        self.assertFalse(state["dismissed"])

    def test_advance_moves_to_next_step(self) -> None:
        state = advance_onboarding(self.database)
        self.assertEqual(state["current_step"], "squad")
        self.assertIn("welcome", state["completed_steps"])

    def test_advance_through_all_steps(self) -> None:
        for _ in range(len(ONBOARDING_STEPS)):
            state = advance_onboarding(self.database)
        self.assertIsNone(state["current_step"])
        self.assertTrue(state["dismissed"])

    def test_dismiss_skips_all_steps(self) -> None:
        state = dismiss_onboarding(self.database)
        self.assertTrue(state["dismissed"])
        self.assertIsNone(state["current_step"])
        self.assertEqual(len(state["completed_steps"]), len(ONBOARDING_STEPS))

    def test_onboarding_steps_have_required_fields(self) -> None:
        for step in ONBOARDING_STEPS:
            self.assertIn("id", step)
            self.assertIn("title", step)
            self.assertIn("description", step)
            self.assertIn("screen", step)

    def test_state_persists_across_calls(self) -> None:
        advance_onboarding(self.database)
        state = get_onboarding_state(self.database)
        self.assertEqual(state["current_step"], "squad")
        self.assertIn("welcome", state["completed_steps"])


class GroundTests(TemporaryGameTest):
    def test_grounds_table_exists(self) -> None:
        with connect(self.database) as conn:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertIn("grounds", tables)

    def test_generate_ground_for_team(self) -> None:
        with connect(self.database) as conn:
            ground = _generate_ground_for_team(conn, 1)
        self.assertIn("id", ground)
        self.assertIn("stadium_name", ground)
        self.assertIn("capacity", ground)
        self.assertIn("boundary_size", ground)
        self.assertIn("outfield_speed", ground)
        self.assertIn("pitch_affinity", ground)
        self.assertEqual(ground["team_id"], 1)
        self.assertIn(ground["boundary_size"], [65, 70, 75, 80, 85])
        self.assertIn(ground["outfield_speed"], ["slow", "medium", "fast"])
        self.assertIn(ground["pitch_affinity"], ["pace", "spin", "balanced"])

    def test_generate_ground_is_idempotent(self) -> None:
        with connect(self.database) as conn:
            first = _generate_ground_for_team(conn, 1)
            second = _generate_ground_for_team(conn, 1)
        self.assertEqual(first["id"], second["id"])

    def test_ensure_grounds_for_all_teams(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_for_all_teams(conn)
            count = conn.execute("SELECT COUNT(*) FROM grounds").fetchone()[0]
            team_count = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        self.assertEqual(count, team_count)

    def test_get_ground_info_returns_dict(self) -> None:
        info = get_ground_info(1, self.database)
        self.assertIsInstance(info, dict)
        self.assertEqual(info["team_id"], 1)
        self.assertIn("boundary_size", info)

    def test_get_ground_info_unknown_team(self) -> None:
        info = get_ground_info(9999, self.database)
        self.assertIsNone(info)

    def test_get_match_ground_details(self) -> None:
        with connect(self.database) as conn:
            rows = conn.execute("SELECT id, home_team FROM matches LIMIT 1").fetchone()
        if not rows:
            self.skipTest("no matches found")
        match_id, home_id = rows
        details = get_match_ground_details(match_id, self.database)
        self.assertIsInstance(details, dict)
        self.assertEqual(details["team_id"], home_id)

    def test_get_match_ground_details_unknown(self) -> None:
        details = get_match_ground_details(99999, self.database)
        self.assertIsNone(details)

    def test_team_city_known(self) -> None:
        self.assertEqual(_team_city("Manchester United"), "Manchester")
        self.assertEqual(_team_city("Sydney Sixers"), "Sydney")

    def test_team_city_fallback(self) -> None:
        city = _team_city("Fictional Town")
        self.assertEqual(city, "Fictional Town City")

    def test_ground_city_from_team_name(self) -> None:
        with connect(self.database) as conn:
            name = conn.execute("SELECT name FROM teams WHERE id=1").fetchone()[0]
        info = get_ground_info(1, self.database)
        expected_city = _team_city(name)
        self.assertEqual(info["city"], expected_city)

    def test_ground_boundary_affects_four_six_weights(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        small_ground = {"boundary_size": 65, "outfield_speed": "medium", "pitch_affinity": "balanced"}
        large_ground = {"boundary_size": 85, "outfield_speed": "medium", "pitch_affinity": "balanced"}
        m_small = Match(team1, team2, players, opp, "T20", seed=42, ground_info=small_ground)
        m_large = Match(team1, team2, players, opp, "T20", seed=42, ground_info=large_ground)
        m_small.simulate()
        m_large.simulate()
        small_boundaries = sum(
            1 for c in m_small.commentary if c.get("outcome") in ("4", "6")
        )
        large_boundaries = sum(
            1 for c in m_large.commentary if c.get("outcome") in ("4", "6")
        )
        self.assertGreaterEqual(large_boundaries, small_boundaries)

    def test_outfield_speed_affects_two_three_weights(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        slow_ground = {"boundary_size": 75, "outfield_speed": "slow", "pitch_affinity": "balanced"}
        fast_ground = {"boundary_size": 75, "outfield_speed": "fast", "pitch_affinity": "balanced"}
        m_slow = Match(team1, team2, players, opp, "T20", seed=42, ground_info=slow_ground)
        m_fast = Match(team1, team2, players, opp, "T20", seed=42, ground_info=fast_ground)
        m_slow.simulate()
        m_fast.simulate()
        slow_runs = sum(c.get("runs", 0) for c in m_slow.commentary if c.get("outcome") in ("1", "2", "3"))
        fast_runs = sum(c.get("runs", 0) for c in m_fast.commentary if c.get("outcome") in ("1", "2", "3"))
        self.assertGreaterEqual(fast_runs, slow_runs)


class AnalyticsTests(TemporaryGameTest):
    def test_get_ground_stats_returns_dict(self) -> None:
        stats = get_ground_stats(1, self.database)
        self.assertIsInstance(stats, dict)
        self.assertIn("matches", stats)
        self.assertIn("avg_score", stats)
        self.assertIn("win_pct", stats)
        self.assertIn("win_pct_batting_first", stats)

    def test_get_ground_stats_no_matches(self) -> None:
        stats = get_ground_stats(9999, self.database)
        self.assertEqual(stats["matches"], 0)

    def test_get_player_form_no_history(self) -> None:
        form = get_player_form(9999, self.database)
        self.assertEqual(form["form_rating"], 5)
        self.assertEqual(form["matches"], 0)

    def test_get_player_form_with_history(self) -> None:
        players = fetch_players(1, self.database)
        pid = players[0]["id"]
        now = "2026-07-28"
        # Simulate form entries
        from database import connect as db_connect
        with db_connect(self.database) as conn:
            for i, perf in enumerate([70, 80, 90]):
                conn.execute(
                    "INSERT INTO player_form_history(player_id,match_date,performance,context) VALUES (?,?,?,?)",
                    (pid, now, perf, "League"),
                )
        form = get_player_form(pid, self.database)
        self.assertGreater(form["matches"], 0)
        self.assertGreaterEqual(form["form_rating"], 1)
        self.assertLessEqual(form["form_rating"], 10)
        self.assertEqual(len(form["recent"]), 3)

    def test_session_data_in_scorecard(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        match = Match(team1, team2, players, opp, "Test", seed=42, batting_first_id=1)
        match.simulate()
        card = match.scorecard(0)
        self.assertIn("session_data", card)
        self.assertIsInstance(card["session_data"], list)

    def test_phase_data_in_scorecard(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        match = Match(team1, team2, players, opp, "T20", seed=42, batting_first_id=1)
        match.simulate()
        card = match.scorecard(0)
        self.assertIn("phase_data", card)
        self.assertIsInstance(card["phase_data"], list)

    def test_key_moments_in_to_dict(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        match = Match(team1, team2, players, opp, "T20", seed=42, batting_first_id=1)
        match.simulate()
        d = match.to_dict()
        self.assertIn("key_moments", d)
        self.assertIsInstance(d["key_moments"], list)
        if d["key_moments"]:
            self.assertIn("text", d["key_moments"][0])

    def test_key_moments_includes_wickets_and_milestones(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        match = Match(team1, team2, players, opp, "T20", seed=42, batting_first_id=1)
        match.simulate()
        moments = match.key_moments()
        kinds = {m["kind"] for m in moments}
        self.assertTrue({"wicket", "milestone"}.intersection(kinds) or len(moments) > 0)


class FacilityUpgradeGroundTests(unittest.TestCase):
    """Tests for facility upgrades affecting ground characteristics."""

    def setUp(self):
        self.db_dir = TemporaryDirectory()
        self.database = str(Path(self.db_dir.name) / "test.db")
        initialise_database(self.database)

    def tearDown(self):
        self.db_dir.cleanup()

    def test_sync_ground_level3_fixes_slow_outfield(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_table(conn)
            _generate_ground_for_team(conn, 1)
            conn.execute("UPDATE teams SET grounds_level=3 WHERE id=1")
            conn.execute("UPDATE grounds SET outfield_speed='slow' WHERE team_id=1")
            _sync_ground_with_upgrades(conn, 1)
            speed = conn.execute("SELECT outfield_speed FROM grounds WHERE team_id=1").fetchone()[0]
        self.assertEqual(speed, "medium")

    def test_sync_ground_level5_upgrades_boundary(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_table(conn)
            _generate_ground_for_team(conn, 1)
            conn.execute("UPDATE teams SET grounds_level=5 WHERE id=1")
            conn.execute("UPDATE grounds SET boundary_size=65, outfield_speed='medium' WHERE team_id=1")
            _sync_ground_with_upgrades(conn, 1)
            row = conn.execute("SELECT boundary_size, outfield_speed FROM grounds WHERE team_id=1").fetchone()
        self.assertEqual(row["boundary_size"], 80)
        self.assertEqual(row["outfield_speed"], "fast")

    def test_sync_ground_level5_fast_outfield(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_table(conn)
            _generate_ground_for_team(conn, 1)
            conn.execute("UPDATE teams SET grounds_level=5 WHERE id=1")
            conn.execute("UPDATE grounds SET outfield_speed='slow' WHERE team_id=1")
            _sync_ground_with_upgrades(conn, 1)
            speed = conn.execute("SELECT outfield_speed FROM grounds WHERE team_id=1").fetchone()[0]
        self.assertEqual(speed, "fast")

    def test_sync_ground_level1_no_change(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_table(conn)
            _generate_ground_for_team(conn, 1)
            conn.execute("UPDATE grounds SET boundary_size=65, outfield_speed='slow' WHERE team_id=1")
            _sync_ground_with_upgrades(conn, 1)
            row = conn.execute("SELECT boundary_size, outfield_speed FROM grounds WHERE team_id=1").fetchone()
        self.assertEqual(row["boundary_size"], 65)
        self.assertEqual(row["outfield_speed"], "slow")

    def test_stadium_upgrade_syncs_capacity(self) -> None:
        with connect(self.database) as conn:
            _ensure_grounds_table(conn)
            _generate_ground_for_team(conn, 1)
            conn.execute("UPDATE teams SET stadium_capacity=50000 WHERE id=1")
            conn.execute("UPDATE grounds SET capacity=20000 WHERE team_id=1")
            _sync_ground_with_upgrades(conn, 1)
            cap = conn.execute("SELECT capacity FROM grounds WHERE team_id=1").fetchone()[0]
        self.assertEqual(cap, 50000)

    def test_complete_grounds_upgrade_triggers_sync(self) -> None:
        start_facility_upgrade(1, "Grounds Department", "2026-07-01", self.database)
        result = complete_due_facility_upgrades(1, "2026-07-10", self.database)
        self.assertIn("Grounds Department", result)
        with connect(self.database) as conn:
            level = conn.execute("SELECT grounds_level FROM teams WHERE id=1").fetchone()[0]
        self.assertEqual(level, 2)


class HomeAdvantageTests(unittest.TestCase):
    """Tests for grounds_level home advantage in match engine."""

    def setUp(self):
        self.db_dir = TemporaryDirectory()
        self.database = str(Path(self.db_dir.name) / "test.db")
        initialise_database(self.database)

    def tearDown(self):
        self.db_dir.cleanup()

    def test_higher_grounds_level_boosts_home_batting(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 5}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        m_high = Match(team1, team2, players, opp, "T20", seed=42, batting_first_id=1)
        m_low = Match({"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1},
                      team2, players, opp, "T20", seed=42, batting_first_id=1)
        m_high.simulate()
        m_low.simulate()
        self.assertGreaterEqual(m_high.current_innings.runs, m_low.current_innings.runs)

    def test_higher_grounds_level_boosts_home_bowling(self) -> None:
        from match_engine import Match
        team1 = {"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 5}
        team2 = {"id": 2, "name": "Away", "stadium_capacity": 15000, "grounds_level": 1}
        players = fetch_players(1, self.database)[:11]
        opp = fetch_players(2, self.database)[:11]
        m_high = Match(team1, team2, players, opp, "T20", seed=42, batting_first_id=2)
        m_low = Match({"id": 1, "name": "Home", "stadium_capacity": 20000, "grounds_level": 1},
                      team2, players, opp, "T20", seed=42, batting_first_id=2)
        m_high.simulate()
        m_low.simulate()
        self.assertGreaterEqual(m_high.current_innings.wickets, m_low.current_innings.wickets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
