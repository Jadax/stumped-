"""Per-nation domestic competition registry (v4.56.0).

Gives every league-playing nation its own domestic structure — a First Class/
Test league, a 50-over (List A) competition, a T20 competition, and (where a
real competition has one) a knockout cup or playoff stage. This is the
"same league structure as Cricket Captain" feature: instead of one global
5-division pyramid mixing nations, each nation plays in competitions built
from its own teams, scoped by ``country_id``.

Real-life competition names and approximate real sizes per nation are used
(County Championship, Sheffield Shield, Ranji Trophy, Quaid-e-Azam, CSA
4-Day, Plunket Shield, National Super League, National Cricket League, West
Indies Championship, Logan Cup; and their 50-over / T20 counterparts). The
engine groups each nation's existing generated teams (via ``teams.country_id``)
into that nation's competitions, so no new teams are required and existing
saves keep loading.

This module is intentionally data + helpers only — the season
generation lives in CompetitionEngine (see competition.py).
"""
from __future__ import annotations

# country_id slug (as stored on teams.country_id) -> domestic competitions.
# each competition:
#   name        display name (also the competitions.name row)
#   format      Test / ODI / T20
#   kind        "league" (round-robin table) or "cup" (knockout)
#   divisions   how many divisions the league is split into (1 = single table)
#   promotion   places up from the *lowest* division each season
#   relegation  places down from every division above the lowest
#   fixtures_per_team  approx round-robin size (double round robin if
#                      2 * (teams - 1) would be too heavy we still do it;
#                      engine clamps by available teams)
#   knockout    True if the competition finishes with a playoff/knockout
#               stage rather than just a table (50-over / T20 style)
NATION_COMPETITIONS: dict[str, list[dict]] = {
    "england": [
        {"name": "County Championship", "format": "Test", "kind": "league", "divisions": 2,
         "promotion": 2, "relegation": 2},
        {"name": "One-Day Cup", "format": "ODI", "kind": "cup", "divisions": 1, "knockout": True},
        {"name": "T20 Blast", "format": "T20", "kind": "league", "divisions": 2,
         "promotion": 2, "relegation": 2, "playoffs": True},
    ],
    "australia": [
        {"name": "Sheffield Shield", "format": "Test", "kind": "league", "divisions": 1, "final": True},
        {"name": "Marsh Cup", "format": "ODI", "kind": "cup", "divisions": 1, "final": True},
        {"name": "Big Bash League", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "india": [
        {"name": "Ranji Trophy", "format": "Test", "kind": "league", "divisions": 2,
         "promotion": 2, "relegation": 2, "knockout": True},
        {"name": "Vijay Hazare Trophy", "format": "ODI", "kind": "cup", "divisions": 1, "knockout": True},
        {"name": "Syed Mushtaq Ali Trophy", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "pakistan": [
        {"name": "Quaid-e-Azam Trophy", "format": "Test", "kind": "league", "divisions": 1, "final": True},
        {"name": "Pakistan Cup", "format": "ODI", "kind": "cup", "divisions": 1, "final": True},
        {"name": "National T20 Cup", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "south_africa": [
        {"name": "CSA 4-Day Series", "format": "Test", "kind": "league", "divisions": 1},
        {"name": "CSA One-Day Cup", "format": "ODI", "kind": "cup", "divisions": 1, "final": True},
        {"name": "CSA T20 Challenge", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "new_zealand": [
        {"name": "Plunket Shield", "format": "Test", "kind": "league", "divisions": 1},
        {"name": "Ford Trophy", "format": "ODI", "kind": "cup", "divisions": 1, "final": True},
        {"name": "Super Smash", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "sri_lanka": [
        {"name": "National Super League", "format": "Test", "kind": "league", "divisions": 1},
        {"name": "Lanka T20 League", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "bangladesh": [
        {"name": "National Cricket League", "format": "Test", "kind": "league", "divisions": 2,
         "promotion": 1, "relegation": 1},
        {"name": "Bangladesh Premier League", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "west_indies": [
        {"name": "West Indies Championship", "format": "Test", "kind": "league", "divisions": 1},
        {"name": "Super50 Cup", "format": "ODI", "kind": "cup", "divisions": 1, "knockout": True},
        {"name": "Caribbean Premier League", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
    "zimbabwe": [
        {"name": "Logan Cup", "format": "Test", "kind": "league", "divisions": 1},
        {"name": "Pro50 Championship", "format": "ODI", "kind": "cup", "divisions": 1, "final": True},
        {"name": "Zimbabwe T20", "format": "T20", "kind": "league", "divisions": 1, "playoffs": True},
    ],
}

# Optional franchise leagues (v4.56.0+): separate T20 competitions whose
# squads are drawn from the same nation's player pool (shared squads — the
# players keep their domestic club; the franchise XI is selected from the
# same talent pool). Real leagues: Indian Premier League, Big Bash League,
# Pakistan Super League, Caribbean Premier League, Bangladesh Premier League,
# SA20, Lanka Premier League.
FRANCHISE_LEAGUES: dict[str, dict] = {
    "india": {"name": "Indian Premier League", "format": "T20", "teams": 10},
    "australia": {"name": "Big Bash League", "format": "T20", "teams": 8},  # already a domestic league above; franchise roster variant
    "pakistan": {"name": "Pakistan Super League", "format": "T20", "teams": 6},
    "west_indies": {"name": "Caribbean Premier League", "format": "T20", "teams": 6},
    "bangladesh": {"name": "Bangladesh Premier League", "format": "T20", "teams": 7},
    "south_africa": {"name": "SA20", "format": "T20", "teams": 6},
    "sri_lanka": {"name": "Lanka Premier League", "format": "T20", "teams": 5},
}


def competitions_for_country(country_id: str) -> list[dict]:
    """The domestic competitions for a given country_id slug."""
    return NATION_COMPETITIONS.get(country_id, [])


def franchise_for_country(country_id: str) -> dict | None:
    """The franchise league definition for a country, if one applies."""
    return FRANCHISE_LEAGUES.get(country_id)
