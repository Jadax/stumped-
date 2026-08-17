"""Form streak detection — the narrative layer for hot/cold runs.

Reads a player's recent performance scores (from player_form_history)
and detects streaks that are worth surfacing as storylines. This module
is pure functions only; persistence lives in database.py (write_streak_event).
"""
from __future__ import annotations
from typing import Any

# A score of 70+ means a genuinely good match performance — batting 50+
# or taking 2+ wickets pushes the combined score above this threshold.
HOT_THRESHOLD = 70
# A score of 30 or below is a genuinely poor match — a duck with no
# wickets, or an expensive bowling spell with nothing to show for it.
COLD_THRESHOLD = 30
# Minimum consecutive matches to qualify as a "streak".
MIN_STREAK_LENGTH = 3


def detect_streak(recent_scores: list[float], format: str = "FC") -> dict[str, Any] | None:
    """Detect a hot or cold form streak from a list of recent performance
    scores (newest first, as returned by database.get_recent_performances).

    Returns None if no streak is detected, or a dict:
        {"type": "hot"/"cold", "length": int, "detail": str}

    ``format`` adjusts thresholds slightly: T20/T10/Hundred formats are
    higher-scoring so a hot streak is easier to reach but cold is harder.
    """
    if len(recent_scores) < MIN_STREAK_LENGTH:
        return None

    t20 = format in ("T20", "T10", "Hundred")
    hot_thresh = HOT_THRESHOLD - (5 if t20 else 0)
    cold_thresh = COLD_THRESHOLD + (3 if t20 else 0)

    hot_length = 0
    cold_length = 0

    for score in recent_scores:
        if score >= hot_thresh:
            if cold_length > 0:
                break
            hot_length += 1
        elif score <= cold_thresh:
            if hot_length > 0:
                break
            cold_length += 1
        else:
            break

    if hot_length >= MIN_STREAK_LENGTH:
        return {
            "type": "hot",
            "length": hot_length,
            "detail": f"{hot_length} consecutive strong performances",
        }
    if cold_length >= MIN_STREAK_LENGTH:
        return {
            "type": "cold",
            "length": cold_length,
            "detail": f"{cold_length} consecutive poor performances",
        }
    return None
