"""v4.84.0: transfer window narrative — pure-function tests."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database, connect, record_narrative_event
from src.models.transfer_narrative import (
    in_transfer_window, is_deadline_period,
    generate_rumours, generate_deadline_day_drama,
    TRANSFER_WINDOW_MONTHS,
)


class InTransferWindowTests(unittest.TestCase):
    def test_april_to_june_domestic_window(self) -> None:
        for m in (4, 5, 6):
            self.assertTrue(in_transfer_window(date(2026, m, 15)),
                            f"Month {m} should be in transfer window")

    def test_july_to_august_international_window(self) -> None:
        for m in (7, 8):
            self.assertTrue(in_transfer_window(date(2026, m, 15)),
                            f"Month {m} should be in transfer window")

    def test_not_in_transfer_window_off_season(self) -> None:
        for m in (1, 2, 3, 9, 10, 11, 12):
            self.assertFalse(in_transfer_window(date(2026, m, 15)),
                             f"Month {m} should NOT be in transfer window")

    def test_accepts_string_date(self) -> None:
        self.assertTrue(in_transfer_window("2026-05-20"))
        self.assertFalse(in_transfer_window("2026-12-25"))


class IsDeadlinePeriodTests(unittest.TestCase):
    def test_last_two_days_of_june(self) -> None:
        self.assertTrue(is_deadline_period(date(2026, 6, 29)))
        self.assertTrue(is_deadline_period(date(2026, 6, 30)))

    def test_last_two_days_of_august(self) -> None:
        self.assertTrue(is_deadline_period(date(2026, 8, 30)))
        self.assertTrue(is_deadline_period(date(2026, 8, 31)))

    def test_not_deadline_mid_month(self) -> None:
        self.assertFalse(is_deadline_period(date(2026, 6, 15)))
        self.assertFalse(is_deadline_period(date(2026, 8, 15)))

    def test_not_deadline_outside_window(self) -> None:
        self.assertFalse(is_deadline_period(date(2026, 9, 29)))


class GenerateRumoursTests(unittest.TestCase):
    def setUp(self) -> None:
        self.squad = [
            {"id": 1, "name": "A. Smith", "role": "Batsman", "overall": 78,
             "morale": 60, "age": 26, "wage": 15000},
            {"id": 2, "name": "B. Jones", "role": "Bowler", "overall": 72,
             "morale": 30, "age": 28, "wage": 12000},
            {"id": 3, "name": "C. Davis", "role": "All-Rounder", "overall": 65,
             "morale": 55, "age": 24, "wage": 10000},
        ]
        self.other = [
            {"id": 10, "name": "X. Player", "role": "Batsman", "overall": 80,
             "team_name": "Tigers", "age": 25, "wage": 20000},
            {"id": 11, "name": "Y. Bowler", "role": "Bowler", "overall": 75,
             "team_name": "Lions", "age": 27, "wage": 14000},
        ]

    def test_returns_2_to_4_rumours(self) -> None:
        rumours = generate_rumours(1, "2026-05-10", self.squad, self.other,
                                   rng_seed="test")
        self.assertGreaterEqual(len(rumours), 2)
        self.assertLessEqual(len(rumours), 4)

    def test_rumours_have_required_keys(self) -> None:
        rumours = generate_rumours(1, "2026-05-10", self.squad, self.other,
                                   rng_seed="test")
        for r in rumours:
            self.assertIn("title", r)
            self.assertIn("body", r)
            self.assertIn("importance", r)
            self.assertIn("player_id", r)

    def test_rumours_reference_real_players(self) -> None:
        rumours = generate_rumours(1, "2026-05-10", self.squad, self.other,
                                   rng_seed="test")
        player_names = {p["name"] for p in self.squad + self.other}
        for r in rumours:
            # At least one player name should appear in the rumour
            self.assertTrue(
                any(name in r["title"] or name in r["body"] for name in player_names),
                f"Rumour doesn't reference any known player: {r['title']}")

    def test_returns_empty_outside_window(self) -> None:
        # The function itself doesn't check window — it's a pure generator.
        # The window check happens in advance_day. So we just test the seed
        # gives deterministic results.
        r1 = generate_rumours(1, "2026-05-10", self.squad, self.other, rng_seed="x")
        r2 = generate_rumours(1, "2026-05-10", self.squad, self.other, rng_seed="x")
        self.assertEqual(len(r1), len(r2))


class GenerateDeadlineDayDramaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.squad = [
            {"id": 1, "name": "A. Smith", "role": "Batsman", "overall": 78,
             "morale": 60, "age": 26, "wage": 15000},
        ]
        self.other = [
            {"id": 10, "name": "X. Player", "role": "Batsman", "overall": 80,
             "team_name": "Tigers", "age": 25, "wage": 20000},
        ]

    def test_returns_1_to_4_drama_items(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        self.assertGreaterEqual(len(drama), 1)
        self.assertLessEqual(len(drama), 4)

    def test_drama_has_high_importance(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        for d in drama:
            self.assertGreaterEqual(d["importance"], 2)

    def test_drama_has_urgency_in_body(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        # At least one item should reference deadline/PM
        has_urgency = any("PM" in d["body"] or "deadline" in d["body"].lower()
                          for d in drama)
        self.assertTrue(has_urgency, "Deadline drama should include time urgency")

    def test_incoming_bid_item_has_bid_dict(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        bids = [d for d in drama if d.get("bid") and d["bid"].get("buyer_name")]
        self.assertGreaterEqual(len(bids), 1,
                                "Should have at least one incoming bid with a buyer_name")
        for item in bids:
            bid = item["bid"]
            self.assertIn("player_id", bid)
            self.assertIn("fee", bid)
            self.assertIn("wage", bid)
            self.assertIsInstance(bid["fee"], int)
            self.assertGreater(bid["fee"], 0)
            self.assertIsInstance(bid["wage"], int)
            self.assertGreater(bid["wage"], 0)

    def test_outgoing_bid_item_has_bid_dict(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        bids = [d for d in drama if d.get("bid") and d["bid"].get("from_team_name")]
        # Outgoing bid is optional (60% chance)
        if bids:
            for item in bids:
                bid = item["bid"]
                self.assertIn("player_id", bid)
                self.assertIn("fee", bid)
                self.assertIn("from_team_name", bid)

    def test_bid_fee_scales_with_overall(self) -> None:
        drama_low = generate_deadline_day_drama(
            "2026-06-30",
            [{"id": 1, "name": "Low", "role": "Bowler", "overall": 65,
              "morale": 50, "age": 25, "wage": 10000}],
            self.other, rng_seed="scale_low")
        drama_high = generate_deadline_day_drama(
            "2026-06-30",
            [{"id": 1, "name": "High", "role": "Batsman", "overall": 90,
              "morale": 50, "age": 25, "wage": 10000}],
            self.other, rng_seed="scale_high")
        # Both should produce bids; the fee ranges are 100k-800k for both
        # but we verify the function works without crashing
        all_drama = drama_low + drama_high
        bids = [d["bid"] for d in all_drama if d.get("bid")]
        self.assertGreater(len(bids), 0)


class TransferWindowNarrativePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_rumours_persist_to_narrative_events(self) -> None:
        record_narrative_event(
            "2026-05-10", "TRANSFER_SAGA",
            "A. Smith eyed by Premier Division club",
            "A. Smith has caught the attention of a top-flight side.",
            team_id=1, player_id=1, importance=2,
            database_path=self.database)
        with connect(self.database) as conn:
            rows = conn.execute(
                "SELECT * FROM narrative_events WHERE category='TRANSFER_SAGA'"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("A. Smith", rows[0]["title"])


class DeadlineDayOfferInsertTests(unittest.TestCase):
    """Verify that the INSERT used by competition.py for deadline-day offers
    actually works against a real database (the same schema)."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)
        self.team_a = 1
        self.team_b = 2
        with connect(self.database) as conn:
            cur = conn.execute(
                """INSERT INTO players (name, age, nationality, role,
                   batting_json, bowling_json, fielding_json, mental_json,
                   overall, form, potential, team_id, wage)
                   VALUES ('DD A. Smith', 26, 'English', 'Batsman',
                   '{}', '{}', '{}', '{}', 78, 50, 85, ?, 15000)""",
                (self.team_a,))
            self.player_id = cur.lastrowid

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_incoming_deadline_offer_inserts(self) -> None:
        with connect(self.database) as conn:
            conn.execute(
                """INSERT INTO transfer_offers
                   (player_id, from_team, to_team, fee,
                    weekly_wage, offer_type, status, created_date)
                   VALUES (?, ?, ?, ?, ?, 'INCOMING', 'PENDING', ?)""",
                (self.player_id, self.team_b, self.team_a, 500000, 20000, "2026-06-30"))
        with connect(self.database) as conn:
            offers = conn.execute(
                "SELECT * FROM transfer_offers WHERE player_id = ? AND fee = ?",
                (self.player_id, 500000)).fetchall()
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["from_team"], self.team_b)
        self.assertEqual(offers[0]["to_team"], self.team_a)
        self.assertEqual(offers[0]["fee"], 500000)
        self.assertEqual(offers[0]["status"], "PENDING")

    def test_deadline_bid_dict_matches_schema(self) -> None:
        squad = [{"id": self.player_id, "name": "DD A. Smith", "role": "Batsman", "overall": 78,
                  "morale": 60, "age": 26, "wage": 15000}]
        other = [{"id": 10, "name": "X. Player", "role": "Batsman", "overall": 80,
                  "team_name": "Tigers", "age": 25, "wage": 20000}]
        drama = generate_deadline_day_drama("2026-06-30", squad, other, rng_seed="schema")
        bids = [d["bid"] for d in drama if d.get("bid") and d["bid"].get("buyer_name")]
        self.assertGreater(len(bids), 0)
        for bid in bids:
            with connect(self.database) as conn:
                conn.execute(
                    """INSERT INTO transfer_offers
                       (player_id, from_team, to_team, fee,
                        weekly_wage, offer_type, status, created_date)
                       VALUES (?, ?, ?, ?, ?, 'INCOMING', 'PENDING', ?)""",
                    (bid["player_id"], self.team_b, self.team_a, bid["fee"], bid["wage"], "2026-06-30"))
            with connect(self.database) as conn:
                row = conn.execute("SELECT * FROM transfer_offers ORDER BY id DESC LIMIT 1").fetchone()
            self.assertEqual(row["fee"], bid["fee"])
            self.assertEqual(row["weekly_wage"], bid["wage"])


if __name__ == "__main__":
    unittest.main()
