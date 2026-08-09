"""Templated press-conference Q&A: a question drawn from the club's
current league position, a manager tone response nudges board confidence
and squad morale — the first manager-driven lever on board confidence;
previously it only ever moved via the passive season-end review
(src/models/career.py's board_confidence, called once a season).
"""
from __future__ import annotations
from typing import Any

# Fixed (not randomised) deltas per tone, kept deliberately simple for a
# scoped v1 — templated questions, templated tone-choice responses, no
# branching dialogue tree.
RESPONSE_TONES: dict[str, dict[str, int]] = {
    "Confident": {"confidence": 5, "morale": 1,
                 "line": "\"We back ourselves. I expect us to keep pushing forward.\""},
    "Diplomatic": {"confidence": 2, "morale": 2,
                  "line": "\"Every game is tough at this level — we'll take it step by step.\""},
    "Critical": {"confidence": -2, "morale": -3,
                "line": "\"Some individuals need to raise their standards, frankly.\""},
    "Humble": {"confidence": 1, "morale": 3,
              "line": "\"The credit belongs to the players. I just try to support them.\""},
}


def press_conference_question(position: int | None, team_count: int = 12) -> str:
    """A question flavoured by table position — high-level context only,
    not a deep branching interview system. Used for the pre-match presser."""
    if position is None:
        return "How do you assess the squad's progress so far this season?"
    if position <= max(1, team_count // 4):
        return "You're flying high in the table — how confident are you of keeping this up?"
    if position >= team_count - 1:
        return "Results have been difficult lately. What's your response to concerned fans?"
    return "A solid mid-table season so far — what's the plan from here?"


def press_conference_question_post_match(outcome: str, opponent: str) -> str:
    """A question flavoured by the result of the match just played
    (outcome is 'won'/'lost'/'tied') — the post-match presser, mirroring
    how FM/Cricket Captain always ask about the game you just finished
    rather than a generic season-progress question."""
    if outcome == "won":
        return f"A big win over {opponent} — talk us through how the team pulled that off."
    if outcome == "lost":
        return f"A tough defeat to {opponent} today. What went wrong out there?"
    return f"A tightly-fought tie with {opponent}. Are you satisfied with that result?"


def answer_press_conference(tone: str, outcome: str | None = None,
                            perk_ids: frozenset[str] | set[str] = frozenset()) -> dict[str, Any]:
    """outcome ('won'/'lost'/'tied'/None) nudges the confidence delta on
    top of the tone's fixed value — so the answer's *effect* on the board
    genuinely depends on both what you said and what actually happened on
    the pitch, not the tone alone. Pre-match pressers (outcome=None) are
    unaffected.

    v4.58.0: `perk_ids` are the calling manager's unlocked manager-progression
    perks (src/models/manager_progression.py) — "media_trained" softens
    Critical's downside, "calm_head" nudges every confidence delta up.
    Optional/backward-compatible: every existing caller passing no perk_ids
    behaves exactly as before."""
    if tone not in RESPONSE_TONES:
        raise ValueError(f"Unknown press conference tone: {tone}")
    entry = dict(RESPONSE_TONES[tone])
    if tone == "Critical" and "media_trained" in perk_ids:
        entry["confidence"] = max(entry["confidence"], -1)
        entry["morale"] = max(entry["morale"], -1)
    outcome_bonus = {"won": 2, "lost": -2, "tied": 0, None: 0}.get(outcome, 0)
    confidence_delta = entry["confidence"] + outcome_bonus
    if "calm_head" in perk_ids:
        confidence_delta += 1
    return {"tone": tone, "confidence_delta": confidence_delta,
           "morale_delta": entry["morale"], "quote": entry["line"]}
