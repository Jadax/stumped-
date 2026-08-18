"""Tests for season awards persistence and season review narrative (v4.92.0)."""
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import (
    connect,
    fetch_all_season_awards,
    fetch_season_awards,
    initialise_database,
    record_honour,
    record_narrative_event,
    record_season_awards,
)
from src.models.career import season_awards
from src.models.season_review import generate_season_review


def _make_player(name, skill, form, consistency, age, role="Batsman", overall=50, potential=70, team_name="Test CC", nationality="ENG"):
    return {
        "name": name, "team_name": team_name, "nationality": nationality,
        "role": role, "age": age, "overall": overall, "potential": potential,
        "form": form, "batting_skill": skill, "bowling_skill": skill,
        "batting_consistency": consistency, "bowling_consistency": consistency,
        "keeping_skill": 0, "batting_aggression": 50, "bowling_aggression": 50,
        "fielding_skill": 50, "pace": 0, "spin": 0,
    }


class SeasonAwardsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_record_and_fetch_single_season(self):
        awards = {
            "Batter": {"name": "Smith", "team": "AUSSIES CC", "nationality": "AUS"},
            "Bowler": {"name": "Bumrah", "team": "INDIA CC", "nationality": "IND"},
            "Young Player": {"name": "Root", "team": "ENGLAND CC", "nationality": "ENG"},
            "Player": {"name": "Smith", "team": "AUSSIES CC", "nationality": "AUS"},
        }
        record_season_awards(2027, awards, "2027-09-30 10:00", self.db)
        result = fetch_season_awards(2027, self.db)
        self.assertEqual(len(result), 4)
        types = {r["award_type"] for r in result}
        self.assertEqual(types, {"Batter", "Bowler", "Young Player", "Player"})
        names = {r["award_type"]: r["player_name"] for r in result}
        self.assertEqual(names["Batter"], "Smith")
        self.assertEqual(names["Bowler"], "Bumrah")

    def test_upsert_replaces_existing(self):
        awards_v1 = {"Batter": {"name": "Smith", "team": "X", "nationality": "AUS"}}
        record_season_awards(2027, awards_v1, "2027-09-30 10:00", self.db)
        awards_v2 = {"Batter": {"name": "Warner", "team": "X", "nationality": "AUS"}}
        record_season_awards(2027, awards_v2, "2027-09-30 11:00", self.db)
        result = fetch_season_awards(2027, self.db)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["player_name"], "Warner")

    def test_fetch_empty_season(self):
        self.assertEqual(fetch_season_awards(9999, self.db), [])

    def test_fetch_all_seasons(self):
        for s in (2027, 2028, 2029):
            record_season_awards(s, {"Batter": {"name": f"B{s}", "team": "X", "nationality": "ENG"}}, f"{s}-09-30", self.db)
        all_awards = fetch_all_season_awards(10, self.db)
        seasons = {a["season"] for a in all_awards}
        self.assertEqual(seasons, {2027, 2028, 2029})

    def test_persist_called_from_awards(self):
        """Verify season_awards() produces output that record_season_awards can consume."""
        pool = [
            _make_player("Smith", 80, 7, 6, 28, overall=85),
            _make_player("Bumrah", 70, 8, 5, 26, role="Bowler", overall=85),
            _make_player("Root", 75, 6, 5, 20, overall=70, potential=90),
        ]
        awards = season_awards(pool)
        self.assertIn("Batter of the Season", awards)
        self.assertIn("Bowler of the Season", awards)
        self.assertIn("Player of the Season", awards)
        # Can persist without error — map to short keys for the DB schema
        db_awards = {}
        key_map = {"Batter of the Season": "Batter", "Bowler of the Season": "Bowler",
                    "Young Player of the Season": "Young Player", "Player of the Season": "Player"}
        for long_key, short_key in key_map.items():
            if long_key in awards:
                db_awards[short_key] = awards[long_key]
        record_season_awards(2027, db_awards, "2027-09-30 10:00", self.db)
        stored = fetch_season_awards(2027, self.db)
        self.assertGreaterEqual(len(stored), 3)


class SeasonReviewTests(unittest.TestCase):
    def test_review_delighted_winners(self):
        text = generate_season_review(
            "Title CC", 2027, 1, 12, "Delighted",
            wins=18, losses=2, draws=2,
            awards={"Batter": {"name": "Smith"}, "Player": {"name": "Smith"}},
            honours=["Division 1 Champions"],
        )
        self.assertIn("Title CC", text)
        self.assertIn("Division 1 Champions", text)
        self.assertIn("Smith", text)
        self.assertGreater(len(text), 80)

    def test_review_under_pressure_relegated(self):
        text = generate_season_review(
            "Struggling CC", 2027, 12, 12, "Ultimatum",
            wins=3, losses=15, draws=4,
        )
        self.assertIn("Struggling CC", text)
        self.assertIn("12th", text)

    def test_review_content_mid_table(self):
        text = generate_season_review(
            "Mid CC", 2027, 6, 12, "Content",
            wins=8, losses=8, draws=8,
        )
        self.assertIn("6th", text)
        self.assertGreater(len(text), 60)

    def test_review_no_awards(self):
        text = generate_season_review(
            "Plain CC", 2027, 4, 12, "Content",
            wins=10, losses=8, draws=4,
            awards=None, honours=None,
        )
        self.assertIn("Plain CC", text)
        self.assertGreater(len(text), 40)

    def test_review_narrative_event_recorded(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = f.name
        try:
            initialise_database(db)
            text = generate_season_review("Test", 2027, 1, 12, "Delighted", 18, 2, 2)
            eid = record_narrative_event("2027-09-30 10:00", "MILESTONE", "2027 Season Review",
                                         text, team_id=1, importance=3, database_path=db)
            self.assertIsNotNone(eid)
            self.assertGreater(eid, 0)
        finally:
            os.unlink(db)


class SeasonReviewTableSchemaTests(unittest.TestCase):
    def test_table_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db = f.name
        try:
            initialise_database(db)
            with connect(db) as conn:
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(season_awards_history)").fetchall()]
            self.assertIn("season", cols)
            self.assertIn("award_type", cols)
            self.assertIn("player_name", cols)
        finally:
            os.unlink(db)


if __name__ == "__main__":
    unittest.main()
