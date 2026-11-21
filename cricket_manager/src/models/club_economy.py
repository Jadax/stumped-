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


def funding_floor(median_weekly_bill: float, division: int) -> int:
    return int(median_weekly_bill * CENTRAL_FUNDING_SHARE.get(int(division or 5), 0.35) * 0.35)


def central_funding(median_weekly_bill: float, division: int, weekly_gate_average: float = 0.0) -> int:
    """Weekly central funding: the gap between the division's median wage
    bill and its clubs' recent average gate income (so an average club
    roughly breaks even and the economy cannot inflate without bound),
    never less than a division-tiered floor."""
    # v5.3.1: 100% (was 97%) of the typical wage + staff bill — the 3% gap
    # bled every average club ~£0.8m a season over a 30-season run.
    return int(max(funding_floor(median_weekly_bill, division), median_weekly_bill - weekly_gate_average))


def club_central_funding(division_amount: int, club_weekly_costs: float, median_weekly_bill: float,
                         division: int) -> int:
    """v5.3.1: one club's share. The distribution never exceeds what the
    club actually spends on wages and staff (above the tier floor) — a
    30-season run showed a club with a run-down, cheap squad banking the
    whole division-median payment every week (+£10m a season, forever)."""
    return int(min(division_amount, max(club_weekly_costs, funding_floor(median_weekly_bill, division))))


def gate_factor(division: int) -> float:
    return GATE_DIVISION_FACTOR.get(int(division or 5), 0.3)


#: v5.3.1: an AI club's comfortable cash reserve by division. Above it the
#: board reinvests part of the surplus each week (ground, facilities,
#: community) — without a sink, lower-tier clubs banked their gate profit
#: for decades (avg £40-57m in Division 3-5 after 30 seasons).
AI_CASH_RESERVE = {1: 30_000_000, 2: 15_000_000, 3: 8_000_000, 4: 5_000_000, 5: 3_000_000}
AI_SURPLUS_REINVEST_RATE = 0.03


def ai_weekly_reinvestment(cash: float, division: int) -> int:
    reserve = AI_CASH_RESERVE.get(int(division or 5), 3_000_000)
    return int(max(0.0, cash - reserve) * AI_SURPLUS_REINVEST_RATE)


# ---------------------------------------------------------------------------
# v5.3.1: sponsorship, facility upkeep and scouting costs
# ---------------------------------------------------------------------------

#: Monthly value of a main sponsorship deal by division before modifiers —
#: a top-flight shirt deal is worth roughly ten times a Division 5 one.
SPONSOR_MONTHLY_BASE = {1: 900_000, 2: 500_000, 3: 260_000, 4: 140_000, 5: 80_000}

SPONSOR_NAMES = (
    "Boundary Bank", "Greenline Financial", "Crease Motors", "Long Room Insurance", "Seamline Energy",
    "Third Man Telecom", "Fine Leg Foods", "Maiden Over Airways", "Willow & Stump Brewery", "Gully Logistics",
    "Cover Drive Software", "Silly Point Media", "Hat-Trick Hotels", "Square Cut Construction",
    "Nightwatch Security", "Yorker Sportswear", "Duckworth Ales", "Pavilion Property Group",
)


def sponsorship_monthly(division: int, commercial_level: int = 1, fan_morale: int = 50,
                        finish_ratio: float = 0.5) -> int:
    """A season's sponsorship value per month. ``finish_ratio`` is last
    season's league finish (0 = champions, 1 = bottom)."""
    base = SPONSOR_MONTHLY_BASE.get(int(division or 5), 80_000)
    commercial = 0.9 + 0.06 * max(1, min(5, int(commercial_level or 1)))
    fans = 0.85 + max(0, min(100, int(fan_morale or 50))) / 333
    success = 1.1 - 0.2 * max(0.0, min(1.0, float(finish_ratio)))
    return int(round(base * commercial * fans * success / 1_000) * 1_000)


def sponsorship_weekly(monthly_value: float) -> int:
    return int(monthly_value * 12 / 52)


#: Weekly running cost of ONE facility at each level (ground, training,
#: medical, academy, commercial operation).
FACILITY_UPKEEP_WEEKLY = {1: 3_000, 2: 7_000, 3: 13_000, 4: 22_000, 5: 34_000}


def facility_upkeep_weekly(*levels: int) -> int:
    return int(sum(FACILITY_UPKEEP_WEEKLY.get(max(1, min(5, int(level or 1))), 3_000) for level in levels))


#: Travel and expenses for each active scouting assignment, per week.
SCOUTING_ASSIGNMENT_WEEKLY = 4_000
