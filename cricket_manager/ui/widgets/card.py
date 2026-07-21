"""Card container with title rail, content inset, and subtle shadow."""
from __future__ import annotations
import pygame
from .common import CARD, BORDER, GREEN, MUTED, PANEL, clipped_text, text
from src.views.theme import ACCENT, CARD_RADIUS, HOVER, vertical_gradient


class Card:
    def __init__(self, rect: pygame.Rect, title: str = "", subtitle: str = "", footer: str = ""):
        self.rect = pygame.Rect(rect)
        self.title, self.subtitle, self.footer = title, subtitle, footer
        self.header_height = 43 if title else 12
        self.footer_height = 28 if footer else 10

    @property
    def content_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x + 14, self.rect.y + self.header_height + 8,
                           self.rect.width - 28, self.rect.height - self.header_height - self.footer_height - 14)

    def draw(self, surface: pygame.Surface) -> None:
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        shadow = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 112 if hovered else 77), shadow.get_rect(), border_radius=CARD_RADIUS)
        surface.blit(shadow, self.rect.move(0, 6 if hovered else 4))
        pygame.draw.rect(surface, CARD.lerp(HOVER, .18) if hovered else CARD, self.rect, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, BORDER.lerp(GREEN, .32) if hovered else BORDER, self.rect, width=1, border_radius=CARD_RADIUS)
        if self.title:
            gradient = vertical_gradient((self.rect.width, self.header_height), PANEL.lerp(ACCENT, .10), PANEL)
            header = pygame.Surface((self.rect.width, self.header_height), pygame.SRCALPHA)
            header.blit(gradient, (0, 0))
            mask = pygame.Surface((self.rect.width, self.header_height), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(),
                             border_top_left_radius=CARD_RADIUS, border_top_right_radius=CARD_RADIUS)
            header.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(header, (self.rect.x, self.rect.y))
            pygame.draw.rect(surface, GREEN, (self.rect.x, self.rect.y, 4, self.header_height))
            title_rect = text(surface, clipped_text(self.title, self.rect.width - 30, 15, True),
                              (self.rect.x + 15, self.rect.y + 12), 15, bold=True)
            if self.subtitle:
                available = self.rect.right - 12 - title_rect.right - 12
                if available >= 52:
                    label = clipped_text(self.subtitle, available, 12)
                    text(surface, label, (self.rect.right - 12, self.rect.y + 13), 12, MUTED, anchor="topright")
        if self.footer:
            pygame.draw.line(surface, BORDER, (self.rect.x + 12, self.rect.bottom - self.footer_height),
                             (self.rect.right - 12, self.rect.bottom - self.footer_height))
            text(surface, self.footer, (self.rect.x + 14, self.rect.bottom - 21), 12, MUTED)
