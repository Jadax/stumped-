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

# Premium dark palette.  Names retained by older screens are aliases into this
# palette so the new skin propagates safely without a brittle mass rewrite.
BACKGROUND = pygame.Color("#0d1117")
SURFACE = pygame.Color("#161b22")
PANEL = SURFACE
CARD = pygame.Color("#1c2333")
ROW_ALT = pygame.Color("#252d3f")
HEADER = pygame.Color("#3fb950")
GREEN = HEADER
GREEN_LIGHT = pygame.Color("#3fb950")
ACCENT = pygame.Color("#58a6ff")
BLUE = ACCENT
TEXT_PRIMARY = pygame.Color("#f0f6fc")
WHITE = TEXT_PRIMARY
TEXT_SECONDARY = pygame.Color("#8b949e")
MUTED = TEXT_SECONDARY
TEXT_MUTED = pygame.Color("#484f58")
DIM = TEXT_MUTED
BORDER = pygame.Color("#30363d")
SUCCESS = pygame.Color("#3fb950")
WARNING = pygame.Color("#d29922")
GOLD = WARNING
YELLOW = WARNING
DANGER = pygame.Color("#f85149")
RED = DANGER
INFO = ACCENT
HOVER = pygame.Color("#252d3f")
ACTIVE = pygame.Color("#2d3748")

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
