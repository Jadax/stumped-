"""Career-depth model and screen tests (v0.13.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


class CareerModelTests(unittest.TestCase):
    def test_board_confidence_scales_with_position_and_cash(self) -> None:
        from src.models.career import board_confidence
        ahead = board_confidence(1, 12, 6, 1_000_000)
        behind = board_confidence(11, 12, 6, -50_000)
        self.assertGreater(ahead["score"], behind["score"])
        self.assertEqual(ahead["label"], "Delighted")
        self.assertEqual(behind["label"], "Ultimatum")

    def test_manager_reputation_rewards_wins_and_trophies(self) -> None:
        from src.models.career import manager_reputation
        rookie = manager_reputation(0, 0)
        winner = manager_reputation(40, 30, trophies=2)
        self.assertLess(rookie["score"], winner["score"])
        self.assertEqual(rookie["label"], "Unproven")

    def test_world_ratings_rank_by_points_within_bounds(self) -> None:
        from src.models.career import world_ratings
        players = [{"name": f"P{i}", "role": "Batter", "nationality": "England", "team_name": "A",
                    "form": 50 + i, "batting": {"technique": 40 + i * 5},
                    "mental": {"consistency": 50}} for i in range(6)]
        rows = world_ratings(players, "batting", 5)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["name"], "P5")
        points = [row["points"] for row in rows]
        self.assertEqual(points, sorted(points, reverse=True))
        self.assertTrue(all(0 <= p <= 1000 for p in points))

    def test_season_awards_cover_all_four_titles(self) -> None:
        from src.models.career import season_awards
        players = [{"name": "Alpha", "role": "Batter", "age": 20, "overall": 70, "potential": 88,
                    "form": 60, "batting": {"technique": 82}, "bowling": {"pace": 30},
                    "mental": {"consistency": 65}},
                   {"name": "Beta", "role": "Bowler", "age": 27, "overall": 75, "form": 55,
                    "batting": {"technique": 35}, "bowling": {"pace": 85},
                    "mental": {"consistency": 70}}]
        awards = season_awards(players)
        self.assertEqual(set(awards), {"Batter of the Season", "Bowler of the Season",
                                       "Young Player of the Season", "Player of the Season"})


class HonoursTests(unittest.TestCase):
    def setUp(self) -> None:
        from database import initialise_database
        self.database = os.path.join(tempfile.mkdtemp(), "honours.db")
        initialise_database(self.database)

    def test_honour_round_trip_and_lazy_migration(self) -> None:
        from database import fetch_honours, record_honour
        self.assertEqual(fetch_honours(1, self.database), [])
        record_honour(1, "Division 1 Champions", 2026, "2026-09-30", self.database)
        record_honour(1, "Knockout Cup Winners", 2027, "2027-09-30", self.database)
        honours = fetch_honours(1, self.database)
        self.assertEqual([h["title"] for h in honours],
                         ["Knockout Cup Winners", "Division 1 Champions"])

    def test_season_end_awards_honours_and_briefs_the_user(self) -> None:
        from competition import CompetitionEngine
        from database import fetch_honours, fetch_inbox_messages, fetch_teams
        teams = [t["id"] for t in fetch_teams(self.database)]
        user = teams[0]
        divisions = {1: teams[:12], 2: teams[12:24]}
        engine = CompetitionEngine(self.database)
        engine._award_season_honours(2026, divisions, None, user)
        self.assertEqual([h["title"] for h in fetch_honours(user, self.database)],
                         ["Division 1 Champions"])
        titles = [m["title"] for m in fetch_inbox_messages(10, self.database)]
        self.assertTrue(any("Silverware" in t for t in titles))
        self.assertTrue(any("Season Awards" in t for t in titles))
        self.assertTrue(any("Board season review" in t for t in titles))


class ChanceLogTests(unittest.TestCase):
    def test_engine_exposes_real_fielding_chances(self) -> None:
        from database import initialise_database, fetch_teams, fetch_players
        from match_engine import Match
        db = os.path.join(tempfile.mkdtemp(), "chances.db")
        initialise_database(db)
        teams = fetch_teams(db)
        home, away = dict(teams[0]), dict(teams[1])
        match = Match(home, away, fetch_players(home["id"], db)[:11],
                      fetch_players(away["id"], db)[:11], "T20")
        for _ in range(400):
            if match.completed: break
            event = match.ball_outcome()
            self.assertIn("chance", event)
            match.event_pool.release(event)
        self.assertIsInstance(match.chance_log, dict)
        for log in match.chance_log.values():
            self.assertEqual(set(log), {"dropped", "missed_stumping", "missed_runout"})


class CareerScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))
        from database import initialise_database, fetch_teams, fetch_players
        cls.database = os.path.join(tempfile.mkdtemp(), "career.db")
        initialise_database(cls.database)
        team = dict(fetch_teams(cls.database)[0])
        cls.context = {"database_path": cls.database, "team": team,
                       "players": fetch_players(team["id"], cls.database)}

    def test_every_tab_and_discipline_renders(self) -> None:
        from ui.career import CareerScreen
        screen = CareerScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                              1.0, self.context)
        for tab in CareerScreen.TABS:
            screen.active_tab = tab
            screen.draw(self.surface)
        screen.active_tab = "World Ratings"
        for discipline in CareerScreen.DISCIPLINES:
            screen.discipline = discipline
            screen.draw(self.surface)
        self.assertEqual(len(screen.awards), 4)

    def test_career_screen_is_registered_in_navigation(self) -> None:
        from main import NAV_SCREEN_NAMES, SCREEN_CLASSES
        self.assertIn("Career", SCREEN_CLASSES)
        self.assertIn("Career", NAV_SCREEN_NAMES)


if __name__ == "__main__":
    unittest.main()
