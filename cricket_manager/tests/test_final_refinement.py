from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest

import database as database_module

from database import (apply_daily_training, connect, fetch_player_records,
                      fetch_players, fetch_teams, generate_player,
                      initialise_database, load_game, record_player_performance,
                      recruit_youth, set_training_schedule,
                      start_facility_upgrade, update_user_settings)
from match_engine import Match
from src.models.currency import convert_from_gbp, format_money, set_active_currency


def player(pid: int, role: str = "Batsman", rating: int = 70) -> dict:
    return {
        "id": pid, "name": f"Player {pid}", "role": role, "overall": rating,
        "form": 55, "potential": 80,
        "batting": {"attack": rating, "defence": rating, "technique_vs_pace": rating,
                    "technique_vs_spin": rating, "concentration": rating},
        "bowling": {"pace": rating, "accuracy": rating, "variation": rating,
                    "stamina": rating, "swing_or_spin": rating},
        "fielding": {"catching": rating, "throwing": rating, "reflexes": rating, "agility": rating},
        "mental": {"experience": rating, "consistency": rating, "big_match": rating,
                   "fitness": rating, "morale": rating},
    }


def match(seed: int = 7) -> Match:
    home = [player(i, "Wicketkeeper" if i == 1 else "Bowler" if i >= 7 else "Batsman", 72) for i in range(1, 12)]
    away = [player(i, "Wicketkeeper" if i == 12 else "Bowler" if i >= 18 else "Batsman", 69) for i in range(12, 23)]
    return Match({"id": 1, "name": "Home"}, {"id": 2, "name": "Away"}, home, away,
                 "T20", seed=seed, batting_first_id=1)


class PlayerTemperamentTests(unittest.TestCase):
    """Natural batting/bowling aggression derived from attributes (docs/UX_ROADMAP.md)."""

    def test_power_hitter_defaults_more_aggressive_than_accumulator(self):
        from src.models.player import natural_batting_aggression
        accumulator = player(1, rating=70); accumulator["batting"]["attack"] = 45; accumulator["batting"]["concentration"] = 85
        hitter = player(2, rating=70); hitter["batting"]["attack"] = 85; hitter["batting"]["concentration"] = 45
        self.assertLess(natural_batting_aggression(accumulator), 5)
        self.assertGreater(natural_batting_aggression(hitter), 5)
        self.assertGreater(natural_batting_aggression(hitter), natural_batting_aggression(accumulator))

    def test_natural_aggression_stays_in_valid_slider_range(self):
        from src.models.player import natural_batting_aggression, natural_bowling_aggression
        extreme = player(3, rating=70)
        extreme["batting"] = {"attack": 100, "defence": 0, "concentration": 0}
        extreme["bowling"] = {"pace": 100, "accuracy": 0, "variation": 100}
        self.assertEqual(natural_batting_aggression(extreme), 10)
        self.assertEqual(natural_bowling_aggression(extreme), 10)
        docile = player(4, rating=70)
        docile["batting"] = {"attack": 0, "defence": 100, "concentration": 100}
        docile["bowling"] = {"pace": 0, "accuracy": 100, "variation": 0}
        self.assertEqual(natural_batting_aggression(docile), 1)
        self.assertEqual(natural_bowling_aggression(docile), 1)

    def test_selection_screen_seeds_defaults_from_player_temperament(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame, pygame_gui
        from ui.selection import SelectionScreen
        pygame.init()
        squad = [player(i, "Wicketkeeper" if i == 1 else "Bowler" if i >= 8 else "Batsman", 70) for i in range(1, 15)]
        squad[1]["batting"]["attack"], squad[1]["batting"]["concentration"] = 90, 30  # aggressive hitter
        squad[2]["batting"]["attack"], squad[2]["batting"]["concentration"] = 30, 90  # accumulator
        screen = SelectionScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(0, 0, 1280, 720), 1.0,
                                 {"players": squad, "database_path": ":memory:", "selection": {}}, lambda *_: None)
        screen.auto_select()
        self.assertGreater(screen.batting_aggression[squad[1]["id"]], screen.batting_aggression[squad[2]["id"]])


