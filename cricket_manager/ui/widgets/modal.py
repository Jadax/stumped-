"""Modal overlay with a dimmed backdrop, close control, and scroll state."""
from __future__ import annotations
import pygame
from .button import Button, ButtonStyle
from .common import BORDER, PANEL, WHITE, text


class Modal:
    def __init__(self, viewport: pygame.Rect, title: str, size: tuple[int, int] | None = None):
        self.viewport, self.title = pygame.Rect(viewport), title
        width = min(viewport.width - 60, size[0] if size else 980)
        height = min(viewport.height - 40, size[1] if size else 610)
        self.rect = pygame.Rect(0, 0, width, height); self.rect.center = viewport.center
        self.close_button = Button(pygame.Rect(self.rect.right - 45, self.rect.y + 10, 32, 28), "×", ButtonStyle.DANGER)
        self.scroll = 0
        self.max_scroll = 0
        self.dragging_scrollbar = False
        self.opened_at = pygame.time.get_ticks()

    @property
    def content_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x + 22, self.rect.y + 58, self.rect.width - 44, self.rect.height - 82)

    def process_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.rect.collidepoint(event.pos):
            return True
        if event.type == pygame.MOUSEWHEEL and self.content_rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(self.max_scroll, self.scroll - event.y * 32))
        track = pygame.Rect(self.rect.right - 12, self.content_rect.y, 11, self.content_rect.height)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.max_scroll and track.collidepoint(event.pos):
            self.dragging_scrollbar = True; self._scroll_from_y(event.pos[1]); return False
        if event.type == pygame.MOUSEMOTION and self.dragging_scrollbar: self._scroll_from_y(event.pos[1])
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.dragging_scrollbar = False
        return self.close_button.process_event(event)

    def _scroll_from_y(self, y: int) -> None:
        track = pygame.Rect(self.rect.right - 8, self.content_rect.y, 3, self.content_rect.height)
        fraction = max(0, min(1, (y - track.y) / max(1, track.height)))
        self.scroll = round(fraction * self.max_scroll)

    def draw(self, surface: pygame.Surface) -> None:
        progress = max(0.0, min(1.0, (pygame.time.get_ticks() - self.opened_at) / 200))
        veil = pygame.Surface(surface.get_size(), pygame.SRCALPHA); veil.fill((0, 0, 0, round(185 * progress))); surface.blit(veil, (0, 0))
        shadow = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, round(100 * progress)), shadow.get_rect(), border_radius=12)
        surface.blit(shadow, self.rect.move(0, 6))
        pygame.draw.rect(surface, PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, BORDER, self.rect, width=1, border_radius=12)
        pygame.draw.line(surface, BORDER, (self.rect.x, self.rect.y + 52), (self.rect.right, self.rect.y + 52))
        text(surface, self.title.upper(), (self.rect.x + 22, self.rect.y + 17), 18, WHITE, bold=True)
        if self.max_scroll:
            track = pygame.Rect(self.rect.right - 8, self.content_rect.y, 3, self.content_rect.height)
            pygame.draw.rect(surface, BORDER, track)
            thumb_height = max(24, int(track.height * track.height / (track.height + self.max_scroll)))
            thumb_y = track.y + int((track.height - thumb_height) * self.scroll / self.max_scroll)
            from .common import GREEN
            pygame.draw.rect(surface, GREEN, (track.x, thumb_y, track.width, thumb_height))
        self.close_button.draw(surface)
