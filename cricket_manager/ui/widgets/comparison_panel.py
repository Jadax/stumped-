"""One half of the player comparison modal."""
from __future__ import annotations
import pygame
from src.utilities.player_portraits import draw_portrait
from .attribute_bar import AttributeBar
from .common import BORDER, CARD, GOLD, MUTED, WHITE, text


class ComparisonPanel:
    def __init__(self, rect: pygame.Rect, player: dict, opponent: dict | None = None):
        self.rect, self.player, self.opponent = pygame.Rect(rect), player, opponent

    @staticmethod
    def flattened(player: dict) -> list[tuple[str, int]]:
        result = []
        for group in ("batting", "bowling", "fielding", "mental"):
            result.extend((key.replace("_", " ").title(), value) for key, value in player.get(group, {}).items())
        return result

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, CARD, self.rect)
        pygame.draw.rect(surface, BORDER, self.rect, width=1)
        avatar_rect = pygame.Rect(self.rect.x + 24, self.rect.y + 22, 68, 68)
        draw_portrait(surface, avatar_rect, self.player)
        text(surface, self.player["name"], (self.rect.x + 108, self.rect.y + 22), 18, bold=True)
        text(surface, f"{self.player['age']}  •  {self.player['role']}", (self.rect.x + 108, self.rect.y + 50), 13, MUTED)
        text(surface, self.player["overall"], (self.rect.right - 25, self.rect.y + 30), 30, GOLD, bold=True, anchor="topright")
        others = dict(self.flattened(self.opponent)) if self.opponent else {}
        attributes = self.flattened(self.player)
        column_width = (self.rect.width - 48) // 2
        per_column = (len(attributes) + 1) // 2
        for index, (label, value) in enumerate(attributes):
            column, row = divmod(index, per_column)
            x = self.rect.x + 16 + column * (column_width + 16)
            y = self.rect.y + 105 + row * 39
            AttributeBar(pygame.Rect(x, y, column_width, 28), label, value, others.get(label)).draw(surface)
