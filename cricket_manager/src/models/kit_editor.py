"""Kit editor — allows users to customise team kit colours.
Stores kit data in the game_state table keyed by team_id.
"""
from __future__ import annotations

import json
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH
from pathlib import Path


def get_team_kit(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Return the kit configuration for a team."""
    key = f"kit_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (key,)
        ).fetchone()
    if row:
        return json.loads(row[0])
    # Default kit colours
    return {
        "primary": "#1a5276",  # Dark blue
        "secondary": "#ffffff",  # White
        "accent": "#f39c12",  # Gold
        "name_color": "#ffffff",
    }


def set_team_kit(team_id: int, kit: dict[str, Any],
                  database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Save kit configuration for a team."""
    key = f"kit_{team_id}"
    with connect(database_path) as connection:
        connection.execute(
            """INSERT INTO game_state (key, value_json, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
                   value_json = excluded.value_json,
                   updated_at = CURRENT_TIMESTAMP""",
            (key, json.dumps(kit)),
        )


def get_all_kits(database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[int, dict[str, Any]]:
    """Return all team kits."""
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT key, value_json FROM game_state WHERE key LIKE 'kit_%'"
        ).fetchall()
    kits = {}
    for row in rows:
        team_id = int(row[0].replace("kit_", ""))
        kits[team_id] = json.loads(row[1])
    return kits


# Default colour palettes for each country
COUNTRY_KIT_COLOURS = {
    "English": {"primary": "#1a5276", "secondary": "#ffffff", "accent": "#f39c12"},
    "Australian": {"primary": "#1e3a5f", "secondary": "#f4d03f", "accent": "#27ae60"},
    "Indian": {"primary": "#1a5276", "secondary": "#f39c12", "accent": "#27ae60"},
    "Pakistani": {"primary": "#1a5276", "secondary": "#27ae60", "accent": "#f39c12"},
    "South African": {"primary": "#27ae60", "secondary": "#f4d03f", "accent": "#1a5276"},
    "New Zealander": {"primary": "#000000", "secondary": "#f4d03f", "accent": "#27ae60"},
    "West Indian": {"primary": "#7d3c98", "secondary": "#f4d03f", "accent": "#27ae60"},
    "Sri Lankan": {"primary": "#1a5276", "secondary": "#f4d03f", "accent": "#27ae60"},
    "Bangladeshi": {"primary": "#1a5276", "secondary": "#27ae60", "accent": "#f39c12"},
    "Zimbabwean": {"primary": "#1a5276", "secondary": "#f4d03f", "accent": "#27ae60"},
}


def get_default_kit(nationality: str) -> dict[str, Any]:
    """Return default kit colours for a nationality."""
    return COUNTRY_KIT_COLOURS.get(nationality, {
        "primary": "#1a5276",
        "secondary": "#ffffff",
        "accent": "#f39c12",
        "name_color": "#ffffff",
    })
