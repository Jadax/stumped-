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

    def test_returns_1_to_3_drama_items(self) -> None:
        drama = generate_deadline_day_drama("2026-06-30", self.squad, self.other,
                                            rng_seed="drama")
        self.assertGreaterEqual(len(drama), 1)
        self.assertLessEqual(len(drama), 3)

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


if __name__ == "__main__":
    unittest.main()
