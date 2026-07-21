"""Screen foundation and shared visual helpers."""
from __future__ import annotations
from typing import Any, Callable
import pygame
import pygame_gui
from .widgets import Card
from .widgets.common import BG, MUTED, WHITE, text
from src.models.squad_metrics import estimated_value, group_average  # noqa: F401 - re-exported for ui/* callers


class BaseScreen:
    """Stable screen API with access to app-wide state and navigation."""
    title = "Screen"
    description = "Functionality will be added in a later development phase."
    dynamic = False

    def __init__(self, manager: pygame_gui.UIManager, content_rect: pygame.Rect, scale: float = 1.0,
                 context: dict[str, Any] | None = None, navigate: Callable[[str], None] | None = None):
        self.manager, self.content_rect, self.scale = manager, pygame.Rect(content_rect), scale
        self.context, self.navigate = context or {}, navigate
        self.root = None
        self.modal = None
        self.dirty = True
        self.build()

    def build(self) -> None:
        """Placeholder screens still use the full card design language."""
        margin = max(20, int(24 * self.scale))
        self.placeholder_card = Card(
            pygame.Rect(self.content_rect.x + margin, self.content_rect.y + 78,
                        self.content_rect.width - margin * 2, self.content_rect.height - 105),
            self.title, "OPERATIONS MODULE",
        )

    def process_event(self, _event: pygame.event.Event) -> None:
        pass

    def update(self, _time_delta: float) -> None:
        pass

    def mark_dirty(self) -> None:
        self.dirty = True

    def draw_header(self, surface: pygame.Surface, subtitle: str = "Cricket operations centre") -> None:
        text(surface, self.title, (self.content_rect.x + 25, self.content_rect.y + 18), 28, WHITE, bold=True)
        text(surface, subtitle, (self.content_rect.x + 27, self.content_rect.y + 50), 13, MUTED)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        self.draw_header(surface)
        self.placeholder_card.draw(surface)
        centre = self.placeholder_card.content_rect.center
        text(surface, f"{self.title} — Coming Soon", (centre[0], centre[1] - 12), 24, WHITE, bold=True, anchor="center")
        text(surface, self.description, (centre[0], centre[1] + 25), 15, MUTED, anchor="center")

    def kill(self) -> None:
        self.modal = None


