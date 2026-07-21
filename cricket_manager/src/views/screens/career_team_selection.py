"""Career club selection with expectations and squad metrics."""
from __future__ import annotations

import pygame
from src.models.currency import format_money

from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import ACCENT, BG, BORDER, CARD, CARD_ALT, GOLD, GREEN, MUTED, RED, WHITE, clipped_text, text


class CareerTeamSelectionScreen(BaseScreen):
    title = "Career Team Selection"

    def build(self) -> None:
        all_teams = self.context["game_controller"].selectable_teams()
        enabled = set(self.context.get("new_game_setup", {}).get("enabled_countries", []))
        primary = self.context.get("new_game_setup", {}).get("primary_country")
        self.teams = [team for team in all_teams if (team.get("country_id") == primary if primary else
                      (not enabled or team.get("country_id") in enabled))] or all_teams
        self.selected_id = int(self.teams[0]["id"]) if self.teams else 0
        self.scroll = 0
        self._layout()

    def _layout(self) -> None:
        r, s = self.content_rect, self.scale
        self.list_card = Card(pygame.Rect(r.x + 28, r.y + 104, int(r.width * .59), r.height - 180), "Available Clubs", "SELECT ONE CLUB")
        self.detail_card = Card(pygame.Rect(self.list_card.rect.right + 16, r.y + 104,
                                            r.right - 28 - self.list_card.rect.right - 16, r.height - 180),
                                "Club Briefing", "BOARD EXPECTATIONS")
        self.visible_count = max(1, (self.list_card.content_rect.height - 27) // 41)
        self._position_rows()
        self.back_button = Button(pygame.Rect(r.x + 28, r.bottom - 55, 150, 38), "BACK", ButtonStyle.SECONDARY)
        self.confirm_button = Button(pygame.Rect(r.right - 248, r.bottom - 55, 220, 38), "CONFIRM CLUB", ButtonStyle.SUCCESS)

    def _position_rows(self) -> None:
        self.rows = []
        y = self.list_card.content_rect.y + 26
        for team in self.teams[self.scroll:self.scroll + self.visible_count]:
            self.rows.append((int(team["id"]), pygame.Rect(self.list_card.content_rect.x, y, self.list_card.content_rect.width, 39)))
            y += 41

    @property
    def selected(self) -> dict:
        return next((team for team in self.teams if int(team["id"]) == self.selected_id), self.teams[0])

    @staticmethod
    def expectation(team: dict) -> tuple[str, str]:
        rating = float(team.get("average_rating") or 50)
        if team["division"] == 1 and rating >= 68:
            return "TITLE CHALLENGE", "Compete for the championship and reach the cup semi-final."
        if team["division"] == 1:
            return "MID-TABLE", "Build sustainably and finish clear of relegation."
        if rating >= 56:
            return "PROMOTION PUSH", "Challenge for a top-two promotion position."
        return "DEVELOP & SURVIVE", "Avoid the bottom two while developing younger players."

    def process_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL and self.list_card.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(max(0, len(self.teams) - self.visible_count), self.scroll - event.y))
            self._position_rows(); self.mark_dirty(); return
        if self.back_button.process_event(event):
            self.navigate("New Game Setup"); return
        if self.confirm_button.process_event(event) and self.selected_id:
            self.context["game_controller"].confirm_career_team(self.selected_id); return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for team_id, rect in self.rows:
                if rect.collidepoint(event.pos):
                    self.selected_id = team_id; self.mark_dirty(); break

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        text(surface, "CHOOSE YOUR CLUB", (self.content_rect.x + 30, self.content_rect.y + 24), 30, WHITE, True)
        text(surface, "Every club has a different budget, squad profile and board mandate.",
             (self.content_rect.x + 31, self.content_rect.y + 64), 15, MUTED)
        self.list_card.draw(surface); self.detail_card.draw(surface)
        headers = [("CLUB", .02), ("DIV", .57), ("SQUAD", .68), ("AVG", .82), ("BUDGET", .98)]
        hy = self.list_card.content_rect.y
        for label, fraction in headers:
            text(surface, label, (self.list_card.content_rect.x + int(self.list_card.content_rect.width * fraction), hy),
                 11, MUTED, True, anchor="topright" if fraction > .6 else "topleft")
        visible = self.teams[self.scroll:self.scroll + self.visible_count]
        for index, (team, (_, row)) in enumerate(zip(visible, self.rows), start=self.scroll):
            selected = int(team["id"]) == self.selected_id
            pygame.draw.rect(surface, CARD.lerp(GOLD, .22) if selected else CARD_ALT if index % 2 else CARD, row)
            if selected: pygame.draw.rect(surface, GOLD, row, 2)
            crest = (row.x + 19, row.centery)
            pygame.draw.aacircle(surface, GREEN if team["division"] == 1 else ACCENT, crest, 12)
            text(surface, str(team["id"]), crest, 9, WHITE, True, anchor="center")
            text(surface, clipped_text(team["name"], int(row.width * .43), 13), (row.x + 39, row.y + 11), 13, WHITE, selected)
            values = [team["division"], team["squad_size"], f"{team['average_rating']:.1f}", format_money(team['cash'], compact=True)]
            for value, fraction in zip(values, [.61, .76, .88, .98]):
                text(surface, value, (row.x + int(row.width * fraction), row.y + 11), 12, GOLD if fraction == .88 else WHITE, anchor="topright")
        if len(self.teams) > self.visible_count:
            text(surface, f"Showing {self.scroll+1}–{min(len(self.teams),self.scroll+self.visible_count)} of {len(self.teams)} • Mouse wheel to scroll",
                 (self.list_card.content_rect.centerx, self.list_card.rect.bottom - 17), 10, MUTED, anchor="center")
        self._draw_details(surface)
        self.back_button.draw(surface); self.confirm_button.draw(surface)

    def _draw_details(self, surface: pygame.Surface) -> None:
        team = self.selected
        c = self.detail_card.content_rect
        centre = (c.centerx, c.y + 58)
        pygame.draw.aacircle(surface, pygame.Color("#1e552d"), centre, 46)
        pygame.draw.aacircle(surface, GOLD, centre, 46, 2)
        text(surface, "S!", centre, 24, WHITE, True, anchor="center")
        text(surface, team["name"], (c.centerx, c.y + 117), 20, WHITE, True, anchor="center")
        expectation, detail = self.expectation(team)
        y = c.y + 162
        stats = [("Starting cash", format_money(team['cash'])), ("Squad size", team["squad_size"]),
                 ("Average rating", f"{team['average_rating']:.1f}"), ("Stadium", f"{team['stadium_capacity']:,} seats"),
                 ("Training level", f"Level {team['training_level']}")]
        for label, value in stats:
            text(surface, label, (c.x + 4, y), 13, MUTED); text(surface, value, (c.right - 4, y), 13, WHITE, True, anchor="topright"); y += 29
        pygame.draw.line(surface, BORDER, (c.x, y + 5), (c.right, y + 5))
        text(surface, expectation, (c.x + 4, y + 24), 14, GOLD, True)
        text(surface, detail, (c.x + 4, y + 52), 12, WHITE)
