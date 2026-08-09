"""v4.62.0: regional scouting (roadmap.json's academy_expansion item).
Before this, recruit_youth silently forced every prospect's nationality to
the club's own country_id no matter what a caller passed in — every club's
academy could only ever produce prospects of its own home nation, with no
lever to scout further afield.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import database


class RegionalScoutingModelTests(unittest.TestCase):
    def _db(self) -> str:
        db = os.path.join(tempfile.mkdtemp(), "academy.db")
        database.initialise_database(db)
        return db

    def _team_id(self, db: str) -> int:
        return database.load_game(db)["user"]["current_team_id"]

    def test_focus_defaults_to_the_clubs_own_nation(self) -> None:
        db = self._db()
        team_id = self._team_id(db)
        with database.connect(db) as connection:
            country_id = connection.execute("SELECT country_id FROM teams WHERE id=?", (team_id,)).fetchone()[0]
        self.assertEqual(database.get_academy_focus_nation(team_id, db), country_id)

    def test_set_academy_focus_nation_persists_and_is_read_back(self) -> None:
        db = self._db()
        team_id = self._team_id(db)
        database.set_academy_focus_nation(team_id, "india", db)
        self.assertEqual(database.get_academy_focus_nation(team_id, db), "india")

    def test_set_academy_focus_nation_rejects_unknown_country(self) -> None:
        db = self._db()
        team_id = self._team_id(db)
        with self.assertRaises(ValueError):
            database.set_academy_focus_nation(team_id, "narnia", db)

    def test_recruit_youth_uses_the_chosen_focus_nation_not_the_clubs_own(self) -> None:
        db = self._db()
        team_id = self._team_id(db)
        with database.connect(db) as connection:
            home_country = connection.execute("SELECT country_id FROM teams WHERE id=?", (team_id,)).fetchone()[0]
        target = "india" if home_country != "india" else "australia"
        database.set_academy_focus_nation(team_id, target, db)
        created = database.recruit_youth(team_id, count=3, database_path=db)
        expected_nationality = database.ACADEMY_NATION_NAMES[target]
        self.assertTrue(created)
        self.assertTrue(all(p["nationality"] == expected_nationality for p in created))

    def test_recruit_youth_still_defaults_to_home_nation_without_a_focus_set(self) -> None:
        db = self._db()
        team_id = self._team_id(db)
        with database.connect(db) as connection:
            home_country = connection.execute("SELECT country_id FROM teams WHERE id=?", (team_id,)).fetchone()[0]
        created = database.recruit_youth(team_id, count=3, database_path=db)
        expected_nationality = database.ACADEMY_NATION_NAMES[home_country]
        self.assertTrue(all(p["nationality"] == expected_nationality for p in created))

    def test_academy_nation_names_covers_every_league_playing_nation(self) -> None:
        from src.models.nations_config import NATION_COMPETITIONS
        self.assertEqual(set(database.ACADEMY_NATION_NAMES), set(NATION_COMPETITIONS))


class RegionalScoutingIpcTests(unittest.TestCase):
    def _context(self) -> dict:
        from database import fetch_players, get_team_summary, initialise_database, load_game
        db = os.path.join(tempfile.mkdtemp(), "academy_ipc.db")
        initialise_database(db)
        game_data = load_game(db)
        team = get_team_summary(game_data["user"]["current_team_id"], db)
        return {"database_path": db, "team": team, "players": fetch_players(team["id"], db), "game_data": game_data}

    def test_get_academy_scouting_region_defaults_to_home(self) -> None:
        import ipc_server
        ctx = self._context()
        result = ipc_server._get_academy_scouting_region({}, ctx)
        self.assertEqual(result["current"], result["home"])
        self.assertEqual(len(result["nations"]), 10)

    def test_set_academy_scouting_region_round_trips_and_rejects_unknown(self) -> None:
        import ipc_server
        ctx = self._context()
        target = "pakistan" if ctx["team"]["country_id"] != "pakistan" else "india"
        result = ipc_server._set_academy_scouting_region({"country_id": target}, ctx)
        self.assertEqual(result["current"], target)
        with self.assertRaises(ValueError):
            ipc_server._set_academy_scouting_region({"country_id": "atlantis"}, ctx)

    def test_recruit_youth_prospects_ipc_respects_the_chosen_region(self) -> None:
        import ipc_server
        ctx = self._context()
        target = "pakistan" if ctx["team"]["country_id"] != "pakistan" else "india"
        ipc_server._set_academy_scouting_region({"country_id": target}, ctx)
        result = ipc_server._recruit_youth_prospects({}, ctx)
        expected_nationality = ipc_server.ACADEMY_NATION_NAMES[target]
        academy_players = [p for p in result["players"] if p.get("nationality") == expected_nationality]
        self.assertTrue(academy_players)


if __name__ == "__main__":
    unittest.main()
