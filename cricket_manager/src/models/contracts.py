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


# ---------------------------------------------------------------------------
# v5.3.1: agent-led, multi-round talks
# ---------------------------------------------------------------------------

def agent_demand(player: Mapping[str, Any], agent: Mapping[str, Any] | None, offer_years: int,
                 rounds_used: int = 0, league_reputation: int = 70) -> dict[str, int]:
    """What the player's camp is asking for this round: a weekly wage and a
    one-off signing bonus. Agents concede a little each round they stay at
    the table, more readily when they like the club."""
    from .agents import demand_multiplier
    valuation = contract_valuation(player, league_reputation)
    morale = int((player.get("mental") or {}).get("morale", 60))
    age = int(player.get("age", 25))
    multiplier = demand_multiplier(agent) + (60 - morale) * 0.003
    if age >= 32 and offer_years >= 3:
        multiplier -= 0.04  # security late in a career is worth money
    if age <= 23 and offer_years >= 4:
        multiplier += 0.04  # tying down a young talent costs more
    multiplier *= max(0.9, 1 - 0.02 * rounds_used)
    wage = int(round(valuation * multiplier / 50) * 50)
    greed = int((agent or {}).get("greed", 6))
    bonus = int(round(wage * max(0, greed - 6) * 0.8 / 1_000) * 1_000)
    return {"wage": wage, "bonus": bonus}


def negotiate_round(player: Mapping[str, Any], agent: Mapping[str, Any] | None, offer_wage: int,
                    offer_years: int, signing_bonus: int, rounds_used: int, patience_left: int,
                    league_reputation: int = 70) -> dict[str, Any]:
    """One round of agent talks.

    Returns ``outcome`` ("accept" | "counter" | "walkout"), the agent's
    ``demand`` (wage + bonus) and ``patience_cost`` (rounds this offer used
    up: a lowball costs two). The package is judged as a whole: every £1 of
    signing bonus is worth about 1/26th of £1 a week over a season."""
    name = player.get("name", "The player")
    demand = agent_demand(player, agent, offer_years, rounds_used, league_reputation)
    offered_value = offer_wage + signing_bonus / 26
    wanted_value = demand["wage"] + demand["bonus"] / 26
    ratio = offered_value / max(1, wanted_value)
    if ratio >= 0.995:
        return {"outcome": "accept", "demand": demand, "patience_cost": 0,
                "reason": f"{name} and his representatives accept the terms."}
    cost = 2 if ratio < 0.75 else 1
    if patience_left - cost <= 0:
        return {"outcome": "walkout", "demand": demand, "patience_cost": cost,
                "reason": "The agent has broken off talks — the club is not taking his client seriously."}
    reason = ("That offer is nowhere near. The agent warns you not to waste his time."
              if cost == 2 else "The agent comes back with a counter-proposal.")
    return {"outcome": "counter", "demand": demand, "patience_cost": cost, "reason": reason}
