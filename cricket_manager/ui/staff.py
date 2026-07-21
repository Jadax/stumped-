"""Coaching, medical, and scouting staff roster."""
from __future__ import annotations

import pygame

from database import fetch_staff
from src.models.currency import format_money
from .shared_components import BaseScreen
from .widgets import Card, DataTable, StarRating, TabBar
from .widgets.datatable import Column
from .widgets.common import CARD_ALT, GOLD, MUTED, WHITE, text


class StaffScreen(BaseScreen):
    title = "Staff"
    GROUPS = ["Coaching", "Medical", "Scouting"]

    GROUP_DETAIL = {
        "Coaching": [("coaching", "Coaching"), ("man_management", "Man Management"),
                    ("working_with_youngsters", "Working With Youngsters")],
        "Medical": [("physiotherapy", "Physiotherapy"), ("sports_science", "Sports Science")],
        "Scouting": [("judging_ability", "Judging Ability"), ("judging_potential", "Judging Potential"),
                    ("adaptability", "Adaptability")],
    }

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.active_group = "Coaching"
        self.group_bar = TabBar(pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 70,
                                            self.content_rect.width - 36, 30), self.GROUPS, self.active_group)
        self.table_rect = pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 116,
                                      int((self.content_rect.width - 36) * .62),
                                      self.content_rect.height - 134)
        detail_x = self.table_rect.right + 12
        self.detail_rect = pygame.Rect(detail_x, self.table_rect.y,
                                       self.content_rect.right - 18 - detail_x, self.table_rect.height)
        self.table = DataTable(self.table_rect, self._columns(), [], 32)
        self.selected: dict | None = None
        self.refresh_rows()

    def _columns(self) -> list[Column]:
        return [Column("role", "Role", .26), Column("name", "Name", .28), Column("age", "Age", .1),
                Column("overall", "Rating", .12), Column("wage", "Wage", .12, "right",
                       lambda v: format_money(v, compact=True)),
                Column("contract_years_remaining", "Yrs", .12)]

    def refresh_rows(self) -> None:
        rows = fetch_staff(self.team_id, self.active_group, self.db)
        self.table.set_rows(rows)
        self.selected = rows[0] if rows else None

    def process_event(self, event: pygame.event.Event) -> None:
        chosen = self.group_bar.process_event(event)
        if chosen:
            self.active_group = chosen
            self.refresh_rows()
        selected = self.table.process_event(event)
        if selected:
            self.selected = selected

    def _draw_detail(self, surface: pygame.Surface) -> None:
        card = Card(self.detail_rect, "STAFF PROFILE")
        card.draw(surface)
        if not self.selected:
            text(surface, "No staff in this department.", (card.rect.centerx, card.rect.centery), 12,
                 MUTED, anchor="center")
            return
        member = self.selected
        x, y = card.rect.x + 18, card.rect.y + 54
        text(surface, member["name"], (x, y), 18, WHITE, bold=True); y += 26
        text(surface, f"{member['role']} • {member['age']} • {member['nationality']}", (x, y), 11, MUTED); y += 34
        StarRating(pygame.Rect(x, y, card.rect.width - 36, 20), member["overall"] * 5, "Overall").draw(surface)
        y += 34
        for key, label in self.GROUP_DETAIL[self.active_group]:
            value = member["attributes"].get(key, 10)
            text(surface, label, (x, y), 11, MUTED)
            track = pygame.Rect(x, y + 16, card.rect.width - 36, 6)
            pygame.draw.rect(surface, CARD_ALT, track, border_radius=3)
            pygame.draw.rect(surface, GOLD, (track.x, track.y, int(track.width * value / 20), 6), border_radius=3)
            text(surface, f"{value}/20", (track.right, y), 10, WHITE, bold=True, anchor="topright")
            y += 34
        y += 10
        text(surface, "CONTRACT", (x, y), 11, MUTED, bold=True); y += 22
        text(surface, f"{format_money(member['wage'])}/wk", (x, y), 13, GOLD, bold=True)
        text(surface, f"{member['contract_years_remaining']} years remaining", (card.rect.right - 18, y), 11,
             WHITE, anchor="topright")

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Coaches accelerate training, medics manage injuries, scouts judge talent")
        self.group_bar.draw(surface)
        Card(self.table_rect, f"{self.active_group.upper()} STAFF", f"{len(self.table.rows)} MEMBERS").draw(surface)
        self.table.draw(surface)
        self._draw_detail(surface)
        if self.context.get("toast"):
            text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52),
                 11, GOLD, anchor="topright")
