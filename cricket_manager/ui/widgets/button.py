"""Consistent primary, secondary, danger, and success buttons."""
from __future__ import annotations
from enum import Enum
import pygame
from .common import BG, BORDER, CARD, DIM, GOLD, GREEN, RED, WHITE, font, text
from src.views.theme import ACTION, BUTTON_RADIUS


class ButtonStyle(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"
    SUCCESS = "success"


class Button:
    # Test at Dusk hierarchy: PRIMARY is the signature cricket-ball red;
    # SUCCESS is the green confirm; DANGER renders as an outline (see draw).
    COLOURS = {ButtonStyle.PRIMARY: ACTION, ButtonStyle.SECONDARY: CARD,
               ButtonStyle.DANGER: BG, ButtonStyle.SUCCESS: GREEN}

    def __init__(self, rect: pygame.Rect, label: str, style: ButtonStyle = ButtonStyle.SECONDARY,
                 enabled: bool = True, selected: bool = False, tooltip: str | None = None):
        self.rect, self.label, self.style = pygame.Rect(rect), label, style
        self.enabled, self.selected, self.hovered = enabled, selected, False
        self.tooltip = tooltip or label.replace(":", " —").title()
        self.hover_started = 0

    def process_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.hovered
            self.hovered = self.rect.collidepoint(event.pos)
            if self.hovered and not was_hovered: self.hover_started = pygame.time.get_ticks()
        return bool(self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self.rect.collidepoint(event.pos))

    def draw(self, surface: pygame.Surface) -> None:
        colour = self.COLOURS[self.style]
        if not self.enabled:
            colour = DIM
        elif self.hovered:
            colour = colour.lerp(WHITE, .16)
        draw_rect = self.rect.inflate(2, 2) if self.hovered and self.enabled else self.rect
        if self.selected:
            pygame.draw.rect(surface, GOLD, draw_rect.inflate(4, 4), width=2, border_radius=BUTTON_RADIUS)
        pygame.draw.rect(surface, colour, draw_rect, border_radius=BUTTON_RADIUS)
        outline = RED if self.style == ButtonStyle.DANGER and self.enabled else BORDER.lerp(WHITE, .2)
        pygame.draw.rect(surface, outline, draw_rect, width=1, border_radius=BUTTON_RADIUS)
        label_colour = RED if self.style == ButtonStyle.DANGER and self.enabled else WHITE
        text(surface, self.label, draw_rect.center, 14, label_colour, bold=True, anchor="center")
        if self.tooltip and self.hovered and pygame.time.get_ticks() - self.hover_started >= 650:
            rendered = font(11).render(self.tooltip, True, WHITE)
            tip = pygame.Rect(self.rect.x, self.rect.bottom + 7, rendered.get_width() + 18, rendered.get_height() + 12)
            bounds = surface.get_rect()
            if tip.right > bounds.right - 6: tip.right = bounds.right - 6
            if tip.bottom > bounds.bottom - 6: tip.bottom = self.rect.y - 7
            pygame.draw.rect(surface, CARD, tip, border_radius=4)
            pygame.draw.rect(surface, GOLD, tip, 1, border_radius=3)
            surface.blit(rendered, rendered.get_rect(center=tip.center))
