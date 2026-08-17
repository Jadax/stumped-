"""v4.88.0: career timeline — pure-function tests."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database import initialise_database, connect, record_career_timeline
from src.models.career_timeline import (
    group_timeline_by_season, format_season_summary, format_timeline_entry,
)


class GroupTimelineTests(unittest.TestCase):
    def test_empty_timeline(self) -> None:
        result = group_timeline_by_season([])
        self.assertEqual(result, {})

    def test_single_season(self) -> None:
        entries = [
            {"season": 2026, "category": "TROPHY", "title": "Won Cup", "created_on": "2026-06-01"},
            {"season": 2026, "category": "MILESTONE", "title": "Debut", "created_on": "2026-04-01"},
        ]
        result = group_timeline_by_season(entries)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[2026]), 2)

    def test_multiple_seasons(self) -> None:
        entries = [
            {"season": 2026, "category": "TROPHY", "title": "Won Cup", "created_on": "2026-06-01"},
            {"season": 2025, "category": "PROMOTION", "title": "Promoted", "created_on": "2025-08-01"},
        ]
        result = group_timeline_by_season(entries)
        self.assertEqual(len(result), 2)
        self.assertIn(2025, result)
        self.assertIn(2026, result)


class FormatSeasonSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _insert_team(self) -> int:
        name = f"Club_{uuid.uuid4().hex[:8]}"
        with connect(self.database) as conn:
            conn.execute(
                "INSERT INTO teams(name,division,cash,stadium_capacity) VALUES (?,?,?,?)",
                (name, 1, 1000000, 20000),
            )
            row = conn.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row["id"]

    def test_empty_returns_zeros(self) -> None:
        tid = self._insert_team()
        summary = format_season_summary(tid, 2026, self.database)
        self.assertEqual(summary["played"], 0)
        self.assertEqual(summary["wins"], 0)
        self.assertEqual(summary["trophies"], [])

    def test_includes_trophies(self) -> None:
        tid = self._insert_team()
        record_career_timeline(tid, 2026, "TROPHY", "Won Cup",
                               "Beat finalists", 3, "2026-06-01",
                               database_path=self.database)
        record_career_timeline(tid, 2026, "TROPHY", "League Champions",
                               "Won the league", 3, "2026-06-15",
                               database_path=self.database)
        summary = format_season_summary(tid, 2026, self.database)
        self.assertEqual(len(summary["trophies"]), 2)
        self.assertIn("Won Cup", summary["trophies"])


class FormatTimelineEntryTests(unittest.TestCase):
    def test_trophy_entry(self) -> None:
        entry = {"category": "TROPHY", "title": "Won Cup", "created_on": "2026-06-01"}
        result = format_timeline_entry(entry)
        self.assertIn("TROPHY", result)
        self.assertIn("Won Cup", result)

    def test_promotion_entry(self) -> None:
        entry = {"category": "PROMOTION", "title": "Promoted", "created_on": "2025-08-01"}
        result = format_timeline_entry(entry)
        self.assertIn("PROMOTED", result)

    def test_milestone_entry(self) -> None:
        entry = {"category": "MILESTONE", "title": "100th match", "created_on": "2026-05-10"}
        result = format_timeline_entry(entry)
        self.assertIn("MILESTONE", result)
        self.assertIn("100th match", result)


class CareerTimelinePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _insert_team(self) -> int:
        name = f"Club_{uuid.uuid4().hex[:8]}"
        with connect(self.database) as conn:
            conn.execute(
                "INSERT INTO teams(name,division,cash,stadium_capacity) VALUES (?,?,?,?)",
                (name, 1, 1000000, 20000),
            )
            row = conn.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row["id"]

    def test_record_and_fetch(self) -> None:
        tid = self._insert_team()
        row_id = record_career_timeline(
            tid, 2026, "TROPHY", "Won Cup", "Beat finalists",
            3, "2026-06-01", database_path=self.database)
        self.assertGreater(row_id, 0)
        with connect(self.database) as conn:
            row = conn.execute(
                "SELECT * FROM career_timeline WHERE id=?", (row_id,)
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Won Cup")

    def test_fetch_ordered_by_season_desc(self) -> None:
        tid = self._insert_team()
        record_career_timeline(tid, 2025, "PROMOTION", "Promoted", "...",
                               2, "2025-08-01", database_path=self.database)
        record_career_timeline(tid, 2026, "TROPHY", "Won Cup", "...",
                               3, "2026-06-01", database_path=self.database)
        from database import fetch_career_timeline
        result = fetch_career_timeline(tid, database_path=self.database)
        self.assertEqual(result[0]["season"], 2026)
        self.assertEqual(result[1]["season"], 2025)

    def test_empty_for_new_team(self) -> None:
        tid = self._insert_team()
        from database import fetch_career_timeline
        result = fetch_career_timeline(tid, database_path=self.database)
        self.assertEqual(result, [])

    def test_ensure_table_idempotent(self) -> None:
        """Calling initialise_database twice should not crash."""
        initialise_database(self.database)
        initialise_database(self.database)
        tid = self._insert_team()
        row_id = record_career_timeline(
            tid, 2026, "OTHER", "Test", "Body",
            1, "2026-01-01", database_path=self.database)
        self.assertGreater(row_id, 0)


if __name__ == "__main__":
    unittest.main()
