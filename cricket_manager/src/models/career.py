"""Manager career depth: board confidence, world ratings, and season awards.

Pure functions over plain player/standing dicts so the career screen and
future season-end processing share one source of truth.
"""
from __future__ import annotations

from statistics import mean
from typing import Any, Mapping, Sequence

CONFIDENCE_LABELS = ((80, "Delighted"), (60, "Content"), (40, "Under pressure"), (0, "Ultimatum"))


def _group(player: Mapping[str, Any], group: str) -> float:
    values = [int(v) for v in dict(player.get(group, {})).values()]
    return mean(values) if values else 50.0


def rating_points(player: Mapping[str, Any], discipline: str = "batting") -> int:
    """ICC-style 0–1000 ranking points from ability, form, and consistency."""
    form = int(player.get("form", 50))
    consistency = int(player.get("mental", {}).get("consistency", 50))
    if discipline == "bowling":
        skill = _group(player, "bowling")
    elif discipline == "all-round":
        skill = (_group(player, "batting") + _group(player, "bowling")) / 2
    else:
        skill = _group(player, "batting")
    points = skill * 7.4 + form * 1.8 + consistency * .8
    return max(0, min(1000, round(points)))


def world_ratings(players: Sequence[Mapping[str, Any]], discipline: str = "batting", limit: int = 20) -> list[dict[str, Any]]:
    """The world's best players in a discipline, ranked with points."""
    if discipline == "bowling":
        pool = [p for p in players if p.get("role") in ("Bowler", "All-Rounder")]
    elif discipline == "all-round":
        pool = [p for p in players if p.get("role") == "All-Rounder"]
    else:
        pool = [p for p in players if p.get("role") in ("Batter", "All-Rounder", "Wicketkeeper")]
    ranked = sorted(pool, key=lambda p: rating_points(p, discipline), reverse=True)[:limit]
    return [{"rank": i + 1, "name": p["name"], "nationality": p.get("nationality", "—"),
             "team": p.get("team_name", ""), "points": rating_points(p, discipline)}
            for i, p in enumerate(ranked)]


def board_confidence(position: int, team_count: int, objective_position: int, cash: int) -> dict[str, Any]:
    """Board mood from league position vs objective and the bank balance."""
    score = 55 + (objective_position - position) * 7
    score += 8 if cash > 0 else -12
    score = max(5, min(98, score))
    label = next(name for threshold, name in CONFIDENCE_LABELS if score >= threshold)
    return {"score": score, "label": label}


def manager_reputation(matches_played: int, wins: int, trophies: int = 0) -> dict[str, Any]:
    """A slow-moving 0–100 standing that trophies accelerate."""
    win_rate = wins / matches_played if matches_played else 0.0
    score = max(1, min(100, round(20 + win_rate * 55 + trophies * 8 + min(matches_played, 60) * .2)))
    bands = ((85, "World class"), (70, "Respected"), (50, "Established"), (30, "Promising"), (0, "Unproven"))
    label = next(name for threshold, name in bands if score >= threshold)
    return {"score": score, "label": label}


def season_awards(players: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Current season-award leaders across the supplied player pool."""
    if not players:
        return {}

    def best(pool: Sequence[Mapping[str, Any]], key) -> Mapping[str, Any] | None:
        pool = list(pool)
        return max(pool, key=key) if pool else None

    batter = best(players, lambda p: rating_points(p, "batting"))
    bowler = best([p for p in players if p.get("role") in ("Bowler", "All-Rounder")] or players,
                  lambda p: rating_points(p, "bowling"))
    young = best([p for p in players if int(p.get("age", 30)) <= 21] or players,
                 lambda p: int(p.get("potential", p.get("overall", 0))) + int(p.get("form", 50)))
    overall = best(players, lambda p: rating_points(p, "all-round") + int(p.get("form", 50)))
    awards = {}
    for title, player in (("Batter of the Season", batter), ("Bowler of the Season", bowler),
                          ("Young Player of the Season", young), ("Player of the Season", overall)):
        if player is not None:
            awards[title] = {"name": player["name"], "team": player.get("team_name", ""),
                             "nationality": player.get("nationality", "—")}
    return awards
