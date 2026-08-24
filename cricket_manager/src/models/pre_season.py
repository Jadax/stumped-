"""Pre-season friendlies — pure functions for scheduling and revenue.

Generates a global pre-season friendly schedule before the competitive
season begins (March). Friendlies serve three purposes:
  1. Revenue generation (gate receipts)
  2. Squad cohesion building (same XI repetition)
  3. Tactical testing before competitive matches

v4.99.1: scheduling is one global pairing pass built as two two-legged
rounds — each leg shuffles all clubs, pairs them off, and plays the
pairing home on one March date and reversed on the next. By construction
no club is ever double-booked, and with an even number of clubs every
team plays exactly four matches, two home and two away (the previous
per-team independent sampling produced hundreds of conflicting
team-days).

All functions are pure (no DB access) — callers wire persistence.
"""
from __future__ import annotations

import random as _rng
from datetime import date
from typing import Any

# Pre-season window: four match days across early-to-mid March
PRE_SEASON_START_MONTH = 3
FRIENDLY_DAYS = (1, 5, 9, 13)
FRIENDLY_FORMAT = "T20"


def generate_pre_season_schedule(
    all_team_ids: list[int],
    all_team_names: dict[int, str],
    season_year: int,
    rng: _rng.Random | None = None,
) -> list[dict[str, Any]]:
    """Generate the full pre-season friendly schedule for every club.

    Returns a list of dicts with keys: home_team, away_team, home_name,
    away_name, date, format.  Deterministic for a given rng/seed.
    """
    r = rng or _rng.Random(f"friendlies:{season_year}")
    teams = [tid for tid in all_team_ids if tid is not None]
    if len(teams) < 2:
        return []
    fixtures: list[dict[str, Any]] = []
    # Two legs of two match days: within a leg the same pairing plays home
    # on the first day and away on the second, which guarantees every even
    # club count yields exactly two home and two away matches per team.
    for day_first, day_second in (FRIENDLY_DAYS[0:2], FRIENDLY_DAYS[2:4]):
        pool = list(teams)
        r.shuffle(pool)
        date_home = date(season_year, PRE_SEASON_START_MONTH, day_first).isoformat()
        date_away = date(season_year, PRE_SEASON_START_MONTH, day_second).isoformat()
        for i in range(0, len(pool) - 1, 2):
            first, second = pool[i], pool[i + 1]
            for home, away, fixture_date in (
                (first, second, date_home),
                (second, first, date_away),
            ):
                fixtures.append({
                    "home_team": home,
                    "away_team": away,
                    "home_name": all_team_names.get(home, "Home"),
                    "away_name": all_team_names.get(away, "Away"),
                    "date": fixture_date,
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


def format_friendly_fixtures(fixtures: list[dict[str, Any]], team_id: int) -> str:
    """Human-readable list of a club's pre-season friendlies.

    v4.99.1: takes the subject ``team_id`` so Home/Away labels are correct
    (the old version compared against the first fixture's home team).
    """
    if not fixtures:
        return "No pre-season friendlies scheduled."
    lines = ["Pre-season friendlies:"]
    for f in fixtures:
        venue = "Home" if f["home_team"] == team_id else "Away"
        lines.append(f"  {f['date']} — {f['home_name']} vs {f['away_name']} ({venue}, {f['format']})")
    return "\n".join(lines)