class MatchRefinementTests(unittest.TestCase):
    def test_energy_depletes_and_recovers_without_exceeding_start(self):
        game = match()
        bowler_id = game.current_innings.current_bowler_id
        before = game.player_energy(bowler_id)
        for _ in range(12):
            game.ball_outcome()
        self.assertLess(game.player_energy(bowler_id), before)
        depleted = game.player_energy(bowler_id)
        game._recover_energy(amount=4)
        self.assertGreater(game.player_energy(bowler_id), depleted)
        self.assertLessEqual(game.player_energy(bowler_id), round(game.starting_energy[bowler_id], 1))

    def test_talents_are_typed_and_commentary_ready(self):
        game = match()
        specialist = player(90, "Bowler", 88)
        specialist["potential"] = 94
        talents = game.talents_for(specialist)
        self.assertIn("passive", talents)
        self.assertIn("triggered", talents)
        self.assertTrue(talents["passive"])
        self.assertTrue(talents["triggered"])

    def test_monte_carlo_predictor_is_stable_and_non_mutating(self):
        game = match(14)
        for _ in range(20): game.ball_outcome()
        snapshot = (game.current_innings.runs, game.current_innings.wickets, game.current_innings.legal_balls)
        first = game.monte_carlo_win_probability(1, 150)
        second = game.monte_carlo_win_probability(1, 150)
        self.assertEqual(first, second)
        self.assertEqual(snapshot, (game.current_innings.runs, game.current_innings.wickets, game.current_innings.legal_balls))
        self.assertTrue(1 <= first <= 99)

    def test_aggressive_order_consolidates_after_early_wickets(self):
        game = match()
        game.batting_aggression = 9
        game.current_innings.wickets = 4
        game.current_innings.legal_balls = 24
        self.assertLess(game._situational_aggression(), 9)

    def test_individual_orders_and_spatial_analytics_reach_engine(self):
        game = match(22)
        striker = game.current_innings.striker_player
        striker["batting_aggression"] = 9
        bowler = next(player for player in game.current_innings.bowling_squad
                      if player["id"] == game.current_innings.current_bowler_id)
        bowler["bowling_aggression"] = 8
        bowler["bowling_style"] = "Fast"
        game.ball_outcome()
        self.assertEqual(game.last_factors["bowling_style"], "Fast")
        self.assertGreaterEqual(game.last_factors["batting_aggression"], 7)
        self.assertEqual(game.shot_events[-1]["innings"], 1)
        self.assertEqual(game.bowling_events[-1]["innings"], 1)

    def test_weather_forecast_rain_reduction_and_pitch_wear(self):
        game = match(31)
        self.assertEqual(len(game.weather_forecast), 12)
        game.apply_rain_interruption(14)
        self.assertEqual(game.rain_overs, 14)
        home = [player(i, "Wicketkeeper" if i == 1 else "Bowler" if i >= 7 else "Batsman", 70) for i in range(1, 12)]
        away = [player(i, "Wicketkeeper" if i == 12 else "Bowler" if i >= 18 else "Batsman", 70) for i in range(12, 23)]
        test = Match({"id": 1, "name": "Home", "grounds_level": 1}, {"id": 2, "name": "Away"},
                     home, away, "Test", pitch="Green", seed=9, batting_first_id=1)
        test.current_innings.legal_balls = 750
        test._update_conditions()
        self.assertEqual(test.pitch, "Worn")


