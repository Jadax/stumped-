"""v4.87.0: historical match context — head-to-head records and player vs
opposition stats, surfaced in the pre-match preview.

Pure functions only; DB reads via database.connect; no writes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database import connect, DEFAULT_DATABASE_PATH


def head_to_head(team_a_id: int, team_b_id: int, limit: int = 10,
                 database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Completed matches between two teams, most recent first.

    Returns {"played": N, "team_a_wins": N, "team_b_wins": N, "draws": N,
             "recent_results": [{"date": str, "winner_id": int|None,
                                 "home_team": int, "away_team": int,
                                 "home_runs": int, "away_runs": int,
                                 "summary": str}]}
    """
    with connect(database_path) as connection:
        rows = connection.execute(
            """SELECT id, date, home_team, away_team, result_json
               FROM matches
               WHERE completed = 1
                 AND ((home_team = ? AND away_team = ?)
                      OR (home_team = ? AND away_team = ?))
               ORDER BY date DESC
               LIMIT ?""",
            (team_a_id, team_b_id, team_b_id, team_a_id, limit),
        ).fetchall()

    results: list[dict[str, Any]] = []
    a_wins = b_wins = draws = 0
    for row in rows:
        res = json.loads(row["result_json"]) if row["result_json"] else {}
        winner = res.get("winner")
        home_runs = res.get("home_runs", 0)
        away_runs = res.get("away_runs", 0)
        drawn = res.get("drawn", False)
        tied = res.get("tied", False)

        if drawn or (winner is None and not tied):
            draws += 1
        elif winner == team_a_id:
            a_wins += 1
        elif winner == team_b_id:
            b_wins += 1

        summary_parts = []
        if home_runs or away_runs:
            summary_parts.append(f"{home_runs}-{away_runs}")
        if drawn:
            summary_parts.append("Drawn")
        elif tied:
            summary_parts.append("Tied")
        elif winner:
            winner_name = "Team A" if winner == team_a_id else "Team B"
            summary_parts.append(f"{winner_name} won")

        results.append({
            "date": row["date"],
            "winner_id": winner,
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_runs": home_runs,
            "away_runs": away_runs,
            "summary": " | ".join(summary_parts) if summary_parts else "No data",
        })

    return {
        "played": len(rows),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "recent_results": results,
    }


def player_vs_opposition(player_id: int, opposition_team_id: int,
                         database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Player's career record against a specific opposition team.

    Aggregates from player_match_events joined with matches to find
    all matches against the opposition, then sums batting runs and
    bowling wickets from event-level data.

    Returns {"matches": N, "runs": N, "average": float, "wickets": N,
             "bowling_average": float, "best_score": int, "best_bowling": str}
    """
    with connect(database_path) as connection:
        # Find all completed matches involving the opposition team
        match_rows = connection.execute(
            """SELECT m.id, m.home_team, m.away_team, m.result_json
               FROM matches m
               WHERE m.completed = 1
                 AND (m.home_team = ? OR m.away_team = ?)""",
            (opposition_team_id, opposition_team_id),
        ).fetchall()

        if not match_rows:
            return {"matches": 0, "runs": 0, "average": 0.0, "wickets": 0,
                    "bowling_average": 0.0, "best_score": 0, "best_bowling": "0/0"}

        match_ids = [row["id"] for row in match_rows]
        placeholders = ",".join("?" * len(match_ids))

        # Aggregate batting: sum runs per match where player batted
        batting_rows = connection.execute(
            f"""SELECT match_id, SUM(runs) AS match_runs
                FROM player_match_events
                WHERE player_id = ?
                  AND match_id IN ({placeholders})
                  AND event_type IN ('shot', 'boundary', 'running', 'extra')
                GROUP BY match_id""",
            (player_id, *match_ids),
        ).fetchall()

        # Aggregate bowling: sum wickets per match where player bowled
        bowling_rows = connection.execute(
            f"""SELECT match_id, SUM(wicket) AS match_wickets,
                       SUM(runs) AS match_runs_conceded
                FROM player_match_events
                WHERE player_id = ?
                  AND match_id IN ({placeholders})
                  AND event_type = 'delivery'
                GROUP BY match_id""",
            (player_id, *match_ids),
        ).fetchall()

    total_matches = len(set(
        [r["match_id"] for r in batting_rows] + [r["match_id"] for r in bowling_rows]
    ))
    total_runs = sum(r["match_runs"] for r in batting_rows)
    innings_with_runs = len([r for r in batting_rows if r["match_runs"] > 0])
    best_score = max((r["match_runs"] for r in batting_rows), default=0)

    total_wickets = sum(r["match_wickets"] for r in bowling_rows)
    total_runs_conceded = sum(r["match_runs_conceded"] for r in bowling_rows)
    bowling_innings = len([r for r in bowling_rows if r["match_wickets"] > 0])

    avg = round(total_runs / max(1, innings_with_runs), 1)
    bowl_avg = round(total_runs_conceded / max(1, total_wickets), 1) if total_wickets else 0.0

    best_bowl_str = "0/0"
    if bowling_rows:
        best = max(bowling_rows, key=lambda r: r["match_wickets"])
        if best["match_wickets"] > 0:
            best_bowl_str = f"{best['match_wickets']}/{best['match_runs_conceded']}"

    return {
        "matches": total_matches,
        "runs": total_runs,
        "average": avg,
        "wickets": total_wickets,
        "bowling_average": bowl_avg,
        "best_score": best_score,
        "best_bowling": best_bowl_str,
    }


def generate_match_context(user_team_id: int, fixture: dict[str, Any],
                           database_path: str | Path = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    """Build a rich historical context dict for the upcoming fixture.

    Combines head-to-head record with key player records against the
    opposition for the user's squad.

    Returns {"head_to_head": {...}, "key_batting": [...], "key_bowling": [...]}
    """
    home_team = int(fixture.get("home_team", 0))
    away_team = int(fixture.get("away_team", 0))
    opposition_id = away_team if user_team_id == home_team else home_team

    h2h = head_to_head(user_team_id, opposition_id, database_path=database_path)

    # Fetch user's current squad to find key performers
    key_batting: list[dict[str, Any]] = []
    key_bowling: list[dict[str, Any]] = []
    with connect(database_path) as connection:
        squad = connection.execute(
            "SELECT id, name FROM players WHERE team_id = ?",
            (user_team_id,),
        ).fetchall()

    for player in squad:
        pvo = player_vs_opposition(player["id"], opposition_id, database_path)
        if pvo["matches"] == 0:
            continue
        if pvo["runs"] > 50:
            key_batting.append({
                "name": player["name"],
                "matches": pvo["matches"],
                "runs": pvo["runs"],
                "average": pvo["average"],
                "best_score": pvo["best_score"],
            })
        if pvo["wickets"] > 3:
            key_bowling.append({
                "name": player["name"],
                "matches": pvo["matches"],
                "wickets": pvo["wickets"],
                "bowling_average": pvo["bowling_average"],
                "best_bowling": pvo["best_bowling"],
            })

    key_batting.sort(key=lambda x: x["average"], reverse=True)
    key_bowling.sort(key=lambda x: x["wickets"], reverse=True)

    return {
        "head_to_head": h2h,
        "key_batting": key_batting[:5],
        "key_bowling": key_bowling[:5],
    }
