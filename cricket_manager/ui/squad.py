"""Sortable, searchable squad management table with profile modals."""
from __future__ import annotations
import csv
from pathlib import Path
import pygame
from database import fetch_player_form, fetch_player_match_events, fetch_player_records
from src.models.currency import format_money
from .player_modals import PlayerComparisonModal, PlayerDetailModal
from .shared_components import BaseScreen, estimated_value, group_average
from .widgets import Button, ButtonStyle, Card, DataTable, QuickCard, TabBar
from .widgets.datatable import Column
from .widgets.common import BLUE, BORDER, DIM, GOLD, GREEN, MUTED, PANEL, WHITE, text


class SquadScreen(BaseScreen):
    title = "Squad"
    FILTERS = ["All", "Batsmen", "Bowlers", "All-Rounders", "Wicketkeepers", "U20", "Overseas"]

    def build(self) -> None:
        self.players = self.context["players"]
        self.filter_index, self.search, self.search_active = 0, "", False
        self.filter_button = Button(pygame.Rect(self.content_rect.x + 24, self.content_rect.y + 78, 170, 34), "FILTER: ALL", ButtonStyle.SECONDARY)
        self.export_button = Button(pygame.Rect(self.content_rect.right - 144, self.content_rect.y + 78, 120, 34), "EXPORT CSV", ButtonStyle.SUCCESS)
        self.search_rect = pygame.Rect(self.content_rect.x + 205, self.content_rect.y + 78, 260, 34)
        self.table_rect = pygame.Rect(self.content_rect.x + 24, self.content_rect.y + 152,
                                      self.content_rect.width - 48, self.content_rect.height - 179)
        self.view_tab = "Overview"
        self.view_bar = TabBar(pygame.Rect(self.content_rect.x + 24, self.content_rect.y + 120,
                                           self.content_rect.width - 48, 28),
                               list(self.COLUMN_SETS), self.view_tab)
        self.table = DataTable(self.table_rect, self.COLUMN_SETS[self.view_tab](), [], 35,
                               colour_func=self._cell_colour)
        self.refresh_rows()

    # Per-tab column sets (docs/DESIGN.md §4 Squad): one shared table, the
    # tab swaps which columns are shown.
    COLUMN_SETS = {
        "Overview": lambda: [Column("name", "Name", .18), Column("age", "Age", .05), Column("role", "Role", .12),
                             Column("bat", "Bat", .06), Column("bowl", "Bowl", .06), Column("field", "Field", .06),
                             Column("overall", "OVR", .065), Column("form", "Form", .065),
                             Column("fatigue", "Fatigue", .07),
                             Column("value", "Value", .1, "right", lambda v: format_money(v, compact=True)),
                             Column("contract_years_remaining", "Contract", .07),
                             Column("wage", "Wage", .09, "right", lambda v: format_money(v))],
        "Skills": lambda: [Column("name", "Name", .24), Column("role", "Role", .14),
                           Column("bat", "Batting", .105), Column("bowl", "Bowling", .105),
                           Column("field", "Fielding", .105), Column("mental_avg", "Mental", .105),
                           Column("overall", "OVR", .09), Column("potential", "POT", .09)],
        "Contracts": lambda: [Column("name", "Name", .24), Column("age", "Age", .07), Column("role", "Role", .14),
                              Column("value", "Value", .14, "right", lambda v: format_money(v, compact=True)),
                              Column("wage", "Wage", .14, "right", lambda v: format_money(v)),
                              Column("contract_years_remaining", "Years left", .12),
                              Column("overall", "OVR", .08)],
        "Planner": lambda: [Column("name", "Name", .22), Column("role", "Role", .13), Column("age", "Age", .06),
                            Column("season_now", "This season", .18), Column("season_next", "Next season", .18),
                            Column("season_after", "Season after", .18), Column("overall", "OVR", .05)],
    }

    # Contract status projected N seasons ahead purely from the annual
    # decrement counter (docs/UX_ROADMAP.md Squad Planner) — no calendar
    # maths needed since contract_years_remaining already ticks down once
    # per season rollover.
    @classmethod
    def _season_label(cls, years_remaining: int, seasons_ahead: int) -> str:
        remaining = years_remaining - seasons_ahead
        if remaining <= 0: return "Free agent"
        if remaining == 1: return "Expires this year"
        return "Contracted"

    @staticmethod
    def _cell_colour(key, value, _row):
        if key == "overall":
            return GOLD if value >= 90 else GREEN if value >= 80 else BLUE if value >= 70 else WHITE if value >= 60 else DIM
        if key in ("season_now", "season_next", "season_after"):
            return DIM if value == "Free agent" else GOLD if value == "Expires this year" else GREEN
        return None

    def refresh_rows(self) -> None:
        filter_name = self.FILTERS[self.filter_index]
        role_map = {"Batsmen": "Batsman", "Bowlers": "Bowler", "All-Rounders": "All-Rounder", "Wicketkeepers": "Wicketkeeper"}
        rows = []
        for player in self.players:
            if filter_name in role_map and player["role"] != role_map[filter_name]: continue
            if filter_name == "U20" and player["age"] >= 20: continue
            if filter_name == "Overseas" and player["nationality"] == "English": continue
            if self.search.lower() not in player["name"].lower(): continue
            years_left = player.get("contract_years_remaining", 0)
            rows.append(dict(player, bat=group_average(player, "batting"), bowl=group_average(player, "bowling"),
                             field=group_average(player, "fielding"), mental_avg=group_average(player, "mental"),
                             potential=player.get("potential", player.get("overall", 50)),
                             value=estimated_value(player),
                             season_now=self._season_label(years_left, 0),
                             season_next=self._season_label(years_left, 1),
                             season_after=self._season_label(years_left, 2)))
        self.table.set_rows(rows)

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            closed = self.modal.process_event(event)
            if isinstance(self.modal, PlayerDetailModal) and self.modal.open_comparison:
                candidate = self.modal.comparison_candidate
                self.modal = PlayerComparisonModal(self.content_rect, self.modal.player, candidate)
            elif closed: self.modal = None
            return
        if self.filter_button.process_event(event):
            self.filter_index = (self.filter_index + 1) % len(self.FILTERS)
            self.filter_button.label = f"FILTER: {self.FILTERS[self.filter_index].upper()}"; self.refresh_rows()
        if self.export_button.process_event(event): self.export_csv()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.search_active = self.search_rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: self.search = self.search[:-1]
            elif event.key == pygame.K_ESCAPE: self.search_active = False
            elif event.unicode and event.unicode.isprintable() and len(self.search) < 30: self.search += event.unicode
            self.refresh_rows()
        chosen = self.view_bar.process_event(event)
        if chosen:
            self.view_tab = chosen
            self.table = DataTable(self.table_rect, self.COLUMN_SETS[chosen](), [], 35,
                                   colour_func=self._cell_colour)
            self.refresh_rows()
        selected = self.table.process_event(event)
        if selected:
            selected["records"] = fetch_player_records(selected["id"], self.context["database_path"])
            selected["form_history"] = fetch_player_form(selected["id"], self.context["database_path"])
            selected["match_events"] = fetch_player_match_events(selected["id"], self.context["database_path"])
            others = [p for p in self.players if p["id"] != selected["id"]]
            candidate = min(others, key=lambda p: abs(p["overall"] - selected["overall"]))
            self.context["selected_player"] = selected
            self.modal = PlayerDetailModal(self.content_rect, selected, candidate, self.context["database_path"])

    def export_csv(self) -> None:
        path = Path(self.context["database_path"]).parent / "squad_export.csv"
        fields = ["name", "age", "nationality", "role", "bat", "bowl", "field", "overall", "form", "value", "contract_years_remaining", "wage"]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(self.table.rows)
        self.context["toast"] = f"Exported to {path.name}"

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Senior and academy roster • click any row for a complete profile")
        card = Card(pygame.Rect(self.content_rect.x + 14, self.content_rect.y + 68,
                                self.content_rect.width - 28, self.content_rect.height - 82), "FIRST-TEAM SQUAD", f"{len(self.table.rows)} PLAYERS")
        card.draw(surface)
        self.filter_button.draw(surface); self.export_button.draw(surface)
        pygame.draw.rect(surface, PANEL, self.search_rect, border_radius=4)
        pygame.draw.rect(surface, GREEN if self.search_active else BORDER, self.search_rect, width=1, border_radius=4)
        text(surface, self.search or "Search player name…", (self.search_rect.x + 11, self.search_rect.y + 9), 13, WHITE if self.search else MUTED)
        self.view_bar.draw(surface)
        self.table.draw(surface)
        if self.modal is None and self.table.hovered_row is not None and 0 <= self.table.hovered_row < len(self.table.rows):
            QuickCard.draw(surface, pygame.mouse.get_pos(), self.table.rows[self.table.hovered_row])
        if self.context.get("toast"):
            text(surface, self.context.pop("toast"), (self.content_rect.right - 25, self.content_rect.y + 48), 12, GREEN, anchor="topright")
        if self.modal: self.modal.draw(surface)
