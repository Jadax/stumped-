"""Coaching, medical, and scouting staff: roster, profiles, and the market."""
from __future__ import annotations

import pygame

from database import (browse_staff_market, fetch_staff, make_staff_offer, resolve_staff_offer,
                      sell_staff_member)
from src.models.currency import format_money
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, DataTable, StarRating, TabBar
from .widgets.datatable import Column
from .widgets.common import CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, text


class StaffScreen(BaseScreen):
    title = "Staff"
    GROUPS = ["Coaching", "Medical", "Scouting"]
    MARKET_FILTERS = ["All"] + GROUPS
    MODES = ["Roster", "Market"]

    GROUP_DETAIL = {
        "Coaching": [("coaching", "Coaching"), ("man_management", "Man Management"),
                    ("working_with_youngsters", "Working With Youngsters")],
        "Medical": [("physiotherapy", "Physiotherapy"), ("sports_science", "Sports Science")],
        "Scouting": [("judging_ability", "Judging Ability"), ("judging_potential", "Judging Potential"),
                    ("adaptability", "Adaptability")],
    }

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.mode = "Roster"
        self.active_group = "Coaching"
        self.market_filter = "All"
        self.mode_bar = TabBar(pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 70, 220, 30), self.MODES, self.mode)
        self.group_bar = TabBar(pygame.Rect(self.content_rect.x + 250, self.content_rect.y + 70,
                                            self.content_rect.width - 268, 30), self.GROUPS, self.active_group)
        self.table_rect = pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 116,
                                      int((self.content_rect.width - 36) * .62),
                                      self.content_rect.height - 134)
        detail_x = self.table_rect.right + 12
        self.detail_rect = pygame.Rect(detail_x, self.table_rect.y,
                                       self.content_rect.right - 18 - detail_x, self.table_rect.height)
        self.table = DataTable(self.table_rect, self._roster_columns(), [], 32)
        self.selected: dict | None = None
        self.action_button = Button(pygame.Rect(0, 0, 160, 30), "SIGN", ButtonStyle.SUCCESS)
        self.action_button.rect.bottomright = (self.detail_rect.right - 18, self.detail_rect.bottom - 18)
        self.refresh_rows()

    def _roster_columns(self) -> list[Column]:
        return [Column("role", "Role", .26), Column("name", "Name", .28), Column("age", "Age", .1),
                Column("overall", "Rating", .12), Column("wage", "Wage", .12, "right",
                       lambda v: format_money(v, compact=True)),
                Column("contract_years_remaining", "Yrs", .12)]

    def _market_columns(self) -> list[Column]:
        return [Column("role", "Role", .2), Column("name", "Name", .2), Column("club_name", "Club", .18),
                Column("age", "Age", .07), Column("overall", "Rating", .1),
                Column("fee", "Fee", .15, "right", lambda v: format_money(v, compact=True)),
                Column("wage", "Wage", .1, "right", lambda v: format_money(v, compact=True))]

    def refresh_rows(self) -> None:
        if self.mode == "Roster":
            rows = fetch_staff(self.team_id, self.active_group, self.db)
            self.table = DataTable(self.table_rect, self._roster_columns(), rows, 32)
        else:
            rows = browse_staff_market(self.market_filter, self.team_id, 40, self.db)
            self.table = DataTable(self.table_rect, self._market_columns(), rows, 32)
        self.selected = rows[0] if rows else None

    def process_event(self, event: pygame.event.Event) -> None:
        chosen_mode = self.mode_bar.process_event(event)
        if chosen_mode:
            self.mode = chosen_mode
            labels = self.GROUPS if self.mode == "Roster" else self.MARKET_FILTERS
            active = self.active_group if self.mode == "Roster" else self.market_filter
            self.group_bar = TabBar(self.group_bar.rect, labels, active)
            self.refresh_rows()
        if self.mode == "Roster":
            chosen = self.group_bar.process_event(event)
            if chosen:
                self.active_group = chosen
                self.refresh_rows()
        else:
            chosen = self.group_bar.process_event(event)
            if chosen and chosen in self.MARKET_FILTERS:
                self.market_filter = chosen
                self.refresh_rows()
        selected = self.table.process_event(event)
        if selected:
            self.selected = selected
        if self.action_button.process_event(event) and self.selected:
            self._act_on_selected()

    def _act_on_selected(self) -> None:
        member = self.selected
        if self.mode == "Market":
            offer_id = make_staff_offer(member["id"], member["team_id"], self.team_id, member["fee"],
                                        member["wage"], self.context.get("current_date", "2026-04-01"), self.db)
            if resolve_staff_offer(offer_id, True, self.db):
                self.context["toast"] = f"Signed {member['name']} for {format_money(member['fee'], compact=True)}"
                self.refresh_rows()
            else:
                self.context["toast"] = "Insufficient funds for that transfer."
        else:
            fee = sell_staff_member(member["id"], self.db)
            if fee:
                self.context["toast"] = f"Sold {member['name']} for {format_money(fee, compact=True)}"
                self.refresh_rows()

    def _draw_detail(self, surface: pygame.Surface) -> None:
        card = Card(self.detail_rect, "STAFF PROFILE" if self.mode == "Roster" else "MARKET LISTING")
        card.draw(surface)
        if not self.selected:
            text(surface, "No staff to show.", (card.rect.centerx, card.rect.centery), 12, MUTED, anchor="center")
            return
        member = self.selected
        detail_group = member.get("group_name", self.active_group)
        x, y = card.rect.x + 18, card.rect.y + 54
        text(surface, member["name"], (x, y), 18, WHITE, bold=True); y += 26
        text(surface, f"{member['role']} • {member['age']} • {member['nationality']}", (x, y), 11, MUTED); y += 34
        StarRating(pygame.Rect(x, y, card.rect.width - 36, 20), member["overall"] * 5, "Overall").draw(surface)
        y += 34
        for key, label in self.GROUP_DETAIL.get(detail_group, []):
            value = member["attributes"].get(key, 10)
            text(surface, label, (x, y), 11, MUTED)
            track = pygame.Rect(x, y + 16, card.rect.width - 36, 6)
            pygame.draw.rect(surface, CARD_ALT, track, border_radius=3)
            pygame.draw.rect(surface, GOLD, (track.x, track.y, int(track.width * value / 20), 6), border_radius=3)
            text(surface, f"{value}/20", (track.right, y), 10, WHITE, bold=True, anchor="topright")
            y += 34
        y += 10
        if self.mode == "Market":
            text(surface, "TRANSFER FEE", (x, y), 11, MUTED, bold=True); y += 22
            text(surface, format_money(member["fee"]), (x, y), 15, GOLD, bold=True)
            text(surface, f"{format_money(member['wage'])}/wk wage", (card.rect.right - 18, y), 11,
                 WHITE, anchor="topright")
            self.action_button.label = "SIGN"
        else:
            text(surface, "CONTRACT", (x, y), 11, MUTED, bold=True); y += 22
            text(surface, f"{format_money(member['wage'])}/wk", (x, y), 13, GOLD, bold=True)
            text(surface, f"{member['contract_years_remaining']} years remaining", (card.rect.right - 18, y), 11,
                 WHITE, anchor="topright")
            self.action_button.label = "RELEASE / SELL"
        self.action_button.style = ButtonStyle.SUCCESS if self.mode == "Market" else ButtonStyle.DANGER

    def draw(self, surface: pygame.Surface) -> None:
        subtitle = ("Coaches accelerate training, medics manage injuries, scouts judge talent"
                   if self.mode == "Roster" else "Browse and sign staff from other clubs")
        self.draw_header(surface, subtitle)
        self.mode_bar.draw(surface)
        self.group_bar.draw(surface)
        label = f"{self.active_group.upper()} STAFF" if self.mode == "Roster" else f"MARKET — {self.market_filter.upper()}"
        Card(self.table_rect, label, f"{len(self.table.rows)} LISTED").draw(surface)
        self.table.draw(surface)
        self._draw_detail(surface)
        if self.selected:
            self.action_button.draw(surface)
        if self.context.get("toast"):
            text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52),
                 11, GOLD, anchor="topright")
