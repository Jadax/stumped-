"""A five-star ability rating with half-star precision (FM-style)."""
from __future__ import annotations

import math

import pygame

from .common import DIM, GOLD, MUTED, text


def _star_points(centre: tuple[int, int], radius: int) -> list[tuple[float, float]]:
    cx, cy = centre
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * .45
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


class StarRating:
    """Renders ``value`` (0–100) as 0–5 stars in half-star steps."""

    def __init__(self, rect: pygame.Rect, value: int, label: str = ""):
        self.rect = pygame.Rect(rect)
        self.value = max(0, min(100, int(value)))
        self.label = label

    def draw(self, surface: pygame.Surface) -> None:
        x = self.rect.x
        if self.label:
            label_rect = text(surface, self.label, (self.rect.x, self.rect.centery), 11, MUTED, anchor="midleft")
            x = label_rect.right + 8
        radius = max(5, min(self.rect.height // 2 - 1, (self.rect.right - x) // 11))
        halves = int(round(self.value / 10))  # 0–10 half stars
        for i in range(5):
            centre = (x + radius + i * (radius * 2 + 4), self.rect.centery)
            points = _star_points(centre, radius)
            pygame.draw.polygon(surface, DIM, points)
            fill = min(2, max(0, halves - i * 2))
            if fill == 2:
                pygame.draw.polygon(surface, GOLD, points)
            elif fill == 1:
                star = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
                local = [(px - centre[0] + radius + 1, py - centre[1] + radius + 1) for px, py in points]
                pygame.draw.polygon(star, GOLD, local)
                surface.blit(star, (centre[0] - radius - 1, centre[1] - radius - 1),
                             area=pygame.Rect(0, 0, radius + 1, radius * 2 + 2))
            pygame.draw.polygon(surface, GOLD if fill else DIM, points, 1)
