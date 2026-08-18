"""Fan sentiment model — pure functions for computing fan morale shifts.

Fan morale is an integer 0–100 (default 50) stored on each team. It
rises and falls with results, streaks, and trophy wins, and feeds back
into ticket demand and gate receipts.

All functions are pure (no DB access) — callers wire persistence.
"""
from __future__ import annotations

import random as _rng

# ── Sentiment deltas ────────────────────────────────────────────────

def win_delta(is_home: bool, margin_comfortable: bool, is_derby: bool) -> int:
    """Return the fan morale delta for a match win."""
    base = 6 if is_home else 4
    if margin_comfortable:
        base += 2
    if is_derby:
        base += 3
    return base


def loss_delta(is_home: bool, heavy_defeat: bool, is_derby: bool) -> int:
    """Return the (negative) fan morale delta for a match loss."""
    base = -5 if is_home else -3
    if heavy_defeat:
        base -= 2
    if is_derby:
        base -= 3
    return base


def draw_delta() -> int:
    """Small positive for a draw — fans appreciate resilience."""
    return 1


def streak_bonus(consecutive_wins: int) -> int:
    """Extra fan morale for a winning streak (3+ wins). Returns 0 below 3."""
    if consecutive_wins < 3:
        return 0
    # 3 wins = +3, 4 = +4, 5+ = +5 (capped)
    return min(consecutive_wins, 5)


def streak_penalty(consecutive_losses: int) -> int:
    """Extra fan morale hit for a losing streak (3+ losses). Returns 0 below 3."""
    if consecutive_losses < 3:
        return 0
    return -min(consecutive_losses, 6)


def trophy_delta() -> int:
    """Fan morale boost for winning a trophy."""
    return 15


def promotion_delta() -> int:
    """Fan morale boost for promotion."""
    return 10


def relegation_delta() -> int:
    """Fan morale hit for relegation."""
    return -12


def title_delta() -> int:
    """Fan morale boost for winning the league title (on top of trophy_delta)."""
    return 10


def clamp_morale(value: int) -> int:
    """Clamp fan morale to 0–100."""
    return max(0, min(100, value))


# ── Demand modifier ─────────────────────────────────────────────────

def demand_modifier(fan_morale: int) -> float:
    """Return a float modifier to the gate demand formula.

    At 50 (default) → +0.000 (neutral).
    At 100 → +0.025 (sell-out more often).
    At 0 → −0.025 (empty seats).
    """
    return (fan_morale - 50) / 2000.0


# ── Label / description ────────────────────────────────────────────

_LABELS = [
    (90, "Ecstatic"),
    (75, "Happy"),
    (60, "Content"),
    (40, "Restless"),
    (25, "Unhappy"),
    (0, "Furious"),
]


def morale_label(fan_morale: int) -> str:
    """Human-readable label for the current fan morale level."""
    for threshold, label in _LABELS:
        if fan_morale >= threshold:
            return label
    return "Furious"


def morale_description(fan_morale: int, team_name: str) -> str:
    """Short prose description of fan sentiment, suitable for an inbox
    or UI tooltip."""
    label = morale_label(fan_morale)
    if fan_morale >= 80:
        return f"The {team_name} faithful are {label.lower()} — the stands are alive with energy."
    if fan_morale >= 60:
        return f"Fans are generally {label.lower()}. A few more wins would really get them going."
    if fan_morale >= 40:
        return f"The mood among supporters is {label.lower()}. Results need to improve."
    if fan_morale >= 20:
        return f"Fans are {label.lower()} — boos echo around the ground after recent performances."
    return f"The {team_name} fanbase is {label.lower()}. Attendance is dropping and patience has run out."
