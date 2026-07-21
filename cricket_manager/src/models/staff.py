"""Coaching, medical, and scouting staff: generation, rating, and effects.

Every club fields a real named staff roster (not just abstract facility
levels). Coaches accelerate training in their discipline, medical staff
reduce injury likelihood and speed recovery, and scouts sharpen the
accuracy of opposition/transfer-market ability estimates — mirroring the
staff department found in Football Manager, OOTP, and similar sims.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

#: (role, group, primary attribute key, headline label) — one row generated
#: per club per role. Coaching roles map onto training_assignments' four
#: discipline groups; Medical and Scouting are department-wide.
ROLES: tuple[tuple[str, str, str], ...] = (
    ("Head Coach", "Coaching", "coaching"),
    ("Batting Coach", "Coaching", "coaching"),
    ("Bowling Coach", "Coaching", "coaching"),
    ("Fielding Coach", "Coaching", "coaching"),
    ("Fitness Coach", "Coaching", "coaching"),
    ("Doctor", "Medical", "physiotherapy"),
    ("Physio", "Medical", "physiotherapy"),
    ("Chief Scout", "Scouting", "judging_ability"),
    ("Scout", "Scouting", "judging_ability"),
)

#: Coach role -> training_assignments focus group it accelerates.
COACH_DISCIPLINE = {
    "Batting Coach": "batting", "Bowling Coach": "bowling",
    "Fielding Coach": "fielding", "Fitness Coach": "mental", "Head Coach": "all",
}


def _attribute(rng: random.Random, centre: float, spread: float = 3.0) -> int:
    return max(1, min(20, round(rng.gauss(centre, spread))))


def generate_staff_member(role: str, group: str, nationality: str, name: str,
                          rng: random.Random, club_quality: float = 10.0) -> dict[str, Any]:
    """One staff member with role-appropriate attributes, all on a 1-20 scale."""
    age = rng.randint(32, 63)
    centre = max(4.0, min(18.0, club_quality + rng.uniform(-2.5, 2.5)))
    if group == "Coaching":
        attributes = {
            "coaching": _attribute(rng, centre),
            "man_management": _attribute(rng, centre - 1),
            "working_with_youngsters": _attribute(rng, centre - (2 if age > 50 else -1)),
        }
        headline = attributes["coaching"]
    elif group == "Medical":
        attributes = {
            "physiotherapy": _attribute(rng, centre),
            "sports_science": _attribute(rng, centre - 1),
        }
        headline = attributes["physiotherapy"]
    else:
        attributes = {
            "judging_ability": _attribute(rng, centre),
            "judging_potential": _attribute(rng, centre - 1.5),
            "adaptability": _attribute(rng, centre - 1),
        }
        headline = round((attributes["judging_ability"] + attributes["judging_potential"]) / 2)
    overall = max(1, min(20, headline))
    wage = int(round((300 + overall * 85) / 25) * 25)
    return {"name": name, "age": age, "nationality": nationality, "role": role,
           "group_name": group, "attributes": attributes, "overall": overall,
           "wage": wage, "contract_years_remaining": rng.randint(1, 4)}


def coach_training_multiplier(coaching_rating: int) -> float:
    """1.0 at an average (10) coach; ~0.8x-1.24x across the 1-20 range."""
    return max(0.72, min(1.32, 1 + (coaching_rating - 10) * .028))


def medical_injury_multiplier(physiotherapy_rating: int) -> float:
    """Individual physio quality on top of the club's medical facility level."""
    return max(0.72, min(1.12, 1 - (physiotherapy_rating - 10) * .014))


def scouting_noise(judging_ability: int, judging_potential: int) -> tuple[float, float]:
    """(overall_noise_stddev, potential_noise_stddev) — tighter for better scouts.

    A Judge Ability/Potential of 20 (world-class) narrows the estimate to
    roughly +/-1; an untrained scout (1) can be off by +/-9 or more.
    """
    overall_noise = max(0.6, 9.5 - judging_ability * 0.43)
    potential_noise = max(1.0, 12.5 - judging_potential * 0.55)
    return overall_noise, potential_noise


def apply_scouting_estimate(player: Mapping[str, Any], scout_rating: tuple[int, int],
                            rng: random.Random) -> dict[str, int]:
    """A deterministic-per-call noisy overall/potential estimate for a scouted player."""
    overall_noise, potential_noise = scouting_noise(*scout_rating)
    estimated_overall = round(max(1, min(100, rng.gauss(player["overall"], overall_noise))))
    estimated_potential = round(max(estimated_overall, min(100, rng.gauss(player["potential"], potential_noise))))
    return {"estimated_overall": estimated_overall, "estimated_potential": estimated_potential,
           "confidence": round(max(10, min(99, 100 - overall_noise * 6)))}


def age_staff_member(attributes: dict[str, int], age: int, rng: random.Random) -> dict[str, int]:
    """Season-rollover drift: young staff slowly improve, veterans slowly fade."""
    updated = dict(attributes)
    for key, value in attributes.items():
        if age < 40 and rng.random() < .18:
            updated[key] = max(1, min(20, value + 1))
        elif age > 56 and rng.random() < .12:
            updated[key] = max(1, min(20, value - 1))
    return updated
