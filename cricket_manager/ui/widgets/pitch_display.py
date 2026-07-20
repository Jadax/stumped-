"""Graphical pitch strip with condition, wear, and tactical effect."""
from __future__ import annotations

import pygame

from .common import WHITE, text


class PitchDisplay:
    def __init__(self, rect: pygame.Rect, condition: str, wear: float = 0):
        self.rect, self.condition, self.wear = pygame.Rect(rect), condition, wear

    def draw(self, surface: pygame.Surface) -> None:
        colours = {"Green": "#6f8f55", "Dry": "#bd9d65", "Dusty": "#9e7b50",
                   "Flat": "#c7ad78", "Worn": "#806b54"}
        rect = self.rect
        pygame.draw.rect(surface, colours.get(self.condition, "#bd9d65"), rect, border_radius=7)
        for index in range(int(self.wear // 15)):
            pygame.draw.line(surface, "#59483a", (rect.x + 10 + index * 17, rect.y + 9),
                             (rect.x + 24 + index * 17, rect.bottom - 9), 2)
        for y in (rect.y + 10, rect.bottom - 11):
            pygame.draw.line(surface, WHITE, (rect.x + 12, y), (rect.right - 12, y), 2)
        effects = {"Green": "Pace and seam", "Dry": "Spin later", "Dusty": "Heavy turn",
                   "Flat": "Batting friendly", "Worn": "Variable bounce"}
        pygame.draw.rect(surface, "#182230", (rect.x + 5, rect.centery - 9, rect.w - 10, 18), border_radius=5)
        text(surface, f"{self.condition.upper()} - {effects.get(self.condition, '')}",
             (rect.centerx, rect.centery), 10, WHITE, True, anchor="center")
