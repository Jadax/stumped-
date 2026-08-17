"""v4.86.0: rich milestone stories — debuts, cap milestones, career-best announcements.

Pure functions only; DB writes live in database.py (record_narrative_event,
called from ipc_server.py _record_match_honours).
"""
from __future__ import annotations
from typing import Any

# Cap milestone thresholds — matches played triggers
CAP_MILESTONES = {50, 100, 150, 200, 250, 300}


def detect_debut(match_count: int) -> bool:
    """True if this is the player's first match (match_count == 1)."""
    return match_count == 1


def detect_cap_milestone(match_count: int) -> int | None:
    """Return the milestone number (50, 100, etc.) if match_count hits one,
    otherwise None."""
    if match_count in CAP_MILESTONES:
        return match_count
    return None


def detect_career_best_batting(runs: int, previous_best: int) -> dict[str, Any] | None:
    """If ``runs`` exceeds ``previous_best``, return career-best detail dict."""
    if runs > previous_best:
        return {
            "type": "batting",
            "value": runs,
            "previous_best": previous_best,
        }
    return None


def detect_career_best_bowling(wickets: int, runs_conceded: int,
                                prev_best_wickets: int,
                                prev_best_runs: int) -> dict[str, Any] | None:
    """If this bowling spell is a career best (more wickets, or same wickets
    with fewer runs), return career-best detail dict."""
    if wickets > prev_best_wickets:
        return {
            "type": "bowling",
            "value": f"{wickets}/{runs_conceded}",
            "previous_best": f"{prev_best_wickets}/{prev_best_runs}",
        }
    if wickets == prev_best_wickets and wickets > 0 and runs_conceded < prev_best_runs:
        return {
            "type": "bowling",
            "value": f"{wickets}/{runs_conceded}",
            "previous_best": f"{prev_best_wickets}/{prev_best_runs}",
        }
    return None


def format_milestone_body(player_name: str, team_name: str,
                          milestone_type: str, detail: dict[str, Any] | int | str) -> str:
    """Rich, flavourful narrative text for each milestone type.

    ``milestone_type`` is one of: 'debut', 'cap_milestone', 'career_best_batting',
    'career_best_bowling', 'century', 'five_wickets'.
    ``detail`` is type-dependent (int for cap count, dict for career bests).
    """
    if milestone_type == "debut":
        return (f"{player_name} makes his debut for {team_name}. "
                f"A proud moment as he pulls on the club colours for the first time "
                f"and looks to make an immediate impression.")

    if milestone_type == "cap_milestone":
        caps = detail if isinstance(detail, (int, str)) else detail.get("value", "?")
        return (f"{player_name} earns his {caps}th cap for {team_name} — "
                f"a remarkable milestone that speaks to his dedication and consistency "
                f"at the club. The crowd acknowledges a true servant of the side.")

    if milestone_type == "career_best_batting":
        d = detail if isinstance(detail, dict) else {}
        runs = d.get("value", "?")
        prev = d.get("previous_best", "?")
        return (f"{player_name} records a career-best batting performance: "
                f"{runs} for {team_name}, surpassing his previous best of {prev}. "
                f"A innings he will remember for the rest of his career.")

    if milestone_type == "career_best_bowling":
        d = detail if isinstance(detail, dict) else {}
        figures = d.get("value", "?")
        prev = d.get("previous_best", "?")
        return (f"{player_name} delivers a career-best bowling spell: "
                f"{figures} for {team_name}, eclipsing his previous best of {prev}. "
                f"A match-winning performance that will live long in the memory.")

    if milestone_type == "century":
        runs = detail if isinstance(detail, (int, str)) else detail.get("value", "?")
        return (f"{player_name} reaches a splendid century ({runs}) for {team_name} — "
                f"a masterclass in concentration and shot-making that has "
                f"the crowd on their feet.")

    if milestone_type == "five_wickets":
        d = detail if isinstance(detail, dict) else {}
        wkts = d.get("wickets", detail) if isinstance(d, dict) else detail
        runs_c = d.get("runs", "") if isinstance(d, dict) else ""
        return (f"{player_name} takes a magnificent five-wicket haul "
                f"({wkts}" + (f"/{runs_c}" if runs_c else "") + f") for {team_name} — "
                f"a devastating spell that torn through the opposition batting lineup.")

    return f"{player_name} achieves a notable milestone for {team_name}."
