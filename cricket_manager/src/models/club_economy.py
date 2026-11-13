"""v5.3.0 club economy constants shared by the weekly finance pass
(competition.py) and the Finances forecast (database.forecast_finances), so
the projection always matches what actually posts."""
from __future__ import annotations

#: Weekly central (broadcast/board) funding as a share of the division's
#: median weekly wage bill — top tiers receive the bigger share.
CENTRAL_FUNDING_SHARE = {1: 0.85, 2: 0.75, 3: 0.6, 4: 0.45, 5: 0.35}

#: Share of gate takings spent on matchday operations (stewarding, ground
#: staff, policing) — charged weekly in the club finance pass.
MATCHDAY_OPERATING_SHARE = 0.35

#: Lower tiers draw smaller crowds than the stadium alone would suggest.
GATE_DIVISION_FACTOR = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.3}


def central_funding(median_weekly_bill: float, division: int, weekly_gate_average: float = 0.0) -> int:
    """Weekly central funding: the gap between the division's median wage
    bill and its clubs' recent average gate income (so an average club
    roughly breaks even and the economy cannot inflate without bound),
    never less than a division-tiered floor."""
    floor = median_weekly_bill * CENTRAL_FUNDING_SHARE.get(int(division or 5), 0.35) * 0.35
    return int(max(floor, median_weekly_bill * 0.97 - weekly_gate_average))


def gate_factor(division: int) -> float:
    return GATE_DIVISION_FACTOR.get(int(division or 5), 0.3)
