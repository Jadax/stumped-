"""A labelled 0–100 attribute meter."""
from __future__ import annotations
import pygame
from .common import CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, text


class AttributeBar:
    def __init__(self, rect: pygame.Rect, label: str, value: int, comparison: int | None = None):
        self.rect, self.label = pygame.Rect(rect), label
        self.value, self.comparison = max(0, min(100, int(value))), comparison

    def draw(self, surface: pygame.Surface) -> None:
        text(surface, self.label, (self.rect.x, self.rect.y), 13, MUTED)
        value_colour = GREEN if self.value >= 75 else GOLD if self.value >= 60 else RED if self.value < 40 else WHITE
        if self.comparison is not None:
            value_colour = GREEN if self.value > self.comparison else RED if self.value < self.comparison else WHITE
        text(surface, self.value, (self.rect.right, self.rect.y), 13, value_colour, bold=True, anchor="topright")
        track = pygame.Rect(self.rect.x, self.rect.y + 20, self.rect.width, 7)
        pygame.draw.rect(surface, CARD_ALT, track, border_radius=3)
        pygame.draw.rect(surface, value_colour, (track.x, track.y, int(track.width * self.value / 100), track.height), border_radius=3)

