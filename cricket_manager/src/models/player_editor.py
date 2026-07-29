"""Player editor — allows users to edit player attributes, role, and contract details.
"""
from __future__ import annotations

import json
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH
from pathlib import Path


def get_player_for_edit(player_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Return player data suitable for editing."""
    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
    if not row:
        return {}
    player = dict(row)
    for field in ("batting_json", "bowling_json", "fielding_json", "mental_json", "physical_json"):
        player[field.removesuffix("_json")] = json.loads(player.pop(field))
    player.pop("traits", None)  # traits are generated, not user-editable
    return player


def update_player(player_id: int, updates: dict[str, Any],
                   database_path: str | Path = DEFAULT_DATABASE_PATH) -> bool:
    """Update player attributes. Returns True if successful."""
    allowed_fields = {"name", "age", "nationality", "role", "overall", "form",
                      "potential", "wage", "contract_years_remaining", "batting_json",
                      "bowling_json", "fielding_json", "mental_json", "physical_json",
                      "batting_aggression", "bowling_aggression", "personality"}
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered:
        return False
    # Convert dict fields to JSON strings
    for field in ("batting_json", "bowling_json", "fielding_json", "mental_json", "physical_json"):
        if field in filtered and isinstance(filtered[field], dict):
            filtered[field] = json.dumps(filtered[field])
    set_clause = ", ".join(f"{k}=?" for k in filtered)
    values = list(filtered.values()) + [player_id]
    with connect(database_path) as connection:
        connection.execute(f"UPDATE players SET {set_clause} WHERE id=?", tuple(values))
    return True


def get_all_players_for_edit(database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return all players for the editor (lightweight, no JSON parsing)."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, age, nationality, role, overall, form, potential, team_id FROM players ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]
