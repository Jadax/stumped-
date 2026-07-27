"""First-run guided tutorial card — shown once per matching screen visit."""
from __future__ import annotations

import pygame

from .button import Button, ButtonStyle
from .common import GOLD, MUTED, WHITE, text, wrap_text
from .modal import Modal


class OnboardingOverlay(Modal):
    def __init__(self, viewport: pygame.Rect, step: dict, step_number: int, total_steps: int):
        super().__init__(viewport, step["title"], (560, 280))
        self.step, self.step_number, self.total_steps = step, step_number, total_steps
        is_last = step_number == total_steps
        width, gap = 150, 10
        next_x = self.rect.right - 22 - width
        y = self.rect.bottom - 50
        self.next_button = Button(pygame.Rect(next_x, y, width, 32), "FINISH" if is_last else "NEXT", ButtonStyle.PRIMARY)
        self.skip_button = Button(pygame.Rect(self.rect.x + 22, y, 150, 32), "SKIP TUTORIAL", ButtonStyle.SECONDARY)

    def process_event(self, event: pygame.event.Event) -> str | None:
        if self.close_button.process_event(event) or self.skip_button.process_event(event):
            return "skip"
        if self.next_button.process_event(event):
            return "next"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        c = self.content_rect
        text(surface, f"STEP {self.step_number} OF {self.total_steps}", (c.x, c.y), 12, GOLD, bold=True)
        y = c.y + 30
        for line in wrap_text(self.step["description"], c.width, 16):
            text(surface, line, (c.x, y), 16, WHITE)
            y += 24
        self.next_button.draw(surface)
        self.skip_button.draw(surface)
