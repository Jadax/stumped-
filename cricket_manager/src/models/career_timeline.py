"""v4.88.0: manager career timeline — pure functions for formatting and
aggregating timeline entries.

DB reads/writes live in database.py (record_career_timeline,
fetch_career_timeline).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH


def group_timeline_by_season(timeline: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group timeline entries by season number, preserving insertion order."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for entry in timeline:
        season = entry["season"]
        grouped.setdefault(season, []).append(entry)
    return grouped


def format_season_summary(team_id: int, season: int,
                          database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Build a season summary card: W/D/L, league position, trophies.

    Returns {"season": int, "played": int, "wins": int, "draws": int,
             "losses": int, "trophies": list[str], "position": int|None}
    """
    with connect(database_path) as connection:
        # Fetch season timeline entries for trophies
        trophy_rows = connection.execute(
            """SELECT title FROM career_timeline
               WHERE team_id=? AND season=? AND category='TROPHY'""",
            (team_id, season),
        ).fetchall()

        # Compute league position from points ordering
        position: int | None = None
        standings = connection.execute(
            """SELECT ls.team_id, ls.points
               FROM league_standings ls
               JOIN competitions c ON c.id = ls.competition_id
               WHERE c.season = ?
               ORDER BY ls.points DESC, ls.net_run_rate DESC""",
            (season,),
        ).fetchall()
        for idx, row in enumerate(standings, start=1):
            if row["team_id"] == team_id:
                position = idx
                break

        # Get W/D/L from matches
        wdl = connection.execute(
            """SELECT
                 SUM(CASE WHEN m.completed=1 AND
                    (json_extract(m.result_json,'$.winner')=?) THEN 1 ELSE 0 END) AS wins,
                 SUM(CASE WHEN m.completed=1 AND
                    (json_extract(m.result_json,'$.drawn')=1) THEN 1 ELSE 0 END) AS draws,
                 SUM(CASE WHEN m.completed=1 AND
                    json_extract(m.result_json,'$.winner') IS NOT NULL AND
                    json_extract(m.result_json,'$.winner')!=? AND
                    json_extract(m.result_json,'$.drawn')!=1 THEN 1 ELSE 0 END) AS losses,
                 SUM(CASE WHEN m.completed=1 THEN 1 ELSE 0 END) AS played
               FROM matches m
               WHERE (m.home_team=? OR m.away_team=?)""",
            (team_id, team_id, team_id, team_id),
        ).fetchone()

    trophies = [row["title"] for row in trophy_rows]
    return {
        "season": season,
        "played": wdl["played"] or 0 if wdl else 0,
        "wins": wdl["wins"] or 0 if wdl else 0,
        "draws": wdl["draws"] or 0 if wdl else 0,
        "losses": wdl["losses"] or 0 if wdl else 0,
        "trophies": trophies,
        "position": position,
    }


def format_timeline_entry(entry: dict[str, Any]) -> str:
    """Format a single timeline entry as a display string."""
    category = entry.get("category", "OTHER")
    title = entry.get("title", "")
    created_on = entry.get("created_on", "")

    prefix = ""
    if category == "PROMOTION":
        prefix = "PROMOTED"
    elif category == "RELEGATION":
        prefix = "RELEGATED"
    elif category == "TROPHY":
        prefix = "TROPHY"
    elif category == "MILESTONE":
        prefix = "MILESTONE"
    elif category == "SEASON_START":
        prefix = "NEW SEASON"
    elif category == "MANAGER_LEVEL":
        prefix = "LEVEL UP"
    elif category == "TRANSFER_HIGH":
        prefix = "TRANSFER"
    elif category == "RECORD":
        prefix = "RECORD"
    else:
        prefix = "EVENT"

    return f"[{created_on}] {prefix}: {title}"
