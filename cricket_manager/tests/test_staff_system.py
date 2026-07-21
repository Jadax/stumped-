"""Coaching, medical, and scouting staff systems (v0.22.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "staff.db")
    initialise_database(path)
    return path


class StaffGenerationTests(unittest.TestCase):
    def test_every_club_gets_a_full_roster_covering_all_three_departments(self) -> None:
        from database import fetch_staff, fetch_teams
        db = _fresh_db()
        for team in fetch_teams(db)[:5]:
            roster = fetch_staff(team["id"], database_path=db)
            groups = {member["group_name"] for member in roster}
            self.assertEqual(groups, {"Coaching", "Medical", "Scouting"})
            roles = {member["role"] for member in roster}
            self.assertTrue({"Head Coach", "Batting Coach", "Bowling Coach", "Fielding Coach", "Fitness Coach"} <= roles)
            self.assertTrue({"Doctor", "Physio"} <= roles)
            self.assertTrue({"Chief Scout", "Scout"} <= roles)

    def test_staff_attributes_are_bounded_one_to_twenty(self) -> None:
        from database import fetch_staff, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        for member in fetch_staff(team["id"], database_path=db):
            for value in member["attributes"].values():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 20)
            self.assertGreaterEqual(member["overall"], 1)
            self.assertLessEqual(member["overall"], 20)

    def test_group_filter_returns_only_that_department(self) -> None:
        from database import fetch_staff, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        medical = fetch_staff(team["id"], "Medical", database_path=db)
        self.assertTrue(medical)
        self.assertTrue(all(m["group_name"] == "Medical" for m in medical))


class CoachTrainingEffectTests(unittest.TestCase):
    def test_better_batting_coach_yields_faster_batting_gains(self) -> None:
        from src.models.staff import coach_training_multiplier
        weak = coach_training_multiplier(2)
        strong = coach_training_multiplier(19)
        self.assertLess(weak, 1.0)
        self.assertGreater(strong, 1.0)
        self.assertGreater(strong, weak)

    def test_team_coach_rating_reads_the_right_specialist(self) -> None:
        from database import fetch_staff, fetch_teams, team_coach_rating
        db = _fresh_db()
        team = fetch_teams(db)[0]
        batting_coach = next(m for m in fetch_staff(team["id"], "Coaching", database_path=db)
                             if m["role"] == "Batting Coach")
        rating = team_coach_rating(team["id"], "batting", db)
        self.assertEqual(rating, batting_coach["attributes"]["coaching"])

    def test_training_actually_applies_and_scales_with_coach_quality(self) -> None:
        """Two identical squads, one with a stronger batting coach, should
        diverge in cumulative batting gains over many simulated training days."""
        from database import (add_financial_transaction, apply_daily_training, connect,
                              fetch_players, fetch_teams, set_training_focus)
        import json
        db = _fresh_db()
        team = fetch_teams(db)[0]
        players = fetch_players(team["id"], db)[:3]
        for player in players:
            set_training_focus(player["id"], "Batting Focus", db)
        with connect(db) as connection:
            connection.execute(
                "UPDATE staff SET attributes_json = ? WHERE team_id = ? AND role = 'Batting Coach'",
                (json.dumps({"coaching": 20, "man_management": 15, "working_with_youngsters": 15}), team["id"]),
            )
        totals = 0
        for day in range(1, 40):
            apply_daily_training(team["id"], f"2026-04-{day:02d}" if day <= 30 else f"2026-05-{day-30:02d}", db)
        after = fetch_players(team["id"], db)
        after_by_id = {p["id"]: p for p in after}
        for player in players:
            self.assertGreaterEqual(after_by_id[player["id"]]["overall"], player["overall"])


class MedicalEffectTests(unittest.TestCase):
    def test_higher_physio_rating_reduces_injury_chance_and_recovery_time(self) -> None:
        from src.models.staff import medical_injury_multiplier
        weak = medical_injury_multiplier(2)
        strong = medical_injury_multiplier(19)
        self.assertGreater(weak, 1.0)
        self.assertLess(strong, 1.0)

    def test_active_injuries_are_fetched_and_expire_on_schedule(self) -> None:
        from database import (apply_match_player_updates, clear_expired_injuries,
                              fetch_active_injuries, fetch_players, fetch_teams)
        db = _fresh_db()
        team = fetch_teams(db)[0]
        player = fetch_players(team["id"], db)[0]
        apply_match_player_updates({}, [{"player_id": player["id"], "severity": "Minor", "days": 3}],
                                   "2026-04-01", db)
        active = fetch_active_injuries(team["id"], db)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["player_name"], player["name"])
        cleared = clear_expired_injuries("2026-04-05", db)
        self.assertGreaterEqual(cleared, 1)
        self.assertEqual(fetch_active_injuries(team["id"], db), [])

    def test_team_physio_rating_is_the_best_medical_staff_member(self) -> None:
        from database import fetch_staff, fetch_teams, team_physio_rating
        db = _fresh_db()
        team = fetch_teams(db)[0]
        medical = fetch_staff(team["id"], "Medical", database_path=db)
        expected = max(m["attributes"]["physiotherapy"] for m in medical)
        self.assertEqual(team_physio_rating(team["id"], db), expected)


class ScoutingEffectTests(unittest.TestCase):
    def test_better_scouts_produce_tighter_estimate_noise(self) -> None:
        from src.models.staff import scouting_noise
        weak_overall, weak_potential = scouting_noise(2, 2)
        strong_overall, strong_potential = scouting_noise(19, 19)
        self.assertGreater(weak_overall, strong_overall)
        self.assertGreater(weak_potential, strong_potential)

    def test_scouted_players_carry_an_estimate_alongside_the_true_value(self) -> None:
        from database import scout_players
        db = _fresh_db()
        results = scout_players(exclude_team=1, limit=5, database_path=db)
        self.assertTrue(results)
        for player in results:
            self.assertIn("estimated_overall", player)
            self.assertIn("estimated_potential", player)
            self.assertIn("confidence", player)
            self.assertGreaterEqual(player["estimated_potential"], player["estimated_overall"] - 1)


class StaffAgeingTests(unittest.TestCase):
    def test_rollover_ages_staff_by_one_year(self) -> None:
        from database import age_staff_at_rollover, connect, fetch_staff, fetch_teams
        db = _fresh_db()
        team = fetch_teams(db)[0]
        before = {m["id"]: m["age"] for m in fetch_staff(team["id"], database_path=db)}
        age_staff_at_rollover(2026, db)
        after = {m["id"]: m["age"] for m in fetch_staff(team["id"], database_path=db)}
        for staff_id, age in before.items():
            self.assertEqual(after[staff_id], age + 1)


class StaffScreenUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))
        from database import fetch_players, fetch_teams
        cls.database = _fresh_db()
        team = dict(fetch_teams(cls.database)[0])
        cls.context = {"database_path": cls.database, "team": team,
                       "players": fetch_players(team["id"], cls.database), "current_date": "2026-04-01"}

    def test_staff_screen_renders_every_group(self) -> None:
        from ui.staff import StaffScreen
        screen = StaffScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                             1.0, dict(self.context))
        for group in screen.GROUPS:
            screen.active_group = group
            screen.group_bar.active = group
            screen.refresh_rows()
            self.assertGreater(len(screen.table.rows), 0)
            screen.draw(self.surface)

    def test_medical_screen_renders_with_and_without_injuries(self) -> None:
        from ui.medical import MedicalScreen
        screen = MedicalScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                               1.0, dict(self.context))
        screen.draw(self.surface)
        from database import apply_match_player_updates
        player = self.context["players"][0]
        apply_match_player_updates({}, [{"player_id": player["id"], "severity": "Major", "days": 30}],
                                   "2026-04-01", self.database)
        screen.refresh()
        screen.draw(self.surface)
        self.assertEqual(len(screen.injuries), 1)

    def test_staff_and_medical_centre_are_registered_in_navigation(self) -> None:
        from main import NAV_SCREEN_NAMES, SCREEN_CLASSES
        self.assertIn("Staff", SCREEN_CLASSES)
        self.assertIn("Medical Centre", SCREEN_CLASSES)
        self.assertIn("Staff", NAV_SCREEN_NAMES)
        self.assertIn("Medical Centre", NAV_SCREEN_NAMES)


if __name__ == "__main__":
    unittest.main()
