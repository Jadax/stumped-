"""Competition editor — allows users to view and edit competition settings.
"""
from __future__ import annotations

import json
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH
from pathlib import Path


def get_competitions(database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return all competitions for the current season."""
    with connect(database_path) as connection:
        season = connection.execute("SELECT current_date FROM user_data WHERE id=1").fetchone()
        if not season:
            return []
        year = season[0][:4]
        rows = connection.execute(
            "SELECT id, name, type, season FROM competitions WHERE season=? ORDER BY name",
            (int(year),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_competition_standings(competition_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return standings for a competition."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT ls.*, t.name AS team_name
               FROM league_standings ls JOIN teams t ON t.id = ls.team_id
               WHERE ls.competition_id=?
               ORDER BY ls.points DESC, ls.won DESC, ls.net_run_rate DESC""",
            (competition_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_competition_matches(competition_id: int, database_path: str | Path = DEFAULT_DATABASE_PATH) -> list[dict[str, Any]]:
    """Return matches for a competition."""
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT m.*, h.name AS home_name, a.name AS away_name
               FROM matches m
               JOIN teams h ON h.id = m.home_team
               JOIN teams a ON a.id = m.away_team
               WHERE m.competition_id=?
               ORDER BY m.date""",
            (competition_id,),
        ).fetchall()
    return [dict(row) for row in rows]
