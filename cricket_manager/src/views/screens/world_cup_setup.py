"""Qualified national-team selection for World Cup mode."""
from __future__ import annotations

import pygame

from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import BG, CARD_ALT, GOLD, GREEN, MUTED, WHITE, text


class WorldCupSetupScreen(BaseScreen):
    title = "World Cup Setup"

    def build(self) -> None:
        self.nations = [c for c in self.context["game_controller"].countries if c["membership"] == "Full Member"]
        self.selected_id = self.nations[0]["id"]
        r = self.content_rect
        self.card = Card(pygame.Rect(r.x + 34, r.y + 105, r.width - 68, r.height - 183), "Qualified Nations", "12 FULL MEMBERS")
        self.nation_buttons = {}
        cols, gap = 4, 13
        bw = (self.card.content_rect.width - gap * (cols - 1)) // cols
        bh = 78
        for i, nation in enumerate(self.nations):
            col, row = i % cols, i // cols
            rect = pygame.Rect(self.card.content_rect.x + col * (bw + gap), self.card.content_rect.y + row * (bh + 13), bw, bh)
            self.nation_buttons[nation["id"]] = Button(rect, f"{nation['flag']}  {nation['name'].upper()}", ButtonStyle.PRIMARY, selected=i == 0)
        self.back_button = Button(pygame.Rect(r.x + 34, r.bottom - 57, 150, 39), "BACK", ButtonStyle.SECONDARY)
        self.confirm_button = Button(pygame.Rect(r.right - 254, r.bottom - 57, 220, 39), "START WORLD CUP", ButtonStyle.SUCCESS)

    def process_event(self, event: pygame.event.Event) -> None:
        if self.back_button.process_event(event): self.navigate("New Game Setup"); return
        if self.confirm_button.process_event(event):
            self.context["game_controller"].confirm_world_cup_team(self.selected_id); return
        for nation_id, button in self.nation_buttons.items():
            if button.process_event(event):
                self.selected_id = nation_id
                for other_id, other in self.nation_buttons.items(): other.selected = other_id == nation_id
                self.mark_dirty()

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BG, self.content_rect)
        text(surface, "LEAD A NATION", (self.content_rect.x + 36, self.content_rect.y + 24), 30, WHITE, True)
        text(surface, "Choose a qualified national team for a focused global tournament campaign.",
             (self.content_rect.x + 37, self.content_rect.y + 65), 15, MUTED)
        self.card.draw(surface)
        for nation in self.nations:
            button = self.nation_buttons[nation["id"]]
            button.draw(surface)
            text(surface, nation["code"], (button.rect.centerx, button.rect.bottom - 19), 11,
                 GOLD if nation["id"] == self.selected_id else MUTED, True, anchor="center")
        self.back_button.draw(surface); self.confirm_button.draw(surface)
