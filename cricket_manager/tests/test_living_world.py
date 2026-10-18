"""v5.0.0 living-world regressions: gate revenue for every completed
match, season prize money at rollover, and the persisted selection/
behaviour counters feeding squad cohesion."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from competition import CompetitionEngine
from database import (connect, fetch_financial_log, fetch_players,
                      initialise_database, load_behaviour_counters,
                      update_behaviour_counters)


class TemporaryGameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "test.db"
        initialise_database(self.database)

    def tearDown(self) -> None:
        self.directory.cleanup()


class LivingWorldTests(TemporaryGameTest):
    def test_league_match_posts_gate_revenue(self) -> None:
        """v5.0.0: competitive home matches earn matchday income, not just
        friendlies — the finance loop must not reduce to wages-vs-sponsor."""
        engine = CompetitionEngine(self.database, seed=7)
        with connect(self.database) as connection:
            team = int(connection.execute("SELECT id FROM teams ORDER BY id LIMIT 1").fetchone()[0])
            connection.execute("UPDATE teams SET fan_morale=80, stadium_capacity=20000, "
                               "ticket_price=24 WHERE id=?", (team,))
        before = {entry["id"] for entry in fetch_financial_log(team, database_path=self.database)}
        engine._post_gate_revenue({"home_team": team, "round_name": ""}, {})
        new_entries = [entry for entry in fetch_financial_log(team, database_path=self.database)
                       if entry["id"] not in before]
        gates = [entry for entry in new_entries if entry["category"] == "Matchday Revenue"]
        self.assertTrue(gates, f"expected a gate receipt entry, saw: {new_entries}")
        self.assertEqual(gates[0]["kind"], "INCOME")
        self.assertGreater(gates[0]["amount"], 0)
        self.assertIn("Gate receipts", gates[0]["description"])

    def test_rollover_pays_prize_money(self) -> None:
        """Every club receives league prize money at the rollover, and the
        standings leader banks the largest share."""
        engine = CompetitionEngine(self.database, seed=99)
        engine.ensure_season(2026)
        from src.models.league_config import LEAGUE_NAMES
        with connect(self.database) as connection:
            div1 = connection.execute(
                "SELECT id FROM competitions WHERE name=? AND season=2026",
                (LEAGUE_NAMES[1],)).fetchone()[0]
            leader = connection.execute(
                "SELECT team_id FROM league_standings WHERE competition_id=? "
                "ORDER BY points DESC, team_id ASC LIMIT 1", (div1,)).fetchone()[0]
        engine.rollover_season(2026)
        with connect(self.database) as connection:
            prize = {row[0]: row[1] for row in connection.execute(
                "SELECT team_id, amount FROM financial_log "
                "WHERE description LIKE '%league finish%' AND amount>0")}
        self.assertTrue(prize)
        self.assertIn(leader, prize)
        self.assertEqual(max(prize.values()), prize[leader],
                         "division champion must take the top share of the prize pot")

    def test_behaviour_counters_persist_across_sessions(self) -> None:
        with connect(self.database) as connection:
            team = int(connection.execute("SELECT id FROM teams ORDER BY id LIMIT 1").fetchone()[0])
            player = int(connection.execute(
                "SELECT id FROM players WHERE team_id=? AND academy_squad=0 ORDER BY id LIMIT 1",
                (team,)).fetchone()[0])
        update_behaviour_counters(team, {player}, database_path=self.database)
        update_behaviour_counters(team, set(), database_path=self.database)
        counters = load_behaviour_counters(team, database_path=self.database)
        self.assertEqual(counters[player]["matches_out_xi"], 1)
        self.assertIn("low_morale_streak", counters[player])


if __name__ == "__main__":
    unittest.main()
