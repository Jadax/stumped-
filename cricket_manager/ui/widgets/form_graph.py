"""Compact last-ten-match line chart."""
from __future__ import annotations
from statistics import mean
import pygame
from .common import BORDER, CARD, GOLD, GREEN, MUTED, RED, text


class FormGraph:
    def __init__(self, rect: pygame.Rect, values: list[int], period: str = "Last 10"):
        self.rect, self.all_values, self.period = pygame.Rect(rect), list(values), period
        limits = {"Week": 2, "Month": 8, "Season": 40, "Last 10": 10}
        self.values = self.all_values[-limits.get(period, 10):]

    @property
    def trend(self) -> str:
        if len(self.values) < 4: return "Steady"
        delta = mean(self.values[-2:]) - mean(self.values[-4:-2])
        return "Improving" if delta > 3 else "Declining" if delta < -3 else "Steady"

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, CARD, self.rect, border_radius=6)
        for fraction in (0, .5, 1):
            y = self.rect.bottom - int(self.rect.height * fraction)
            pygame.draw.line(surface, BORDER, (self.rect.x, y), (self.rect.right, y))
        if len(self.values) < 2:
            return
        points = [(self.rect.x + int(i * self.rect.width / (len(self.values) - 1)),
                   self.rect.bottom - int(max(0, min(100, value)) * self.rect.height / 100))
                  for i, value in enumerate(self.values)]
        pygame.draw.lines(surface, GREEN, False, points, 3)
        for point in points:
            pygame.draw.circle(surface, GREEN, point, 4)
        trend_colour = GREEN if self.trend == "Improving" else RED if self.trend == "Declining" else GOLD
        text(surface, self.period.upper(), (self.rect.x + 7, self.rect.y + 6), 10, MUTED, bold=True)
        text(surface, self.trend.upper(), (self.rect.right - 7, self.rect.y + 6), 10, trend_colour,
             bold=True, anchor="topright")
