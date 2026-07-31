"""International cricket — bilateral tours, ICC tournaments, and
player call-ups. Expanded from v0.72.0's minimal single-window system
to support named tours (Ashes, Border-Gavaskar, etc.), multiple windows
per season, and player availability tracking during international duty.
"""
from __future__ import annotations

# The nationalities represented in this game's generated world
# (see database.py's TEAM_DEFINITIONS).
INTERNATIONAL_NATIONALITIES = [
    "English", "Australian", "Indian", "Pakistani",
    "South African", "New Zealander", "West Indian",
    "Sri Lankan", "Bangladeshi", "Zimbabwean",
]

NATIONAL_TEAM_NAMES = {
    "English": "England", "Australian": "Australia", "Indian": "India",
    "Pakistani": "Pakistan", "South African": "South Africa",
    "New Zealander": "New Zealand", "West Indian": "West Indies",
    "Sri Lankan": "Sri Lanka", "Bangladeshi": "Bangladesh", "Zimbabwean": "Zimbabwe",
}

# Negative, stable synthetic ids so national "teams" never collide with
# a real club id (club ids are positive autoincrement).
NATIONAL_TEAM_IDS = {nationality: -(index + 1) for index, nationality in enumerate(INTERNATIONAL_NATIONALITIES)}

# Reverse lookup (id -> display name) — used anywhere that only has a raw
# team_id off a matches/league_standings row and needs a human name without
# a `teams` table join, which returns nothing for a negative national id.
NATIONAL_TEAM_NAMES_BY_ID = {NATIONAL_TEAM_IDS[nat]: name for nat, name in NATIONAL_TEAM_NAMES.items()}

INTERNATIONAL_SERIES_LENGTH = 3
INTERNATIONAL_CALLUP_MORALE_BONUS = 10
# A well-resourced "world XI" quality level for match_engine.py's
# pitch-wear/injury calculations, which read these off the team dict —
# international sides get the best facilities in the game.
NATIONAL_TEAM_FACILITIES = {"grounds_level": 3, "medical_level": 3, "physio_rating": 15}

# Named bilateral tours — each is a specific home/away matchup with a
# name, scheduled month, and series length. These run every year.
BILATERAL_TOURS = [
    {"name": "The Ashes", "home": "English", "away": "Australian", "month": 11, "length": 5, "format": "Test"},
    {"name": "Border-Gavaskar Trophy", "home": "Australian", "away": "Indian", "month": 12, "length": 4, "format": "Test"},
    {"name": "Freedom Trophy", "home": "South African", "away": "Indian", "month": 1, "length": 3, "format": "Test"},
    {"name": "Frank Worrell Trophy", "home": "West Indian", "away": "Australian", "month": 2, "length": 3, "format": "Test"},
    {"name": "Chappell-Hadlee Trophy", "home": "New Zealander", "away": "Australian", "month": 2, "length": 3, "format": "ODI"},
    {"name": "Deodhar Trophy", "home": "Indian", "away": "Bangladeshi", "month": 3, "length": 3, "format": "ODI"},
    {"name": "T20I Series", "home": "English", "away": "Indian", "month": 6, "length": 3, "format": "T20"},
    {"name": "T20I Series", "home": "South African", "away": "English", "month": 10, "length": 3, "format": "T20"},
]

# ICC tournament windows — run at specific months. Real group-stage shapes
# (v4.10.0 — previously "teams" was declared but never actually used to
# build a tournament; _run_international_window sampled N nations and then
# only ever played a single match between the first two, silently dropping
# every other nation and never actually running a group stage or knockout).
# Months are chosen to avoid colliding with any BILATERAL_TOURS start month
# (1, 2, 3, 6, 10, 11, 12 are taken) — 4, 8, 9 are free. A tournament's
# group stage plus knockout takes several real weeks, not one instant call,
# so competition.py also pauses bilateral tours while one is in progress.
ICC_TOURNAMENTS = [
    # All 10 nations, single round-robin group — this is exactly the real
    # 2023 ODI World Cup format (9 matches per team, top 4 to the knockout).
    {"name": "ICC World Cup", "month": 9, "format": "ODI", "team_count": 10,
     "group_count": 1, "advance_per_group": 4},
    # All 10 nations split into 2 groups of 5; top 2 from each (4 total)
    # advance — a scaled-down version of the real Super 12/Super 8 shape,
    # sized to this game's 10-nation world.
    {"name": "ICC T20 World Cup", "month": 4, "format": "T20", "team_count": 10,
     "group_count": 2, "advance_per_group": 2},
    # 8 of the 10 nations (the 2 lowest by current national-XI strength sit
    # out, mirroring real ODI-ranking-based qualification), 2 groups of 4.
    {"name": "ICC Champions Trophy", "month": 8, "format": "ODI", "team_count": 8,
     "group_count": 2, "advance_per_group": 2},
]


def national_team(nationality: str) -> dict:
    """The synthetic "team" dict match_engine.Match expects for a nation."""
    return {"id": NATIONAL_TEAM_IDS[nationality], "name": NATIONAL_TEAM_NAMES[nationality],
            **NATIONAL_TEAM_FACILITIES}


def get_tour_for_month(month: int) -> dict | None:
    """Return the bilateral tour scheduled for this month, or None."""
    for tour in BILATERAL_TOURS:
        if tour["month"] == month:
            return tour
    return None


def get_tournament_for_month(month: int) -> dict | None:
    """Return the ICC tournament scheduled for this month, or None."""
    for tournament in ICC_TOURNAMENTS:
        if tournament["month"] == month:
            return tournament
    return None
