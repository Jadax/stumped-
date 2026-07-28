"""Calibrated fictional-player generation helpers."""
from __future__ import annotations
from .player import calculate_wage

def wage_for_player(overall: int, age: int, role: str, potential: int, division: int) -> int:
    return calculate_wage(overall, age, role, potential, 78 if division == 1 else 52)
