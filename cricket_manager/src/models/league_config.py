"""League configuration — defines rules for each domestic competition
including foreign player limits, format, and schedule.
"""
from __future__ import annotations

# Foreign player limits per division
# 0 = no foreign players (domestic only), N = max N foreign players
FOREIGN_PLAYER_LIMITS = {
    1: 0,   # County Championship — no foreign players
    2: 2,   # Sheffield Shield — 2 overseas players
    3: 4,   # IPL style — 4 overseas players
    4: 3,   # Big Bash/PSL — 3 overseas players
    5: 4,   # IPL/CPL — 4 overseas players
}

# League formats per division
LEAGUE_FORMATS = {
    1: "Test",    # First-class cricket
    2: "ODI",     # One-day cricket
    3: "T20",     # T20 cricket
    4: "T20",     # T20 cricket
    5: "T20",     # T20 cricket
}

# League names per division
LEAGUE_NAMES = {
    1: "County Championship",
    2: "Sheffield Shield",
    3: "Ranji Trophy",
    4: "Big Bash League",
    5: "Indian Premier League",
}

# Countries per division (which countries' teams are in each division)
DIVISION_COUNTRIES = {
    1: ["English"],
    2: ["Australian", "Indian"],
    3: ["Indian", "Pakistani", "Sri Lankan", "Bangladeshi", "Zimbabwean"],
    4: ["Australian", "Pakistani", "West Indian"],
    5: ["Indian", "Australian"],
}


def get_foreign_player_limit(division: int) -> int:
    """Return the maximum number of foreign players allowed in a division."""
    return FOREIGN_PLAYER_LIMITS.get(division, 0)


def get_league_format(division: int) -> str:
    """Return the match format for a division."""
    return LEAGUE_FORMATS.get(division, "T20")


def get_league_name(division: int) -> str:
    """Return the competition name for a division."""
    return LEAGUE_NAMES.get(division, f"Division {division}")


def get_division_countries(division: int) -> list[str]:
    """Return the list of nationalities represented in a division."""
    return DIVISION_COUNTRIES.get(division, [])
