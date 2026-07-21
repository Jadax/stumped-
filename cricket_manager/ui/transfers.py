"""Transfer market: incoming bids, scouting, offers, and player listing."""
from __future__ import annotations
import pygame
from src.models.currency import format_money
from database import (create_inbox_message, fetch_players, fetch_transfer_offers, get_team_summary, resolve_transfer_offer,
                      scout_players, set_transfer_listed, submit_transfer_offer)
from .shared_components import BaseScreen, estimated_value
from .widgets import Button, ButtonStyle, Card, DataTable, Slider
from .widgets.datatable import Column
from .widgets.common import GOLD, GREEN, MUTED, RED, WHITE, text, clipped_text


class TransfersScreen(BaseScreen):
    title = "Transfers"
    ROLES = ["All", "Batsman", "Bowler", "All-Rounder", "Wicketkeeper"]
    NATIONALITIES = ["All", "English", "Australian", "Indian", "Pakistani", "South African", "New Zealander", "West Indian"]

    def build(self) -> None:
        self.team_id, self.db = self.context["team"]["id"], self.context["database_path"]
        self.offers = fetch_transfer_offers(self.team_id, self.db)
        self.role_index = self.nationality_index = 0; self.age_band = 0; self.rating_band = 0
        self.scouted = scout_players(exclude_team=self.team_id, limit=None, database_path=self.db)
        self.selected_scout = self.scouted[0] if self.scouted else None
        self.list_index = 0
        self._layout()

    def _layout(self) -> None:
        x, y, w = self.content_rect.x + 18, self.content_rect.y + 76, self.content_rect.width - 36
        gap, top_h = 10, 205; left_w = int(w * .47)
        self.incoming_rect = pygame.Rect(x, y, left_w, top_h)
        self.scout_rect = pygame.Rect(x + left_w + gap, y, w - left_w - gap, top_h)
        bottom_y = y + top_h + gap; bottom_h = self.content_rect.bottom - 16 - bottom_y
        self.results_rect = pygame.Rect(x, bottom_y, int(w * .64), bottom_h)
        self.offer_rect = pygame.Rect(self.results_rect.right + gap, bottom_y, self.content_rect.right - 18 - self.results_rect.right - gap, bottom_h)
        self.offer_buttons = []
        for i, offer in enumerate(self.offers[:4]):
            yy = self.incoming_rect.y + 55 + i * 34
            self.offer_buttons.append((offer, Button(pygame.Rect(self.incoming_rect.right - 145, yy, 62, 25), "ACCEPT", ButtonStyle.PRIMARY),
                                       Button(pygame.Rect(self.incoming_rect.right - 76, yy, 58, 25), "REJECT", ButtonStyle.DANGER)))
        bx = self.scout_rect.x + 14; by = self.scout_rect.y + 55; bw = (self.scout_rect.width - 38) // 2
        self.role_button = Button(pygame.Rect(bx, by, bw, 28), "ROLE: ALL")
        self.nation_button = Button(pygame.Rect(bx + bw + 10, by, bw, 28), "NATION: ALL")
        self.age_button = Button(pygame.Rect(bx, by + 36, bw, 28), "AGE: 16–40")
        self.rating_button = Button(pygame.Rect(bx + bw + 10, by + 36, bw, 28), "OVR: 0–100")
        self.search_button = Button(pygame.Rect(bx, by + 78, self.scout_rect.width - 28, 30), "SEARCH MARKET", ButtonStyle.SUCCESS)
        table = pygame.Rect(self.results_rect.x + 10, self.results_rect.y + 48, self.results_rect.width - 20, self.results_rect.height - 58)
        cols = [Column("name", "Player", .22), Column("age", "Age", .06), Column("role", "Role", .14),
                Column("estimated_overall", "OVR~", .08), Column("estimated_potential", "POT~", .08),
                Column("confidence", "Scout %", .1), Column("sale_reason", "Availability", .16),
                Column("asking_price", "Price", .16, "right", lambda v: format_money(v, compact=True))]
        rows = self.scouted
        self.table = DataTable(table, cols, rows, 30)
        ox = self.offer_rect.x + 16; ow = self.offer_rect.width - 32
        base_value = estimated_value(self.selected_scout) if self.selected_scout else 1_000_000
        self.bid_slider = Slider(pygame.Rect(ox, self.offer_rect.y + 105, ow, 38), "Transfer bid", 100_000, 20_000_000,
                                 min(20_000_000, max(100_000, base_value)), 100_000, lambda v: format_money(int(v)))
        self.wage_slider = Slider(pygame.Rect(ox, self.offer_rect.y + 153, ow, 38), "Weekly wage", 500, 100_000, 15_000, 500,
                                  lambda v: format_money(int(v)))
        self.submit_button = Button(pygame.Rect(ox, self.offer_rect.y + 202, ow, 29), "SUBMIT OFFER", ButtonStyle.PRIMARY, enabled=bool(self.selected_scout))
        self.list_cycle = Button(pygame.Rect(ox, self.offer_rect.bottom - 78, ow, 27), "SELECT SQUAD PLAYER")
        self.list_button = Button(pygame.Rect(ox, self.offer_rect.bottom - 44, ow, 27), "LIST / UNLIST", ButtonStyle.SECONDARY)

    def _refresh_market(self) -> None:
        age_ranges = [(16, 40), (16, 20), (21, 27), (28, 34), (35, 45)]
        rating_ranges = [(0, 100), (40, 59), (60, 69), (70, 79), (80, 100)]
        amin, amax = age_ranges[self.age_band]; rmin, rmax = rating_ranges[self.rating_band]
        self.scouted = scout_players(self.ROLES[self.role_index], amin, amax, rmin, rmax,
                                     self.NATIONALITIES[self.nationality_index], self.team_id, None, self.db)
        self.selected_scout = self.scouted[0] if self.scouted else None
        self.table.set_rows(self.scouted)

    def process_event(self, event: pygame.event.Event) -> None:
        for offer, accept, reject in self.offer_buttons:
            if accept.process_event(event) or reject.process_event(event):
                accepted = accept.rect.collidepoint(getattr(event, "pos", (-1, -1)))
                success = resolve_transfer_offer(offer["id"], accepted, self.db)
                self.context["players"] = fetch_players(self.team_id, self.db); self.context["team"] = get_team_summary(self.team_id, self.db)
                self.context["toast"] = "Transfer accepted" if accepted and success else "Transfer rejected" if not accepted else "Buyer could not fund the transfer"
                self.build(); return
        if self.role_button.process_event(event):
            self.role_index = (self.role_index + 1) % len(self.ROLES); self.role_button.label = f"ROLE: {self.ROLES[self.role_index].upper()}"
        if self.nation_button.process_event(event):
            self.nationality_index = (self.nationality_index + 1) % len(self.NATIONALITIES); self.nation_button.label = f"NATION: {self.NATIONALITIES[self.nationality_index].upper()}"
        if self.age_button.process_event(event):
            self.age_band = (self.age_band + 1) % 5; self.age_button.label = ["AGE: 16–40", "AGE: U21", "AGE: 21–27", "AGE: 28–34", "AGE: 35+"][self.age_band]
        if self.rating_button.process_event(event):
            self.rating_band = (self.rating_band + 1) % 5; self.rating_button.label = ["OVR: 0–100", "OVR: 40–59", "OVR: 60–69", "OVR: 70–79", "OVR: 80+"][self.rating_band]
        if self.search_button.process_event(event): self._refresh_market()
        selected = self.table.process_event(event)
        if selected:
            self.selected_scout = selected; self.bid_slider.value = min(20_000_000, max(100_000, selected["asking_price"])); self.submit_button.enabled = True
        self.bid_slider.process_event(event); self.wage_slider.process_event(event)
        if self.submit_button.process_event(event) and self.selected_scout:
            submit_transfer_offer(self.selected_scout["id"], self.team_id, int(self.bid_slider.value), int(self.wage_slider.value),
                                  self.context.get("current_date", "2026-04-01"), self.db)
            create_inbox_message("MEDIUM", "Transfer offer submitted",
                                 f"An offer has been sent for {self.selected_scout['name']}. The selling club will respond shortly.",
                                 timestamp=f"{self.context.get('current_date','2026-04-01')} 12:00", database_path=self.db)
            self.context["refresh_inbox"] = True
            self.context["toast"] = f"Offer submitted for {self.selected_scout['name']}"; self.submit_button.enabled = False
        squad = self.context["players"]
        if self.list_cycle.process_event(event) and squad:
            self.list_index = (self.list_index + 1) % len(squad)
        if self.list_button.process_event(event) and squad:
            player = squad[self.list_index]; new_value = not bool(player.get("transfer_listed", 0))
            set_transfer_listed(player["id"], new_value, self.db); player["transfer_listed"] = int(new_value)
            self.context["toast"] = f"{player['name']} {'listed' if new_value else 'removed from list'}"

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_header(surface, "Negotiate bids, scout targets, and manage player availability")
        for rect, title, subtitle in ((self.incoming_rect, "INCOMING OFFERS", f"{len(self.offers)} PENDING"),
                                      (self.scout_rect, "MARKET DATABASE", "ALL REGISTERED PLAYERS"),
                                      (self.results_rect, "PLAYER SEARCH", f"{len(self.scouted)} MATCHES • CLICK TO SELECT"),
                                      (self.offer_rect, "MAKE OFFER & LISTING", "TRANSFER DESK")):
            Card(rect, title, subtitle).draw(surface)
        if not self.offers: text(surface, "No incoming offers", self.incoming_rect.center, 14, MUTED, anchor="center")
        for i, (offer, accept, reject) in enumerate(self.offer_buttons):
            y = self.incoming_rect.y + 57 + i * 34
            text(surface, clipped_text(offer["player_name"], 145, 11), (self.incoming_rect.x + 14, y), 11, WHITE, bold=True)
            text(surface, f"{offer['to_name']} • {format_money(offer['fee'], compact=True)}", (self.incoming_rect.x + 160, y), 10, GOLD)
            accept.draw(surface); reject.draw(surface)
        for button in (self.role_button, self.nation_button, self.age_button, self.rating_button, self.search_button): button.draw(surface)
        self.table.draw(surface)
        if self.selected_scout:
            text(surface, self.selected_scout["name"], (self.offer_rect.x + 16, self.offer_rect.y + 53), 16, GOLD, bold=True)
            scouted_ovr = self.selected_scout.get("estimated_overall", self.selected_scout["overall"])
            confidence = self.selected_scout.get("confidence")
            confidence_text = f" • scout confidence {confidence}%" if confidence is not None else ""
            text(surface, f"{self.selected_scout['role']} • OVR~ {scouted_ovr} • {self.selected_scout['nationality']}{confidence_text}", (self.offer_rect.x + 16, self.offer_rect.y + 78), 11, MUTED)
            sale_colour = GREEN if self.selected_scout.get("for_sale") else RED
            text(surface, f"{self.selected_scout.get('sale_reason','Not for sale')} • asking {format_money(self.selected_scout.get('asking_price',0), compact=True)}",
                 (self.offer_rect.x + 16, self.offer_rect.y + 94), 10, sale_colour)
        self.bid_slider.draw(surface); self.wage_slider.draw(surface); self.submit_button.draw(surface)
        squad = self.context["players"]
        if squad:
            p = squad[self.list_index]; status = "LISTED" if p.get("transfer_listed") else "NOT LISTED"
            self.list_cycle.label = f"{clipped_text(p['name'], 135, 11)} • {status}"
        self.list_cycle.draw(surface); self.list_button.draw(surface)
        if self.context.get("toast"): text(surface, self.context.pop("toast"), (self.content_rect.right - 20, self.content_rect.y + 52), 11, GREEN, anchor="topright")
