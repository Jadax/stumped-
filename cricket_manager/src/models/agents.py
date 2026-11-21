"""v5.3.1: player agents.

Every senior professional is represented by an agent. Agents differ in how
greedy they are (the premium they ask over a player's market value), how
patient they are at the table (rounds of talks before they walk out), the
fee they take from the club on every deal, and how they feel about the
manager's club after past dealings. Super-agents look after the best
players and drive the hardest bargains.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

AGENCY_SUFFIXES = ("Sports Management", "Talent Group", "Athlete Partners", "Cricket Agency",
                   "Representation", "Associates", "Global Sports", "& Co.")

#: Number of agents in the world; about one in eight is a super-agent.
AGENT_COUNT = 60
SUPER_AGENT_SHARE = 0.125


def generate_agent(rng: random.Random, name: str, super_agent: bool = False) -> dict[str, Any]:
    if super_agent:
        greed = rng.randint(14, 20)
        patience = rng.randint(2, 4)
        fee_pct = round(rng.uniform(0.08, 0.12), 3)
    else:
        greed = rng.randint(4, 16)
        patience = rng.randint(2, 5)
        fee_pct = round(rng.uniform(0.03, 0.08), 3)
    agency = f"{name.split()[-1]} {rng.choice(AGENCY_SUFFIXES)}"
    return {"name": name, "agency": agency, "greed": greed, "patience": patience, "fee_pct": fee_pct,
            "super_agent": int(super_agent), "relationship": 50}


def agent_style(agent: Mapping[str, Any] | None) -> str:
    """One-line description the manager sees before talks."""
    if not agent:
        return "No agent: the player negotiates for himself"
    greed, patience = int(agent.get("greed", 10)), int(agent.get("patience", 3))
    tone = "hard bargainer" if greed >= 15 else "fair negotiator" if greed >= 8 else "easy-going"
    temper = "short fuse" if patience <= 2 else "patient" if patience >= 5 else "reasonable patience"
    relation = int(agent.get("relationship", 50))
    feel = "likes your club" if relation >= 65 else "wary of your club" if relation <= 35 else "neutral towards you"
    return f"{tone}, {temper}, {feel}"


def demand_multiplier(agent: Mapping[str, Any] | None) -> float:
    """Premium over the player's own valuation the agent asks for."""
    if not agent:
        return 1.0
    relationship = int(agent.get("relationship", 50))
    return 1.0 + (int(agent.get("greed", 10)) - 10) * 0.015 - (relationship - 50) * 0.001


def agent_fee(agent: Mapping[str, Any] | None, weekly_wage: int) -> int:
    """The agent's cut, paid by the club when a deal is signed: a share of
    the player's first year's wages."""
    if not agent:
        return 0
    return int(round(float(agent.get("fee_pct", 0.05)) * weekly_wage * 52 / 1_000) * 1_000)
