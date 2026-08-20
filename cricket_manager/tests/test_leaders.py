"""Tests for league statistics leaders (v4.94.0)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import (
    fetch_all_season_leaders,
    fetch_season_leaders,
    initialise_database,
    record_season_leaders,
)
from src.models.leaders import (
    batting_leaders,
    bowling_leaders,
    best_economy_bowlers,
    most_runs_leaders,
    most_wickets_leaders,
    top_strike_rate_batters,
    _overs_to_balls,
)


def _player(**overrides):
    defaults = {
        "name": "Test Player", "team_name": "Test CC", "nationality": "ENG",
        "career_matches": 0, "career_innings": 0, "career_not_outs": 0,
        "career_runs": 0, "career_balls": 0, "career_batting_average": 0.0,
        "career_strike_rate": 0.0, "career_hundreds": 0, "career_fifties": 0,
        "career_highest_score": 0, "career_wickets": 0,
        "career_bowling_average": 0.0, "career_economy": 0.0,
        "career_overs": "0.0", "career_five_wickets": 0,
    }
    defaults.update(overrides)
    return defaults


class BattingLeadersTests(unittest.TestCase):
    def test_top_by_average(self):
        players = [
            _player(name="A", career_innings=20, career_runs=1000, career_batting_average=50.0),
            _player(name="B", career_innings=20, career_runs=900, career_batting_average=45.0),
            _player(name="C", career_innings=20, career_runs=1100, career_batting_average=55.0),
        ]
        leaders = batting_leaders(players, min_innings=5, limit=10)
        self.assertEqual(len(leaders), 3)
        self.assertEqual(leaders[0]["name"], "C")
        self.assertEqual(leaders[1]["name"], "A")
        self.assertEqual(leaders[2]["name"], "B")

    def test_filters_by_min_innings(self):
        players = [
            _player(name="Qualified", career_innings=20, career_runs=500, career_batting_average=25.0),
            _player(name="Unqualified", career_innings=3, career_runs=100, career_batting_average=33.0),
        ]
        leaders = batting_leaders(players, min_innings=5)
        self.assertEqual(len(leaders), 1)
        self.assertEqual(leaders[0]["name"], "Qualified")

    def test_respects_limit(self):
        players = [_player(name=f"P{i}", career_innings=20, career_runs=500 + i * 100,
                           career_batting_average=25.0 + i) for i in range(20)]
        leaders = batting_leaders(players, min_innings=5, limit=5)
        self.assertEqual(len(leaders), 5)

    def test_empty_input(self):
        self.assertEqual(batting_leaders([]), [])


class BowlingLeadersTests(unittest.TestCase):
    def test_top_by_average(self):
        players = [
            _player(name="A", career_wickets=30, career_bowling_average=25.0),
            _player(name="B", career_wickets=20, career_bowling_average=20.0),
            _player(name="C", career_wickets=40, career_bowling_average=30.0),
        ]
        leaders = bowling_leaders(players, min_wickets=10)
        self.assertEqual(len(leaders), 3)
        # Sorted by wickets desc first, then average asc
        self.assertEqual(leaders[0]["name"], "C")
        self.assertEqual(leaders[1]["name"], "A")
        self.assertEqual(leaders[2]["name"], "B")

    def test_filters_by_min_wickets(self):
        players = [
            _player(name="Qualified", career_wickets=15, career_bowling_average=25.0),
            _player(name="Unqualified", career_wickets=3, career_bowling_average=15.0),
        ]
        leaders = bowling_leaders(players, min_wickets=10)
        self.assertEqual(len(leaders), 1)

    def test_empty_input(self):
        self.assertEqual(bowling_leaders([]), [])


class MostRunsLeadersTests(unittest.TestCase):
    def test_top_by_runs(self):
        players = [
            _player(name="A", career_innings=20, career_runs=800),
            _player(name="B", career_innings=20, career_runs=1200),
            _player(name="C", career_innings=20, career_runs=1000),
        ]
        leaders = most_runs_leaders(players, min_innings=3)
        self.assertEqual(leaders[0]["name"], "B")
        self.assertEqual(leaders[1]["name"], "C")
        self.assertEqual(leaders[2]["name"], "A")


class MostWicketsLeadersTests(unittest.TestCase):
    def test_top_by_wickets(self):
        players = [
            _player(name="A", career_wickets=20),
            _player(name="B", career_wickets=40),
            _player(name="C", career_wickets=30),
        ]
        leaders = most_wickets_leaders(players, min_wickets=3)
        self.assertEqual(leaders[0]["name"], "B")
        self.assertEqual(leaders[1]["name"], "C")
        self.assertEqual(leaders[2]["name"], "A")


class TopStrikeRateTests(unittest.TestCase):
    def test_top_by_sr(self):
        players = [
            _player(name="A", career_runs=300, career_strike_rate=120.0),
            _player(name="B", career_runs=500, career_strike_rate=150.0),
        ]
        leaders = top_strike_rate_batters(players, min_runs=200)
        self.assertEqual(leaders[0]["name"], "B")
        self.assertEqual(leaders[1]["name"], "A")

    def test_filters_by_min_runs(self):
        players = [
            _player(name="Qualified", career_runs=300, career_strike_rate=120.0),
            _player(name="Unqualified", career_runs=100, career_strike_rate=200.0),
        ]
        leaders = top_strike_rate_batters(players, min_runs=200)
        self.assertEqual(len(leaders), 1)


class BestEconomyTests(unittest.TestCase):
    def test_top_by_economy(self):
        players = [
            _player(name="A", career_wickets=20, career_economy=5.5, career_overs="100.0"),
            _player(name="B", career_wickets=30, career_economy=4.2, career_overs="150.0"),
        ]
        leaders = best_economy_bowlers(players, min_overs="50.0")
        self.assertEqual(leaders[0]["name"], "B")
        self.assertEqual(leaders[1]["name"], "A")


class OversToBallsTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(_overs_to_balls("10.0"), 60)

    def test_with_balls(self):
        self.assertEqual(_overs_to_balls("10.3"), 63)

    def test_zero(self):
        self.assertEqual(_overs_to_balls("0.0"), 0)

    def test_invalid(self):
        self.assertEqual(_overs_to_balls("abc"), 0)

    def test_none(self):
        self.assertEqual(_overs_to_balls(None), 0)


class SeasonLeadersPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = self._tmp.name
        self._tmp.close()
        initialise_database(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_record_and_fetch(self):
        leaders = {
            "Batting Average": [{"name": "Smith", "team_name": "X", "nationality": "AUS", "stat_value": 55.3}],
            "Most Runs": [{"name": "Root", "team_name": "Y", "nationality": "ENG", "stat_value": 1200.0}],
        }
        record_season_leaders(2027, leaders, "2027-09-30 10:00", self.db)
        result = fetch_season_leaders(2027, self.db)
        self.assertEqual(len(result), 2)
        cats = {r["category"] for r in result}
        self.assertEqual(cats, {"Batting Average", "Most Runs"})

    def test_upsert_replaces(self):
        leaders_v1 = {"Batting Average": [{"name": "Smith", "team_name": "X", "nationality": "AUS", "stat_value": 55.0}]}
        record_season_leaders(2027, leaders_v1, "2027-09-30 10:00", self.db)
        leaders_v2 = {"Batting Average": [{"name": "Warner", "team_name": "X", "nationality": "AUS", "stat_value": 60.0}]}
        record_season_leaders(2027, leaders_v2, "2027-09-30 11:00", self.db)
        result = fetch_season_leaders(2027, self.db)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["player_name"], "Warner")

    def test_fetch_all_seasons(self):
        for s in (2027, 2028):
            record_season_leaders(s, {"Batting Average": [{"name": f"P{s}", "team_name": "X", "nationality": "ENG", "stat_value": 50.0}]}, f"{s}-09-30", self.db)
        all_leaders = fetch_all_season_leaders(10, self.db)
        seasons = {l["season"] for l in all_leaders}
        self.assertEqual(seasons, {2027, 2028})


if __name__ == "__main__":
    unittest.main()