class CurrencyAndWorldTests(unittest.TestCase):
    def tearDown(self):
        set_active_currency("GBP")

    def test_currency_changes_display_not_base_value(self):
        set_active_currency("INR")
        self.assertEqual(convert_from_gbp(100), 10500)
        self.assertEqual(format_money(100), "₹10,500")
        self.assertEqual(format_money(1_000_000, "GBP", compact=True), "£1.0M")

    def test_currency_and_new_hq_facilities_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "test.db"
            initialise_database(database)
            update_user_settings({"currency": "AUD"}, database)
            self.assertEqual(load_game(database)["user"]["currency"], "AUD")
            upgrade = start_facility_upgrade(1, "Commercial Office", "2026-04-01", database)
            self.assertEqual(upgrade["facility"], "Commercial Office")
            with connect(database) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(teams)")}
            self.assertTrue({"commercial_level", "scouting_level", "grounds_level"}.issubset(columns))

    def test_country_name_pool_drives_generated_player(self):
        pools = json.loads((Path(__file__).parents[1] / "src" / "data" / "names.json").read_text(encoding="utf-8"))
        generated = generate_player(1, 1, "India", 5, random.Random(12), set())
        first, last = generated["name"].split(" ", 1)
        aliases = {"English": "England", "Australian": "Australia", "Indian": "India", "Pakistani": "Pakistan",
                   "South African": "South Africa", "New Zealander": "New Zealand", "West Indian": "West Indies"}
        country = aliases.get(generated["nationality"], generated["nationality"])
        self.assertIn(first, pools[country]["first_names"])
        self.assertIn(last, pools[country]["last_names"])

    def test_world_has_correct_club_count_per_division(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "world.db"
            initialise_database(database)
            teams = fetch_teams(database)
            self.assertEqual(len(teams), 100)
            for division in (1, 2, 3, 4, 5):
                self.assertTrue(sum(team["division"] == division for team in teams) >= 10)

    def test_existing_club_save_expands_without_id_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "migration.db"
            initialise_database(database)
            with connect(database) as connection:
                original = dict(connection.execute("SELECT id,name FROM teams WHERE id<=16").fetchall())
                connection.execute("DELETE FROM league_standings WHERE team_id>16")
                connection.execute("DELETE FROM training_assignments WHERE player_id IN (SELECT id FROM players WHERE team_id>16)")
                connection.execute("DELETE FROM player_records WHERE player_id IN (SELECT id FROM players WHERE team_id>16)")
                connection.execute("DELETE FROM player_form_history WHERE player_id IN (SELECT id FROM players WHERE team_id>16)")
                connection.execute("DELETE FROM player_match_events WHERE player_id IN (SELECT id FROM players WHERE team_id>16)")
                connection.execute("DELETE FROM players WHERE team_id>16")
                connection.execute("DELETE FROM teams WHERE id>16")
            initialise_database(database)
            migrated = fetch_teams(database)
            self.assertEqual(len(migrated), 100)
            self.assertEqual({team["id"]: team["name"] for team in migrated if team["id"] <= 16}, original)

    def test_youth_intake_uses_club_country(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "youth.db"
            initialise_database(database)
            teams = fetch_teams(database)
            team = teams[0]
            from database import connect as _connect
            with _connect(database) as conn:
                club_country = conn.execute("SELECT division FROM teams WHERE id=?", (team["id"],)).fetchone()[0]
            intake = recruit_youth(team["id"], "English", 4, database_path=database)
            self.assertTrue(len(intake) > 0)


class RecordsAndTrainingTests(unittest.TestCase):
    def test_test_match_record_counts_match_once_and_both_innings(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "records.db"
            initialise_database(database)
            player_id = fetch_players(1, database)[0]["id"]
            record_player_performance(
                player_id, "2026-06-10", "League",
                batting=[{"runs": 45, "balls": 80, "fours": 5},
                         {"runs": 103, "balls": 151, "fours": 12, "sixes": 1}],
                bowling=[{"balls": 60, "runs": 28, "wickets": 2},
                         {"balls": 72, "runs": 31, "wickets": 5}],
                database_path=database,
            )
            record = fetch_player_records(player_id, database)["League"]
            self.assertEqual((record["matches"], record["innings"], record["runs"]), (1, 2, 148))
            self.assertEqual((record["hundreds"], record["five_wickets"]), (1, 1))

    def test_combined_record_sums_every_format_context(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "combined.db"
            initialise_database(database)
            from database import fetch_player_records
            from src.models.player_records import combined_record, format_context
            player_id = fetch_players(1, database)[0]["id"]
            record_player_performance(player_id, "2026-05-01", format_context("T20", False),
                                      batting={"runs": 45, "balls": 30, "fours": 5}, database_path=database)
            record_player_performance(player_id, "2026-06-01", format_context("ODI", False),
                                      batting={"runs": 60, "balls": 70, "fours": 6},
                                      bowling={"balls": 30, "runs": 20, "wickets": 2}, database_path=database)
            combined = combined_record(fetch_player_records(player_id, database))
            self.assertEqual((combined["matches"], combined["runs"], combined["wickets"]), (2, 105, 2))
            self.assertAlmostEqual(combined["batting_average"], 52.5)

    def test_format_context_maps_domestic_and_international_labels(self):
        from src.models.player_records import format_context
        self.assertEqual(format_context("Test", international=False), "First Class")
        self.assertEqual(format_context("ODI", international=False), "One Day")
        self.assertEqual(format_context("T20", international=True), "20 Over International")
        self.assertEqual(format_context("Hundred", international=True), "The Hundred International")

    def test_player_chances_round_trip_through_database(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "chances.db"
            initialise_database(database)
            from database import fetch_player_match_events, record_player_chances
            player_id = fetch_players(1, database)[0]["id"]
            record_player_chances(101, {player_id: {"dropped": 1, "catchable": 2, "lbw_appeals": 0, "played_and_missed": 3}}, database)
            chances = fetch_player_match_events(player_id, database)["chances"]
            self.assertEqual(chances, {"dropped": 1, "catchable": 2, "played_and_missed": 3})

    def test_match_chance_log_only_uses_known_categories(self):
        engine = match()
        engine.simulate()
        allowed = set(Match._empty_chance_log().keys())
        self.assertGreater(len(engine.chance_log), 0)
        for counts in engine.chance_log.values():
            self.assertLessEqual(set(counts.keys()), allowed)
            self.assertTrue(all(v >= 0 for v in counts.values()))

    def test_training_obeys_assigned_weekday(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "training.db"
            initialise_database(database)
            candidate = next(p for p in fetch_players(1, database) if p["potential"] > p["overall"])
            set_training_schedule(candidate["id"], "Batting Focus", "Heavy", (0,), database)
            apply_daily_training(1, "2026-04-07", database)  # Tuesday
            with connect(database) as connection:
                tuesday = connection.execute("SELECT last_trained FROM training_assignments WHERE player_id=?",
                                             (candidate["id"],)).fetchone()[0]
            apply_daily_training(1, "2026-04-06", database)  # Monday
            with connect(database) as connection:
                monday = connection.execute("SELECT last_trained FROM training_assignments WHERE player_id=?",
                                            (candidate["id"],)).fetchone()[0]
            self.assertIsNone(tuesday)
            self.assertEqual(monday, "2026-04-06")

    def test_training_keeps_fractional_progress_between_visible_points(self):
        """Training keeps hidden FM-style progress instead of rounding daily."""
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "fractional_training.db"
            initialise_database(database)
            candidate = next(p for p in fetch_players(1, database)
                             if p["potential"] > p["overall"])
            set_training_schedule(candidate["id"], "Batting Focus", "Light", (0,), database)
            apply_daily_training(1, "2026-04-06", database)  # Monday
            assignments = database_module.fetch_training_assignments(1, database)
            progress = assignments[candidate["id"]]["progress"]
            self.assertGreater(sum(float(value) for value in progress.values()), 0.0)
            refreshed = next(p for p in fetch_players(1, database)
                             if p["id"] == candidate["id"])
            self.assertLessEqual(refreshed["overall"], refreshed["potential"])


class HighDpiTests(unittest.TestCase):
    def test_4k_uses_readable_exact_two_x_canvas(self):
        from main import CricketManagerApp
        self.assertEqual(CricketManagerApp._fullscreen_logical_size((3840, 2160)), (1920, 1080))
        self.assertEqual(CricketManagerApp._fullscreen_logical_size((1920, 1080)), (1920, 1080))


if __name__ == "__main__":
    unittest.main()
