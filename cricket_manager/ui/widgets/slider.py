"""Step-based horizontal slider with mouse dragging."""
from __future__ import annotations
import pygame
from .common import BORDER, GOLD, GREEN, MUTED, WHITE, text


class Slider:
    def __init__(self, rect: pygame.Rect, label: str, minimum: float, maximum: float,
                 value: float, step: float = 1, formatter=None):
        self.rect, self.label = pygame.Rect(rect), label
        self.minimum, self.maximum, self.step = minimum, maximum, step
        self.value, self.dragging = value, False
        self.display_value = float(value)
        self.formatter = formatter

    def _set_from_x(self, x: int) -> None:
        fraction = max(0, min(1, (x - self.rect.x) / max(1, self.rect.width)))
        raw = self.minimum + fraction * (self.maximum - self.minimum)
        self.value = round(raw / self.step) * self.step
        self.value = max(self.minimum, min(self.maximum, self.value))

    def process_event(self, event: pygame.event.Event) -> bool:
        changed = False
        track = pygame.Rect(self.rect.x, self.rect.y + 27, self.rect.width, 18)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and track.collidepoint(event.pos):
            self.dragging, changed = True, True
            self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0]); changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        return changed

    def draw(self, surface: pygame.Surface) -> None:
        self.display_value += (float(self.value) - self.display_value) * .28
        text(surface, self.label, (self.rect.x, self.rect.y), 13, MUTED)
        shown = self.formatter(self.value) if self.formatter else f"{self.value:g}"
        text(surface, shown, (self.rect.right, self.rect.y), 14, GOLD, bold=True, anchor="topright")
        y = self.rect.y + 34
        pygame.draw.line(surface, BORDER, (self.rect.x, y), (self.rect.right, y), 4)
        fraction = (self.display_value - self.minimum) / max(1, self.maximum - self.minimum)
        knob_x = self.rect.x + int(fraction * self.rect.width)
        pygame.draw.line(surface, GREEN, (self.rect.x, y), (knob_x, y), 4)
        pygame.draw.aacircle(surface, WHITE, (knob_x, y), 10)
        pygame.draw.aacircle(surface, GREEN, (knob_x, y), 6)
