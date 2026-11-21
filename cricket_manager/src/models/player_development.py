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

#: v5.3.1: annual chance a professional calls time, by age. Modelled on
#: real first-class careers: a handful stop at 30-32 (body, family, a job
#: outside the game), most finish between 33 and 37, and almost nobody is
#: still playing at 40. The old curve gave only 11% at 35 and 29% at 38, so
#: the world filled with 36-37-year-olds.
RETIREMENT_HAZARD = {30: 0.02, 31: 0.03, 32: 0.08, 33: 0.13, 34: 0.20, 35: 0.30,
                     36: 0.42, 37: 0.55, 38: 0.68, 39: 0.80, 40: 0.90}


def is_pace_bowler(role: str, bowling: dict | None) -> bool:
    """Seamers and quicks (pace >= 55) — the bodies that break down first."""
    if role not in ("Bowler", "All-Rounder") or not bowling:
        return False
    return float(bowling.get("pace", 0) or 0) >= 55


def decline_onset(role: str, pace_bowler: bool = False) -> int:
    """Age at which a player's physical game starts to go: fast bowlers
    first (pace and recovery), keepers and batters a little later
    (reflexes, eyesight), spinners last (craft outlasts the body)."""
    if pace_bowler:
        return 31
    if role == "Bowler":
        return 34
    return 33


def annual_decline(age: int, role: str, potential: int, pace_bowler: bool = False) -> float:
    """Overall points lost in a year of decline — slow at first, then
    accelerating, and gentler for genuinely class players."""
    years = age - decline_onset(role, pace_bowler) + 1
    if years <= 0:
        return 0.0
    base = 0.8 + 0.55 * (years - 1) + 0.08 * (years - 1) ** 2
    talent = 0.8 if potential >= 85 else 0.9 if potential >= 75 else 1.0
    return base * talent


def retirement_probability(age: int, overall: int, role: str = "Batsman", pace_bowler: bool = False,
                           club_level: float | None = None, major_injury: bool = False) -> float:
    """Return a 0.0-1.0 probability that a player retires this off-season.

    Age is the main driver; quick bowlers go sooner, stars carry on longer,
    and a player who has lost his place (well below his club's level) or is
    coming back from a major injury is more likely to call it a day.
    """
    if age < 30:
        return 0.0
    if age > 40:
        return 0.97
    probability = RETIREMENT_HAZARD.get(age, 0.0)
    if pace_bowler and age >= 31:
        probability += 0.05
    if overall >= 80:
        probability *= 0.7
    elif overall < 45:
        probability += 0.08
    if club_level is not None and overall < club_level - 8:
        probability += 0.07
    if major_injury and age >= 32:
        probability += 0.12
    return min(0.97, probability)


def post_career_role(role: str, overall: int, mental: dict | None, rng) -> str | None:
    """What a retiring player does next, if he stays in the game.

    Natural leaders with experience become head coaches (the club's
    manager in cricket), specialists coach their own discipline, sharp
    readers of the game scout, and the fittest become fitness coaches. Most
    leave the professional game altogether."""
    mental = mental or {}
    leadership = float(mental.get("leadership", 50) or 50)
    experience = float(mental.get("experience", 50) or 50)
    chance = 0.08 + 0.25 * leadership / 100 + 0.15 * experience / 100 + (0.08 if overall >= 75 else 0.0)
    if rng.random() >= chance:
        return None
    if leadership >= 70 and experience >= 65 and rng.random() < 0.45:
        return "Head Coach"
    roll = rng.random()
    if roll < 0.2:
        return "Scout"
    if roll < 0.28:
        return "Fitness Coach"
    return {"Batsman": "Batting Coach", "Bowler": "Bowling Coach", "Wicketkeeper": "Fielding Coach"}.get(
        role, rng.choice(["Batting Coach", "Bowling Coach"]))


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
