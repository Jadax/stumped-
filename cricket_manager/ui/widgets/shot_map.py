"""Supersampled wagon-wheel, boundary map, and tactical ring."""
from __future__ import annotations

import math
import pygame

from .common import GOLD, GREEN, RED, MUTED, text


class ShotMap:
    """Render persistent shot events; optionally overlay field placements."""

    def __init__(self, rect: pygame.Rect, events: list[dict], show_field: bool = False):
        self.rect, self.events, self.show_field = pygame.Rect(rect), events, show_field

    def draw(self, surface: pygame.Surface) -> None:
        scale = 3
        canvas = pygame.Surface((self.rect.w * scale, self.rect.h * scale), pygame.SRCALPHA)
        centre = canvas.get_rect().center
        radius = min(canvas.get_size()) // 2 - 18
        pygame.draw.circle(canvas, "#174f2c", centre, radius)
        pygame.draw.circle(canvas, "#246b38", centre, int(radius * .63))
        pygame.draw.circle(canvas, "#8fb99a", centre, int(radius * .34), 2)
        pygame.draw.circle(canvas, "#f2f6fc", centre, radius, 4)
        pygame.draw.rect(canvas, "#cbb98b", (centre[0] - 12, centre[1] - 38, 24, 76), border_radius=4)
        pygame.draw.line(canvas, "#f2f6fc", (centre[0] - 18, centre[1] - 22),
                         (centre[0] + 18, centre[1] - 22), 2)

        for event in self.events:
            angle, distance = float(event.get("angle", 0)), float(event.get("distance", .2))
            end = (centre[0] + math.cos(angle) * radius * distance,
                   centre[1] + math.sin(angle) * radius * distance)
            colour = RED if event.get("wicket") else GOLD if event.get("runs", 0) >= 4 else GREEN if event.get("runs", 0) else MUTED
            pygame.draw.aaline(canvas, colour, centre, end)
            pygame.draw.circle(canvas, colour, (round(end[0]), round(end[1])), 6)

        if self.show_field:
            positions = {
                "Slip": (-.18, -.20), "Point": (-.58, -.10), "Cover": (-.46, -.48),
                "Mid-off": (-.20, -.62), "Mid-on": (.20, -.62), "Midwicket": (.48, -.36),
                "Square": (.58, .04), "Fine": (.28, .67), "Third": (-.33, .66),
            }
            tiny = pygame.font.Font(None, max(18, round(7 * scale)))
            for label, (nx, ny) in positions.items():
                point = (round(centre[0] + nx * radius), round(centre[1] + ny * radius))
                pygame.draw.circle(canvas, "#4cc2ff", point, 8)
                pygame.draw.circle(canvas, "#dbeafe", point, 8, 2)
                tag = tiny.render(label, True, "#f2f6fc")
                canvas.blit(tag, (point[0] - tag.get_width() // 2, point[1] + 9))

        surface.blit(pygame.transform.smoothscale(canvas, self.rect.size), self.rect)
        caption = "Ring - every shot plus the current field" if self.show_field else "Wagon wheel - gold boundaries, red dismissals"
        text(surface, caption, (self.rect.centerx, self.rect.bottom + 4), 10, MUTED, anchor="midtop")
