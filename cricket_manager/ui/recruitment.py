"""Recruitment Hub — a tiled front page over Transfers, Staff Market, and
squad-gap data that already exists (docs/UX_ROADMAP.md item 1)."""
from __future__ import annotations

import pygame

from .shared_components import BaseScreen, group_average
from .widgets import Button, ButtonStyle, Card
from .widgets.common import GOLD, GREEN, MUTED, RED, WHITE, clipped_text, text
from .widgets.spacing import columns, rows

ROLE_TARGETS = {"Wicketkeeper": 2, "Bowler": 5, "All-Rounder": 2, "Batsman": 5}


class RecruitmentHubScreen(BaseScreen):
    title = "Recruitment"

    def build(self) -> None:
        self.players = self.context["players"]
        self.buttons = []
        actions = [("Browse Transfers", ButtonStyle.SUCCESS, "Transfers"),
                   ("Staff Market", ButtonStyle.PRIMARY, "Staff"),
                   ("Academy", ButtonStyle.SECONDARY, "Youth Academy")]
        width, gap = 140, 8
        x = self.content_rect.right - 20 - len(actions) * width - (len(actions) - 1) * gap
        for label, style, destination in actions:
            self.buttons.append((Button(pygame.Rect(x, self.content_rect.y + 23, width, 30), label, style), destination))
            x += width + gap

    def process_event(self, event: pygame.event.Event) -> None:
        for button, destination in self.buttons:
            if button.process_event(event) and self.navigate:
                self.navigate(destination)

    def _objectives(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        team = self.context["team"]
        gaps = self._role_gaps()
        weakest = min(("batting", "bowling", "fielding"),
                      key=lambda group: sum(group_average(p, group) for p in self.players) / max(1, len(self.players)))
        headline = f"Strengthen {weakest}" if not gaps else f"Fill {gaps[0][0]} — only {gaps[0][1]} in the squad"
        Card(rect, "RECRUITMENT OBJECTIVES", f"DIVISION {team.get('division', 1)} TARGET").draw(surface)
        text(surface, headline, (rect.x + 15, rect.y + 52), 14, GOLD, bold=True)
        text(surface, "Board expects a squad built to compete at this level — see Squad Report for a full comparison.",
             (rect.x + 15, rect.y + 76), 11, MUTED)
        text(surface, f"Cash available: {team.get('cash', 0):,}", (rect.x + 15, rect.y + 100), 12, WHITE)

    def _role_gaps(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for player in self.players:
            counts[player["role"]] = counts.get(player["role"], 0) + 1
        return [(role, counts.get(role, 0)) for role, target in ROLE_TARGETS.items() if counts.get(role, 0) < target]

    def _squad_gaps(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        gaps = self._role_gaps()
        Card(rect, "SQUAD GAPS", f"{len(gaps)} ROLE(S) SHORT").draw(surface)
        if not gaps:
            text(surface, "Every role meets its target headcount.", (rect.x + 15, rect.y + 55), 12, GREEN)
            return
        for i, (role, have) in enumerate(gaps[:4]):
            y = rect.y + 52 + i * 22
            text(surface, role, (rect.x + 15, y), 12, WHITE)
            text(surface, f"{have}/{ROLE_TARGETS[role]}", (rect.right - 15, y), 12, RED, bold=True, anchor="topright")

    def _contract_watch(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        expiring = sorted((p for p in self.players if p.get("contract_years_remaining", 2) <= 1),
                          key=lambda p: p.get("contract_years_remaining", 0))
        Card(rect, "CONTRACT WATCH", f"{len(expiring)} EXPIRING").draw(surface)
        if not expiring:
            text(surface, "No contracts expiring within a year.", (rect.x + 15, rect.y + 55), 12, GREEN)
            return
        for i, player in enumerate(expiring[:5]):
            y = rect.y + 52 + i * 22
            text(surface, clipped_text(player["name"], rect.width - 110, 12), (rect.x + 15, y), 12, WHITE)
            years = player.get("contract_years_remaining", 0)
            label = "Free agent" if years <= 0 else "Expires this year"
            text(surface, label, (rect.right - 15, y), 11, GOLD if years > 0 else RED, bold=True, anchor="topright")

    def _top_scouted(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        Card(rect, "REQUIREMENTS", "SCOUT FOCUS").draw(surface)
        gaps = self._role_gaps()
        lines = [f"Recruit a {role}" for role, _ in gaps[:3]] or ["No open recruitment requirements — squad is at target strength."]
        for i, line in enumerate(lines):
            text(surface, clipped_text(line, rect.width - 30, 12), (rect.x + 15, rect.y + 52 + i * 22), 12, WHITE)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Scouting, transfers, and staff recruitment in one view")
        for button, _ in self.buttons:
            button.draw(surface)
        body = pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 69,
                           self.content_rect.width - 36, self.content_rect.height - 84)
        top, bottom = rows(body, (.42, .58), 10)
        left, right = columns(top, (.6, .4), 10)
        bottom_cols = columns(bottom, (.5, .5), 10)
        self._objectives(surface, left)
        self._squad_gaps(surface, right)
        self._contract_watch(surface, bottom_cols[0])
        self._top_scouted(surface, bottom_cols[1])
