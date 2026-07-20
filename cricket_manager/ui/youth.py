"""Youth Academy roster, collective focus, recruitment, and prospect profiles."""
from __future__ import annotations
import pygame
from src.models.currency import format_money
from database import (add_financial_transaction, create_inbox_message, fetch_players, recruit_youth,
                      set_training_focus)
from .player_modals import PlayerDetailModal
from .shared_components import BaseScreen, group_average
from .widgets import Button, ButtonStyle, Card, DataTable
from .widgets.datatable import Column
from .widgets.common import GOLD, GREEN, MUTED, WHITE, text


class YouthScreen(BaseScreen):
    title = "Youth Academy"
    FOCUSES = ["Balanced", "Batting", "Bowling", "Fielding"]

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.all_players = fetch_players(self.team_id, self.db)
        self.players = [p for p in self.all_players if p["age"] <= 20 or p.get("academy_squad")]
        self.focus_index = int(self.context.get("academy_focus_index", 0)) % len(self.FOCUSES)
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 76, self.content_rect.width - 36
        self.table_card = pygame.Rect(x, y, int(w * .72), self.content_rect.height - 92)
        self.side_card = pygame.Rect(self.table_card.right + 10, y, self.content_rect.right - 18 - self.table_card.right - 10, self.content_rect.height - 92)
        table_rect = pygame.Rect(self.table_card.x + 10, self.table_card.y + 48, self.table_card.width - 20, self.table_card.height - 58)
        columns = [Column("name", "Prospect", .27), Column("age", "Age", .07), Column("role", "Role", .17),
                   Column("bat", "Bat", .09), Column("bowl", "Bowl", .09), Column("field", "Field", .09),
                   Column("overall", "OVR", .1), Column("potential", "POT", .12)]
        self.table = DataTable(table_rect, columns, self._rows(), 32)
        sx, sw = self.side_card.x + 15, self.side_card.width - 30
        self.focus_button = Button(pygame.Rect(sx, self.side_card.y + 105, sw, 30), "FOCUS: BALANCED", ButtonStyle.PRIMARY)
        self.recruit_button = Button(pygame.Rect(sx, self.side_card.y + 187, sw, 32), f"RECRUIT YOUTH • {format_money(50_000, compact=True)}", ButtonStyle.SUCCESS)

    def _rows(self):
        return [dict(p, bat=group_average(p, "batting"), bowl=group_average(p, "bowling"), field=group_average(p, "fielding")) for p in self.players]

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self.modal.process_event(event): self.modal = None
            return
        selected = self.table.process_event(event)
        if selected:
            candidate = max((p for p in self.players if p["id"] != selected["id"]), key=lambda p: p["potential"], default=selected)
            self.modal = PlayerDetailModal(self.content_rect, selected, candidate)
        if self.focus_button.process_event(event):
            self.focus_index = (self.focus_index + 1) % len(self.FOCUSES); self.context["academy_focus_index"] = self.focus_index
            programme = {"Balanced": "All-Round", "Batting": "Batting Focus", "Bowling": "Bowling Focus", "Fielding": "Fielding Focus"}[self.FOCUSES[self.focus_index]]
            for player in self.players: set_training_focus(player["id"], programme, self.db)
            self.context["toast"] = f"Academy focus changed to {self.FOCUSES[self.focus_index]}"
        if self.recruit_button.process_event(event):
            created = recruit_youth(self.team_id, count=None, database_path=self.db)
            add_financial_transaction(self.team_id, self.context.get("current_date", "2026-04-01"), "Youth Academy", "EXPENSE", 50_000,
                                      "Youth recruitment trials", self.db)
            self.all_players = fetch_players(self.team_id, self.db); self.context["players"] = self.all_players
            self.players = [p for p in self.all_players if p["age"] <= 20 or p.get("academy_squad")]
            self.table.set_rows(self._rows()); self.context["toast"] = f"Recruited {len(created)} new prospects"
            create_inbox_message("LOW", "Youth recruitment complete",
                                 f"Academy trials have produced {len(created)} new 16-year-old prospects.",
                                 timestamp=f"{self.context.get('current_date','2026-04-01')} 16:00", database_path=self.db)
            self.context["refresh_inbox"] = True

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Identify, recruit, and develop the club's next generation")
        Card(self.table_card, "UNDER-20 SQUAD", f"{len(self.players)} PROSPECTS").draw(surface)
        Card(self.side_card, "ACADEMY PROGRAMME", f"LEVEL {self.context['team']['academy_level']}").draw(surface)
        self.table.draw(surface)
        x = self.side_card.x + 15
        text(surface, "COLLECTIVE TRAINING FOCUS", (x, self.side_card.y + 58), 11, MUTED, bold=True)
        self.focus_button.label = f"FOCUS: {self.FOCUSES[self.focus_index].upper()}"; self.focus_button.draw(surface)
        text(surface, "RECRUITMENT TRIAL", (x, self.side_card.y + 158), 11, MUTED, bold=True)
        self.recruit_button.draw(surface)
        text(surface, "Generates 3–5 new 16-year-olds", (x, self.side_card.y + 232), 10, WHITE)
        text(surface, "Potential range: 40–85", (x, self.side_card.y + 252), 10, GOLD)
        text(surface, "Academy level improves intake quality.", (x, self.side_card.y + 272), 10, GREEN)
        y = self.side_card.y + 320; text(surface, "DEVELOPMENT PIPELINE", (x, y), 11, MUTED, bold=True)
        bands = [("Elite potential (80+)", sum(p["potential"] >= 80 for p in self.players), GOLD),
                 ("First-team potential (65+)", sum(p["potential"] >= 65 for p in self.players), GREEN),
                 ("Long-term projects", sum(p["potential"] < 65 for p in self.players), WHITE)]
        for label, value, colour in bands:
            y += 31; text(surface, label, (x, y), 10, MUTED); text(surface, value, (self.side_card.right - 15, y), 12, colour, bold=True, anchor="topright")
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52), 11, GREEN, anchor="topright")
        if self.modal: self.modal.draw(surface)
