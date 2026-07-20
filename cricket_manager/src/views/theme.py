"""Production typography, colour, spacing, and geometry design tokens.

This is the single source of truth for both the hand-drawn Pygame UI and
pygame-gui.  Keeping the tokens here prevents individual screens from slowly
drifting into different shades, typefaces, and spacing rules.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

import pygame


def _resource_root() -> Path:
    """Return the source root in development and PyInstaller's bundle root."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


FONT_FAMILY = "Inter"
FONT_PATH = _resource_root() / "assets" / "fonts" / "Inter-VariableFont_opsz,wght.ttf"
FONT_FALLBACKS = ("Segoe UI", "Helvetica", "Arial")

# "Midnight Pitch" premium dark palette.  Names retained by older screens are
# aliases into this palette so the skin propagates safely without a brittle
# mass rewrite.  Deep blue-black canvas, cool elevated surfaces, an electric
# sky-blue action accent, and a vibrant pitch green reserved for positives.
BACKGROUND = pygame.Color("#0a0d16")
SURFACE = pygame.Color("#10141f")
PANEL = SURFACE
CARD = pygame.Color("#171d2b")
ROW_ALT = pygame.Color("#1f2637")
HEADER = pygame.Color("#2fd06f")
GREEN = HEADER
GREEN_LIGHT = pygame.Color("#4ade80")
ACCENT = pygame.Color("#4cc2ff")
BLUE = ACCENT
TEXT_PRIMARY = pygame.Color("#f2f6fc")
WHITE = TEXT_PRIMARY
TEXT_SECONDARY = pygame.Color("#8e99ad")
MUTED = TEXT_SECONDARY
TEXT_MUTED = pygame.Color("#4b5468")
DIM = TEXT_MUTED
BORDER = pygame.Color("#2a3245")
SUCCESS = GREEN
WARNING = pygame.Color("#e8b53e")
GOLD = WARNING
YELLOW = WARNING
DANGER = pygame.Color("#ff5c5c")
RED = DANGER
INFO = ACCENT
HOVER = pygame.Color("#242c40")
ACTIVE = pygame.Color("#2c3650")
ELITE = pygame.Color("#f0c34e")

# FM-style attribute tiers: red (weak) → amber (modest) → white (solid) →
# green (strong) → gold (elite).  Every attribute meter, comparison view, and
# scout report should colour values through this single function.
def attribute_colour(value: int) -> pygame.Color:
    if value >= 90:
        return ELITE
    if value >= 75:
        return GREEN
    if value >= 60:
        return TEXT_PRIMARY
    if value >= 40:
        return WARNING
    return DANGER


def vertical_gradient(size: tuple[int, int], top: pygame.Color, bottom: pygame.Color) -> pygame.Surface:
    """A cached-free two-stop vertical gradient surface for headers/panels."""
    width, height = max(1, size[0]), max(1, size[1])
    strip = pygame.Surface((1, height)).convert()
    for y in range(height):
        strip.set_at((0, y), top.lerp(bottom, y / max(1, height - 1)))
    return pygame.transform.scale(strip, (width, height))

FONT_SIZES = {
    "h1": 32,
    "h2": 24,
    "h3": 18,
    "body": 14,
    "small": 12,
    "stats": 16,
    # Compatibility aliases used by existing startup views.
    "display": 32,
    "header": 24,
    "subheader": 18,
}
FONT_WEIGHTS = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700}
SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}
CARD_RADIUS = 12
BUTTON_RADIUS = 8
SHADOW_OFFSET = (0, 4)
SHADOW_ALPHA = 77


@lru_cache(maxsize=128)
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Load Inter at a readable size, with a robust system-font fallback.

    The bundled variable font is used for every normal run.  Synthetic bold is
    intentionally enabled for headings because ``pygame.font`` does not expose
    the variable font's weight axis consistently across supported SDL builds.
    """
    pixel_size = max(11, int(round(size)))
    try:
        if FONT_PATH.is_file():
            result = pygame.font.Font(str(FONT_PATH), pixel_size)
            result.set_bold(bool(bold))
            return result
    except (OSError, pygame.error):
        pass
    for family in FONT_FALLBACKS:
        matched = pygame.font.match_font(family, bold=bold)
        if matched:
            return pygame.font.Font(matched, pixel_size)
    return pygame.font.Font(None, pixel_size)


def scaled(value: int, scale: float, minimum: int | None = None) -> int:
    result = round(value * scale)
    return max(minimum or 0, result)
