"""Consistent responsive spacing helpers for screen grids."""
from __future__ import annotations

import pygame


def inset(rect: pygame.Rect, amount: int) -> pygame.Rect:
    return pygame.Rect(rect).inflate(-amount * 2, -amount * 2)


def columns(rect: pygame.Rect, ratios: tuple[float, ...], gap: int = 12) -> list[pygame.Rect]:
    """Divide a rectangle into exact ratio-based columns without accumulated gaps."""
    available = rect.width - gap * (len(ratios) - 1)
    total = sum(ratios)
    widths = [round(available * ratio / total) for ratio in ratios]
    widths[-1] += available - sum(widths)
    result, x = [], rect.x
    for width in widths:
        result.append(pygame.Rect(x, rect.y, width, rect.height)); x += width + gap
    return result


def rows(rect: pygame.Rect, ratios: tuple[float, ...], gap: int = 12) -> list[pygame.Rect]:
    available = rect.height - gap * (len(ratios) - 1)
    total = sum(ratios)
    heights = [round(available * ratio / total) for ratio in ratios]
    heights[-1] += available - sum(heights)
    result, y = [], rect.y
    for height in heights:
        result.append(pygame.Rect(rect.x, y, rect.width, height)); y += height + gap
    return result

