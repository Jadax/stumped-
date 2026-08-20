"""League statistics leaders — pure functions for ranking players by career stats.

All functions are pure (no DB access). Callers wire persistence.
"""
from __future__ import annotations

from typing import Any


def batting_leaders(players: list[dict[str, Any]], min_innings: int = 5, limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by batting average (descending), requiring *min_innings* dismissals.

    Each entry in *players* must have at least:
      name, team_name, career_innings, career_not_outs (default 0),
      career_runs, career_batting_average, career_strike_rate,
      career_hundreds (default 0), career_fifties (default 0),
      career_highest_score (default 0), career_matches.

    Returns the top *limit* players as a list of dicts sorted by average.
    """
    qualified = []
    for p in players:
        innings = int(p.get("career_innings", 0))
        not_outs = int(p.get("career_not_outs", 0))
        dismissals = innings - not_outs
        if dismissals < min_innings:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "innings": innings,
            "not_outs": not_outs,
            "runs": int(p.get("career_runs", 0)),
            "average": float(p.get("career_batting_average", 0)),
            "strike_rate": float(p.get("career_strike_rate", 0)),
            "hundreds": int(p.get("career_hundreds", 0)),
            "fifties": int(p.get("career_fifties", 0)),
            "highest_score": int(p.get("career_highest_score", 0)),
        })
    qualified.sort(key=lambda x: (-x["average"], -x["runs"]))
    return qualified[:limit]


def bowling_leaders(players: list[dict[str, Any]], min_wickets: int = 10, limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by bowling average (ascending), requiring *min_wickets* wickets.

    Each entry in *players* must have at least:
      name, team_name, career_wickets, career_bowling_average,
      career_economy, career_overs, career_matches,
      career_five_wickets (default 0).

    Returns the top *limit* bowlers as a list of dicts sorted by average.
    """
    qualified = []
    for p in players:
        wickets = int(p.get("career_wickets", 0))
        if wickets < min_wickets:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "wickets": wickets,
            "average": float(p.get("career_bowling_average", 0)),
            "economy": float(p.get("career_economy", 0)),
            "overs": p.get("career_overs", "0.0"),
            "five_wickets": int(p.get("career_five_wickets", 0)),
        })
    qualified.sort(key=lambda x: (-x["wickets"], x["average"]))
    return qualified[:limit]


def most_runs_leaders(players: list[dict[str, Any]], min_innings: int = 3, limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by total runs scored (descending)."""
    qualified = []
    for p in players:
        if int(p.get("career_innings", 0)) < min_innings:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "innings": int(p.get("career_innings", 0)),
            "runs": int(p.get("career_runs", 0)),
            "average": float(p.get("career_batting_average", 0)),
            "hundreds": int(p.get("career_hundreds", 0)),
            "fifties": int(p.get("career_fifties", 0)),
        })
    qualified.sort(key=lambda x: -x["runs"])
    return qualified[:limit]


def most_wickets_leaders(players: list[dict[str, Any]], min_wickets: int = 3, limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by total wickets taken (descending)."""
    qualified = []
    for p in players:
        if int(p.get("career_wickets", 0)) < min_wickets:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "wickets": int(p.get("career_wickets", 0)),
            "average": float(p.get("career_bowling_average", 0)),
            "economy": float(p.get("career_economy", 0)),
            "five_wickets": int(p.get("career_five_wickets", 0)),
        })
    qualified.sort(key=lambda x: -x["wickets"])
    return qualified[:limit]


def top_strike_rate_batters(players: list[dict[str, Any]], min_runs: int = 200, limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by strike rate (descending), requiring minimum runs scored."""
    qualified = []
    for p in players:
        if int(p.get("career_runs", 0)) < min_runs:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "runs": int(p.get("career_runs", 0)),
            "average": float(p.get("career_batting_average", 0)),
            "strike_rate": float(p.get("career_strike_rate", 0)),
            "innings": int(p.get("career_innings", 0)),
        })
    qualified.sort(key=lambda x: -x["strike_rate"])
    return qualified[:limit]


def best_economy_bowlers(players: list[dict[str, Any]], min_overs: str = "50.0", limit: int = 10) -> list[dict[str, Any]]:
    """Rank players by economy rate (ascending), requiring minimum overs bowled.

    *min_overs* is a formatted string like "50.0" (overs.balls).
    """
    min_balls = _overs_to_balls(min_overs)
    qualified = []
    for p in players:
        balls = _overs_to_balls(p.get("career_overs", "0.0"))
        if balls < min_balls:
            continue
        qualified.append({
            "name": p.get("name", "Unknown"),
            "team_name": p.get("team_name", ""),
            "nationality": p.get("nationality", ""),
            "matches": int(p.get("career_matches", 0)),
            "wickets": int(p.get("career_wickets", 0)),
            "economy": float(p.get("career_economy", 0)),
            "overs": p.get("career_overs", "0.0"),
            "average": float(p.get("career_bowling_average", 0)),
        })
    qualified.sort(key=lambda x: x["economy"])
    return qualified[:limit]


def _overs_to_balls(overs_str: str | Any) -> int:
    """Convert an overs string like '125.3' to total balls (753)."""
    try:
        parts = str(overs_str).split(".")
        whole = int(parts[0])
        balls = int(parts[1]) if len(parts) > 1 else 0
        return whole * 6 + balls
    except (ValueError, IndexError):
        return 0
