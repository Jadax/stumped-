"""Club infrastructure upgrades with costs, benefits, and build timers."""
from __future__ import annotations
import pygame
from src.models.currency import format_money
from database import fetch_facility_upgrades, get_team_summary, start_facility_upgrade
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card
from .widgets.common import BORDER, DIM, GOLD, GREEN, MUTED, RED, WHITE, text


class FacilitiesScreen(BaseScreen):
    title = "Facilities"
    DEFINITIONS = {
        "Stadium": ("stadium_level", 2_500_000, "capacity", "+5,000 seats per level"),
        "Training Ground": ("training_level", 1_400_000, "development", "+8% development speed per level"),
        "Medical Centre": ("medical_level", 1_100_000, "recovery", "-10% injury recovery time per level"),
        "Academy": ("academy_level", 1_250_000, "potential", "Higher-quality youth intakes"),
        "Commercial Office": ("commercial_level", 900_000, "sponsors", "+2.5% sponsor value per level"),
        "Scouting Network": ("scouting_level", 1_050_000, "knowledge", "+2 detailed scout results per level"),
        "Grounds Department": ("grounds_level", 800_000, "pitch", "More reliable pitch preparation"),
    }

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.team = get_team_summary(self.team_id, self.db); self.context["team"] = self.team
        self.upgrades = fetch_facility_upgrades(self.team_id, self.db)
        self.pending = {row["facility"]: row for row in self.upgrades if row["status"] == "BUILDING"}
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 78, self.content_rect.width - 36
        gap = 10; columns = 3; rows = 3
        card_w = (w - gap * (columns - 1)) // columns
        card_h = (self.content_rect.bottom - 16 - y - gap * (rows - 1)) // rows
        self.cards, self.buttons = {}, {}
        for i, facility in enumerate(self.DEFINITIONS):
            rect = pygame.Rect(x + (i % columns) * (card_w + gap), y + (i // columns) * (card_h + gap), card_w, card_h)
            self.cards[facility] = rect
            self.buttons[facility] = Button(pygame.Rect(rect.right - 152, rect.bottom - 43, 134, 29), "START UPGRADE", ButtonStyle.SUCCESS)

    def process_event(self, event: pygame.event.Event) -> None:
        for facility, button in self.buttons.items():
            if button.process_event(event):
                try:
                    upgrade = start_facility_upgrade(self.team_id, facility, self.context.get("current_date", "2026-04-01"), self.db)
                    self.pending[facility] = upgrade; self.team = get_team_summary(self.team_id, self.db); self.context["team"] = self.team
                    self.context["toast"] = f"{facility} upgrade completes {upgrade['completion_date']}"
                except ValueError as exc: self.context["toast"] = str(exc)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Invest in infrastructure • every upgrade takes one simulated week")
        for facility, (column, base_cost, benefit_key, benefit) in self.DEFINITIONS.items():
            rect = self.cards[facility]; level = self.team[column]; pending = self.pending.get(facility)
            Card(rect, facility.upper(), "MAX LEVEL" if level >= 5 else f"LEVEL {level} / 5").draw(surface)
            x, y = rect.x + 14, rect.y + 54
            if facility == "Stadium":
                text(surface, "Current capacity", (x, y), 11, MUTED); text(surface, f"{self.team['stadium_capacity']:,}", (rect.right - 18, y), 14, WHITE, bold=True, anchor="topright")
                text(surface, "Next capacity", (x, y + 30), 11, MUTED); text(surface, f"{self.team['stadium_capacity'] + 5000:,}", (rect.right - 18, y + 30), 13, GREEN, bold=True, anchor="topright")
            else:
                text(surface, "Current benefit", (x, y), 10, MUTED); text(surface, benefit, (x, y + 21), 10, GREEN, bold=True)
            cost = int(base_cost * (1 + (level - 1) * .75))
            text(surface, "Upgrade cost", (x, rect.bottom - 61), 10, MUTED)
            text(surface, format_money(cost), (rect.right - 14, rect.bottom - 61), 11, GOLD if self.team["cash"] >= cost else RED, bold=True, anchor="topright")
            button = self.buttons[facility]
            button.enabled = not pending and level < 5 and self.team["cash"] >= cost
            button.label = f"BUILDING • {pending['completion_date']}" if pending else "MAXIMUM LEVEL" if level >= 5 else "START UPGRADE"
            button.draw(surface)
            # Five-block level indicator follows the Motorsport Manager-style upgrade rail.
            block_w = 25
            for index in range(5):
                block = pygame.Rect(x + index * (block_w + 4), rect.y + 105, block_w, 8)
                pygame.draw.rect(surface, GREEN if index < level else DIM, block)
                pygame.draw.rect(surface, BORDER, block, 1)
        text(surface, f"AVAILABLE CASH  {format_money(self.team['cash'])}", (self.content_rect.right - 20, self.content_rect.y + 51), 11, GOLD, bold=True, anchor="topright")
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 64), 10, GREEN, anchor="topright")
