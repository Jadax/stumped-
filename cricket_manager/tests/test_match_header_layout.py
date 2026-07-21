"""Match screen score-bug and action-row layout regressions (v0.21.0).

The original single-row header and ten-across action row overlapped badly
at 1280x720 (T20/DRS/status text merging, button labels bleeding into their
neighbours). This locks in the column-grid header and two-row action
layout so those regressions can't silently return.
"""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
import pygame_gui  # noqa: E402


def _match_context() -> dict:
    from database import initialise_database, fetch_teams, fetch_players
    db = os.path.join(tempfile.mkdtemp(), "header_layout.db")
    initialise_database(db)
    teams = fetch_teams(db)
    home, away = dict(teams[0]), dict(teams[1])
    return {
        "database_path": db, "team": home, "players": fetch_players(home["id"], db),
        "match_setup": {"user_xi": fetch_players(home["id"], db)[:11],
                        "opponent_xi": fetch_players(away["id"], db)[:11],
                        "fixture": {"format": "T20", "home_team": home["id"], "away_team": away["id"],
                                    "away_name": away["name"], "home_name": home["name"], "id": 1},
                        "pitch": "Green", "weather": "Overcast"},
        "selection": {}, "new_game_setup": {}, "current_date": "2026-04-01",
    }


class MatchHeaderLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def test_header_columns_sum_to_one_and_never_overlap(self) -> None:
        from ui.match_view import MatchScreen
        self.assertAlmostEqual(sum(MatchScreen.HEADER_COLUMNS), 1.0, places=6)

    def test_action_buttons_are_fully_populated_and_index_stable(self) -> None:
        from ui.match_view import MatchScreen
        screen = MatchScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                             1.0, _match_context())
        self.assertEqual(len(screen.action_buttons), 10)
        self.assertTrue(all(button is not None for button in screen.action_buttons))
        expected = ["PREDICT", "AUTO: OFF", "NEXT BALL", "OVER", "CHANGE",
                   "FIELD", "DRS 2", "SKIP", "PLAY", "EXIT"]
        self.assertEqual([b.label for b in screen.action_buttons], expected)

    def test_two_button_rows_do_not_vertically_overlap(self) -> None:
        from ui.match_view import MatchScreen
        screen = MatchScreen(pygame_gui.UIManager((1280, 660)), pygame.Rect(200, 60, 1080, 660),
                             1.0, _match_context())
        row_tops = sorted({button.rect.y for button in screen.action_buttons})
        self.assertEqual(len(row_tops), 2)
        first_row_bottom = row_tops[0] + screen.action_buttons[0].rect.height
        self.assertLessEqual(first_row_bottom, row_tops[1])

    def test_action_buttons_within_a_row_do_not_overlap_horizontally(self) -> None:
        from ui.match_view import MatchScreen
        screen = MatchScreen(pygame_gui.UIManager((1280, 660)), pygame.Rect(200, 60, 1080, 660),
                             1.0, _match_context())
        by_row: dict[int, list] = {}
        for button in screen.action_buttons:
            by_row.setdefault(button.rect.y, []).append(button.rect)
        for rects in by_row.values():
            rects.sort(key=lambda r: r.x)
            for a, b in zip(rects, rects[1:]):
                self.assertLessEqual(a.right, b.x, f"{a} overlaps {b}")

    def test_match_screen_renders_without_error_at_1280x720(self) -> None:
        from ui.match_view import MatchScreen
        screen = MatchScreen(pygame_gui.UIManager((1280, 720)), pygame.Rect(200, 60, 1080, 660),
                             1.0, _match_context())
        for _ in range(20):
            screen.simulate_ball()
        screen.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
