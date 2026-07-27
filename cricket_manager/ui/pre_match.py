"""Toss countdown and final line-up review before entering the live match."""
from __future__ import annotations
import random
import pygame
from database import adjust_players_morale, fetch_next_fixture, fetch_players
from .player_modals import PlayerDetailModal
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, PitchDisplay, WeatherDisplay
from .widgets.common import BG, CARD, CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, text, clipped_text
from src.models.morale import DROPPED_MORALE_PENALTY, dropped_from_xi


class PreMatchScreen(BaseScreen):
    dynamic = True
    title = "Pre-Match"

    def build(self) -> None:
        selection = self.context.get("selection", {})
        ids = selection.get("xi", [])
        self.user_xi = [p for pid in ids for p in self.context["players"] if p["id"] == pid]
        if len(self.user_xi) != 11:
            keepers = [p for p in self.context["players"] if p["role"] == "Wicketkeeper"]
            self.user_xi = (keepers[:1] + [p for p in sorted(self.context["players"], key=lambda p: p["overall"], reverse=True) if p not in keepers[:1]])[:11]
        last = self.context.get("last_match_xi")
        if last and last.get("team_id") == self.context["team"]["id"]:
            dropped = dropped_from_xi(last.get("xi", []), [p["id"] for p in self.user_xi])
            adjust_players_morale(dropped, DROPPED_MORALE_PENALTY, self.context["database_path"])
        fixture = fetch_next_fixture(self.context["team"]["id"], self.context["database_path"])
        self.fixture = fixture
        opponent_id = fixture["away_team"] if fixture and fixture["home_team"] == self.context["team"]["id"] else fixture["home_team"] if fixture else 2
        self.opponent_xi = fetch_players(opponent_id, self.context["database_path"])[:11]
        self.elapsed, self.flipping = 0.0, True
        self.toss_result = random.choice(["Manchester Mavericks won the toss", "Sydney Sixers won the toss"])
        self.decision = random.choice(["and chose to bat first.", "and elected to bowl first."])
        self.start_button = Button(pygame.Rect(self.content_rect.centerx - 110, self.content_rect.bottom - 49, 220, 35),
                                   "START MATCH", ButtonStyle.SUCCESS, enabled=False)
        layout_x = self.content_rect.x + 22
        layout_w = self.content_rect.width - 44
        side_w, centre_w, gap = int(layout_w * .34), int(layout_w * .26), 12
        self.lineup_hit_rects = [
            pygame.Rect(layout_x + 12, self.content_rect.y + 127, side_w - 24, 11 * 29),
            pygame.Rect(layout_x + side_w + gap + centre_w + gap + 12,
                        self.content_rect.y + 127,
                        self.content_rect.right - 22 - (layout_x + side_w + gap + centre_w + gap) - 24,
                        11 * 29),
        ]

    def update(self, time_delta: float) -> None:
        if self.flipping:
            self.elapsed += time_delta
            if self.elapsed >= 2.2: self.flipping = False; self.start_button.enabled = True

    def process_event(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self.modal.process_event(event): self.modal = None
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for area, players, candidates in zip(self.lineup_hit_rects,
                                                  (self.user_xi, self.opponent_xi),
                                                  (self.opponent_xi, self.user_xi)):
                if area.collidepoint(event.pos):
                    index = (event.pos[1] - area.y) // 29
                    if 0 <= index < len(players): self.modal = PlayerDetailModal(self.content_rect, players[index], candidates[0], self.context["database_path"])
        if self.start_button.process_event(event):
            self.context["match_setup"] = {"user_xi": self.user_xi, "opponent_xi": self.opponent_xi, "fixture": self.fixture}
            if self.navigate: self.navigate("Match")

    def _draw_xi(self, surface, card, players, user=False):
        y = card.rect.y + 52
        captain = self.context.get("selection", {}).get("captain") if user else None
        keeper = self.context.get("selection", {}).get("keeper") if user else None
        for i, player in enumerate(players):
            row = pygame.Rect(card.rect.x + 12, y + i * 29, card.rect.width - 24, 26)
            pygame.draw.rect(surface, CARD_ALT if i % 2 else CARD, row)
            suffix = " (C)" if player["id"] == captain else " (WK)" if player["id"] == keeper else ""
            text(surface, f"{i+1:>2}", (row.x + 7, row.y + 6), 11, GOLD)
            text(surface, clipped_text(player["name"] + suffix, row.width - 100, 12), (row.x + 34, row.y + 5), 12, WHITE)
            text(surface, player["overall"], (row.right - 9, row.y + 5), 12, GREEN, bold=True, anchor="topright")

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Final preparations • conditions and confirmed line-ups")
        x, y, w = self.content_rect.x + 22, self.content_rect.y + 75, self.content_rect.width - 44
        side_w, centre_w, gap = int(w * .34), int(w * .26), 12
        left = Card(pygame.Rect(x, y, side_w, self.content_rect.height - 145), "MANCHESTER MAVERICKS", "PLAYING XI")
        centre = Card(pygame.Rect(left.rect.right + gap, y, centre_w, self.content_rect.height - 145), "TOSS & CONDITIONS")
        right = Card(pygame.Rect(centre.rect.right + gap, y, self.content_rect.right - 22 - centre.rect.right - gap, self.content_rect.height - 145), "SYDNEY SIXERS", "PLAYING XI")
        for card in (left, centre, right): card.draw(surface)
        self._draw_xi(surface, left, self.user_xi, True); self._draw_xi(surface, right, self.opponent_xi)
        coin_y = centre.rect.y + 112
        radius = 42 if self.flipping else 36
        squash = max(7, int(abs(((self.elapsed * 5) % 2) - 1) * radius)) if self.flipping else radius
        pygame.draw.ellipse(surface, GOLD, (centre.rect.centerx - squash, coin_y - radius, squash * 2, radius * 2))
        text(surface, "M" if int(self.elapsed * 7) % 2 else "S", (centre.rect.centerx, coin_y), 24, BG, bold=True, anchor="center")
        if self.flipping:
            text(surface, "COIN IN THE AIR…", (centre.rect.centerx, coin_y + 67), 14, GOLD, bold=True, anchor="center")
        else:
            text(surface, self.toss_result, (centre.rect.centerx, coin_y + 62), 13, WHITE, bold=True, anchor="center")
            text(surface, self.decision, (centre.rect.centerx, coin_y + 84), 12, MUTED, anchor="center")
        info_y = centre.rect.y + 246
        WeatherDisplay(pygame.Rect(centre.rect.x + 14, info_y, centre.rect.width - 28, 62), "Overcast",
                       ["Overcast", "Cloudy", "Overcast", "Rain Threat", "Cloudy", "Sunny"]).draw(surface)
        PitchDisplay(pygame.Rect(centre.rect.x + 14, info_y + 70, centre.rect.width - 28, 40), "Green", 4).draw(surface)
        info_y += 118
        text(surface, "KEY WATCH", (centre.rect.x + 18, info_y + 14), 11, MUTED, bold=True)
        text(surface, "• New ball may swing sharply", (centre.rect.x + 18, info_y + 40), 11, GOLD)
        text(surface, "• Protect recovering players", (centre.rect.x + 18, info_y + 61), 11, RED)
        self.start_button.draw(surface)
        if self.modal: self.modal.draw(surface)
