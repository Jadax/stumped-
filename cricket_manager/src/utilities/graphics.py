"""Original programmatic icons and crests; no external copyrighted artwork."""
from __future__ import annotations

import hashlib
import pygame
from src.utilities.logo_generator import draw_team_logo
from src.views.theme import BACKGROUND, WARNING, get_font


def _colours(seed: str) -> tuple[pygame.Color, pygame.Color]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    primary = pygame.Color(45 + digest[0] % 100, 55 + digest[1] % 100, 55 + digest[2] % 100)
    accent = pygame.Color(145 + digest[3] % 100, 145 + digest[4] % 100, 35 + digest[5] % 100)
    return primary, accent


def draw_crest(surface: pygame.Surface, centre: tuple[int, int], size: int, seed: str,
               initials: str = "S") -> None:
    """Draw a deterministic geometric shield usable for any generated club."""
    draw_team_logo(surface, centre, size, seed, initials)


def draw_cricket_icon(surface: pygame.Surface, kind: str, rect: pygame.Rect,
                      colour: pygame.Color | str = WARNING) -> None:
    """Draw simple bat, ball, stumps, trophy, stadium, coach, money icons."""
    r, colour = pygame.Rect(rect), pygame.Color(colour)
    cx, cy = r.center; unit = max(1, min(r.width, r.height) // 12)
    if kind == "ball":
        pygame.draw.aacircle(surface, colour, r.center, min(r.width, r.height) // 3)
        pygame.draw.arc(surface, pygame.Color("white"), r.inflate(-r.width // 3, -r.height // 5), -1.2, 1.2, unit)
    elif kind == "bat":
        pygame.draw.polygon(surface, colour, [(cx-3*unit, r.bottom-2*unit),(cx+unit,r.bottom),(cx+3*unit,r.y+3*unit),(cx,r.y+2*unit)])
        pygame.draw.line(surface, colour, (cx+2*unit, r.y+3*unit), (cx+4*unit, r.y), unit*2)
    elif kind == "stumps":
        for dx in (-3*unit, 0, 3*unit): pygame.draw.line(surface, colour, (cx+dx, r.y+2*unit), (cx+dx, r.bottom-2*unit), unit)
        pygame.draw.line(surface, colour, (cx-4*unit, r.y+2*unit), (cx+4*unit, r.y+2*unit), unit)
    elif kind == "trophy":
        pygame.draw.rect(surface, colour, (cx-3*unit, cy-4*unit, 6*unit, 6*unit), border_radius=unit)
        pygame.draw.arc(surface, colour, (cx-6*unit, cy-4*unit, 5*unit, 5*unit), 1.4, 4.8, unit)
        pygame.draw.arc(surface, colour, (cx+unit, cy-4*unit, 5*unit, 5*unit), -1.7, 1.7, unit)
        pygame.draw.line(surface, colour, (cx, cy+2*unit), (cx, cy+5*unit), unit*2)
        pygame.draw.line(surface, colour, (cx-3*unit, cy+5*unit), (cx+3*unit, cy+5*unit), unit*2)
    elif kind == "money":
        pygame.draw.rect(surface, colour, r.inflate(-2*unit, -4*unit), border_radius=unit)
        pygame.draw.aacircle(surface, BACKGROUND, r.center, 2*unit)
    else:
        pygame.draw.aacircle(surface, colour, (cx, cy-3*unit), 2*unit)
        pygame.draw.line(surface, colour, (cx, cy-unit), (cx, cy+5*unit), unit*2)
        pygame.draw.line(surface, colour, (cx-4*unit, cy+unit), (cx+4*unit, cy+unit), unit)
