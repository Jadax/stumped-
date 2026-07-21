"""Medical Centre: active injuries, recovery timelines, and staff-driven risk."""
from __future__ import annotations

from datetime import date

import pygame

from database import fetch_active_injuries, fetch_players, team_physio_rating
from .shared_components import BaseScreen
from .widgets import Card
from .widgets.common import CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, clipped_text, text

SEVERITY_COLOUR = {"Minor": GOLD, "Moderate": pygame.Color("#ff9500"), "Major": RED}


class MedicalScreen(BaseScreen):
    title = "Medical Centre"

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.current_date = self.context.get("current_date", "2026-04-01")
        self.refresh()
        left_w = int((self.content_rect.width - 54) * .58)
        x, y = self.content_rect.x + 18, self.content_rect.y + 76
        self.injuries_rect = pygame.Rect(x, y, left_w, self.content_rect.height - 94)
        self.risk_rect = pygame.Rect(self.injuries_rect.right + 18, y,
                                     self.content_rect.right - 18 - self.injuries_rect.right - 18,
                                     self.content_rect.height - 94)

    def refresh(self) -> None:
        self.injuries = fetch_active_injuries(self.team_id, self.db)
        self.physio_rating = team_physio_rating(self.team_id, self.db)
        self.players = fetch_players(self.team_id, self.db)

    def process_event(self, event: pygame.event.Event) -> None:
        pass

    def _days_remaining(self, return_date: str) -> int:
        try:
            return max(0, (date.fromisoformat(return_date) - date.fromisoformat(self.current_date)).days)
        except ValueError:
            return 0

    def _draw_injuries(self, surface: pygame.Surface) -> None:
        card = Card(self.injuries_rect, "ACTIVE INJURIES", f"{len(self.injuries)} PLAYERS OUT")
        card.draw(surface)
        if not self.injuries:
            text(surface, "The treatment room is empty — the whole squad is fit.",
                 (card.rect.centerx, card.rect.centery), 13, GREEN, anchor="center")
            return
        y = card.rect.y + 52
        headers = ["PLAYER", "SEVERITY", "RETURNS", "DAYS LEFT"]
        fractions = [.03, .48, .72, .97]
        for header, frac in zip(headers, fractions):
            text(surface, header, (card.rect.x + int(card.rect.width * frac), y), 9, MUTED, bold=True,
                 anchor="topright" if frac > .5 else "topleft")
        y += 22
        for index, injury in enumerate(self.injuries):
            row = pygame.Rect(card.rect.x + 10, y, card.rect.width - 20, 30)
            if index % 2 == 0:
                pygame.draw.rect(surface, CARD_ALT, row)
            colour = SEVERITY_COLOUR.get(injury["severity"], MUTED)
            text(surface, clipped_text(injury["player_name"], int(card.rect.width * .4), 12),
                 (row.x + 8, row.y + 7), 12, WHITE, bold=True)
            text(surface, injury["severity"], (card.rect.x + int(card.rect.width * .48), row.y + 7), 11,
                 colour, bold=True, anchor="topright")
            text(surface, injury["return_date"], (card.rect.x + int(card.rect.width * .72), row.y + 7), 11,
                 WHITE, anchor="topright")
            days_left = self._days_remaining(injury["return_date"])
            text(surface, days_left, (card.rect.x + int(card.rect.width * .97), row.y + 7), 12,
                 GREEN if days_left <= 3 else WHITE, bold=True, anchor="topright")
            y += 32

    def _draw_risk(self, surface: pygame.Surface) -> None:
        card = Card(self.risk_rect, "INJURY RISK ASSESSMENT", "STAFF-DRIVEN")
        card.draw(surface)
        x, y = card.rect.x + 18, card.rect.y + 54
        text(surface, "TEAM PHYSIOTHERAPY RATING", (x, y), 11, MUTED, bold=True); y += 20
        track = pygame.Rect(x, y, card.rect.width - 36, 8)
        pygame.draw.rect(surface, CARD_ALT, track, border_radius=4)
        fill_colour = GREEN if self.physio_rating >= 14 else GOLD if self.physio_rating >= 8 else RED
        pygame.draw.rect(surface, fill_colour, (track.x, track.y, int(track.width * self.physio_rating / 20), 8),
                         border_radius=4)
        text(surface, f"{self.physio_rating}/20", (track.right, y - 2), 11, WHITE, bold=True, anchor="topright")
        y += 30
        verdict = ("Excellent medical care — injuries are rarer and recoveries faster."
                  if self.physio_rating >= 14 else
                  "Solid medical support at league-average levels."
                  if self.physio_rating >= 8 else
                  "A thin medical department — consider investing in better physios.")
        for line in [verdict[i:i + 44] for i in range(0, len(verdict), 44)]:
            text(surface, line, (x, y), 10, MUTED); y += 15
        y += 12
        text(surface, "PLAYERS AT ELEVATED RISK", (x, y), 11, MUTED, bold=True); y += 20
        at_risk = sorted(
            (p for p in self.players if p.get("physical", {}).get("fitness", p.get("mental", {}).get("fitness", 60)) < 55),
            key=lambda p: p.get("physical", {}).get("fitness", 100),
        )[:6]
        if not at_risk:
            text(surface, "No players currently show elevated injury risk.", (x, y), 11, GREEN)
            return
        for player in at_risk:
            fitness = player.get("physical", {}).get("fitness", player.get("mental", {}).get("fitness", 60))
            text(surface, clipped_text(player["name"], card.rect.width - 100, 11), (x, y), 11, WHITE)
            text(surface, f"Fit {fitness}", (card.rect.right - 18, y), 10, GOLD if fitness < 45 else MUTED,
                 bold=True, anchor="topright")
            y += 22

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Treatment room status and staff-driven injury risk")
        self._draw_injuries(surface)
        self._draw_risk(surface)
