"""v4.66.0: real national squad/XI control (roadmap.json's
international_management item). Research before this found that every
national-team decision was 100% automatic — select_national_xi always
hardcoded the best-11 by overall, with no setter anywhere in the codebase.
Also found a real, separate bug while fixing this: database.get_national_xi
imported `select_national_xi` from src.models.international, a module that
has never defined that function (it only ever lived in database.py) —
every call raised ImportError, meaning ipc_server._get_national_team_ipc
(the National Team screen's backend) has been broken for any manager who
ever accepted a national job, with zero test coverage catching it.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import database


def _fresh_db() -> str:
    db = os.path.join(tempfile.mkdtemp(), "national.db")
    database.initialise_database(db)
    return db


class GetNationalXiBugFixTests(unittest.TestCase):
    def test_get_national_xi_does_not_raise_and_returns_eleven_players(self) -> None:
        db = _fresh_db()
        xi = database.get_national_xi("English", db)
        self.assertEqual(len(xi), 11)

    def test_get_national_xi_matches_select_national_xi_with_no_override(self) -> None:
        db = _fresh_db()
        via_get = [p["id"] for p in database.get_national_xi("Australian", db)]
        via_select = [p["id"] for p in database.select_national_xi("Australian", db)]
        self.assertEqual(via_get, via_select)


class OverrideTests(unittest.TestCase):
    def test_no_override_by_default(self) -> None:
        db = _fresh_db()
        self.assertIsNone(database.get_national_xi_override("English", db))

    def test_toggling_a_player_in_adds_them_to_the_override(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_id = connection.execute(
                "SELECT id FROM players WHERE nationality='English' LIMIT 1"
            ).fetchone()[0]
        current = database.toggle_national_xi("English", player_id, db)
        self.assertIn(player_id, current)

    def test_toggling_the_same_player_twice_removes_them_again(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_id = connection.execute(
                "SELECT id FROM players WHERE nationality='English' LIMIT 1"
            ).fetchone()[0]
        database.toggle_national_xi("English", player_id, db)
        current = database.toggle_national_xi("English", player_id, db)
        self.assertNotIn(player_id, current)

    def test_cannot_toggle_in_a_player_of_the_wrong_nationality(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_id = connection.execute(
                "SELECT id FROM players WHERE nationality!='English' LIMIT 1"
            ).fetchone()[0]
        with self.assertRaises(ValueError):
            database.toggle_national_xi("English", player_id, db)

    def test_a_twelfth_player_is_rejected(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_ids = [r[0] for r in connection.execute(
                "SELECT id FROM players WHERE nationality='English' LIMIT 12"
            )]
        for player_id in player_ids[:11]:
            database.toggle_national_xi("English", player_id, db)
        with self.assertRaises(ValueError):
            database.toggle_national_xi("English", player_ids[11], db)

    def test_a_complete_eleven_player_override_is_used_by_select_national_xi(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_ids = [r[0] for r in connection.execute(
                "SELECT id FROM players WHERE nationality='English' ORDER BY overall ASC LIMIT 11"
            )]
        for player_id in player_ids:
            database.toggle_national_xi("English", player_id, db)
        xi = database.select_national_xi("English", db)
        self.assertEqual({p["id"] for p in xi}, set(player_ids))

    def test_an_incomplete_override_falls_back_to_the_automatic_best_eleven(self) -> None:
        db = _fresh_db()
        with database.connect(db) as connection:
            player_id = connection.execute(
                "SELECT id FROM players WHERE nationality='English' LIMIT 1"
            ).fetchone()[0]
        database.toggle_national_xi("English", player_id, db)  # only 1 of 11
        xi = database.select_national_xi("English", db)
        automatic = database.select_national_xi("English", db)
        self.assertEqual(len(xi), 11)
        self.assertEqual([p["id"] for p in xi], [p["id"] for p in automatic])


class IpcNationalXiTests(unittest.TestCase):
    def _context_managing_england(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game, set_national_team_id
        from src.models.international import NATIONAL_TEAM_IDS
        db = os.path.join(tempfile.mkdtemp(), "national_ipc.db")
        initialise_database(db)
        set_national_team_id(NATIONAL_TEAM_IDS["English"], db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_get_national_team_does_not_error_and_reports_managing(self) -> None:
        import ipc_server
        ctx = self._context_managing_england()
        result = ipc_server._get_national_team_ipc({}, ctx)
        self.assertTrue(result["managing"])
        self.assertEqual(len(result["xi"]), 11)
        self.assertFalse(result["is_custom_xi"])

    def test_toggle_national_xi_ipc_updates_selection(self) -> None:
        import ipc_server
        ctx = self._context_managing_england()
        squad_player_id = ipc_server._get_national_team_ipc({}, ctx)["squad"][0]["id"]
        result = ipc_server._toggle_national_xi_ipc({"player_id": squad_player_id}, ctx)
        matching = [p for p in result["squad"] if p["id"] == squad_player_id]
        self.assertTrue(matching[0]["selected"])

    def test_toggle_national_xi_ipc_requires_managing_a_nation(self) -> None:
        import ipc_server
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "no_nation.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        ctx = {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}
        with self.assertRaises(ValueError):
            ipc_server._toggle_national_xi_ipc({"player_id": 1}, ctx)


if __name__ == "__main__":
    unittest.main()
