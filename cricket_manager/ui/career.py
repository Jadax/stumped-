"""Manager career hub: reputation, board confidence, world ratings, awards."""
from __future__ import annotations

import pygame

from database import fetch_honours, fetch_league_standings, fetch_players, fetch_teams
from src.models.career import board_confidence, manager_reputation, season_awards, world_ratings
from .shared_components import BaseScreen
from .widgets import Button, ButtonStyle, Card, draw_country_flag
from .widgets.common import BORDER, CARD, CARD_ALT, DIM, GOLD, GREEN, MUTED, RED, WHITE, clipped_text, text


class CareerScreen(BaseScreen):
    title = "Career"
    TABS = ["Overview", "World Ratings", "Awards", "Trophies"]
    DISCIPLINES = ["batting", "bowling", "all-round"]

    def build(self) -> None:
        db, team = self.context["database_path"], self.context["team"]
        self.standings = [dict(position=i + 1, **row) for i, row in enumerate(fetch_league_standings(db))]
        teams = fetch_teams(db)
        self.world_players: list[dict] = []
        for club in teams:
            for player in fetch_players(club["id"], db):
                player["team_name"] = club["name"]
                self.world_players.append(player)
        my_row = next((r for r in self.standings if r["team_id"] == team["id"]), None)
        objective = int(self.context.get("new_game_setup", {}).get("objective_position", 6) or 6)
        cash = int(team.get("budget", team.get("cash", 0)) or 0)
        position = my_row["position"] if my_row else len(self.standings) or 12
        self.confidence = board_confidence(position, max(1, len(self.standings)), objective, cash)
        played = my_row["played"] if my_row else 0
        wins = my_row["won"] if my_row else 0
        self.honours = fetch_honours(team["id"], db) or list(self.context.get("honours") or [])
        self.reputation = manager_reputation(played, wins, len(self.honours))
        self.awards = season_awards(self.world_players)
        self.active_tab, self.discipline = "Overview", "batting"
        self.tab_buttons = []
        x = self.content_rect.x + 18
        for label in self.TABS:
            self.tab_buttons.append((label, Button(pygame.Rect(x, self.content_rect.y + 70, 132, 29), label.upper(),
                                                   ButtonStyle.SECONDARY, selected=label == self.active_tab)))
            x += 138
        self.discipline_buttons = []
        x = self.content_rect.right - 3 * 118 - 18
        for label in self.DISCIPLINES:
            self.discipline_buttons.append((label, Button(pygame.Rect(x, self.content_rect.y + 70, 112, 29),
                                                          label.upper(), ButtonStyle.SECONDARY,
                                                          selected=label == self.discipline)))
            x += 118

    def process_event(self, event: pygame.event.Event) -> None:
        for label, button in self.tab_buttons:
            if button.process_event(event):
                self.active_tab = label
                for other_label, other in self.tab_buttons: other.selected = other_label == label
        if self.active_tab == "World Ratings":
            for label, button in self.discipline_buttons:
                if button.process_event(event):
                    self.discipline = label
                    for other_label, other in self.discipline_buttons: other.selected = other_label == label

    def _gauge(self, surface: pygame.Surface, rect: pygame.Rect, title: str, score: int, label: str) -> None:
        card = Card(rect, title); card.draw(surface)
        text(surface, f"{score}", (rect.centerx, rect.y + 92), 44, GOLD, bold=True, anchor="center")
        text(surface, label.upper(), (rect.centerx, rect.y + 130), 13,
             GREEN if score >= 60 else GOLD if score >= 40 else RED, bold=True, anchor="center")
        track = pygame.Rect(rect.x + 24, rect.y + 152, rect.width - 48, 10)
        pygame.draw.rect(surface, CARD_ALT, track, border_radius=5)
        fill = GREEN if score >= 60 else GOLD if score >= 40 else RED
        pygame.draw.rect(surface, fill, (track.x, track.y, int(track.width * score / 100), 10), border_radius=5)

    def _draw_overview(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        gap = 12; third = (area.width - 2 * gap) // 3
        self._gauge(surface, pygame.Rect(area.x, area.y, third, 190), "BOARD CONFIDENCE",
                    self.confidence["score"], self.confidence["label"])
        self._gauge(surface, pygame.Rect(area.x + third + gap, area.y, third, 190), "MANAGER REPUTATION",
                    self.reputation["score"], self.reputation["label"])
        status = Card(pygame.Rect(area.x + 2 * (third + gap), area.y, area.right - area.x - 2 * (third + gap), 190),
                      "SEASON STATUS"); status.draw(surface)
        my_row = next((r for r in self.standings if r["team_id"] == self.context["team"]["id"]), None)
        rows = [("League position", f"{my_row['position']} of {len(self.standings)}" if my_row else "—"),
                ("Record", f"{my_row['won']}W {my_row['lost']}L {my_row['tied']}T" if my_row else "—"),
                ("Points", my_row["points"] if my_row else "—"),
                ("Net run rate", f"{my_row['net_run_rate']:+.2f}" if my_row else "—")]
        y = status.rect.y + 56
        for label, value in rows:
            text(surface, label, (status.rect.x + 16, y), 11, MUTED)
            text(surface, value, (status.rect.right - 16, y), 12, WHITE, bold=True, anchor="topright"); y += 30
        board = Card(pygame.Rect(area.x, area.y + 202, area.width, area.height - 202), "BOARD VERDICT"); board.draw(surface)
        verdicts = {"Delighted": "The board is thrilled with the club's direction. Budgets are safe and your standing grows.",
                    "Content": "The board is satisfied. Keep the club on its objective and support will continue.",
                    "Under pressure": "Results are short of the objective. A run of wins is needed to steady the boardroom.",
                    "Ultimatum": "The board's patience is nearly exhausted. Immediate results are required to keep your job."}
        text(surface, verdicts[self.confidence["label"]], (board.rect.x + 18, board.rect.y + 58), 13, WHITE)
        text(surface, "Reputation grows with wins and silverware, and unlocks bigger clubs and international honours.",
             (board.rect.x + 18, board.rect.y + 88), 11, MUTED)

    def _draw_ratings(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        card = Card(area, f"WORLD RATINGS — {self.discipline.upper()}", "TOP 20 • ALL CLUBS"); card.draw(surface)
        rows = world_ratings(self.world_players, self.discipline, 20)
        y = area.y + 52
        text(surface, "#", (area.x + 22, y), 10, MUTED, bold=True)
        text(surface, "PLAYER", (area.x + 56, y), 10, MUTED, bold=True)
        text(surface, "CLUB", (area.x + int(area.width * .45), y), 10, MUTED, bold=True)
        text(surface, "PTS", (area.right - 26, y), 10, MUTED, bold=True, anchor="topright")
        y += 22
        row_h = max(18, min(26, (area.height - 88) // 20))
        for row in rows:
            rr = pygame.Rect(area.x + 12, y, area.width - 24, row_h - 2)
            pygame.draw.rect(surface, CARD_ALT if row["rank"] % 2 else CARD, rr)
            if row["rank"] <= 3: pygame.draw.rect(surface, GOLD, (rr.x, rr.y, 3, rr.height))
            text(surface, row["rank"], (rr.x + 10, rr.y + 3), 11, GOLD if row["rank"] <= 3 else MUTED, bold=True)
            flag = pygame.Rect(rr.x + 36, rr.y + 3, 22, max(10, row_h - 10))
            draw_country_flag(surface, flag, row["nationality"])
            text(surface, clipped_text(row["name"], int(area.width * .3), 11), (rr.x + 66, rr.y + 3), 11, WHITE, bold=row["rank"] <= 3)
            text(surface, clipped_text(row["team"], int(area.width * .3), 10), (area.x + int(area.width * .45), rr.y + 4), 10, MUTED)
            text(surface, row["points"], (area.right - 26, rr.y + 3), 11, WHITE, bold=True, anchor="topright")
            y += row_h

    def _draw_awards(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        gap = 12; half_w = (area.width - gap) // 2; half_h = (area.height - gap) // 2
        cells = [pygame.Rect(area.x, area.y, half_w, half_h),
                 pygame.Rect(area.x + half_w + gap, area.y, half_w, half_h),
                 pygame.Rect(area.x, area.y + half_h + gap, half_w, half_h),
                 pygame.Rect(area.x + half_w + gap, area.y + half_h + gap, half_w, half_h)]
        for rect, (title, winner) in zip(cells, self.awards.items()):
            card = Card(rect, title.upper(), "CURRENT LEADER"); card.draw(surface)
            text(surface, winner["name"], (rect.centerx, rect.centery + 6), 17, GOLD, bold=True, anchor="center")
            text(surface, winner["team"], (rect.centerx, rect.centery + 33), 11, MUTED, anchor="center")
            flag = pygame.Rect(rect.centerx - 14, rect.centery + 50, 28, 18)
            draw_country_flag(surface, flag, winner["nationality"])

    def _draw_trophies(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        card = Card(area, "TROPHY CABINET", f"{len(self.honours)} HONOURS"); card.draw(surface)
        if not self.honours:
            text(surface, "The cabinet is waiting for its first trophy.", (area.centerx, area.centery - 12), 15, MUTED, anchor="center")
            text(surface, "Win the league or the knockout cup to start the collection.", (area.centerx, area.centery + 14), 11, DIM, anchor="center")
            return
        y = area.y + 60
        for honour in self.honours[-12:]:
            pygame.draw.circle(surface, GOLD, (area.x + 34, y + 9), 8)
            text(surface, honour.get("title", "Honour"), (area.x + 54, y), 13, WHITE, bold=True)
            text(surface, honour.get("season", ""), (area.right - 24, y), 12, MUTED, anchor="topright")
            y += 30

    def draw(self, surface: pygame.Surface) -> None:
        for _, button in self.tab_buttons: button.draw(surface)
        if self.active_tab == "World Ratings":
            for _, button in self.discipline_buttons: button.draw(surface)
        area = pygame.Rect(self.content_rect.x + 18, self.content_rect.y + 112,
                           self.content_rect.width - 36, self.content_rect.height - 130)
        if self.active_tab == "Overview": self._draw_overview(surface, area)
        elif self.active_tab == "World Ratings": self._draw_ratings(surface, area)
        elif self.active_tab == "Awards": self._draw_awards(surface, area)
        else: self._draw_trophies(surface, area)
