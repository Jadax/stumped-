"""Focused validation for Steps 1-3 of the pre-release startup flow."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.controllers.game_controller import GameController
from src.models.manager import Manager


DATA_ROOT = Path(__file__).resolve().parents[1] / "src" / "data"


class StartupFlowTests(unittest.TestCase):
    def test_world_data_has_requested_members_and_competitions(self) -> None:
        countries = json.loads((DATA_ROOT / "countries.json").read_text(encoding="utf-8"))["countries"]
        leagues = json.loads((DATA_ROOT / "leagues.json").read_text(encoding="utf-8"))["leagues"]
        self.assertEqual(len(countries), 20)
        self.assertEqual(sum(country["membership"] == "Full Member" for country in countries), 12)
        self.assertEqual({league["format"] for league in leagues}, {"T20", "ODI", "Test"})

    def test_manager_profile_contains_management_identity_only(self) -> None:
        self.assertEqual(set(Manager.__dataclass_fields__), {"name", "nationality", "background"})
        self.assertEqual(Manager("Alex Morgan", "England", "Coach").to_dict()["name"], "Alex Morgan")
        with self.assertRaises(ValueError):
            Manager("A", "England", "Coach").validate()

    def test_setup_expands_enabled_countries_into_leagues(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            context = {"database_path": Path(folder) / "setup.db"}
            controller = GameController(context, lambda _name: None, lambda: None)
            draft = controller.save_new_game_setup(
                Manager("Alex Morgan", "England", "Coach"), "Career", "Normal", ["england", "australia"]
            )
            self.assertEqual(len(draft["enabled_leagues"]), 6)
            self.assertEqual(draft["status"], "awaiting_team_or_tournament_selection")
            self.assertEqual(context["new_game_setup"], draft)

    def test_world_cup_and_custom_tournament_generate_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            destinations = []
            context = {"database_path": Path(folder) / "modes.db", "team": {"id": 1, "name": "Club"}}
            controller = GameController(context, destinations.append, lambda: None)
            controller.confirm_world_cup_team("england")
            self.assertEqual(context["world_cup"]["stage"], "Group Stage")
            self.assertEqual(len(context["world_cup"]["fixtures"]), 30)
            controller.confirm_custom_tournament(["england", "australia", "india", "pakistan"], "T20")
            self.assertEqual(len(context["custom_tournament"]["fixtures"]), 6)
            self.assertEqual(destinations[-1], "Dashboard")


if __name__ == "__main__":
    unittest.main()
