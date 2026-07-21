"""The Over Beads — Stumped!'s signature six-ball strip (docs/DESIGN.md).

Each legal delivery renders as an 18 px bead: hollow for a dot, green fill
for runs, gold for a boundary, signature red for a wicket, sky outline for
extras.  Used on the live match footer, dashboards, and match reports so the
same glyph language reads everywhere.
"""
from __future__ import annotations

import pygame

from .common import BG, DIM, GOLD, GREEN, MUTED, WHITE, text
from src.views.theme import ACCENT, ACTION


class OverBeads:
    """Render up to ``capacity`` ball results as beads inside ``rect``."""

    def __init__(self, rect: pygame.Rect, results: list[str], capacity: int = 6,
                 radius: int = 9, show_glyphs: bool = True):
        self.rect = pygame.Rect(rect)
        self.results = list(results)[-capacity:]
        self.capacity = max(1, capacity)
        self.radius = radius
        self.show_glyphs = show_glyphs

    @staticmethod
    def _style(result: str) -> tuple[pygame.Color, bool]:
        """(colour, filled) for one ball result string."""
        if result == "W":
            return ACTION, True
        if result in ("4", "6"):
            return GOLD, True
        if result in ("Wd", "Nb"):
            return ACCENT, False
        if result in ("•", "0", "dot", ""):
            return DIM, False
        return GREEN, True

    def draw(self, surface: pygame.Surface) -> None:
        step = self.radius * 2 + 8
        cy = self.rect.centery
        start_x = self.rect.x + self.radius + 1
        for index in range(self.capacity):
            cx = start_x + index * step
            if index < len(self.results):
                result = str(self.results[index])
                colour, filled = self._style(result)
                if filled:
                    pygame.draw.aacircle(surface, colour, (cx, cy), self.radius)
                    pygame.draw.aacircle(surface, colour.lerp(WHITE, .25), (cx, cy), self.radius, 1)
                else:
                    pygame.draw.aacircle(surface, BG, (cx, cy), self.radius)
                    pygame.draw.aacircle(surface, colour, (cx, cy), self.radius, 2)
                if self.show_glyphs and result not in ("•", "0", "dot", ""):
                    glyph_colour = BG if filled else colour
                    text(surface, result, (cx, cy), 10, glyph_colour, bold=True, anchor="center")
            else:
                pygame.draw.aacircle(surface, DIM, (cx, cy), self.radius, 1)

    @property
    def width(self) -> int:
        return self.capacity * (self.radius * 2 + 8)
