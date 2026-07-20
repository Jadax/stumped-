"""Headless visual audit for the final warm-theme refinement.

Run with SDL_VIDEODRIVER=dummy. Images are written to ``artifacts`` for a
human layout check at the minimum and 4K target resolutions.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
import pygame_gui

from database import fetch_players, get_team_summary, initialise_database
from src.utilities.logo_generator import draw_team_logo
from src.utilities.player_portraits import draw_portrait
from src.views.theme import BACKGROUND, FONT_PATH, TEXT_PRIMARY, get_font
from ui.dashboard import DashboardScreen
from ui.facilities import FacilitiesScreen
from ui.selection import SelectionScreen
from ui.training import TrainingScreen
from ui.transfers import TransfersScreen


def manager(size: tuple[int, int]) -> pygame_gui.UIManager:
    result = pygame_gui.UIManager(size)
    if FONT_PATH.is_file(): result.add_font_paths("inter", str(FONT_PATH), str(FONT_PATH))
    result.get_theme().load_theme(str(ROOT / "ui" / "theme.json"))
    return result


def render_screen(screen_type, name: str, size: tuple[int, int], database: Path,
                  output_size: tuple[int, int] | None = None) -> None:
    surface = pygame.Surface(size)
    team = get_team_summary(1, database)
    context = {"database_path": database, "team": team, "players": fetch_players(1, database),
               "current_date": "2026-04-01", "user_settings": {"currency": "GBP"}}
    screen = screen_type(manager(size), pygame.Rect(0, 0, *size), size[0] / 1280, context)
    screen.draw(surface)
    output_size = output_size or size
    output = pygame.transform.smoothscale(surface, output_size) if output_size != size else surface
    pygame.image.save(output, ROOT / "artifacts" / f"final-{name}-{output_size[0]}x{output_size[1]}.png")


def render_identity_sheet(database: Path) -> None:
    surface = pygame.Surface((1280, 720)); surface.fill(BACKGROUND)
    title = get_font(30, True).render("Original procedural identity system", True, TEXT_PRIMARY)
    surface.blit(title, (32, 25))
    players = fetch_players(1, database)[:10]
    for index, person in enumerate(players):
        x, y = 35 + (index % 5) * 245, 95 + (index // 5) * 245
        draw_portrait(surface, pygame.Rect(x, y, 130, 130), person)
        label = get_font(13, True).render(person["name"], True, TEXT_PRIMARY)
        surface.blit(label, (x, y + 138))
        draw_team_logo(surface, (x + 184, y + 65), 92, f"Club {index + 1}", f"C{index + 1}")
    pygame.image.save(surface, ROOT / "artifacts" / "final-identities.png")


def main() -> None:
    pygame.init(); (ROOT / "artifacts").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / "audit.db"; initialise_database(database)
        render_screen(DashboardScreen, "dashboard", (1280, 720), database)
        render_screen(FacilitiesScreen, "hq", (1280, 720), database)
        render_screen(SelectionScreen, "selection", (1280, 720), database)
        render_screen(TrainingScreen, "training", (1280, 720), database)
        render_screen(TransfersScreen, "market", (1280, 720), database)
        # The production app uses a 1920x1080 SDL logical canvas at 4K.  This
        # mirrors the real high-DPI path and checks the exact 2x presentation.
        render_screen(DashboardScreen, "dashboard", (1920, 1080), database, (3840, 2160))
        render_screen(FacilitiesScreen, "hq", (1920, 1080), database, (3840, 2160))
        render_identity_sheet(database)
    pygame.quit()


if __name__ == "__main__": main()
