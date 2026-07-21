"""Stumped! application entry point and production bootstrap.

This module owns the window, persistent navigation chrome, and modular screen
manager. Run it from any working directory with ``python main.py``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from typing import Type

from src.utilities.launcher import (create_recovery_save, end_session, get_launch_paths,
                                    prepare_environment, run_diagnostics)

LAUNCH_PATHS = get_launch_paths()
PROJECT_ROOT = LAUNCH_PATHS.resource_root
WRITABLE_ROOT = LAUNCH_PATHS.writable_root
CONFIG_PATH = LAUNCH_PATHS.config
THEME_PATH = PROJECT_ROOT / "ui" / "theme.json"
from src.utilities.launcher import app_version
GAME_VERSION = app_version()

from src.utilities.logger import install_exception_hooks, setup_logging, show_crash_dialog

LOGGER, ERROR_LOG_PATH = setup_logging(WRITABLE_ROOT / "logs")

# Keep pygame's support banner out of the commercial game's console output.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import pygame
    import pygame_gui
except ImportError as exc:  # Friendly error for first-time non-technical users.
    LOGGER.critical("Required game library is missing", exc_info=True)
    show_crash_dialog(exc, ERROR_LOG_PATH)
    raise SystemExit(
        "A required game library is missing. Open PowerShell in this folder and run:\n"
        "  python -m pip install -r requirements.txt\n"
        "Then run: python main.py"
    ) from exc

from database import fetch_players, get_team_summary, initialise_database, load_game, save_game, unread_inbox_count
from competition import CompetitionEngine
from src.controllers.audio_controller import AudioManager, get_audio_event_bus
from src.controllers.game_controller import GameController
from src.models.currency import format_money, set_active_currency
from src.steam_integration import SteamIntegration
from src.views.splash_screen import SplashCancelled, SplashScreen
from src.views.theme import FONT_PATH
from src.views.screens import (CareerTeamSelectionScreen, MainMenuScreen,
                               NewGameSetupScreen, WorldCupSetupScreen, HelpScreen)
from src.views.screens import TournamentSetupScreen
from ui.career import CareerScreen
from ui.dashboard import DashboardScreen
from ui.facilities import FacilitiesScreen
from ui.finances import FinancesScreen
from ui.match_view import MatchScreen
from ui.inbox import InboxScreen
from ui.pre_match import PreMatchScreen
from ui.selection import SelectionScreen
from ui.settings import SettingsScreen
from ui.shared_components import BaseScreen
from ui.squad import SquadScreen
from ui.training import TrainingScreen
from ui.transfers import TransfersScreen
from ui.youth import YouthScreen


SCREEN_CLASSES: dict[str, Type[BaseScreen]] = {
    "Main Menu": MainMenuScreen,
    "New Game Setup": NewGameSetupScreen,
    "Career Team Selection": CareerTeamSelectionScreen,
    "World Cup Setup": WorldCupSetupScreen,
    "Tournament Setup": TournamentSetupScreen,
    "Help": HelpScreen,
    "Dashboard": DashboardScreen,
    "Squad": SquadScreen,
    "Inbox": InboxScreen,
    "Selection": SelectionScreen,
    "Match": MatchScreen,
    "Transfers": TransfersScreen,
    "Career": CareerScreen,
    "Training": TrainingScreen,
    "Finances": FinancesScreen,
    "Youth Academy": YouthScreen,
    "Facilities": FacilitiesScreen,
    "Settings": SettingsScreen,
    "Pre-Match": PreMatchScreen,
}

STARTUP_SCREEN_NAMES = {"Main Menu", "New Game Setup", "Career Team Selection", "World Cup Setup", "Tournament Setup"}
NAV_SCREEN_NAMES = ["Dashboard", "Inbox", "Squad", "Selection", "Match", "Transfers", "Training",
                    "Finances", "Youth Academy", "Facilities", "Career", "Settings", "Help"]
# Grouped sidebar sections per the approved redesign (docs/DESIGN.md §3.4).
NAV_GROUPS = [("CLUB", ["Dashboard", "Inbox"]),
              ("SQUAD", ["Squad", "Selection", "Training", "Youth Academy"]),
              ("MATCH", ["Match"]),
              ("BUSINESS", ["Transfers", "Finances", "Facilities"]),
              ("WORLD", ["Career"]),
              ("SYSTEM", ["Settings", "Help"])]


def load_config() -> dict:
    """Load and lightly validate the human-editable application configuration."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read {CONFIG_PATH}: {exc}") from exc
    required = {"game_title", "database_path", "resolution", "minimum_resolution", "ui", "colours"}
    missing = required.difference(config)
    if missing:
        raise SystemExit(f"config.json is missing: {', '.join(sorted(missing))}")
    return config


