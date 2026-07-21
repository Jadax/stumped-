"""Recruitment Hub screen — tiled front page over existing data (v0.26.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


def _context() -> dict:
    from database import initialise_database, fetch_teams, fetch_players
    db = os.path.join(tempfile.mkdtemp(), "recruitment.db")
    initialise_database(db)
    team = dict(fetch_teams(db)[0])
    return {"database_path": db, "team": team, "players": fetch_players(team["id"], db)}


class RecruitmentHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def test_registered_in_navigation(self) -> None:
        from main import NAV_SCREEN_NAMES, SCREEN_CLASSES, NAV_GROUPS
        self.assertIn("Recruitment", SCREEN_CLASSES)
        self.assertIn("Recruitment", NAV_SCREEN_NAMES)
        self.assertTrue(any("Recruitment" in names for _, names in NAV_GROUPS))

    def test_renders_with_a_real_squad(self) -> None:
        from ui.recruitment import RecruitmentHubScreen
        screen = RecruitmentHubScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                                      1.0, _context())
        screen.draw(self.surface)

    def test_role_gaps_flag_understrength_roles(self) -> None:
        from ui.recruitment import RecruitmentHubScreen
        ctx = _context()
        ctx["players"] = [dict(p, role="Wicketkeeper") for p in ctx["players"][:1]]
        screen = RecruitmentHubScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660), 1.0, ctx)
        gaps = dict(screen._role_gaps())
        self.assertIn("Bowler", gaps)
        self.assertEqual(gaps["Wicketkeeper"], 1)

    def test_quick_action_buttons_navigate(self) -> None:
        from ui.recruitment import RecruitmentHubScreen
        destinations = []
        screen = RecruitmentHubScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                                      1.0, _context(), destinations.append)
        button, destination = screen.buttons[0]
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": button.rect.center, "button": 1})
        screen.process_event(event)
        self.assertEqual(destinations, [destination])


if __name__ == "__main__":
    unittest.main()
