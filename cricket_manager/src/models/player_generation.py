"""Calibrated fictional-player generation helpers."""
from __future__ import annotations
import random
from .player import calculate_wage, clamp

def realistic_rating(division: int, age: int, rng: random.Random) -> int:
    centre = 68 if division == 1 else 55
    if age < 18: centre -= 15
    elif age < 20: centre -= 9
    elif age > 35: centre -= (age - 35) * 2
    roll = rng.random()
    if roll < .003: return rng.randint(96, 99)
    if roll < .018: return rng.randint(86, 95)
    if roll < .085: return rng.randint(75, 85)
    return clamp(rng.gauss(centre, 7.5))

def wage_for_player(overall: int, age: int, role: str, potential: int, division: int) -> int:
    return calculate_wage(overall, age, role, potential, 78 if division == 1 else 52)