def bootstrap_game(splash: SplashScreen) -> dict:
    """Load genuine startup dependencies while reporting each splash stage."""
    splash.set_progress(10, "Loading config")
    config = load_config()
    LOGGER.info(f"Starting Stumped! version {config.get('version', 'development')}")

    splash.set_progress(30, "Loading database")
    database_path = LAUNCH_PATHS.database
    initialise_database(database_path)
    game_data = load_game(database_path)

    splash.set_progress(50, "Loading teams")
    team = get_team_summary(game_data["user"]["current_team_id"], database_path)

    splash.set_progress(70, "Loading players")
    players = fetch_players(team["id"], database_path)

    splash.set_progress(90, "Initialising match engine")
    competition_engine = CompetitionEngine(database_path)
    competition_engine.ensure_season(date.fromisoformat(game_data["user"]["current_date"]).year)
    unread_count = unread_inbox_count(database_path)
    LOGGER.info(f"Bootstrap complete: {team['name']}, {len(players)} senior players")
    return {"config": config, "database_path": database_path, "game_data": game_data,
            "team": team, "players": players, "competition_engine": competition_engine,
            "unread_count": unread_count}


class ScreenManager:
    """Create exactly one content screen at a time and switch it cleanly."""

    def __init__(self, ui_manager: pygame_gui.UIManager, content_rect: pygame.Rect, scale: float,
                 context: dict, navigate):
        self.ui_manager = ui_manager
        self.content_rect = content_rect
        self.scale = scale
        self.context, self.navigate = context, navigate
        self.current_name = ""
        self.current_screen: BaseScreen | None = None
        self.cached_surface = pygame.Surface((content_rect.right, content_rect.bottom), pygame.SRCALPHA)
        self.dirty = True

    def show(self, screen_name: str) -> None:
        if screen_name not in SCREEN_CLASSES:
            raise KeyError(f"Unknown screen: {screen_name}")
        if self.current_screen is not None:
            self.current_screen.kill()
        self.current_name = screen_name
        self.current_screen = SCREEN_CLASSES[screen_name](self.ui_manager, self.content_rect, self.scale,
                                                          self.context, self.navigate)
        self.dirty = True

    def process_event(self, event: pygame.event.Event) -> None:
        if self.current_screen is not None:
            self.current_screen.process_event(event)
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                              pygame.MOUSEWHEEL, pygame.KEYDOWN, pygame.KEYUP):
                self.dirty = True

    def update(self, time_delta: float) -> None:
        if self.current_screen is not None:
            self.current_screen.update(time_delta)
            if self.current_screen.dynamic or self.current_screen.dirty:
                self.dirty = True

    def draw(self, surface: pygame.Surface) -> None:
        if self.current_screen is not None:
            if self.dirty:
                self.cached_surface.fill((0, 0, 0, 0))
                self.current_screen.draw(self.cached_surface)
                self.current_screen.dirty = False
                self.dirty = False
            surface.blit(self.cached_surface, (0, 0))


