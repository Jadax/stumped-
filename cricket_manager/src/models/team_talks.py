"""Pre-match team talks: a manager-chosen tone nudges squad morale before
kickoff. Mirrors src/models/morale.py's role as a shared pure-function
source of truth for both clients — previously board/squad confidence only
ever moved via passive events (results, contracts, promotion), never a
manager-driven interaction.
"""
from __future__ import annotations
import random
from typing import Any

# (min, max) whole-squad morale delta per tone — a calmer talk is
# reliable but modest, an aggressive one is higher-risk/higher-reward
# (can genuinely backfire, unlike the other two).
TEAM_TALK_TONES: dict[str, tuple[int, int]] = {
    "Calm": (1, 4),
    "Assertive": (-2, 7),
    "Aggressive": (-8, 10),
}


def deliver_team_talk(tone: str, rng: random.Random | None = None,
                      perk_ids: frozenset[str] | set[str] = frozenset()) -> dict[str, Any]:
    """Roll this talk's morale swing and a flavour reaction line.

    v4.58.0: `perk_ids` are the calling manager's unlocked manager-progression
    perks (src/models/manager_progression.py) — "motivational_speaker" widens
    the upside, "squad_harmony" raises Aggressive's floor so it can no longer
    badly backfire. Optional/backward-compatible: every existing caller
    passing no perk_ids behaves exactly as before."""
    if tone not in TEAM_TALK_TONES:
        raise ValueError(f"Unknown team talk tone: {tone}")
    rng = rng or random.Random()
    low, high = TEAM_TALK_TONES[tone]
    if "motivational_speaker" in perk_ids:
        high += 3
    if tone == "Aggressive" and "squad_harmony" in perk_ids:
        low = max(low, -2)
    delta = rng.randint(low, high)
    if delta >= 7:
        reaction = "The dressing room is fired up — you can feel it."
    elif delta >= 3:
        reaction = "The talk landed well. Heads are up."
    elif delta >= 0:
        reaction = "A muted response from the squad."
    else:
        reaction = "That didn't land — a few players looked unconvinced."
    return {"tone": tone, "delta": delta, "reaction": reaction}
