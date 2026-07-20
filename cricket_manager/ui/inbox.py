"""Priority-coloured Inbox and full-message viewer."""
from __future__ import annotations
import pygame
from database import fetch_inbox_messages, mark_inbox_read
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, DataTable, Modal
from .widgets.datatable import Column
from .widgets.common import GOLD, GREEN, MUTED, RED, WHITE, text, wrap_text


class MessageModal(Modal):
    def __init__(self, viewport: pygame.Rect, message: dict):
        super().__init__(viewport, message["title"], (760, 430)); self.message = message; self.action = None
        width, gap = 105, 8; x = self.rect.right - 22 - width * 4 - gap * 3; y = self.rect.bottom - 50
        specs = [("ACCEPT", ButtonStyle.PRIMARY), ("REJECT", ButtonStyle.DANGER),
                 ("VIEW", ButtonStyle.SUCCESS), ("DISMISS", ButtonStyle.SECONDARY)]
        self.action_buttons = []
        for label, style in specs:
            enabled = bool(message["action_required"]) if label in ("ACCEPT", "REJECT") else True
            self.action_buttons.append((label, Button(pygame.Rect(x, y, width, 32), label, style, enabled=enabled))); x += width + gap

    def process_event(self, event: pygame.event.Event) -> bool:
        for label, button in self.action_buttons:
            if button.process_event(event):
                self.action = label
                if label in ("ACCEPT", "REJECT", "DISMISS"): return True
        return super().process_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface); c = self.content_rect
        colour = RED if self.message["priority"] == "HIGH" else GOLD if self.message["priority"] == "MEDIUM" else MUTED
        icon = "!!!" if self.message["priority"] == "HIGH" else "!!" if self.message["priority"] == "MEDIUM" else "!"
        text(surface, f"{icon}  {self.message['priority']} PRIORITY", (c.x, c.y), 13, colour, bold=True)
        text(surface, self.message["timestamp"], (c.right, c.y), 12, MUTED, anchor="topright")
        y = c.y + 48
        for line in wrap_text(self.message["content"], c.width, 17):
            text(surface, line, (c.x, y), 17, WHITE); y += 27
        if self.message["action_required"]:
            text(surface, "ACTION REQUIRED", (c.x, c.bottom - 66), 13, GOLD, bold=True)
        if self.action == "VIEW": text(surface, "Attachment/details view placeholder", (c.x, c.bottom - 42), 11, GREEN)
        for _, button in self.action_buttons: button.draw(surface)


class InboxScreen(BaseScreen):
    title = "Inbox"

    def build(self) -> None:
        self.messages = fetch_inbox_messages(database_path=self.context["database_path"])
        rect = pygame.Rect(self.content_rect.x + 24, self.content_rect.y + 118,
                           self.content_rect.width - 48, self.content_rect.height - 145)
        cols = [Column("priority_icon", "Priority", .13), Column("timestamp", "Received", .2),
                Column("title", "Subject", .5), Column("action", "Status", .17)]
        rows = [dict(m, priority_icon="!!!" if m["priority"] == "HIGH" else "!!" if m["priority"] == "MEDIUM" else "!",
                     action="ACCEPT / REJECT" if m["action_required"] else "VIEW / DISMISS") for m in self.messages]
        self.table = DataTable(rect, cols, rows, 40, colour_func=self._colour)

    @staticmethod
    def _colour(key, value, row):
        if key == "priority_icon": return RED if row["priority"] == "HIGH" else GOLD if row["priority"] == "MEDIUM" else MUTED
        return None

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self.modal.process_event(event): self.modal = None
            return
        selected = self.table.process_event(event)
        if selected:
            mark_inbox_read(selected["id"], self.context["database_path"]); selected["read"] = 1
            self.modal = MessageModal(self.content_rect, selected)
            self.context["refresh_inbox"] = True

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Messages, reports and decisions from across the club")
        card = Card(pygame.Rect(self.content_rect.x + 24, self.content_rect.y + 76,
                                self.content_rect.width - 48, self.content_rect.height - 103), "MESSAGE CENTRE", f"{sum(not m['read'] for m in self.messages)} UNREAD")
        card.draw(surface); self.table.draw(surface)
        if self.modal: self.modal.draw(surface)
