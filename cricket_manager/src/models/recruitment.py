"""Recruitment Hub logic shared by the pygame and Godot clients.

Previously lived only inside ui/recruitment.py's RecruitmentHubScreen,
which meant the headless Godot IPC backend couldn't reuse it without
either duplicating the rules or importing a pygame-dependent module
(docs/GRAPHICS_MIGRATION_PLAN.md's Recruitment placeholder note). Moved
here, pure Python, so both clients call the same rules.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from .squad_metrics import group_average

ROLE_TARGETS = {"Wicketkeeper": 2, "Bowler": 5, "All-Rounder": 2, "Batsman": 5}


def role_gaps(players: Sequence[Mapping[str, Any]]) -> list[tuple[str, int]]:
    """Roles currently below their target headcount, in ROLE_TARGETS order."""
    counts: dict[str, int] = {}
    for player in players:
        counts[player["role"]] = counts.get(player["role"], 0) + 1
    return [(role, counts.get(role, 0)) for role, target in ROLE_TARGETS.items() if counts.get(role, 0) < target]


def weakest_attribute_group(players: Sequence[Mapping[str, Any]]) -> str:
    """Which of batting/bowling/fielding the squad is weakest in, on average."""
    return min(("batting", "bowling", "fielding"),
              key=lambda group: sum(group_average(p, group) for p in players) / max(1, len(players)))


def contract_watch(players: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Players with a year or less remaining, soonest-expiring first."""
    expiring = sorted((p for p in players if p.get("contract_years_remaining", 2) <= 1),
                      key=lambda p: p.get("contract_years_remaining", 0))
    return [{"id": p["id"], "name": p["name"], "contract_years_remaining": p.get("contract_years_remaining", 0),
            "status": "Free agent" if p.get("contract_years_remaining", 0) <= 0 else "Expires this year"}
            for p in expiring]
