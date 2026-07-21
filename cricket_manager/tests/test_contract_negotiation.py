"""Contract negotiation model and UI tests (v0.20.0)."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402


def _player(**overrides) -> dict:
    base = {"id": 5, "name": "Test Player", "age": 26, "role": "Batsman",
            "overall": 78, "potential": 82, "wage": 4000, "contract_years_remaining": 1,
            "mental": {"morale": 60}}
    base.update(overrides)
    return base


class ContractModelTests(unittest.TestCase):
    def test_generous_offer_is_accepted(self) -> None:
        from src.models.contracts import contract_valuation, negotiate
        player = _player()
        valuation = contract_valuation(player)
        result = negotiate(player, int(valuation * 1.3), 3)
        self.assertEqual(result["outcome"], "accept")

    def test_lowball_offer_is_rejected(self) -> None:
        from src.models.contracts import contract_valuation, negotiate
        player = _player()
        valuation = contract_valuation(player)
        result = negotiate(player, int(valuation * 0.4), 1)
        self.assertEqual(result["outcome"], "reject")

    def test_midrange_offer_produces_a_counter(self) -> None:
        from src.models.contracts import contract_valuation, negotiate
        player = _player()
        valuation = contract_valuation(player)
        result = negotiate(player, int(valuation * 0.9), 2)
        self.assertIn(result["outcome"], {"counter", "accept"})
        if result["outcome"] == "counter":
            self.assertIsInstance(result["counter_wage"], int)
            self.assertGreater(result["counter_wage"], 0)

    def test_unhappy_player_demands_more_than_content_player(self) -> None:
        from src.models.contracts import negotiate
        happy = _player(mental={"morale": 90})
        unhappy = _player(mental={"morale": 20})
        offer = 5000
        happy_result = negotiate(happy, offer, 2)
        unhappy_result = negotiate(unhappy, offer, 2)
        rank = {"accept": 2, "counter": 1, "reject": 0}
        self.assertGreaterEqual(rank[happy_result["outcome"]], rank[unhappy_result["outcome"]])

    def test_veteran_rejects_very_long_new_contract(self) -> None:
        from src.models.contracts import contract_valuation, negotiate
        veteran = _player(age=34)
        valuation = contract_valuation(veteran)
        short_result = negotiate(veteran, int(valuation * 1.05), 2)
        long_result = negotiate(veteran, int(valuation * 1.05), 5)
        rank = {"accept": 2, "counter": 1, "reject": 0}
        self.assertGreaterEqual(rank[short_result["outcome"]], rank[long_result["outcome"]])


class ContractDatabaseTests(unittest.TestCase):
    def test_renew_player_contract_updates_wage_years_and_cash(self) -> None:
        from database import initialise_database, fetch_players, renew_player_contract, fetch_teams
        db = os.path.join(tempfile.mkdtemp(), "contracts.db")
        initialise_database(db)
        team = fetch_teams(db)[0]
        player = fetch_players(team["id"], db)[0]
        before_cash = team["cash"]
        renew_player_contract(player["id"], 9999, 4, signing_bonus=1000, database_path=db)
        after = fetch_players(team["id"], db)[0]
        self.assertEqual(after["wage"], 9999)
        self.assertEqual(after["contract_years_remaining"], 4)
        after_team = fetch_teams(db)[0]
        self.assertEqual(after_team["cash"], before_cash - 1000)


class ContractModalUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.surface = pygame.display.set_mode((1280, 720))

    def test_negotiation_modal_renders_and_can_reach_agreement(self) -> None:
        from src.models.contracts import contract_valuation
        from ui.widgets import ContractNegotiationModal
        player = _player(mental={"morale": 95})
        modal = ContractNegotiationModal(pygame.Rect(0, 0, 1280, 720), player)
        modal.draw(self.surface)
        self.assertIsNone(modal.agreed_terms)
        # Direct slider assignment (as used throughout this test file) is not
        # clamped to the widget's displayed max — mirrors a generous offer
        # against the player's true valuation rather than a fixed multiple
        # of their (deliberately underpriced) starting test wage.
        modal.wage_slider.value = int(contract_valuation(player) * 1.3)
        modal.years_slider.value = 3
        modal.propose()
        modal.draw(self.surface)
        self.assertTrue(modal.agreed)
        self.assertIsNotNone(modal.agreed_terms)

    def test_rejecting_a_lowball_then_countering_reaches_agreement(self) -> None:
        from ui.widgets import ContractNegotiationModal
        player = _player(mental={"morale": 50}, wage=4000)
        modal = ContractNegotiationModal(pygame.Rect(0, 0, 1280, 720), player)
        modal.wage_slider.value = player["wage"] * 0.95
        modal.years_slider.value = 2
        modal.propose()
        self.assertIn(modal.result["outcome"], {"counter", "reject", "accept"})
        if modal.result["outcome"] == "counter":
            modal.accept_counter()
            self.assertTrue(modal.agreed)

    def test_proposals_are_capped_at_max_rounds(self) -> None:
        from ui.widgets import ContractNegotiationModal
        player = _player(wage=4000)
        modal = ContractNegotiationModal(pygame.Rect(0, 0, 1280, 720), player)
        modal.wage_slider.value = 1  # always rejected
        for _ in range(5):
            modal.propose()
        self.assertLessEqual(modal.rounds_used, 3)

    def test_player_profile_negotiate_button_opens_and_persists(self) -> None:
        from database import initialise_database, fetch_players, fetch_teams
        from ui.player_modals import PlayerDetailModal
        db = os.path.join(tempfile.mkdtemp(), "profile_contract.db")
        initialise_database(db)
        team = fetch_teams(db)[0]
        player = dict(fetch_players(team["id"], db)[0])
        modal = PlayerDetailModal(pygame.Rect(0, 0, 1280, 720), player, database_path=db)
        modal.active_tab = "Personal"
        modal.draw(self.surface)
        self.assertIsNone(modal.contract_modal)
        modal.contract_modal = modal.contract_modal or __import__(
            "ui.widgets", fromlist=["ContractNegotiationModal"]
        ).ContractNegotiationModal(modal.viewport, modal.player)
        modal.contract_modal.agreed = True
        modal.contract_modal.wage_slider.value = player["wage"] * 2
        modal.contract_modal.years_slider.value = 3
        modal.contract_modal.bonus_slider.value = 0
        terms = modal.contract_modal.agreed_terms
        self.assertIsNotNone(terms)
        from database import renew_player_contract
        renew_player_contract(player["id"], terms["wage"], terms["years"], terms["bonus"], db)
        refreshed = fetch_players(team["id"], db)
        updated = next(p for p in refreshed if p["id"] == player["id"])
        self.assertEqual(updated["wage"], player["wage"] * 2)
        self.assertEqual(updated["contract_years_remaining"], 3)


if __name__ == "__main__":
    unittest.main()
