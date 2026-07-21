"""Underline tab bar (docs/DESIGN.md §5): text tabs with a sliding red rail."""
from __future__ import annotations

import pygame

from .common import MUTED, WHITE, font, text
from src.views.theme import ACTION


class TabBar:
    """A horizontal row of text tabs with the signature-red active underline."""

    def __init__(self, rect: pygame.Rect, labels: list[str], active: str | None = None,
                 counts: dict[str, int] | None = None):
        self.rect = pygame.Rect(rect)
        self.labels = list(labels)
        self.active = active if active in self.labels else (self.labels[0] if self.labels else "")
        self.counts = counts or {}
        self.hovered: str | None = None
        self._zones: dict[str, pygame.Rect] = {}
        self._layout()

    def _layout(self) -> None:
        x = self.rect.x
        for label in self.labels:
            display = self._display(label)
            width = font(13, True).size(display)[0] + 26
            self._zones[label] = pygame.Rect(x, self.rect.y, width, self.rect.height)
            x += width

    def _display(self, label: str) -> str:
        count = self.counts.get(label)
        return f"{label.upper()}  {count}" if count else label.upper()

    def process_event(self, event: pygame.event.Event) -> str | None:
        """Return the newly-selected label, or None."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = next((l for l, z in self._zones.items() if z.collidepoint(event.pos)), None)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for label, zone in self._zones.items():
                if zone.collidepoint(event.pos) and label != self.active:
                    self.active = label
                    return label
        return None

    def draw(self, surface: pygame.Surface) -> None:
        for label, zone in self._zones.items():
            is_active = label == self.active
            colour = WHITE if is_active or label == self.hovered else MUTED
            text(surface, self._display(label), (zone.centerx, zone.centery - 1), 13, colour,
                 bold=is_active, anchor="center")
            if is_active:
                pygame.draw.rect(surface, ACTION, (zone.x + 8, zone.bottom - 3, zone.width - 16, 2))
