"""v5.3.1: agents, agent-led contract talks, transfer personal terms, sponsor
negotiation and training-driven development."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import shutil
import tempfile
import unittest

from database import (accept_sponsor_offer, club_development_factors, connect, current_sponsorship, fetch_players,
                      fetch_sponsor_offers, generate_sponsor_offers, initialise_database, negotiate_sponsor_offer,
                      open_contract_talks, personal_terms_agreed, respond_to_user_bids, submit_contract_offer,
                      submit_transfer_offer)

_TEMPLATE: Path | None = None


def _fresh_save(directory: str) -> Path:
    global _TEMPLATE
    if _TEMPLATE is None:
        _TEMPLATE = Path(tempfile.mkdtemp()) / "template.db"
        initialise_database(_TEMPLATE)
    target = Path(directory) / "save.db"
    shutil.copy(_TEMPLATE, target)
    return target


class WorldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = _fresh_save(self.directory.name)
        with connect(self.database) as connection:
            self.user, self.today = connection.execute(
                'SELECT current_team_id, "current_date" FROM user_data').fetchone()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def query(self, sql: str, *args):
        with connect(self.database) as connection:
            return connection.execute(sql, args).fetchall()

    def senior(self) -> dict:
        return next(p for p in fetch_players(self.user, self.database) if not p.get("academy_squad") and p["age"] >= 20)


class AgentTests(WorldTest):
    def test_every_senior_professional_has_an_agent(self) -> None:
        self.assertGreater(self.query("SELECT COUNT(*) FROM agents")[0][0], 20)
        self.assertEqual(self.query(
            "SELECT COUNT(*) FROM players WHERE age>=18 AND academy_squad=0 AND agent_id IS NULL")[0][0], 0)

    def test_stars_mostly_use_super_agents(self) -> None:
        stars = self.query("SELECT AVG(a.super_agent) FROM players p JOIN agents a ON a.id=p.agent_id "
                           "WHERE p.overall>=80")[0][0]
        ordinary = self.query("SELECT AVG(a.super_agent) FROM players p JOIN agents a ON a.id=p.agent_id "
                              "WHERE p.overall<60")[0][0]
        self.assertGreater(stars, ordinary)


class ContractTalkTests(WorldTest):
    def test_meeting_the_demand_signs_and_charges_bonus_and_agent_fee(self) -> None:
        player = self.senior()
        talks = open_contract_talks(player, self.today, self.database)
        result = submit_contract_offer(player, talks["demand"]["wage"], talks["years"], talks["demand"]["bonus"],
                                       self.today, self.database)
        self.assertEqual(result["outcome"], "accept")
        self.assertEqual(self.query("SELECT wage FROM players WHERE id=?", player["id"])[0][0], talks["demand"]["wage"])
        categories = {row[0] for row in self.query("SELECT category FROM financial_log WHERE team_id=?", self.user)}
        if talks["agent"]:
            self.assertIn("Agent Fees", categories)
        if talks["demand"]["bonus"]:
            self.assertIn("Signing Bonuses", categories)

    def test_lowballing_burns_patience_until_the_agent_walks_out(self) -> None:
        player = self.senior()
        outcomes = []
        for _ in range(8):
            outcomes.append(submit_contract_offer(player, 100, 2, 0, self.today, self.database)["outcome"])
            if outcomes[-1] in ("walkout", "locked"):
                break
        self.assertIn("walkout", outcomes)
        again = submit_contract_offer(player, 10**7, 2, 0, self.today, self.database)
        self.assertEqual(again["outcome"], "locked", "talks stay closed after a walk-out")


class TransferBidTests(WorldTest):
    def target(self):
        return self.query("SELECT id, team_id FROM players WHERE team_id!=? AND academy_squad=0 AND age>=20 "
                          "ORDER BY overall DESC LIMIT 1", self.user)[0]

    def test_a_derisory_bid_is_rejected_by_the_selling_club(self) -> None:
        player_id, _ = self.target()
        submit_transfer_offer(player_id, self.user, 1_000, 10**6, "2026-03-01", self.database)
        outcomes = respond_to_user_bids("2026-03-02", self.user, self.database)
        self.assertEqual(outcomes[0]["result"], "rejected")

    def test_fee_agreed_but_wage_too_low_fails_on_personal_terms(self) -> None:
        player_id, _ = self.target()
        with connect(self.database) as connection:
            connection.execute("UPDATE teams SET cash=10000000000 WHERE id=?", (self.user,))
        submit_transfer_offer(player_id, self.user, 10**9, 1, "2026-03-01", self.database)
        outcomes = respond_to_user_bids("2026-03-02", self.user, self.database)
        self.assertEqual(outcomes[0]["result"], "terms")

    def test_good_bid_with_agreed_terms_signs_the_player(self) -> None:
        player_id, seller = self.target()
        with connect(self.database) as connection:
            connection.execute("UPDATE teams SET cash=10000000000 WHERE id=?", (self.user,))
        wage = personal_terms_agreed(player_id, 0, 3, self.database)["demand"]["wage"]
        submit_transfer_offer(player_id, self.user, 10**9, wage, "2026-03-01", self.database)
        outcomes = respond_to_user_bids("2026-03-02", self.user, self.database)
        self.assertEqual(outcomes[0]["result"], "signed")
        self.assertEqual(self.query("SELECT team_id FROM players WHERE id=?", player_id)[0][0], self.user)
        self.assertEqual(self.query("SELECT COUNT(*) FROM financial_log WHERE team_id=? AND category='Transfers'",
                                    seller)[0][0], 1)


class SponsorNegotiationTests(WorldTest):
    def test_three_competing_offers(self) -> None:
        offers = generate_sponsor_offers(self.user, 2026, 0.5, self.database)
        self.assertEqual(len(offers), 3)
        self.assertEqual(len({o["style"] for o in offers}), 3)

    def test_modest_ask_is_signed_and_runs_for_the_offer_length(self) -> None:
        offer = max(generate_sponsor_offers(self.user, 2026, 0.5, self.database), key=lambda o: o["years"])
        result = negotiate_sponsor_offer(self.user, offer["id"], offer["monthly_value"] + 1_000, self.database)
        self.assertEqual(result["outcome"], "accept")
        deal = current_sponsorship(self.user, self.database)
        self.assertEqual(deal["end_date"], f"{2026 + offer['years'] - 1}-09-30")
        self.assertEqual(fetch_sponsor_offers(self.user, self.database), [])

    def test_greedy_asks_eventually_make_the_sponsor_walk(self) -> None:
        offer = generate_sponsor_offers(self.user, 2026, 0.5, self.database)[0]
        outcome = None
        for _ in range(6):
            outcome = negotiate_sponsor_offer(self.user, offer["id"], offer["monthly_value"] * 3, self.database)
            if outcome["outcome"] == "withdrawn":
                break
        self.assertEqual(outcome["outcome"], "withdrawn")

    def test_board_signs_the_best_offer_on_decision_day(self) -> None:
        from competition import CompetitionEngine
        with connect(self.database) as connection:
            connection.execute("UPDATE sponsorships SET status='EXPIRED' WHERE team_id=?", (self.user,))
        engine = CompetitionEngine(self.database, seed=1)
        engine._manager_sponsorship(self.user, date(2026, 3, 2))
        self.assertEqual(len(fetch_sponsor_offers(self.user, self.database)), 3)
        engine._manager_sponsorship(self.user, date(2026, 3, 16))
        self.assertIsNotNone(current_sponsorship(self.user, self.database))

    def test_accepting_an_offer_declines_the_rest(self) -> None:
        offers = generate_sponsor_offers(self.user, 2026, 0.5, self.database)
        accept_sponsor_offer(self.user, offers[1]["id"], self.database)
        self.assertEqual(self.query("SELECT COUNT(*) FROM sponsor_offers WHERE status='DECLINED'")[0][0], 2)


class TrainingDevelopmentTests(WorldTest):
    def test_better_facilities_and_coaches_develop_players_faster(self) -> None:
        clubs = [row[0] for row in self.query("SELECT id FROM teams WHERE id>0 ORDER BY id LIMIT 2")]
        with connect(self.database) as connection:
            connection.execute("UPDATE teams SET training_level=5 WHERE id=?", (clubs[0],))
            connection.execute("UPDATE teams SET training_level=1 WHERE id=?", (clubs[1],))
            factors = club_development_factors(connection)
        self.assertGreater(factors[clubs[0]], factors[clubs[1]])


if __name__ == "__main__":
    unittest.main()
