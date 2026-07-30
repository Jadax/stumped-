"""Tests for keeper batting roles (roadmap: keeper_batting).

Wicketkeepers should be classified by batting ability and placed at
appropriate batting order positions, with specialist keepers batting
more defensively and keeper-batsmen batting more freely.
"""
from __future__ import annotations
import os
import tempfile
import unittest


def _fresh_db() -> str:
    from database import initialise_database
    path = os.path.join(tempfile.mkdtemp(), "keeper_bat.db")
    initialise_database(path)
    return path


class KeeperBatRoleClassificationTests(unittest.TestCase):
    def test_non_keeper_returns_specialist(self) -> None:
        from database import classify_keeper_batting_role
        player = {"role": "Batsman", "batting": {"attack": 80}, "fielding": {"keeping": 30}}
        self.assertEqual(classify_keeper_batting_role(player), "specialist_keeper")

    def test_keeper_with_strong_batting_is_keeper_batsman(self) -> None:
        import json
        from database import classify_keeper_batting_role
        batting = {"attack": 70, "defence": 68, "technique_vs_pace": 65, "technique_vs_spin": 65,
                    "concentration": 60, "timing": 65, "power": 60}
        fielding = {"keeping": 68, "reflexes": 65, "catching": 65, "throwing": 55, "agility": 55}
        player = {"role": "Wicketkeeper",
                   "batting_json": json.dumps(batting),
                   "fielding_json": json.dumps(fielding)}
        self.assertEqual(classify_keeper_batting_role(player), "keeper_batsman")

    def test_keeper_with_weak_batting_is_specialist(self) -> None:
        import json
        from database import classify_keeper_batting_role
        batting = {"attack": 35, "defence": 38, "technique_vs_pace": 35, "technique_vs_spin": 35,
                    "concentration": 35, "timing": 35, "power": 35}
        fielding = {"keeping": 75, "reflexes": 70, "catching": 70, "throwing": 60, "agility": 60}
        player = {"role": "Wicketkeeper",
                   "batting_json": json.dumps(batting),
                   "fielding_json": json.dumps(fielding)}
        self.assertEqual(classify_keeper_batting_role(player), "specialist_keeper")

    def test_keeper_with_balanced_stats_is_allround(self) -> None:
        import json
        from database import classify_keeper_batting_role
        batting = {"attack": 55, "defence": 55, "technique_vs_pace": 55, "technique_vs_spin": 55,
                    "concentration": 55, "timing": 55, "power": 55}
        fielding = {"keeping": 65, "reflexes": 62, "catching": 62, "throwing": 55, "agility": 55}
        player = {"role": "Wicketkeeper",
                   "batting_json": json.dumps(batting),
                   "fielding_json": json.dumps(fielding)}
        self.assertEqual(classify_keeper_batting_role(player), "allround_keeper")


class BestXiKeeperPositionTests(unittest.TestCase):
    def test_keeper_is_not_at_top_of_batting_order(self) -> None:
        from database import fetch_players
        import ipc_server
        db = _fresh_db()
        players = fetch_players(1, db)
        xi = ipc_server._best_xi(players)
        keeper = next((p for p in xi if p.get("role") == "Wicketkeeper"), None)
        self.assertIsNotNone(keeper, "XI must include a wicketkeeper")
        keeper_pos = xi.index(keeper)
        # Keeper should bat at position 7 (index 6), not opener (index 0)
        self.assertGreater(keeper_pos, 3, "keeper should not bat in top 4")

    def test_keeper_is_in_the_xi(self) -> None:
        from database import fetch_players
        import ipc_server
        db = _fresh_db()
        players = fetch_players(1, db)
        xi = ipc_server._best_xi(players)
        self.assertEqual(len(xi), 11)
        self.assertTrue(any(p.get("role") == "Wicketkeeper" for p in xi))


class KeeperBatRoleIPCMethodTests(unittest.TestCase):
    def test_ipc_returns_keeper_batting_role(self) -> None:
        from database import fetch_players, get_team_summary
        import ipc_server
        db = _fresh_db()
        team = get_team_summary(1, db)
        players = fetch_players(1, db)
        keeper = next(p for p in players if p["role"] == "Wicketkeeper")
        ctx = {"database_path": db, "team": team, "players": players}
        handler = ipc_server.METHODS["get_keeper_batting_role"]
        result = handler({"player_id": keeper["id"]}, ctx)
        self.assertIn(result["role"], ("keeper_batsman", "allround_keeper", "specialist_keeper"))
        self.assertIn("label", result)


if __name__ == "__main__":
    unittest.main()
