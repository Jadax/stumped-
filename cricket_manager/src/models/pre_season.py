"""Pre-season friendlies — pure functions for scheduling and revenue.

Generates 3–4 pre-season friendly fixtures for each club before the
competitive season begins (March). Friendlies serve three purposes:
  1. Revenue generation (gate receipts)
  2. Squad cohesion building (same XI repetition)
  3. Tactical testing before competitive matches

All functions are pure (no DB access) — callers wire persistence.
"""
from __future__ import annotations

import random as _rng
from datetime import date, timedelta
from typing import Any

# Pre-season window: first three weeks of March
PRE_SEASON_START_MONTH = 3
PRE_SEASON_START_DAY = 1
FRIENDLY_COUNT_RANGE = (3, 4)
FRIENDLY_FORMAT = "T20"


def generate_pre_season_fixtures(
    user_team_id: int,
    all_team_ids: list[int],
    all_team_names: dict[int, str],
    season_year: int,
    rng: _rng.Random | None = None,
) -> list[dict[str, Any]]:
    """Generate 3–4 pre-season friendly fixtures for the user's team.

    Returns a list of dicts with keys: home_team, away_team, home_name,
    away_name, date, format.
    """
    r = rng or _rng.Random(f"friendlies:{user_team_id}:{season_year}")
    num_friendlies = r.randint(*FRIENDLY_COUNT_RANGE)
    opponents = [tid for tid in all_team_ids if tid != user_team_id]
    if not opponents:
        return []
    chosen_opponents = r.sample(opponents, min(num_friendlies, len(opponents)))
    # Alternate home/away
    fixtures = []
    start = date(season_year, PRE_SEASON_START_MONTH, PRE_SEASON_START_DAY)
    for i, opp_id in enumerate(chosen_opponents):
        fixture_date = start + timedelta(days=i * 4)
        is_home = i % 2 == 0
        home = user_team_id if is_home else opp_id
        away = opp_id if is_home else user_team_id
        fixtures.append({
            "home_team": home,
            "away_team": away,
            "home_name": all_team_names.get(home, "Home"),
            "away_name": all_team_names.get(away, "Away"),
            "date": fixture_date.isoformat(),
            "format": FRIENDLY_FORMAT,
        })
    return fixtures


def friendly_gate_revenue(
    stadium_capacity: int,
    ticket_price: int,
    attendance_pct: float = 0.65,
) -> int:
    """Estimate gate revenue for a friendly match.

    Friendlies draw ~65% of a competitive match's attendance by default.
    """
    attendance = int(stadium_capacity * attendance_pct)
    return attendance * ticket_price


def friendly_attendance(
    stadium_capacity: int,
    attendance_pct: float = 0.65,
) -> int:
    """Estimated attendance for a friendly."""
    return int(stadium_capacity * attendance_pct)


def format_friendly_fixtures(fixtures: list[dict[str, Any]]) -> str:
    """Human-readable list of pre-season friendlies."""
    if not fixtures:
        return "No pre-season friendlies scheduled."
    lines = ["Pre-season friendlies:"]
    for f in fixtures:
        venue = "Home" if f["home_team"] == fixtures[0].get("home_team", -1) else "Away"
        lines.append(f"  {f['date']} — {f['home_name']} vs {f['away_name']} ({venue}, {f['format']})")
    return "\n".join(lines)
