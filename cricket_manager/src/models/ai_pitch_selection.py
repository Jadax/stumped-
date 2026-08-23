"""AI pitch selection — pure functions for automated pitch choice.

AI clubs pick a pitch surface before each home match based on:
  - Their ground's pitch_affinity (pace / spin / balanced)
  - Their own squad strengths (batting depth vs bowling strength)
  - Opposition weaknesses (technique vs pace/spin gaps)

No DB access — callers pass in ground and squad data.
"""
from __future__ import annotations

import random as _rng
from typing import Any

PITCH_TYPES = ["Green", "Dry", "Dusty", "Flat", "Worn"]


def choose_ai_pitch(
    pitch_affinity: str,
    own_batting_avg: float,
    own_bowling_avg: float,
    opp_technique_vs_pace: float = 50.0,
    opp_technique_vs_spin: float = 50.0,
    rng: _rng.Random | None = None,
) -> str:
    """Pick a pitch type for an AI home team.

    Parameters
    ----------
    pitch_affinity : str
        The ground's pitch_affinity ('pace', 'spin', or 'balanced').
    own_batting_avg, own_bowling_avg : float
        Team averages — higher is better for batting, lower is better
        for bowling.
    opp_technique_vs_pace, opp_technique_vs_spin : float
        Opposition technique scores (0–100, lower = weaker).
    rng : random.Random, optional
        Seeded RNG for deterministic results.

    Returns
    -------
    str
        One of PITCH_TYPES.
    """
    r = rng or _rng.Random()

    scores: dict[str, float] = {}
    for pitch in PITCH_TYPES:
        scores[pitch] = _pitch_score(pitch, pitch_affinity, own_batting_avg,
                                     own_bowling_avg, opp_technique_vs_pace,
                                     opp_technique_vs_spin)

    # Pick the highest-scoring pitch, with a small random tiebreaker
    best_score = max(scores.values())
    candidates = [p for p, s in scores.items() if s == best_score]
    return r.choice(candidates)


def _pitch_score(
    pitch: str,
    pitch_affinity: str,
    own_batting_avg: float,
    own_bowling_avg: float,
    opp_pace: float,
    opp_spin: float,
) -> float:
    """Score a pitch type — higher means more favourable for the home side."""
    score = 0.0

    # Affinity alignment bonus
    if pitch_affinity == "pace" and pitch in ("Green", "Dry"):
        score += 4
    elif pitch_affinity == "spin" and pitch in ("Dusty", "Worn"):
        score += 4
    elif pitch_affinity == "balanced":
        score += 1  # slight neutral bonus

    # Exploit opposition weaknesses
    if pitch in ("Green", "Dry") and opp_pace < 45:
        score += 3  # weak against pace
    elif pitch in ("Dusty", "Worn") and opp_spin < 45:
        score += 3  # weak against spin

    # Flat pitch if our batting is strong relative to bowling
    if pitch == "Flat":
        batting_edge = own_batting_avg - own_bowling_avg
        if batting_edge > 10:
            score += 3
        elif batting_edge > 0:
            score += 1

    # Green/Worn favour bowling — good if our bowling is strong
    if pitch in ("Green", "Worn"):
        if own_bowling_avg < 30:
            score += 2

    # Dusty — risky but good if opponent is weak to spin AND our bowling
    # is decent
    if pitch == "Dusty":
        if opp_spin < 40 and own_bowling_avg < 35:
            score += 2

    return score


def describe_pitch_choice(pitch: str, reason: str | None = None) -> str:
    """Human-readable headline for a chosen pitch."""
    if reason:
        return f"{pitch} pitch selected — {reason}"
    return f"{pitch} pitch selected"
