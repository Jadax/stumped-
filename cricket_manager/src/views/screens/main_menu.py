"""Professional full-window main menu for Stumped!."""
from __future__ import annotations

import pygame

from src.utilities.launcher import app_version

from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import BG, BORDER, CARD, GOLD, GREEN, MUTED, PANEL, WHITE, text, wrap_text


class MainMenuScreen(BaseScreen):
    """First interactive screen shown after the launch splash."""

    title = "Main Menu"
    dynamic = True

    def build(self) -> None:
        self.elapsed = 0.0
        self.panel: str | None = None
        self.buttons: dict[str, Button] = {}
        self._layout()

    def _layout(self) -> None:
        width, height = self.content_rect.size
        scale = max(1.0, min(width / 1280, height / 720, 1.65))
        menu_w = int(330 * scale)
        button_h = int(48 * scale)
        gap = int(10 * scale)
        x = self.content_rect.x + int(82 * scale)
        y = self.content_rect.y + int(250 * scale)
        specs = [
            ("New Game", ButtonStyle.PRIMARY), ("Load Game", ButtonStyle.SUCCESS),
            ("Settings", ButtonStyle.SECONDARY), ("Help", ButtonStyle.SECONDARY),
            ("Credits", ButtonStyle.SECONDARY), ("Exit", ButtonStyle.DANGER),
        ]
        self.buttons = {
            label: Button(pygame.Rect(x, y + index * (button_h + gap), menu_w, button_h), label.upper(), style)
            for index, (label, style) in enumerate(specs)
        }
        overlay_w = min(int(620 * scale), width - int(120 * scale))
        overlay_h = min(int(410 * scale), height - int(110 * scale))
        self.overlay_card = Card(
            pygame.Rect(self.content_rect.centerx - overlay_w // 2,
                        self.content_rect.centery - overlay_h // 2, overlay_w, overlay_h),
            "", "",
        )
        self.close_button = Button(
            pygame.Rect(self.overlay_card.rect.right - int(132 * scale),
                        self.overlay_card.rect.bottom - int(58 * scale), int(108 * scale), int(36 * scale)),
            "CLOSE", ButtonStyle.PRIMARY,
        )

    def process_event(self, event: pygame.event.Event) -> None:
        if self.panel:
            if self.close_button.process_event(event) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                self.panel = None
                self.mark_dirty()
            return
        for label, button in self.buttons.items():
            if not button.process_event(event):
                continue
            controller = self.context["game_controller"]
            if label == "New Game":
                controller.begin_new_game()
            elif label == "Load Game":
                controller.load_existing_game()
            elif label == "Help":
                self.context["help_return"] = "Main Menu"
                self.navigate("Help")
            elif label in {"Settings", "Credits"}:
                self.panel = label
                self.mark_dirty()
            elif label == "Exit":
                controller.request_exit()

    def update(self, time_delta: float) -> None:
        self.elapsed += time_delta
        self.dirty = True

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_background(surface)
        s = max(1.0, min(self.content_rect.width / 1280, self.content_rect.height / 720, 1.65))
        left = self.content_rect.x + int(82 * s)
        text(surface, "STUMPED!", (left, self.content_rect.y + int(82 * s)), int(62 * s), WHITE, True)
        pygame.draw.rect(surface, GOLD, (left, self.content_rect.y + int(158 * s), int(190 * s), int(5 * s)))
        text(surface, "CRICKET MANAGEMENT, BALL BY BALL", (left, self.content_rect.y + int(177 * s)),
             int(16 * s), MUTED, True)
        text(surface, "Build a dynasty. Read the conditions. Own every decision.",
             (left, self.content_rect.y + int(208 * s)), int(14 * s), WHITE)

        for button in self.buttons.values():
            button.draw(surface)

        self._draw_feature_panel(surface, s)
        text(surface, f"v{app_version()}  •  F11 Fullscreen", (self.content_rect.right - int(30 * s),
             self.content_rect.bottom - int(26 * s)), int(12 * s), MUTED, anchor="bottomright")
        if self.panel:
            self._draw_overlay(surface, s)

    def _draw_background(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        for y in range(self.content_rect.top, self.content_rect.bottom, 8):
            ratio = (y - self.content_rect.top) / max(1, self.content_rect.height)
            colour = pygame.Color(int(26 + 7 * ratio), int(26 + 10 * ratio), int(26 + 7 * ratio))
            pygame.draw.rect(surface, colour, (self.content_rect.x, y, self.content_rect.width, 8))
        # Original geometric cricket motif: pitch, crease, ball and seam.
        cx = self.content_rect.x + int(self.content_rect.width * .75)
        cy = self.content_rect.centery
        pitch = pygame.Rect(cx - 95, cy - 245, 190, 490)
        pygame.draw.rect(surface, pygame.Color("#234529"), pitch, border_radius=20)
        pygame.draw.rect(surface, pygame.Color("#315f36"), pitch.inflate(-34, 0), border_radius=14)
        pygame.draw.line(surface, WHITE, (pitch.x + 18, pitch.y + 62), (pitch.right - 18, pitch.y + 62), 3)
        pygame.draw.line(surface, WHITE, (pitch.x + 18, pitch.bottom - 62), (pitch.right - 18, pitch.bottom - 62), 3)
        ball_y = cy + int(22 * pygame.math.Vector2(1, 0).rotate(self.elapsed * 75).y)
        pygame.draw.circle(surface, pygame.Color("#a62e2e"), (cx + 180, ball_y), 42)
        pygame.draw.arc(surface, WHITE, (cx + 154, ball_y - 39, 52, 78), -1.1, 1.1, 3)
        pygame.draw.arc(surface, WHITE, (cx + 154, ball_y - 39, 52, 78), 2.05, 4.2, 3)

    def _draw_feature_panel(self, surface: pygame.Surface, scale: float) -> None:
        x = self.content_rect.x + int(self.content_rect.width * .52)
        y = self.content_rect.y + int(94 * scale)
        w = min(int(320 * scale), self.content_rect.right - x - int(45 * scale))
        pygame.draw.rect(surface, (20, 20, 20, 205), (x, y, w, int(150 * scale)), border_radius=7)
        pygame.draw.rect(surface, BORDER, (x, y, w, int(150 * scale)), 1, border_radius=7)
        text(surface, "THE MANAGER'S GAME", (x + 18, y + 17), int(17 * scale), GOLD, True)
        points = ("Three authentic match formats", "Deep careers and club building", "Live tactical decisions")
        for index, point in enumerate(points):
            yy = y + int((55 + index * 28) * scale)
            pygame.draw.circle(surface, GREEN, (x + 21, yy + 6), 4)
            text(surface, point, (x + 36, yy), int(13 * scale), WHITE)

    def _draw_overlay(self, surface: pygame.Surface, scale: float) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 190))
        surface.blit(shade, (0, 0))
        self.overlay_card.draw(surface)
        rect = self.overlay_card.rect
        text(surface, self.panel.upper(), (rect.x + 28, rect.y + 25), int(24 * scale), GOLD, True)
        pygame.draw.line(surface, BORDER, (rect.x + 25, rect.y + 66), (rect.right - 25, rect.y + 66), 1)
        if self.panel == "Settings":
            lines = ["Full settings remain available inside every loaded career.",
                     "F11 toggles fullscreen at any time.",
                     "Match crowd audio follows your saved mute and volume preferences."]
        elif self.panel == "Help":
            lines = ["Start with NEW GAME to create your manager and choose a mode.",
                     "LOAD GAME opens the integrity-checked local career save.",
                     "A comprehensive guide is prepared in help_content.json and will receive its full screen next."]
        else:
            lines = ["STUMPED!", "Design and development: Stumped! development team.",
                     "Built with Python, Pygame, Pygame-GUI and SQLite.",
                     "All visual motifs are original geometric artwork. No real player photos or club logos are used."]
        y = rect.y + 90
        for line in lines:
            for wrapped in wrap_text(line, rect.width - 56, int(15 * scale)):
                text(surface, wrapped, (rect.x + 28, y), int(15 * scale), WHITE)
                y += int(25 * scale)
            y += int(10 * scale)
        self.close_button.draw(surface)

    def kill(self) -> None:
        self.panel = None
