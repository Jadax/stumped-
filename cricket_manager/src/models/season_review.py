"""Rich season review narrative generation.

Pure-function module that takes structured season data and produces a
prose summary suitable for an inbox message or narrative event.
"""
from __future__ import annotations

from typing import Any

# Season review templates keyed by board verdict
_VERDICT_INTROS = {
    "Delighted": [
        "It has been a season to remember for {team}.",
        "A magnificent campaign has the fans dreaming of more success.",
        "What a year it has been — the board are thrilled with proceedings.",
    ],
    "Content": [
        "It has been a solid season for {team}.",
        "A respectable campaign that the board can be satisfied with.",
        "Steady progress all round — the club is moving in the right direction.",
    ],
    "Under pressure": [
        "It has been a difficult season for {team}.",
        "The board expected more from this campaign.",
        "A season of frustration that will need to be addressed.",
    ],
    "Ultimatum": [
        "It has been a torrid season for {team}.",
        "The board have lost patience with the way things have gone.",
        "A disastrous campaign that has left the club in a perilous position.",
    ],
}

_POSITION_LINES = {
    1: "Winning the title was the crowning glory.",
    2: "A valiant title challenge fell just short.",
    3: "A strong third-place finish puts the club in contention.",
    "mid": "A mid-table finish was perhaps reflective of the campaign.",
    "bottom": "A battle against relegation defined much of the season.",
}

_AWARD_TEMPLATES = {
    "Batter": "With the bat, {name} was the standout performer across the league.",
    "Bowler": "With the ball, {name} proved to be the pick of the bunch.",
    "Player": "Overall, {name} was the player of the season — a true match-winner.",
    "Young Player": "The future looks bright with {name} winning Young Player of the Season.",
}


def generate_season_review(
    team_name: str,
    season: int,
    position: int | None,
    total_teams: int,
    verdict: str,
    wins: int,
    losses: int,
    draws: int,
    awards: dict[str, dict[str, Any]] | None = None,
    honours: list[str] | None = None,
) -> str:
    """Generate a prose season review narrative.

    Returns a multi-paragraph string suitable for an inbox message.
    """
    import random as _rng

    lines: list[str] = []

    # Opening — always include team name
    intros = _VERDICT_INTROS.get(verdict, _VERDICT_INTROS["Content"])
    opening = _rng.choice(intros).format(team=team_name)
    if team_name not in opening:
        opening = f"{team_name}. {opening}"
    lines.append(opening)

    # League summary
    if position is not None:
        if position == 1:
            pos_line = _POSITION_LINES[1]
        elif position == 2:
            pos_line = _POSITION_LINES[2]
        elif position <= total_teams // 3:
            pos_line = _POSITION_LINES[3]
        elif position > total_teams * 2 // 3:
            pos_line = _POSITION_LINES["bottom"]
        else:
            pos_line = _POSITION_LINES["mid"]
        lines.append(f"Finishing {position}{'st' if position == 1 else 'nd' if position == 2 else 'rd' if position == 3 else 'th'} "
                     f"out of {total_teams} teams, {pos_line}")

    # Results summary
    total = wins + losses + draws
    if total > 0:
        win_pct = wins * 100 // total
        if win_pct >= 60:
            lines.append(f"The win rate of {win_pct}% was among the best in the league.")
        elif win_pct >= 40:
            lines.append(f"A win rate of {win_pct}% kept the club competitive throughout.")
        else:
            lines.append(f"Winning just {wins} of {total} matches ({win_pct}%) was below expectations.")

    # Trophies
    if honours:
        if len(honours) == 1:
            lines.append(f"The season was capped by winning the {honours[0]}.")
        else:
            lines.append(f"The silverware cabinet grew with {len(honours)} trophies: {', '.join(honours)}.")

    # Individual awards
    if awards:
        for award_type, winner in awards.items():
            if winner and winner.get("name"):
                template = _AWARD_TEMPLATES.get(award_type)
                if template:
                    lines.append(template.format(name=winner["name"]))

    # Closing
    if verdict == "Delighted":
        lines.append("The foundations are laid for an even bigger season ahead.")
    elif verdict == "Content":
        lines.append("With continued investment, next season could be even better.")
    elif verdict == "Under pressure":
        lines.append("Reinforcements will be needed if the club is to improve next year.")
    else:
        lines.append("Major changes may be required to arrest this decline.")

    return " ".join(lines)
