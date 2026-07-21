"""Five-axis polygon chart used in player profiles."""
from __future__ import annotations
import math
import pygame
from .common import BORDER, GREEN, MUTED, WHITE, text


class RadarChart:
    def __init__(self, rect: pygame.Rect, values: dict[str, float]):
        self.rect, self.values = pygame.Rect(rect), values

    def _points(self, radius_factor: float) -> list[tuple[float, float]]:
        cx, cy = self.rect.center
        radius = min(self.rect.width, self.rect.height) * .34
        return [(cx + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * radius * radius_factor,
                 cy + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * radius * radius_factor) for i in range(5)]

    def draw(self, surface: pygame.Surface) -> None:
        labels = list(self.values)[:5]
        while len(labels) < 5:
            labels.append("")
        for level in (.25, .5, .75, 1.0):
            pygame.draw.aalines(surface, BORDER, True, self._points(level))
        centre = self.rect.center
        outer = self._points(1)
        for point in outer:
            pygame.draw.line(surface, BORDER, centre, point)
        data = []
        for i, label in enumerate(labels):
            value = max(0, min(100, self.values.get(label, 0))) / 100
            ox, oy = outer[i]
            data.append((centre[0] + (ox - centre[0]) * value, centre[1] + (oy - centre[1]) * value))
            label_pos = (centre[0] + (ox - centre[0]) * 1.28, centre[1] + (oy - centre[1]) * 1.28)
            text(surface, label, (int(label_pos[0]), int(label_pos[1])), 11, MUTED, anchor="center")
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(overlay, (*GREEN[:3], 105), data)
        pygame.draw.polygon(overlay, GREEN, data, width=2)
        pygame.draw.aalines(overlay, GREEN, True, data)
        surface.blit(overlay, (0, 0))
        for point in data:
            pygame.draw.aacircle(surface, WHITE, (int(point[0]), int(point[1])), 3)

