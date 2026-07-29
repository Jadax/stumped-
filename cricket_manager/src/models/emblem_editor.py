"""Emblem editor — allows users to customise team emblems/logos.
Stores emblem data in the game_state table keyed by team_id.
"""
from __future__ import annotations

import json
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH
from pathlib import Path


def get_team_emblem(team_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Return the emblem configuration for a team."""
    key = f"emblem_{team_id}"
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT value_json FROM game_state WHERE key=?", (key,)
        ).fetchone()
    if row:
        return json.loads(row[0])
    # Default emblem
    return {
        "shape": "shield",
        "primary_color": "#1a5276",
        "secondary_color": "#f39c12",
        "icon": "star",
    }


def set_team_emblem(team_id: int, emblem: dict[str, Any],
                     database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Save emblem configuration for a team."""
    key = f"emblem_{team_id}"
    with connect(database_path) as connection:
        connection.execute(
            """INSERT INTO game_state (key, value_json, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
                   value_json = excluded.value_json,
                   updated_at = CURRENT_TIMESTAMP""",
            (key, json.dumps(emblem)),
        )


# Emblem shapes
EMBLEM_SHAPES = ["shield", "circle", "diamond", "hexagon", "star", "crest"]

# Emblem icons
EMBLEM_ICONS = ["star", "lion", "eagle", "bat", "ball", "stump", "crown", "flame"]

# Default emblem colours per country
COUNTRY_EMBLEM_COLOURS = {
    "English": {"primary_color": "#1a5276", "secondary_color": "#f39c12"},
    "Australian": {"primary_color": "#1e3a5f", "secondary_color": "#f4d03f"},
    "Indian": {"primary_color": "#1a5276", "secondary_color": "#f39c12"},
    "Pakistani": {"primary_color": "#1a5276", "secondary_color": "#27ae60"},
    "South African": {"primary_color": "#27ae60", "secondary_color": "#f4d03f"},
    "New Zealander": {"primary_color": "#000000", "secondary_color": "#f4d03f"},
    "West Indian": {"primary_color": "#7d3c98", "secondary_color": "#f4d03f"},
    "Sri Lankan": {"primary_color": "#1a5276", "secondary_color": "#f4d03f"},
    "Bangladeshi": {"primary_color": "#1a5276", "secondary_color": "#27ae60"},
    "Zimbabwean": {"primary_color": "#1a5276", "secondary_color": "#f4d03f"},
}


def get_default_emblem(nationality: str) -> dict[str, Any]:
    """Return default emblem for a nationality."""
    colours = COUNTRY_EMBLEM_COLOURS.get(nationality, {
        "primary_color": "#1a5276",
        "secondary_color": "#f39c12",
    })
    return {
        "shape": "shield",
        "primary_color": colours["primary_color"],
        "secondary_color": colours["secondary_color"],
        "icon": "star",
    }
