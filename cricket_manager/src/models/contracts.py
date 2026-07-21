"""Contract negotiation model — the manager side of FM/OOTP-style talks.

A player has a private valuation derived from the same wage model used for
new signings.  An offer is judged against that valuation, current morale,
age, and years of security already on the books; the player either accepts,
counters with a number partway between the offer and their valuation, or
rejects outright if the gap is too wide or they are unhappy.
"""
from __future__ import annotations

from typing import Any, Mapping

from .player import calculate_wage


def contract_valuation(player: Mapping[str, Any], league_reputation: int = 70) -> int:
    """The player's private idea of a fair weekly wage."""
    return calculate_wage(int(player.get("overall", 50)), int(player.get("age", 25)),
                          str(player.get("role", "Batsman")), int(player.get("potential", player.get("overall", 50))),
                          league_reputation, max(1, int(player.get("contract_years_remaining", 1))))


def negotiate(player: Mapping[str, Any], offer_wage: int, offer_years: int,
             signing_bonus: int = 0, league_reputation: int = 70) -> dict[str, Any]:
    """Judge one round of a contract offer.

    Returns ``{"outcome": "accept"|"counter"|"reject", "counter_wage": int|None,
    "reason": str}``.
    """
    valuation = contract_valuation(player, league_reputation)
    morale = int(player.get("mental", {}).get("morale", 60))
    age = int(player.get("age", 25))
    years_left = int(player.get("contract_years_remaining", 1))

    ratio = offer_wage / max(1, valuation)
    # Bonuses count for a fraction of a year's wage towards the ratio.
    ratio += (signing_bonus / max(1, valuation)) * 0.08
    # Unhappy players demand a premium; settled players are more reasonable.
    demand_shift = (60 - morale) * 0.003
    # Players low on contract security accept a slightly lower rate to lock in a deal;
    # long-served veterans with plenty of years left hold out for more.
    security_shift = -0.03 if years_left <= 1 else 0.02 if years_left >= 3 else 0.0
    threshold = 1.0 + demand_shift + security_shift
    # Very short contract offers to ageing veterans, or very long ones to
    # rebuilding youngsters, are unwelcome regardless of money.
    length_penalty = 0.0
    if age >= 32 and offer_years >= 4:
        length_penalty = 0.05
    elif age <= 21 and offer_years <= 1:
        length_penalty = 0.04
    threshold += length_penalty

    if ratio >= threshold:
        return {"outcome": "accept", "counter_wage": None,
               "reason": f"{player.get('name', 'The player')} is satisfied with the terms and signs."}
    if ratio >= threshold - 0.22:
        counter = int(round(valuation * (threshold + 0.02) / 50) * 50)
        return {"outcome": "counter", "counter_wage": counter,
               "reason": f"{player.get('name', 'The player')} wants a higher weekly wage."}
    return {"outcome": "reject", "counter_wage": None,
           "reason": f"{player.get('name', 'The player')} feels the offer falls well short of their value."}
