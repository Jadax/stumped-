"""Steamworks preparation layer with safe local stubs.

No Steam SDK calls are made until a real app ID and approved binding are
provided. The public API is intentionally stable so the stub can later be
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


ACHIEVEMENTS = [
    Achievement("ACH_WIN_100", "Century of Victories", "Win 100 matches."),
    Achievement("ACH_CENTURY", "Century Scorer", "Score 100 or more in an innings."),
    Achievement("ACH_FIVE_WICKET", "Five-Wicket Haul", "Take five wickets in an innings."),
    Achievement("ACH_HAT_TRICK", "Hat-trick", "Take three wickets in three consecutive deliveries."),
    Achievement("ACH_PROMOTION", "Promotion Winner", "Earn promotion to Division 1."),
    Achievement("ACH_CUP_CHAMPION", "Cup Champion", "Win the domestic knockout cup."),
    Achievement("ACH_DOUBLE_WINNER", "Double Winner", "Win the league and cup in one season."),
    Achievement("ACH_1000_RUNS", "One Thousand Runs", "A player reaches 1,000 career runs."),
    Achievement("ACH_50_WICKETS", "Fifty Wickets", "A player reaches 50 career wickets."),
    Achievement("ACH_TEST_DEBUT", "Test Debut", "Manage your first Test match."),
    Achievement("ACH_CAPTAIN_50", "Long-serving Captain", "Captain the club for 50 matches."),
    Achievement("ACH_PERFECT_SEASON", "Perfect Season", "Finish a league season undefeated."),
    Achievement("ACH_COMEBACK_300", "Comeback Victory", "Successfully chase 300 or more."),
    Achievement("ACH_GOLDEN_DUCK", "Golden Duck", "Have a batter dismissed first ball."),
    Achievement("ACH_SUPER_OVER", "Super Over Specialist", "Win a match in a Super Over."),
    Achievement("ACH_DLS_WIN", "Weather Reader", "Win a rain-reduced match under DLS."),
    Achievement("ACH_YOUTH_STAR", "Academy Graduate", "Develop an academy player to 80 overall."),
    Achievement("ACH_RECORD_TRANSFER", "Record Signing", "Complete a transfer worth £5 million."),
    Achievement("ACH_MAX_FACILITY", "World-class Facilities", "Upgrade a facility to level five."),
    Achievement("ACH_CLEAN_SWEEP", "Clean Sweep", "Win every match in a series."),
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
        if result.get("super_over") and result.get("winner_id") == user_team_id: self.unlock_achievement("ACH_SUPER_OVER")
        for innings in result.get("innings", []):
            for batter in innings.get("batting", []):
                if batter.get("runs", 0) >= 100: self.unlock_achievement("ACH_CENTURY")
                if batter.get("runs", 0) == 0 and batter.get("balls", 0) == 1 and not batter.get("not_out", True):
                    self.unlock_achievement("ACH_GOLDEN_DUCK")
            for bowler in innings.get("bowling", []):
                if bowler.get("wickets", 0) >= 5: self.unlock_achievement("ACH_FIVE_WICKET")
        return True

