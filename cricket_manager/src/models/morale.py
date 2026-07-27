"""Pure morale-event helpers shared by both clients (pygame's
ui/pre_match.py + ui/match_view.py, and the headless Godot IPC backend
in ipc_server.py) — mirrors src/models/squad_metrics.py's role as a
single source of truth so neither client invents its own formula.

Morale was previously a fixed random constant set once at player
generation: it genuinely affects match performance (match_engine.py),
AI team selection (ui/selection.py), and contract negotiation
(src/models/contracts.py), but nothing ever changed it. These are the
four events that now do: match results, being dropped from the XI after
playing last time, a signed contract renewal, and promotion/relegation.
"""
from __future__ import annotations
from typing import Sequence

WIN_MORALE_DELTA = 5
LOSS_MORALE_DELTA = -5
TIE_MORALE_DELTA = 1
CUP_STAKES_MULTIPLIER = 1.6
DROPPED_MORALE_PENALTY = -4
CONTRACT_SIGNED_MORALE_BONUS = 8
PROMOTION_MORALE_BONUS = 6
RELEGATION_MORALE_PENALTY = -6


def match_result_morale_deltas(winner_id: int | None, home_id: int, away_id: int,
                               tied: bool, is_cup: bool = False) -> dict[int, int]:
    """Whole-squad morale delta per team for a completed match — a club is
    collectively lifted or deflated by a result, not just the XI that
    played. Cup fixtures carry higher stakes than a league game."""
    stakes = CUP_STAKES_MULTIPLIER if is_cup else 1.0
    if tied or winner_id is None:
        return {home_id: TIE_MORALE_DELTA, away_id: TIE_MORALE_DELTA}
    loser_id = away_id if winner_id == home_id else home_id
    return {winner_id: round(WIN_MORALE_DELTA * stakes), loser_id: round(LOSS_MORALE_DELTA * stakes)}


def dropped_from_xi(previous_xi: Sequence[int], new_xi: Sequence[int]) -> list[int]:
    """Player ids who were in the previous match's XI but aren't in the
    new one — the real-world "unhappy to be dropped" case."""
    new_set = set(new_xi)
    return [player_id for player_id in previous_xi if player_id not in new_set]
