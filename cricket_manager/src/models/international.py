"""International cricket — the scoped first slice of "deeper league/
international structure" (the third user-directed roadmap priority,
sequenced last for being the largest/most disruptive).

Deliberately NOT a separate national-team career mode (manager creation,
a parallel calendar, user-controlled squad selection) — that's a much
larger redesign than fits one pass. This slice adds a real, periodic
in-season event within the existing club career: once a season, the
best 11 eligible players of two randomly-chosen represented nations
(drawn from every club in the game world, not just the user's) contest
a 3-match T20I series using the same match_engine.Match the rest of the
game already trusts. A user's own player being selected is a genuine
event — an inbox message, an "International" player_records entry
(a context the schema already anticipated), and a morale boost.

Both clients share this module so neither invents its own nation list
or selection rule — mirrors src/models/morale.py and squad_metrics.py.
"""
from __future__ import annotations

# The seven nationalities every club in the generated world draws from
# (see database.py's TEAM_DEFINITIONS) — not an exhaustive real-world
# list, just what's actually represented in this game's data.
INTERNATIONAL_NATIONALITIES = [
    "English", "Australian", "Indian", "Pakistani",
    "South African", "New Zealander", "West Indian",
]

NATIONAL_TEAM_NAMES = {
    "English": "England", "Australian": "Australia", "Indian": "India",
    "Pakistani": "Pakistan", "South African": "South Africa",
    "New Zealander": "New Zealand", "West Indian": "West Indies",
}

# Negative, stable synthetic ids so national "teams" never collide with
# a real club id (club ids are positive autoincrement).
NATIONAL_TEAM_IDS = {nationality: -(index + 1) for index, nationality in enumerate(INTERNATIONAL_NATIONALITIES)}

INTERNATIONAL_SERIES_LENGTH = 3
INTERNATIONAL_CALLUP_MORALE_BONUS = 10
# A well-resourced "world XI" quality level for match_engine.py's
# pitch-wear/injury calculations, which read these off the team dict —
# international sides get the best facilities in the game.
NATIONAL_TEAM_FACILITIES = {"grounds_level": 3, "medical_level": 3, "physio_rating": 15}


def national_team(nationality: str) -> dict:
    """The synthetic "team" dict match_engine.Match expects for a nation."""
    return {"id": NATIONAL_TEAM_IDS[nationality], "name": NATIONAL_TEAM_NAMES[nationality],
           **NATIONAL_TEAM_FACILITIES}
