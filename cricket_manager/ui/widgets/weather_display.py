"""Compact graphical current conditions and six-period forecast."""
from __future__ import annotations

import pygame

from .common import GOLD, WHITE, MUTED, text


class WeatherDisplay:
    def __init__(self, rect: pygame.Rect, current: str, forecast: list[str]):
        self.rect, self.current, self.forecast = pygame.Rect(rect), current, forecast

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.rect
        pygame.draw.rect(surface, "#10141f", rect, border_radius=10)
        spacing = max(32, (rect.w - 28) // max(1, min(6, len(self.forecast))))
        for index, state in enumerate(self.forecast[:6]):
            x, y = rect.x + 18 + index * spacing, rect.y + 22
            if state == "Sunny":
                pygame.draw.circle(surface, GOLD, (x, y), 9)
            else:
                pygame.draw.circle(surface, "#8e99ad", (x - 5, y), 8)
                pygame.draw.circle(surface, "#b1bac4", (x + 4, y - 3), 10)
                if state == "Rain Threat":
                    for dx in (-6, 0, 6):
                        pygame.draw.line(surface, "#4cc2ff", (x + dx, y + 10), (x + dx - 2, y + 18), 2)
            short = {"Sunny": "SUN", "Cloudy": "CLOUD", "Overcast": "OVC", "Rain Threat": "RAIN"}.get(state, state[:4].upper())
            text(surface, short, (x, y + 25), 8, WHITE if index == 0 else MUTED, anchor="midtop")
