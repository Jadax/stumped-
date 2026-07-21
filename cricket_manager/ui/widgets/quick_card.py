"""Universal player quick-card: a hover popover shown over any player list."""
from __future__ import annotations

import pygame

from src.utilities.player_portraits import draw_portrait
from src.views.theme import ACTION, CARD_RADIUS, attribute_colour
from .common import BG, BORDER, CARD, GOLD, MUTED, WHITE, text
from .star_rating import StarRating


class QuickCard:
    """Compact player summary drawn near the cursor; clamps to the surface."""

    SIZE = (264, 168)

    @classmethod
    def draw(cls, surface: pygame.Surface, anchor: tuple[int, int], player: dict) -> None:
        width, height = cls.SIZE
        bounds = surface.get_rect()
        rect = pygame.Rect(anchor[0] + 18, anchor[1] + 14, width, height)
        if rect.right > bounds.right - 8: rect.right = anchor[0] - 18
        if rect.bottom > bounds.bottom - 8: rect.bottom = anchor[1] - 12
        rect.clamp_ip(bounds)
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 130), shadow.get_rect(), border_radius=CARD_RADIUS)
        surface.blit(shadow, rect.move(0, 5))
        pygame.draw.rect(surface, CARD, rect, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, BORDER, rect, 1, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, ACTION, (rect.x, rect.y, 3, rect.height))
        portrait = pygame.Rect(rect.x + 14, rect.y + 14, 52, 52)
        draw_portrait(surface, portrait, player)
        text(surface, player.get("name", "—"), (rect.x + 78, rect.y + 16), 14, WHITE, bold=True)
        text(surface, f"{player.get('role', '—')} • {player.get('age', '—')} yrs • {player.get('nationality', '—')}",
             (rect.x + 78, rect.y + 38), 10, MUTED)
        overall = int(player.get("overall", 50))
        text(surface, overall, (rect.right - 20, rect.y + 15), 19, attribute_colour(overall), bold=True, anchor="topright")
        StarRating(pygame.Rect(rect.x + 78, rect.y + 54, rect.width - 96, 14),
                   int(player.get("potential", overall))).draw(surface)
        y = rect.y + 84
        for label, value in (("Form", int(player.get("form", 50))),
                             ("Fitness", int(player.get("mental", {}).get("fitness", 50))),
                             ("Morale", int(player.get("mental", {}).get("morale", 50)))):
            text(surface, label, (rect.x + 16, y), 10, MUTED)
            track = pygame.Rect(rect.x + 74, y + 3, rect.width - 130, 6)
            pygame.draw.rect(surface, BG, track, border_radius=3)
            pygame.draw.rect(surface, attribute_colour(value),
                             (track.x, track.y, max(2, int(track.width * value / 100)), 6), border_radius=3)
            text(surface, value, (rect.right - 16, y), 10, WHITE, bold=True, anchor="topright")
            y += 22
        text(surface, "Click row for full profile", (rect.centerx, rect.bottom - 14), 9, GOLD, anchor="center")
