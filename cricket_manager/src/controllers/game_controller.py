"""Startup-flow coordinator for main-menu and new-game screens."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from database import apply_difficulty_starting_cash, fetch_teams, save_game, set_current_team
from src.models.manager import Manager
from src.models.difficulty import DifficultyManager


class GameController:
    """Own startup state without coupling screens to the database schema."""

    def __init__(self, context: dict[str, Any], navigate: Callable[[str], None],
                 request_exit: Callable[[], None]) -> None:
        self.context = context
        self.navigate = navigate
        self.request_exit = request_exit
        self.data_root = Path(__file__).resolve().parents[1] / "data"
        self.countries = self._read_json("countries.json")["countries"]
        self.leagues = self._read_json("leagues.json")["leagues"]

    def _read_json(self, filename: str) -> dict[str, Any]:
        with (self.data_root / filename).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def begin_new_game(self) -> None:
        self.navigate("New Game Setup")

    def load_existing_game(self) -> None:
        """The launcher has already integrity-checked and loaded the local save."""
        self.context["toast"] = "Save loaded"
        self.navigate("Dashboard")

    def save_new_game_setup(self, manager: Manager, mode: str, difficulty: str,
                            enabled_countries: list[str], primary_country: str | None = None) -> dict[str, Any]:
        """Validate and persist the setup draft ready for the next selection step."""
        profile = manager.to_dict()
        if mode not in {"Career", "World Cup", "Tournament"}:
            raise ValueError("Select a game mode.")
        if difficulty not in {"Easy", "Normal", "Hard"}:
            raise ValueError("Select a difficulty.")
        if not enabled_countries:
            raise ValueError("Enable at least one domestic league nation.")
        # Older saves/tests did not store a primary country.  Preserve that
        # compatibility while the new-game UI still requires an explicit card
        # click before its Continue button is enabled.
        if mode == "Career" and primary_country is None:
            primary_country = enabled_countries[0]
        if mode == "Career" and primary_country not in enabled_countries:
            raise ValueError("Choose the country whose league you want to manage in.")

        enabled_leagues = [
            league["id"] for league in self.leagues if league["country"] in enabled_countries
        ]
        draft = {
            "manager": profile,
            "mode": mode,
            "difficulty": difficulty,
            "enabled_countries": list(enabled_countries),
            "enabled_leagues": enabled_leagues,
            "primary_country": primary_country,
            "status": "awaiting_team_or_tournament_selection",
        }
        save_game({"new_game_setup": draft}, self.context["database_path"])
        self.context["new_game_setup"] = draft
        self.context["toast"] = "New-game setup saved"
        return draft

    def continue_from_setup(self, draft: dict[str, Any]) -> None:
        """Route a validated setup to its mode-specific selection screen."""
        destination = {"Career": "Career Team Selection", "World Cup": "World Cup Setup",
                       "Tournament": "Tournament Setup"}[draft["mode"]]
        self.navigate(destination)

    def selectable_teams(self) -> list[dict[str, Any]]:
        return fetch_teams(self.context["database_path"])

    def confirm_career_team(self, team_id: int) -> None:
        """Start a career at the selected club and rebuild shared app state."""
        set_current_team(team_id, self.context["database_path"])
        level = self.context.get("new_game_setup", {}).get("difficulty", "Normal")
        apply_difficulty_starting_cash(
            team_id, DifficultyManager(level).user_cash_bonus, self.context["database_path"]
        )
        save_game({"career_team_id": int(team_id), "game_mode": "Career"}, self.context["database_path"])
        refresh = self.context.get("refresh_campaign")
        if refresh:
            refresh()
        self.context["toast"] = "Career created successfully"
        self.navigate("Dashboard")

    def confirm_world_cup_team(self, country_id: str) -> None:
        """Persist the chosen nation for a focused international tournament."""
        nation = next((country for country in self.countries if country["id"] == country_id), None)
        if nation is None or nation["membership"] != "Full Member":
            raise ValueError("Select a qualified full-member nation.")
        qualified = [country for country in self.countries if country["membership"] == "Full Member"]
        groups = {"A": qualified[::2], "B": qualified[1::2]}
        fixtures = []
        for group_name, members in groups.items():
            for index, home in enumerate(members):
                for away in members[index + 1:]:
                    fixtures.append({"group": group_name, "home": home["id"], "away": away["id"],
                                     "format": "ODI", "completed": False})
        tournament = {"name": "World Cup", "selected_team": nation["id"], "groups": groups,
                      "fixtures": fixtures, "stage": "Group Stage"}
        save_game({"game_mode": "World Cup", "national_team": nation, "world_cup": tournament}, self.context["database_path"])
        self.context["game_mode"] = "World Cup"
        self.context["national_team"] = nation
        self.context["world_cup"] = tournament
        display_team = dict(self.context["team"]); display_team["name"] = nation["name"]
        self.context["team"] = display_team
        self.context["toast"] = f"World Cup campaign created for {nation['name']}"
        self.navigate("Dashboard")

    def confirm_custom_tournament(self, country_ids: list[str], match_format: str) -> None:
        if not 4 <= len(country_ids) <= 12:
            raise ValueError("Select between 4 and 12 teams.")
        if match_format not in {"T20", "ODI", "Test"}:
            raise ValueError("Select a valid format.")
        teams = [country for country in self.countries if country["id"] in country_ids]
        fixtures = []
        for index, home in enumerate(teams):
            for away in teams[index + 1:]:
                fixtures.append({"home": home["id"], "away": away["id"], "format": match_format, "completed": False})
        state = {"name": "Custom Championship", "format": match_format, "teams": teams,
                 "fixtures": fixtures, "stage": "League"}
        save_game({"game_mode": "Tournament", "custom_tournament": state}, self.context["database_path"])
        self.context.update({"game_mode": "Tournament", "custom_tournament": state,
                             "toast": f"Custom {match_format} tournament created"})
        self.navigate("Dashboard")
