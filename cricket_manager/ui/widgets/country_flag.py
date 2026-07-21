"""Country flags rendered from bundled public-domain PNGs (Flagpedia set).

Real flag artwork lives in ``assets/images/flags`` (w80 PNGs, public
domain).  West Indies is a cricket entity without an ISO flag, so it keeps
an original drawn design; unknown countries fall back to a neutral tricolor.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

import pygame

ALIASES = {"English": "England", "Australian": "Australia", "Indian": "India", "Pakistani": "Pakistan",
           "South African": "South Africa", "New Zealander": "New Zealand", "West Indian": "West Indies",
           "Sri Lankan": "Sri Lanka", "Bangladeshi": "Bangladesh", "Afghan": "Afghanistan",
           "Zimbabwean": "Zimbabwe", "Irish": "Ireland", "Dutch": "Netherlands", "Scottish": "Scotland",
           "American": "USA", "Emirati": "UAE", "Nepalese": "Nepal", "Omani": "Oman",
           "Namibian": "Namibia", "Papua New Guinean": "Papua New Guinea"}

ISO_CODES = {"England": "gb-eng", "Australia": "au", "India": "in", "Pakistan": "pk",
             "South Africa": "za", "New Zealand": "nz", "Sri Lanka": "lk", "Bangladesh": "bd",
             "Afghanistan": "af", "Zimbabwe": "zw", "Ireland": "ie", "Netherlands": "nl",
             "Scotland": "gb-sct", "USA": "us", "UAE": "ae", "Nepal": "np", "Oman": "om",
             "Namibia": "na", "Papua New Guinea": "pg"}


def _flag_dir() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "assets" / "images" / "flags"


@lru_cache(maxsize=128)
def _flag_surface(code: str, width: int, height: int) -> pygame.Surface | None:
    path = _flag_dir() / f"{code}.png"
    if not path.is_file():
        return None
    try:
        image = pygame.image.load(str(path))
        try:
            image = image.convert_alpha()
        except pygame.error:
            pass
        return pygame.transform.smoothscale(image, (max(1, width), max(1, height)))
    except pygame.error:
        return None


def draw_country_flag(surface: pygame.Surface, rect: pygame.Rect, country: str) -> None:
    r = pygame.Rect(rect)
    country = ALIASES.get(country, country)
    code = ISO_CODES.get(country)
    flag = _flag_surface(code, r.width, r.height) if code else None
    if flag is not None:
        surface.blit(flag, r)
    elif country == "West Indies":
        pygame.draw.rect(surface, "#7B0041", r)
        pygame.draw.aacircle(surface, "#FFD100", r.center, r.h // 4)
        pygame.draw.line(surface, "#007A3D", (r.centerx, r.centery - r.h // 4), (r.centerx, r.bottom - 2), 2)
    else:
        for i, colour in enumerate(("#304FFE", "white", "#D29922")):
            pygame.draw.rect(surface, colour, (r.x + i * r.w // 3, r.y, r.w // 3 + 1, r.h))
    pygame.draw.rect(surface, "#404855", r, 1, border_radius=2)
