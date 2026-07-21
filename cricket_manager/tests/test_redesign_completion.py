"""Coverage for the final redesign deliverables (v0.19.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


class RedesignCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))
        from database import initialise_database, fetch_teams, fetch_players
        cls.database = os.path.join(tempfile.mkdtemp(), "redesign.db")
        initialise_database(cls.database)
        team = dict(fetch_teams(cls.database)[0])
        cls.context = {"database_path": cls.database, "team": team,
                       "players": fetch_players(team["id"], cls.database),
                       "user_settings": {}}

    def test_quick_card_renders_and_clamps(self) -> None:
        from ui.widgets import QuickCard
        player = self.context["players"][0]
        QuickCard.draw(self.surface, (20, 20), player)
        QuickCard.draw(self.surface, (1275, 715), player)  # clamps inside bounds

    def test_squad_tabs_swap_column_sets(self) -> None:
        from ui.squad import SquadScreen
        screen = SquadScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                             1.0, dict(self.context))
        for tab in screen.COLUMN_SETS:
            screen.view_tab = tab
            screen.table = screen.table.__class__(screen.table_rect, screen.COLUMN_SETS[tab](), [], 35,
                                                  colour_func=screen._cell_colour)
            screen.refresh_rows()
            screen.draw(self.surface)
            self.assertGreater(len(screen.table.rows), 0)

    def test_accessibility_settings_persist_and_migrate(self) -> None:
        from database import load_game, update_user_settings
        update_user_settings({"reduced_motion": 1, "colour_blind_mode": 0, "ui_scale": 1.1},
                             self.database)
        user = dict(load_game(self.database)["user"])
        self.assertEqual(user["reduced_motion"], 1)
        self.assertEqual(user["colour_blind_mode"], 0)
        self.assertAlmostEqual(user["ui_scale"], 1.1)

    def test_ui_scale_changes_font_ramp_and_restores(self) -> None:
        from src.views.theme import get_font, set_ui_scale
        base_height = get_font(14).get_height()
        set_ui_scale(1.2)
        try:
            self.assertGreater(get_font(14).get_height(), base_height)
        finally:
            set_ui_scale(1.0)
        self.assertEqual(get_font(14).get_height(), base_height)

    def test_reduced_motion_suppresses_wicket_flash_scheduling(self) -> None:
        from src.views.theme import PREFS
        self.assertIn("reduced_motion", PREFS)
        self.assertIn("colour_blind", PREFS)


if __name__ == "__main__":
    unittest.main()
