"""Pure squad-metric helpers shared by every client (pygame's ui/shared_components.py
re-exports these; the headless Godot IPC backend imports them directly so it never
has to import anything pygame-dependent — see docs/GRAPHICS_MIGRATION_PLAN.md)."""
from __future__ import annotations
from typing import Any, Mapping


def group_average(player: Mapping[str, Any], group: str) -> int:
    values = player.get(group, {}).values()
    return round(sum(values) / max(1, len(player.get(group, {}))))


def estimated_value(player: Mapping[str, Any]) -> int:
    age_factor = max(.35, 1.3 - max(0, player["age"] - 26) * .045)
    potential_factor = 1 + max(0, player["potential"] - player["overall"]) / 65
    return int(round((player["overall"] ** 3 * 12 * age_factor * potential_factor) / 1000) * 1000)
