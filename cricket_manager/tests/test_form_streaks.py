"""v4.82.0: form streak detection and narrative persistence."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import (connect, fetch_narrative_events,
                      get_recent_performances, initialise_database,
                      write_streak_event)
from src.models.form_streaks import detect_streak, HOT_THRESHOLD, COLD_THRESHOLD, MIN_STREAK_LENGTH


class DetectStreakTests(unittest.TestCase):
    def test_hot_streak_detected_at_3_consecutive(self) -> None:
        scores = [80.0, 75.0, 72.0]
        result = detect_streak(scores)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "hot")
        self.assertEqual(result["length"], 3)

    def test_cold_streak_detected_at_3_consecutive(self) -> None:
        scores = [20.0, 10.0, 25.0]
        result = detect_streak(scores)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "cold")
        self.assertEqual(result["length"], 3)

    def test_streak_below_threshold_not_triggered(self) -> None:
        scores = [80.0, 50.0, 80.0]
        result = detect_streak(scores)
        self.assertIsNone(result)

    def test_hot_streak_stops_at_non_hot(self) -> None:
        scores = [80.0, 75.0, 50.0, 80.0]
        result = detect_streak(scores)
        self.assertIsNone(result)

    def test_cold_streak_stops_at_non_cold(self) -> None:
        scores = [20.0, 15.0, 60.0, 10.0]
        result = detect_streak(scores)
        self.assertIsNone(result)

    def test_longer_streak_detected(self) -> None:
        scores = [90.0, 85.0, 80.0, 78.0, 72.0]
        result = detect_streak(scores)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "hot")
        self.assertEqual(result["length"], 5)

    def test_t20_format_uses_lower_hot_threshold(self) -> None:
        # 68 is below FC hot threshold (70) but above T20 hot threshold (65)
        scores = [68.0, 70.0, 69.0]
        result_fc = detect_streak(scores, format="FC")
        result_t20 = detect_streak(scores, format="T20")
        self.assertIsNone(result_fc)
        self.assertIsNotNone(result_t20)
        self.assertEqual(result_t20["type"], "hot")

    def test_insufficient_data_returns_none(self) -> None:
        scores = [80.0, 75.0]
        result = detect_streak(scores)
        self.assertIsNone(result)

    def test_empty_scores_returns_none(self) -> None:
        self.assertIsNone(detect_streak([]))


class WriteStreakEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_hot_streak_creates_narrative_event(self) -> None:
        write_streak_event(1, "Test Player", 1, "hot", 4, "2026-08-15",
                           database_path=self.database)
        events = fetch_narrative_events(team_id=1, database_path=self.database)
        streak_events = [e for e in events if e["category"] == "FORM_STREAK"]
        self.assertEqual(len(streak_events), 1)
        self.assertIn("on fire", streak_events[0]["title"].lower())
        self.assertEqual(streak_events[0]["player_id"], 1)

    def test_cold_streak_creates_narrative_event(self) -> None:
        write_streak_event(2, "Cold Player", 1, "cold", 3, "2026-08-15",
                           database_path=self.database)
        events = fetch_narrative_events(team_id=1, database_path=self.database)
        streak_events = [e for e in events if e["category"] == "FORM_STREAK"]
        self.assertEqual(len(streak_events), 1)
        self.assertIn("slump", streak_events[0]["title"].lower())

    def test_dedup_prevents_reposting_same_streak(self) -> None:
        write_streak_event(1, "Test Player", 1, "hot", 4, "2026-08-15",
                           database_path=self.database)
        write_streak_event(1, "Test Player", 1, "hot", 5, "2026-08-20",
                           database_path=self.database)
        events = fetch_narrative_events(team_id=1, database_path=self.database)
        streak_events = [e for e in events if e["category"] == "FORM_STREAK"]
        self.assertEqual(len(streak_events), 1)

    def test_different_player_not_deduped(self) -> None:
        write_streak_event(1, "Player A", 1, "hot", 3, "2026-08-15",
                           database_path=self.database)
        write_streak_event(2, "Player B", 1, "hot", 3, "2026-08-15",
                           database_path=self.database)
        events = fetch_narrative_events(team_id=1, database_path=self.database)
        streak_events = [e for e in events if e["category"] == "FORM_STREAK"]
        self.assertEqual(len(streak_events), 2)


class GetRecentPerformancesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_returns_recent_scores_newest_first(self) -> None:
        # Insert 3 raw form_history entries for player 1
        with connect(self.database) as conn:
            for i, (perf, ctx) in enumerate([(80.0, "League"), (60.0, "League"), (90.0, "Cup")]):
                conn.execute(
                    "INSERT INTO player_form_history(player_id,match_date,performance,context) VALUES (?,?,?,?)",
                    (1, f"2026-08-{10 + i:02d}", perf, ctx))
        scores = get_recent_performances(1, limit=3, database_path=self.database)
        self.assertEqual(len(scores), 3)
        # Most recent first
        self.assertEqual(scores[0], 90.0)
        self.assertEqual(scores[1], 60.0)
        self.assertEqual(scores[2], 80.0)

    def test_returns_empty_for_unknown_player(self) -> None:
        scores = get_recent_performances(9999, database_path=self.database)
        self.assertEqual(scores, [])


if __name__ == "__main__":
    unittest.main()
