"""v4.86.0: rich milestone stories — pure-function tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database, connect, record_narrative_event
from src.models.milestones import (
    detect_debut, detect_cap_milestone,
    detect_career_best_batting, detect_career_best_bowling,
    format_milestone_body,
    CAP_MILESTONES,
)


class DetectDebutTests(unittest.TestCase):
    def test_debut_on_first_match(self) -> None:
        self.assertTrue(detect_debut(1))

    def test_no_debut_after_first_match(self) -> None:
        self.assertFalse(detect_debut(2))
        self.assertFalse(detect_debut(10))


class DetectCapMilestoneTests(unittest.TestCase):
    def test_cap_milestone_at_50(self) -> None:
        self.assertEqual(detect_cap_milestone(50), 50)

    def test_cap_milestone_at_100(self) -> None:
        self.assertEqual(detect_cap_milestone(100), 100)

    def test_no_milestone_at_49(self) -> None:
        self.assertIsNone(detect_cap_milestone(49))

    def test_no_milestone_at_101(self) -> None:
        self.assertIsNone(detect_cap_milestone(101))

    def test_all_thresholds_work(self) -> None:
        for threshold in CAP_MILESTONES:
            self.assertEqual(detect_cap_milestone(threshold), threshold)


class DetectCareerBestBattingTests(unittest.TestCase):
    def test_new_best_detected(self) -> None:
        result = detect_career_best_batting(120, 95)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "batting")
        self.assertEqual(result["value"], 120)
        self.assertEqual(result["previous_best"], 95)

    def test_no_best_when_equal(self) -> None:
        self.assertIsNone(detect_career_best_batting(95, 95))

    def test_no_best_when_worse(self) -> None:
        self.assertIsNone(detect_career_best_batting(80, 95))


class DetectCareerBestBowlingTests(unittest.TestCase):
    def test_more_wickets_is_best(self) -> None:
        result = detect_career_best_bowling(7, 45, 5, 30)
        self.assertIsNotNone(result)
        self.assertEqual(result["value"], "7/45")

    def test_same_wickets_fewer_runs_is_best(self) -> None:
        result = detect_career_best_bowling(5, 20, 5, 30)
        self.assertIsNotNone(result)
        self.assertEqual(result["value"], "5/20")

    def test_same_wickets_more_runs_not_best(self) -> None:
        self.assertIsNone(detect_career_best_bowling(5, 40, 5, 30))

    def test_fewer_wickets_not_best(self) -> None:
        self.assertIsNone(detect_career_best_bowling(3, 20, 5, 30))

    def test_zero_wickets_not_best(self) -> None:
        self.assertIsNone(detect_career_best_bowling(0, 50, 0, 999))


class FormatMilestoneBodyTests(unittest.TestCase):
    def test_debut_text(self) -> None:
        body = format_milestone_body("A. Smith", "Lions", "debut", {})
        self.assertIn("A. Smith", body)
        self.assertIn("debut", body.lower())
        self.assertIn("Lions", body)

    def test_cap_milestone_text(self) -> None:
        body = format_milestone_body("B. Jones", "Tigers", "cap_milestone", 100)
        self.assertIn("100th cap", body)
        self.assertIn("B. Jones", body)

    def test_career_best_batting_text(self) -> None:
        body = format_milestone_body("C. Davis", "Eagles", "career_best_batting",
                                     {"value": 145, "previous_best": 112})
        self.assertIn("145", body)
        self.assertIn("112", body)

    def test_career_best_bowling_text(self) -> None:
        body = format_milestone_body("D. Wilson", "Hawks", "career_best_bowling",
                                     {"value": "7/32", "previous_best": "5/28"})
        self.assertIn("7/32", body)
        self.assertIn("5/28", body)

    def test_century_text(self) -> None:
        body = format_milestone_body("E. Brown", "Wolves", "century", 118)
        self.assertIn("century", body.lower())
        self.assertIn("118", body)

    def test_five_wickets_text(self) -> None:
        body = format_milestone_body("F. Green", "Bears", "five_wickets",
                                     {"wickets": 6, "runs": 25})
        self.assertIn("five-wicket", body.lower())
        self.assertIn("6", body)


class MilestonePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_milestone_writes_to_narrative_events(self) -> None:
        record_narrative_event(
            "2026-08-15", "MILESTONE",
            "A. Smith makes his debut",
            "A. Smith makes his debut for Lions.",
            team_id=1, player_id=1, importance=2,
            database_path=self.database)
        with connect(self.database) as conn:
            rows = conn.execute(
                "SELECT * FROM narrative_events WHERE category='MILESTONE'"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("debut", rows[0]["title"].lower())


if __name__ == "__main__":
    unittest.main()
