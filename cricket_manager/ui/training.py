"""Individual training programmes and gradual potential-capped development."""
from __future__ import annotations
from datetime import date, timedelta
import pygame
from database import (apply_daily_training, fetch_players, fetch_training_assignments,
                      set_training_focus, set_training_schedule)
from .shared_components import BaseScreen
from .widgets import AttributeBar, Button, ButtonStyle, Card, DataTable
from .widgets.datatable import Column
from .widgets.common import GOLD, GREEN, MUTED, WHITE, text


class TrainingScreen(BaseScreen):
    title = "Training"
    FOCUSES = ["None", "Batting Focus", "Bowling Focus", "Fielding Focus", "Fitness", "All-Round"]

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.players = fetch_players(self.team_id, self.db); self.context["players"] = self.players
        self.assignments = fetch_training_assignments(self.team_id, self.db)
        self.selected = self.players[0] if self.players else None
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 76, self.content_rect.width - 36
        self.table_card = pygame.Rect(x, y, int(w * .69), self.content_rect.height - 92)
        self.detail_card = pygame.Rect(self.table_card.right + 10, y, self.content_rect.right - 18 - self.table_card.right - 10, self.content_rect.height - 92)
        rows = self._rows()
        table_rect = pygame.Rect(self.table_card.x + 10, self.table_card.y + 48, self.table_card.width - 20, self.table_card.height - 58)
        cols = [Column("name", "Player", .28), Column("role", "Role", .17), Column("overall", "OVR", .09),
                Column("potential", "POT", .08), Column("focus", "Programme ▼", .20),
                Column("schedule", "Days ▼", .10), Column("intensity", "Load ▼", .10), Column("growth", "30D", .08)]
        self.table = DataTable(table_rect, cols, rows, 31)
        dx = self.detail_card.x + 15; dw = self.detail_card.width - 30
        self.focus_button = Button(pygame.Rect(dx, self.detail_card.y + 104, dw, 29), "CYCLE PROGRAMME", ButtonStyle.PRIMARY)
        self.intensity_button = Button(pygame.Rect(dx, self.detail_card.y + 139, dw, 27), "INTENSITY: NORMAL", ButtonStyle.SECONDARY)
        self.days_button = Button(pygame.Rect(dx, self.detail_card.y + 172, dw, 27), "DAYS: MON / WED / FRI", ButtonStyle.SECONDARY)
        self.bulk_button = Button(pygame.Rect(dx, self.detail_card.bottom - 107, dw, 27), "APPLY PROGRAMME TO ALL", ButtonStyle.PRIMARY)
        self.day_button = Button(pygame.Rect(dx, self.detail_card.bottom - 74, dw, 27), "ADVANCE TO NEXT SESSION", ButtonStyle.SUCCESS)
        self.month_button = Button(pygame.Rect(dx, self.detail_card.bottom - 41, dw, 27), "SIMULATE 30 CALENDAR DAYS", ButtonStyle.SECONDARY)

    def _rows(self) -> list[dict]:
        rows = []
        for player in self.players:
            assignment = self.assignments.get(player["id"], {"focus": "None", "progress": {}, "intensity": "Normal", "days": [0,2,4]})
            growth = sum(assignment["progress"].values())
            labels = "".join("MTWTFSS"[day] for day in assignment.get("days", [0,2,4]))
            rows.append(dict(player, focus=assignment["focus"], schedule=labels,
                             intensity=assignment.get("intensity", "Normal"), growth=f"+{growth:.2f}"))
        return rows

    def _cycle_selected(self) -> None:
        if not self.selected: return
        current = self.assignments.get(self.selected["id"], {"focus": "None"})["focus"]
        focus = self.FOCUSES[(self.FOCUSES.index(current) + 1) % len(self.FOCUSES)]
        set_training_focus(self.selected["id"], focus, self.db)
        self.assignments = fetch_training_assignments(self.team_id, self.db); self.table.set_rows(self._rows())

    def _update_schedule(self, *, cycle_intensity: bool = False, cycle_days: bool = False) -> None:
        if not self.selected: return
        assignment = self.assignments.get(self.selected["id"], {"focus":"None","intensity":"Normal","days":[0,2,4]})
        intensity, days = assignment.get("intensity", "Normal"), assignment.get("days", [0,2,4])
        if cycle_intensity:
            levels = ["Light", "Normal", "Heavy"]; intensity = levels[(levels.index(intensity) + 1) % len(levels)]
        if cycle_days:
            patterns = [[0,2,4], [1,3], [0,1,3,4]]
            days = patterns[(patterns.index(days) + 1) % len(patterns)] if days in patterns else patterns[0]
        set_training_schedule(self.selected["id"], assignment["focus"], intensity, days, self.db)
        self.assignments = fetch_training_assignments(self.team_id, self.db); self.table.set_rows(self._rows())

    def _apply_all(self) -> None:
        if not self.selected: return
        assignment = self.assignments.get(self.selected["id"], {"focus":"None","intensity":"Normal","days":[0,2,4]})
        for player in self.players:
            set_training_schedule(player["id"], assignment["focus"], assignment.get("intensity","Normal"), assignment.get("days",[0,2,4]), self.db)
        self.assignments = fetch_training_assignments(self.team_id, self.db); self.table.set_rows(self._rows())
        self.context["toast"] = "Programme and weekly schedule applied to the full squad"

    def _simulate_days(self, count: int) -> None:
        start = date.fromisoformat(self.context.get("current_date", "2026-04-01")); points = 0
        for offset in range(count): points += apply_daily_training(self.team_id, (start + timedelta(days=offset)).isoformat(), self.db)
        self.context["toast"] = f"Training complete • {points} attribute points gained"
        selected_id = self.selected["id"] if self.selected else None
        self.players = fetch_players(self.team_id, self.db); self.context["players"] = self.players
        self.selected = next((p for p in self.players if p["id"] == selected_id), self.players[0] if self.players else None)
        self.assignments = fetch_training_assignments(self.team_id, self.db); self.table.set_rows(self._rows())

    def process_event(self, event: pygame.event.Event) -> None:
        row = self.table.process_event(event)
        if row:
            self.selected = next((p for p in self.players if p["id"] == row["id"]), None)
            # The three inline selector columns behave like compact dropdowns:
            # one click advances the relevant choice without leaving the list.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                columns = self.table._column_rects()
                if columns[4].collidepoint(event.pos): self._cycle_selected()
                elif columns[5].collidepoint(event.pos): self._update_schedule(cycle_days=True)
                elif columns[6].collidepoint(event.pos): self._update_schedule(cycle_intensity=True)
        if self.focus_button.process_event(event): self._cycle_selected()
        if self.intensity_button.process_event(event): self._update_schedule(cycle_intensity=True)
        if self.days_button.process_event(event): self._update_schedule(cycle_days=True)
        if self.bulk_button.process_event(event): self._apply_all()
        if self.day_button.process_event(event):
            current = date.fromisoformat(self.context.get("current_date", "2026-04-01")); offset = 1
            while (current + timedelta(days=offset)).weekday() not in (0,2,4): offset += 1
            self._simulate_days(offset + 1)
        if self.month_button.process_event(event): self._simulate_days(30)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Assign programmes • development is gradual and capped by potential")
        Card(self.table_card, "SQUAD TRAINING", f"{len(self.players)} PLAYERS").draw(surface)
        Card(self.detail_card, "PROGRAMME DETAIL", "COACHING REPORT").draw(surface)
        self.table.draw(surface)
        if self.selected:
            assignment = self.assignments.get(self.selected["id"], {"focus": "None", "progress": {}, "intensity":"Normal", "days":[0,2,4]})
            x, y = self.detail_card.x + 15, self.detail_card.y + 52
            text(surface, self.selected["name"], (x, y), 16, GOLD, bold=True)
            text(surface, f"OVR {self.selected['overall']}  •  POT {self.selected['potential']}", (x, y + 25), 11, MUTED)
            self.focus_button.label = f"PROGRAMME: {assignment['focus'].upper()}"
            self.intensity_button.label = f"INTENSITY: {assignment.get('intensity','Normal').upper()}"
            day_names = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
            self.days_button.label = "DAYS: " + " / ".join(day_names[d] for d in assignment.get("days",[0,2,4]))
            progress = assignment["progress"]
            group_values = {}
            for group in ("batting", "bowling", "fielding", "mental"):
                group_values[group] = min(100, int(sum(value for key, value in progress.items() if key.startswith(group)) * 20))
            yy = self.detail_card.y + 218
            for group, value in group_values.items():
                AttributeBar(pygame.Rect(x, yy, self.detail_card.width - 30, 27), f"{group.title()} growth", value).draw(surface); yy += 43
            text(surface, "Expected focused growth: 1–3 points / season", (x, yy + 10), 10, GREEN)
            text(surface, "Higher Training Ground levels accelerate gains.", (x, yy + 30), 10, MUTED)
        self.focus_button.draw(surface); self.intensity_button.draw(surface); self.days_button.draw(surface)
        self.bulk_button.draw(surface); self.day_button.draw(surface); self.month_button.draw(surface)
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52), 11, GREEN, anchor="topright")
