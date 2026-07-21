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

# "Test at Dusk" palette (docs/DESIGN.md).  Names retained by older screens
# are aliases into this palette so the skin propagates safely without a
# brittle mass rewrite.  Warm near-black canvas, warm charcoal surfaces,
# cricket-ball red as the signature action colour, gold for ratings, pitch
# green for positives, and a cool sky accent reserved for links/info.
BACKGROUND = pygame.Color("#12100e")
SURFACE = pygame.Color("#1a1714")
PANEL = SURFACE
CARD = pygame.Color("#221e1a")
ROW_ALT = pygame.Color("#2b2620")
HEADER = pygame.Color("#4caf6d")
GREEN = HEADER
GREEN_LIGHT = pygame.Color("#66c285")
ACCENT = pygame.Color("#7fb8d8")
BLUE = ACCENT
TEXT_PRIMARY = pygame.Color("#f4efe8")
WHITE = TEXT_PRIMARY
TEXT_SECONDARY = pygame.Color("#a79e92")
MUTED = TEXT_SECONDARY
TEXT_MUTED = pygame.Color("#5a5248")
DIM = TEXT_MUTED
BORDER = pygame.Color("#3a332b")
SUCCESS = GREEN
WARNING = pygame.Color("#e0a63c")
GOLD = WARNING
YELLOW = WARNING
DANGER = pygame.Color("#d6493f")
RED = DANGER
INFO = ACCENT
HOVER = pygame.Color("#2b2620")
ACTIVE = pygame.Color("#342e26")
ELITE = pygame.Color("#eebb55")
# Signature cricket-ball red: primary actions, live indicators, wickets.
ACTION = pygame.Color("#d6493f")

# Runtime accessibility preferences (docs/DESIGN.md §8), applied at startup
# from user settings and updated live by the Settings screen.
PREFS = {"reduced_motion": False, "colour_blind": True, "ui_scale": 1.0}


def set_ui_scale(scale: float) -> None:
    """Change the font ramp multiplier and invalidate every cached render."""
    PREFS["ui_scale"] = max(1.0, min(1.3, float(scale)))
    get_font.cache_clear()
    try:
        from ui.widgets.common import _render_text
        _render_text.cache_clear()
    except ImportError:
        pass

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
    strip = pygame.Surface((1, height))
    try:
        strip = strip.convert()
    except pygame.error:
        pass  # headless renders before display.set_mode still work
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
    pixel_size = max(11, int(round(size * PREFS["ui_scale"])))
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
