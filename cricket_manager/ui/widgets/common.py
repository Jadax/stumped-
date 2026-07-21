"""Shared production theme exports and small text drawing helpers."""
from __future__ import annotations

import pygame

from src.views.theme import (
    ACCENT, ACTIVE, BACKGROUND, BORDER, CARD, CARD_RADIUS, DANGER, DIM,
    GREEN, GREEN_LIGHT, HEADER, HOVER, INFO, MUTED, PANEL, RED, ROW_ALT,
    SUCCESS, SURFACE, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, WARNING,
    WHITE, YELLOW, BLUE, GOLD, get_font,
)

# Backwards-compatible short names used throughout the current screens.
BG = BACKGROUND
CARD_ALT = ROW_ALT


def font(size: int, bold: bool = False) -> pygame.font.Font:
    return get_font(size, bold)


from functools import lru_cache


@lru_cache(maxsize=6144)
def _render_text(value: str, size: int, rgba: tuple[int, int, int, int], bold: bool) -> pygame.Surface:
    """Cached native-size text render.

    Rendered at the exact pixel size (SDL_ttf's own anti-aliasing) — earlier
    2x supersampling read soft/blurry once the window was scaled up on large
    monitors, so glyphs now stay on the pixel grid.  The cache makes the
    per-frame cost equivalent to a plain blit for repeated strings.
    """
    return get_font(size, bold).render(value, True, rgba)


def text(surface: pygame.Surface, value: object, pos: tuple[int, int], size: int = 14,
         colour: pygame.Color = WHITE, bold: bool = False, anchor: str = "topleft") -> pygame.Rect:
    rendered = _render_text(str(value), int(size), (colour.r, colour.g, colour.b, colour.a), bool(bold))
    rect = rendered.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(rendered, rect)
    return rect


def clipped_text(value: object, max_width: int, size: int = 14, bold: bool = False) -> str:
    raw = str(value)
    if font(size, bold).size(raw)[0] <= max_width:
        return raw
    while raw and font(size, bold).size(raw + "…")[0] > max_width:
        raw = raw[:-1]
    return raw + "…"


def wrap_text(value: str, max_width: int, size: int = 14) -> list[str]:
    words, lines, current = value.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font(size).size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