class CricketManagerApp:
    """Window lifecycle, responsive layout, global navigation, and main loop."""

    def __init__(self, bootstrap: dict | None = None) -> None:
        self.config = bootstrap["config"] if bootstrap else load_config()
        self.minimum_size = (
            int(self.config["minimum_resolution"]["width"]),
            int(self.config["minimum_resolution"]["height"]),
        )
        self.window_size = (
            max(self.minimum_size[0], int(self.config["resolution"]["width"])),
            max(self.minimum_size[1], int(self.config["resolution"]["height"])),
        )
        self.fullscreen = bool(self.config["resolution"].get("fullscreen", False))

        pygame.init()
        pygame.display.set_caption(self.config["game_title"])
        self.window = self._create_window()
        self.clock = pygame.time.Clock()
        # Register the bundled Inter face before loading pygame-gui's theme so
        # native widgets and hand-drawn screens share exactly one type system.
        self.ui_manager = pygame_gui.UIManager(self.window_size)
        if FONT_PATH.is_file():
            self.ui_manager.add_font_paths("inter", str(FONT_PATH), str(FONT_PATH))
        self.ui_manager.get_theme().load_theme(str(THEME_PATH))

        database_path = bootstrap["database_path"] if bootstrap else LAUNCH_PATHS.database
        if bootstrap:
            self.game_data, self.team = bootstrap["game_data"], bootstrap["team"]
            self.competition_engine = bootstrap["competition_engine"]
            players = bootstrap["players"]
        else:
            initialise_database(database_path)
            self.game_data = load_game(database_path)
            self.team = get_team_summary(self.game_data["user"]["current_team_id"], database_path)
            self.competition_engine = CompetitionEngine(database_path)
            self.competition_engine.ensure_season(date.fromisoformat(self.game_data["user"]["current_date"]).year)
            players = fetch_players(self.team["id"], database_path)
        saved_mode = self.game_data["state"].get("game_mode", "Career")
        set_active_currency(self.game_data["user"].get("currency", "GBP"))
        if saved_mode == "World Cup" and self.game_data["state"].get("national_team"):
            self.team = dict(self.team)
            self.team["name"] = self.game_data["state"]["national_team"]["name"]
        self.audio_manager = AudioManager()
        self.audio_manager.initialise(
            PROJECT_ROOT / "assets" / "audio",
            volume=int(self.game_data["user"].get("master_volume", self.config.get("gameplay", {}).get("master_volume", 70))),
            muted=not bool(self.game_data["user"].get("sound_on", 1)),
        )
        steam_config = self.config.get("steam", {})
        self.steam = SteamIntegration(WRITABLE_ROOT, steam_config.get("app_id"), steam_config.get("user_id"))
        self.steam.initialise()
        self.app_context = {
            "database_path": database_path,
            "team": self.team,
            "players": players,
            "selection": self.game_data["state"].get("selection", {}),
            "selected_player": None,
            "current_match": None,
            "current_date": self.game_data["user"]["current_date"],
            "user_settings": dict(self.game_data["user"]),
            "advance_day": self.advance_campaign_day,
            "apply_resolution": self.apply_resolution_setting,
            "competition_engine": self.competition_engine,
            "audio_manager": self.audio_manager,
            "event_bus": get_audio_event_bus(),
            "steam": self.steam,
            "refresh_campaign": self.refresh_campaign_context,
            "game_mode": saved_mode,
            "national_team": self.game_data["state"].get("national_team"),
            "world_cup": self.game_data["state"].get("world_cup"),
            "custom_tournament": self.game_data["state"].get("custom_tournament"),
            "new_game_setup": self.game_data["state"].get("new_game_setup", {}),
        }
        self.game_controller = GameController(self.app_context, self.set_active_screen, self.request_exit)
        self.app_context["game_controller"] = self.game_controller
        self.unread_count = bootstrap["unread_count"] if bootstrap else unread_inbox_count(database_path)

        self.running = True
        self.active_screen = "Main Menu"
        self.nav_buttons: dict[str, pygame_gui.elements.UIButton] = {}
        self.screen_manager: ScreenManager | None = None
        self.build_interface()

    def _create_window(self) -> pygame.Surface:
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        if self.fullscreen:
            desktop = pygame.display.get_desktop_sizes()[0]
            self.window_size = self._fullscreen_logical_size(desktop)
            flags |= pygame.SCALED
        return pygame.display.set_mode(self.window_size, flags)

    @staticmethod
    def _fullscreen_logical_size(desktop: tuple[int, int]) -> tuple[int, int]:
        """Choose a crisp, readable render canvas for high-DPI displays.

        SDL scales this logical surface to the monitor's native mode.  A 4K
        desktop therefore receives a polished 1920x1080 UI at exact 2x output
        instead of stretching card geometry while leaving text at 12 pixels.
        Lower-resolution monitors continue to render at native resolution.
        """
        width, height = desktop
        if width <= 1920 and height <= 1080:
            return desktop
        aspect = width / max(1, height)
        logical_width = 1920
        logical_height = round(logical_width / aspect)
        if logical_height > 1080:
            logical_height = 1080
            logical_width = round(logical_height * aspect)
        return max(1280, logical_width), max(720, logical_height)

    @property
    def scale(self) -> float:
        """Scale layout furniture while preserving space for core content."""
        return max(1.0, min(self.window_size[0] / 1280, self.window_size[1] / 720, 1.8))

    def build_interface(self) -> None:
        """Rebuild responsive chrome and current screen after display changes."""
        self.ui_manager.clear_and_reset()
        if hasattr(self, "app_context"):
            self.team = self.app_context.get("team", self.team)
        self.nav_buttons.clear()
        width, height = self.window_size
        if self.active_screen in STARTUP_SCREEN_NAMES:
            self.sidebar_width = 0
            self.screen_manager = ScreenManager(
                self.ui_manager, pygame.Rect(0, 0, width, height), self.scale,
                self.app_context, self.set_active_screen,
            )
            self.screen_manager.show(self.active_screen)
            return

        sidebar_width = int(self.config["ui"]["sidebar_width"] * self.scale)
        top_height = int(self.config["ui"]["top_bar_height"] * self.scale)

        sidebar = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, sidebar_width, height),
            manager=self.ui_manager,
            object_id="#sidebar",
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(8, 12, sidebar_width - 16, max(45, int(48 * self.scale))),
            text="CRICKET MANAGER",
            manager=self.ui_manager,
            container=sidebar,
            object_id="#brand",
        )

        nav_start = max(70, int(78 * self.scale))
        nav_gap = max(2, int(3 * self.scale))
        section_height = max(16, int(18 * self.scale))
        button_count = sum(len(names) for _, names in NAV_GROUPS)
        available_nav_height = max(420, height - nav_start - 66)
        fixed = len(NAV_GROUPS) * (section_height + 4) + nav_gap * (button_count - 1)
        button_height = max(28, min(int(40 * self.scale), (available_nav_height - fixed) // button_count))
        y = nav_start
        for section, names in NAV_GROUPS:
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(20, y, sidebar_width - 32, section_height),
                text=section, manager=self.ui_manager, container=sidebar,
                object_id="#nav_section",
            )
            y += section_height + 4
            for name in names:
                button = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(0, y, sidebar_width, button_height),
                    text=name, manager=self.ui_manager, container=sidebar,
                    object_id="#nav_button",
                )
                self.nav_buttons[name] = button
                y += button_height + nav_gap

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(18, height - 56, sidebar_width - 36, 28),
            text="UI FOUNDATION 2.14+",
            manager=self.ui_manager,
            container=sidebar,
            object_id="#subtitle",
        )

        top_bar = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(sidebar_width, 0, width - sidebar_width, top_height),
            manager=self.ui_manager,
            object_id="#top_bar",
        )
        usable_width = width - sidebar_width
        team_width = min(int(usable_width * 0.34), 390)
        current_date = self.game_data["user"]["current_date"]
        current = date.fromisoformat(current_date)
        season_day = max(1, (current - date(current.year, 4, 1)).days + 1)
        season_week = max(1, (season_day - 1) // 7 + 1)
        self.top_team_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(24, 3, team_width - 24, 29), text=self.team["name"],
            manager=self.ui_manager, container=top_bar, object_id="#top_primary",
        )
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(24, 29, team_width - 24, 25),
            text=f"Season 1  ·  Week {season_week}  ·  Day {season_day}  ·  {current.strftime('%b %d, %Y')}",
            manager=self.ui_manager, container=top_bar, object_id="#top_value",
        )
        self.top_cash_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(team_width + 8, 7, 185, top_height - 14),
            text=f"CASH  {format_money(self.team['cash'])}", manager=self.ui_manager,
            container=top_bar, object_id="#top_value",
        )
        progress_x = team_width + 200
        progress_width = max(90, usable_width - progress_x - 112)
        progress = self._season_progress(current_date)
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(progress_x, 4, progress_width, 25),
            text=f"SEASON  {int(progress * 100)}%",
            manager=self.ui_manager,
            container=top_bar,
            object_id="#top_value",
        )
        progress_track = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(progress_x, top_height - 22, progress_width, 9),
            manager=self.ui_manager,
            container=top_bar,
            object_id="#progress_track",
        )
        pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, max(2, int((progress_width - 4) * progress)), 5),
            manager=self.ui_manager,
            container=progress_track,
            object_id="#progress_fill",
        )
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(usable_width - 94, 12, 82, 36), text="SAVE",
            manager=self.ui_manager, container=top_bar, object_id="#nav_button",
        )
        # The context-aware Continue button: the game's primary loop device.
        self.continue_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(usable_width - 218, 12, 116, 36), text="CONTINUE ▸",
            manager=self.ui_manager, container=top_bar, object_id="#top_action",
        )

        content_rect = pygame.Rect(sidebar_width, top_height, width - sidebar_width, height - top_height)
        self.sidebar_width = sidebar_width
        self.screen_manager = ScreenManager(self.ui_manager, content_rect, self.scale,
                                            self.app_context, self.set_active_screen)
        self.set_active_screen(self.active_screen)

    @staticmethod
    def _season_progress(current_date: str) -> float:
        start = date.fromisoformat("2026-04-01")
        end = date.fromisoformat("2026-09-30")
        current = date.fromisoformat(current_date)
        return max(0.0, min(1.0, (current - start).days / (end - start).days))

    def set_active_screen(self, name: str) -> None:
        previous_startup = self.active_screen in STARTUP_SCREEN_NAMES
        target_startup = name in STARTUP_SCREEN_NAMES
        self.active_screen = name
        if previous_startup != target_startup:
            self.build_interface()
            return
        if hasattr(self, "app_context"):
            self.team = self.app_context.get("team", self.team)
            if hasattr(self, "top_team_label"): self.top_team_label.set_text(self.team["name"])
            if hasattr(self, "top_cash_label"): self.top_cash_label.set_text(f"CASH  {format_money(self.team['cash'])}")
        for button_name, button in self.nav_buttons.items():
            button.select() if button_name == name else button.unselect()
        if self.screen_manager is not None:
            self.screen_manager.show(name)

    def request_exit(self) -> None:
        """Allow startup screens to request a normal, auto-saving shutdown."""
        self.running = False

    def refresh_campaign_context(self) -> None:
        """Reload the selected club and shared save data after world setup."""
        self.game_data = load_game(self.app_context["database_path"])
        self.team = get_team_summary(self.game_data["user"]["current_team_id"], self.app_context["database_path"])
        self.app_context.update({"team": self.team, "players": fetch_players(self.team["id"], self.app_context["database_path"]),
                                 "current_date": self.game_data["user"]["current_date"],
                                 "user_settings": dict(self.game_data["user"])})

    def advance_campaign_day(self) -> dict:
        """Run one complete calendar day and refresh shared application state."""
        events = self.competition_engine.advance_day(auto_sim_user=False)
        self.game_data = load_game(self.app_context["database_path"])
        self.team = get_team_summary(self.game_data["user"]["current_team_id"], self.app_context["database_path"])
        self.app_context.update({"team": self.team, "players": fetch_players(self.team["id"], self.app_context["database_path"]),
                                 "current_date": events["date"], "user_settings": dict(self.game_data["user"])})
        message = f"Advanced to {events['date']}"
        if events.get("user_fixture"): message += " • Match day"
        self.app_context["toast"] = message
        frequency = self.game_data["user"].get("auto_save_frequency", "Monthly")
        if frequency == "Monthly" and date.fromisoformat(events["date"]).day == 1:
            save_game({"selection": self.app_context.get("selection", {})}, self.app_context["database_path"])
        self.build_interface()
        return events

    def apply_resolution_setting(self, value: str) -> None:
        """Recreate the display immediately after Settings is saved."""
        if value == "Fullscreen":
            self.fullscreen = True
            desktop = pygame.display.get_desktop_sizes()[0]
            self.window_size = self._fullscreen_logical_size(desktop)
            self.window = pygame.display.set_mode(self.window_size, pygame.FULLSCREEN | pygame.SCALED)
        else:
            self.fullscreen = False
            width, height = (int(part) for part in value.lower().split("x"))
            self.window_size = (max(width, self.minimum_size[0]), max(height, self.minimum_size[1]))
            self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.ui_manager.set_window_resolution(self.window_size)
        self.build_interface()

    def draw_notification_badge(self) -> None:
        """Draw Inbox's unread count above Pygame-GUI's sidebar widgets."""
        if self.app_context.pop("refresh_inbox", False):
            self.unread_count = unread_inbox_count(self.app_context["database_path"])
        if not self.unread_count or "Inbox" not in self.nav_buttons:
            return
        button = self.nav_buttons["Inbox"]
        rect = button.get_abs_rect()
        centre = (rect.right - 18, rect.centery)
        pygame.draw.circle(self.window, pygame.Color("#d64545"), centre, 10)
        from src.views.theme import get_font
        badge_font = get_font(11, bold=True)
        rendered = badge_font.render(str(min(99, self.unread_count)), True, pygame.Color("white"))
        self.window.blit(rendered, rendered.get_rect(center=centre))

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            desktop = pygame.display.get_desktop_sizes()[0]
            self.window_size = self._fullscreen_logical_size(desktop)
            self.window = pygame.display.set_mode(self.window_size, pygame.FULLSCREEN | pygame.SCALED)
        else:
            configured = self.config["resolution"]
            self.window_size = (int(configured["width"]), int(configured["height"]))
            self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.ui_manager.set_window_resolution(self.window_size)
        self.build_interface()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                if self.active_screen == "New Game Setup":
                    self.set_active_screen("Main Menu")
                    return
                if self.active_screen in {"Career Team Selection", "World Cup Setup", "Tournament Setup"}:
                    self.set_active_screen("New Game Setup")
                    return
                if self.active_screen == "Help":
                    self.set_active_screen(self.app_context.pop("help_return", "Dashboard"))
                    return
                current = self.screen_manager.current_screen if self.screen_manager else None
                if self.active_screen == "Main Menu" and getattr(current, "panel", None):
                    # The menu screen consumes Escape to close its information panel.
                    pass
                elif self.fullscreen:
                    self.toggle_fullscreen()
                else:
                    self.running = False
        elif event.type == pygame.WINDOWRESIZED and not self.fullscreen:
            new_size = (max(event.x, self.minimum_size[0]), max(event.y, self.minimum_size[1]))
            if new_size != self.window_size:
                self.window_size = new_size
                self.window = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
                self.ui_manager.set_window_resolution(self.window_size)
                self.build_interface()
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == getattr(self, "continue_button", None):
                events = self.advance_campaign_day()
                if events.get("user_fixture"):
                    self.set_active_screen("Pre-Match")
                return
            if event.ui_element == getattr(self, "save_button", None):
                save_game({"selection": self.app_context.get("selection", {}),
                           "current_match_ui": self.app_context.get("match_state", {})},
                          self.app_context["database_path"])
                self.app_context["toast"] = "Game saved"
                self.steam.cloud_save(self.app_context["database_path"])
                return
            for name, button in self.nav_buttons.items():
                if event.ui_element == button:
                    self.set_active_screen(name)
                    break

        if self.screen_manager is not None:
            self.screen_manager.process_event(event)

    def run(self) -> None:
        target_fps = int(self.config["ui"].get("target_fps", 60))
        background = pygame.Color(self.config["colours"]["background"])
        while self.running:
            time_delta = self.clock.tick(target_fps) / 1000.0
            for event in pygame.event.get():
                # Pygame-GUI must see input before application-level reactions.
                self.ui_manager.process_events(event)
                self.handle_event(event)

            if self.screen_manager is not None:
                self.screen_manager.update(time_delta)
            self.ui_manager.update(time_delta)
            self.window.fill(background)
            if self.screen_manager is not None:
                self.screen_manager.draw(self.window)
            self.ui_manager.draw_ui(self.window)
            self.draw_notification_badge()
            pygame.display.update()

        save_game({"selection": self.app_context.get("selection", {}),
                   "current_match_ui": self.app_context.get("match_state", {})},
                  self.app_context["database_path"])
        self.audio_manager.shutdown()
        self.steam.cloud_save(self.app_context["database_path"])
        self.steam.shutdown()
        pygame.quit()


