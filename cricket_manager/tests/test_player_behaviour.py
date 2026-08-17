"""v4.85.0: player behaviour — transfer requests, complaints, retirements."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database, connect, record_narrative_event
from src.models.player_behaviour import (
    check_transfer_requests, check_playing_time_complaints,
    check_retirements, format_behaviour_event, process_player_behaviour,
)


class CheckTransferRequestsTests(unittest.TestCase):
    def test_low_morale_streak_triggers_request(self) -> None:
        squad = [{"id": 1, "name": "A. Smith", "overall": 72, "morale": 25,
                  "personality": "Professional", "matches_out_xi": 0,
                  "low_morale_streak": 4}]
        reqs = check_transfer_requests(squad, "2026-08-15")
        self.assertEqual(len(reqs), 1)
        self.assertIn("unhappy", reqs[0]["reason"])

    def test_high_value_benched_player_triggers_request(self) -> None:
        squad = [{"id": 2, "name": "B. Jones", "overall": 75, "morale": 50,
                  "personality": "Professional", "matches_out_xi": 6,
                  "low_morale_streak": 0}]
        reqs = check_transfer_requests(squad, "2026-08-15")
        self.assertEqual(len(reqs), 1)
        self.assertIn("hasn't featured", reqs[0]["reason"])

    def test_no_request_for_loyalist(self) -> None:
        # Loyalist with low morale but no streak
        squad = [{"id": 3, "name": "C. Davis", "overall": 70, "morale": 40,
                  "personality": "Loyalist", "matches_out_xi": 0,
                  "low_morale_streak": 0}]
        reqs = check_transfer_requests(squad, "2026-08-15")
        self.assertEqual(len(reqs), 0)

    def test_mercenary_in_bottom_half_requests(self) -> None:
        squad = [{"id": 4, "name": "D. Wilson", "overall": 68, "morale": 40,
                  "personality": "Mercenary", "matches_out_xi": 0,
                  "low_morale_streak": 0}]
        reqs = check_transfer_requests(squad, "2026-08-15", season_position=10)
        self.assertEqual(len(reqs), 1)
        self.assertIn("league position", reqs[0]["reason"])

    def test_no_request_for_happy_player(self) -> None:
        squad = [{"id": 5, "name": "E. Brown", "overall": 78, "morale": 70,
                  "personality": "Professional", "matches_out_xi": 0,
                  "low_morale_streak": 0}]
        reqs = check_transfer_requests(squad, "2026-08-15")
        self.assertEqual(len(reqs), 0)


class CheckPlayingTimeComplaintsTests(unittest.TestCase):
    def test_high_value_benched_player_complains(self) -> None:
        squad = [{"id": 1, "name": "A. Smith", "overall": 72,
                  "personality": "Maverick", "matches_out_xi": 5}]
        complaints = check_playing_time_complaints(squad)
        self.assertEqual(len(complaints), 1)

    def test_loyalist_never_complains(self) -> None:
        squad = [{"id": 2, "name": "B. Jones", "overall": 80,
                  "personality": "Loyalist", "matches_out_xi": 10}]
        complaints = check_playing_time_complaints(squad)
        self.assertEqual(len(complaints), 0)

    def test_hot_head_complains_early(self) -> None:
        squad = [{"id": 3, "name": "C. Davis", "overall": 68,
                  "personality": "Hot Head", "matches_out_xi": 3}]
        complaints = check_playing_time_complaints(squad)
        self.assertEqual(len(complaints), 1)

    def test_low_value_player_no_complaint(self) -> None:
        squad = [{"id": 4, "name": "D. Wilson", "overall": 50,
                  "personality": "Professional", "matches_out_xi": 8}]
        complaints = check_playing_time_complaints(squad)
        self.assertEqual(len(complaints), 0)


class CheckRetirementsTests(unittest.TestCase):
    def test_old_declining_player_retires(self) -> None:
        squad = [{"id": 1, "name": "A. Smith", "age": 39, "overall": 42,
                  "role": "Batsman"}]
        rets = check_retirements(squad, "2026-08-15")
        self.assertEqual(len(rets), 1)
        self.assertIn("retirement", rets[0]["reason"].lower())

    def test_young_player_no_retirement(self) -> None:
        squad = [{"id": 2, "name": "B. Jones", "age": 28, "overall": 75,
                  "role": "Bowler"}]
        rets = check_retirements(squad, "2026-08-15")
        self.assertEqual(len(rets), 0)

    def test_old_but_good_player_no_retirement(self) -> None:
        squad = [{"id": 3, "name": "C. Davis", "age": 38, "overall": 55,
                  "role": "All-Rounder"}]
        rets = check_retirements(squad, "2026-08-15")
        self.assertEqual(len(rets), 0)


class FormatBehaviourEventTests(unittest.TestCase):
    def test_transfer_request_format(self) -> None:
        event = {"name": "A. Smith", "reason": "Wants out.", "urgency": 2}
        result = format_behaviour_event("transfer_request", event)
        self.assertEqual(result["priority"], "HIGH")
        self.assertIn("Transfer request", result["title"])

    def test_complaint_format(self) -> None:
        event = {"name": "B. Jones", "reason": "Left out.", "urgency": 1}
        result = format_behaviour_event("playing_time_complaint", event)
        self.assertEqual(result["priority"], "MEDIUM")
        self.assertIn("Playing-time", result["title"])

    def test_retirement_format(self) -> None:
        event = {"name": "C. Davis", "reason": "Age 39.", "urgency": 3}
        result = format_behaviour_event("retirement", event)
        self.assertEqual(result["priority"], "HIGH")
        self.assertIn("Retirement", result["title"])


class ProcessPlayerBehaviourTests(unittest.TestCase):
    def test_returns_formatted_events(self) -> None:
        squad = [
            {"id": 1, "name": "A. Smith", "overall": 72, "morale": 25,
             "personality": "Professional", "matches_out_xi": 0,
             "low_morale_streak": 4, "age": 26, "role": "Batsman"},
            {"id": 2, "name": "B. Jones", "age": 39, "overall": 42,
             "role": "Bowler", "personality": "Professional",
             "matches_out_xi": 0, "low_morale_streak": 0, "morale": 50},
        ]
        events = process_player_behaviour(squad, "2026-08-15")
        # Should get transfer request + retirement
        self.assertGreaterEqual(len(events), 2)
        categories = {e["category"] for e in events}
        self.assertIn("TRANSFER_SAGA", categories)
        self.assertIn("MILESTONE", categories)

    def test_events_have_player_id(self) -> None:
        squad = [{"id": 1, "name": "A. Smith", "overall": 72, "morale": 25,
                  "personality": "Professional", "matches_out_xi": 0,
                  "low_morale_streak": 4, "age": 26, "role": "Batsman"}]
        events = process_player_behaviour(squad, "2026-08-15")
        for e in events:
            self.assertIn("player_id", e)
            self.assertIsNotNone(e["player_id"])


class BehaviourPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_behaviour_events_write_to_narrative_events(self) -> None:
        record_narrative_event(
            "2026-08-15", "TRANSFER_SAGA",
            "Transfer request: A. Smith",
            "A. Smith has been unhappy and wants out.",
            team_id=1, player_id=1, importance=2,
            database_path=self.database)
        with connect(self.database) as conn:
            rows = conn.execute(
                "SELECT * FROM narrative_events WHERE category='TRANSFER_SAGA'"
            ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_behaviour_events_create_inbox_messages(self) -> None:
        from database import create_inbox_message
        create_inbox_message(
            "HIGH", "Transfer request: A. Smith",
            "A. Smith wants out.",
            database_path=self.database)
        with connect(self.database) as conn:
            rows = conn.execute(
                "SELECT * FROM inbox_messages WHERE title=?",
                ("Transfer request: A. Smith",)
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["priority"], "HIGH")


if __name__ == "__main__":
    unittest.main()
