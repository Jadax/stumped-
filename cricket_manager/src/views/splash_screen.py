"""Professional launch splash used while the real game data is initialised."""
from __future__ import annotations

import math
import os
import time
from typing import Final

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from src.views.theme import (BACKGROUND, BORDER, CARD, GREEN, GREEN_LIGHT,
                             GOLD, PANEL, WHITE, MUTED, get_font)


class SplashCancelled(RuntimeError):
    """Raised when the player closes the application during startup."""


class SplashScreen:
    """Draw an animated, resolution-independent startup screen.

    ``set_progress`` animates between genuine bootstrap milestones. ``finish``
    enforces a short minimum display time and fades smoothly into the game.
    """

    def __init__(self, version: str | None = None, size: tuple[int, int] = (960, 540),
                 minimum_seconds: float = 3.0) -> None:
        pygame.init()
        pygame.display.set_caption("Stumped! — Starting")
        self.size = size
        self.surface = pygame.display.set_mode(size, pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        if version is None:
            from src.utilities.launcher import app_version
            version = app_version()
        self.version = version
        self.minimum_seconds = max(0.0, minimum_seconds)
        self.started_at = time.perf_counter()
        self.progress = 0.0
        self.message = "Starting"
        self._draw_frame()

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        return get_font(size, bold)

    def _events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                raise SplashCancelled("Startup cancelled")

    def _draw_logo_mark(self, centre: tuple[int, int]) -> None:
        """Draw a crisp ball-and-stumps mark without external assets."""
        x, y = centre
        for offset in (-20, 0, 20):
            pygame.draw.rect(self.surface, GOLD, (x + offset - 4, y - 48, 8, 90), border_radius=3)
        pygame.draw.rect(self.surface, GOLD, (x - 31, y - 57, 28, 7), border_radius=3)
        pygame.draw.rect(self.surface, GOLD, (x + 3, y - 57, 28, 7), border_radius=3)
        ball_centre = (x + 61, y - 3)
        pygame.draw.aacircle(self.surface, pygame.Color("#b42f35"), ball_centre, 25)
        pygame.draw.arc(self.surface, WHITE, (ball_centre[0] - 19, ball_centre[1] - 24, 30, 48),
                        -math.pi / 2, math.pi / 2, 2)

    def _draw_frame(self, opacity: int = 255) -> None:
        width, height = self.size
        self.surface.fill(BACKGROUND)
        # Subtle diagonal bands add depth while retaining the business UI look.
        overlay = pygame.Surface(self.size, pygame.SRCALPHA)
        for x in range(-height, width, 88):
            pygame.draw.polygon(overlay, (46, 125, 50, 10), [(x, height), (x + 210, 0),
                                (x + 274, 0), (x + 64, height)])
        self.surface.blit(overlay, (0, 0))
        panel = pygame.Rect(90, 68, width - 180, height - 136)
        pygame.draw.rect(self.surface, (0, 0, 0), panel.move(7, 9), border_radius=14)
        pygame.draw.rect(self.surface, PANEL, panel, border_radius=14)
        pygame.draw.rect(self.surface, BORDER, panel, 1, border_radius=14)
        self._draw_logo_mark((panel.centerx, panel.y + 95))

        title = self._font(64, True).render("STUMPED!", True, WHITE)
        self.surface.blit(title, title.get_rect(center=(panel.centerx, panel.y + 205)))
        tagline = self._font(18).render("THE COMPLETE CRICKET MANAGEMENT SIMULATION", True, GREEN_LIGHT)
        self.surface.blit(tagline, tagline.get_rect(center=(panel.centerx, panel.y + 254)))

        track = pygame.Rect(panel.x + 74, panel.bottom - 94, panel.width - 148, 14)
        pygame.draw.rect(self.surface, CARD, track, border_radius=7)
        fill_width = round(track.width * max(0.0, min(100.0, self.progress)) / 100)
        if fill_width:
            pygame.draw.rect(self.surface, GREEN, (track.x, track.y, fill_width, track.height), border_radius=7)
            shine = pygame.Rect(track.x + 2, track.y + 2, max(0, fill_width - 4), 3)
            if shine.width: pygame.draw.rect(self.surface, GREEN_LIGHT, shine, border_radius=2)

        dots = "." * (int((time.perf_counter() - self.started_at) * 2.5) % 4)
        status = self._font(15).render(f"{self.message}{dots}", True, MUTED)
        self.surface.blit(status, (track.x, track.y - 29))
        percent = self._font(15, True).render(f"{round(self.progress)}%", True, GOLD)
        self.surface.blit(percent, percent.get_rect(topright=(track.right, track.y - 29)))
        version = self._font(13).render(f"VERSION {self.version}", True, MUTED)
        self.surface.blit(version, version.get_rect(bottomright=(panel.right - 18, panel.bottom - 13)))

        if opacity < 255:
            fade = pygame.Surface(self.size)
            fade.fill(BACKGROUND); fade.set_alpha(255 - opacity); self.surface.blit(fade, (0, 0))
        pygame.display.flip()

    def set_progress(self, percent: int | float, message: str, animation_seconds: float = 0.22) -> None:
        """Animate to a real startup milestone while keeping Windows responsive."""
        target = max(self.progress, min(100.0, float(percent)))
        start = self.progress
        started = time.perf_counter()
        while True:
            self._events()
            elapsed = time.perf_counter() - started
            fraction = 1.0 if animation_seconds <= 0 else min(1.0, elapsed / animation_seconds)
            eased = 1 - (1 - fraction) ** 3
            self.progress = start + (target - start) * eased
            self.message = message
            self._draw_frame()
            self.clock.tick(60)
            if fraction >= 1: break

    def finish(self) -> None:
        """Hold until the minimum duration, then fade out over 450 ms."""
        self.set_progress(100, "Ready!", .25)
        while time.perf_counter() - self.started_at < self.minimum_seconds:
            self._events(); self._draw_frame(); self.clock.tick(60)
        fade_started = time.perf_counter()
        while True:
            self._events()
            fraction = min(1.0, (time.perf_counter() - fade_started) / .45)
            self._draw_frame(round(255 * (1 - fraction)))
            self.clock.tick(60)
            if fraction >= 1: break
