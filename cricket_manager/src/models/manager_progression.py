"""Manager progression (v4.58.0): a real reputation ladder the manager
THEMSELVES grows, separate from src/models/career.py's manager_reputation()
(which is stateless — recomputed fresh each call from win/trophy history,
nothing persists about the manager between sessions beyond what the club
already accumulates). Competitive research (docs/COMPETITIVE_RESEARCH.md,
gap #4) flagged this as the single biggest hook a competitor (Cricket
Management Tycoon) has that Stumped! didn't.

XP earned from meaningful actions (match wins, season trophies, board
objectives met, engaging with team talks/press conferences) grants a level;
each level past 1 banks one perk point spendable on a small perk tree that
modifies existing formulas at their exact source (team talks, press
conferences, youth intake, pitch-change delay) rather than adding new
systems. Pure data + helpers only — persistence lives in database.py
(mirrors nations_config.py's split, see competition.py/database.py v4.56.0).
"""
from __future__ import annotations

XP_PER_LEVEL = 100  # a flat curve for v1 — a diminishing-returns curve is a
                    # tuning follow-up, not core to the mechanic.

PERKS: list[dict] = [
    {"id": "motivational_speaker", "name": "Motivational Speaker", "tier": 1, "min_level": 2,
     "description": "Team talks swing squad morale further, for better or worse."},
    {"id": "media_trained", "name": "Media Trained", "tier": 1, "min_level": 2,
     "description": "A Critical press answer's downside is softened."},
    {"id": "eye_for_talent", "name": "Eye for Talent", "tier": 1, "min_level": 3,
     "description": "Youth intake finds one extra academy prospect each season."},
    {"id": "groundsman_friend", "name": "Groundsman's Friend", "tier": 1, "min_level": 3,
     "description": "A pitch change takes effect a day sooner."},
    {"id": "calm_head", "name": "Calm Head", "tier": 2, "min_level": 5,
     "description": "Press conference confidence swings lean more positive."},
    {"id": "squad_harmony", "name": "Squad Harmony", "tier": 2, "min_level": 6,
     "description": "An Aggressive team talk can no longer badly backfire."},
]

PERKS_BY_ID: dict[str, dict] = {perk["id"]: perk for perk in PERKS}


def level_for_xp(xp: int) -> int:
    """1-indexed manager level; XP_PER_LEVEL XP per level, no cap."""
    return max(1, xp // XP_PER_LEVEL + 1)


def points_available(xp: int, unlocked_count: int) -> int:
    """Perk points banked (one per level past 1) minus however many have
    already been spent — each perk costs exactly one point."""
    return max(0, level_for_xp(xp) - 1 - unlocked_count)


def can_unlock(perk_id: str, xp: int, unlocked: set[str]) -> tuple[bool, str]:
    """Whether a perk can be unlocked right now, and a reason if not."""
    perk = PERKS_BY_ID.get(perk_id)
    if perk is None:
        return False, "Unknown perk."
    if perk_id in unlocked:
        return False, "Already unlocked."
    if level_for_xp(xp) < perk["min_level"]:
        return False, f"Requires manager level {perk['min_level']}."
    if points_available(xp, len(unlocked)) < 1:
        return False, "No perk points available."
    return True, ""
