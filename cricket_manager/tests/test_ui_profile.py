"""Headless render checks for the FM-style player profile upgrades."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402


def _player() -> dict:
    return {"id": 7, "name": "Profile Tester", "age": 24, "role": "Batter", "nationality": "England",
            "overall": 82, "potential": 91, "form": 63, "wage": 5200, "contract_years_remaining": 2,
            "batting": {"technique": 80, "timing": 75, "power": 70},
            "bowling": {"pace": 40, "accuracy": 45},
            "fielding": {"catching": 66, "ground": 61},
            "mental": {"big_match": 72, "consistency": 68, "fitness": 77, "morale": 81},
            "physical": {"fitness": 77}}


class ProfileUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def test_star_rating_renders_all_half_star_values(self) -> None:
        from ui.widgets import StarRating
        for value in range(0, 101, 5):
            StarRating(pygame.Rect(10, 10, 220, 20), value, "Ability").draw(self.surface)

    def test_over_beads_render_every_result_type(self) -> None:
        from ui.widgets import OverBeads
        beads = OverBeads(pygame.Rect(10, 40, 220, 26), ["•", "1", "4", "W", "Wd", "6"])
        beads.draw(self.surface)
        self.assertGreater(beads.width, 0)

    def test_palette_meets_wcag_contrast(self) -> None:
        from src.views.theme import ACTION, BACKGROUND, CARD, TEXT_PRIMARY, TEXT_SECONDARY

        def luminance(colour) -> float:
            def channel(v: int) -> float:
                v /= 255
                return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
            return .2126 * channel(colour.r) + .7152 * channel(colour.g) + .0722 * channel(colour.b)

        def ratio(a, b) -> float:
            la, lb = sorted((luminance(a), luminance(b)), reverse=True)
            return (la + .05) / (lb + .05)

        self.assertGreaterEqual(ratio(TEXT_PRIMARY, BACKGROUND), 7.0)   # AAA body
        self.assertGreaterEqual(ratio(TEXT_SECONDARY, CARD), 4.5)       # AA body
        self.assertGreaterEqual(ratio(TEXT_PRIMARY, ACTION), 3.0)       # AA large/bold on red

    def test_attribute_tiers_span_red_to_elite_gold(self) -> None:
        from src.views.theme import DANGER, ELITE, GREEN, WARNING, TEXT_PRIMARY, attribute_colour
        self.assertEqual(attribute_colour(20), DANGER)
        self.assertEqual(attribute_colour(50), WARNING)
        self.assertEqual(attribute_colour(65), TEXT_PRIMARY)
        self.assertEqual(attribute_colour(80), GREEN)
        self.assertEqual(attribute_colour(95), ELITE)

    def test_player_modal_tabs_render_with_value_and_stars(self) -> None:
        from ui.player_modals import PlayerDetailModal
        modal = PlayerDetailModal(pygame.Rect(0, 0, 1280, 720), _player())
        for tab in ["Personal", "Match Stats", "Records", "Bat Form", "Attributes"]:
            modal.active_tab = tab
            modal.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
