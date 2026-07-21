"""Contract negotiation modal — offer terms, read the reaction, close the deal."""
from __future__ import annotations

import pygame

from src.models.contracts import negotiate
from src.models.currency import format_money
from .button import Button, ButtonStyle
from .common import CARD_ALT, DIM, GOLD, GREEN, MUTED, RED, WHITE, text, wrap_text
from .modal import Modal
from .slider import Slider

MAX_ROUNDS = 3


class ContractNegotiationModal(Modal):
    """Propose wage/length/bonus terms; the player accepts, counters, or walks."""

    def __init__(self, viewport: pygame.Rect, player: dict, league_reputation: int = 70):
        super().__init__(viewport, "Contract Negotiation", (620, 460))
        self.player, self.league_reputation = player, league_reputation
        self.rounds_used = 0
        self.result: dict | None = None
        self.agreed = False
        c = self.content_rect
        current_wage = int(player.get("wage", 1000))
        self.wage_slider = Slider(pygame.Rect(c.x + 20, c.y + 70, c.width - 40, 50),
                                  "Weekly wage", current_wage, current_wage * 3, current_wage, 50,
                                  lambda v: format_money(int(v)))
        self.years_slider = Slider(pygame.Rect(c.x + 20, c.y + 140, c.width - 40, 50),
                                   "Contract length (years)", 1, 5, 2, 1, lambda v: f"{int(v)} yr")
        self.bonus_slider = Slider(pygame.Rect(c.x + 20, c.y + 210, c.width - 40, 50),
                                   "Signing bonus", 0, current_wage * 10, 0, 250,
                                   lambda v: format_money(int(v)))
        self.propose_button = Button(pygame.Rect(c.x + 20, c.bottom - 96, 170, 34), "PROPOSE TERMS", ButtonStyle.PRIMARY)
        self.accept_counter_button = Button(pygame.Rect(c.x + 200, c.bottom - 96, 190, 34),
                                            "ACCEPT COUNTER", ButtonStyle.SUCCESS, enabled=False)
        self.close_button = Button(pygame.Rect(c.right - 130, c.bottom - 96, 110, 34), "WALK AWAY", ButtonStyle.DANGER)

    @property
    def agreed_terms(self) -> dict[str, int] | None:
        """The final wage/years/bonus once a deal is struck, else ``None``."""
        if not self.agreed:
            return None
        return {"wage": int(self.wage_slider.value), "years": int(self.years_slider.value),
               "bonus": int(self.bonus_slider.value)}

    def propose(self) -> None:
        """Submit the current slider terms as one negotiation round."""
        if self.rounds_used >= MAX_ROUNDS:
            return
        self.rounds_used += 1
        self.result = negotiate(self.player, int(self.wage_slider.value), int(self.years_slider.value),
                                int(self.bonus_slider.value), self.league_reputation)
        if self.result["outcome"] == "accept":
            self._mark_agreed()
        elif self.result["outcome"] == "counter":
            self.accept_counter_button.enabled = True
        if self.rounds_used >= MAX_ROUNDS and self.result["outcome"] != "accept":
            self.propose_button.enabled = False

    def accept_counter(self) -> None:
        """Sign at the player's last counter-offer wage."""
        if not (self.result and self.result.get("counter_wage")):
            return
        self.wage_slider.value = self.result["counter_wage"]
        self.result = {"outcome": "accept", "counter_wage": None,
                       "reason": f"{self.player.get('name', 'The player')} signs at the agreed figure."}
        self._mark_agreed()

    def _mark_agreed(self) -> None:
        self.agreed = True
        self.propose_button.label = "AGREED"
        self.close_button.label = "DONE"

    def process_event(self, event: pygame.event.Event) -> bool:
        if self.agreed:
            return self.close_button.process_event(event) or super().process_event(event)
        for slider in (self.wage_slider, self.years_slider, self.bonus_slider):
            slider.process_event(event)
        if self.propose_button.process_event(event):
            self.propose()
        if self.accept_counter_button.process_event(event):
            self.accept_counter()
        return self.close_button.process_event(event) or super().process_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        c = self.content_rect
        text(surface, self.player.get("name", "Player"), (c.x + 20, c.y + 14), 18, WHITE, bold=True)
        text(surface, f"Currently {format_money(int(self.player.get('wage', 0)))}/wk • "
                      f"{self.player.get('contract_years_remaining', 1)} yr remaining • "
                      f"Round {min(self.rounds_used + 1, MAX_ROUNDS)} of {MAX_ROUNDS}",
             (c.x + 20, c.y + 40), 11, MUTED)
        for slider in (self.wage_slider, self.years_slider, self.bonus_slider):
            slider.draw(surface)
        banner = pygame.Rect(c.x + 20, c.bottom - 152, c.width - 40, 46)
        pygame.draw.rect(surface, CARD_ALT, banner, border_radius=6)
        if self.result:
            colour = GREEN if self.result["outcome"] == "accept" else GOLD if self.result["outcome"] == "counter" else RED
            lines = wrap_text(self.result["reason"], banner.width - 24, 12)
            for i, line in enumerate(lines[:2]):
                text(surface, line, (banner.x + 12, banner.y + 6 + i * 17), 12, colour, bold=True)
            if self.result["outcome"] == "counter" and self.result.get("counter_wage"):
                text(surface, f"Counter: {format_money(self.result['counter_wage'])}/wk",
                     (banner.right - 12, banner.y + 6), 11, GOLD, bold=True, anchor="topright")
        else:
            text(surface, "Set your terms and propose — the player will accept, counter, or reject.",
                 (banner.x + 12, banner.y + 14), 12, MUTED)
        self.propose_button.draw(surface)
        self.accept_counter_button.draw(surface)
        self.close_button.draw(surface)
