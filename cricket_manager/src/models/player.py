"""Authoritative player attribute model shared by simulation and management."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

ATTRIBUTE_DEFAULTS = {
    "batting": {"attack": 50, "defence": 50, "technique_vs_pace": 50,
                "technique_vs_spin": 50, "concentration": 50, "power": 50,
                "timing": 50, "running": 50},
    "bowling": {"pace": 50, "accuracy": 50, "variation": 50, "stamina": 50,
                "swing_or_spin": 50, "control": 50, "deception": 50},
    "fielding": {"catching": 50, "throwing": 50, "reflexes": 50, "agility": 50,
                 "keeping": 20, "ground_fielding": 50},
    "mental": {"experience": 50, "consistency": 50, "big_match": 50,
               "fitness": 50, "endurance": 50, "morale": 50, "leadership": 50},
    "physical": {"fitness": 50, "endurance": 50, "speed": 50, "agility": 50,
                 "strength": 50},
}

BOWLING_STYLES = ("Fast", "Fast-Medium", "Medium-Fast", "Medium", "Off-Spin",
                  "Leg-Spin", "Left-Arm Spin", "Left-Arm Fast")
SPIN_STYLES = {"Off-Spin", "Leg-Spin", "Left-Arm Spin"}

def clamp(value: float) -> int: return max(0, min(100, round(value)))

def expanded_groups(player: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """Return complete 0-100 groups while accepting every older save format."""
    result: dict[str, dict[str, int]] = {}
    for group, defaults in ATTRIBUTE_DEFAULTS.items():
        source = dict(player.get(group, {}) or {})
        if group == "physical" and not source:
            mental, fielding = player.get("mental", {}) or {}, player.get("fielding", {}) or {}
            source = {"fitness": mental.get("fitness", 50), "endurance": mental.get("endurance", mental.get("fitness", 50)),
                      "speed": fielding.get("agility", 50), "agility": fielding.get("agility", 50),
                      "strength": mental.get("fitness", 50)}
        result[group] = {key: clamp(source.get(key, default)) for key, default in defaults.items()}
    if str(player.get("role", "")) == "Wicketkeeper" and "keeping" not in (player.get("fielding", {}) or {}):
        result["fielding"]["keeping"] = clamp((result["fielding"]["reflexes"] * .6) + 25)
    return result

def infer_bowling_style(player: Mapping[str, Any]) -> str:
    explicit = player.get("bowling_style")
    if explicit in BOWLING_STYLES: return str(explicit)
    bowling = expanded_groups(player)["bowling"]
    pid = int(player.get("id", 0))
    if bowling["pace"] >= 78: return "Left-Arm Fast" if pid % 7 == 0 else "Fast"
    if bowling["pace"] >= 65: return "Fast-Medium" if pid % 2 else "Medium-Fast"
    if bowling["swing_or_spin"] >= bowling["pace"] + 8:
        return ("Off-Spin", "Leg-Spin", "Left-Arm Spin")[pid % 3]
    return "Medium"

def natural_batting_aggression(player: Mapping[str, Any]) -> int:
    """A player's inherent scoring temperament (1-10), from attack vs. concentration.

    Mirrors the accumulator-vs-boundary-hitter split real management sims model as
    a player trait, not just a manager-chosen dial — a high-attack/low-concentration
    player defaults to attacking orders, a high-concentration anchor defaults to
    conservative ones, independent of whatever the manager later overrides.
    """
    batting = expanded_groups(player)["batting"]
    return max(1, min(10, round(5 + (batting["attack"] - batting["concentration"]) / 12)))

def natural_bowling_aggression(player: Mapping[str, Any]) -> int:
    """Inherent attacking intent with the ball (1-10), from pace/variation vs. accuracy."""
    bowling = expanded_groups(player)["bowling"]
    strike_intent = max(bowling["pace"], bowling["variation"])
    return max(1, min(10, round(5 + (strike_intent - bowling["accuracy"]) / 12)))

def calculate_wage(overall: int, age: int, role: str, potential: int,
                   league_reputation: int = 70, contract_years: int = 2) -> int:
    """Weekly wage in base GBP; elite scarcity creates the realistic top tail."""
    ability = max(20, overall)
    base = 180 + (ability / 100) ** 3.15 * 92_000
    peak = 1.12 if 24 <= age <= 31 else .78 if age < 20 else .94 if age <= 35 else .70
    role_factor = 1.08 if role == "All-Rounder" else 1.04 if role == "Wicketkeeper" else 1.0
    upside = 1 + max(0, potential - overall) * (.008 if age < 24 else .002)
    reputation = .55 + max(20, min(100, league_reputation)) / 155
    security = 1 + max(0, contract_years - 1) * .015
    return max(250, int(round(base * peak * role_factor * upside * reputation * security / 50) * 50))

@dataclass(frozen=True)
class PlayerTactics:
    batting_aggression: int = 5
    bowling_aggression: int = 5
    bowling_style: str = "Medium"
    preferred_line: str = "Off Stump"
    preferred_length: str = "Good"

    @classmethod
    def from_player(cls, player: Mapping[str, Any]) -> "PlayerTactics":
        return cls(max(1, min(10, int(player.get("batting_aggression", 5)))),
                   max(1, min(10, int(player.get("bowling_aggression", 5)))),
                   infer_bowling_style(player), str(player.get("preferred_line", "Off Stump")),
                   str(player.get("preferred_length", "Good")))
