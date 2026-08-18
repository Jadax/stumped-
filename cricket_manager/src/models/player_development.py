"""Unified player age-curve and retirement story generation.

This module provides a single, consistent age curve used across training,
post-match development, and retirement logic.  The curve models a realistic
cricket career arc: rapid rise through the teenage years, peak in the late
20s, gradual decline through the 30s, and steep drop-off in the late 30s.

Pure functions only — no database or pygame dependencies.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Age curve
# ---------------------------------------------------------------------------

def age_curve(age: int) -> float:
    """Return a 0.0–1.0 multiplier reflecting a player's physical/mental
    capability at *age*, modelled as a smooth bell curve.

    The curve peaks at 1.0 around ages 26–28 and decays symmetrically
    but more steeply on the decline side (cricket careers end earlier
    than most sports due to the technical/physical demands).

    Typical values:
        16 → 0.55   20 → 0.80   25 → 0.98   27 → 1.00
        30 → 0.96   35 → 0.74   40 → 0.45   45 → 0.20
    """
    if age <= 0:
        return 0.0
    peak = 27.0
    if age <= peak:
        sigma = 9.0
    else:
        sigma = 6.5
    raw = math.exp(-0.5 * ((age - peak) / sigma) ** 2)
    return max(0.10, min(1.0, raw))


def training_age_factor(age: int) -> float:
    """Age multiplier for training stat gains.

    Young players develop faster (higher ceiling), prime-age players
    develop at baseline, veterans develop slowly, and past-35 players
    barely improve at all.

    Replaces the ad-hoc age_factor tables in training.py and
    apply_daily_training.
    """
    if age < 18:
        return 1.40
    if age < 21:
        return 1.28
    if age < 29:
        return 1.00
    if age < 33:
        return 0.72
    if age < 37:
        return 0.42
    return 0.25


def post_match_delta(age: int, potential: int, overall: int) -> float:
    """Return the overall-rating change after a match.

    Players under 30 with room to grow get a small positive delta.
    Players over 34 decline each match at an accelerating rate.
    Players in between are roughly stable.

    Returns a float to be rounded and applied.
    """
    if age <= 30 and overall < potential:
        room = potential - overall
        return min(0.5, max(0.0, room * 0.012))
    if age > 34:
        decline_rate = {35: 0.06, 36: 0.09, 37: 0.12, 38: 0.16,
                        39: 0.20, 40: 0.25}.get(age, min(0.35, (age - 34) * 0.07))
        return -min(0.5, decline_rate)
    return 0.0


# ---------------------------------------------------------------------------
# Retirement probability
# ---------------------------------------------------------------------------

def retirement_probability(age: int, overall: int) -> float:
    """Return a 0.0–1.0 probability that a player retires this off-season.

    Combines a smooth age-based retirement curve with an overall-rating
    modifier for players over 35: those whose ability has declined
    significantly are more likely to retire earlier.

    Replaces the ad-hoc _retirement_probability in competition.py.
    """
    if age < 33:
        base = 0.0
    elif age >= 45:
        base = 0.97
    else:
        base = min(0.95, ((age - 32) / 12) ** 1.6)

    # Only apply the overall modifier for players old enough to be
    # genuinely declining (not young lower-division players).
    if age >= 35:
        if overall < 25:
            base = min(0.95, base + 0.18)
        elif overall < 40:
            base = min(0.95, base + 0.10)
        elif overall < 55:
            base = min(0.95, base + 0.04)

    return min(0.97, base)


# ---------------------------------------------------------------------------
# Retirement stories
# ---------------------------------------------------------------------------

def generate_retirement_message(player: Mapping[str, Any], career: Mapping[str, Any] | None = None) -> str:
    """Generate a rich, personalised retirement inbox message.

    *player* is a dict with at least: name, age, role, overall, nationality.
    *career* is an optional dict with career stats: matches, runs, wickets,
    hundreds, fifties, best_score, best_bowling, average, etc.
    """
    name = player.get("name", "The player")
    age = player.get("age", 35)
    role = player.get("role", "All-Rounder")
    overall = player.get("overall", 50)

    lines: list[str] = []

    # Opening line
    if age >= 40:
        lines.append(f"At {age}, {name} has finally decided to hang up the boots after a remarkable career.")
    elif age >= 37:
        lines.append(f"{name}, aged {age}, has announced his retirement from professional cricket.")
    elif overall < 35:
        lines.append(f"With his form declining, {name} has decided to step away from the game at {age}.")
    else:
        lines.append(f"{name} has announced his retirement at the age of {age}.")

    # Career summary
    if career:
        matches = career.get("matches", 0)
        runs = career.get("runs", 0)
        wickets = career.get("wickets", 0)
        hundreds = career.get("hundreds", 0)
        fifties = career.get("fifties", 0)
        best_score = career.get("best_score")
        best_bowling = career.get("best_bowling")

        if role == "Batsman":
            if matches > 50:
                lines.append(f"Over {matches} matches, he scored {runs:,} runs")
                extras = []
                if hundreds: extras.append(f"{hundreds} centuries")
                if fifties: extras.append(f"{fifties} half-centuries")
                if extras:
                    lines[-1] += f" including {', '.join(extras)}."
                else:
                    lines[-1] += "."
            if best_score:
                lines.append(f"His career-best of {best_score} will live long in the memory.")
        elif role == "Bowler":
            if matches > 50:
                lines.append(f"In {matches} matches he took {wickets} wickets.")
            if best_bowling:
                lines.append(f"His best bowling figures of {best_bowling} were a highlight.")
        else:
            parts = []
            if runs > 200: parts.append(f"{runs:,} runs")
            if wickets > 20: parts.append(f"{wickets} wickets")
            if parts:
                lines.append(f"Over {matches} matches, he contributed {', '.join(parts)} to the side.")

    # Legacy line
    if overall >= 85:
        lines.append(f"A true great of the game, {name} will be remembered as one of the finest in his era.")
    elif overall >= 70:
        lines.append(f"{name} was a dependable performer who gave his all every time he took the field.")
    else:
        lines.append(f"{name} served the club with dedication throughout his career.")

    return " ".join(lines)


def generate_release_message(player: Mapping[str, Any]) -> str:
    """Generate a message for a player released due to very low ability."""
    name = player.get("name", "The player")
    return (f"{name} has been released from the squad. With his overall ability "
            f"falling below the minimum threshold, the club has decided not to "
            f"renew his contract.")


def generate_young_retirement_message(player: Mapping[str, Any]) -> str:
    """Generate a message for a player retiring unusually early (injury/personal)."""
    name = player.get("name", "The player")
    age = player.get("age", 30)
    reasons = [
        f"{name} has announced his retirement at the young age of {age}, citing personal reasons.",
        f"In a surprise announcement, {name} has decided to retire at just {age}.",
        f"{name} has been forced to retire at {age} due to persistent injury concerns.",
    ]
    # Use the player id as a simple hash to pick a consistent reason
    idx = hash(name) % len(reasons)
    return reasons[idx]
