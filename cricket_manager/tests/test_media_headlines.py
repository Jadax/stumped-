"""Tests for media headlines system (v4.96.0)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import initialise_database, record_narrative_event
from src.models.media_headlines import (
    fan_sentiment_headlines,
    match_headlines,
    milestone_headlines,
    streak_headlines,
)


class MatchHeadlinesTests(unittest.TestCase):
    def test_no_winner_returns_empty(self):
        self.assertEqual(match_headlines("A", "B", 100, 100, None, 1, 2), [])

    def test_big_win_returns_headline(self):
        h = match_headlines("A", "B", 200, 100, 1, 1, 2, margin_comfortable=True)
        self.assertEqual(len(h), 1)
        self.assertIn("A", h[0]["title"])

    def test_derby_returns_importance_3(self):
        h = match_headlines("A", "B", 120, 90, 1, 1, 2, is_derby=True)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["importance"], 3)

    def test_title_decider_returns_importance_3(self):
        h = match_headlines("A", "B", 150, 100, 1, 1, 2, title_decider=True)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["importance"], 3)
        self.assertTrue(len(h[0]["title"]) > 0)

    def test_promotion_decider(self):
        h = match_headlines("A", "B", 150, 100, 1, 1, 2, promotion_decider=True)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["importance"], 3)
        self.assertTrue(len(h[0]["title"]) > 0)

    def test_relegation_decider(self):
        h = match_headlines("A", "B", 150, 100, 1, 1, 2, relegation_decider=True)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["importance"], 3)
        self.assertTrue(len(h[0]["title"]) > 0)

    def test_normal_win_no_margin_no_derby_returns_empty(self):
        h = match_headlines("A", "B", 120, 100, 1, 1, 2)
        self.assertEqual(len(h), 0)

    def test_away_winner(self):
        h = match_headlines("A", "B", 100, 200, 2, 1, 2, margin_comfortable=True)
        self.assertEqual(len(h), 1)
        self.assertIn("B", h[0]["title"])


class MilestoneHeadlinesTests(unittest.TestCase):
    def test_century(self):
        h = milestone_headlines("Player", "Team", "century")
        self.assertEqual(len(h), 1)
        self.assertIn("Player", h[0]["title"])

    def test_debut_century(self):
        h = milestone_headlines("Player", "Team", "century", is_debut=True)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["importance"], 3)
        self.assertIn("Player", h[0]["title"])

    def test_five_wickets(self):
        h = milestone_headlines("Player", "Team", "five_wickets")
        self.assertEqual(len(h), 1)
        self.assertIn("five", h[0]["title"].lower())

    def test_career_best_batting(self):
        h = milestone_headlines("Player", "Team", "career_best_batting")
        self.assertEqual(len(h), 1)
        self.assertIn("best", h[0]["title"].lower())

    def test_career_best_bowling(self):
        h = milestone_headlines("Player", "Team", "career_best_bowling")
        self.assertEqual(len(h), 1)
        self.assertIn("best", h[0]["title"].lower())

    def test_unknown_type_returns_empty(self):
        h = milestone_headlines("Player", "Team", "unknown")
        self.assertEqual(len(h), 0)


class StreakHeadlinesTests(unittest.TestCase):
    def test_win_streak_3(self):
        h = streak_headlines("Team", "win", 3)
        self.assertEqual(len(h), 1)
        self.assertIn("Team", h[0]["title"])

    def test_win_streak_below_threshold(self):
        h = streak_headlines("Team", "win", 2)
        self.assertEqual(len(h), 0)

    def test_loss_streak_3(self):
        h = streak_headlines("Team", "loss", 3)
        self.assertEqual(len(h), 1)
        self.assertIn("Team", h[0]["title"])

    def test_loss_streak_below_threshold(self):
        h = streak_headlines("Team", "loss", 2)
        self.assertEqual(len(h), 0)


class FanSentimentHeadlinesTests(unittest.TestCase):
    def test_angry_fans(self):
        h = fan_sentiment_headlines("Team", 10)
        self.assertEqual(len(h), 1)
        self.assertIn("Team", h[0]["title"])

    def test_happy_fans(self):
        h = fan_sentiment_headlines("Team", 90)
        self.assertEqual(len(h), 1)
        self.assertIn("Team", h[0]["title"])

    def test_neutral_fans(self):
        h = fan_sentiment_headlines("Team", 50)
        self.assertEqual(len(h), 0)


class NarrativeRecordTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_record_headline_as_record_category(self):
        eid = record_narrative_event("2026-08-17", "RECORD",
                                     "Big win headline",
                                     "Big win body",
                                     team_id=1, importance=3,
                                     database_path=self.db)
        self.assertGreater(eid, 0)

    def test_fetch_only_record_category(self):
        record_narrative_event("2026-08-17", "RECORD", "Headline 1", "Body 1",
                               importance=3, database_path=self.db)
        record_narrative_event("2026-08-17", "MILESTONE", "Milestone 1", "Body 2",
                               importance=2, database_path=self.db)
        from database import fetch_narrative_events
        all_events = fetch_narrative_events(None, 10, self.db)
        self.assertEqual(len(all_events), 2)
        record_events = [e for e in all_events if e["category"] == "RECORD"]
        self.assertEqual(len(record_events), 1)
        self.assertEqual(record_events[0]["title"], "Headline 1")


if __name__ == "__main__":
    unittest.main()