def main() -> int:
    """Show startup progress, run the game, and report fatal errors cleanly."""
    if "--diagnostics" in sys.argv:
        return 0 if run_diagnostics(LAUNCH_PATHS) else 1
    install_exception_hooks(LOGGER, ERROR_LOG_PATH)
    launch_state = None
    try:
        launch_state = prepare_environment(LAUNCH_PATHS)
        splash = SplashScreen(version=GAME_VERSION)
        bootstrap = bootstrap_game(splash)
        splash.finish()
        CricketManagerApp(bootstrap).run()
        end_session(launch_state, clean=True)
        LOGGER.info("Application closed normally")
    except SplashCancelled:
        pygame.quit()
        if launch_state: end_session(launch_state, clean=True)
        LOGGER.info("Startup cancelled by user")
        return 0
    except KeyboardInterrupt:
        pygame.quit()
        if launch_state: end_session(launch_state, clean=True)
        LOGGER.info("Application interrupted by user")
        return 0
    except BaseException as exc:
        LOGGER.critical("Fatal application error", exc_info=True)
        if launch_state:
            create_recovery_save(launch_state.paths.database, launch_state.paths.recovery)
            end_session(launch_state, clean=False)
        pygame.quit()
        show_crash_dialog(exc, ERROR_LOG_PATH)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
