"""Steamworks preparation layer with safe local stubs.

No Steam SDK calls are made until a real app ID and approved binding
are provided. The public API is intentionally stable so the stub can later be
replaced without modifying gameplay screens.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any

from src.utilities.launcher import create_recovery_save, database_integrity


LOGGER = logging.getLogger("stumped")


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str


# Merged achievement list from src/models/achievements.py
ACHIEVEMENTS = [
    Achievement("ACH_FIRST_WIN", "First Victory", "Win your first match as manager."),
    Achievement("ACH_FIRST_DRAW", "Hard Fought Draw", "Draw your first match as manager."),
    Achievement("ACH_SEASON_SURVIVOR", "Season Survivor", "Complete your first full season."),
    Achievement("ACH_TWO_SEASON_VETERAN", "Two-Season Veteran", "Complete two full seasons."),
    Achievement("ACH_FIVE_SEASON_LEGEND", "Five-Season Legend", "Complete five full seasons."),
    Achievement("ACH_CENTURY_MANAGER", "Century Manager", "Manage 100 matches."),
    Achievement("ACH_WINNING_MANAGER", "Winning Manager", "Achieve 50 wins as manager."),
    Achievement("ACH_ELITE_MANAGER", "Elite Manager", "Achieve 100 wins as manager."),
    Achievement("ACH_HAT_TRICK_HERO", "Hat Trick Hero", "A bowler takes a hat-trick in a match."),
    Achievement("ACH_DOUBLE_CENTURY", "Double Century", "A batsman scores 200+ in an innings."),
    Achievement("ACH_PERFECT_GAME", "Perfect Game", "Win a match without losing any wickets."),
    Achievement("ACH_RUN_CHASE_MASTER", "Run Chase Master", "Successfully chase 200+ in T20."),
    Achievement("ACH_CENTURY_MAKER", "Century Maker", "A batsman scores 100+ in an innings."),
    Achievement("ACH_FIVE_WICKET_HAUL", "Five-Wicket Haul", "A bowler takes 5+ wickets in an innings."),
    Achievement("ACH_TEN_WICKET_MATCH", "Ten-Wicket Match", "A bowler takes 10+ wickets in a match."),
    Achievement("ACH_DUCK_HUNTER", "Duck Hunter", "Bowling team dismisses opposition for under 50."),
    Achievement("ACH_SUPER_OVER_HERO", "Super Over Hero", "Win a Super Over."),
    Achievement("ACH_PROMOTION_PARTY", "Promotion Party", "Get promoted to a higher division."),
    Achievement("ACH_RELEGATION_SURVIVOR", "Relegation Survivor", "Avoid relegation in final match."),
    Achievement("ACH_DIVISION_ONE_CHAMPION", "Division One Champion", "Win Division 1 title."),
    Achievement("ACH_TREBLE_WINNER", "Treble Winner", "Win league, cup, and international same season."),
    Achievement("ACH_CUP_GLORY", "Cup Glory", "Win the Domestic Knockout Cup or T20 Cup."),
    Achievement("ACH_UNDEFEATED_SEASON", "Undefeated Season", "Complete a league season undefeated."),
    Achievement("ACH_FINANCIAL_WIZARD", "Financial Wizard", "Reach £10M in club finances."),
    Achievement("ACH_YOUTH_DEVELOPER", "Youth Developer", "Promote 5 players from academy to first team."),
    Achievement("ACH_STAFF_MASTER", "Staff Master", "Hire coaches in all three departments."),
    Achievement("ACH_FACILITY_MOGUL", "Facility Mogul", "Upgrade all facilities to max level."),
    Achievement("ACH_BOARD_FAVOURITE", "Board Favourite", "Reach 90+ board confidence."),
    Achievement("ACH_SQUAD_DEPTH", "Squad Depth", "Have 25+ players with 60+ overall."),
    Achievement("ACH_TRANSFER_MASTER", "Transfer Master", "Sign 20 players through transfers."),
    Achievement("ACH_CONTRACT_GURU", "Contract Guru", "Successfully negotiate 10 contract renewals."),
    Achievement("ACH_PLAYER_COLLECTOR", "Player Collector", "Have 50 different players in career."),
    Achievement("ACH_INTERNATIONAL_EXPORT", "International Export", "Have 5+ players called up to international duty."),
    Achievement("ACH_SCOUTING_NETWORK", "Scouting Network", "Scout 30+ players."),
    Achievement("ACH_DEBUT_CALLUP", "International Debut", "First player called up to international duty."),
    Achievement("ACH_INTERNATIONAL_WINNER", "International Winner", "Your player's nation wins international series."),
    Achievement("ACH_ASHES_LEGEND", "Ashes Legend", "Your player scores 150+ in an Ashes Test."),
    Achievement("ACH_MULTIPLE_INTERNATIONALS", "International Factory", "Have 3+ players called up in same window."),
]


class SteamIntegration:
    """Successful no-op Steam facade with local achievement/cloud emulation."""

    def __init__(self, writable_root: str | Path, app_id: str | int | None = None,
                 user_id: str | int | None = None, steam_root: str | Path | None = None) -> None:
        self.writable_root = Path(writable_root)
        self.app_id = str(app_id or "APP_ID_PENDING")
        self.user_id = str(user_id or "LOCAL_USER")
        configured = steam_root or os.environ.get("STEAM_PATH")
        if configured: self.steam_root = Path(configured)
        else:
            conventional = Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam"
            self.steam_root = conventional if conventional.exists() else self.writable_root / "Steam"
        self.remote_path = self.steam_root / "userdata" / self.user_id / self.app_id / "remote"
        self.state_path = self.writable_root / "steam_stub.json"
        self.initialised = False
        self.unlocked: set[str] = set()

    def initialise(self) -> bool:
        self.remote_path.mkdir(parents=True, exist_ok=True)
        if self.state_path.exists():
            try: self.unlocked = set(json.loads(self.state_path.read_text(encoding="utf-8")).get("achievements", []))
            except (OSError, json.JSONDecodeError): self.unlocked = set()
        self.initialised = True
        LOGGER.info(f"Steam stub initialised (app id: {self.app_id})")
        return True

    def shutdown(self) -> bool:
        self._save_state(); self.initialised = False
        return True

    def run_callbacks(self) -> bool: return True
    def is_overlay_enabled(self) -> bool: return True
    def open_overlay(self, page: str = "Community") -> bool:
        LOGGER.info(f"Steam overlay stub requested: {page}"); return True

    def unlock_achievement(self, achievement_id: str) -> bool:
        if achievement_id not in {achievement.id for achievement in ACHIEVEMENTS}:
            LOGGER.warning(f"Unknown achievement id: {achievement_id}"); return False
        self.unlocked.add(achievement_id); self._save_state()
        return True

    def clear_achievement(self, achievement_id: str) -> bool:
        self.unlocked.discard(achievement_id); self._save_state(); return True

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"app_id": self.app_id, "user_id": self.user_id,
                                    "achievements": sorted(self.unlocked)}, indent=2) + "\n", encoding="utf-8")

    def cloud_save(self, local_database: str | Path) -> bool:
        self.remote_path.mkdir(parents=True, exist_ok=True)
        return create_recovery_save(local_database, self.remote_path / "cricket_manager.db")

    def cloud_load(self, local_database: str | Path) -> bool:
        cloud = self.remote_path / "cricket_manager.db"
        if not cloud.exists() or not database_integrity(cloud)[0]: return False
        target = Path(local_database); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cloud, target)
        return database_integrity(target)[0]

    def evaluate_match(self, result: dict[str, Any], user_team_id: int) -> bool:
        if result.get("format") == "Test": self.unlock_achievement("ACH_TEST_DEBUT")
        if result.get("super_over") and result.get("winner_id") == user_team_id: self.unlock_achievement("ACH_SUPER_OVER_HERO")
        for innings in result.get("innings", []):
            for batter in innings.get("batting", []):
                if batter.get("runs", 0) >= 100: self.unlock_achievement("ACH_CENTURY_MAKER")
                if batter.get("runs", 0) >= 200: self.unlock_achievement("ACH_DOUBLE_CENTURY")
                if batter.get("runs", 0) == 0 and batter.get("balls", 0) == 1 and not batter.get("not_out", True):
                    self.unlock_achievement("ACH_GOLDEN_DUCK")
            for bowler in innings.get("bowling", []):
                if bowler.get("wickets", 0) >= 5: self.unlock_achievement("ACH_FIVE_WICKET_HAUL")
        return True

