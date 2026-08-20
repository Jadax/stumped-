"""Squad cohesion model — pure functions for computing team bond dynamics.

Squad cohesion is an integer 0–100 (default 50) stored on each team.
It rises when the same XI is fielded and the team wins, and falls when
the manager rotates heavily or the team loses. A small modifier feeds
into the match engine's rating calculations.

All functions are pure (no DB access) — callers wire persistence.
"""
from __future__ import annotations

import random as _rng

# ── XI consistency ──────────────────────────────────────────────────

def consistency_bonus(repeated: int) -> int:
    """Extra cohesion from fielding the same core XI.

    *repeated* is the number of players from the last match's XI who
    also start this match (0–11).

    Returns 0–5: 0 for fewer than 6 repeats, scaling up to +5 for a
    completely unchanged XI.
    """
    if repeated < 6:
        return 0
    # 6→1, 7→2, 8→3, 9→4, 10–11→5
    return min(repeated - 5, 5)


def rotation_penalty(new_players: int) -> int:
    """Cohesion hit for heavy rotation.

    *new_players* is how many different faces are in this XI compared
    to the last match (0–11).

    Returns 0 to −4: 0 for 3 or fewer new faces, up to −4 for 7+.
    """
    if new_players <= 3:
        return 0
    return -min(new_players - 3, 4)


# ── Match result ────────────────────────────────────────────────────

def win_delta(is_home: bool, comfortable: bool) -> int:
    """Cohesion boost for a match win."""
    base = 4 if is_home else 3
    if comfortable:
        base += 1
    return base


def loss_delta(is_home: bool, heavy: bool) -> int:
    """Cohesion hit for a match loss."""
    base = -3 if is_home else -2
    if heavy:
        base -= 1
    return base


def draw_delta() -> int:
    """Small positive for a draw."""
    return 1


# ── Season events ───────────────────────────────────────────────────

def promotion_delta() -> int:
    return 5


def relegation_delta() -> int:
    return -8


def trophy_delta() -> int:
    return 8


# ── Match engine modifier ──────────────────────────────────────────

def match_modifier(cohesion: int) -> float:
    """Return a float added to the team's composite rating in the engine.

    At 50 (default) → +0.0 (neutral).
    At 100 → +1.5 (familiar, well-oiled unit).
    At 0 → −1.5 (disjointed, strangers).
    """
    return (cohesion - 50) * 0.03


# ── Clamp / label ───────────────────────────────────────────────────

def clamp_cohesion(value: int) -> int:
    return max(0, min(100, value))


_LABELS = [
    (90, "United"),
    (75, "Solid"),
    (60, "Settled"),
    (40, "Uncertain"),
    (25, "Fragmented"),
    (0, "Toxic"),
]


def cohesion_label(cohesion: int) -> str:
    for threshold, label in _LABELS:
        if cohesion >= threshold:
            return label
    return "Toxic"


def cohesion_description(cohesion: int, team_name: str) -> str:
    label = cohesion_label(cohesion)
    if cohesion >= 80:
        return f"The {team_name} squad is {label.lower()} — players know each other's games inside out."
    if cohesion >= 60:
        return f"Cohesion is {label.lower()}. The squad is gelling nicely."
    if cohesion >= 40:
        return f"Things feel {label.lower()} among the squad. New faces are still finding their feet."
    if cohesion >= 20:
        return f"The dressing room is {label.lower()} — cliques are forming and performances are suffering."
    return f"The {team_name} squad is {label.lower()}. The manager faces a crisis of unity."
