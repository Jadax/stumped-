"""Pure squad-metric helpers shared by every client (pygame's ui/shared_components.py
re-exports these; the headless Godot IPC backend imports them directly so it never
has to import anything pygame-dependent — see docs/GRAPHICS_MIGRATION_PLAN.md)."""
from __future__ import annotations
from typing import Any, Mapping


def group_average(player: Mapping[str, Any], group: str) -> int:
    values = player.get(group, {}).values()
    return round(sum(values) / max(1, len(player.get(group, {}))))


def estimated_value(player: Mapping[str, Any]) -> int:
    """Squad-overview value estimate — a thin wrapper around
    src/models/transfer.py's transfer_value() at a neutral (60) team
    reputation, so every screen quotes the same number for the same
    player. Used to be an independent formula that diverged from
    transfer_value by 30-40% for the same player depending on which
    screen you looked at; consolidated to a single source of truth."""
    from .transfer import transfer_value
    return transfer_value(player)
